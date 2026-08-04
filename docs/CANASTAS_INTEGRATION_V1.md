# canastasINDEC candidate handoff

Copy the complete content-addressed directory printed by `make price-candidate`.
The directory—not a branch URL—is the integration unit. It contains monthly and
quarterly products, `manifest.json`, `compatibility.json`, and
`checksums.sha256`. Before reading it, run:

```bash
PYTHONPATH=src python -m arg_price.validate artifacts/price_releases/<release-id> \
  --require-no-projection \
  --require-monetary-reference research.argentina-price-composite/legacy-compatible-v1@2016-01=100
```

Consumers must retain the candidate status and warning set. The core ends at
the declared derived-from-observed boundary; it includes neither projection nor
interpolation. This handoff does not modify or automatically approve canastas.
