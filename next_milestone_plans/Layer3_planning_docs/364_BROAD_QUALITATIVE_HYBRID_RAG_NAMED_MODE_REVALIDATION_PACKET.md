# Broad Qualitative Hybrid RAG Named Mode Revalidation Packet

## Status

Status: planning/control broad qualitative hybrid RAG named-mode revalidation packet only; no runtime behavior admitted.

This packet follows current-main doc `363_NEXT_DEFERRED_SERVER_AUTHORITATIVE_RUNTIME_LANE_AFTER_PACKAGE_ACTION_CURRENT_MAIN_SYNC.md`.

The selected packet is `broad_qualitative_hybrid_rag_named_mode_revalidation_packet`.

## Decision

No broad qualitative, hybrid, or RAG/vector runtime is selected.

The revalidation result is `no_runtime_now_broad_qualitative_hybrid_rag_named_mode_absent`.

Current repo authority admits `single_aps_doc_qualitative_pass` only, not broad qualitative execution, hybrid execution, or RAG/vector indexing/retrieval.

The next required action is `current_main_sync_broad_qualitative_hybrid_rag_named_mode_revalidation_packet_after_merge`.

## Repo-confirmed authority

Current repo authority is intentionally narrow:

- `backend/app/services/layer3_bootstrap_contract.py` sets `single_aps_doc_qualitative_execution` true while `broad_qualitative_execution`, `hybrid_execution`, and `rag_vector_retrieval` are false.
- `backend/app/services/layer3_state_action_contract.py` admits `single_aps_doc_qualitative_execution` only and lists `broad_qualitative_execution`, `hybrid_execution`, and `rag_vector_retrieval` as deferred capabilities.
- `backend/app/services/layer3_execution_request_contract.py` forbids `qualitative_plan`, `hybrid_plan`, `rag_plan`, and `vector_plan` in execution-start scope.
- `backend/app/services/layer3_qual_aps_execution.py` owns `QUALITATIVE_BOUNDARY_MODE = "single_aps_doc_qualitative_pass_only"`, admits only `single_aps_doc_qualitative_pass`, and explicitly disables broad qualitative, associated-cohort qualitative, comparative qualitative, cross-document synthesis, hybrid execution, RAG/vector retrieval, hidden LLM planning, source widening, connector/destination dispatch, and package mutation/reconstruction.
- `backend/app/services/layer3_source_intake.py` keeps `rag_vector_index` as forbidden request scope and projects source-intake RAG/vector indexing as disabled rather than active runtime.

## Gate result

```yaml
broad_qualitative_hybrid_rag_named_mode_revalidation:
  selected_planning_mode: broad_qualitative_hybrid_rag_named_mode_revalidation_packet
  entry_decision: no_runtime_now_broad_qualitative_hybrid_rag_named_mode_absent
  admitted_current_mode: single_aps_doc_qualitative_pass
  broad_qualitative_runtime_selected: false
  hybrid_runtime_selected: false
  rag_vector_runtime_selected: false
  named_broad_analysis_mode_selected: null
  retrieval_index_store_selected: null
  source_corpus_boundary_selected: null
  result_artifact_contract_selected: false
  stale_authority_policy_selected: false
  idempotency_replay_recovery_policy_selected: false
  receipt_audit_contract_selected: false
  rendered_control_plan_selected: false
  auth_security_posture_selected: false
```

## Why runtime remains blocked

Current main does not prove:

- one named broad qualitative, hybrid, or RAG/vector analysis mode
- one operator use case for that mode
- source corpus authority beyond already admitted bounded source-intake and APS content-document surfaces
- retrieval/index/store ownership
- prompt, context-packet, or hidden-planning contract
- deterministic request/response contract for broad qualitative/hybrid/RAG execution
- stale-authority behavior
- idempotency, replay, duplicate-action, or recovery behavior
- result artifact, receipt, and audit contract
- rendered controls or headed/headless/theme proof obligations
- leak controls for prompts, retrieved text, vector ids, local paths, provider URLs, connector targets, traces, screenshots, responses, and errors
- auth/security posture

The existing qualitative runtime is not absent; it is deliberately bounded to the exact single APS content-document qualitative pass. That existing path is not authority to widen into broad qualitative, hybrid, or RAG/vector runtime.

## Explicit non-goals

No broad qualitative runtime is admitted.

No associated-cohort qualitative runtime is admitted.

No comparative qualitative runtime is admitted.

No cross-document synthesis runtime is admitted.

No hybrid execution runtime is admitted.

No RAG/vector indexing or retrieval runtime is admitted.

No hidden LLM planning is admitted.

No source expansion is admitted.

No connector/destination dispatch is admitted.

No provider-public delivery/use is admitted.

No package mutation or reconstruction is admitted.

No rendered package mutation control is admitted.

No full mockup activation is admitted.

No auth/security behavior is admitted.

No route, model, migration, schema, or frontend-only durable authority is admitted.

## Future reopening condition

A later broad qualitative/hybrid/RAG runtime freeze may proceed only if it names:

- one analysis mode and one operator use case
- exact source authority and admitted corpus boundary
- retrieval/index/store ownership, or explicit no-RAG mode
- prompt/context-packet/hidden-planning policy
- deterministic request/response contract
- stale-authority behavior
- idempotency, replay, duplicate-action, and recovery behavior
- result artifact and receipt/audit contract
- leak controls
- browser proof obligations if rendered controls are involved
- auth/security posture

Until then, broad qualitative/hybrid/RAG remains blocked behind the existing `single_aps_doc_qualitative_pass_only` boundary.
