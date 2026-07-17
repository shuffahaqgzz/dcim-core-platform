# Repository Bootstrap Evidence — 2026-07-16

- **Recorded at:** 2026-07-16T09:46:03Z
- **Milestone:** Dev Platform Bootstrap v0.1
- **Scope:** public-repository scaffold, governance baseline, local safety/contract checks, GitHub Actions definitions, and constrained Codex assets
- **Data posture:** synthetic/public-safe content only
- **Owner status:** prepared for owner review; not a Production approval

## Acceptance evidence

| Check | Command or method | Result |
|---|---|---|
| Public-repository content scan | `python3 scripts/check-public-safety.py` through `make preflight` | PASS — 79 repository files scanned after this evidence record was added |
| JSON Schema and fixture validation | `python3 scripts/validate-json.py` through `make preflight` | PASS — five JSON files validated, including two synthetic event fixtures |
| Unit and structure tests | `python3 -m unittest discover -s tests -p 'test_*.py' -v` through `make preflight` | PASS — 12 tests |
| Codex TOML parsing | Python `tomllib` for `.codex/config.toml` and `docs/codex/USER-CONFIG.example.toml` | PASS |
| GitHub configuration YAML parsing | Python `yaml.safe_load` for issue forms, Dependabot, and workflow files | PASS |
| Shell syntax | `bash -n` for every tracked shell script | PASS |
| Python syntax | `python -m compileall -q scripts tests` | PASS |
| GitHub Action immutability | Manual review of committed workflow definitions | PASS — third-party/action references use exact commit SHAs |
| Git staging and ignore behavior | Temporary clean repository; `git add`, `git check-ignore`, and tracked-file review | PASS — 79 intended files tracked; local environment/runtime/data samples remained ignored |

## Delivered controls

- public/private data boundary and prohibited-content policy;
- repository-level `.gitignore` and placeholder-only `.env.example`;
- PR template, issue forms, CODEOWNERS, Dependabot, local CI, dependency review, and secret-scan workflows;
- Development baseline, condition register, open-decision register, ADR workflow, ten-day task plan, and repository-settings runbook;
- synthetic P1/P2 event fixtures and JSON Schema contracts;
- conservative Codex project config, custom read-oriented subagents, repository skills, MCP policy, prompt catalog, and operator setup guide;
- one-command local verification through `make preflight`.

## Limitations and pending evidence

- The GitHub settings described in `docs/runbooks/GITHUB-REPOSITORY-SETUP.md` require owner/admin configuration and were not changed by this local validation.
- GitHub-hosted workflow results are pending the bootstrap pull request. This record does not claim that remote checks have passed.
- Docker Compose services, real connector implementations, databases, Kafka, observability, dashboard, SIEM/SOAR, workflow engine, analytics, and Hermes runtime are placeholders for later task-plan increments.
- No office/Production source was contacted. Source authorization, classification, read-only credentials, negative write tests, network separation, and polling-impact evidence remain open conditions.
- Codex CLI itself was not installed or executed in this validation environment. Repository configuration was syntax-checked only.
- No repository license has been selected; public visibility does not grant reuse rights.
- Open architecture decisions remain unresolved and must not be silently encoded by an agent.
- This evidence supports repository bootstrap review only. It is not a Development exit, Staging entry, Production readiness, HA, SLA, security accreditation, or operational authorization claim.
