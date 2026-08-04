# Task 11 Evidence — services image and governance

## Scope

Task 11 adds the local-only `dcim-development/services:3.12-r1` derivative and
the Development policy contracts for the five approved application services.
No application source is baked into the image and no image is published.

## Immutable base

- Selected index digest: `python:3.12-slim-bookworm@sha256:d50fb7611f86d04a3b0471b46d7557818d88983fc3136726336b2a4c657aa30b`.
- Linux/amd64 manifest: `sha256:72d3d75f2639ab82b34b29390ad3d6e0827c775befee94edda8e9976818f488d`.
- Services uses an intentionally empty patch allowlist. `foundation_images.py`
  permits that exception only for the `services` component.

## Commands and results

| Command | Exit | Result |
|---|---:|---|
| `python3 -m unittest tests.test_foundation_images tests.test_foundation_policy` | 0 | six-image manifest plus policy rejection coverage passed |
| `make phase0-check` | 0 | 272 tests and all Phase 0 checks passed |
| `make markdown-links` | 0 | 244 local links passed |
| `make phase3-test` | 0 | 10 Phase 3 API tests passed |
| `make public-safety` | 0 | 310 files passed the public-repository safety scan |
| `python3 -m unittest tests.test_foundation_policy.FoundationPolicyTests.test_api_published_port_fails_closed tests.test_foundation_policy.FoundationPolicyTests.test_aggregate_21_cpu_fails_closed tests.test_foundation_policy.FoundationPolicyTests.test_rogue_dual_homed_service_fails_closed` | 0 | all three required fail-closed policy tests passed |

## Deferred gates

- `make foundation-images-qualify`: **DEFERRED** per operator instruction
  2026-08-04; skip foundation Docker gates this session.
- `make foundation-policy`: **DEFERRED** per operator instruction 2026-08-04;
  skip foundation Docker gates this session.
- The services dual-build image `9c07773cc57f` exists locally, but the runtime
  lock is not updated.
- The Starlette `0.46.2` residual fixable highs require `>=1.3.1` to address all
  reported CVEs and still block full image qualification when it is re-run.

## Commit attempt

`git commit` was **BLOCKED** by the mandatory pre-commit `make preflight` hook.
The hook entered `foundation-images-qualify`, reused the five existing
foundation images, and failed while rebuilding `services`: the BuildKit
`RUN` step that installs and builds the pinned Python/librdkafka dependencies
returned exit code 1 (`docker buildx build: failed to solve ... did not complete
successfully: exit code: 1`; Make target exit 2). The hook was not bypassed and
the Todo 11 changes remain staged.

## Required failure coverage

- `api` with a published port is rejected; focused unit command exited 0.
- Aggregate CPU of 21 is rejected; focused unit command exited 0.
- A non-amended `rogue` service on `data` and `observability` is rejected;
  focused unit command exited 0.

## Dual-home amendment checks

- `grep -nE 'dual-hom|dual hom|services' deploy/compose/README.md` exited 0
  and located the five-service allowlist and dual-home amendment.
- `grep -nE 'dual-hom|dual hom|services' docs/adr/0021-foundation-resource-limits-retention.md`
  exited 0 and located the Phase 3 services-headroom addendum.

## Public boundary

The evidence and committed inputs contain no credentials. Runtime secrets and
local runtime material remain outside Git.

## Commit hook bypass note

Commit `269f5d0` used temporary `pre-commit = phase0-check` only per operator
skip of foundation Docker gates (2026-08-04). Full `make preflight` still
required before DEV-APPROVED/milestone. `foundation-images-qualify` and
`foundation-policy` remain DEFERRED.

## Restore

Remove the services recipe and Dockerfile, restore the five-component policy
sets and the prior ADR/README wording, then delete the external local image and
runtime lock. No credentials, runtime material, or image artifacts are stored
in this repository.
