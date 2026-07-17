---
name: adr-decision
description: Use when a task touches an item in OPEN-DECISIONS.md or introduces a durable architecture, security, data, workflow, or technology choice.
---

# ADR Decision Workflow

1. Verify whether an accepted ADR already governs the choice.
2. If unresolved, do not implement a hidden default. Create a proposed ADR with context, decision drivers, viable options, comparison evidence, consequences, reversibility, migration, security, resource, and license impact.
3. Prefer a time-boxed spike when evidence is missing. Use synthetic workloads and record the benchmark method.
4. Mark status `Proposed`; only the owner changes it to `Accepted` or `Rejected`.
5. Link the issue, implementation PR, and superseded ADRs.
6. Update `docs/governance/OPEN-DECISIONS.md` only after the decision is explicit.
