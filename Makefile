PY ?= python3

.PHONY: help check smoke regenerate release-fixture release-check monetary-lineage-report

help:
	@echo "IPC-Argentina command surface"
	@echo ""
	@echo "  make check       Verify the committed snapshot offline"
	@echo "  make smoke       Alias for the bounded offline snapshot check"
	@echo "  make regenerate  Attempt source-dependent data regeneration"
	@echo "  make release-fixture  Rebuild the deterministic synthetic fixture"
	@echo "  make release-check    Validate fixture manifests and compatibility"
	@echo "  make monetary-lineage-report  Report historical EPH evidence (offline)"
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
