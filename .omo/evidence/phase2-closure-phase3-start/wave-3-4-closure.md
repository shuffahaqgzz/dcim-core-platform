# Wave 3 and Wave 4 closure record

## Purpose

This public-safe, synthetic-only record closes Wave 3 and Wave 4 at owner
request, pending owner review. It is closure bookkeeping only: it does not
start Wave 5 or add product behavior.

The closing gate set was run at `4160d09` on the
`feat/phase2-closure-phase3-start` branch.

## Commit inventory

| Wave | Todo | Commit(s) | Deliverable |
| --- | --- | --- | --- |
| 3 | 6 | `ddb20fa` | Added validate-and-publish stream mode while retaining the frozen batch-mode boundary. |
| 3 | 12 | `f35a3b7`, `a154b90`, `4c8219f` | Added the asset repository create/read and alias-resolution service, then corrected and clarified its evidence. |
| 3 | 13 | `50b615a`, `2f26676` | Added CMDB create/read/list, typed relationships, impact traversal, and the m0003 role-scoped migration; then made migration-error redaction fail closed and expanded HTTP tests. |
| 4 | 7 | `13c65d5`, `4160d09` | Added the bounded stream consumer as persistence owner, then corrected watermark capture and offset-assignment contracts. |
| 4 | 14 | `489d923` | Added structural core-profile compose integration for asset-repository and CMDB. |

## Previously recorded independent verification

- Todo 12: **confirmed** after evidence correction.
- Todo 13: **confirmed** after fail-closed redaction and HTTP tests.
- Todo 14: **confirmed structurally**.
- Todo 7: **confirmed** after the watermark/assign correction.

## Closing gate results

| Command | Exit | Summary |
| --- | ---: | --- |
| `make phase0-check` | 0 | PASS: 272 tests; compile, public-safety scan (331 files), JSON validation (373 files and 6 event fixtures), synthetic-fixture validation (9 mandatory fixtures), and 244 Markdown links passed. |
| `make phase2-test` | 0 | PASS: 196 tests; recovery reported PASS for all checked tables, unchanged live schema, and temporary-database cleanup. |
| `make phase3-test` | 0 | PASS: 27 tests; one Starlette/httpx deprecation warning was emitted. |
| `make foundation-policy` | 0 | PASS: six derived images reused; image qualification and foundation policy passed. |
| `.venv/bin/python -m unittest discover -s tests/phase2 -p 'test_stream_consumer*' -v` | 0 | PASS: 9 stream-consumer tests. |
| `python3 -m compileall -q services scripts` | 0 | PASS: no output. |
| LOC ceiling loop for `asset-repository cmdb api analytics workflow` | 0 | PASS: asset-repository 298/500; cmdb 279/500; api 230/500; analytics 18/500; workflow 18/500. |
| `git ls-files '*.sql'` | 0 | No tracked SQL files found. |
| `git ls-files --others --exclude-standard '*.sql'` | 0 | No untracked SQL files found. |
| `grep -n "ports:" deploy/compose/dev-build/compose.yaml` | 1 | No published `ports:` entry found; expected no-match guardrail result. |
| `grep -rn "pytest" Makefile services/` | 1 | No pytest reference found; expected no-match guardrail result. |
| `grep -rni "sqlalchemy" services/ scripts/` | 1 | No SQLAlchemy reference found; expected no-match guardrail result. |
| `grep -nE ">=|~=" services/*/pyproject.toml` | 0 | Five matches, all `requires-python = ">=3.12"`; no dependency-range match was reported. |
| `git diff --quiet docs/governance/CONDITIONS-REGISTER.md docs/phase0/staging-handover-contract.md` | 0 | Protected governance and staging-handover files were unchanged. |

For grep guardrails, exit 1 means the searched pattern was absent; those
results are recorded as observed rather than rewritten as command success.

## Carried-forward limitations

- Todo 7 offset/watermark contracts are proven only against fake consumers;
  live Kafka round-trip is todo 10/19 scope.
- Todo 14 is structural-only: no `docker compose up --wait`, no in-network
  HTTP probe, and no live Prometheus scrape were performed for its
  verification.
- Todo 13 exposes create/read/list plus relationships and impact; it does not
  expose update/delete.
- The internal-token boundary is a Development-scoped static token. Full
  ADR-0007:160 identity/token-lifecycle evidence remains pending.
- `make preflight` requires recovery evidence bound to the exact commit. Stale
  receipts were archived under the protected runtime root outside Git; this
  recurring gate friction is worth an owner decision.

## Explicit non-claims

- No condition is closed. C-01, C-06, C-07, and C-09 remain **OPEN**.
- This record does not mark `DEV-APPROVED`.
- This record makes no Phase 2 completion claim; todo 20 owns that claim.
- This record makes no Phase 3 completion claim.
- This record makes no Staging, Production, HA, or SLA claim.

## Next unstarted work

Wave 5 remains unstarted: todos 10, 15, 16, and 17. Subsequent work remains
todos 18, 19, 20, and 21, followed by F1-F4. None of those items is started or
checked by this closure record.
