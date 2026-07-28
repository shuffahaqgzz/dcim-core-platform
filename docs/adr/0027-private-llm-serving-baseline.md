# ADR-0027: Private LLM Serving Baseline for the Analytics/RAG Explanation Layer

- Status: Accepted
- Date: 2026-07-28
- Owner: shuffahaqgzz
- Decision source: owner confirmation 2026-07-28 (`docs/research/PRD.md` §7 Q7)
- Related ADRs: ADR-0009 (Hermes deferred), ADR-0002 (public code/private runtime)

## Context

`docs/research/PRD.md` §7 Q7 confirms the AI model-serving decision for the
analytics/RAG explanation layer. The choice is between private on-premise GPU
hosting and a managed external API. The DCIM data model may contain office
layout, asset identity, operational state, and enriched event context, so any
inference path that sends Production or office data to an external AI service
triggers the `CONDITIONS-REGISTER.md` auto-NO-GO item 4: "Office data can
egress to an unapproved external AI, CI, logging, or telemetry service."

OD-05 (Hermes model/inference) is already `DEFERRED` and bound by
ADR-0009. This ADR records the serving baseline for the separate analytics/RAG
explanation layer and does **not** re-open OD-05 or authorize Hermes work.

The Development baseline refers to a single "24 GB VRAM GPU" for the analytics
plane. The owner confirmed the actual sizing is **2× NVIDIA RTX A5000 24 GB
VRAM**. The confirmed 2-GPU sizing is recorded here as the serving baseline;
the single-GPU reference in the baseline is treated as a Phase 4 capacity
discrepancy that will be reconciled when the analytics scope activates.

## Decision drivers

- Data sovereignty and the auto-NO-GO on office/Production data egress to external AI.
- Offline/on-premise operation for the explanation layer.
- Hermes remains gated; AI value must be advisory and non-blocking only.
- GPU headroom for concurrent RAG retrieval and inference.
- Repository safety: no model weights, inference endpoints, or GPU workload
  definitions may enter the public repository.

## Decision

Adopt **private on-premise LLM serving** for the analytics/RAG explanation
layer, with the following constraints:

1. **Hardware baseline.** Private hosting on **2× NVIDIA RTX A5000 24 GB VRAM**
   GPUs. Each card provides 24 GB VRAM; the pair supplies the capacity and
   headroom for RAG context + inference concurrency.
2. **Serving stack.** Ollama- or llama.cpp-class serving on the private host.
   No specific model weights, inference endpoint, or GPU workload manifest is
   recorded in this repository.
3. **Provider abstraction layer.** The analytics service consumes inference
   through a provider abstraction that defaults to the private local host. A
   managed-API fallback is permitted **only** after an explicit data-boundary
   review that proves no office/Production data will egress to the external
   service.
4. **Data boundary.** The default and preferred path keeps all prompts,
   context, and responses on the private GPU host. Any proposal to route data
   to an external AI API must be reviewed against the `CONDITIONS-REGISTER.md`
   auto-NO-GO list and approved outside Git.
5. **Scope boundary.** This decision covers the analytics/RAG explanation
   layer only. It does **not** re-open OD-05 and does **not** authorize Hermes
   work. ADR-0009 remains the Hermes gate, and C-08 stays `DEFERRED`.
6. **Repository safety.** No GPU workload, model weight file, inference
   endpoint, or hardware hostname is committed to this repository.
7. **Sizing discrepancy.** The Development baseline's single "24 GB VRAM GPU"
   reference is superseded by the owner-confirmed 2×A5000 sizing. The mismatch is
   recorded as a Phase 4 capacity item to be resolved when the analytics/RAG
   scope is activated.

## Options considered

### 1. Managed external AI API only (rejected)

Simpler scaling and no local GPU operations, but violates the data-sovereignty
principle and the `CONDITIONS-REGISTER.md` auto-NO-GO item 4 unless an explicit
review approves a sanitized, non-Production subset. Rejected as the default.

### 2. Single 24 GB VRAM GPU (superseded)

Matched the original baseline wording, but the owner confirmed the actual
hardware sizing is 2×RTX A5000 24 GB. This option is superseded by the
confirmed 2-GPU configuration.

### 3. Private 2×RTX A5000 24 GB hosting (selected)

Selected per owner confirmation 2026-07-28. Provides on-premise data
sovereignty, offline operation, and the capacity for the RAG explanation layer.

## Security impact

- Private hosting keeps prompts, retrieved context, and generated explanations
  within the operational boundary.
- The provider abstraction layer defaults to the local host; a managed-API path
  requires an explicit data-boundary review and approval before any data may
  egress.
- No model weights, inference endpoints, or GPU host identifiers are stored in
  the public repository.
- Hermes remains gated; the explanation layer cannot become a blocking or
  state-changing dependency.

## License impact

- LLM serving tools (Ollama/llama.cpp-class) and any model weights are governed
  by their own licenses. The project integrates via API only and makes no
  distribution claim.
- License obligations are recorded in the dependency inventory when concrete
  tools are selected; the ADR itself does not name or commit model weights.

## Resource and operational impact

- 2× NVIDIA RTX A5000 24 GB VRAM GPUs, private host.
- Ollama- or llama.cpp-class serving runtime; monitoring of VRAM, token
  throughput, queue depth, and host power/thermal.
- The confirmed 2-GPU sizing is recorded as the serving baseline; the Phase 4
  capacity plan reconciles the earlier single-GPU baseline reference.

## Migration and rollback

- The provider abstraction layer allows switching between the private local
  host and an approved fallback without repository changes.
- Rollback to private-only serving is always available by disabling the fallback
  provider.
- Any fallback activation requires a completed data-boundary review; the
  abstraction keeps the default path local.

## Acceptance evidence

- owner marks this ADR Accepted;
- provider abstraction layer design documented outside the model weights;
- data-boundary review procedure exists before any managed-API fallback is
  enabled;
- Phase 4 capacity plan reconciles the single-GPU baseline reference with the
  confirmed 2×A5000 sizing;
- GPU fit and offline inference demonstrated when the analytics/RAG scope
  activates;
- repository scan confirms no model weights, inference endpoints, or GPU host
  identifiers are present in Git.

## Revalidation triggers

- OD-05 or Hermes is re-opened (ADR-0009 is the governing gate);
- a proposal to use a managed external AI API as a fallback or default;
- a change in serving-tool or model-weight licensing terms;
- a GPU capacity change or replacement of the 2×A5000 baseline;
- any evidence that the abstraction layer could route office/Production data
  to an external AI service without review.
