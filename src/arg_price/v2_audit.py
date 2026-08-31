"""Scientific comparison utilities for legacy-compatible v1 versus curated v2.

The audit never promotes either method. It summarizes common-support differences,
panel coverage and bounded robustness alternatives from immutable candidate files.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _rows(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _number(value):
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _legacy_rows(path: Path) -> dict[str, dict]:
    rows = {}
    for row in _rows(path):
        period = row.get("period") or row.get("") or row.get("indice_tiempo")
        if not period:
            continue
        rows[period[:7] + "-01"] = {
            "index": _number(row.get("index")),
            "monthly_change_pct": _number(row.get("pct_m") or row.get("monthly_change_pct")),
        }
    return rows


def _geometric_rate(rates: list[float]) -> float:
    relatives = [1.0 + rate / 100.0 for rate in rates]
    if any(value <= 0 for value in relatives):
        raise ValueError("nonpositive_price_relative")
    return 100.0 * (math.prod(relatives) ** (1.0 / len(relatives)) - 1.0)


def _mean_abs(values: list[float]) -> float | None:
    return statistics.fmean(abs(x) for x in values) if values else None


def _summary(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "mean_difference_pct_points": None, "mean_absolute_difference_pct_points": None, "max_absolute_difference_pct_points": None}
    return {
        "count": len(values),
        "mean_difference_pct_points": statistics.fmean(values),
        "mean_absolute_difference_pct_points": _mean_abs(values),
        "max_absolute_difference_pct_points": max(abs(x) for x in values),
    }


def audit(
    legacy_monthly: Path,
    normalized_sources: Path,
    consensus_monthly: Path,
    output_dir: Path,
) -> dict:
    legacy = _legacy_rows(legacy_monthly)
    normalized = _rows(normalized_sources)
    consensus = _rows(consensus_monthly)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_rates = defaultdict(list)
    for row in normalized:
        if row.get("eligibility_status") != "eligible" or row.get("monthly_change_status") != "eligible_rate":
            continue
        rate = _number(row.get("monthly_inflation_pct"))
        if rate is not None:
            source_rates[row["period"]].append((row["panel_member_id"], row["source_id"], rate))

    comparison = []
    robustness = []
    common_differences = []
    intervention_differences = []
    index_differences = []
    coverage_counts = defaultdict(int)
    max_dropout_shift = 0.0
    max_arithmetic_geometric_gap = 0.0

    for row in consensus:
        period = row["period"]
        v2_rate = _number(row.get("consensus_monthly_inflation_pct"))
        v2_index = _number(row.get("consensus_index"))
        v1 = legacy.get(period, {})
        v1_rate = v1.get("monthly_change_pct")
        v1_index = v1.get("index")
        rate_diff = v2_rate - v1_rate if v2_rate is not None and v1_rate is not None else None
        index_diff = v2_index - v1_index if v2_index is not None and v1_index is not None else None
        if rate_diff is not None:
            common_differences.append(rate_diff)
            if "2007-01-01" <= period <= "2015-12-01":
                intervention_differences.append(rate_diff)
        if index_diff is not None:
            index_differences.append(index_diff)
        coverage_counts[row.get("coverage_class", "unknown")] += 1
        comparison.append({
            "period": period,
            "v1_monthly_change_pct": "" if v1_rate is None else format(v1_rate, ".15g"),
            "v2_monthly_inflation_pct": "" if v2_rate is None else format(v2_rate, ".15g"),
            "v2_minus_v1_pct_points": "" if rate_diff is None else format(rate_diff, ".15g"),
            "v1_index": "" if v1_index is None else format(v1_index, ".15g"),
            "v2_index": "" if v2_index is None else format(v2_index, ".15g"),
            "v2_minus_v1_index_points": "" if index_diff is None else format(index_diff, ".15g"),
            "contributing_source_count": row.get("contributing_source_count", ""),
            "coverage_class": row.get("coverage_class", ""),
        })

        members = source_rates.get(period, [])
        rates = [item[2] for item in members]
        arithmetic = statistics.fmean(rates) if rates else None
        geometric = _geometric_rate(rates) if rates else None
        arithmetic_geometric_gap = arithmetic - geometric if arithmetic is not None else None
        if arithmetic_geometric_gap is not None:
            max_arithmetic_geometric_gap = max(max_arithmetic_geometric_gap, abs(arithmetic_geometric_gap))
        leave_one_out = []
        if len(rates) >= 3:
            for member, _, rate in members:
                reduced = [x for x in rates if x is not rate]
                # Values can coincide; remove by position instead of equality.
            for index, (member, _, _) in enumerate(members):
                reduced = [item[2] for j, item in enumerate(members) if j != index]
                shift = statistics.fmean(reduced) - statistics.fmean(rates)
                leave_one_out.append((member, shift))
                max_dropout_shift = max(max_dropout_shift, abs(shift))
        worst = max(leave_one_out, key=lambda item: abs(item[1])) if leave_one_out else ("", None)
        robustness.append({
            "period": period,
            "source_count": str(len(rates)),
            "arithmetic_mean_pct": "" if arithmetic is None else format(arithmetic, ".15g"),
            "geometric_mean_pct": "" if geometric is None else format(geometric, ".15g"),
            "arithmetic_minus_geometric_pct_points": "" if arithmetic_geometric_gap is None else format(arithmetic_geometric_gap, ".15g"),
            "worst_leave_one_out_member": worst[0],
            "worst_leave_one_out_shift_pct_points": "" if worst[1] is None else format(worst[1], ".15g"),
        })

    with (output_dir / "monthly_v1_v2_comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = list(comparison[0]) if comparison else ["period"]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n"); writer.writeheader(); writer.writerows(comparison)
    with (output_dir / "monthly_robustness.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = list(robustness[0]) if robustness else ["period"]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n"); writer.writeheader(); writer.writerows(robustness)

    summary = {
        "schema": "argentina-price-v1-v2-scientific-audit/v1",
        "status": "diagnostic_only_no_promotion",
        "common_monthly_change_comparison": _summary(common_differences),
        "intervention_window_2007_2015": _summary(intervention_differences),
        "common_index_points": _summary(index_differences),
        "v2_coverage_counts": dict(sorted(coverage_counts.items())),
        "robustness": {
            "max_absolute_arithmetic_vs_geometric_gap_pct_points": max_arithmetic_geometric_gap,
            "max_absolute_single_member_dropout_shift_pct_points": max_dropout_shift,
        },
        "interpretation_guardrails": [
            "v1 and v2 are distinct method identities and are not expected to match",
            "the 2007-2015 slice is diagnostic, not evidence that any one source is ground truth",
            "leave-one-out sensitivity is a robustness diagnostic, not a source-selection rule",
            "no promotion decision is made by this report",
        ],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-monthly", default=str(ROOT / "data/info/indice_precios_M.csv"))
    parser.add_argument("--normalized-sources", required=True)
    parser.add_argument("--consensus-monthly", required=True)
    parser.add_argument("--output", default="artifacts/price_v2/audit")
    args = parser.parse_args()
    summary = audit(Path(args.legacy_monthly), Path(args.normalized_sources), Path(args.consensus_monthly), Path(args.output))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
