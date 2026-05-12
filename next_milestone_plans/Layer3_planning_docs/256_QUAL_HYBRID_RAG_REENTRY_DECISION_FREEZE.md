# Qualitative Hybrid RAG Reentry Decision Freeze

Status: current-main reentry decision freeze for `qual_hybrid_rag_reentry_decision`.

This document follows `255_PACKAGE_MUTATION_REENTRY_DECISION_FREEZE.md`. It records the qualitative/hybrid/RAG reentry decision after the goal-stack, source rendered-control, connector/destination, and package mutation reentry audits: current main already has the single APS-document qualitative pass and the bounded qualitative APS downstream chain, but no broad qualitative execution, qualitative associated-cohort execution, comparative execution, cross-document synthesis, hybrid execution, RAG/vector retrieval, vector index creation, embedding generation, prompt/model/provider runtime, rendered qualitative/RAG control expansion, output taxonomy expansion, source expansion, package mutation side effect, provider/public URL runtime, connector/destination dispatch, full mockup activation, auth/security behavior, hidden LLM planning, or frontend-only durable authority is admitted.

## Decision

```yaml
selected_planning_mode: qual_hybrid_rag_reentry_decision
entry_decision: single_aps_doc_qualitative_live_broad_hybrid_rag_blocked
base_branch: main
implementation_branch: codex/l3-qual-hybrid-rag-reentry-freeze
live_behavior_change: false
current_qualitative_runtime: single_aps_doc_qualitative_pass_only
current_qual_aps_downstream_runtime: bounded_qual_aps_backend_api_downstream_chain
current_rendered_qual_aps_controls: qual_aps_rendered_downstream_existing_controls_only
broad_qualitative_execution: blocked
qualitative_associated_cohort_execution: blocked
comparative_qualitative_execution: blocked
cross_document_synthesis: blocked
hybrid_execution: blocked
rag_vector_retrieval: blocked
vector_index_creation: blocked
embedding_generation: blocked
prompt_model_provider_runtime: blocked
rendered_qual_hybrid_rag_controls: blocked
implementation_entry_allowed_next: false
next_required_boundary: single_named_qual_hybrid_rag_mode_freeze_before_runtime
```

The decision is deliberately not a broad analysis implementation. The live qualitative boundary is the deterministic single APS content-document path and its already bounded downstream package/handoff/export chain. That boundary is not authority for arbitrary prompt/model execution, cohort reasoning, comparative synthesis, retrieval corpora, vector stores, embeddings, browser-supplied prompts, or rendered RAG controls.

## Current Live Boundary

The current qualitative boundary is:

- owner service: `backend/app/services/layer3_qual_aps_execution.py`;
- live mode: `single_aps_doc_qualitative_pass`;
- source class: `aps_content_document` within the current source boundary;
- downstream chain: qualitative APS package review, package construction, package review submit, handoff/export prepare, APS handoff dispatch, and external export/download prepare/deliver;
- rendered controls: existing qualitative APS downstream controls only;
- proof posture: fail-closed request fields and checker-enforced non-admission for broad qualitative, hybrid, RAG/vector, hidden LLM, source expansion, package mutation, provider/public URL, connector/destination, and mockup behavior.

## Runtime Still Blocked

The following remain blocked:

- broad qualitative execution;
- qualitative associated-cohort execution;
- comparative qualitative execution;
- cross-document synthesis;
- hybrid quantitative/qualitative execution;
- RAG/vector retrieval;
- vector index creation or mutation;
- embedding generation or embedding-vector exposure;
- retrieval-augmented planning;
- arbitrary prompt text or hidden LLM planning;
- prompt/model/provider runtime;
- output taxonomy expansion;
- rendered qualitative/hybrid/RAG controls;
- source expansion, local upload, directory ingestion, web retrieval, or unbounded runtime DB source reads;
- package mutation/reconstruction;
- provider/public URL runtime;
- connector/destination dispatch;
- full mockup activation;
- auth/security behavior changes.

## Reentry Requirements

A later qualitative, hybrid, or RAG implementation may proceed only if it selects exactly one mode:

- `single_aps_doc_qualitative_current_chain_extension`;
- `qualitative_associated_cohort_execution`;
- `comparative_qualitative_execution`;
- `cross_document_synthesis`;
- `hybrid_quantitative_qualitative_execution`;
- `rag_vector_retrieval`;
- `retrieval_augmented_qualitative_pass`;
- `qualitative_output_taxonomy_expansion`.

The selected mode must define:

- named analysis use case;
- exact source scope and source authority;
- execution authority and deterministic input contract;
- retrieval corpus authority if retrieval is involved;
- vector storage boundary if vector retrieval is involved;
- embedding/model/prompt authority if model behavior is involved;
- output taxonomy and package compatibility;
- downstream delivery semantics;
- idempotency, concurrency, stale-authority, and failure policy;
- leak-control policy for prompts, model credentials, vectors, local paths, provider URLs, connector targets, destination targets, package contents, logs, error bodies, traces, screenshots, and responses;
- rendered UI state, theme, headed Chromium proof, and headless Chromium proof if controls are admitted.

## Validation Evidence

This freeze relies on already-landed implementation/audit evidence:

- PR `#809` recorded the goal-stack implementation audit and proved the current bounded implementation state.
- PR `#810` recorded the source rendered-control decision and preserved source/rendered non-admission.
- PR `#811` recorded the connector/destination reentry decision and preserved external dispatch non-admission.
- PR `#812` recorded the package mutation reentry decision and preserved rendered/broad mutation non-admission.
- Current single APS-document qualitative behavior remains governed by `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md` and `124_QUAL_HYBRID_RAG_FREEZE.md`.
- Current broad qualitative/hybrid/RAG non-admission remains governed by `195_QUAL_HYBRID_RAG_VECTOR_ENTRY_FREEZE.md`, `196_QUAL_HYBRID_RAG_VECTOR_ENTRY_CONTRACT.md`, and `217_QUAL_HYBRID_RAG_AUTHORITY_DISCOVERY_CLOSEOUT.md`.
- `python .\tools\l3-progress-check.py` must pass after this freeze is wired.

This validation does not prove cohort analysis, comparative/cross-document synthesis, hybrid execution semantics, RAG retrieval quality, vector store architecture, embedding generation, prompt/model/provider safety, output taxonomy compatibility, rendered qualitative/RAG controls, or auth/security production readiness.

## Negative Invariants

- no broad qualitative execution;
- no qualitative associated-cohort execution;
- no comparative qualitative execution;
- no cross-document synthesis;
- no hybrid execution;
- no RAG/vector retrieval;
- no vector index creation;
- no embedding generation;
- no retrieval-augmented planning;
- no arbitrary prompt text accepted from UI or API;
- no model credentials accepted from UI or API;
- no prompt/model/provider runtime;
- no hidden LLM planning;
- no output taxonomy expansion;
- no rendered qualitative/hybrid/RAG control;
- no source expansion;
- no local upload;
- no local-directory ingestion;
- no arbitrary local path input;
- no web connector retrieval;
- no unbounded runtime DB source reads;
- no package mutation/reconstruction;
- no provider/public URL runtime;
- no connector or destination dispatch;
- no generic downstream dispatch;
- no full mockup activation;
- no frontend-only durable execution authority;
- no browser-only qualitative/RAG authority;
- no auth/security behavior change;
- no route/API/DTO/model/migration/service behavior change;
- no executable test behavior change;
- no CI workflow or Playwright configuration change.

## Stop Condition

Stop before code if the next qualitative/hybrid/RAG proposal lacks one named mode, treats the single APS-document qualitative chain as broad analysis authority, accepts arbitrary prompts/model settings/provider credentials/vectors/local paths from the browser, creates or mutates vector indexes without a storage freeze, fetches sources or connectors as a side effect, mutates packages or delivery state as a side effect, lacks retrieval corpus/vector/model/output-taxonomy/leakage/idempotency/stale-authority tests, lacks headed/headless/theme proof for rendered controls, or changes source/package/provider/connector/mockup/auth behavior as a side effect.
