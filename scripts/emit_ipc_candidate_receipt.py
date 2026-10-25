#!/usr/bin/env python3
"""Source-owned, metadata-only semantic IPC v2 candidate receipt.

Do not equate a green Actions job, an uploaded artifact, or maturity with
immutable candidate publication. Source bytes are read only to verify hashes;
the emitted document contains only bounded metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

CONTRACT = "evidence:producer-run-receipt@1"
PRODUCER = "producer.github.ipc-price-candidate"
REPO = "matuteiglesias/IPC-Argentina"
OUTPUT = "publicdata.argentina-ipc-candidate@2"
METHOD = "research.argentina-price-consensus/curated-official-panel-v2"
PANEL = ["indec", "caba", "cordoba", "san_luis", "neuquen"]
STEPS = ("source_acquisition", "source_lock_check", "normalized_build",
         "consensus_verification", "conversion_qa", "candidate_packaging",
         "prerelease_publication", "scheduled_maturity", "manual_approval_gate")
ALLOWED_QA_WARNINGS = {"source_unavailable:cordoba_ipc", "thin_coverage_rows_present"}
HEX = re.compile(r"[a-f0-9]{64}\Z")
ID = re.compile(r"[a-z0-9][a-z0-9-]{0,119}\Z")
COVERAGE = {"strong_coverage", "acceptable_coverage", "thin_coverage", "no_consensus"}

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def load(path: Path) -> dict | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except (OSError, ValueError, UnicodeError):
        return None

def iso(s: str) -> str | None:
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.isoformat().replace("+00:00", "Z") if dt.tzinfo else None
    except (TypeError, ValueError, AttributeError):
        return None

def valid_id(s: object) -> bool:
    return isinstance(s, str) and ID.fullmatch(s) is not None

def valid_hash(s: object) -> bool:
    return isinstance(s, str) and HEX.fullmatch(s) is not None

def source_lock(root: Path) -> str | None:
    path = root / "build/price_sources/source_lock.json"
    obj = load(path)
    if not obj or obj.get("schema") != "price-source-lock/v1":
        return None
    entries = obj.get("entries")
    if not isinstance(entries, list) or len(entries) < 5:
        return None
    ids = set()
    pinned = 0
    for e in entries:
        if not isinstance(e, dict) or not isinstance(e.get("source_id"), str) or not re.fullmatch(r"[a-z0-9_]+", e["source_id"]) or e["source_id"] in ids:
            return None
        ids.add(e["source_id"])
        if e.get("status") == "pinned":
            if not valid_hash(e.get("sha256")) or not isinstance(e.get("byte_size"), int) or e["byte_size"] <= 0:
                return None
            pinned += 1
        elif e.get("status") != "unavailable":
            return None
    return digest(path) if pinned >= 1 else None

def release(root: Path, kind: str, artifact_type: str) -> tuple[dict, Path, dict] | None:
    directory = root / "artifacts/price_v2" / kind
    dirs = sorted(p for p in directory.glob("*") if p.is_dir())
    if len(dirs) != 1:
        return None  # prevent arbitrary selection when candidates are ambiguous
    path = dirs[0]
    m = load(path / "manifest.json")
    qa = load(path / "qa.json")
    if not m or not qa:
        return None
    if (m.get("schema") != "research-artifact-manifest/v1" or
            m.get("status") != "candidate" or
            m.get("artifact_type") != artifact_type or
            not valid_id(m.get("release_id")) or path.name != m["release_id"] or
            qa.get("result") not in {"pass", "pass_with_warnings"} or
            qa.get("hard_failures") != []):
        return None
    files = m.get("files")
    if not isinstance(files, list) or not files:
        return None
    seen = set()
    for item in files:
        if not isinstance(item, dict):
            return None
        name = item.get("path")
        if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9_.-]+", name) or name in seen:
            return None
        seen.add(name)
        f = path / name
        if not f.is_file() or f.stat().st_size != item.get("size") or digest(f) != item.get("sha256"):
            return None
    if "qa.json" not in seen:
        return None
    return m, path, qa

def linked(child: dict, child_dir: Path, parent: dict, parent_dir: Path, parent_file: str) -> bool:
    ref = child.get("parent")
    return bool(isinstance(ref, dict) and ref.get("release_id") == parent.get("release_id")
                and ref.get("artifact_type") == parent.get("artifact_type")
                and ref.get("manifest_sha256") == digest(parent_dir / "manifest.json")
                and load(child_dir / parent_file) == ref)

def evidence(root: Path) -> tuple[dict, list[str], list[str]]:
    checks: dict[str, bool] = {}
    refs: list[str] = []
    warnings: list[str] = []
    lock_hash = source_lock(root)
    checks["source_lock"] = bool(lock_hash)
    if lock_hash:
        refs.append("ipc:source-lock:sha256:" + lock_hash)

    types = {"normalized": "publicdata.argentina-price-sources/v1",
             "consensus": "research.argentina-price-consensus/v2",
             "conversion": "research.argentina-monetary-conversion/v1"}
    found = {kind: release(root, kind, atype) for kind, atype in types.items()}
    for kind, data in found.items():
        checks[kind] = data is not None
        if data is not None:
            m, path, qa = data
            refs.append(f"ipc:{kind}:{m['release_id']}:sha256:{digest(path / 'manifest.json')}")
            if qa.get("result") == "pass_with_warnings":
                warnings.append(f"qa_{kind}_pass_with_warnings")
            for code in (qa.get("warnings") if isinstance(qa.get("warnings"), list) else []):
                if isinstance(code, str) and code in ALLOWED_QA_WARNINGS:
                    warnings.append("qa_" + code.replace(":", "_"))
    if all(found.values()):
        n, np, nq = found["normalized"]
        c, cp, cq = found["consensus"]
        v, vp, vq = found["conversion"]
        method = load(cp / "method.json")
        checks["lineage"] = bool(
            n.get("source_lock_sha256") == lock_hash and
            load(np / "source_parent.json") == {
                "schema": "price-source-lock/v1",
                "registry_id": "registry:research.argentina-price-sources@2",
                "source_lock_sha256": lock_hash,
                "source_lock_transport": "external_content_addressed_parent",
            } and
            linked(c, cp, n, np, "normalized_parent.json") and
            linked(v, vp, c, cp, "consensus_parent.json") and
            n.get("status") == c.get("status") == v.get("status") == "candidate" and
            c.get("method_id") == v.get("method_id") == METHOD and
            isinstance(method, dict) and method.get("panel_member_ids") == PANEL and
            isinstance(method.get("aggregation"), dict) and
            method["aggregation"].get("dynamic_source_substitution") is False)
        if (valid_id(cq.get("latest_period", "")) or
            re.fullmatch(r"20\d\d-\d\d-\d\d", str(cq.get("latest_period", "")))):
            period = cq.get("latest_period")
            count = cq.get("latest_contributing_source_count")
            coverage = cq.get("latest_coverage_class")
            if isinstance(count, int) and 0 <= count <= 5 and coverage in COVERAGE:
                refs.append(f"ipc:qa:latest:{period}:contributors:{count}:coverage:{coverage}")
    else:
        checks["lineage"] = False

    published = False
    if found["conversion"] and checks.get("lineage"):
        v, vp, _ = found["conversion"]
        d = load(root / "build/publication/discovery.json")
        w = load(root / "build/publication/verified-transport.json")
        g = d.get("github_release", {}) if d else {}
        g = g if isinstance(g, dict) else {}
        asset_name = f"{v['release_id']}.zip"
        asset = root / "build/publication" / asset_name
        published = bool(
            d and w and
            d.get("schema") == "ecosystem-release-discovery/v1" and
            d.get("producer") == REPO and
            d.get("status") == "candidate" and
            d.get("artifact_type") == v["artifact_type"] and
            d.get("release_id") == v["release_id"] and
            d.get("parent") == v.get("parent") and
            d.get("method_id") == METHOD and
            g.get("tag") == "candidate-" + v["release_id"] and
            g.get("asset_name") == asset_name and
            valid_hash(g.get("asset_sha256")) and
            g.get("manifest_sha256") == digest(vp / "manifest.json") and
            asset.is_file() and digest(asset) == g.get("asset_sha256") and
            w == {"schema": "ipc-candidate-transport-verified/v1",
                  "tag": g.get("tag"), "asset_sha256": g.get("asset_sha256"),
                  "discovery_sha256": digest(root / "build/publication/discovery.json"),
                  "prerelease": True})
        if published:
            refs.append(f"github-release:{REPO}:{g['tag']}:sha256:{g['asset_sha256']}")
    checks["publication"] = published
    return checks, refs, sorted(set(warnings))

def receipt(root: Path, *, run_id: str, attempt: str, event: str, mode: str,
            require_approved: bool, job_status: str, started_at: str,
            outcomes: dict[str, str], finished_at: str | None = None) -> dict:
    if not re.fullmatch(r"[0-9]+", run_id) or not re.fullmatch(r"[1-9][0-9]*", attempt):
        raise ValueError("invalid github run/attempt")
    if event not in {"schedule", "workflow_dispatch"} or mode not in {"full-v2", "source-only"}:
        raise ValueError("invalid event or mode")
    if event == "schedule":
        mode = "full-v2"  # source-only is not a valid scheduled execution
    end = iso(finished_at) if finished_at else datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    start = iso(started_at)
    if not end:
        raise ValueError("invalid finish")
    missing_start = start is None
    start = start or end
    if start > end:
        raise ValueError("inverted time bounds")
    full = mode == "full-v2"
    checks, refs, qa_warnings = evidence(root)
    stage = {}
    mapping = {"source_acquisition": "source", "source_lock_check": "lock",
               "normalized_build": "build", "consensus_verification": "validate",
               "conversion_qa": "validate", "candidate_packaging": "package",
               "prerelease_publication": "publish",
               "scheduled_maturity": "maturity", "manual_approval_gate": "approval"}
    for name in STEPS:
        raw = outcomes.get(mapping[name], "unknown")
        stage[name] = raw if raw in {"success", "failure", "skipped"} else "unknown"
        if stage[name] == "failure":
            stage[name] = "failed"
        if (not full and name in {"normalized_build", "consensus_verification", "conversion_qa",
                                  "candidate_packaging", "prerelease_publication"}):
            stage[name] = "not_applicable" if raw == "skipped" else stage[name]
    for name, good in (("source_lock_check", checks["source_lock"]),
                       ("normalized_build", checks["normalized"]),
                       ("consensus_verification", checks["consensus"] and checks["lineage"]),
                       ("conversion_qa", checks["conversion"] and checks["lineage"]),
                       ("prerelease_publication", checks["publication"])):
        if stage[name] == "success" and not good:
            stage[name] = "failed"   # a green step cannot override contradicted evidence
    if stage["candidate_packaging"] == "success" and not (
            checks["conversion"] and (root / "build/publication/discovery.json").is_file()):
        stage["candidate_packaging"] = "failed"
    if event != "schedule":
        stage["scheduled_maturity"] = "not_applicable"
    if event != "workflow_dispatch" or not require_approved:
        stage["manual_approval_gate"] = "not_applicable"
    required = ("source_acquisition", "source_lock_check") + (
        ("normalized_build", "consensus_verification", "conversion_qa",
         "candidate_packaging", "prerelease_publication") if full else ())
    bad = any(stage[x] == "failed" for x in required)
    complete = all(stage[x] == "success" for x in required)
    published = full and complete and checks["publication"]
    maturity_failed = stage["scheduled_maturity"] == "failed"
    explicit_failed = stage["manual_approval_gate"] == "failed"
    other_failed = job_status == "failure" or bad or explicit_failed
    warnings = qa_warnings[:]
    if maturity_failed:
        warnings.append("scheduled_maturity_check_failed_advisory")
    if explicit_failed:
        warnings.append("explicit_approval_gate_failed")
    if missing_start:
        warnings.append("start_boundary_unavailable")
    if not published and full:
        warnings.append("candidate_publication_unverified")
    if not checks["source_lock"]:
        warnings.append("source_lock_unverified")
    return {
        "contract": CONTRACT,
        "run_id": f"github-actions:{REPO}:{run_id}:{attempt}",
        "producer_id": PRODUCER,
        "scheduler_run_id": run_id,
        "trigger": "schedule" if event == "schedule" else "manual",
        "started_at": start,
        "finished_at": end,
        "inputs": [{"ref": "ipc:mode:" + mode},
                   {"ref": "ipc:require-approved-latest:" + str(require_approved).lower()}],
        "stages": stage,
        "outputs": ([{"type": OUTPUT,
                     "state": "valid" if published else ("invalid" if bad else "partial" if any(checks.values()) else "missing"),
                     "durability": "candidate_release",
                     "ref": next((x for x in refs if x.startswith("github-release:")), None)}]
                    if full else []),
        "result": {
            "scheduler_state": "healthy" if not missing_start else "unknown",
            "execution_state": ("failed" if other_failed else
                                "degraded" if maturity_failed else
                                "healthy" if complete else "unknown"),
            "artifact_state": ("not_applicable" if not full else
                               "healthy" if published else "failed" if bad else
                               "degraded" if any(checks.values()) else "unknown"),
            "terminal_state": "failed" if job_status == "failure" else "healthy" if job_status == "success" else "unknown",
            "authority_state": "candidate" if published else "unknown",
        },
        "warnings": sorted(set(warnings)),
        "evidence_refs": [f"github-actions:{REPO}:{run_id}:attempt:{attempt}"] + refs,
    }

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--started-at", default="")
    p.add_argument("--finished-at", default="")
    args = p.parse_args()
    try:
        env = os.environ
        outcomes = {k: env.get("STEP_" + k.upper(), "unknown") for k in
                    ("source", "lock", "build", "validate", "package", "publish", "maturity", "approval")}
        r = receipt(args.root, run_id=env["GITHUB_RUN_ID"], attempt=env["GITHUB_RUN_ATTEMPT"],
                    event=env["GITHUB_EVENT_NAME"], mode=env.get("PRODUCER_MODE") or "full-v2",
                    require_approved=env.get("PRODUCER_REQUIRE_APPROVED") == "true",
                    job_status=env.get("PRODUCER_JOB_STATUS", "unknown"),
                    started_at=args.started_at, outcomes=outcomes,
                    finished_at=args.finished_at or None)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(r, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"run_id": r["run_id"], "artifact_state": r["result"]["artifact_state"],
                          "authority_state": r["result"]["authority_state"]}, sort_keys=True))
        return 0
    except (KeyError, ValueError, OSError, TypeError) as exc:
        print(f"ipc receipt emission failed: {type(exc).__name__}", file=__import__("sys").stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
