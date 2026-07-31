# Phase 2 Resource Caps Declaration

Status: planned, not activated

ADR-0021 reserves approximately 33 GB RAM and 18 vCPU of Development-VM
headroom after the foundation allocation. Future Phase 2 application services
must fit within that remaining envelope and declare Compose resource limits
before activation.

The initial planned caps are:

| Future service class | Memory limit | CPU limit |
|---|---:|---:|
| Batch ingestion and validation | 4 GB | 2 vCPU |
| Asset/CMDB application | 4 GB | 2 vCPU |
| NOC read-model generation | 2 GB | 1 vCPU |
| Workflow draft/dry-run processing | 4 GB | 2 vCPU |
| Search and analytics allowance | 8 GB | 4 vCPU |
| Phase 2 contingency | 4 GB | 2 vCPU |
| **Planned Phase 2 maximum** | **26 GB** | **13 vCPU** |

These allocations are declarations for later service activation, not current
reservations. This vertical slice activates no long-running Phase 2 service
and makes no Production, HA, or SLA claim. Any future activation must validate
actual idle and smoke-load usage, remain within the ADR-0021 headroom, and
revisit the caps when that ADR's revalidation triggers apply.

## C-07 impact

This declaration records the Phase 2 impact on condition C-07 by assigning
planned caps within the accepted headroom. It does **not** claim that C-07 is
closed; the conditions register and its required evidence remain authoritative.

## References

- [ADR-0021: Foundation Resource Limits, Retention, and Disk Watermarks](../adr/0021-foundation-resource-limits-retention.md)
- [Phase 1 compact infrastructure foundation policy](../plan/PHASE1-COMPACT-INFRASTRUCTURE-FOUNDATION.md)
- [Conditions register](../governance/CONDITIONS-REGISTER.md)
