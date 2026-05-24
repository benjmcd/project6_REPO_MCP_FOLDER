# Candidate B Async Cancel/Retry/Queue Authority Selection

```yaml
milestone: candidate_b_async_cancel_retry_queue_authority_selection_v1
source_expiry_closeout_runtime: next_milestone_plans/Layer3_planning_docs/999-cb-workflow-expiry-closeout-runtime.md
current_main_entry: 8320d8e480ea368fed1504ed985061910936dc11
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_workflow_queue_state_authority_v1
selected_next_runtime_scope: server_owned_candidate_b_full_corpus_operator_workflow_queue_state_receipts
selected_first_runtime_reason: cancel_retry_resume_require_server_owned_queue_attempt_and_checkpoint_authority
selected_queue_state_mode: append_only_queue_state_receipt_without_background_scheduler
selected_queue_state_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state
existing_run_start_endpoint_reused_for_current_sync_start: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
existing_history_endpoint_reused_for_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
existing_expiry_closeout_endpoint_remains_only_lifecycle_mutation: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire
selected_queue_state_receipt_model: append_only_queue_state_receipt_without_mutating_source_run_receipt
selected_queue_state_receipt_binding: operator_workflow_receipt_id,operator_workflow_receipt_hash,authority_basis_hash,history_hash,queue_state_hash
selected_queue_state_idempotency_basis: client_request_id_plus_queue_state_authority_hash
stale_run_receipt_must_reject: true
stale_history_row_must_reject: true
missing_run_receipt_must_reject: true
source_run_receipt_mutation_admitted: false
browser_supplied_receipt_root_admitted: false
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_bridge_dir_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
queue_state_authority_runtime_selected_after_sync: true
queue_scheduler_runtime_selected_now: false
background_worker_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_workflow_queue_state_authority_v1
```

This freeze selects queue-state authority as the next runtime-bearing slice after expiry/closeout. Current main proves a synchronous rendered workflow-run start, status inspection, read-only history projection, and append-only expiry closeout, but it does not prove a server-owned async queue, active lease, attempt model, retry policy, resume checkpoint, or cancellation target.

The first async runtime should therefore record bounded queue-state receipts for server-owned Candidate B full-corpus operator workflow runs. It must not start a background scheduler, mutate the source run receipt, cancel a running job, retry a failed job, resume a checkpoint, expand Candidate B default scope, write provider objects, dispatch connectors, activate RAG/vector/model runtime, activate the full mockup, or rely on browser/front-end durable authority.

## Grill Check

- Can cancel be first? Recommended answer: no. The current run surface writes a proven receipt synchronously, so there is no repo-confirmed in-flight server job or lease to cancel.
- Can retry be first? Recommended answer: no. Existing idempotency covers exact replay; runtime retry needs queue attempt authority and failure classification first.
- Can resume be first? Recommended answer: no. Current main has no checkpoint/resume authority for Candidate B workflow execution.
- Can queue scheduling be first? Recommended answer: not full scheduling. The smallest next step is server-owned queue-state receipt authority; a scheduler/worker can be admitted only after queue state is proven.
- Should provider writes, connectors, broader source scope, RAG/model runtime, or full mockup activation be combined here? Recommended answer: no. None are needed to establish Candidate B async workflow authority and each requires its own admission proof.
