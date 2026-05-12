# Qual Hybrid RAG Named Analysis Packet

Status: current-main qualitative/hybrid/RAG named-analysis packet for `qual_hybrid_rag_named_analysis_packet`.

## Decision YAML

```yaml
selected_planning_mode: qual_hybrid_rag_named_analysis_packet
entry_decision: no_runtime_now_named_analysis_mode_absent
base_branch: main
implementation_branch: codex/l3-qual-analysis-packet
live_behavior_change: false
upstream_reentry_doc: 256_QUAL_HYBRID_RAG_REENTRY_DECISION_FREEZE.md
current_qualitative_runtime: single_aps_doc_qualitative_pass_only
named_analysis_use_case: null
selected_qual_hybrid_rag_mode: null
source_scope_selected: false
retrieval_corpus_selected: false
vector_storage_model_selected: false
embedding_model_authority_selected: false
prompt_model_provider_authority_selected: false
output_taxonomy_selected: false
implementation_entry_allowed_next: false
next_required_boundary: named_qual_hybrid_rag_analysis_mode_before_runtime
broad_qual_hybrid_rag_runtime_status: blocked
```

## Purpose

Doc `256_QUAL_HYBRID_RAG_REENTRY_DECISION_FREEZE.md` requires a single named qualitative, hybrid, or RAG mode before any broad analysis runtime. This packet answers that gate from current repo evidence.

The result is no runtime now. Current main proves the deterministic single APS-document qualitative pass and bounded qualitative APS downstream chain. It does not prove broad qualitative execution, qualitative cohort execution, comparative or cross-document synthesis, hybrid execution, RAG/vector retrieval, vector storage, embedding generation, prompt/model/provider runtime, output taxonomy expansion, or rendered qualitative/RAG controls.

## Repo-confirmed analysis truth

Current qualitative authority remains:

- `single_aps_doc_qualitative_pass` is the only admitted qualitative execution mode.
- The source class remains `aps_content_document` under the current source boundary.
- The qualitative APS downstream chain is bounded to package review, package construction, package review submit, handoff/export prepare, APS handoff dispatch, and external export/download prepare/deliver.
- Existing rendered qualitative APS controls remain limited to already-admitted downstream controls.
- Broad qualitative, qualitative associated-cohort, comparative, cross-document, hybrid, RAG/vector, embedding, prompt/model/provider, output taxonomy, and rendered qualitative/RAG expansion remain blocked.

## Named-analysis gate result

```yaml
named_analysis_gate:
  named_analysis_use_case:
    status: not_found_in_current_authority
    consequence: runtime_blocked
  selected_qual_hybrid_rag_mode:
    status: null
    consequence: runtime_blocked
  source_scope:
    status: current_single_aps_content_document_only
    consequence: insufficient_for_broad_or_cross_document_runtime
  retrieval_corpus:
    status: not_selected
    consequence: rag_runtime_blocked
  vector_storage_model:
    status: not_selected
    consequence: vector_runtime_blocked
  embedding_model_authority:
    status: not_selected
    consequence: embedding_runtime_blocked
  prompt_model_provider_authority:
    status: not_selected
    consequence: prompt_model_provider_runtime_blocked
  output_taxonomy:
    status: current_single_doc_qualitative_output_only
    consequence: insufficient_for_broad_or_hybrid_runtime
  rendered_control_plan:
    status: not_selected
    consequence: rendered_qual_hybrid_rag_controls_blocked
  auth_security_posture:
    status: not_selected_for_prompt_model_retrieval_runtime
    consequence: runtime_blocked
```

## Why no broad qualitative/hybrid/RAG runtime is selected

A broad qualitative, hybrid, or RAG runtime would need a real analysis use case and authority model. Current authority does not answer:

- whether the next analysis should be associated-cohort qualitative execution, comparative synthesis, cross-document synthesis, hybrid quantitative/qualitative execution, RAG/vector retrieval, retrieval-augmented qualitative pass, or output taxonomy expansion;
- which source set is authoritative;
- whether retrieval is allowed and what corpus bounds it;
- whether vector indexes can be created, stored, reused, or exposed;
- what embedding model, prompt model, provider, or model profile is allowed;
- how prompt text, model credentials, vectors, local paths, provider URLs, connector targets, destination targets, package contents, traces, screenshots, responses, and errors avoid leakage;
- how output taxonomy changes remain package-compatible;
- whether rendered controls are needed and how headed/headless/theme proof would be run.

Selecting broad analysis or RAG from the existence of one single-document qualitative path would overclaim live authority and create unsafe hidden model/retrieval coupling.

## Required future named-analysis packet contents

A future qualitative/hybrid/RAG runtime entry may proceed only after a packet names:

- one concrete analysis use case;
- one selected mode from the allowed qualitative/hybrid/RAG candidates;
- exact source scope and source authority;
- deterministic input contract;
- retrieval corpus authority if retrieval is involved;
- vector storage boundary if vector retrieval is involved;
- embedding/model/prompt/provider authority if model behavior is involved;
- output taxonomy and package compatibility;
- downstream delivery semantics;
- idempotency, concurrency, stale-authority, and failure policy;
- leak-control policy;
- rendered UI state plan and headed/headless/theme proof if controls are admitted;
- explicit no-go list for source expansion, package mutation, provider/public URL behavior, connector/destination dispatch, full mockup activation, and auth/security behavior.

## Non-admission

This packet admits no runtime behavior, broad qualitative execution, qualitative associated-cohort execution, comparative qualitative execution, cross-document synthesis, hybrid execution, RAG/vector retrieval, vector index creation, embedding generation, retrieval-augmented planning, arbitrary prompt text, model credentials, prompt/model/provider runtime, output taxonomy expansion, route/API/DTO/model/migration/service behavior, executable test behavior, rendered UI behavior, rendered qualitative/hybrid/RAG controls, source expansion, local upload, local-directory ingestion, web connector retrieval, package mutation/reconstruction, provider/public URL runtime, external connector invocation, destination writes, full mockup activation, auth/security behavior, hidden LLM planning, CI workflow change, Playwright configuration change, or frontend-only durable authority.

## Stop condition

Stop before implementation if the next analysis proposal cannot name one analysis use case and resolve selected mode, source authority, retrieval corpus, vector storage, embedding/model/prompt/provider authority, output taxonomy, package compatibility, leakage, browser proof, and no-go boundaries from explicit evidence rather than inference.
