PY ?= python3

.PHONY: help check smoke regenerate release-fixture release-check monetary-lineage-report price-source-probe price-source-lock price-source-lock-check price-candidate price-candidate-check price-candidate-smoke test-price

help:
	@echo "IPC-Argentina command surface"
	@echo ""
	@echo "  make check       Verify the committed snapshot offline"
	@echo "  make smoke       Alias for the bounded offline snapshot check"
	@echo "  make regenerate  Attempt source-dependent data regeneration"
	@echo "  make release-fixture  Rebuild the deterministic synthetic fixture"
	@echo "  make release-check    Validate fixture manifests and compatibility"
	@echo "  make monetary-lineage-report  Report historical EPH evidence (offline)"
	@echo "  make price-source-probe       Probe declared live sources (network)"
	@echo "  make price-source-lock        Download and pin available source bytes"
	@echo "  make price-source-lock-check  Verify local pinned bytes"
	@echo "  make price-candidate          Build the copyable candidate envelope"
	@echo "  make price-candidate-check    Run consumer preflight"
	@echo ""
	@echo "Regeneration may require network access and source compatibility."

check:
	$(PY) scripts/verify_snapshot.py

smoke: check

release-fixture:
	$(PY) scripts/build_price_fixture.py

release-check:
	$(PY) scripts/validate_price_release.py fixtures/price-lineage

monetary-lineage-report:
	$(PY) scripts/monetary_lineage_report.py

regenerate:
	$(PY) computarInflacion.py

price-source-probe:
	PYTHONPATH=src $(PY) -m arg_price.cli probe

price-source-lock:
	PYTHONPATH=src $(PY) -m arg_price.cli lock

price-source-lock-check:
	PYTHONPATH=src $(PY) -m arg_price.cli lock-check

price-candidate:
	PYTHONPATH=src $(PY) -m arg_price.cli candidate

price-candidate-check:
	PYTHONPATH=src $(PY) -m arg_price.validate $$(find artifacts/price_releases -mindepth 1 -maxdepth 1 -type d | sort | tail -1) --require-no-projection --require-period 2025-07-01

price-candidate-smoke: price-candidate-check

test-price:
	PYTHONPATH=src $(PY) -m unittest discover -s tests
