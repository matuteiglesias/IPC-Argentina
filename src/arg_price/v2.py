"""Curated official-panel v2 semantics and deterministic consensus kernel.

This module is intentionally independent of network/source adapters. It consumes
source-normalized monthly level observations and applies the frozen v2 panel
policy. Source acquisition and parsing remain separate concerns.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def load_policy(path: Path) -> dict:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("schema") != "argentina-price-consensus-panel/v2":
        raise ValueError("unsupported_panel_policy")
    members = policy.get("panel_members", [])
    ids = [m.get("member_id") for m in members]
    if len(ids) != 5 or len(set(ids)) != 5:
        raise ValueError("v2_panel_must_have_exactly_five_unique_members")
    return policy


def _month(value: str) -> str:
    value = str(value)[:10]
    if len(value) < 7:
        raise ValueError(f"invalid_period:{value}")
    year, month = map(int, value[:7].split("-"))
    if not 1 <= month <= 12:
        raise ValueError(f"invalid_period:{value}")
    return f"{year:04d}-{month:02d}-01"


def _previous_month(period: str) -> str:
    year, month = map(int, _month(period)[:7].split("-"))
    if month == 1:
        return f"{year - 1:04d}-12-01"
    return f"{year:04d}-{month - 1:02d}-01"


def _next_month(period: str) -> str:
    year, month = map(int, _month(period)[:7].split("-"))
    if month == 12:
        return f"{year + 1:04d}-01-01"
    return f"{year:04d}-{month + 1:02d}-01"


def _in_window(period: str, start: str | None, end: str | None) -> bool:
    period = _month(period)
    return (start is None or period >= _month(start)) and (end is None or period <= _month(end))


def member_for_source(source_id: str, policy: dict) -> str:
    matches = [m["member_id"] for m in policy["panel_members"] if source_id in m.get("source_ids", [])]
    if len(matches) != 1:
        raise ValueError(f"source_not_uniquely_bound_to_panel:{source_id}")
    return matches[0]


def eligibility_status(source_id: str, period: str, policy: dict) -> str:
    member = next((m for m in policy["panel_members"] if source_id in m.get("source_ids", [])), None)
    if member is None:
        return "not_in_panel"
    rules = [r for r in member.get("eligibility", []) if r.get("source_id") == source_id]
    matches = [r for r in rules if _in_window(period, r.get("start"), r.get("end"))]
    if len(matches) > 1:
        raise ValueError(f"overlapping_eligibility_rules:{source_id}:{_month(period)}")
    if not matches:
        return "unavailable"
    return matches[0]["status"]


def normalize_source_rows(rows: list[dict], policy: dict) -> list[dict]:
    """Decorate canonical level rows with panel identity, eligibility and MoM rate.

    The month-over-month rate is emitted only when both endpoints are eligible
    observations from the same source and are exactly consecutive months.
    """
    canonical = []
    seen: dict[tuple[str, str], float] = {}
    for raw in rows:
        sid = raw["source_id"]
        period = _month(raw["period"])
        value = float(raw["source_index"])
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"nonfinite_or_nonpositive_index:{sid}:{period}")
        key = (sid, period)
        if key in seen and seen[key] != value:
            raise ValueError(f"conflicting_duplicate:{sid}:{period}")
        seen[key] = value
        canonical.append({
            "source_id": sid,
            "panel_member_id": member_for_source(sid, policy),
            "period": period,
            "source_index": format(value, ".15g"),
            "source_base_or_vintage": raw.get("source_base_or_vintage", "source-declared"),
            "value_status": raw.get("value_status", "observed"),
            "eligibility_status": eligibility_status(sid, period, policy),
            "monthly_inflation_pct": "",
            "monthly_change_status": "not_computable",
            "source_snapshot_sha256": raw.get("source_snapshot_sha256", ""),
            "parser_id": raw.get("parser_id", ""),
        })

    by_source: dict[str, list[dict]] = defaultdict(list)
    for row in canonical:
        by_source[row["source_id"]].append(row)

    for source_rows in by_source.values():
        source_rows.sort(key=lambda r: r["period"])
        previous = None
        for row in source_rows:
            if row["eligibility_status"] != "eligible":
                row["monthly_change_status"] = row["eligibility_status"]
            elif previous is None:
                row["monthly_change_status"] = "no_previous_observation"
            elif previous["period"] != _previous_month(row["period"]):
                row["monthly_change_status"] = "nonconsecutive_observation"
            elif previous["eligibility_status"] != "eligible":
                row["monthly_change_status"] = "previous_period_not_eligible"
            else:
                current_value = float(row["source_index"])
                previous_value = float(previous["source_index"])
                rate = 100.0 * (current_value / previous_value - 1.0)
                row["monthly_inflation_pct"] = format(rate, ".15g")
                row["monthly_change_status"] = "eligible_rate"
            previous = row

    return sorted(canonical, key=lambda r: (r["period"], r["panel_member_id"], r["source_id"]))


def coverage_class(count: int, policy: dict) -> str:
    return policy.get("coverage_classes", {}).get(str(count), "no_consensus")


def build_consensus(normalized_rows: list[dict], policy: dict) -> list[dict]:
    """Build equal-weight monthly v2 consensus plus coverage/dispersion evidence."""
    order = [m["member_id"] for m in policy["panel_members"]]
    by_period: dict[str, list[dict]] = defaultdict(list)
    for row in normalized_rows:
        by_period[_month(row["period"])].append(row)

    minimum = int(policy["minimum_emitted_contributors"])
    approved_min = int(policy["approved_mode_minimum_contributors"])
    out = []
    for period in sorted(by_period):
        period_rows = by_period[period]
        contributing = [
            r for r in period_rows
            if r.get("eligibility_status") == "eligible"
            and r.get("monthly_change_status") == "eligible_rate"
            and r.get("monthly_inflation_pct") not in (None, "")
        ]
        # One fixed panel member contributes at most once per month.
        by_member: dict[str, dict] = {}
        for row in contributing:
            member = row["panel_member_id"]
            if member in by_member:
                raise ValueError(f"multiple_contributing_sources_for_member:{member}:{period}")
            by_member[member] = row
        contributing = [by_member[m] for m in order if m in by_member]
        count = len(contributing)
        if count < minimum:
            continue

        rates = [float(r["monthly_inflation_pct"]) for r in contributing]
        reasons = []
        for member in order:
            if member in by_member:
                continue
            member_rows = [r for r in period_rows if r["panel_member_id"] == member]
            if member_rows:
                statuses = sorted({r.get("eligibility_status", "unavailable") for r in member_rows})
                change_statuses = sorted({r.get("monthly_change_status", "not_computable") for r in member_rows})
                reason = "+".join(statuses + change_statuses)
            else:
                reason = "unavailable"
            reasons.append(f"{member}:{reason}")

        row = {
            "period": period,
            "consensus_monthly_inflation_pct": format(statistics.fmean(rates), ".15g"),
            "median_monthly_inflation_pct": format(statistics.median(rates), ".15g"),
            "min_monthly_inflation_pct": format(min(rates), ".15g"),
            "max_monthly_inflation_pct": format(max(rates), ".15g"),
            "population_std_monthly_inflation_pct": format(statistics.pstdev(rates), ".15g"),
            "contributing_member_ids": "|".join(r["panel_member_id"] for r in contributing),
            "contributing_source_ids": "|".join(r["source_id"] for r in contributing),
            "contributing_source_count": str(count),
            "coverage_class": coverage_class(count, policy),
            "approved_mode_eligible": "true" if count >= approved_min else "false",
            "noncontributing_member_reasons": "|".join(reasons),
            "consensus_index": "",
            "index_status": "unanchored",
            "method_id": policy["method_id"],
        }
        out.append(row)

    _anchor_index(out, policy["analytical_base_period"])
    return out


def _anchor_index(rows: list[dict], base_period: str) -> None:
    if not rows:
        return
    base_period = _month(base_period)
    index_by_period = {r["period"]: i for i, r in enumerate(rows)}
    if base_period not in index_by_period:
        raise ValueError("consensus_base_period_missing")
    base_i = index_by_period[base_period]
    rows[base_i]["consensus_index"] = "100"
    rows[base_i]["index_status"] = "anchored"

    value = 100.0
    previous_period = base_period
    for i in range(base_i + 1, len(rows)):
        row = rows[i]
        if row["period"] != _next_month(previous_period):
            break
        rate = float(row["consensus_monthly_inflation_pct"])
        value *= 1.0 + rate / 100.0
        row["consensus_index"] = format(value, ".15g")
        row["index_status"] = "anchored"
        previous_period = row["period"]

    value = 100.0
    next_period = base_period
    for i in range(base_i - 1, -1, -1):
        row = rows[i]
        if row["period"] != _previous_month(next_period):
            break
        next_row = rows[index_by_period[next_period]]
        rate = float(next_row["consensus_monthly_inflation_pct"])
        denominator = 1.0 + rate / 100.0
        if denominator <= 0:
            raise ValueError(f"invalid_consensus_rate:{next_period}")
        value /= denominator
        row["consensus_index"] = format(value, ".15g")
        row["index_status"] = "anchored"
        next_period = row["period"]


def conversion_factor(consensus_rows: list[dict], from_period: str, to_period: str) -> float:
    indexed = {r["period"]: r for r in consensus_rows if r.get("index_status") == "anchored"}
    start = indexed.get(_month(from_period))
    end = indexed.get(_month(to_period))
    if start is None or end is None:
        raise ValueError("unsupported_conversion_period")
    return float(end["consensus_index"]) / float(start["consensus_index"])
