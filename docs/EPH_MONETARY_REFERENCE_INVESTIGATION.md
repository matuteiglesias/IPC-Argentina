# Historical EPH monetary-reference investigation

## Updated finding — 2026-08-27

The earlier investigation could not inspect the downstream EPH repositories and therefore classified the annual artifacts themselves as unavailable. That part is now resolved.

`income-modeling-eph` currently contains exact annual artifacts and manifests for 2022–2025:

| Annual artifact | SHA-256 | Materialization identity | Monetary classification |
|---|---|---|---|
| `EPHARG_annual_input_22.csv` | `05397f7e7c7ce174ffba4e17bcbbdfbbc5790d3e9aaebfb94b3a056908fc2dd3` | `unresolved-historical-materialization` | `provisional:legacy-price-series-unidentified` |
| `EPHARG_annual_input_23.csv` | `1788a3d9829e7772829e9a99adafc51e2ad5c77406c3ef74b2f5f413a56ece4a` | `unresolved-historical-materialization` | `provisional:legacy-price-series-unidentified` |
| `EPHARG_annual_input_24.csv` | `b8262193afd1a495f31b45d7fd72e795259829b5a1bc7084fa7741c5d4661d1f` | `unresolved-historical-materialization` | `provisional:legacy-price-series-unidentified` |
| `EPHARG_annual_input_25.csv` | `460a6ee7b64eda71745fce2d3f069af903d1f747aa7b015079477aebe122d1e0` | `unresolved-historical-materialization` | `provisional:legacy-price-series-unidentified` |

So the **artifact identity problem is now bounded**, while the exact price-series vintage remains unresolved.

## Historical transformation shape is identified

The former producer is preserved in `encuestador-de-hogares/src/encuestador/preprocesar_datos.py` and its lineage documentation.

The historical code:

1. loaded `IPC-Argentina/main/data/info/indice_precios_Q.csv` from a mutable raw GitHub URL;
2. loaded `indice_precios_M.csv` from the same mutable branch;
3. took the January-2016 monthly `index` value as `ix`;
4. assigned each EPH quarter the 15th day of its middle month;
5. multiplied nine monetary fields by `ix / quarter_index`;
6. rounded the resulting values.

Conceptually:

```text
amount_jan2016
  = round(
      nominal_amount_quarter
      * ipc_index[2016-01]
      / ipc_index[quarter_reference]
    )
```

for:

```text
P21
P47T
PP08D1
TOT_P12
T_VI
V12_M
V2_M
V3_M
V5_M
```

This supports a stronger classification than the previous `no code evidence` state:

```text
transformation_shape = identified_by_code
reference_semantics  = January-2016 analytical price reference
price_series_vintage = unresolved
artifact_materialization_revision = unresolved
```

The code path alone does **not** identify which commit/snapshot of `indice_precios_Q.csv` and `indice_precios_M.csv` produced the exact tracked annual artifacts because the producer read mutable `main` URLs.

## What is still not proven

Do not upgrade the annual artifacts to an approved monetary reference yet.

The remaining evidence gap is narrower:

- exact `IPC-Argentina` revision or price-release bytes used at each historical materialization;
- exact producing revision/time for each annual artifact;
- bounded value-level confirmation that the tracked CSV values match a candidate IPC snapshot under the identified formula and rounding rule.

The current `income-modeling-eph` manifests explicitly preserve the unresolved monetary state and should continue to do so until this gap is closed.

## Reproducible next investigation

For each annual artifact:

1. retain the exact artifact SHA-256 already recorded above;
2. locate the most plausible historical producing window/revision from Git history or workflow evidence;
3. enumerate candidate `IPC-Argentina` revisions/snapshots available in that window;
4. reconstruct the exact quarter reference dates used by the historical producer;
5. compare bounded rows for several monetary fields against:

```text
round(raw_nominal * ipc_2016_01 / ipc_quarter)
```

6. record both matches and counterexamples under an explicit tolerance;
7. classify only after evidence:
   - `identified_with_hash_evidence` if an exact retained price artifact/release identity is recovered;
   - `identified_by_code_and_value_match` if the historical code path plus bounded exact value matches uniquely identify one candidate;
   - `multiple_candidates` if more than one snapshot remains observationally compatible;
   - `unresolved` otherwise.

Similar dates, filenames, or plausible magnitudes remain insufficient.

## Forward-looking boundary

Historical reconstruction is a compatibility concern. New EPH analysis frames and new welfare releases should not depend on reconstructing mutable historical URLs.

For modern production:

```text
approved monetary-conversion release
        ↓
explicit source reference
explicit target reference
exact factor/method lineage
        ↓
consumer applies conversion
```

The downstream artifact should record the exact conversion release ID. `income-modeling-eph` and `encuestador-de-hogares` should not independently reproduce the IPC transformation graph.
