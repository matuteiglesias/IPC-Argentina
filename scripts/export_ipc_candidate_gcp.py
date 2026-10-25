#!/usr/bin/env python3
"""Strict metadata-only Cloud Logging projection for IPC v2 semantic receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from scripts.emit_ipc_candidate_receipt import CONTRACT, OUTPUT, PRODUCER, REPO, STEPS

PROJECT = "estate-observability-510700"
LOG = "estate-producer-run"
ENDPOINT = "https://logging.googleapis.com/v2/entries:write"
SCOPES = ["https://www.googleapis.com/auth/logging.write"]
RUN_STATES = {"healthy", "degraded", "failed", "unknown", "not_applicable"}
ARTIFACT_STATES = RUN_STATES | {"stale"}
STAGE_STATES = {"success", "failed", "skipped", "unknown", "not_applicable"}
REF = re.compile(r"(?:github-actions:matuteiglesias/IPC-Argentina:[0-9]+:attempt:[1-9][0-9]*|"
                 r"ipc:(?:source-lock:sha256:[a-f0-9]{64}|(?:normalized|consensus|conversion):[a-z0-9-]+:sha256:[a-f0-9]{64}|"
                 r"qa:latest:20[0-9]{2}-[0-9]{2}-[0-9]{2}:contributors:[0-5]:coverage:(?:strong_coverage|acceptable_coverage|thin_coverage|no_consensus))|"
                 r"github-release:matuteiglesias/IPC-Argentina:candidate-[a-z0-9-]+:sha256:[a-f0-9]{64})\Z")
WARNING = re.compile(r"(?:qa_(?:normalized|consensus|conversion)_pass_with_warnings|"
                     r"qa_source_unavailable_cordoba_ipc|qa_thin_coverage_rows_present|"
                     r"scheduled_maturity_check_failed_advisory|explicit_approval_gate_failed|"
                     r"start_boundary_unavailable|candidate_publication_unverified|source_lock_unverified)\Z")

class ExportError(ValueError):
    pass

def require(ok: bool, message: str) -> None:
    if not ok:
        raise ExportError(message)

def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def validate_receipt(r: dict, run_id: str, attempt: str) -> None:
    require(isinstance(r, dict), "receipt_not_object")
    require(set(r) == {"contract", "run_id", "producer_id", "scheduler_run_id", "trigger",
                        "started_at", "finished_at", "inputs", "stages", "outputs", "result",
                        "warnings", "evidence_refs"}, "unknown_receipt_keys")
    require(re.fullmatch(r"[0-9]+", run_id) is not None and
            re.fullmatch(r"[1-9][0-9]*", attempt) is not None, "bad_run_identity")
    require(r["contract"] == CONTRACT and r["producer_id"] == PRODUCER and
            r["scheduler_run_id"] == run_id and
            r["run_id"] == f"github-actions:{REPO}:{run_id}:{attempt}", "bad_producer_identity")
    require(r["trigger"] in {"schedule", "manual"}, "invalid_trigger")
    require(all(isinstance(r[k], str) and len(r[k]) <= 40 for k in ("started_at", "finished_at")), "bad_times")
    try:
        start = datetime.fromisoformat(r["started_at"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(r["finished_at"].replace("Z", "+00:00"))
        require(start.tzinfo is not None and end.tzinfo is not None and start <= end, "invalid_time_range")
    except (TypeError, ValueError) as exc:
        raise ExportError("invalid_timestamp") from exc
    require(isinstance(r["inputs"], list) and len(r["inputs"]) == 2, "invalid_inputs")
    inp = [x.get("ref") if isinstance(x, dict) and set(x) == {"ref"} else None for x in r["inputs"]]
    require(inp[0] in {"ipc:mode:full-v2", "ipc:mode:source-only"} and
            inp[1] in {"ipc:require-approved-latest:true", "ipc:require-approved-latest:false"},
            "unsafe_input")
    require(isinstance(r["stages"], dict) and set(r["stages"]) == set(STEPS) and
            all(s in STAGE_STATES for s in r["stages"].values()), "bad_stages")
    require(isinstance(r["outputs"], list) and len(r["outputs"]) in (0, 1), "bad_output_count")
    if inp[0] == "ipc:mode:source-only":
        require(not r["outputs"], "source_only_must_not_claim_candidate")
    else:
        require(len(r["outputs"]) == 1, "missing_declared_candidate")
    for item in r["outputs"]:
        require(isinstance(item, dict) and set(item) == {"type", "state", "durability", "ref"} and
                item["type"] == OUTPUT and item["durability"] == "candidate_release" and
                item["state"] in {"valid", "partial", "invalid", "missing", "unknown"} and
                (item["ref"] is None or (isinstance(item["ref"], str) and REF.fullmatch(item["ref"]))),
                "unsafe_output")
    require(isinstance(r["result"], dict) and
            set(r["result"]) == {"scheduler_state", "execution_state", "artifact_state",
                                  "terminal_state", "authority_state"}, "bad_result_keys")
    require(all(r["result"][k] in RUN_STATES for k in
                ("scheduler_state", "execution_state", "terminal_state")) and
            r["result"]["artifact_state"] in ARTIFACT_STATES and
            r["result"]["authority_state"] in {"candidate", "unknown"}, "bad_result_state")
    if r["result"]["artifact_state"] == "healthy":
        require(len(r["outputs"]) == 1 and r["outputs"][0]["state"] == "valid" and
                r["result"]["authority_state"] == "candidate" and
                all(r["stages"][k] == "success" for k in
                    ("source_acquisition", "source_lock_check", "normalized_build",
                     "consensus_verification", "conversion_qa", "candidate_packaging",
                     "prerelease_publication")), "unproven_health")
    require(isinstance(r["warnings"], list) and len(r["warnings"]) <= 18 and
            all(isinstance(w, str) and WARNING.fullmatch(w) for w in r["warnings"]),
            "unsafe_warning")
    require(isinstance(r["evidence_refs"], list) and
            1 <= len(r["evidence_refs"]) <= 8 and
            r["evidence_refs"][0] == f"github-actions:{REPO}:{run_id}:attempt:{attempt}" and
            all(isinstance(x, str) and REF.fullmatch(x) for x in r["evidence_refs"]),
            "unsafe_reference")
    # No arbitrary URLs, OS paths, embedded source text or unknown JSON fields
    require(len(canonical(r)) < 9500, "oversized_payload")
    if r["outputs"]:
        published = r["outputs"][0]["state"] == "valid"
        require(published == (r["result"]["artifact_state"] == "healthy"), "state_mismatch")
        if published:
            require(r["outputs"][0]["ref"] in r["evidence_refs"], "unbound_release_ref")

def build_entry(r: dict, run_id: str, attempt: str) -> dict:
    validate_receipt(r, run_id, attempt)
    sha = hashlib.sha256(canonical(r).encode("utf-8")).hexdigest()
    identity = {"producer_id": PRODUCER, "run_id": r["run_id"], "receipt_sha256": sha}
    insert_id = hashlib.sha256(canonical(identity).encode("utf-8")).hexdigest()
    states = {r["result"]["execution_state"], r["result"]["artifact_state"],
              r["result"]["terminal_state"]}
    severity = "ERROR" if "failed" in states else ("WARNING" if states & {"unknown", "degraded"} else "INFO")
    return {
        "logName": f"projects/{PROJECT}/logs/{LOG}",
        "resource": {"type": "global", "labels": {"project_id": PROJECT}},
        "timestamp": r["finished_at"],
        "severity": severity,
        "insertId": insert_id,
        "labels": {"producer_id": PRODUCER, "source_contract": CONTRACT, "receipt_sha256": sha},
        "jsonPayload": {
            "contract": CONTRACT,
            "receipt": r,
            "receipt_sha256": sha,
            "logical_receipt_id": f"{PRODUCER}:{r['run_id']}",
            "producer": {"producer_id": PRODUCER, "owner": REPO, "scheduler_kind": "github_actions",
                         "observation_mode": "semantic_receipt",
                         "authority_state": r["result"]["authority_state"]},
        },
    }

def write(session, entry: dict, dry_run: bool) -> None:
    payload = {"logName": f"projects/{PROJECT}/logs/{LOG}", "resource": entry["resource"],
               "entries": [entry], "partialSuccess": False}
    response = session.post(ENDPOINT, params={"dryRun": "true"} if dry_run else None,
                            json=payload, timeout=30)
    if not response.ok:
        raise ExportError(f"logging_write_http_{response.status_code}")

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--receipt", required=True, type=Path)
    p.add_argument("--scheduler-run-id", required=True)
    p.add_argument("--run-attempt", required=True)
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--validate-only", action="store_true")
    grp.add_argument("--write", action="store_true")
    args = p.parse_args()
    try:
        r = json.loads(args.receipt.read_text(encoding="utf-8"))
        entry = build_entry(r, args.scheduler_run_id, args.run_attempt)
        if args.write:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession
            creds, _ = google.auth.default(scopes=SCOPES)
            session = AuthorizedSession(creds)
            write(session, entry, True)
            write(session, entry, False)
        print(json.dumps({"producer_id": PRODUCER, "insert_id": entry["insertId"],
                          "receipt_sha256": entry["labels"]["receipt_sha256"],
                          "mode": "exported" if args.write else "validated"}, sort_keys=True))
        return 0
    except (ExportError, OSError, ValueError, KeyError, TypeError) as exc:
        print("ipc GCP receipt export failed: " + type(exc).__name__, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
