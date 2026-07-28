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

Phase 0 rule: these directories contain **only scaffolds**. No source connection, no credentials, no runtime state, no FastAPI app instantiation at import, no DB/network clients, no server start. Dependencies are declared in `pyproject.toml` but are not installed or executed in Phase 0.

`.sql` files are prohibited anywhere under `services/` (and the whole repository). The public-safety scanner blocks them and the rule is not allowlistable; migrations must be Python modules or JSON/YAML.

Run the repo gate:

```bash
make phase0-check
```
