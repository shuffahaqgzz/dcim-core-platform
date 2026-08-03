# ADR-0024: Python/FastAPI Service Language Baseline

- Status: Accepted
- Date: 2026-07-28
- Owner: shuffahaqgzz
- Decision reference: OD-07
- Decision source: owner confirmation 2026-07-28 (`docs/research/PRD.md` §7 Q2)
- Related ADRs: [ADR-0017](0017-react-noc-dashboard-frontend.md) (frontend), [ADR-0019](0019-apache-2-0-repository-license.md) (license), [ADR-0007](0007-cmdb-implementation-for-development.md) (CMDB)

## Context

OD-07 was the open decision blocking implementation of the core service
boundaries: `services/{cmdb,asset-repository,api,analytics,workflow}` and the
`web/` frontend. The owner confirmed on 2026-07-28 that the backend services use
Python with FastAPI and Pydantic v2, while the frontend continues with the
React + TypeScript + Vite stack already selected in ADR-0017. This decision
locks the service language baseline so Phase 1–2 scaffolds and vertical slices
can proceed without revisiting the stack.

## Decision drivers

- Consistency with the existing ingestion and analytics Python ecosystem in the
  satellite repositories.
- First-class, type-safe REST contract support via FastAPI + Pydantic v2 for
  the canonical event envelope and Asset/CI schemas.
- Single backend language across the five core services, reducing context
  switching for the solo-to-small-team operating model.
- Clear language boundary between backend services (Python) and the NOC
  dashboard (`web/` — TypeScript/React).
- Reuse the existing repository tooling: Python 3.12, `ruff` (`ruff.toml`,
  py312, line-length 120), and the stdlib `unittest` gate runner.
- The public-safety scanner forbids `.sql` files; therefore migrations must be
  expressible in a form that passes the gate.

## Decision

Adopt the following service language baseline for the DCIM Core Platform
services:

1. **Backend services.** `services/{cmdb,asset-repository,api,analytics,workflow}`
   use **Python 3.12**, **FastAPI**, and **Pydantic v2**. Each service owns its
   own `pyproject.toml` with exact, pinned dependency versions (no version
   ranges). Distribution names use hyphens (`dcim-<service>`), package names
   use underscores (`dcim_<service>`).
2. **Frontend.** `web/` uses **TypeScript + React + Vite** as specified in
   ADR-0017; this decision reaffirms ADR-0017 and does not introduce a new
   frontend stack.
3. **Linter.** `ruff` is the linter/formatter, configured from the root
   `ruff.toml` (Python 3.12 target, line-length 120). Services extend the root
   configuration rather than inventing a new style.
4. **Test runner split.** The repository gate (`make phase0-check`) continues to
   run stdlib `unittest` over `tests/`. Service-level `pytest` is allowed once a
   service's dependencies are installable outside the zero-dependency Phase 0
   gate.
5. **Standard service layout.** Every service carries:
   - `README.md` — purpose, owning ADRs, planned API group, local commands,
     and the "no source connection, no credentials, no runtime state" Phase 0
     statement.
   - `pyproject.toml` — `[project] name = "dcim-<service>"`,
     `requires-python = ">=3.12"`, pinned exact dependencies, and a
     `[tool.ruff]` block that extends the root configuration.
   - `src/dcim_<service>/__init__.py` — package marker.
   - `src/dcim_<service>/main.py` — a placeholder module that exports only a
     docstring and a side-effect-free factory (`create_app()` or `describe()`);
     no FastAPI instantiation at import time, no network or database clients,
     no `if __name__ == "__main__"` server start.
   - `tests/` — service-level tests, introduced as the service develops.
6. **Pinned dependencies.** All production and development dependencies in each
   `pyproject.toml` are declared with exact versions. Version ranges are not
   permitted; upgrades are explicit, reviewed changes.
7. **No `.sql` migrations.** Database migrations and schema definitions are
   expressed as Python modules (e.g., Alembic-style) or as JSON/YAML fixtures.
   **`.sql` files are prohibited.** The repository public-safety scanner
   (`scripts/check_public_repo_safety.py`) lists `.sql` in `FORBIDDEN_SUFFIXES`
   and the `forbidden-extension` rule is not allowlistable
   (`ALLOWLISTABLE_RULES` is empty), so `.sql` files can never be committed.
   This is a durable constraint, not a temporary Phase 0 restriction.
8. **Phase 0 scaffolds contain no runtime code.** The initial scaffold files
   import only the standard library and declare functions. They do not open
   sockets, instantiate HTTP clients, connect to databases, or start servers.
   Import-time side effects are forbidden.

## Options considered

### 1. Go (rejected)

Go would align with the compiled/binary mindset of some foundation components,
but it splits the team skill set away from the existing ingestion and analytics
Python code. More importantly, Pydantic-class schema ergonomics for the
contract-heavy Asset/CI domain are weaker in Go, and the repository would need
a second backend toolchain before the first vertical slice is complete.

### 2. TypeScript / NestJS (rejected)

TypeScript would reuse the frontend language, but it fragments the backend from
the analytics/ingestion Python ecosystem and from the existing repository Python
tooling. NestJS also adds a runtime and dependency surface that does not match
the Phase 0 zero-dependency gate.

### 3. Python / FastAPI / Pydantic v2 (selected)

Selected per owner confirmation. It gives one backend language across the core
services, strong contract-driven APIs, and direct reuse of the team's Python
investment.

## Security impact

- No secrets, endpoints, or credentials are present in Phase 0 scaffold files.
- Dependencies are pinned to reduce supply-chain drift; license and provenance
  are recorded when the dependency is introduced.
- The `.sql` prohibition is enforced by the public-safety scanner; migration
  logic remains reviewable as Python/JSON/YAML.

## License impact

Project code is licensed under Apache-2.0 per ADR-0019. The licenses of runtime
dependencies (FastAPI, Pydantic, Starlette, and any future service libraries)
are recorded in the dependency inventory when those dependencies are
introduced, not during the Phase 0 scaffold. The dependency inventory is the
authoritative source for third-party license obligations.

## Resource and operational impact

- Python 3.12 services run as standard ASGI/WSGI processes; memory and CPU
  characteristics are bounded by the foundation plane limits defined in
  ADR-0021.
- Pydantic v2 provides a single validation layer for request/response schemas
  and event contract parsing.
- `ruff` is the only linting dependency required for Phase 0 scaffolding; it is
  installed outside the gate when available.

## Migration and rollback

- Services are independently replaceable; a future decision to move one service
  to another language would only require that service's ADR addendum.
- Database migrations live as Python modules (or JSON/YAML) under each service
  boundary, so they are versioned, reviewed, and scanner-safe.
- Rollback of a migration is a migration module revert; there is no reliance on
  `.sql` deltas stored in the repository.

## Acceptance evidence

- This ADR is marked `Accepted` and dated 2026-07-28.
- The five service scaffolds match the standard layout and contain no runtime
  code, no `.sql` files, and no secrets.
- `make phase0-check` passes on the repository head.
- The public-safety scanner accepts the scaffold tree.

## Revalidation triggers

- A proposal to change the backend language for any of the five core services.
- A major FastAPI or Pydantic v3 migration that breaks the contract pattern.
- A change to the public-safety scanner rules that makes the `.sql`
  prohibition allowlistable or removes it.
- Phase 2 vertical slice evidence that demonstrates a material runtime cost or
  security issue traceable to the chosen stack.
