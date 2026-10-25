"""Lightweight synthetic evidence for source-owned IPC v2 receipts (no price rows)."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.emit_ipc_candidate_receipt import PANEL, digest, receipt, evidence
from scripts.export_ipc_candidate_gcp import ExportError, build_entry, validate_receipt
from scripts.package_v2_candidate import package

SUCCESS = {key: "success" for key in
           ("source", "lock", "build", "validate", "package", "publish", "maturity", "approval")}

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n", encoding="utf-8")

def fixture(root: Path):
    lockpath = root / "build/price_sources/source_lock.json"
    write_json(lockpath, {
        "schema": "price-source-lock/v1",
        "entries": [
            {"source_id": item, "status": "pinned", "sha256": chr(97 + i) * 64,
             "byte_size": 42}
            for i, item in enumerate(("indec_ipc", "caba_ipc", "san_luis_ipc", "neuquen_ipc"))
        ] + [{"source_id": "cordoba_ipc", "status": "unavailable"}]})
    lock_sha = digest(lockpath)

    def artifact(kind, rid, atype, parent=None, extra=None):
        p = root / "artifacts/price_v2" / kind / rid
        p.mkdir(parents=True)
        (p / "data.csv").write_text("period,factor\n2000-01,1\n", encoding="utf-8")  # synthetic only
        qa = {"hard_failures": [], "result": "pass_with_warnings",
              "warnings": ["source_unavailable:cordoba_ipc"]}
        if kind == "consensus":
            qa.update({"latest_contributing_source_count": 2,
                       "latest_coverage_class": "thin_coverage",
                       "latest_period": "2026-09-01"})
        write_json(p / "qa.json", qa)
        files = ["data.csv", "qa.json"]
        if parent:
            filename = {"consensus": "normalized_parent.json", "conversion": "consensus_parent.json"}[kind]
            write_json(p / filename, parent)
            files.append(filename)
        if kind == "normalized":
            write_json(p / "source_parent.json", {
                "schema": "price-source-lock/v1",
                "registry_id": "registry:research.argentina-price-sources@2",
                "source_lock_sha256": lock_sha,
                "source_lock_transport": "external_content_addressed_parent",
            })
            files.append("source_parent.json")
        if kind == "consensus":
            write_json(p / "method.json", {
                "panel_member_ids": PANEL,
                "aggregation": {"dynamic_source_substitution": False},
            })
            files.append("method.json")
        manifest = {"schema": "research-artifact-manifest/v1",
                    "release_id": rid, "artifact_type": atype, "status": "candidate",
                    "files": [{"path": x, "sha256": digest(p / x),
                               "size": (p / x).stat().st_size} for x in files]}
        if parent:
            manifest["parent"] = parent
        if kind == "normalized":
            manifest["source_lock_sha256"] = lock_sha
        else:
            manifest["method_id"] = "research.argentina-price-consensus/curated-official-panel-v2"
        if kind == "conversion":
            manifest.update({"created_at": "2026-10-25T00:00:00Z",
                             "monetary_reference_id": "research.argentina-price-consensus/curated-official-panel-v2@2016-01=100"})
        if extra:
            manifest.update(extra)
        write_json(p / "manifest.json", manifest)
        return p, manifest

    n, nm = artifact("normalized", "synthetic-normalized", "publicdata.argentina-price-sources/v1")
    nref = {"release_id": nm["release_id"], "artifact_type": nm["artifact_type"],
            "manifest_sha256": digest(n / "manifest.json")}
    c, cm = artifact("consensus", "synthetic-consensus", "research.argentina-price-consensus/v2", nref)
    cref = {"release_id": cm["release_id"], "artifact_type": cm["artifact_type"],
            "manifest_sha256": digest(c / "manifest.json")}
    v, vm = artifact("conversion", "synthetic-conversion", "research.argentina-monetary-conversion/v1", cref)
    pub = root / "build/publication"
    package(v, pub)
    d = json.loads((pub / "discovery.json").read_text())
    write_json(pub / "verified-transport.json", {
        "schema": "ipc-candidate-transport-verified/v1",
        "tag": d["github_release"]["tag"],
        "asset_sha256": d["github_release"]["asset_sha256"],
        "discovery_sha256": digest(pub / "discovery.json"),
        "prerelease": True,
    })
    return {"lock": lockpath, "normalized": n, "consensus": c,
            "conversion": v, "publication": pub}

def observed(root, **kw):
    p = {"run_id": "39286713821", "attempt": "1", "event": "schedule",
         "mode": "full-v2", "require_approved": False, "job_status": "success",
         "started_at": "2026-10-25T09:37:00Z",
         "finished_at": "2026-10-25T09:39:00Z",
         "outcomes": SUCCESS.copy()}
    p.update(kw)
    return receipt(root, **p)

class SemanticReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = fixture(self.root)

    def test_scheduled_maturity_failure_preserves_verified_candidate(self):
        r = observed(self.root, outcomes={**SUCCESS, "maturity": "failure"})
        self.assertEqual(r["outputs"][0]["state"], "valid")
        self.assertEqual(r["result"]["artifact_state"], "healthy")
        self.assertEqual(r["result"]["execution_state"], "degraded")
        self.assertEqual(r["result"]["terminal_state"], "healthy")
        self.assertEqual(r["result"]["authority_state"], "candidate")
        self.assertEqual(r["stages"]["scheduled_maturity"], "failed")
        self.assertIn("thin_coverage", json.dumps(r))
        validate_receipt(r, "39286713821", "1")

    def test_manual_gate_succeeds_without_approving_candidate(self):
        r = observed(self.root, event="workflow_dispatch", require_approved=True)
        self.assertEqual(r["stages"]["manual_approval_gate"], "success")
        self.assertEqual(r["stages"]["scheduled_maturity"], "not_applicable")
        self.assertEqual(r["result"]["authority_state"], "candidate")

    def test_manual_gate_fails_closed_without_erasing_candidate(self):
        r = observed(self.root, event="workflow_dispatch", require_approved=True,
                     job_status="failure", outcomes={**SUCCESS, "approval": "failure"})
        self.assertEqual(r["outputs"][0]["state"], "valid")
        self.assertEqual(r["result"]["artifact_state"], "healthy")
        self.assertEqual(r["result"]["execution_state"], "failed")
        self.assertEqual(r["result"]["terminal_state"], "failed")
        self.assertEqual(r["stages"]["manual_approval_gate"], "failed")
        validate_receipt(r, "39286713821", "1")

    def test_source_only_has_no_candidate_output(self):
        r = observed(self.root, event="workflow_dispatch", mode="source-only",
                     outcomes={**SUCCESS, **{x: "skipped" for x in
                               ("build", "validate", "package", "publish", "maturity", "approval")}})
        self.assertEqual(r["outputs"], [])
        self.assertEqual(r["result"]["artifact_state"], "not_applicable")
        self.assertEqual(r["result"]["authority_state"], "unknown")
        self.assertEqual(r["stages"]["prerelease_publication"], "not_applicable")
        validate_receipt(r, "39286713821", "1")

    def test_missing_lock_fails_validation_even_if_step_green(self):
        self.paths["lock"].unlink()
        r = observed(self.root)
        self.assertEqual(r["stages"]["source_lock_check"], "failed")
        self.assertNotEqual(r["outputs"][0]["state"], "valid")
        self.assertNotEqual(r["result"]["artifact_state"], "healthy")

    def test_early_failure_is_truthful(self):
        r = observed(Path(self.tmp.name) / "empty", job_status="failure",
                     outcomes={**{x: "skipped" for x in SUCCESS}, "source": "failure"})
        self.assertEqual(r["result"]["terminal_state"], "failed")
        self.assertEqual(r["outputs"][0]["state"], "invalid")
        self.assertEqual(r["stages"]["source_acquisition"], "failed")
        validate_receipt(r, "39286713821", "1")

    def test_corrupt_qa_digest_and_hard_failures(self):
        qa = self.paths["consensus"] / "qa.json"
        obj = json.loads(qa.read_text())
        obj["hard_failures"] = ["synthetic"]
        write_json(qa, obj)
        r = observed(self.root)
        self.assertEqual(r["stages"]["consensus_verification"], "failed")
        self.assertNotEqual(r["result"]["artifact_state"], "healthy")

    def test_parent_drift(self):
        m = self.paths["conversion"] / "manifest.json"
        obj = json.loads(m.read_text())
        obj["parent"]["manifest_sha256"] = "e" * 64
        write_json(m, obj)
        r = observed(self.root)
        self.assertEqual(r["stages"]["conversion_qa"], "failed")

    def test_missing_or_stale_transport(self):
        self.paths["publication"].joinpath("verified-transport.json").unlink()
        self.assertEqual(observed(self.root)["stages"]["prerelease_publication"], "failed")
        w = self.paths["publication"] / "verified-transport.json"
        write_json(w, {"schema": "ipc-candidate-transport-verified/v1",
                       "tag": "wrong", "asset_sha256": "a" * 64,
                       "discovery_sha256": "b" * 64, "prerelease": True})
        self.assertNotEqual(observed(self.root)["outputs"][0]["state"], "valid")

    def test_unknown_missing_metadata_not_green(self):
        r = observed(self.root, outcomes={**SUCCESS, "publish": "skipped"})
        self.assertNotEqual(r["outputs"][0]["state"], "valid")
        self.assertNotEqual(r["result"]["artifact_state"], "healthy")

    def test_exact_replay_deterministic_and_attempt_is_distinct(self):
        r = observed(self.root)
        a = build_entry(r, "39286713821", "1")
        b = build_entry(copy.deepcopy(r), "39286713821", "1")
        self.assertEqual(a["insertId"], b["insertId"])
        self.assertEqual(a["labels"]["receipt_sha256"], b["labels"]["receipt_sha256"])
        retried = observed(self.root, attempt="2")
        self.assertNotEqual(a["insertId"], build_entry(retried, "39286713821", "2")["insertId"])

    def test_projection_privacy_and_injection_rejection(self):
        r = observed(self.root)
        s = json.dumps(build_entry(r, "39286713821", "1"))
        for forbidden in ("/home/", "period,factor", "access_token", "source-archive.csv"):
            self.assertNotIn(forbidden, s)
        poisoned = copy.deepcopy(r)
        poisoned["evidence_refs"].append("/home/matias/private.csv")
        with self.assertRaises(ExportError):
            build_entry(poisoned, "39286713821", "1")
        injected = copy.deepcopy(r)
        injected["warnings"].append("password=secret")
        with self.assertRaises(ExportError):
            build_entry(injected, "39286713821", "1")

if __name__ == "__main__":
    unittest.main()
