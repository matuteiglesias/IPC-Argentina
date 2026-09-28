# INDEC IPC regional divisions v1

`publicdata.indec-ipc-regional-divisions/v1` is a narrow direct-official evidence product for monthly INDEC consumer-price indices at the grain:

```text
period × official statistical region × COICOP expenditure division
```

It exists to support research such as Engel/CBT trajectory work without changing the repository's existing curated multi-source monetary-consensus authority.

## Official source

Primary machine source:

- `https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_divisiones.csv`

Companion metadata:

- `https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_metadatos.txt`

Landing page:

- `https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-31`

INDEC describes the regional/division series as IPC with national coverage, regional results, COICOP divisions, and base December 2016=100. The release lock pins the exact CSV and metadata bytes before any normalization occurs.

## Product boundary

This surface is direct normalized INDEC evidence. It is not a member of `research.argentina-price-consensus/v2` and is never averaged with CABA, Córdoba, San Luis, Neuquén, or any other publisher.

The product does not own or apply ENGHo expenditure weights, Engel coefficients, CBA/CBT methodology, poverty thresholds, or missing-value imputation.

## Stable identities

Regions are normalized to:

- `gran_buenos_aires`
- `pampeana`
- `noreste`
- `noroeste`
- `cuyo`
- `patagonia`

The twelve official expenditure divisions use transparent stable IDs `coicop01` through `coicop12`. The official Spanish division label is retained beside the ID.

Each observation also retains:

- the exact source snapshot SHA-256;
- a source-cell identity locating the source CSV row and `Indice_IPC` cell;
- the explicit index base `2016-12=100`;
- `value_status=direct_official_observation`.

## Exact materialization

```bash
PYTHONPATH=src python3 -m arg_price.indec_regional_divisions lock \
  --output-root build/indec_ipc_regional_divisions

PYTHONPATH=src python3 -m arg_price.indec_regional_divisions build \
  --lock build/indec_ipc_regional_divisions/source_lock.json \
  --output-root artifacts/indec_ipc_regional_divisions

RELEASE="$(find artifacts/indec_ipc_regional_divisions -mindepth 1 -maxdepth 1 -type d | sort | tail -1)"
PYTHONPATH=src python3 -m arg_price.indec_regional_divisions validate \
  "$RELEASE" --require-engel-window

PYTHONPATH=src python3 -m arg_price.indec_regional_divisions coverage "$RELEASE"
```

Equivalent Make targets are `indec-regional-lock`, `indec-regional-build`, `indec-regional-check`, and `indec-regional-coverage`.

## Release contents

An immutable release contains:

- `regional_division_indices.csv` — normalized observations only;
- `source_lock.json` — exact source identity and hashes (without mutable local paths);
- `coverage.json` — first/last month, observed and expected month counts, missing-month diagnostics, inventories, missing/duplicate counts, base consistency and structural-break diagnostics;
- `missing_cells.csv` — explicit absent period × region × division cells;
- `contract.json` — compact machine-readable product boundary;
- `manifest.json` and `checksums.sha256` — content-addressed release envelope.

Existing release directories are never overwritten. Re-running a build from the same lock returns the same release; a path/content collision fails.

## Coverage gate

Hosted/offline tests deliberately use small synthetic fixtures and do not pretend to establish real INDEC coverage. Real commissioning must run `validate --require-engel-window`, which requires every monthly period from May 2018 through December 2025 to be present, not merely suitable endpoints. Missing months and missing cells are surfaced explicitly and never filled.
