import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from arg_price.indec_regional_divisions import (
    INDEX_BASE,
    OUTPUT_FIELDS,
    build_release,
    coverage,
    normalize_csv,
    source_lock,
    validate_release,
)


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "indec-regional-divisions" / "serie_ipc_divisiones.csv"


class RegionalDivisionTests(unittest.TestCase):
    def raw(self):
        return FIXTURE.read_bytes()

    def test_multiple_regions_divisions_months_and_cell_lineage(self):
        rows = normalize_csv(self.raw())
        self.assertEqual(len(rows), 12)
        self.assertEqual({r["region_id"] for r in rows}, {"gran_buenos_aires", "pampeana"})
        self.assertEqual({r["division_id"] for r in rows}, {"coicop01", "coicop07"})
        self.assertEqual({r["period"] for r in rows}, {"2024-01-01", "2024-02-01", "2024-03-01"})
        self.assertTrue(all("#row=" in r["source_cell_identity"] and ";column=Indice_IPC;" in r["source_cell_identity"] for r in rows))
        self.assertTrue(all(r["index_base"] == INDEX_BASE for r in rows))
        self.assertTrue(all(r["value_status"] == "direct_official_observation" for r in rows))

    def test_duplicate_cell_rejected(self):
        raw = self.raw() + self.raw().splitlines(keepends=True)[1]
        with self.assertRaisesRegex(ValueError, "duplicate_cell"):
            normalize_csv(raw)

    def test_missing_region_division_diagnostics_do_not_impute(self):
        rows = normalize_csv(self.raw())
        cov = coverage(rows)
        self.assertEqual(cov["number_of_months"], 3)
        self.assertIn("noreste", cov["missing_region_ids"])
        self.assertIn("coicop12", cov["missing_division_ids"])
        self.assertGreater(cov["missing_cells_count"], 0)
        self.assertEqual(len(rows), 12, "coverage diagnostics must not materialize missing cells")

    def test_missing_month_is_explicit_and_counts_as_missing_cells(self):
        rows = [r for r in normalize_csv(self.raw()) if r["period"] != "2024-02-01"]
        cov = coverage(rows)
        self.assertEqual(cov["missing_months"], ["2024-02-01"])
        self.assertEqual(cov["expected_months_in_span"], 3)
        feb_missing = [r for r in cov["missing_cells"] if r["period"] == "2024-02-01"]
        self.assertEqual(len(feb_missing), 6 * 12)

    def test_base_period_inconsistency_rejected(self):
        text = self.raw().decode().replace(
            "Periodo,Region,Codigo,Descripcion_divisiones,Clasificador,Indice_IPC",
            "Periodo,Region,Codigo,Descripcion_divisiones,Clasificador,Indice_IPC,index_base",
        )
        lines = text.splitlines()
        lines[1] += ",2021=100"
        for i in range(2, len(lines)):
            lines[i] += ",2016-12=100"
        with self.assertRaisesRegex(ValueError, "base_period_inconsistent"):
            normalize_csv(("\n".join(lines) + "\n").encode())

    def test_deterministic_release_and_validation(self):
        raw = self.raw()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock_root = root / "lock"
            snap = lock_root / "snapshots" / "source.csv"
            snap.parent.mkdir(parents=True)
            snap.write_bytes(raw)
            lock = source_lock(raw, "2026-09-28T12:00:00Z")
            lock["snapshot_path"] = "snapshots/source.csv"
            lock_path = lock_root / "source_lock.json"
            lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
            first = build_release(lock_path, root / "releases")
            first_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in first.iterdir() if p.is_file()}
            second = build_release(lock_path, root / "releases")
            second_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in second.iterdir() if p.is_file()}
            self.assertEqual(first, second)
            self.assertEqual(first_hashes, second_hashes)
            self.assertEqual(validate_release(first), [])
            with (first / "regional_division_indices.csv").open() as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(tuple(rows[0]), OUTPUT_FIELDS)
            self.assertEqual(len(rows), 12)

    def test_real_coverage_gate_is_optional_for_hosted_fixture(self):
        raw = self.raw()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snap = root / "snap.csv"
            snap.write_bytes(raw)
            lock = source_lock(raw, "2026-09-28T12:00:00Z")
            lock["snapshot_path"] = "snap.csv"
            lock_path = root / "source_lock.json"
            lock_path.write_text(json.dumps(lock))
            release = build_release(lock_path, root / "releases")
            self.assertEqual(validate_release(release), [])
            self.assertIn(
                "required_2018_05_through_2025_coverage_missing",
                validate_release(release, require_engel_window=True),
            )


if __name__ == "__main__":
    unittest.main()
