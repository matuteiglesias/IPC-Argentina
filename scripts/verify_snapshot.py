#!/usr/bin/env python3
"""Verify the declared IPC snapshot boundaries without network access."""

from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "DATA_STATUS.json"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        fail(f"invalid ISO date {value!r}: {exc}")


status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
artifact = ROOT / status["artifact"]
if not artifact.is_file():
    fail(f"missing declared artifact: {artifact.relative_to(ROOT)}")

with artifact.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))

if not rows:
    fail("artifact contains no data rows")

date_column = next((name for name in rows[0] if name in {"", "date", "period", "Q"}), None)
if date_column is None:
    fail(f"could not identify date column; columns={list(rows[0])}")

periods = [parse_date(row[date_column]) for row in rows]
actual_max = max(periods).isoformat()
if actual_max != status["artifact_max_period"]:
    fail(
        "declared artifact_max_period does not match CSV: "
        f"declared={status['artifact_max_period']} actual={actual_max}"
    )

observed_through = parse_date(status["observed_through"])
projected_from = parse_date(status["projected_from"])
projected = [row for row, period in zip(rows, periods) if period >= projected_from]
if not projected:
    fail("no rows exist at or after projected_from")

if "pct_m" not in rows[0]:
    fail("expected pct_m column is missing")

projected_rates = {row["pct_m"] for row in projected}
if len(projected_rates) != 1:
    fail(
        "projected tail no longer has one repeated pct_m value; "
        "review DATA_STATUS.json and the projection boundary"
    )

print(
    json.dumps(
        {
            "artifact": status["artifact"],
            "rows": len(rows),
            "first_period": min(periods).isoformat(),
            "artifact_max_period": actual_max,
            "observed_through": observed_through.isoformat(),
            "projected_from": projected_from.isoformat(),
            "projected_rows": len(projected),
            "projected_pct_m": next(iter(projected_rates)),
            "automation_last_successful_run": status["automation"]["last_successful_run"],
            "result": "snapshot declaration matches committed artifact",
        },
        indent=2,
    )
)
