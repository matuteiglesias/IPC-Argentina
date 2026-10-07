import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from arg_price.v2 import load_policy
from arg_price.v2_promote import promote
from arg_price.v2_validate import validate_release

ROOT = Path(__file__).parents[1]
POLICY = load_policy(ROOT / "contracts/panel_v2.json")


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(root: Path, manifest: dict, payload_names: list[str]) -> None:
    manifest["files"] = [
        {
            "path": name,
            "sha256": sha(root / name),
            "size": (root / name).stat().st_size,
        }
        for name in payload_names
    ]
    (root / "manifest.json").write_bytes(canonical(manifest))


class PromotionTests(unittest.TestCase):
    def candidates(self, root: Path, *, approved_latest: bool = True):
        consensus_id = "arg-price-consensus-v2-fixture"
        consensus = root / consensus_id
        consensus.mkdir()
        count = "3" if approved_latest else "2"
        coverage = "acceptable_coverage" if approved_latest else "thin_coverage"
        eligible = "true" if approved_latest else "false"
        with (consensus / "monthly_consensus.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "period",
                    "consensus_monthly_inflation_pct",
                    "median_monthly_inflation_pct",
                    "min_monthly_inflation_pct",
                    "max_monthly_inflation_pct",
                    "population_std_monthly_inflation_pct",
                    "contributing_member_ids",
                    "contributing_source_ids",
                    "contributing_source_count",
                    "coverage_class",
                    "approved_mode_eligible",
                    "noncontributing_member_reasons",
                    "consensus_index",
                    "index_status",
                    "method_id",
                ],
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerow(
                {
                    "period": "2016-01-01",
                    "consensus_monthly_inflation_pct": "2",
                    "median_monthly_inflation_pct": "2",
                    "min_monthly_inflation_pct": "1",
                    "max_monthly_inflation_pct": "3",
                    "population_std_monthly_inflation_pct": "0.8",
                    "contributing_member_ids": "caba|cordoba|san_luis",
                    "contributing_source_ids": "a|b|c",
                    "contributing_source_count": count,
                    "coverage_class": coverage,
                    "approved_mode_eligible": eligible,
                    "noncontributing_member_reasons": "",
                    "consensus_index": "100",
                    "index_status": "anchored",
                    "method_id": POLICY["method_id"],
                }
            )
        (consensus / "normalized_parent.json").write_text("{}\n")
        (consensus / "method.json").write_text("{}\n")
        (consensus / "qa.json").write_text("{}\n")
        (consensus / "limitations.md").write_text("# Limitations\n")
        consensus_manifest = {
            "schema": "research-artifact-manifest/v1",
            "artifact_type": POLICY["consensus_artifact_type"],
            "release_id": consensus_id,
            "status": "candidate",
            "method_id": POLICY["method_id"],
            "monetary_reference_id": POLICY["monetary_reference_id"],
            "created_at": "2026-10-07T00:00:00Z",
            "parent": {"release_id": "normalized-fixture"},
            "warnings": [],
        }
        write_manifest(
            consensus,
            consensus_manifest,
            [
                "monthly_consensus.csv",
                "normalized_parent.json",
                "method.json",
                "qa.json",
                "limitations.md",
            ],
        )
        consensus_sha = sha(consensus / "manifest.json")

        conversion_id = "arg-monetary-conversion-v1-fixture"
        conversion = root / conversion_id
        conversion.mkdir()
        (conversion / "monthly_conversion_factors.csv").write_text(
            "period,reference_period,consensus_index,factor_period_to_reference,"
            "factor_reference_to_period,coverage_class,approved_mode_eligible\n"
            f"2016-01-01,2016-01-01,100,1,1,{coverage},{eligible}\n",
            encoding="utf-8",
        )
        (conversion / "consensus_parent.json").write_bytes(
            canonical(
                {
                    "artifact_type": POLICY["consensus_artifact_type"],
                    "release_id": consensus_id,
                    "manifest_sha256": consensus_sha,
                }
            )
        )
        (conversion / "qa.json").write_text("{}\n")
        (conversion / "limitations.md").write_text("# Limitations\n")
        conversion_manifest = {
            "schema": "research-artifact-manifest/v1",
            "artifact_type": POLICY["conversion_artifact_type"],
            "release_id": conversion_id,
            "status": "candidate",
            "method_id": POLICY["method_id"],
            "monetary_reference_id": POLICY["monetary_reference_id"],
            "created_at": "2026-10-07T00:00:00Z",
            "parent": {
                "artifact_type": POLICY["consensus_artifact_type"],
                "release_id": consensus_id,
                "manifest_sha256": consensus_sha,
            },
            "warnings": [],
        }
        write_manifest(
            conversion,
            conversion_manifest,
            [
                "monthly_conversion_factors.csv",
                "consensus_parent.json",
                "qa.json",
                "limitations.md",
            ],
        )
        return consensus, conversion

    def decision(
        self,
        root: Path,
        consensus: Path,
        conversion: Path,
        *,
        decision: str = "approved",
    ):
        audit = root / "audit-summary.json"
        audit.write_bytes(
            canonical(
                {
                    "schema": "argentina-price-v1-v2-scientific-audit/v1",
                    "status": "diagnostic_only_no_promotion",
                }
            )
        )
        record = {
            "schema": "argentina-price-v2-promotion-decision/v1",
            "decision_id": "ipc-v2-owner-review-fixture",
            "decision": decision,
            "approved_by": "owner-fixture",
            "decided_at": "2026-10-07T00:00:00Z",
            "candidates": {
                "consensus": {
                    "release_id": consensus.name,
                    "manifest_sha256": sha(consensus / "manifest.json"),
                },
                "conversion": {
                    "release_id": conversion.name,
                    "manifest_sha256": sha(conversion / "manifest.json"),
                },
            },
            "audit": {"summary_sha256": sha(audit)},
        }
        path = root / "decision.json"
        path.write_bytes(canonical(record))
        return path, audit

    def test_promotion_materializes_immutable_approved_children(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consensus, conversion = self.candidates(root)
            decision, audit = self.decision(root, consensus, conversion)
            result = promote(
                consensus,
                conversion,
                decision,
                audit,
                root / "approved",
            )
            approved_consensus = json.loads(
                (result["consensus"] / "manifest.json").read_text()
            )
            approved_conversion = json.loads(
                (result["conversion"] / "manifest.json").read_text()
            )
            self.assertEqual(approved_consensus["status"], "approved")
            self.assertEqual(approved_conversion["status"], "approved")
            self.assertNotEqual(approved_consensus["release_id"], consensus.name)
            self.assertEqual(
                approved_conversion["parent"]["release_id"],
                approved_consensus["release_id"],
            )
            self.assertEqual(
                validate_release(result["consensus"], POLICY, True),
                [],
            )
            self.assertEqual(validate_release(result["conversion"], POLICY), [])
            self.assertEqual(
                json.loads((consensus / "manifest.json").read_text())["status"],
                "candidate",
            )

    def test_nonapproved_decision_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consensus, conversion = self.candidates(root)
            decision, audit = self.decision(
                root,
                consensus,
                conversion,
                decision="rejected",
            )
            with self.assertRaisesRegex(
                ValueError,
                "promotion_decision_is_not_approved",
            ):
                promote(
                    consensus,
                    conversion,
                    decision,
                    audit,
                    root / "approved",
                )

    def test_thin_latest_consensus_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consensus, conversion = self.candidates(
                root,
                approved_latest=False,
            )
            decision, audit = self.decision(root, consensus, conversion)
            with self.assertRaisesRegex(
                ValueError,
                "latest_period_not_approved_mode_eligible",
            ):
                promote(
                    consensus,
                    conversion,
                    decision,
                    audit,
                    root / "approved",
                )


if __name__ == "__main__":
    unittest.main()
