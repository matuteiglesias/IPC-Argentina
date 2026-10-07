# IPC-Argentina v2 delivery plan

Status: **candidate system implemented; scientific promotion/review remains open**  
Tracking issue: **#18 — review/promote curated official-panel v2 for approved-mode use**

W0-W4 and the scheduled candidate/publication mechanics are implemented on `main`: fixed panel/policy contracts, exact source adapters including Neuquén, normalized source/consensus/conversion builders, validators and immutable candidate packaging. The remaining gate is scientific review/promotion, including review of the v1↔v2 audit and explicit approved-mode eligibility. Candidate health must not be rewritten as approval. `make price-v2-promote` now provides only the mechanical half of promotion: it requires an owner-supplied `argentina-price-v2-promotion-decision/v1` record that pins the exact candidate manifest hashes and exact audit-summary hash. The command cannot create or infer that decision.

## Mission

`IPC-Argentina` v2 will have two deliberately separate responsibilities:

1. preserve exact, provenance-rich price-index source releases from a fixed set of named publishers; and
2. publish one explicit, bounded, reproducible Argentine multi-source price reference for estate consumers.

The repository does **not** become an official CPI authority. Its official publishers remain authoritative for their own observations. The v2 consensus is an analytical research product.

`legacy-compatible-v1` remains immutable compatibility evidence. v2 receives a new method identity and must be compared side by side before promotion.

## Fixed official panel

The first v2 panel is fixed by method identity:

- INDEC;
- CABA;
- Córdoba;
- San Luis;
- Neuquén.

Availability does not change membership. Other official provincial series may be catalogued and preserved, but they do not automatically replace a missing panel member. A future private-index panel is a separate product family.

## INDEC source eligibility

Observations are retained even when they are excluded from the consensus.

| Interval | v2 panel treatment |
| --- | --- |
| through 2006-12 | historical INDEC/GBA may be eligible |
| 2007-01 through 2015-12 | preserve as source evidence; `excluded_by_policy` from consensus |
| 2016 | explicit transition interval; no automatic splice |
| from 2017-01 | modern INDEC national may be eligible |

The exact calendar is machine-readable and part of method identity. Changing it requires a new policy revision and scientific comparison.

## Product graph

```text
exact publisher snapshots
        ↓
publicdata.argentina-price-sources/v1
        ↓
normalized monthly source series
        ↓
research.argentina-price-consensus/v2
        ↓
research.argentina-monetary-conversion/v1
```

The normalized source product is independently useful. Normal estate consumers should consume the governed consensus/conversion product rather than reproduce panel-selection logic.

## Coverage semantics

Consensus rows preserve the panel denominator and the exact contributing members.

| Contributing eligible members | Coverage class | Default consumer semantics |
| ---: | --- | --- |
| 5 | `full_panel` | eligible |
| 4 | `strong_coverage` | eligible |
| 3 | `acceptable_coverage` | eligible |
| 2 | `thin_coverage` | candidate/diagnostic only |
| 0–1 | no consensus row | unavailable |

Approved-mode downstream use should require at least three members unless a consumer explicitly declares another policy.

## W0 — Constitution and contracts

Freeze the v2 scientific boundary before implementing live transformations.

Required:

- new method/panel identity;
- fixed five-member roster;
- machine-readable eligibility calendar;
- source-period statuses such as `eligible`, `excluded_by_policy`, `unavailable`, `break_unresolved`;
- coverage classes above;
- normalized-source, consensus and conversion schemas;
- explicit statement that v2 does not mutate v1.

**DoD:** fixture contracts can represent every allowed status and reject dynamic panel substitution.

## W1 — Source registry and exact adapters

Promote the source layer into a durable first-class product.

Required:

- add Neuquén with exact official discovery/retrieval surfaces and methodology/base metadata;
- harden INDEC, CABA, Córdoba and San Luis adapters;
- retain downloaded bytes, resolved URL, retrieval timestamp, byte size, SHA-256 and parser revision;
- preserve official base/method breaks and declared official empalmes;
- mirrors remain explicit mirrors and never silently become statistical authority;
- one dynamic source is acquired once per run and the exact acquired bytes become the lock evidence.

**DoD:** one relocatable source-lock bundle reproduces all reachable retained source observations after copying to a different filesystem location.

## W2 — Normalized source release

Build a consumer-neutral monthly source surface before averaging anything.

Minimum fields:

```text
source_id
period
published_index_level
published_base_or_vintage
monthly_inflation_pct
eligibility_status
source_snapshot_sha256
parser_id
break_or_empalme_status
```

Monthly inflation is computed only where two consecutive observations form an admissible within-source comparison. A method/base break cannot be bridged merely because both sides have numbers.

No consensus is built in W2.

**DoD:** exact source locks deterministically produce an independently validatable normalized-source release.

## W3 — Consensus kernel

The primary v2 statistic is intentionally simple:

```text
consensus_monthly_inflation
    = equal-weight arithmetic mean
      of eligible available panel-member monthly inflation rates
```

No hidden source weights. No opportunistic replacement source.

Every month also emits:

- contributing source IDs;
- source count;
- excluded/unavailable member IDs and reasons;
- minimum and maximum source inflation;
- standard deviation (or another frozen dispersion statistic);
- median as a diagnostic, not the reference estimator;
- coverage class.

The monthly rates are chained into an analytical reference index. `2016-01 = 100` may remain the scale convention, but this base does not imply that INDEC is an eligible January-2016 observation.

**DoD:** same source parent + same method config produces byte-identical consensus output; no emitted row has fewer than two contributors.

## W4 — Governed consensus and conversion releases

Emit immutable release directories for:

- `research.argentina-price-consensus/v2`;
- `research.argentina-monetary-conversion/v1` derived from the approved/candidate consensus parent.

A release must retain:

- normalized-source parent identity;
- panel/method identity;
- eligibility-policy revision;
- source availability and coverage by period;
- dispersion diagnostics;
- warnings and limitations;
- manifest and checksums.

Projection and interpolation are separate optional artifacts. They never extend the observed consensus cutoff silently.

**DoD:** a copied release can validate and apply period-to-period monetary conversion without importing this repository or fetching `main`.

## W5 — Scientific comparison with v1

Do not promote v2 merely because it is cleaner software.

Compare v1 and v2 across common support:

- monthly rate differences;
- cumulative index differences;
- source-count history;
- 2007–2015 behavior;
- one-member-drop sensitivity;
- source break/empalme sensitivity;
- arithmetic mean versus log/geometric aggregation as a bounded robustness check;
- effect on representative downstream conversions.

The comparison must explain why v2 is fit or not fit for promotion. It must not redefine v1.

## W6 — Scheduled maintenance

Monday convergence should eventually perform:

```text
acquire each panel source once
        ↓
verify relocatable exact source lock
        ↓
materialize normalized source candidate
        ↓
materialize v2 consensus candidate
        ↓
validate provenance / coverage / dispersion
        ↓
publish candidate evidence
```

A missing panel member lowers coverage; it does not trigger dynamic substitution. Scientific `candidate → reviewed → approved` promotion remains manual.

Health and maturity stay separate. Source acquisition may be green while a latest-period consensus is only `thin_coverage` and therefore scientifically blocked for approved consumers.

## W7 — Downstream handoffs

Build independent-copy consumer proofs for:

- `income-modeling-eph`;
- `encuestador-de-hogares`;
- `canastasINDEC`.

Consumers pin immutable parent identity and validate period, status and monetary-reference semantics. They do not import the IPC working tree and do not fetch mutable repository URLs at runtime.

## Future wave — private panel

A later product may support a separately governed fixed roster of respected private price indices. It receives its own panel/method identity and can be compared against the official panel.

Private sources are never pulled opportunistically to fill missing official-panel members.

## Global invariants

- publisher observation != analytical consensus;
- panel membership is fixed by method version, not current availability;
- excluded INDEC periods remain independently inspectable;
- no silent bridge across unresolved source methodology/base changes;
- no automatic province substitution;
- no projection masquerades as observation;
- no automatic scientific promotion;
- v2 never mutates v1;
- every downstream numerical conversion identifies the exact consensus release that authorizes it.

## Final definition of done

The first v2 is ready for governed use when:

1. all five panel members have explicit source/adaptor/provenance definitions, even if one is temporarily unavailable;
2. a real exact source-lock parent produces a deterministic normalized-source release;
3. that release produces a deterministic v2 consensus with source-count and dispersion diagnostics;
4. the INDEC exclusion/transition policy is machine-enforced;
5. a conversion release validates after independent copying;
6. v1 versus v2 comparison has been reviewed;
7. scheduled maintenance rebuilds candidate evidence without dynamic source substitution; and
8. each accepted consumer period has at least `acceptable_coverage`, or the consumer is explicitly blocked.
## Explicit promotion packet

Scientific promotion is deliberately two-step.

1. Review the exact v1↔v2 audit and candidate QA outside the promotion command.
2. Only after the owner records an explicit decision, materialize immutable approved children.

The decision file must have this minimum shape:

```json
{
  "schema": "argentina-price-v2-promotion-decision/v1",
  "decision_id": "<stable review id>",
  "decision": "approved",
  "approved_by": "<owner identity>",
  "decided_at": "<UTC timestamp>",
  "candidates": {
    "consensus": {
      "release_id": "<candidate consensus release>",
      "manifest_sha256": "<exact manifest sha256>"
    },
    "conversion": {
      "release_id": "<candidate conversion release>",
      "manifest_sha256": "<exact manifest sha256>"
    }
  },
  "audit": {
    "summary_sha256": "<exact audit summary sha256>"
  }
}
```

Then run:

```bash
make price-v2-promote \
  V2_CONSENSUS=/path/to/exact/candidate-consensus \
  V2_CONVERSION=/path/to/exact/candidate-conversion \
  PROMOTION_DECISION=/path/to/owner-decision.json \
  AUDIT_SUMMARY=/path/to/audit/summary.json

make price-v2-package-approved \
  V2_APPROVED_CONVERSION=/path/to/approved-conversion
```

Promotion creates new immutable approved child identities; it never mutates candidate directories. The approved conversion points at the newly approved consensus child. The packager emits an `ecosystem-release-discovery/v1` envelope with `status=approved` and an `approved-<release_id>` transport tag.

The promotion command still fails closed if the latest consensus period is not approved-mode eligible. An agent must not fabricate the owner decision merely to satisfy this gate.
