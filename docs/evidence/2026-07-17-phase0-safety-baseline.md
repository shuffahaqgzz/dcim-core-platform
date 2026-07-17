# Evidence — Phase 0 Safety Baseline

- UTC: `2026-07-17T05:42:08Z`
- Verified implementation/settings commit: `54783927749fb1825c2c3dad4b7bba273ac3e2a5`
- Branch: `chore/phase-0-safety-baseline`
- Issue: tidak diberikan; owner task berada di luar commit scope
- Pull request: `#2` — `https://github.com/shuffahaqgzz/dcim-core-platform/pull/2`
- Owner: `shuffahaqgzz`
- Read-only reviewers: architecture audit dan security audit agents

## Scope dan method

Commit diekspor memakai `git archive HEAD` ke isolated temporary directory. Empty local `.git/` marker mencegah parent worktree discovery, sehingga scanner memakai exact archived tree. Tiga owner-WIP files (`RTK.md`, task prompt, proposed ADR-0007) dan perubahan `AGENTS.md` tidak masuk archive/PR.

Fixture sepenuhnya repository-authored synthetic data. Reserved documentation domain/range dan explicit `SYNTHETIC-*`/`GENERIC-*` marker dipakai. Sanitization input/expected pair memakai public test vector salt `phase0-fixture-salt-v1`; bukan runtime secret.

## Commands dan results

| Command/gate | Result |
|---|---|
| `make preflight` pada clean archive | PASS; aggregate wall time sekitar 0.9 detik |
| Python compile | PASS |
| Unit/negative/workflow tests | PASS; 37 tests |
| JSON/contract validation | PASS; 12 JSON files dan 6 event fixtures |
| Synthetic fixture inventory | PASS; 9 mandatory classes |
| Public-safety scanner | PASS; 120 exact-tree files |
| Markdown local links | PASS; 33 links |
| `git check-ignore -v` private/Hermes paths | PASS pada working-tree verification |

Remote draft PR checks PASS: CI preflight, public-safety scanner, full-history gitleaks, dan official pinned dependency-review action. Latest verified dependency-review job menjalankan action secara langsung; tidak ada conditional skip.

Repository setting verification pada `2026-07-17T06:20:12Z`: visibility public; default branch `main`; private vulnerability reporting, secret scanning, push protection, Dependabot alerts, dan Dependabot security updates enabled. Ruleset `main-development-gate` active dan menargetkan `main`, tanpa bypass, dengan PR-only/squash-only, conversation resolution, linear history, deletion/force-push protection, strict up-to-date policy, serta required checks `preflight`, `dependency-review`, dan `public-safety`.

Tidak ada third-party Python dependency, package install, container image, atau new Action source ditambahkan. Existing trusted Actions tetap pinned ke full commit SHA. License OD-06 tetap OPEN.

## Review dan failure disposition

Independent read-only reviews menemukan scanner, sanitizer, evidence-scope, dan ADR traceability issues selama implementasi. Semua code/docs blocker diremediasi dan regression tests ditambahkan sebelum clean-tree run. Tidak ada active secret, private key, live payload, dump, Production identifier, atau connector/deployment path ditemukan.

## Limitations

- Local `gitleaks` tidak tersedia; remote full-history gitleaks PASS pada PR #2.
- PR tetap draft dan owner review atas ADR crosswalk, read-only policy, serta open decisions masih required sebelum merge.
- Source authorization, effective read-only identity, network separation, retention values, dan owner policy approval tetap future/private conditions.
- Evidence ini bukan `DEV-APPROVED`, Staging entry, atau Production authorization.
