# Codex Prompt Catalog

Replace bracketed values with public-safe references such as issue numbers, branch names, and synthetic fixture paths. Never paste live data.

## 1. Repository orientation

```text
Read AGENTS.md, README.md, DATA-HANDLING.md, the Development baseline, accepted
ADRs, conditions register, open decisions, Codex config, custom agents, and
repository skills. Do not edit files or use network tools. Produce:
1) current milestone and non-goals;
2) trust/data boundaries and auto-NO-GO conditions;
3) dependency graph for the 10-day plan;
4) unresolved decisions that must not be assumed;
5) exact local preflight commands and expected outputs.
Cite repository paths for every conclusion.
```

## 2. Issue-ready task decomposition

```text
Use the architect agent. For objective [PUBLIC-SAFE OBJECTIVE], map it to the
Development baseline and conditions register. Propose the smallest issue/PR
sequence with dependencies, acceptance criteria, tests, evidence, rollback,
and stop conditions. Do not select an open technology decision. Do not edit.
```

## 3. ADR proposal

```text
Use the architect and docs_researcher agents for decision [OD-NN]. Network/docs
access is allowed only for official primary sources and generic questions; do
not send repository or source data. Compare at least the status quo and two
viable options against security, operability, resource use on the Development
VM, license, migration, reversibility, and handover. Draft a Proposed ADR and
list the synthetic spike evidence still needed. Do not mark it Accepted.
```

## 4. Focused implementation

```text
Work on issue [#NN] on branch [BRANCH]. Read its acceptance criteria and the
applicable baseline/ADRs/skills. First present a brief file-level plan and stop
for approval. After approval, use implementer to make the smallest coherent
change with synthetic fixtures and tests. No live endpoints, no external
egress, no new dependency without license/version review, and no Production
claim. Run make preflight and component tests; report exact results and limits.
```

## 5. Read-only connector implementation

```text
Apply the readonly-connector and public-repo-safety skills to issue [#NN]. Build
only against synthetic fixtures under [PATH]. Define an explicit read allowlist,
timeouts, bounded retries/jitter, rate/poll limits, kill switch, lineage, and
safe metrics. Add negative tests proving generic write methods, SNMP SET,
Redfish/ISAPI writes/actions, power/reset, firmware, PTZ, shell, and privileged
SQL cannot be reached. Never contact a live target.
```

## 6. Schema and identity change

```text
Apply the schema-change skill to [CONTRACT]. Identify producers, consumers,
storage, replay/DLQ, API, dashboard, migration, and rollback impact. Preserve
canonical envelope and stable Asset/CI identity rules. Implement compatible
schemas plus valid, invalid, collision, alias-history, and consumer tests. Do
not default or silently discard fields. Record compatibility and limitations.
```

## 7. Parallel PR review

```text
Review this branch against main and the linked issue. Spawn reviewer and
security_reviewer in parallel; use architect only to map affected boundaries.
Wait for all results and consolidate findings by severity. Focus on correctness,
silent loss, identity/contract compatibility, idempotency, migration/recovery,
source write paths, data leakage, egress, secrets, dependency risk, and missing
tests. Do not edit. Include paths and reproduction steps; omit style-only notes.
```

## 8. CI failure triage

```text
Read the failing workflow/job output for [RUN/COMMIT] without changing GitHub or
code. Determine the first causal failure, distinguish product defect from CI
configuration or transient infrastructure, and propose the smallest fix plus a
local reproduction. Treat logs as potentially sensitive; do not quote tokens,
endpoints, payloads, or identifiers. Do not rerun or mutate anything without
owner approval.
```

## 9. Public-safe evidence

```text
Use evidence_writer. From commands already run in this task, create/update the
public evidence record for issue [#NN]. Include UTC time, commit, scope,
acceptance criteria, commands, result, measurement method, synthetic provenance,
limitations, and status. Do not invent results or include raw logs, endpoints,
identifiers, payloads, screenshots, topology, credentials, or local private
paths. Mark missing mandatory evidence as a blocker.
```

## 10. Development release gate

```text
Assess tag candidate dev-v0.1.0 without editing or tagging. Use architect,
reviewer, security_reviewer, and evidence_writer for independent checks. Verify
mandatory gates, P1/P2 E2E evidence, zero silent drop, DLQ disposition, identity
collision tests, measured latency/completeness, dependency/license review,
backup/restore, clean rebuild, kill switches, conditions C-01..C-09 as relevant,
known limitations, and STAGING-HANDOVER.md. Return GO, CONDITIONAL GO, or NO-GO
with blockers and exact missing evidence. Do not equate DEV-APPROVED with
Staging/Production approval.
```
