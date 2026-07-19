# Evidence — Phase 0 Corrective Controls

- Issue: [#3](https://github.com/shuffahaqgzz/dcim-core-platform/issues/3)
- Base: merge commit PR #2 (`11fc8c6657e937f4b76ebe10bb35b29e1eb354b0`)
- Verification subject: immutable corrective PR head reported by GitHub checks. Exact head SHA, run URLs, owner decisions, dan independent verdict wajib direkam pada PR; perubahan setelah review membatalkan binding.
- Full-history baseline run: [run 29699171363](https://github.com/shuffahaqgzz/dcim-core-platform/actions/runs/29699171363), `workflow_dispatch`, target `main` SHA `11fc8c6657e937f4b76ebe10bb35b29e1eb354b0`; checkout, project scan, dan gitleaks steps PASS.
- Status: local corrective verification dan full-history baseline proof PASS; pending exact-head remote checks, owner decisions, dan independent review.

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
| `make preflight` | PASS local; remote exact-head run pending |
| PR checks | Pending exact corrective head |
| Full-history secret scan | PASS; separate `workflow_dispatch` against recorded `main` SHA |
| Owner decisions | ADR crosswalk + read-only policy recorded untuk exact corrective head |
| Independent review | PASS sebelum merge; no Critical/High open finding |

## Limits

C-02 tetap `IN PROGRESS`; C-05 tetap `OPEN`. Evidence ini bukan `DEV-APPROVED`, Staging entry, Production authorization, source authorization, runtime separation proof, atau connector approval.

Tidak ada package, runtime dependency, container image, persistence contract, migration, deployment, atau recovery state ditambahkan. Dependency/license delta dan data migration check tidak berlaku; existing OD-06 tetap OPEN.
