# Python dependency inventory

This inventory covers the exact Python pins installed by `make phase3-deps`.
Licenses use SPDX identifiers; PyPI project pages are the recorded provenance
for the named distributions.

| Dependency | Exact version | SPDX license | PyPI evidence | Purpose | Introduced by |
| --- | --- | --- | --- | --- | --- |
| pydantic | 2.9.2 | MIT | [pydantic 2.9.2](https://pypi.org/project/pydantic/2.9.2/) | Typed API boundary models | ADR-0024 Phase 0 service scaffold; installed by Todo 9 |
| fastapi | 0.115.0 | MIT | [fastapi 0.115.0](https://pypi.org/project/fastapi/0.115.0/) | ASGI API framework | ADR-0024 Phase 0 service scaffold; installed by Todo 9 |
| uvicorn[standard] | 0.30.6 | BSD-3-Clause | [uvicorn 0.30.6](https://pypi.org/project/uvicorn/0.30.6/) | ASGI service process | ADR-0024 Phase 0 service scaffold; installed by Todo 9 |
| asyncpg | 0.30.0 | Apache-2.0 | [asyncpg 0.30.0](https://pypi.org/project/asyncpg/0.30.0/) | Explicit asynchronous PostgreSQL SQL, without an ORM | Wave 2 Todo 9 (`asyncpg==0.30.0`) |
| httpx | 0.28.1 | BSD-3-Clause | [httpx 0.28.1](https://pypi.org/project/httpx/0.28.1/) | In-process ASGI tests and later internal gateway calls | Wave 2 Todo 9 |
| prometheus-client | 0.26.0 | Apache-2.0 AND BSD-2-Clause | [prometheus-client 0.26.0](https://pypi.org/project/prometheus-client/0.26.0/) | Prometheus metrics exposition | Wave 2 Todo 9 |
| confluent-kafka | 2.15.0 | Apache-2.0 | [confluent-kafka 2.15.0](https://pypi.org/project/confluent-kafka/2.15.0/) | Phase 2 Kafka producer and consumer clients | Wave 2 Todo 9 |

## Platform compatibility note

`confluent-kafka==2.15.0` publishes Linux wheels at the
`manylinux_2_28`/glibc baseline. The Development targets satisfy that floor:
Ubuntu 24.04 uses glibc 2.39, and `python:3.12-slim-bookworm` uses glibc 2.36.
This is a Development compatibility statement, not a Production-readiness
claim.
