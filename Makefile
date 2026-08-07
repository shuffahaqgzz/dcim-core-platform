.PHONY: help bootstrap compile lint public-safety validate-json validate-fixtures markdown-links test phase0-check preflight foundation-bootstrap foundation-artifacts foundation-images-qualify foundation-policy foundation-up foundation-stop foundation-down foundation-reset foundation-smoke foundation-recovery foundation-grafana-url foundation-supply-chain foundation-evidence-summary foundation-clean-acceptance phase2-deps phase2-test phase2-check
.PHONY: phase3-deps phase3-test service-smoke e2e service-check _service-check

PYTHON ?= python3
PHASE2_VENV ?= .venv
PHASE2_PYTHON ?= $(PHASE2_VENV)/bin/python
DCIM_STATE_HOME := $(if $(XDG_STATE_HOME),$(XDG_STATE_HOME),$(HOME)/.local/state)
DCIM_RUNTIME_ROOT ?= $(DCIM_STATE_HOME)/dcim-core-platform/runtime
export DCIM_RUNTIME_ROOT
FOUNDATION_COMPOSE := deploy/compose/dev-build/compose.yaml
FOUNDATION_ENV := $$DCIM_RUNTIME_ROOT/dev-build/runtime.env
FOUNDATION_IMAGE_ENV := $$DCIM_RUNTIME_ROOT/dev-build/images.env
FOUNDATION_IMAGE_LOCK := $$DCIM_RUNTIME_ROOT/dev-build/derived-images-lock.json
FOUNDATION_IMAGE_RECIPES := deploy/compose/derived-images/recipes.json
FOUNDATION_LICENSE_DISPOSITIONS := deploy/compose/derived-images/license-dispositions.json
FOUNDATION_PROFILES := --profile data --profile observability --profile smoke
FOUNDATION_SERVICES := postgres kafka postgres-exporter kafka-jmx-exporter prometheus grafana
FOUNDATION_COMPOSE_CMD := env -u DCIM_COMPOSE_OVERRIDE COMPOSE_PROJECT_NAME='dcim-build' docker compose --env-file "$(FOUNDATION_ENV)" --env-file "$(FOUNDATION_IMAGE_ENV)" -f '$(FOUNDATION_COMPOSE)' $(FOUNDATION_PROFILES)
FOUNDATION_SMOKE_CMD := env -u DCIM_COMPOSE_OVERRIDE COMPOSE_PROJECT_NAME='dcim-build' $(PYTHON) scripts/foundation_smoke.py
SERVICE_PROFILES := --profile data --profile observability --profile core --profile dashboard --profile workflow
SERVICE_COMPOSE_CMD := env -u DCIM_COMPOSE_OVERRIDE COMPOSE_PROJECT_NAME='dcim-build' docker compose --env-file "$(FOUNDATION_ENV)" --env-file "$(FOUNDATION_IMAGE_ENV)" -f '$(FOUNDATION_COMPOSE)' $(SERVICE_PROFILES)
SERVICE_SMOKE_EVIDENCE := $$DCIM_RUNTIME_ROOT/dev-build/evidence/service-smoke/evidence.json
E2E_EVIDENCE := $$DCIM_RUNTIME_ROOT/dev-build/evidence/e2e/evidence-e2e.json
SERVICE_CHECK_LOCK_TIMEOUT ?= 3600

help:
	@printf '%s\n' \
	  'bootstrap       Prepare a public-safe local workspace' \
	  'compile         Compile-check Python sources' \
	  'lint            Run ruff check if installed (optional, not part of phase0-check)' \
	  'public-safety   Scan tracked files for prohibited public-repo content' \
	  'validate-json   Parse schemas and validate synthetic event fixtures' \
	  'validate-fixtures Validate mandatory synthetic fixture inventory' \
	  'markdown-links  Check repository-local Markdown links' \
	  'test            Run standard-library tests' \
	  'phase0-check    Run all Phase 0 gates' \
	  'preflight       Run all Development gates' \
	  'foundation-bootstrap Create protected synthetic runtime material' \
	  'foundation-images-qualify Build, reproduce, and scan local derived images' \
	  'foundation-up   Start explicit synthetic foundation capabilities' \
	  'foundation-stop Stop containers and preserve state' \
	  'foundation-down Remove containers/networks and preserve state' \
	  'foundation-grafana-url Resolve current internal Grafana URL' \
	  'foundation-reset Interactively remove only dcim-build volumes' \
	  'foundation-smoke Run bounded synthetic fast smoke' \
	  'foundation-recovery Run restart and PostgreSQL restore checks' \
	  'foundation-supply-chain Generate external SBOM/license/vulnerability evidence' \
	  'foundation-evidence-summary Generate public-safe evidence summary' \
	  'foundation-clean-acceptance Run isolated clean-runtime acceptance' \
	  'service-smoke   Start all service profiles and run the Phase 3 smoke gate' \
	  'e2e            Run the bounded Kafka-to-dashboard E2E gate' \
	  'service-check  Run Phase 3 deps, tests, and the service smoke gate'

bootstrap:
	./scripts/bootstrap-dev.sh

foundation-bootstrap:
	$(PYTHON) scripts/foundation_bootstrap.py --runtime-root "$$DCIM_RUNTIME_ROOT"

foundation-artifacts:
	$(PYTHON) scripts/foundation_artifacts.py --runtime-root "$$DCIM_RUNTIME_ROOT"

foundation-images-qualify:
	$(PYTHON) scripts/foundation_images.py --manifest '$(FOUNDATION_IMAGE_RECIPES)' --license-dispositions '$(FOUNDATION_LICENSE_DISPOSITIONS)' --runtime-root "$$DCIM_RUNTIME_ROOT"

foundation-policy: foundation-images-qualify
	@$(FOUNDATION_COMPOSE_CMD) config --format json | $(PYTHON) scripts/foundation_policy.py --input - --runtime-root "$$DCIM_RUNTIME_ROOT" --derived-lock "$(FOUNDATION_IMAGE_LOCK)" --license-dispositions '$(FOUNDATION_LICENSE_DISPOSITIONS)' --project-name 'dcim-build'

foundation-up: foundation-artifacts foundation-supply-chain foundation-policy
	$(FOUNDATION_COMPOSE_CMD) up -d --wait --wait-timeout 180 $(FOUNDATION_SERVICES)

foundation-stop:
	$(FOUNDATION_COMPOSE_CMD) stop --timeout 60

foundation-down:
	$(FOUNDATION_COMPOSE_CMD) down --timeout 60

foundation-grafana-url:
	$(FOUNDATION_SMOKE_CMD) grafana-url

foundation-reset:
	$(PYTHON) scripts/foundation_reset.py

foundation-smoke: foundation-up
	$(FOUNDATION_SMOKE_CMD) fast

foundation-recovery: foundation-up
	$(FOUNDATION_SMOKE_CMD) recovery

foundation-supply-chain: foundation-images-qualify
	$(PYTHON) scripts/foundation_supply_chain.py --runtime-root "$$DCIM_RUNTIME_ROOT" --derived-lock "$(FOUNDATION_IMAGE_LOCK)" --license-dispositions '$(FOUNDATION_LICENSE_DISPOSITIONS)'

foundation-evidence-summary:
	$(PYTHON) scripts/foundation_evidence_summary.py --evidence-dir "$$DCIM_RUNTIME_ROOT/dev-build/evidence" --commit '$(shell git rev-parse HEAD)' --require-modes 'recovery' --require-pass --strict-commit

foundation-clean-acceptance:
	$(PYTHON) scripts/foundation_acceptance.py

compile:
	$(PYTHON) -m compileall -q scripts tests contracts connectors

lint:
	@command -v ruff >/dev/null 2>&1 && ruff check || echo "ruff not installed; skipping optional lint"

public-safety:
	$(PYTHON) scripts/check_public_repo_safety.py

validate-json:
	$(PYTHON) scripts/validate-json.py

validate-fixtures:
	$(PYTHON) scripts/validate_synthetic_fixtures.py

markdown-links:
	$(PYTHON) scripts/check_markdown_links.py

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

phase2-deps:
	@test -x "$(PHASE2_PYTHON)" || $(PYTHON) -m venv "$(PHASE2_VENV)"
	$(PHASE2_PYTHON) -m pip install "pydantic==2.9.2" "confluent-kafka==2.15.0"

phase2-test:
	@test -x "$(PHASE2_PYTHON)" || { printf '%s\n' 'Phase 2 environment unavailable; run make phase2-deps' >&2; exit 1; }
	@$(PHASE2_PYTHON) -c 'import importlib.util,sys; sys.exit(0) if importlib.util.find_spec("pydantic") else (print("Pydantic unavailable; run make phase2-deps", file=sys.stderr), sys.exit(1))'
	$(PHASE2_PYTHON) -m unittest discover -s tests/phase2 -p 'test_*.py' -v

phase3-deps:
	@test -x "$(PHASE2_PYTHON)" || $(PYTHON) -m venv "$(PHASE2_VENV)"
	$(PHASE2_PYTHON) -m pip install "pydantic==2.9.2" "fastapi==0.141.1" "starlette==1.3.1" "uvicorn[standard]==0.30.6" "asyncpg==0.30.0" "httpx==0.28.1" "prometheus-client==0.26.0" "confluent-kafka==2.15.0"

phase3-test:
	@test -x "$(PHASE2_PYTHON)" || { printf '%s\n' 'Phase 3 environment unavailable; run make phase3-deps' >&2; exit 1; }
	$(PHASE2_PYTHON) -m unittest discover -s tests/phase3 -p 'test_*.py' -v

phase2-check: phase2-deps
	scripts/phase2/kafka_host.sh -- $(PHASE2_PYTHON) scripts/phase2/check.py

service-smoke: foundation-up
	@status=0; \
	$(SERVICE_COMPOSE_CMD) up -d --wait --wait-timeout 240 || status=$$?; \
	if [ $$status -eq 0 ]; then \
	  $(PYTHON) scripts/phase3/smoke.py --output "$(SERVICE_SMOKE_EVIDENCE)" || status=$$?; \
	fi; \
	$(SERVICE_COMPOSE_CMD) stop --timeout 60 || status=$$?; \
	exit $$status

e2e: service-smoke
	@status=0; \
	$(SERVICE_COMPOSE_CMD) up -d --wait --wait-timeout 240 || status=$$?; \
	if [ $$status -eq 0 ]; then \
	  scripts/phase2/kafka_host.sh -- $(PHASE2_PYTHON) scripts/phase3/e2e.py --output "$(E2E_EVIDENCE)" || status=$$?; \
	fi; \
	$(SERVICE_COMPOSE_CMD) stop --timeout 60 || status=$$?; \
	exit $$status

service-check:
	@mkdir -p "$$DCIM_RUNTIME_ROOT/dev-build"
	@flock --exclusive --timeout "$(SERVICE_CHECK_LOCK_TIMEOUT)" "$$DCIM_RUNTIME_ROOT/dev-build/service-check.lock" $(MAKE) --no-print-directory _service-check

_service-check: phase3-deps phase3-test service-smoke e2e
	@printf '%s\n' 'service-check: PASS (phase3-deps, phase3-test, service-smoke, e2e)'

phase0-check: compile public-safety validate-json validate-fixtures markdown-links test

preflight: phase0-check foundation-supply-chain foundation-recovery foundation-evidence-summary
