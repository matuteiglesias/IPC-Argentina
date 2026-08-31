import csv
import json
import tempfile
import unittest
from pathlib import Path

from arg_price.v2_audit import audit


def write_csv(path, fields, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


class V2AuditTests(unittest.TestCase):
    def test_common_support_and_robustness_are_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "legacy.csv"
            normalized = root / "normalized.csv"
            consensus = root / "consensus.csv"
            write_csv(legacy, ["", "index", "pct_m"], [
                {"": "2014-01-01", "index": "80", "pct_m": "2.0"},
                {"": "2014-02-01", "index": "82", "pct_m": "2.5"},
                {"": "2016-01-01", "index": "100", "pct_m": "2.0"},
                {"": "2016-02-01", "index": "102.2", "pct_m": "2.2"},
            ])
            fields = ["source_id", "panel_member_id", "period", "eligibility_status", "monthly_change_status", "monthly_inflation_pct"]
            rows = []
            for period, values in {
                "2014-01-01": [("caba", 1.8), ("cordoba", 2.0), ("san_luis", 2.2)],
                "2014-02-01": [("caba", 2.2), ("cordoba", 2.4), ("san_luis", 2.6)],
                "2016-01-01": [("caba", 1.9), ("cordoba", 2.0), ("san_luis", 2.1)],
                "2016-02-01": [("caba", 2.0), ("cordoba", 2.2), ("san_luis", 2.4)],
            }.items():
                for member, rate in values:
                    rows.append({"source_id": member + "_source", "panel_member_id": member, "period": period, "eligibility_status": "eligible", "monthly_change_status": "eligible_rate", "monthly_inflation_pct": str(rate)})
            write_csv(normalized, fields, rows)
            write_csv(consensus, ["period", "consensus_monthly_inflation_pct", "consensus_index", "contributing_source_count", "coverage_class"], [
                {"period": "2014-01-01", "consensus_monthly_inflation_pct": "2.0", "consensus_index": "80.5", "contributing_source_count": "3", "coverage_class": "acceptable_coverage"},
                {"period": "2014-02-01", "consensus_monthly_inflation_pct": "2.4", "consensus_index": "82.432", "contributing_source_count": "3", "coverage_class": "acceptable_coverage"},
                {"period": "2016-01-01", "consensus_monthly_inflation_pct": "2.0", "consensus_index": "100", "contributing_source_count": "3", "coverage_class": "acceptable_coverage"},
                {"period": "2016-02-01", "consensus_monthly_inflation_pct": "2.2", "consensus_index": "102.2", "contributing_source_count": "3", "coverage_class": "acceptable_coverage"},
            ])
            out = root / "audit"
            summary = audit(legacy, normalized, consensus, out)
            self.assertEqual(summary["status"], "diagnostic_only_no_promotion")
            self.assertEqual(summary["common_monthly_change_comparison"]["count"], 4)
            self.assertEqual(summary["intervention_window_2007_2015"]["count"], 2)
            self.assertGreater(summary["robustness"]["max_absolute_single_member_dropout_shift_pct_points"], 0)
            self.assertGreaterEqual(summary["robustness"]["max_absolute_arithmetic_vs_geometric_gap_pct_points"], 0)
            self.assertTrue((out / "monthly_v1_v2_comparison.csv").is_file())
            self.assertTrue((out / "monthly_robustness.csv").is_file())
            persisted = json.loads((out / "summary.json").read_text())
            self.assertEqual(persisted["v2_coverage_counts"], {"acceptable_coverage": 4})


if __name__ == "__main__":
    unittest.main()
