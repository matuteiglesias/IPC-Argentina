import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.package_v2_candidate import package, sha256


class PublicationTests(unittest.TestCase):
    def make_release(self, root: Path) -> Path:
        rid = "arg-monetary-conversion-v1-fixture"
        release = root / rid
        release.mkdir()
        (release / "monthly_conversion_factors.csv").write_text("period,factor\n2024-01-01,1\n")
        manifest = {
            "schema": "research-artifact-manifest/v1",
            "artifact_type": "research.argentina-monetary-conversion/v1",
            "release_id": rid,
            "status": "candidate",
            "created_at": "2026-08-31T00:00:00Z",
            "method_id": "research.argentina-price-consensus/curated-official-panel-v2",
            "monetary_reference_id": "research.argentina-price-consensus/curated-official-panel-v2@2016-01=100",
            "parent": {"release_id": "arg-price-consensus-v2-fixture"},
        }
        (release / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return release

    def test_package_is_deterministic_and_self_describing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = self.make_release(root)
            first = package(release, root / "a")
            second = package(release, root / "b")
            self.assertEqual(sha256(Path(first["asset"])), sha256(Path(second["asset"])))
            discovery = json.loads(Path(first["discovery"]).read_text())
            self.assertEqual(discovery["release_id"], release.name)
            self.assertEqual(discovery["status"], "candidate")
            self.assertEqual(discovery["github_release"]["asset_sha256"], sha256(Path(first["asset"])))
            with zipfile.ZipFile(first["asset"]) as zf:
                self.assertEqual(sorted(zf.namelist()), [
                    f"{release.name}/manifest.json",
                    f"{release.name}/monthly_conversion_factors.csv",
                ])

    def test_refuses_non_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = self.make_release(Path(tmp))
            manifest = json.loads((release / "manifest.json").read_text())
            manifest["status"] = "approved"
            (release / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "only_candidate_publication_supported"):
                package(release, Path(tmp) / "out")


if __name__ == "__main__":
    unittest.main()
