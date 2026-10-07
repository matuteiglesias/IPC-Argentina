"""Explicit scientific-promotion transport for curated official-panel v2.

This module never decides whether v2 should be approved. It only materializes an
immutable approved child release after an owner-supplied adjudication record binds
that decision to the exact candidate consensus, conversion release, and v1-v2 audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath

from .v2 import load_policy
from .v2_validate import validate_release

ROOT = Path(__file__).resolve().parents[2]
DECISION_SCHEMA = "argentina-price-v2-promotion-decision/v1"
AUDIT_SCHEMA = "argentina-price-v1-v2-scientific-audit/v1"


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _load_json(path: Path, reason: str) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(reason) from exc
    if not isinstance(value, dict):
        raise ValueError(reason)
    return value


def _safe_payload(root: Path, name: str) -> Path:
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ValueError(f"unsafe_payload_path:{name}")
    target = (root / name).resolve()
    base = root.resolve()
    if target == base or base not in target.parents or not target.is_file():
        raise ValueError(f"missing_or_unsafe_payload:{name}")
    return target


def _payload_names(manifest: dict) -> list[str]:
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("candidate_manifest_files_invalid")
    names: list[str] = []
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("candidate_manifest_files_invalid")
        names.append(item["path"])
    if len(names) != len(set(names)):
        raise ValueError("candidate_manifest_duplicate_file")
    return names


def _file_identities(root: Path, names: list[str]) -> list[dict]:
    return [
        {"path": name, "sha256": sha256_path(root / name), "size": (root / name).stat().st_size}
        for name in names
    ]


def _write_checksums(root: Path) -> None:
    names = sorted(
        p.name for p in root.iterdir()
        if p.is_file() and p.name != "checksums.sha256"
    )
    (root / "checksums.sha256").write_text(
        "".join(f"{sha256_path(root / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )


def _copy_payload(
    candidate: Path,
    destination: Path,
    manifest: dict,
    *,
    exclude: set[str] | None = None,
) -> list[str]:
    exclude = exclude or set()
    copied: list[str] = []
    for name in _payload_names(manifest):
        if name in exclude:
            continue
        source = _safe_payload(candidate, name)
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(name)
    return copied


def _candidate_manifest(root: Path, artifact_type: str) -> tuple[dict, str]:
    root = Path(root).resolve()
    manifest_path = root / "manifest.json"
    manifest = _load_json(manifest_path, "candidate_manifest_invalid")
    if manifest.get("schema") != "research-artifact-manifest/v1":
        raise ValueError("candidate_manifest_schema_mismatch")
    if manifest.get("artifact_type") != artifact_type:
        raise ValueError("candidate_artifact_type_mismatch")
    if manifest.get("status") != "candidate":
        raise ValueError("promotion_requires_candidate_status")
    if root.name != manifest.get("release_id"):
        raise ValueError("candidate_release_id_directory_mismatch")
    return manifest, sha256_path(manifest_path)


def _verify_decision(
    decision_path: Path,
    audit_summary_path: Path,
    consensus_manifest: dict,
    consensus_manifest_sha: str,
    conversion_manifest: dict,
    conversion_manifest_sha: str,
) -> tuple[dict, str, str]:
    decision_path = Path(decision_path).resolve()
    audit_summary_path = Path(audit_summary_path).resolve()
    decision = _load_json(decision_path, "promotion_decision_invalid")
    if decision.get("schema") != DECISION_SCHEMA:
        raise ValueError("promotion_decision_schema_mismatch")
    if decision.get("decision") != "approved":
        raise ValueError("promotion_decision_is_not_approved")
    for key in ("decision_id", "approved_by", "decided_at"):
        if not isinstance(decision.get(key), str) or not decision[key].strip():
            raise ValueError(f"promotion_decision_missing_{key}")

    candidates = decision.get("candidates")
    if not isinstance(candidates, dict):
        raise ValueError("promotion_decision_candidates_missing")
    expected = {
        "consensus": (consensus_manifest.get("release_id"), consensus_manifest_sha),
        "conversion": (conversion_manifest.get("release_id"), conversion_manifest_sha),
    }
    for key, (release_id, manifest_sha) in expected.items():
        ref = candidates.get(key)
        if not isinstance(ref, dict):
            raise ValueError(f"promotion_decision_{key}_missing")
        if ref.get("release_id") != release_id or ref.get("manifest_sha256") != manifest_sha:
            raise ValueError(f"promotion_decision_{key}_identity_mismatch")

    audit = _load_json(audit_summary_path, "promotion_audit_summary_invalid")
    if audit.get("schema") != AUDIT_SCHEMA or audit.get("status") != "diagnostic_only_no_promotion":
        raise ValueError("promotion_audit_summary_contract_mismatch")
    audit_sha = sha256_path(audit_summary_path)
    audit_ref = decision.get("audit")
    if not isinstance(audit_ref, dict) or audit_ref.get("summary_sha256") != audit_sha:
        raise ValueError("promotion_decision_audit_identity_mismatch")
    return decision, sha256_path(decision_path), audit_sha


def promote(
    consensus_candidate: Path,
    conversion_candidate: Path,
    decision_path: Path,
    audit_summary_path: Path,
    output_root: Path,
    *,
    policy_path: Path | None = None,
) -> dict[str, Path]:
    policy_path = Path(policy_path or ROOT / "contracts/panel_v2.json").resolve()
    policy = load_policy(policy_path)
    consensus_candidate = Path(consensus_candidate).resolve()
    conversion_candidate = Path(conversion_candidate).resolve()

    consensus_manifest, consensus_manifest_sha = _candidate_manifest(
        consensus_candidate, policy["consensus_artifact_type"]
    )
    conversion_manifest, conversion_manifest_sha = _candidate_manifest(
        conversion_candidate, policy["conversion_artifact_type"]
    )

    consensus_errors = validate_release(
        consensus_candidate, policy, require_approved_latest=True
    )
    if consensus_errors:
        raise ValueError("consensus_candidate_invalid:" + ",".join(consensus_errors))
    conversion_errors = validate_release(conversion_candidate, policy)
    if conversion_errors:
        raise ValueError("conversion_candidate_invalid:" + ",".join(conversion_errors))

    parent = conversion_manifest.get("parent")
    if not isinstance(parent, dict):
        raise ValueError("conversion_candidate_parent_missing")
    if (
        parent.get("release_id") != consensus_manifest.get("release_id")
        or parent.get("manifest_sha256") != consensus_manifest_sha
    ):
        raise ValueError("conversion_candidate_parent_mismatch")

    decision, decision_sha, audit_sha = _verify_decision(
        decision_path,
        audit_summary_path,
        consensus_manifest,
        consensus_manifest_sha,
        conversion_manifest,
        conversion_manifest_sha,
    )

    output_root = Path(output_root).resolve()
    consensus_id = "arg-price-consensus-v2-approved-" + sha256_bytes(
        canonical_json(
            {
                "candidate_release_id": consensus_manifest["release_id"],
                "candidate_manifest_sha256": consensus_manifest_sha,
                "decision_sha256": decision_sha,
                "audit_summary_sha256": audit_sha,
            }
        )
    )[:16]
    consensus_root = output_root / "consensus" / consensus_id
    if consensus_root.exists():
        raise ValueError(f"approved_release_exists:{consensus_root}")
    consensus_root.mkdir(parents=True)

    consensus_names = _copy_payload(consensus_candidate, consensus_root, consensus_manifest)
    consensus_promotion = {
        "schema": "argentina-price-v2-promotion-record/v1",
        "decision_id": decision["decision_id"],
        "approved_by": decision["approved_by"],
        "decided_at": decision["decided_at"],
        "candidate": {
            "release_id": consensus_manifest["release_id"],
            "manifest_sha256": consensus_manifest_sha,
        },
        "adjudication_sha256": decision_sha,
        "audit_summary_sha256": audit_sha,
    }
    (consensus_root / "promotion.json").write_bytes(canonical_json(consensus_promotion))
    consensus_names.append("promotion.json")
    approved_consensus_manifest = dict(consensus_manifest)
    approved_consensus_manifest.update(
        {
            "release_id": consensus_id,
            "status": "approved",
            "approved_at": decision["decided_at"],
            "promotion": consensus_promotion,
            "files": _file_identities(consensus_root, consensus_names),
        }
    )
    (consensus_root / "manifest.json").write_bytes(canonical_json(approved_consensus_manifest))
    _write_checksums(consensus_root)
    post_errors = validate_release(consensus_root, policy, require_approved_latest=True)
    if post_errors:
        raise ValueError("approved_consensus_invalid:" + ",".join(post_errors))

    approved_consensus_sha = sha256_path(consensus_root / "manifest.json")
    conversion_id = "arg-monetary-conversion-v1-approved-" + sha256_bytes(
        canonical_json(
            {
                "candidate_release_id": conversion_manifest["release_id"],
                "candidate_manifest_sha256": conversion_manifest_sha,
                "approved_consensus_release_id": consensus_id,
                "approved_consensus_manifest_sha256": approved_consensus_sha,
                "decision_sha256": decision_sha,
            }
        )
    )[:16]
    conversion_root = output_root / "conversion" / conversion_id
    if conversion_root.exists():
        raise ValueError(f"approved_release_exists:{conversion_root}")
    conversion_root.mkdir(parents=True)

    conversion_names = _copy_payload(
        conversion_candidate,
        conversion_root,
        conversion_manifest,
        exclude={"consensus_parent.json"},
    )
    approved_parent = {
        "artifact_type": policy["consensus_artifact_type"],
        "release_id": consensus_id,
        "manifest_sha256": approved_consensus_sha,
    }
    (conversion_root / "consensus_parent.json").write_bytes(canonical_json(approved_parent))
    conversion_names.append("consensus_parent.json")
    conversion_promotion = {
        "schema": "argentina-price-v2-promotion-record/v1",
        "decision_id": decision["decision_id"],
        "approved_by": decision["approved_by"],
        "decided_at": decision["decided_at"],
        "candidate": {
            "release_id": conversion_manifest["release_id"],
            "manifest_sha256": conversion_manifest_sha,
        },
        "approved_consensus_parent": approved_parent,
        "adjudication_sha256": decision_sha,
        "audit_summary_sha256": audit_sha,
    }
    (conversion_root / "promotion.json").write_bytes(canonical_json(conversion_promotion))
    conversion_names.append("promotion.json")
    approved_conversion_manifest = dict(conversion_manifest)
    approved_conversion_manifest.update(
        {
            "release_id": conversion_id,
            "status": "approved",
            "approved_at": decision["decided_at"],
            "parent": approved_parent,
            "promotion": conversion_promotion,
            "files": _file_identities(conversion_root, conversion_names),
        }
    )
    (conversion_root / "manifest.json").write_bytes(canonical_json(approved_conversion_manifest))
    _write_checksums(conversion_root)
    post_errors = validate_release(conversion_root, policy)
    if post_errors:
        raise ValueError("approved_conversion_invalid:" + ",".join(post_errors))

    return {"consensus": consensus_root, "conversion": conversion_root}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize immutable approved v2 children from an explicit owner adjudication."
    )
    parser.add_argument("--consensus-candidate", type=Path, required=True)
    parser.add_argument("--conversion-candidate", type=Path, required=True)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--audit-summary", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/price_v2/approved"))
    parser.add_argument("--policy", type=Path, default=ROOT / "contracts/panel_v2.json")
    args = parser.parse_args()
    result = promote(
        args.consensus_candidate,
        args.conversion_candidate,
        args.decision,
        args.audit_summary,
        args.output_root,
        policy_path=args.policy,
    )
    print(json.dumps({k: str(v) for k, v in result.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
