# Price method decision record — candidate v1

**Owner:** Matías Iglesias  
**Decision date:** 2026-08-04  
**Lifecycle authorized:** `candidate` only  
**Method identity:** `research.argentina-price-composite/legacy-compatible-v1`

## Purpose

Move from a well-documented but disconnected historical snapshot to a real, versioned analytical price artifact that can be copied into downstream release directories and validated independently.

This decision deliberately separates **artifact integrity** from **historical completeness**:

- broken bytes, unsafe paths, contradictory values, and invalid numerical outputs remain hard failures;
- incomplete historical provenance, one unavailable jurisdiction, or an unresolved old materialization hash are warnings that lower the release status but do not automatically prevent a candidate artifact from being built.

This repository remains an analytical composite producer. It does not become an official IPC authority.

## Approved source set

Use the machine-readable and discoverable sources declared in `contracts/source_registry.json`:

1. historical INDEC IPC-GBA series through the legacy cutoff;
2. national INDEC IPC from the Datos Argentina catalog;
3. the official CABA empalmed level-general workbook;
4. the official Córdoba IPC empalmed series, discovered through CKAN metadata;
5. San Luis provincial IPC, preferring official reports for authority and the IERIC workbook as the machine-readable historical-series mirror.

A source adapter must record the landing page, resolved file URL, retrieval timestamp, byte size, SHA-256, parser version, detected schema, base/vintage language, and actual period coverage.

A missing source for one month is not fatal when at least one valid declared source supports that month. The resulting row must preserve source availability and status.

## Approved legacy-compatible composite method

For candidate v1, preserve the established analytical method rather than redesigning the index:

1. parse each source as a positive monthly level index;
2. preserve each source's original level and base metadata;
3. transform source levels with `log10`;
4. align successive source series through mean log-level offsets over their overlapping observations, using the declared source order;
5. calculate the monthly composite level as the row mean of available aligned log levels;
6. normalize the composite to `2016-01 = 100`;
7. calculate monthly change from available source percentage changes using the existing non-zero-source convention;
8. retain source-count and source-identity columns in QA/provenance outputs.

This method is frozen for compatibility. A different linking or aggregation method requires a new method identity and a side-by-side comparison; it must not silently replace v1.

## Products and status boundaries

### Candidate core monthly product

Emit an immutable monthly analytical composite through the latest month supported by at least one successfully retrieved declared source.

Every row must carry or be recoverably linked to:

- `period`;
- `index`;
- `log_index`;
- `monthly_change_pct`;
- contributing source IDs;
- contributing source count;
- row status;
- method ID;
- release ID.

Rows built from official source observations are `derived_from_observed`. They are not themselves official observations.

### Projection product

The legacy six-month extension may be preserved only as a separate artifact or clearly separated table with status `projected` or `synthetic_projection`.

It must not extend the observed/composite cutoff, and downstream approved-mode consumers may reject it.

### Daily product

Quadratic interpolation may be preserved as a compatibility product with status `interpolated`. It does not create daily observations.

### Quarterly product

Use the arithmetic mean of monthly composite levels in each calendar quarter and label the row with the 15th day of the middle month, preserving the historical consumer convention.

## Monetary reference

The analytical base remains:

```text
monetary_reference_id: research.argentina-price-composite/legacy-compatible-v1@2016-01=100
```

The annual EPH artifacts may be described at candidate stage as **probably materialized in the legacy Jan-2016 composite reference**, based on the retained producer/consumer code path and comments. Until exact historical input hashes or bounded value matches are recovered, this is a warning-level inference, not hash-proven lineage.

Use:

```text
status: probable_by_code_lineage
warning: exact historical price-artifact hash unavailable
```

Do not retain `provisional:legacy-price-series-unidentified` as a reason to block all integration once the candidate v1 artifact and code-lineage evidence exist.

## Failure policy

### Hard failures

Stop publication when any of these occurs:

- unsafe or escaping artifact path;
- downloaded-byte or copied-artifact checksum mismatch;
- parser cannot establish a period/value series;
- duplicate period with conflicting values within one source snapshot;
- nonfinite or nonpositive source/composite index;
- no valid declared source for an emitted month;
- missing required manifest identity or corrupted declared file;
- method/config identity differs from the release declaration;
- output is nondeterministic from the same pinned inputs and configuration.

### Warning-level conditions

Build the candidate and record limitations when:

- one or more declared jurisdictions are unavailable;
- a source is stale relative to another;
- a source workbook/base changed but an explicit official empalmed series is used;
- historical source bytes were not retained in an earlier materialization;
- the exact historical EPH-consumed IPC hash is unavailable;
- monthly source coverage is partial but at least one valid source exists;
- San Luis requires the declared third-party machine-readable mirror;
- the projection or interpolation products exist but are excluded from the candidate core.

Warnings must be machine-readable and summarized in `limitations.md`; they do not automatically become approvals.

## Publication and promotion language

Permitted:

- “analytical composite”;
- “derived from declared official jurisdiction sources”;
- “candidate research release”;
- “projected” and “interpolated” where applicable;
- explicit warning that source coverage varies by period.

Not permitted:

- “official Argentine IPC”;
- “official provincial index” for the composite;
- representing projection or interpolation as observation;
- automatic promotion from `candidate` to `reviewed` or `approved`.

## Downstream contract

Downstream repositories consume copied immutable release directories or content-addressed archives. They must not fetch this repository's `main` branch at runtime.

A candidate consumer may accept warning-level provenance gaps when it records them. It must still reject integrity failures, incompatible monetary references, unsupported statuses, or corrupted files.

## Decisions superseded

This record answers the open decision table in `docs/PRICE_METHOD_DECISIONS_REQUIRED.md` for candidate v1. It does not erase that document's alternatives; those remain the design space for a future v2.
