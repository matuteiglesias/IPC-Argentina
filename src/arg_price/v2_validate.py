"""Standard-library consumer preflight for v2 source/consensus/conversion releases."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

from .v2 import load_policy

ROOT = Path(__file__).resolve().parents[2]


def _safe_file(base: Path, name: str) -> Path | None:
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts or name in {"", "."}:
        return None
    path = (base / name).resolve()
    if path == base or base not in path.parents:
        return None
    return path


def validate_release(base: Path, policy: dict, require_approved_latest: bool = False) -> list[str]:
    base = Path(base).resolve(); errors = []
    try:
        manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return ["corrupted_declared_file:" + str(exc)]
    if manifest.get("schema") != "research-artifact-manifest/v1":
        errors.append("manifest_schema_mismatch")
    artifact_type = manifest.get("artifact_type")
    allowed = {
        policy["normalized_artifact_type"],
        policy["consensus_artifact_type"],
        policy["conversion_artifact_type"],
    }
    if artifact_type not in allowed:
        errors.append("artifact_type_mismatch")
    for item in manifest.get("files", []):
        name = item.get("path", "")
        path = _safe_file(base, name)
        if path is None or not path.is_file():
            errors.append("unsafe_or_missing_path:" + name); continue
        raw = path.read_bytes()
        if len(raw) != item.get("size") or hashlib.sha256(raw).hexdigest() != item.get("sha256"):
            errors.append("checksum_mismatch:" + name)

    if artifact_type == policy["normalized_artifact_type"]:
        table = base / "normalized_sources.csv"
        if not table.is_file(): errors.append("normalized_sources_missing")
        else:
            rows = list(csv.DictReader(table.open(encoding="utf-8")))
            allowed_sources = {sid for member in policy["panel_members"] for sid in member["source_ids"]}
            if not rows: errors.append("normalized_sources_empty")
            if any(r.get("source_id") not in allowed_sources for r in rows): errors.append("unbounded_source_in_normalized_release")
            if any(r.get("eligibility_status") not in {"eligible","excluded_by_policy","transition_unapproved","unavailable"} for r in rows): errors.append("invalid_eligibility_status")
    elif artifact_type == policy["consensus_artifact_type"]:
        if manifest.get("method_id") != policy["method_id"] or manifest.get("monetary_reference_id") != policy["monetary_reference_id"]:
            errors.append("method_identity_mismatch")
        table = base / "monthly_consensus.csv"
        if not table.is_file(): errors.append("monthly_consensus_missing")
        else:
            rows = list(csv.DictReader(table.open(encoding="utf-8")))
            if not rows: errors.append("monthly_consensus_empty")
            for row in rows:
                try:
                    count = int(row["contributing_source_count"])
                    rate = float(row["consensus_monthly_inflation_pct"])
                except Exception:
                    errors.append("invalid_consensus_row"); continue
                if count < int(policy["minimum_emitted_contributors"]): errors.append("undercovered_emitted_row")
                if row.get("coverage_class") != policy["coverage_classes"].get(str(count), "no_consensus"): errors.append("coverage_class_mismatch")
                if not math.isfinite(rate): errors.append("nonfinite_consensus_rate")
            base_rows = [r for r in rows if r.get("period") == policy["analytical_base_period"]]
            if len(base_rows) != 1 or base_rows[0].get("consensus_index") != "100" or base_rows[0].get("index_status") != "anchored":
                errors.append("analytical_base_not_anchored")
            if require_approved_latest and rows:
                latest = rows[-1]
                if latest.get("approved_mode_eligible") != "true" or int(latest.get("contributing_source_count", 0)) < int(policy["approved_mode_minimum_contributors"]):
                    errors.append("latest_period_not_approved_mode_eligible")
    elif artifact_type == policy["conversion_artifact_type"]:
        if manifest.get("method_id") != policy["method_id"] or manifest.get("monetary_reference_id") != policy["monetary_reference_id"]:
            errors.append("method_identity_mismatch")
        table = base / "monthly_conversion_factors.csv"
        if not table.is_file(): errors.append("conversion_table_missing")
        else:
            rows = list(csv.DictReader(table.open(encoding="utf-8")))
            if not rows: errors.append("conversion_table_empty")
            for row in rows:
                try:
                    values = [float(row["consensus_index"]), float(row["factor_period_to_reference"]), float(row["factor_reference_to_period"])]
                except Exception:
                    errors.append("invalid_conversion_row"); continue
                if any(not math.isfinite(v) or v <= 0 for v in values): errors.append("invalid_conversion_factor")
    return sorted(set(errors))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("release")
    parser.add_argument("--require-approved-latest", action="store_true")
    parser.add_argument("--policy", default=str(ROOT / "contracts/panel_v2.json"))
    args = parser.parse_args()
    policy = load_policy(Path(args.policy))
    errors = validate_release(Path(args.release), policy, args.require_approved_latest)
    if errors:
        raise SystemExit("ERROR: " + ", ".join(errors))
    print("valid v2 candidate")


if __name__ == "__main__":
    main()
