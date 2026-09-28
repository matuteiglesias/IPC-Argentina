# Codex P1 — materialize and commission real INDEC regional-division IPC

## Scope

Work only in `matuteiglesias/IPC-Argentina` after the cloud implementation of `publicdata.indec-ipc-regional-divisions/v1` is present.

Do not modify Canastas, Poverty, ENGHo weights, the curated v2 price consensus, or monetary-conversion methodology.

## Goal

Run the new source-lock and release machinery against the live official INDEC historical regional-division series, then return a compact coverage/identity receipt. Do not commit raw source snapshots unless repository policy explicitly changes; the important persistent result is the receipt/evidence needed to decide whether a small derived release should be retained.

## Commands

```bash
make indec-regional-lock
make indec-regional-build

REGIONAL_RELEASE="$(find artifacts/indec_ipc_regional_divisions -mindepth 1 -maxdepth 1 -type d | sort | tail -1)"
make indec-regional-check REGIONAL_RELEASE="$REGIONAL_RELEASE"
make indec-regional-coverage REGIONAL_RELEASE="$REGIONAL_RELEASE" > /tmp/indec-regional-coverage.json
```

The commissioning validation must include the real-data `--require-engel-window` gate through the Make target.

## Required receipt

Return exactly these facts from the materialized release:

1. source lock SHA-256 for `serie_ipc_divisiones.csv` and companion metadata SHA-256;
2. resolved official source URLs and retrieval timestamp;
3. release ID and normalized payload checksum;
4. first month, last month, number of distinct months, and any missing months inside the observed span;
5. exact region inventory and exact division inventory;
6. missing-cell count and, if nonzero, a compact grouped summary by period/region/division rather than silently filling anything;
7. duplicate-cell count;
8. index-base inventory and any structural-break/base-change diagnostic;
9. explicit PASS/FAIL for coverage from 2018-05 through 2025-12;
10. confirmation that all emitted rows have `value_status=direct_official_observation` and source-cell identities.

## Acceptance

P1 is complete only if the release validator passes with `--require-engel-window`, duplicates are zero, the six governed regions and twelve division IDs are present, base metadata is consistent with `2016-12=100`, and no imputation occurred.

If the source schema has changed, stop at a parser mismatch with the exact observed headers/sample identities. Repair the source adapter narrowly; do not weaken the contract or infer missing observations.
