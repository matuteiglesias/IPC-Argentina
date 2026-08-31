"""Governed release builder for curated official-panel v2."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from .normalize import parse_snapshot
from .sources import _resolve_snapshot_path, check_lock
from .v2 import build_consensus, load_policy, normalize_source_rows

ROOT = Path(__file__).resolve().parents[2]


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_path(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_checksums(root: Path) -> None:
    names = sorted(p.name for p in root.iterdir() if p.is_file() and p.name != "checksums.sha256")
    (root / "checksums.sha256").write_text(
        "".join(f"{digest_path(root / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )


def _files(root: Path, names: list[str]) -> list[dict]:
    return [
        {"path": name, "sha256": digest_path(root / name), "size": (root / name).stat().st_size}
        for name in names
    ]


def _registry(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_rows(lock_path: Path, registry_path: Path, policy: dict) -> tuple[list[dict], dict, list[str]]:
    lock_path = lock_path.resolve()
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    errors = check_lock(lock, lock_path.parent)
    if errors:
        raise ValueError("invalid_source_lock:" + ",".join(errors))
    registry = _registry(registry_path)
    specs = {source["source_id"]: source for source in registry["sources"]}
    allowed = {source_id for member in policy["panel_members"] for source_id in member["source_ids"]}
    rows: list[dict] = []
    warnings: list[str] = []
    for entry in lock.get("entries", []):
        sid = entry["source_id"]
        if sid not in allowed:
            continue
        if entry.get("status") != "pinned":
            warnings.append(f"source_unavailable:{sid}")
            continue
        if sid not in specs:
            raise ValueError(f"source_missing_from_registry:{sid}")
        path, path_error = _resolve_snapshot_path(entry["snapshot_path"], lock_path.parent)
        if path_error or path is None:
            raise ValueError(f"unsafe_snapshot_path:{sid}")
        meta = {
            "source_id": sid,
            "sha256": entry["sha256"],
            "parser_id": entry.get("parser_id", sid + "/v1"),
            "source_base_or_vintage": entry.get("source_base_or_vintage", "adapter-inspected"),
        }
        try:
            parsed = parse_snapshot(path, meta)
        except Exception as exc:
            raise ValueError(f"source_parse_failed:{sid}:{type(exc).__name__}:{exc}") from exc
        rows.extend(parsed)
    if not rows:
        raise ValueError("no_normalized_panel_source_rows")
    return rows, lock, sorted(set(warnings))


def _source_coverage(normalized: list[dict], policy: dict, lock: dict) -> list[dict]:
    by_source: dict[str, list[dict]] = defaultdict(list)
    for row in normalized:
        by_source[row["source_id"]].append(row)
    lock_status = {entry["source_id"]: entry.get("status", "unavailable") for entry in lock.get("entries", [])}
    output = []
    for member in policy["panel_members"]:
        for sid in member["source_ids"]:
            rows = sorted(by_source.get(sid, []), key=lambda r: r["period"])
            statuses = Counter(r["eligibility_status"] for r in rows)
            output.append({
                "panel_member_id": member["member_id"],
                "source_id": sid,
                "lock_status": lock_status.get(sid, "unavailable"),
                "period_start": rows[0]["period"] if rows else "",
                "period_end": rows[-1]["period"] if rows else "",
                "row_count": str(len(rows)),
                "eligible_row_count": str(statuses.get("eligible", 0)),
                "excluded_by_policy_row_count": str(statuses.get("excluded_by_policy", 0)),
                "transition_unapproved_row_count": str(statuses.get("transition_unapproved", 0)),
            })
    return output


def _created_at(lock: dict) -> str:
    stamps = [e.get("retrieved_at_utc") for e in lock.get("entries", []) if e.get("retrieved_at_utc")]
    return max(stamps) if stamps else "source-lock-without-retrieval-time"


def build_all(
    lock_path: Path,
    output_root: Path | None = None,
    policy_path: Path | None = None,
    registry_path: Path | None = None,
) -> dict[str, Path]:
    output_root = (output_root or ROOT / "artifacts/price_v2").resolve()
    policy_path = (policy_path or ROOT / "contracts/panel_v2.json").resolve()
    registry_path = (registry_path or ROOT / "contracts/source_registry.json").resolve()
    lock_path = lock_path.resolve()
    policy = load_policy(policy_path)
    source_rows, lock, warnings = _source_rows(lock_path, registry_path, policy)
    normalized = normalize_source_rows(source_rows, policy)
    consensus = build_consensus(normalized, policy)
    if not consensus:
        raise ValueError("no_v2_consensus_rows")

    lock_hash = digest_path(lock_path)
    policy_hash = digest_path(policy_path)
    normalized_seed = {"lock_sha256": lock_hash, "policy_sha256": policy_hash, "rows": normalized}
    normalized_id = "arg-price-sources-v1-" + digest_bytes(canonical_json(normalized_seed))[:16]
    normalized_root = output_root / "normalized" / normalized_id
    normalized_root.mkdir(parents=True, exist_ok=True)
    normalized_fields = [
        "source_id", "panel_member_id", "period", "source_index", "source_base_or_vintage",
        "value_status", "eligibility_status", "monthly_inflation_pct", "monthly_change_status",
        "source_snapshot_sha256", "parser_id",
    ]
    write_csv(normalized_root / "normalized_sources.csv", normalized, normalized_fields)
    coverage = _source_coverage(normalized, policy, lock)
    write_csv(
        normalized_root / "source_coverage.csv",
        coverage,
        ["panel_member_id", "source_id", "lock_status", "period_start", "period_end", "row_count", "eligible_row_count", "excluded_by_policy_row_count", "transition_unapproved_row_count"],
    )
    source_parent = {
        "schema": lock.get("schema"),
        "registry_id": lock.get("registry_id"),
        "source_lock_sha256": lock_hash,
        "source_lock_locator": str(lock_path),
    }
    (normalized_root / "source_parent.json").write_bytes(canonical_json(source_parent))
    normalized_qa = {
        "schema": "argentina-price-sources-qa/v1",
        "result": "pass_with_warnings" if warnings else "pass",
        "hard_failures": [],
        "warnings": warnings,
        "row_count": len(normalized),
        "source_count": len({r["source_id"] for r in normalized}),
        "panel_member_count_with_rows": len({r["panel_member_id"] for r in normalized}),
    }
    (normalized_root / "qa.json").write_bytes(canonical_json(normalized_qa))
    (normalized_root / "limitations.md").write_text(
        "# Limitations\n\nThis candidate preserves publisher observations and v2 eligibility decisions. "
        "A missing panel source remains missing; no other province is substituted. Source availability and method/base breaks are declared in coverage and QA.\n",
        encoding="utf-8",
    )
    normalized_payload = ["normalized_sources.csv", "source_coverage.csv", "source_parent.json", "qa.json", "limitations.md"]
    normalized_manifest = {
        "schema": "research-artifact-manifest/v1",
        "artifact_type": policy["normalized_artifact_type"],
        "release_id": normalized_id,
        "status": "candidate",
        "created_at": _created_at(lock),
        "source_lock_sha256": lock_hash,
        "panel_policy_sha256": policy_hash,
        "warnings": warnings,
        "files": _files(normalized_root, normalized_payload),
    }
    (normalized_root / "manifest.json").write_bytes(canonical_json(normalized_manifest))
    write_checksums(normalized_root)

    normalized_manifest_hash = digest_path(normalized_root / "manifest.json")
    consensus_seed = {
        "normalized_release_id": normalized_id,
        "normalized_manifest_sha256": normalized_manifest_hash,
        "method_id": policy["method_id"],
        "rows": consensus,
    }
    consensus_id = "arg-price-consensus-v2-" + digest_bytes(canonical_json(consensus_seed))[:16]
    consensus_root = output_root / "consensus" / consensus_id
    consensus_root.mkdir(parents=True, exist_ok=True)
    consensus_fields = [
        "period", "consensus_monthly_inflation_pct", "median_monthly_inflation_pct",
        "min_monthly_inflation_pct", "max_monthly_inflation_pct", "population_std_monthly_inflation_pct",
        "contributing_member_ids", "contributing_source_ids", "contributing_source_count", "coverage_class",
        "approved_mode_eligible", "noncontributing_member_reasons", "consensus_index", "index_status", "method_id",
    ]
    write_csv(consensus_root / "monthly_consensus.csv", consensus, consensus_fields)
    parent = {
        "artifact_type": policy["normalized_artifact_type"],
        "release_id": normalized_id,
        "manifest_sha256": normalized_manifest_hash,
    }
    (consensus_root / "normalized_parent.json").write_bytes(canonical_json(parent))
    method = {
        "method_id": policy["method_id"],
        "monetary_reference_id": policy["monetary_reference_id"],
        "panel_member_ids": [m["member_id"] for m in policy["panel_members"]],
        "aggregation": policy["aggregation"],
        "approved_mode_minimum_contributors": policy["approved_mode_minimum_contributors"],
        "minimum_emitted_contributors": policy["minimum_emitted_contributors"],
        "analytical_base_period": policy["analytical_base_period"],
        "policy_sha256": policy_hash,
    }
    (consensus_root / "method.json").write_bytes(canonical_json(method))
    coverage_counts = Counter(r["coverage_class"] for r in consensus)
    anchored = [r for r in consensus if r["index_status"] == "anchored"]
    consensus_warnings = list(warnings)
    if any(r["approved_mode_eligible"] != "true" for r in consensus):
        consensus_warnings.append("thin_coverage_rows_present")
    if not anchored:
        raise ValueError("consensus_index_not_anchored")
    qa = {
        "schema": "argentina-price-consensus-qa/v2",
        "result": "pass_with_warnings" if consensus_warnings else "pass",
        "hard_failures": [],
        "warnings": sorted(set(consensus_warnings)),
        "monthly_rows": len(consensus),
        "anchored_rows": len(anchored),
        "coverage_counts": dict(sorted(coverage_counts.items())),
        "latest_period": consensus[-1]["period"],
        "latest_coverage_class": consensus[-1]["coverage_class"],
        "latest_contributing_source_count": int(consensus[-1]["contributing_source_count"]),
    }
    (consensus_root / "qa.json").write_bytes(canonical_json(qa))
    (consensus_root / "limitations.md").write_text(
        "# Limitations\n\nThis is an analytical equal-weight consensus, not an official Argentine IPC. "
        "It uses only the fixed panel declared by the method version. Months with two contributors are candidate-only thin coverage; "
        "months with zero or one contributor are not emitted. INDEC observations excluded by the method remain available upstream.\n",
        encoding="utf-8",
    )
    consensus_payload = ["monthly_consensus.csv", "normalized_parent.json", "method.json", "qa.json", "limitations.md"]
    consensus_manifest = {
        "schema": "research-artifact-manifest/v1",
        "artifact_type": policy["consensus_artifact_type"],
        "release_id": consensus_id,
        "status": "candidate",
        "method_id": policy["method_id"],
        "monetary_reference_id": policy["monetary_reference_id"],
        "created_at": _created_at(lock),
        "parent": parent,
        "coverage": {
            "start": consensus[0]["period"],
            "end": consensus[-1]["period"],
            "anchored_start": anchored[0]["period"],
            "anchored_end": anchored[-1]["period"],
        },
        "warnings": sorted(set(consensus_warnings)),
        "files": _files(consensus_root, consensus_payload),
    }
    (consensus_root / "manifest.json").write_bytes(canonical_json(consensus_manifest))
    write_checksums(consensus_root)

    consensus_manifest_hash = digest_path(consensus_root / "manifest.json")
    conversion_rows = []
    base_period = policy["analytical_base_period"]
    for row in anchored:
        index = float(row["consensus_index"])
        conversion_rows.append({
            "period": row["period"],
            "reference_period": base_period,
            "consensus_index": row["consensus_index"],
            "factor_period_to_reference": format(100.0 / index, ".15g"),
            "factor_reference_to_period": format(index / 100.0, ".15g"),
            "coverage_class": row["coverage_class"],
            "approved_mode_eligible": row["approved_mode_eligible"],
        })
    conversion_seed = {
        "consensus_release_id": consensus_id,
        "consensus_manifest_sha256": consensus_manifest_hash,
        "rows": conversion_rows,
    }
    conversion_id = "arg-monetary-conversion-v1-" + digest_bytes(canonical_json(conversion_seed))[:16]
    conversion_root = output_root / "conversion" / conversion_id
    conversion_root.mkdir(parents=True, exist_ok=True)
    write_csv(
        conversion_root / "monthly_conversion_factors.csv",
        conversion_rows,
        ["period", "reference_period", "consensus_index", "factor_period_to_reference", "factor_reference_to_period", "coverage_class", "approved_mode_eligible"],
    )
    consensus_parent = {
        "artifact_type": policy["consensus_artifact_type"],
        "release_id": consensus_id,
        "manifest_sha256": consensus_manifest_hash,
    }
    (conversion_root / "consensus_parent.json").write_bytes(canonical_json(consensus_parent))
    conversion_qa = {
        "schema": "argentina-monetary-conversion-qa/v1",
        "result": "pass_with_warnings" if consensus_warnings else "pass",
        "hard_failures": [],
        "warnings": sorted(set(consensus_warnings)),
        "row_count": len(conversion_rows),
    }
    (conversion_root / "qa.json").write_bytes(canonical_json(conversion_qa))
    (conversion_root / "limitations.md").write_text(
        "# Limitations\n\nConversion factors inherit all consensus coverage and provenance limitations. "
        "Approved-mode consumers must independently enforce their minimum coverage policy.\n",
        encoding="utf-8",
    )
    conversion_payload = ["monthly_conversion_factors.csv", "consensus_parent.json", "qa.json", "limitations.md"]
    conversion_manifest = {
        "schema": "research-artifact-manifest/v1",
        "artifact_type": policy["conversion_artifact_type"],
        "release_id": conversion_id,
        "status": "candidate",
        "method_id": policy["method_id"],
        "monetary_reference_id": policy["monetary_reference_id"],
        "created_at": _created_at(lock),
        "parent": consensus_parent,
        "warnings": sorted(set(consensus_warnings)),
        "files": _files(conversion_root, conversion_payload),
    }
    (conversion_root / "manifest.json").write_bytes(canonical_json(conversion_manifest))
    write_checksums(conversion_root)

    return {"normalized": normalized_root, "consensus": consensus_root, "conversion": conversion_root}
