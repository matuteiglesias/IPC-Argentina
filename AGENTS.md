# AGENTS.md — IPC Argentina analytical index

## Mission

Maintain a versioned composite price-index artifact with an explicit boundary between observed inputs, projected months, interpolation, and generated outputs.

This repository is an analytical construction. It is not the official IPC authority of any jurisdiction and must not imply that a future-dated artifact or configured workflow proves current official data.

## Authority boundary

Matías owns source selection, linking methodology, base-period decisions, projection policy, publication framing, and approval of any regenerated series.

Agents may:

- improve offline snapshot verification and provenance;
- repair a reproduced transformation defect;
- update source adapters or methodology only under an explicit task;
- prepare a source-compatibility or regeneration report.

Agents must not independently:

- change the observed/projected cutoff;
- replace an input series or jurisdiction;
- change linking, normalization, interpolation, or projection methodology;
- describe projections as observations;
- claim automation or source freshness from repository activity;
- regenerate and commit data merely to make dates look current;
- modify downstream `canastasINDEC` or other consumers.

## Data-status contract

`DATA_STATUS.json` is the declared status of the committed snapshot.

Update it only with evidence from the exact artifact and run being accepted. Keep separate:

- latest observed source month;
- first projected month;
- artifact maximum date;
- last successful pipeline execution;
- workflow configuration state;
- source compatibility and known limitations.

A successful local verifier proves consistency with the declaration; it does not prove official-source freshness or methodological validity.

## Commands

Safe default:

```bash
make check
make smoke
```

Both run the bounded offline snapshot verifier.

Consequential and source-dependent:

```bash
make regenerate
```

Do not run `make regenerate` unless the task explicitly authorizes network/source access and inspection of all resulting data, figures, metadata, and status changes.

There is intentionally no generic `make run` and no broad cleanup target.

## Generated artifacts

The versioned outputs under `data/info/` and figure paths are generated analytical artifacts.

Do not hand-edit rows, projected tails, indices, rates, dates, or figures. Fix the source logic or approved input, rerun, verify, and record provenance.

Do not delete old evidence or replace the snapshot without reviewing downstream compatibility.

## Change discipline

- Prefer a bounded verifier or source-adapter repair over a methodology rewrite.
- Preserve observed versus projected labels through every output.
- Record exact source URLs/files, access dates, vintages, bases, and transformations.
- Treat source outages and changed formats as explicit blocked states.
- Do not add current-data badges, automatic-update claims, or schedules without verified operational evidence.
- Do not choose a software or data license without reviewing source and derived-data rights separately.

## Completion report

```text
Changed:
Methodology changed:
Sources contacted:
Observed cutoff:
Projected cutoff:
Artifact maximum date:
Commands run:
Outputs changed:
DATA_STATUS changed:
Downstream compatibility checked:
Blocked:
Next:
```
