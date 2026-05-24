# Candidate B Async Retry-Attempt Authority Selection

```yaml
milestone: candidate_b_async_retry_attempt_authority_selection_v1
source_retry_policy_runtime: next_milestone_plans/Layer3_planning_docs/1011-cb-async-retry-policy-runtime.md
current_main_entry: 264e397c49512bbf280e9511b24e39b78dbd0dd0
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_retry_queue_state_receipt_v1
selected_first_retry_runtime_reason: retry_attempt_requires_new_queue_state_scheduler_lease_and_worker_attempt_lineage
selected_retry_lineage_order: retry_queue_state_receipt,retry_scheduler_lease_receipt,retry_worker_attempt_receipt,retry_progress_checkpoint_receipt,retry_completion_failure_receipt
selected_retry_queue_state_scope: server_owned_candidate_b_full_corpus_operator_workflow_eligible_retry_policy_receipts
selected_retry_queue_state_mode: append_only_retry_queue_state_receipt_without_creating_scheduler_lease_worker_attempt_or_mutating_original_lineage
selected_retry_queue_state_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state
existing_retry_policy_endpoint_reused_for_retry_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy
existing_completion_failure_endpoint_reused_for_failed_terminal_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/failure
existing_history_endpoint_reused_for_run_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_run_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_retry_queue_state_receipt_model: append_only_retry_queue_state_receipt_without_mutating_retry_policy_completion_failure_progress_checkpoint_worker_attempt_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_queue_state_receipt_binding: retry_policy_receipt_id,retry_policy_receipt_hash,retry_policy_authority_hash,retry_policy_result,completion_failure_receipt_id,completion_failure_receipt_hash,completion_failure_authority_hash,failed_worker_attempt_receipt_id,failed_worker_attempt_authority_hash,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_queue_state_hash
selected_retry_queue_state_idempotency_basis: client_request_id_plus_retry_queue_state_authority_hash
retry_policy_result_required: eligible
ineligible_retry_policy_rejected: true
missing_retry_policy_receipt_rejected: true
stale_retry_policy_receipt_rejected: true
retry_policy_conflict_rejected: true
retry_attempt_number_selected: 2
retry_scheduler_lease_creation_admitted_now: false
retry_worker_attempt_creation_admitted_now: false
retry_progress_checkpoint_creation_admitted_now: false
retry_completion_failure_creation_admitted_now: false
retry_queue_state_runtime_selected_after_sync: true
retry_attempt_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_retry_queue_state_receipt_v1
```

This freeze selects retry queue-state authority as the first retry-attempt lineage runtime. The retry-policy receipt proves whether a failed terminal attempt is eligible for retry, but it does not itself create new queue, lease, attempt, progress, or terminal lineage.

The next runtime should therefore write a new append-only retry queue-state receipt over an eligible retry-policy receipt. It must not mutate the retry-policy receipt, the failed terminal receipt, the original progress checkpoint, the original worker attempt, the original scheduler lease, the original queue-state receipt, or the source workflow-run receipt. It also must not create the retry scheduler lease, retry worker attempt, retry progress checkpoint, retry terminal receipt, execute a job, cancel, resume, broaden Candidate B scope, or expose raw authority in this slice.

## Coherence Check

- Should the retry-policy runtime create a retry worker attempt directly? Recommended answer: no. A retry worker attempt needs a new retry queue-state and retry scheduler-lease lineage first.
- Should this slice reuse the original queue-state or scheduler-lease receipt? Recommended answer: no. Retry lineage must be separately append-only and must not reinterpret the original failed lineage as active.
- Should an ineligible retry-policy receipt create retry queue state? Recommended answer: no. Only `retry_policy_result: eligible` can admit retry queue-state authority.
- Should retry queue-state execute Candidate B work? Recommended answer: no. Execution remains unselected; this is lineage authority only.
- Should cancel or resume be bundled here? Recommended answer: no. They remain separate lifecycle policy/runtime selections.
