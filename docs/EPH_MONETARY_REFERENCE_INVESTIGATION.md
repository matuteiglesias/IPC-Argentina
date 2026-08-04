# Historical EPH monetary-reference investigation

## Finding

| Annual artifact | Classification | Evidence available here | Missing evidence |
|---|---|---|---|
| `EPHARG_annual_input_22.csv` | `unresolved` | no filename, hash, manifest, script reference, or value sample in repository history/workspace | artifact/hash, producing revision and bounded value pairs |
| `EPHARG_annual_input_23.csv` | `unresolved` | same | same |
| `EPHARG_annual_input_24.csv` | `unresolved` | same | same |
| `EPHARG_annual_input_25.csv` | `unresolved` | same | same |

The only checkout under `/workspace` during the 2026-08-04 investigation was `IPC-Argentina`; neither `income-modeling-eph` nor `canastasINDEC` was available. Searches of all repository refs found no EPH annual filename or monetary-reference manifest. The two unrelated committed tables (`ex_PPP.csv` and `tcambiousd_diario.csv`) are not evidence that either was used for EPH materialization.

Therefore retain **`provisional:legacy-price-series-unidentified`**. No candidate achieved `identified_with_hash_evidence`, `identified_by_code_and_value_match`, `probable_but_unverified`, or `multiple_candidates`.

## Reproducible next investigation

Obtain the four exact annual artifacts and read-only downstream history. Record SHA-256 hashes before analysis. Locate the producing script/config at its historical commit; then compare bounded monetary columns against each candidate conversion with documented rounding tolerance. A code path plus exact bounded matches may support `identified_by_code_and_value_match`; an artifact manifest or recorded matching hash is required for `identified_with_hash_evidence`. Similar dates, names, or plausible magnitudes are insufficient.
