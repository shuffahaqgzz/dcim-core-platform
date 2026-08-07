# services/

Five DCIM Core Platform service boundaries live here.

| Service | Package | API group | Purpose |
|---|---|---|---|
| cmdb | dcim_cmdb | `/api/v1/cis` | Configuration-item identity, relationships, history |
| asset-repository | dcim_asset_repository | `/api/v1/assets` | Stable physical/logical asset identity and lifecycle |
| api | dcim_api | `/api/v1/dashboard` + gateway | NOC dashboard gateway and public API façade |
| analytics | dcim_analytics | `/api/v1/analytics` | Health, capacity, freshness, completeness, quality |
| workflow | dcim_workflow | `/api/v1/workflows` | Notifications, drafts, approval simulation, dry-run |

Stack per ADR-0024: Python 3.12, FastAPI, Pydantic v2. Each service owns `pyproject.toml`, `src/dcim_<service>/`, and a `tests/` directory to be introduced as it develops.

Phase 0 scaffolds have no source connection, credentials, runtime state,
FastAPI app instantiation at import, DB/network clients, or server start.
Implemented services retain the import-time rule and acquire runtime resources
only through their application lifespan.

## Development internal-token pattern

Services copy the small dependency pattern from
`api/src/dcim_api/auth.py`. When `DCIM_AUTH_REQUIRED=true`, app creation reads
`INTERNAL_API_TOKEN_FILE` (default `/run/secrets/internal-api-token`) and fails
closed if the file is unavailable or empty. Every `/api/*` router attaches the
token dependency and returns 403 unless `X-Internal-Token` matches. `/health`,
`/ready`, and `/metrics` do not attach that dependency. Tokens are never
accepted from an inline environment variable, command argument, log, or error
message.

`.sql` files are prohibited anywhere under `services/` (and the whole repository). The public-safety scanner blocks them and the rule is not allowlistable; migrations must be Python modules or JSON/YAML.

Run the repo gate:

```bash
make phase0-check
```
