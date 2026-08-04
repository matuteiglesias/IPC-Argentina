PY ?= python3

.PHONY: help check smoke regenerate

help:
	@echo "IPC-Argentina command surface"
	@echo ""
	@echo "  make check       Verify the committed snapshot offline"
	@echo "  make smoke       Alias for the bounded offline snapshot check"
	@echo "  make regenerate  Attempt source-dependent data regeneration"
	@echo ""
	@echo "Regeneration may require network access and source compatibility."

check:
	$(PY) scripts/verify_snapshot.py

smoke: check

regenerate:
	$(PY) computarInflacion.py
