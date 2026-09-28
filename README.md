# IPC Argentina — monetary-reference and conversion authority

`IPC-Argentina` is the poverty/research estate's analytical authority for **versioned monetary references and conversions**. It preserves exact source evidence from named official publishers and can build a fixed-panel analytical consensus. It is **not** an official IPC publication authority.

> **Current state:** the modern v2 candidate path is implemented. Immutable `research.argentina-price-consensus/v2` and `research.argentina-monetary-conversion/v1` candidates can be built/published with explicit coverage, lineage and maturity. Candidate availability is not scientific approval; approved-mode consumers must still honor the producer's coverage/promotion gate.

## Current product families

### Curated official panel v2

The active modern method is:

```text
exact official publisher snapshots
        ↓
publicdata.argentina-price-sources/v1
        ↓
normalized monthly source observations
        ↓
research.argentina-price-consensus/v2
        ↓
research.argentina-monetary-conversion/v1
```

The fixed panel is INDEC, CABA, Córdoba, San Luis and Neuquén. Membership is part of method identity; a missing publisher lowers coverage rather than causing opportunistic source substitution.

Coverage and approval remain distinct. In particular, two contributing members are `thin_coverage` candidate evidence, while approved-mode consumers require the governed minimum coverage declared by the v2 policy.

### Legacy-compatible v1

The historical composite and the committed `data/info/` snapshots remain compatibility/evidence surfaces. They must not be mistaken for the current governed v2 candidate path or for official observations. Projected/interpolated periods remain explicitly distinguishable from observed source periods.

## Authority boundary

This repository owns:

- exact retained source snapshots, provenance and source eligibility policy;
- the fixed-panel v2 analytical method and coverage classes;
- versioned analytical monetary-reference identities;
- deterministic consensus/conversion candidates and their manifests/checksums;
- candidate/reviewed/approved status and approved-mode eligibility;
- scheduled source/candidate maintenance.

It does **not** own:

- official IPC publication status for any jurisdiction;
- poverty basket/CBA/CBT semantics;
- EPH targets or income-model science;
- Census welfare inference;
- poverty classification or FGT.

## Consumer rule

Downstreams consume an immutable conversion release, not `data/info/*.csv`, a mutable GitHub URL or this repository's runtime. A numerical factor is unusable without exact source/target monetary references, period coverage, release identity and status.

Candidate publication intentionally remains separate from approval. A healthy scheduled run may publish a candidate that an approved-mode consumer must reject.

## Verification and operation

The modern v2 contracts live in `contracts/panel_v2.json` and the v2 implementation under `src/arg_price/`. Scheduled candidate maintenance is in `.github/workflows/scheduled-price-candidate.yml`.

Useful local verification surfaces include the repository's existing checks/tests plus the v2 audit and release validators. See `docs/V2_DELIVERY_PLAN.md` for the implemented product graph and the remaining promotion gate.

## Historical snapshot

`DATA_STATUS.json`, `computarInflacion.py`, notebooks and the old `data/info/` outputs remain valuable historical evidence. Their freshness does not determine v2 candidate maturity and they are not the preferred cross-repository interface.

## Citation

> Iglesias, M. (2021–). *IPC-Argentina*. Analytical price-reference and monetary-conversion research infrastructure.
