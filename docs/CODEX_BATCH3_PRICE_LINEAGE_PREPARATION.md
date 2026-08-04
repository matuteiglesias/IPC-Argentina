# Codex work packet — Portfolio Batch 3 preparation: price and monetary-reference lineage

## Mission

Prepare the price-index repository for a later methodology-approved monetary-reference release without changing the current analytical series or publishing a new official-statistics claim.

This packet is deliberately deferred from the active Batch 2/4 focus. It should produce the evidence and release contracts needed to answer:

> What exact price series, transformations, base/reference periods, projections, and interpolations were used by the historical EPH annual inputs and by downstream basket/poverty artifacts?

The result is a lineage and release-preparation packet, not a methodological replacement decision.

## Read first

1. Read every applicable `AGENTS.md` file.
2. Read `README.md`, `SYSTEM.yaml`, `DATA_STATUS.json`, `Makefile`, source/acquisition code, transformation code, generated tables, source notes, tests, and current CI.
3. Inspect commit history around source-series changes, projections, interpolations, base-period changes, and the analytical composite.
4. Inspect `income-modeling-eph` annual manifests and decision logs read-only for the unresolved historical monetary-reference identifier.
5. Inspect `canastasINDEC` read-only only to identify exact consumed price files and transformations.
6. Do not mutate those downstream repositories from this task.

## Authority and scientific boundary

This repository may own:

- acquisition and normalization of declared price series;
- versioned analytical composites;
- declared interpolation/projection transformations;
- monetary-reference conversion factors;
- provenance and data-status classification.

It does not own:

- official national/provincial statistical authority;
- poverty methodology;
- regional basket methodology;
- retroactive approval of undocumented historical transformations;
- proof that historical annual EPH files used a particular series without artifact evidence.

## Required deliverables

### 1. Product-family inventory

Create `docs/PRICE_PRODUCT_FAMILIES.md` separating every output into explicit families such as:

```text
official_observed_source
normalized_observed_series
analytical_composite
interpolated_daily_series
projected_extension
conversion_factor_release
historical_unresolved_artifact
```

For every tracked/generated table record:

- path;
- columns and units;
- frequency;
- base/reference period;
- observed coverage;
- projected/interpolated coverage;
- source publisher and URL/evidence;
- producing code/config;
- downstream consumers;
- current status and limitations.

Do not describe an analytical composite as an official IPC.

### 2. Transformation graph

Create a machine-readable graph showing:

- source series;
- normalization/rebasing;
- splicing;
- jurisdiction aggregation;
- missing-period treatment;
- projection;
- daily/monthly interpolation;
- output files;
- downstream use.

Each edge must identify code, configuration, parameters, and transformation class.

### 3. Observed/derived status table

For every period in every candidate release, classify values using a controlled vocabulary:

```text
observed
derived
imputed
interpolated
projected
synthetic
unresolved
```

A value may require a primary class plus flags, but the semantics must be explicit and deterministic.

### 4. Historical monetary-reference investigation

Attempt to identify the historical price treatment used to materialize:

```text
EPHARG_annual_input_22.csv
EPHARG_annual_input_23.csv
EPHARG_annual_input_24.csv
EPHARG_annual_input_25.csv
```

Use evidence only:

- exact scripts/configs;
- committed or externally supplied hashes;
- matching values in bounded samples;
- historical commit paths;
- old documentation or run logs.

Create `docs/EPH_MONETARY_REFERENCE_INVESTIGATION.md` classifying each annual artifact as:

```text
identified_with_hash_evidence
identified_by_code_and_value_match
probable_but_unverified
multiple_candidates
unresolved
```

Do not replace `provisional:legacy-price-series-unidentified` without sufficient evidence.

### 5. Shared artifact envelope

Adopt `research-artifact-manifest/v1` for fixture/candidate releases while preserving price-specific extensions.

Required artifact types should remain distinct, for example:

```text
publicdata.argentina-price-observed/v1
research.argentina-price-composite/v1
research.argentina-monetary-conversion/v1
```

Do not combine observed source data and analytical projections under one ambiguous release identity.

Use status semantics:

```text
synthetic
candidate
reviewed
approved
```

No automatic promotion.

### 6. Compatibility declaration and preflight

Provide a standard-library validator and compatibility declaration covering:

- manifest schema/type/status;
- frequency and coverage;
- base/reference period;
- observed versus derived policy;
- file hashes and safe paths;
- consumer requirements for `income-modeling-eph` and `canastasINDEC`;
- approved-mode rejection of unresolved or projected periods when prohibited.

### 7. Bounded fixture release

Create a tiny deterministic fixture containing:

- two observed series with different bases;
- a declared rebase;
- a declared splice;
- one missing period;
- one interpolation;
- one projection;
- conversion between two named monetary references;
- explicit status classifications.

The fixture demonstrates mechanics only and must not imitate a real approved IPC.

### 8. Decision packet

Create `docs/PRICE_METHOD_DECISIONS_REQUIRED.md` with the minimum decisions Matías must make before a candidate real release:

- authoritative source series and vintages;
- whether the historical composite remains a supported research product;
- splicing/aggregation policy;
- missing-period treatment;
- projection policy;
- interpolation policy;
- base and output monetary references;
- acceptable use by annual EPH and regional baskets;
- publication language.

For each decision, show observed alternatives and downstream consequences without choosing automatically.

## Command surface

Provide commands equivalent to:

```bash
make check
make release-fixture
make release-check
make monetary-lineage-report
```

Offline checks must not regenerate live data or mutate published tracked outputs.

## Human checkpoints

Stop before:

- changing real historical values;
- rebasing or resplicing the current public series;
- selecting an official/analytical authority;
- replacing the unresolved EPH monetary reference;
- approving projected periods;
- publishing a real candidate release;
- changing downstream basket or poverty calculations.

## Non-goals

- No new current IPC estimate.
- No automatic live refresh.
- No poverty or basket computation.
- No silent historical correction.
- No official-statistics claim.
- No large data commits.
- No downstream repository mutation.

## Acceptance criteria

```text
all price outputs are assigned to explicit product families
the source-to-output transformation graph is machine-readable
periods are classified observed/derived/imputed/interpolated/projected/synthetic/unresolved
the EPH historical monetary-reference investigation reports evidence strength without guessing
fixture releases use the shared envelope and validate independently
observed source releases and analytical composites have separate artifact identities
method decisions and downstream consequences are ready for Matías
no real methodology or historical value is silently changed
```

## Completion report

Report:

- files and product families inventoried;
- transformation graph coverage;
- observed/derived period counts;
- EPH monetary-reference evidence and unresolved gaps;
- fixture release IDs/hashes;
- exact checks run;
- decisions required;
- confirmation that no real price method, downstream calculation, or official claim changed.
