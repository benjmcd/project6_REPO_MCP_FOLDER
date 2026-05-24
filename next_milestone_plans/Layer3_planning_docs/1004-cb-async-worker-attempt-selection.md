# Candidate B Async Worker Attempt Authority Selection

```yaml
milestone: candidate_b_async_worker_attempt_authority_selection_v1
source_scheduler_lease_runtime: next_milestone_plans/Layer3_planning_docs/1003-cb-async-scheduler-lease-runtime.md
current_main_entry: 1330270116a637eed6aa45a740146d53b838add0
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_worker_attempt_receipt_v1
selected_worker_attempt_scope: server_owned_candidate_b_full_corpus_operator_workflow_scheduler_lease_receipts
selected_worker_attempt_mode: append_only_worker_attempt_receipt_without_job_execution
selected_worker_attempt_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt
existing_scheduler_lease_endpoint_reused_for_source_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease
existing_queue_state_endpoint_reused_for_queue_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state
existing_history_endpoint_reused_for_run_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_run_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_worker_attempt_receipt_model: append_only_worker_attempt_receipt_without_mutating_scheduler_lease_queue_state_or_source_run_receipt
selected_worker_attempt_receipt_binding: scheduler_lease_receipt_id,scheduler_lease_receipt_hash,scheduler_lease_authority_hash,queue_state_receipt_id,queue_state_receipt_hash,operator_workflow_receipt_id,operator_workflow_receipt_hash,worker_attempt_hash
selected_worker_attempt_idempotency_basis: client_request_id_plus_worker_attempt_authority_hash
selected_initial_attempt_number: 1
exclusive_initial_attempt_per_scheduler_lease: true
stale_scheduler_lease_receipt_must_reject: true
stale_queue_state_receipt_must_reject: true
stale_run_receipt_must_reject: true
stale_history_row_must_reject: true
missing_scheduler_lease_receipt_must_reject: true
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
worker_attempt_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
progress_checkpoint_runtime_selected_now: false
completion_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_worker_attempt_receipt_v1
```

This freeze selects the first worker-attempt authority slice after scheduler lease receipts. The next runtime must create an append-only initial worker-attempt receipt over one existing scheduler lease receipt. It must bind the scheduler lease, queue-state receipt, current workflow-run history row, and operator workflow-run receipt without mutating any prior receipt or executing the Candidate B job.

The worker-attempt receipt is authority for an attempt identity only. It does not start a background process, execute work, emit progress checkpoints, complete the job, cancel, retry, resume, enforce expiry, broaden Candidate B default scope, write provider objects, dispatch connectors, run RAG/vector/model logic, expose raw paths or URLs, or activate full mockup behavior.

## Coherence Check

- Should the first worker-attempt receipt execute the Candidate B job? Recommended answer: no. It should establish attempt identity and lineage before execution/progress is separately admitted.
- Should retry create additional attempts in this slice? Recommended answer: no. Retry still needs failure classification and attempt outcome authority.
- Should cancel be implemented now that a lease exists? Recommended answer: no. Cancellation needs an admitted worker-attempt/progress state target first.
- Should resume be implemented before checkpoints exist? Recommended answer: no. Resume still needs separately admitted checkpoint authority.
