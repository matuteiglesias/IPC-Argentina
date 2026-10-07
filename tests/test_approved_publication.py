import json
import tempfile
import unittest
from pathlib import Path

from scripts.package_v2_approved import package


class ApprovedPublicationTests(unittest.TestCase):
    def test_approved_release_packages_with_approved_transport(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rid = "arg-monetary-conversion-v1-approved-fixture"
            release = root / rid
            release.mkdir()
            (release / "monthly_conversion_factors.csv").write_text(
                "period,reference_period,consensus_index,factor_period_to_reference,"
                "factor_reference_to_period,coverage_class,approved_mode_eligible\n"
                "2016-01-01,2016-01-01,100,1,1,acceptable_coverage,true\n"
            )
            manifest = {
                "schema": "research-artifact-manifest/v1",
                "artifact_type": "research.argentina-monetary-conversion/v1",
                "release_id": rid,
                "status": "approved",
                "method_id": "research.argentina-price-consensus/curated-official-panel-v2",
                "monetary_reference_id": (
                    "research.argentina-price-consensus/"
                    "curated-official-panel-v2@2016-01=100"
                ),
                "created_at": "2026-10-07T00:00:00Z",
                "approved_at": "2026-10-07T01:00:00Z",
                "promotion": {
                    "decision_id": "decision-1",
                    "approved_by": "owner",
                    "adjudication_sha256": "a" * 64,
                    "audit_summary_sha256": "b" * 64,
                },
            }
            (release / "manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n"
            )
            result = package(release, root / "out")
            discovery = json.loads(Path(result["discovery"]).read_text())
            self.assertEqual(discovery["status"], "approved")
            self.assertEqual(
                discovery["github_release"]["tag"],
                f"approved-{rid}",
            )
            self.assertEqual(
                discovery["promotion"]["decision_id"],
                "decision-1",
            )

    def test_candidate_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "candidate"
            release.mkdir()
            (release / "manifest.json").write_text(
                json.dumps(
                    {
                        "artifact_type": "research.argentina-monetary-conversion/v1",
                        "method_id": (
                            "research.argentina-price-consensus/"
                            "curated-official-panel-v2"
                        ),
                        "release_id": "candidate",
                        "status": "candidate",
                    }
                )
            )
            with self.assertRaisesRegex(
                ValueError,
                "only_approved_publication_supported",
            ):
                package(release, root / "out")


if __name__ == "__main__":
    unittest.main()
