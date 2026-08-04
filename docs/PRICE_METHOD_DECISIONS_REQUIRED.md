# Price methodology decisions required

No option below is selected. Matías must approve any real candidate release.

| Decision | Evidence-backed alternatives | Consequences |
|---|---|---|
| Authoritative inputs and vintages | retained official national series; retained jurisdiction series; current five-source set with exact snapshots | determines authority language, coverage, reproducibility and break handling |
| Historical composite support | freeze as legacy research snapshot; support as versioned composite; retire after compatibility window | affects citations and downstream reproducibility; never converts it into official IPC |
| Linking/aggregation | preserve sequential overlap log offsets and row means; explicit splice at approved breaks; another reviewed method | can change every derived level and must be versioned as a new identity |
| Missing periods | unresolved/fail; impute by named rule; omit unavailable jurisdiction | changes coverage and uncertainty; must produce period flags |
| Projection | prohibit; publish separately; append a declared horizon | controls whether approved consumers may accept tail periods |
| Daily interpolation | quadratic as legacy; log-linear; no daily product | affects daily conversion factors; none creates daily observations |
| Base/reference | retain Jan-2016=100 analytical base; rebase new major version; named monetary references for conversion | affects factor semantics and compatibility, although rates may remain invariant |
| Annual EPH use | reject unresolved; accept reviewed conversion only; preserve a frozen legacy identifier | determines whether historical inputs can claim reproducible monetary comparability |
| Basket use | observed-only; reviewed composite; explicitly permitted projection | affects regional basket calculations and preflight rules |
| Publication language | “official source snapshot” only for unmodified retained inputs; “analytical composite” for combinations; “projection” for extensions | prevents an official-statistics or freshness claim |

Before approval, require source hashes/access dates, transformation-graph revision, period classifications, consumer preflight results, diff review of every output, and a manually promoted manifest status. `synthetic → candidate → reviewed → approved` has no automatic transition.
