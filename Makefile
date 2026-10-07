PY ?= python3

.PHONY: help check smoke regenerate release-fixture release-check monetary-lineage-report price-source-probe price-source-lock price-source-lock-check price-candidate price-candidate-check price-candidate-smoke price-v2-build price-v2-check price-v2-approved-check price-v2-audit indec-regional-lock indec-regional-build indec-regional-check indec-regional-coverage indec-regional-test test-price

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
	@echo "  make price-candidate          Build the legacy-compatible candidate envelope"
	@echo "  make price-candidate-check    Run legacy-compatible consumer preflight"
	@echo "  make price-v2-build           Build normalized sources + v2 consensus + conversion from SOURCE_LOCK"
	@echo "  make price-v2-check           Validate all three v2 candidate releases independently"
	@echo "  make price-v2-approved-check  Require latest v2 consensus month to have >=3 contributors"
	@echo "  make price-v2-audit           Compare v1/v2 common support and bounded robustness diagnostics"
	@echo "  make price-v2-promote         Materialize approved children from an explicit owner decision"
	@echo "  make price-v2-package-approved Package an approved conversion for immutable transport"
	@echo "  make indec-regional-lock      Pin official INDEC regional-division CSV + metadata (network)"
	@echo "  make indec-regional-build     Build direct official regional-division release from its lock"
	@echo "  make indec-regional-check     Validate a real release incl. contiguous 2018-05..2025-12 coverage"
	@echo "  make indec-regional-coverage  Print coverage/identity diagnostics for a release"
	@echo "  make indec-regional-test      Run synthetic regional-division tests offline"
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

price-v2-build:
	@test -n "$(SOURCE_LOCK)" || (echo "SOURCE_LOCK is required" >&2; exit 2)
	PYTHONPATH=src $(PY) -m arg_price.cli v2-build --lock "$(SOURCE_LOCK)" --output-root artifacts/price_v2

price-v2-check:
	@set -eu; \
	for kind in normalized consensus conversion; do \
		d=$$(find "artifacts/price_v2/$$kind" -mindepth 1 -maxdepth 1 -type d | sort | tail -1); \
		test -n "$$d" || (echo "missing v2 $$kind release" >&2; exit 2); \
		PYTHONPATH=src $(PY) -m arg_price.v2_validate "$$d"; \
	done

price-v2-approved-check:
	@set -eu; \
	d=$$(find artifacts/price_v2/consensus -mindepth 1 -maxdepth 1 -type d | sort | tail -1); \
	test -n "$$d" || (echo "missing v2 consensus release" >&2; exit 2); \
	PYTHONPATH=src $(PY) -m arg_price.v2_validate "$$d" --require-approved-latest

price-v2-audit:
	@test -n "$(V2_NORMALIZED)" -a -n "$(V2_CONSENSUS)" || (echo "V2_NORMALIZED and V2_CONSENSUS are required" >&2; exit 2)
	PYTHONPATH=src $(PY) -m arg_price.v2_audit --normalized-sources "$(V2_NORMALIZED)/normalized_sources.csv" --consensus-monthly "$(V2_CONSENSUS)/monthly_consensus.csv" --output "$${AUDIT_OUTPUT:-artifacts/price_v2/audit}"

indec-regional-lock:
	PYTHONPATH=src $(PY) -m arg_price.indec_regional_divisions lock --output-root build/indec_ipc_regional_divisions

indec-regional-build:
	PYTHONPATH=src $(PY) -m arg_price.indec_regional_divisions build --lock "$(if $(REGIONAL_LOCK),$(REGIONAL_LOCK),build/indec_ipc_regional_divisions/source_lock.json)" --output-root artifacts/indec_ipc_regional_divisions

indec-regional-check:
	@test -n "$(REGIONAL_RELEASE)" || (echo "REGIONAL_RELEASE is required" >&2; exit 2)
	PYTHONPATH=src $(PY) -m arg_price.indec_regional_divisions validate "$(REGIONAL_RELEASE)" --require-engel-window

indec-regional-coverage:
	@test -n "$(REGIONAL_RELEASE)" || (echo "REGIONAL_RELEASE is required" >&2; exit 2)
	PYTHONPATH=src $(PY) -m arg_price.indec_regional_divisions coverage "$(REGIONAL_RELEASE)"

indec-regional-test:
	PYTHONPATH=src $(PY) -m unittest tests.test_indec_regional_divisions

test-price:
	PYTHONPATH=src $(PY) -m unittest discover -s tests

.PHONY: price-v2-promote price-v2-package-approved

price-v2-promote:
	@test -n "$(V2_CONSENSUS)" -a -n "$(V2_CONVERSION)" -a -n "$(PROMOTION_DECISION)" -a -n "$(AUDIT_SUMMARY)" || (echo "V2_CONSENSUS, V2_CONVERSION, PROMOTION_DECISION and AUDIT_SUMMARY are required" >&2; exit 2)
	PYTHONPATH=src $(PY) -m arg_price.v2_promote \\
		--consensus-candidate "$(V2_CONSENSUS)" \\
		--conversion-candidate "$(V2_CONVERSION)" \\
		--decision "$(PROMOTION_DECISION)" \\
		--audit-summary "$(AUDIT_SUMMARY)" \\
		--output-root "$${APPROVED_OUTPUT_ROOT:-artifacts/price_v2/approved}"

price-v2-package-approved:
	@test -n "$(V2_APPROVED_CONVERSION)" || (echo "V2_APPROVED_CONVERSION is required" >&2; exit 2)
	$(PY) scripts/package_v2_approved.py "$(V2_APPROVED_CONVERSION)" \\
		--output "$${APPROVED_PUBLICATION_OUTPUT:-build/approved-publication}"
