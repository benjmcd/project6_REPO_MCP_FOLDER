# Candidate B Async Queue Scheduler Authority Selection

```yaml
milestone: candidate_b_async_queue_scheduler_authority_selection_v1
source_queue_state_runtime: next_milestone_plans/Layer3_planning_docs/1001-cb-async-queue-state-runtime.md
current_main_entry: ead28c301404b7a3128b4a8234177efd29d44164
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_scheduler_lease_receipt_v1
selected_scheduler_scope: server_owned_candidate_b_full_corpus_operator_workflow_queue_state_receipts
selected_scheduler_mode: append_only_scheduler_lease_receipt_without_background_worker
selected_scheduler_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease
existing_queue_state_endpoint_reused_for_source_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state
existing_history_endpoint_reused_for_run_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_run_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
existing_expiry_closeout_endpoint_remains_only_lifecycle_mutation: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire
selected_scheduler_receipt_model: append_only_scheduler_lease_receipt_without_mutating_queue_state_or_source_run_receipt
selected_scheduler_receipt_binding: queue_state_receipt_id,queue_state_receipt_hash,queue_state_authority_hash,operator_workflow_receipt_id,operator_workflow_receipt_hash,scheduler_lease_hash
selected_scheduler_idempotency_basis: client_request_id_plus_scheduler_lease_authority_hash
stale_queue_state_receipt_must_reject: true
stale_run_receipt_must_reject: true
stale_history_row_must_reject: true
missing_queue_state_receipt_must_reject: true
source_run_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
browser_supplied_receipt_root_admitted: false
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_bridge_dir_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
scheduler_lease_runtime_selected_after_sync: true
background_worker_runtime_selected_now: false
job_execution_runtime_selected_now: false
cancel_runtime_selected_now: false
retry_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_scheduler_lease_receipt_v1
```

This freeze selects a scheduler lease receipt as the next runtime-bearing slice after queue-state authority. Current main can record queue-state authority for a selected Candidate B workflow-run row, but it still has no server-owned lease, lease expiry, attempt number, worker handoff, running-state transition, or deterministic ownership model.

The next runtime must therefore create an append-only scheduler lease receipt over an existing queue-state receipt. It must prove exclusive server-owned lease authority, stale queue-state/run/history rejection, deterministic idempotency, no queue-state receipt mutation, no source run receipt mutation, and no browser-supplied paths, URLs, roots, connector/model/provider controls, or frontend durable authority.

## Grill Check

- Should the scheduler lease start a background worker? Recommended answer: no. The first scheduler runtime should only create server-owned lease authority; execution belongs to a separate worker/runtime slice.
- Can cancel be implemented after queue-state but before a scheduler lease? Recommended answer: no. Cancellation still lacks a server-owned in-flight lease or worker target.
- Can retry be implemented before lease attempts exist? Recommended answer: no. Retry needs attempt identity, failure classification, and lease/queue lineage first.
- Can resume be implemented before checkpoint authority exists? Recommended answer: no. Resume still needs a separate checkpoint model after scheduler/worker semantics exist.
- Should this broaden Candidate B default scope, provider writes, connectors, RAG/model runtime, or full mockup behavior? Recommended answer: no. The scheduler lease is only workflow-run authority.
