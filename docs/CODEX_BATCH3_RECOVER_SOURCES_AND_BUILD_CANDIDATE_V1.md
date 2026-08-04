# Codex work packet — recover price sources and build candidate v1

## Mission

Implement the first real source-backed candidate release of the legacy-compatible Argentine analytical price composite.

This is no longer an audit-only task. Contact the declared sources where the environment permits, recover exact source snapshots, normalize them, run the approved candidate-v1 method, and emit an immutable candidate artifact that downstream repositories can copy and validate independently.

Read and obey:

1. every applicable `AGENTS.md`;
2. `docs/PRICE_METHOD_DECISION_RECORD_V1.md`;
3. `contracts/source_registry.json`;
4. `docs/PRICE_PRODUCT_FAMILIES.md`;
5. `docs/PRICE_RELEASE_CONTRACT.md`;
6. `contracts/price-transformation-graph.json`;
7. `contracts/price-release-compatibility.json`;
8. `computarInflacion.py`, the legacy notebook export, `DATA_STATUS.json`, `Makefile`, and current fixture validators.

The owner has approved candidate-v1 source selection and methodology. Do not stop merely because one historical source hash, one jurisdiction, or the exact old EPH-consumed price artifact is unavailable. Record those conditions as warnings. Stop on integrity failures or when no source supports an emitted month.

## Approved boundary

### Own here

- source discovery and byte snapshots for the declared IPC inputs;
- source-specific parsing and normalization;
- legacy-compatible monthly composite v1;
- separate projected, interpolated, and quarterly products;
- deterministic manifests, reports, limitations, and validation;
- a content-addressed candidate release directory;
- a portable consumer preflight command.

### Do not own

- official source publication;
- changes to provincial or national source values;
- poverty classification;
- regional basket methodology;
- EPH model training;
- automatic downstream mutation;
- automatic promotion above `candidate`.

## Required implementation

### 1. Source adapter package

Create a small package under a coherent namespace such as:

```text
src/arg_price/
  __init__.py
  sources.py
  normalize.py
  composite.py
  release.py
  validate.py
  cli.py
```

Alternative paths are acceptable when they fit the repository, but do not keep the live logic as one large script.

Each source adapter must:

- use the stable landing/catalog/series page in `contracts/source_registry.json` where available;
- resolve the current downloadable resource rather than depending on a rolling filename;
- use bounded HTTP timeouts and clear user-agent identification;
- fail locally for malformed bytes while allowing the overall run to continue without that source;
- store the resolved URL, retrieval timestamp, headers useful for provenance, byte count, SHA-256, parser ID, schema observations, base/vintage text, and actual period coverage;
- preserve source snapshots outside Git by default under a run-local or cache directory;
- support reading a previously downloaded snapshot offline;
- never execute spreadsheet macros or unsafe archive extraction.

Implement adapters for:

- historical INDEC IPC-GBA workbook;
- national INDEC Datos Argentina CSV;
- CABA official empalmed workbook;
- Córdoba CKAN package/resource discovery, preferring the official empalmed CSV;
- San Luis official report discovery plus the declared IERIC machine-readable workbook mirror.

When a source schema has changed, implement an explicit parser version or adapter variant. Do not silently reinterpret columns.

### 2. Source probe and source-lock commands

Add commands equivalent to:

```bash
make price-source-probe
make price-source-lock
make price-source-lock-check
```

The probe may contact the network and should report availability and schemas without publishing a release.

The source lock must pin every successful source snapshot by:

- source ID;
- resolved URL;
- SHA-256;
- byte size;
- retrieval timestamp;
- parser version;
- observed period range;
- source/base metadata.

Unavailable sources must be recorded with warning codes and evidence, not omitted invisibly.

A source lock is valid when at least one declared source was successfully pinned and every pinned snapshot passes integrity checks. Candidate release generation will independently require source coverage for every emitted month.

### 3. Canonical normalized source table

Produce one deterministic normalized table with at least:

```text
source_id
period
source_index
source_base_or_vintage
value_status
source_snapshot_sha256
parser_id
```

Rules:

- `period` is the first day of the represented month;
- values are finite and positive;
- source-period is unique;
- original values are not rebased in this table;
- sort deterministically by period and source ID;
- preserve all successfully parsed observations rather than truncating sources merely to mimic old notebook display ranges, except where the approved historical INDEC cutoff is part of the declared method.

Emit a source coverage report and overlap matrix.

### 4. Candidate-v1 composite

Implement exactly the approved method in `docs/PRICE_METHOD_DECISION_RECORD_V1.md`:

- source order from `contracts/source_registry.json`;
- `log10` source levels;
- sequential mean overlap offsets;
- monthly row mean across available aligned log levels;
- normalization to `2016-01 = 100`;
- legacy-compatible monthly-change calculation from available non-zero source percentage changes;
- source count and source identity evidence per row.

Do not tune the method or replace it with a modern alternative in this task.

Add deterministic tests for:

- two overlapping sources with known offset;
- partial source availability;
- a month with one source;
- a month with no source, which must fail emission;
- base-level invariance under multiplicative rescaling of one source when overlap alignment is available;
- source-order identity recorded in the method manifest;
- nonpositive and nonfinite input rejection;
- conflicting duplicate rejection;
- stable byte-equivalent output from pinned fixtures.

### 5. Separate derived products

Produce separate artifacts or clearly distinct files for:

1. monthly candidate core;
2. projected extension, when requested explicitly;
3. daily quadratic interpolation, when requested explicitly;
4. quarterly mean with the historical middle-month-day-15 label.

Projection must not be generated by default during the core candidate build. Add a named flag/config and preserve the historical six-month last-six-month-mean rule only as `synthetic_projection`.

Interpolation rows are `interpolated`; quarterly rows are `derived_aggregate`.

### 6. Candidate release envelope

Create an immutable directory under a generated path such as:

```text
artifacts/price_releases/<release-id>/
```

At minimum include:

```text
manifest.json
compatibility.json
method.json
source_lock.json
source_coverage.csv
normalized_sources.csv
monthly_composite.csv
quarterly_composite.csv
qa.json
limitations.md
checksums.sha256
```

Optional products should be absent unless explicitly requested, or live in separately identified files with their own statuses.

The manifest must use `research-artifact-manifest/v1` and declare:

```text
artifact_type: research.argentina-price-composite/v1
status: candidate
method_id: research.argentina-price-composite/legacy-compatible-v1
monetary_reference_id: research.argentina-price-composite/legacy-compatible-v1@2016-01=100
```

Record:

- producer repository and commit;
- source-lock identity;
- source snapshots and parser IDs;
- exact method/config hashes;
- files, sizes, hashes and roles;
- actual observed/derived/projected/interpolated ranges;
- warning and limitation codes;
- deterministic creation time derived from the producer commit or another declared reproducible source, not an unrecorded wall-clock dependency.

Do not claim that the composite is official or that every month has every jurisdiction.

### 7. Warning-versus-failure semantics

Implement machine-readable severity.

Hard failures include:

```text
unsafe_path
checksum_mismatch
unparseable_pinned_source
conflicting_duplicate
nonfinite_or_nonpositive_index
no_source_for_emitted_month
method_identity_mismatch
corrupted_declared_file
nondeterministic_output
```

Warnings include:

```text
source_unavailable
source_stale_relative_to_others
partial_monthly_source_coverage
source_base_changed_with_official_empalme
third_party_machine_readable_mirror
historical_source_hash_not_retained
historical_eph_price_hash_unavailable
projection_excluded_from_core
interpolation_not_observation
```

The validator must reject hard failures and return success-with-warnings for a structurally valid candidate.

Do not use warnings to conceal checksum mismatches, malformed pinned bytes, or incompatible method identities.

### 8. Consumer preflight

Expose a standard-library-only command where practical:

```bash
python -m arg_price.validate <release-directory>
```

It must validate paths, file identities, schema version, artifact type, monetary-reference identity, statuses, coverage, and hashes before pandas is imported by a downstream consumer.

Support policies such as:

```text
allow_candidate_with_warnings
require_no_projection
require_period
require_monetary_reference
```

Do not require every warning to be resolved before a candidate can be copied and consumed in research mode.

### 9. Historical EPH compatibility evidence

Create a bounded report that compares the approved code lineage with the four current annual EPH manifests.

Record the monetary-reference conclusion as:

```text
probable_by_code_lineage
research.argentina-price-composite/legacy-compatible-v1@2016-01=100
```

with the exact warning that the historical consumed artifact hash is unavailable.

Do not mutate annual EPH data or upgrade that conclusion to hash-proven lineage without evidence.

### 10. Integration bundle for canastasINDEC

Produce a small copyable integration bundle or document the exact candidate release path and manifest identity needed by `canastasINDEC`.

The bundle must include the monthly and quarterly price products, compatibility declaration, manifest, checksums, monetary-reference ID, observed/derived boundary, and warning set.

Do not edit `canastasINDEC` from this repository.

## Commands

Add a clear command surface, approximately:

```bash
make price-source-probe
make price-source-lock
make price-source-lock-check
make price-candidate
make price-candidate-check
make price-candidate-smoke
```

Keep existing snapshot verification commands intact. Do not make a network refresh run under `make check` or `make smoke` unless it consumes only pinned local fixture bytes.

## Live-source execution policy

This task explicitly authorizes bounded source contact and candidate regeneration.

Before committing generated real candidate outputs:

- show source availability and hashes;
- show row/period coverage;
- show differences against the committed legacy snapshot;
- explain base or parser changes;
- preserve old snapshot evidence;
- keep generated source bytes out of Git unless they are genuinely small, rights-compatible fixtures;
- stop on surprising historical-value changes that cannot be explained by source/base/parser evidence.

When network access is blocked, still implement and test all adapters against retained small fixtures, produce the exact probe command, and clearly identify the environmental limitation. Do not fabricate live hashes or coverage.

## Non-goals

- no new optimal composite methodology;
- no population-weighted national index;
- no substitution of another province merely to improve coverage;
- no automatic scheduled refresh;
- no official-current claim;
- no basket regeneration here;
- no poverty output;
- no automatic release approval.

## Acceptance criteria

```text
exact legacy source graph is represented in a machine-readable registry
stable discovery replaces rolling-file hard-coding where possible
successful source bytes are pinned by SHA-256
source adapters produce one deterministic normalized source table
the approved legacy-compatible monthly composite is reproducible from the source lock
partial source availability produces warnings rather than automatic failure
months with no valid source fail
derived projection/interpolation/quarterly products remain status-separated
one immutable candidate release passes its preflight validator
canastas receives a copyable price release identity, not a branch URL
historical EPH compatibility is recorded as probable-by-code-lineage with a warning
no official-statistics or automatic-approval claim is made
```

## Completion report

State:

- source pages and resolved files contacted;
- successful and failed adapters;
- source hashes, periods and bases;
- exact method identity;
- candidate release ID and path;
- core and optional product coverage;
- warnings versus hard failures;
- representative differences from the previous snapshot;
- commands run and exact results;
- files committed and generated files intentionally excluded;
- EPH compatibility conclusion;
- canastas integration handoff;
- remaining blockers for `reviewed` or `approved` status.
