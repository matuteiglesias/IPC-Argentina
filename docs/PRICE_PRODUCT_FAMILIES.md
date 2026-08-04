# Price product families and period-status contract

This inventory describes the committed snapshot; it does not certify current official data. The official publishers own their input series, while every combined output here is an analytical construction.

## Inventory

| Path/product | Family | Columns / unit | Frequency and base | Coverage and classification | Publisher/evidence and producer | Consumers / limitations |
|---|---|---|---|---|---|---|
| INDEC historical input (not retained) | `official_observed_source` | level-general index, source units | monthly; source base | code selects 2000-01–2007-02; exact retrieved vintage unresolved | INDEC URL embedded in `computarInflacion.py`; parsed there | feeds monthly composite; no input hash or access date |
| INDEC modern input (not retained) | `official_observed_source` | `ipc_ng_nacional`, source index | monthly; Dec-2016 base | retrieval coverage varies; current retrieved cutoff unverified | datos.gob.ar URL; `computarInflacion.py` | feeds monthly composite; no retained source snapshot |
| CABA input (not retained) | `official_observed_source` | general level, source index | monthly; source-declared base | retrieval coverage and vintage unresolved | CABA workbook URL; `computarInflacion.py` | feeds monthly composite; URL embeds 2022/02 |
| Córdoba input (not retained) | `official_observed_source` | general level, source index | monthly; 2014 base named in worksheet | retrieval coverage and vintage unresolved | Córdoba workbook URL; `computarInflacion.py` | feeds monthly composite; fixed resource name contains “enero” |
| San Luis input (not retained) | `official_observed_source` | general level, source index | monthly; source-declared base | retrieval coverage and vintage unresolved | IERIC discovery page/workbook; `computarInflacion.py` | feeds monthly composite; adapter depends on link text |
| `data/info/indice_precios_M.csv` | `analytical_composite` plus `projected_extension` | `log_index`, `index`, log change, percent monthly | monthly; Jan-2016=100 | 312 periods: 2000-01–2025-12; 307 declared derived through 2025-07, 5 projected 2025-08–12 | five inputs and transformation code | public research output; likely downstream use, but exact consumer checkout unavailable |
| `data/info/indice_precios_d.csv` | `interpolated_daily_series` | log index and index | daily; Jan-2016=100 | 9,467 dates: monthly knots are derived/projected; all other dates interpolated; projection flag propagates after 2025-07 | quadratic interpolation in `computarInflacion.py` | never an observed daily IPC |
| `data/info/indice_precios_Q.csv` | `analytical_composite` | index | quarterly, mid-quarter label; Jan-2016=100 scale | 104 quarters: aggregations of derived monthly values; final two quarters include projected inputs | quarterly mean in `computarInflacion.py` | class is derived, with projected flag where applicable |
| `data/info/ex_PPP.csv` | `historical_unresolved_artifact` | OECD-style PPP table; national currency/USD | annual; series-specific | 1960–2021, many countries; provenance/producer not declared in code | committed file only | not connected to price graph; do not infer EPH conversion use |
| `data/info/tcambiousd_diario.csv` | `historical_unresolved_artifact` | multiple nominal exchange rates/market fields | daily, nominal references | 2002-03-05–2022-11-30 | committed file only | not connected to price graph; not a price index |
| `figuras/figura2.png`, `figuras/figura3.png` | `analytical_composite` visualization | raster plots | generated | reflects the then-generated composite; no embedded lineage | `computarInflacion.py` | not a release-grade numeric artifact |

There is currently no real `normalized_observed_series` or `conversion_factor_release`: source inputs are held only in memory. The synthetic fixture demonstrates the latter without asserting a real monetary reference.

## Deterministic classification semantics

* `observed`: a value copied from a named publisher artifact without numeric transformation beyond parsing.
* `derived`: computed from one or more values without filling a missing period or changing frequency.
* `imputed`: supplied for a missing expected source period by a declared fill rule.
* `interpolated`: estimated between temporal knots while changing or completing frequency.
* `projected`: extends beyond the declared observed-source cutoff.
* `synthetic`: invented solely for tests or demonstrations.
* `unresolved`: evidence is insufficient to assign lineage or method.

Primary class uses the most consequential operation in this order: `unresolved`, `synthetic`, `projected`, `interpolated`, `imputed`, `derived`, `observed`. Flags preserve additional operations. Thus monthly composite periods through July 2025 are **derived**, not observed; August–December 2025 are **projected** with a derived flag. Daily non-knot values are interpolated and inherit projected when their bracketing/preceding release segment is projected. Quarterly values are derived and inherit projected if any contributing month is projected.

## Current online-chain finding

A current guarantee is impossible from this snapshot. The pipeline neither retains exact downloaded inputs nor records response metadata, hashes, vintages, or a successful run after 2025-07-15. On 2026-08-04, bounded GET attempts to all five configured endpoints were blocked by this execution environment's proxy (HTTP tunnel 403), so source compatibility could not be distinguished from network policy. Even a successful probe would establish reachability, not official freshness or a valid composite. A safe recovery needs staged source snapshots, adapter checks, reviewed transformation output, and explicit human acceptance before `DATA_STATUS.json` changes.
