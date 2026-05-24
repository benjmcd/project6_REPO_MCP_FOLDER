# Candidate B Async Retry Scheduler-Lease Authority Selection

```yaml
milestone: candidate_b_async_retry_scheduler_lease_authority_selection_v1
source_retry_queue_state_runtime: next_milestone_plans/Layer3_planning_docs/1013-cb-async-retry-queue-state-runtime.md
current_main_entry: 23d11e18f2c97450108ffb8c194cee9de789303d
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_retry_scheduler_lease_receipt_v1
selected_retry_lineage_order: retry_queue_state_receipt,retry_scheduler_lease_receipt,retry_worker_attempt_receipt,retry_progress_checkpoint_receipt,retry_completion_failure_receipt
selected_retry_scheduler_lease_scope: server_owned_candidate_b_full_corpus_operator_workflow_retry_queue_state_receipts
selected_retry_scheduler_lease_mode: append_only_retry_scheduler_lease_receipt_without_creating_worker_attempt_or_mutating_retry_queue_state_original_lineage
selected_retry_scheduler_lease_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/scheduler/lease
existing_retry_queue_state_endpoint_reused_for_retry_lineage_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state
existing_retry_policy_endpoint_reused_for_retry_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy
existing_history_endpoint_reused_for_run_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_run_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_retry_scheduler_lease_receipt_model: append_only_retry_scheduler_lease_receipt_without_mutating_retry_queue_state_retry_policy_completion_failure_progress_checkpoint_worker_attempt_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_scheduler_lease_receipt_binding: retry_queue_state_receipt_id,retry_queue_state_receipt_hash,retry_queue_state_authority_hash,retry_attempt_number,retry_policy_receipt_id,retry_policy_authority_hash,completion_failure_receipt_id,failed_worker_attempt_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_scheduler_lease_hash
selected_retry_scheduler_lease_idempotency_basis: client_request_id_plus_retry_scheduler_lease_authority_hash
retry_queue_state_receipt_required: true
retry_queue_state_runtime_required: true
retry_attempt_number_required: 2
missing_retry_queue_state_receipt_rejected: true
stale_retry_queue_state_receipt_rejected: true
retry_queue_state_conflict_rejected: true
retry_worker_attempt_creation_admitted_now: false
retry_progress_checkpoint_creation_admitted_now: false
retry_completion_failure_creation_admitted_now: false
retry_scheduler_lease_runtime_selected_after_sync: true
retry_worker_attempt_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
retry_queue_state_receipt_mutation_admitted: false
retry_policy_receipt_mutation_admitted: false
completion_failure_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_retry_scheduler_lease_receipt_v1
```

This freeze selects retry scheduler-lease authority as the second retry-attempt lineage runtime. The retry queue-state receipt starts retry attempt number 2, but it intentionally does not create a scheduler lease, worker attempt, progress checkpoint, terminal receipt, or job execution.

The next runtime should therefore write a new append-only retry scheduler-lease receipt over a current retry queue-state receipt. It must not mutate the retry queue-state receipt, retry-policy receipt, failed terminal receipt, original progress checkpoint, original worker attempt, original scheduler lease, original queue-state receipt, or source workflow-run receipt. It also must not create the retry worker attempt, retry progress checkpoint, retry terminal receipt, execute a job, cancel, resume, broaden Candidate B scope, or expose raw authority in this slice.

## Coherence Check

- Should retry queue-state immediately create a worker attempt? Recommended answer: no. The retry scheduler-lease receipt is the next authority boundary before worker-attempt creation.
- Should the retry scheduler lease reuse the original scheduler lease from the failed attempt? Recommended answer: no. Retry lineage must remain distinct and append-only.
- Should this slice create job execution or a background worker? Recommended answer: no. It records lease authority only.
- Should a stale or conflicting retry queue-state receipt be accepted? Recommended answer: no. It must fail closed.
- Should cancel or resume be bundled here? Recommended answer: no. They remain separate lifecycle policy/runtime selections.
