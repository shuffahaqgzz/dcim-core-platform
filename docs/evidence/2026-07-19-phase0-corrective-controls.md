# Evidence — Phase 0 Corrective Controls

- Governing specification: [#5](https://github.com/shuffahaqgzz/dcim-core-platform/issues/5)
- Corrective implementation issue: [#3](https://github.com/shuffahaqgzz/dcim-core-platform/issues/3)
- Base: merge commit PR #2 (`11fc8c6657e937f4b76ebe10bb35b29e1eb354b0`)
- Corrective verification subject: PR #4 head `1cba7642ddda54562871a8c7e7e96dfedaf2004e`, merged as `f7b0d63`; both commits have the same tree.
- Remote exact-head checks: preflight [run 29699743959](https://github.com/shuffahaqgzz/dcim-core-platform/actions/runs/29699743959), dependency review [run 29699743954](https://github.com/shuffahaqgzz/dcim-core-platform/actions/runs/29699743954), dan public safety [run 29699743956](https://github.com/shuffahaqgzz/dcim-core-platform/actions/runs/29699743956); all PASS on the corrective head.
- Binding rule: any change after `1cba7642ddda54562871a8c7e7e96dfedaf2004e` invalidates prior local results, remote results, owner-decision binding, security verdict, dan governance verdict for the changed tree. Full revalidation is required.
- Full-history baseline run: [run 29699171363](https://github.com/shuffahaqgzz/dcim-core-platform/actions/runs/29699171363), `workflow_dispatch`, target `main` SHA `11fc8c6657e937f4b76ebe10bb35b29e1eb354b0`; checkout, project scan, dan gitleaks steps PASS.
- Status: historical local/remote corrective verification dan full-history baseline proof PASS. Public issue/PR records inspected for #4 and #5 contain no explicit exact-head owner approval of the ADR crosswalk/numbering or read-only connector policy; merge status does not infer those approvals.

## Scope

Corrective change memperbaiki structured JSON credential detection, sanitizer fail-closed behavior, fixture provenance validation, checkout credential posture, threat coverage, dan evidence semantics. Semua probes repository-authored synthetic. Tidak ada Production source, credential, endpoint, identifier, payload, log, screenshot, topology, deployment, connector activation, atau Hermes activation.

## Required evidence

| Gate | Required result |
|---|---|
| Scanner quoted/nested/malformed JSON adversarial tests | PASS local; finding value tetap redacted |
| Sanitizer key/type/preserved-field adversarial tests | PASS local; unsafe input tidak menghasilkan output |
| Fixture provenance negative tests | PASS local |
| Workflow credential and trigger invariants | PASS local |
| Python compile | PASS local |
| Unit/negative/workflow tests | PASS local; 60 tests |
| JSON/contract validation | PASS local; 12 JSON files / 6 event fixtures |
| Fixture inventory/provenance | PASS local; 9 mandatory fixtures |
| Public-safety exact-tree scan | PASS local; 122 files |
| Markdown local links | PASS local; 35 links |
| `make preflight` | Historical local and remote PASS on recorded corrective head; changed trees require rerun |
| PR checks | PASS on exact corrective head; run subjects recorded above |
| Full-history secret scan | PASS; separate `workflow_dispatch` against recorded `main` SHA |
| Owner decisions | NOT EVIDENCED in inspected public issue/PR records; explicit exact-head decisions still required |
| Independent review | Historical PASS stated for exact corrective head; any changed tree requires new independent verdicts |

## Limits

C-02 tetap `IN PROGRESS`; C-05 tetap `OPEN`. Evidence ini bukan `DEV-APPROVED`, Staging entry, Production authorization, source authorization, runtime separation proof, atau connector approval.

Tidak ada package, runtime dependency, container image, persistence contract, migration, deployment, atau recovery state ditambahkan. Dependency/license delta dan data migration check tidak berlaku; existing OD-06 tetap OPEN.
