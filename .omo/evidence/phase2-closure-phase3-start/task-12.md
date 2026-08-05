# Task 12 — Asset Repository service evidence

Date: 2026-08-05

## Scope

Implemented the synthetic Development Asset Repository boundary:

- Pydantic v2 Asset and Alias models mirror `schemas/asset.schema.json`.
- `POST`/`GET` Asset API uses `phase2.assets` and `phase2.aliases` only, with
  `dcim_assets_rw` as the default database role.
- Canonical `scripts.phase2.identity.derive_asset_id` validates identity; the
  service does not reproduce UUIDv5 semantics.
- Alias lookup uses the ADR-0020 live-window predicate and confidence/latest
  validity ordering.
- `/api/*` requires the internal token; `/health`, `/ready`, and `/metrics`
  remain exempt.

All test values are synthetic. This evidence contains no runtime credential,
endpoint, source, or operational data.

## Commands and results

| Command | Exit | Result |
| --- | ---: | --- |
| `.venv/bin/python -m unittest tests.phase3.test_asset_repository -v` | 0 | 6 Asset Repository seam tests passed. |
| `test $(find services/asset-repository/src -name '*.py' -exec cat {} + \| wc -l) -le 500` | 0 | 299 source lines; within the 500 line acceptance limit. |
| `python3 -m compileall -q services/asset-repository` | 0 | Asset Repository compilation passed. |
| `lsp_diagnostics services/asset-repository/src/dcim_asset_repository` | 0 | No diagnostics. |
| `make phase3-test` | 2 | Blocked by pre-existing out-of-scope `services/cmdb/src/dcim_cmdb/main.py`: FastAPI resolves a local `Response` forward annotation and raises `PydanticUndefinedAnnotation`. Asset Repository tests passed before the CMDB failures. |
| `make phase0-check` | 2 | Public-safety scan blocked by pre-existing out-of-scope findings in `scripts/phase2/migrate.py` and `services/cmdb/src/dcim_cmdb/main.py`; task-12 files no longer produce findings. |

## TestClient manual surface checks

- Happy path: authorized create returns 201; GET returns the same serialized
  payload; alias resolution returns only live aliases.
- Idempotency: replaying the same `asset_id` and payload returns 200.
- Failure mutation: changing the serial number while retaining the same
  `asset_id` returns 409.
- Failure mutation: setting an alias `valid_to` in the past yields no alias
  resolution result; the asserted SQL contains the required live-window
  predicate and confidence/latest-validity ordering.
- Failure mutation: missing or wrong internal token returns 403; unauthenticated
  `/health` returns 200.

## Limitations and cleanup

- No Docker-backed PostgreSQL integration was run in this sandbox.
- `make phase3-test` currently cannot reach a green repository result because of
  the separately scoped CMDB implementation. No CMDB, migration, or m0003 file
  was changed by task 12.
- No runtime artifacts, credentials, or test data remain outside temporary test
  directories.
