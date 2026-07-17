.PHONY: help bootstrap compile public-safety validate-json validate-fixtures markdown-links test phase0-check preflight

PYTHON ?= python3

help:
	@printf '%s\n' \
	  'bootstrap       Prepare a public-safe local workspace' \
	  'compile         Compile-check Python sources' \
	  'public-safety   Scan tracked files for prohibited public-repo content' \
	  'validate-json   Parse schemas and validate synthetic event fixtures' \
	  'validate-fixtures Validate mandatory synthetic fixture inventory' \
	  'markdown-links  Check repository-local Markdown links' \
	  'test            Run standard-library tests' \
	  'phase0-check    Run all Phase 0 gates' \
	  'preflight       Alias for Phase 0 gates'

bootstrap:
	./scripts/bootstrap-dev.sh

compile:
	$(PYTHON) -m compileall -q scripts tests

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

phase0-check: compile public-safety validate-json validate-fixtures markdown-links test

preflight: phase0-check
