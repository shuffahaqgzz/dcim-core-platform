.PHONY: help bootstrap public-safety validate-json test preflight

PYTHON ?= python3

help:
	@printf '%s\n' \
	  'bootstrap       Prepare a public-safe local workspace' \
	  'public-safety   Scan tracked files for prohibited public-repo content' \
	  'validate-json   Parse schemas and validate synthetic event fixtures' \
	  'test            Run standard-library tests' \
	  'preflight       Run all repository bootstrap gates'

bootstrap:
	./scripts/bootstrap-dev.sh

public-safety:
	$(PYTHON) scripts/check-public-safety.py

validate-json:
	$(PYTHON) scripts/validate-json.py

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

preflight: public-safety validate-json test
