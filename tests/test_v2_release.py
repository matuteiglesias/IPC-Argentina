import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from arg_price.v2 import load_policy
from arg_price.v2_release import build_all
from arg_price.v2_validate import validate_release

ROOT = Path(__file__).parents[1]
POLICY = load_policy(ROOT / "contracts/panel_v2.json")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(source_id, filename, raw):
    content_type = "application/json" if filename.endswith((".json", ".php")) else "text/csv"
    return {
        "source_id": source_id,
        "status": "pinned",
        "resolved_url": "fixture://" + filename,
        "retrieved_at_utc": "2026-08-31T00:00:00+00:00",
        "headers": {"content-type": content_type},
        "byte_size": len(raw),
        "sha256": sha(raw),
        "snapshot_path": "snapshots/" + filename,
        "parser_id": source_id + "/fixture-v1",
        "source_base_or_vintage": "fixture",
    }


class V2ReleaseTests(unittest.TestCase):
    def make_bundle(self, parent):
        root = Path(parent) / "bundle"; snapshots = root / "snapshots"; snapshots.mkdir(parents=True)
        cordoba = "\n".join([
            "Índice de Precios al Consumidor de Córdoba. Nivel General;;;;",
            "Índice mensual empalmado con la serie anterior;;;;",
            "fixture period;;;;",
            ";;;;",
            "COICOP;Descripción;dic-15;ene-16;feb-16",
            ";NIVEL GENERAL;100,00;102,00;104,04",
        ]).encode("cp1252")
        neuquen = b'[{"anio":"2015","mes":"12","indice":"200"},{"anio":"2016","mes":"1","indice":"206"},{"anio":"2016","mes":"2","indice":"210.12"}]'
        (snapshots / "cordoba.csv").write_bytes(cordoba)
        (snapshots / "neuquen.php").write_bytes(neuquen)
        entries = [
            {"source_id": "indec_ipc_gba_historical", "status": "unavailable", "warning_code": "source_unavailable"},
            {"source_id": "indec_ipc_national", "status": "unavailable", "warning_code": "source_unavailable"},
            {"source_id": "idecba_ipc_level_general_empalmed", "status": "unavailable", "warning_code": "source_unavailable"},
            pinned("cordoba_ipc", "cordoba.csv", cordoba),
            {"source_id": "san_luis_ipc_provincial", "status": "unavailable", "warning_code": "source_unavailable"},
            pinned("neuquen_ipc_provincial", "neuquen.php", neuquen),
        ]
        lock = {"schema": "price-source-lock/v1", "registry_id": "fixture", "entries": entries}
        (root / "source_lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
        return root

    def test_full_release_chain_and_thin_coverage_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self.make_bundle(tmp)
            result = build_all(bundle / "source_lock.json", Path(tmp) / "out")
            for kind in ("normalized", "consensus", "conversion"):
                self.assertEqual(validate_release(result[kind], POLICY), [])
            consensus_errors = validate_release(result["consensus"], POLICY, require_approved_latest=True)
            self.assertEqual(consensus_errors, ["latest_period_not_approved_mode_eligible"])
            manifest = json.loads((result["consensus"] / "manifest.json").read_text())
            self.assertEqual(manifest["artifact_type"], "research.argentina-price-consensus/v2")
            qa = json.loads((result["consensus"] / "qa.json").read_text())
            self.assertEqual(qa["latest_coverage_class"], "thin_coverage")

    def test_release_identity_survives_source_bundle_relocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = self.make_bundle(Path(tmp) / "a")
            second_parent = Path(tmp) / "b"; second_parent.mkdir()
            shutil.copytree(first, second_parent / "bundle")
            second = second_parent / "bundle"
            a = build_all(first / "source_lock.json", Path(tmp) / "out-a")
            b = build_all(second / "source_lock.json", Path(tmp) / "out-b")
            for kind in ("normalized", "consensus", "conversion"):
                ma = json.loads((a[kind] / "manifest.json").read_text())
                mb = json.loads((b[kind] / "manifest.json").read_text())
                self.assertEqual(ma["release_id"], mb["release_id"])
                self.assertEqual((a[kind] / "manifest.json").read_bytes(), (b[kind] / "manifest.json").read_bytes())
            parent = json.loads((a["normalized"] / "source_parent.json").read_text())
            self.assertNotIn(str(first.resolve()), json.dumps(parent))


if __name__ == "__main__":
    unittest.main()
