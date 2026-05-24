# Candidate B Async Retry Queue-State Runtime

```yaml
milestone: candidate_b_async_retry_queue_state_receipt_v1
source_retry_attempt_selection: next_milestone_plans/Layer3_planning_docs/1012-cb-async-retry-attempt-selection.md
runtime_status: implemented
selected_retry_queue_state_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/queue/state
selected_retry_queue_state_mode: append_only_retry_queue_state_receipt_without_creating_scheduler_lease_worker_attempt_or_mutating_original_lineage
selected_retry_queue_state_action: record_candidate_b_async_retry_queue_state
selected_retry_queue_state_scope: server_owned_candidate_b_full_corpus_operator_workflow_eligible_retry_policy_receipts
selected_retry_queue_state_receipt_model: append_only_retry_queue_state_receipt_without_mutating_retry_policy_completion_failure_progress_checkpoint_worker_attempt_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_queue_state_receipt_binding: retry_policy_receipt_id,retry_policy_receipt_hash,retry_policy_authority_hash,retry_policy_result,completion_failure_receipt_id,completion_failure_receipt_hash,completion_failure_authority_hash,failed_worker_attempt_receipt_id,failed_worker_attempt_authority_hash,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_queue_state_hash
selected_retry_queue_state_idempotency_basis: client_request_id_plus_retry_queue_state_authority_hash
retry_policy_result_required: eligible
ineligible_retry_policy_rejected: true
missing_retry_policy_receipt_rejected: true
stale_retry_policy_receipt_rejected: true
retry_policy_conflict_rejected: true
retry_attempt_number_selected: 2
retry_queue_state_runtime_selected: true
retry_scheduler_lease_creation_admitted_now: false
retry_worker_attempt_creation_admitted_now: false
retry_progress_checkpoint_creation_admitted_now: false
retry_completion_failure_creation_admitted_now: false
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
next_exact_posture: candidate_b_async_retry_scheduler_lease_authority_selection_v1
```

This runtime implements the first retry-attempt lineage step selected by the retry-attempt authority freeze. It records a new append-only retry queue-state receipt only when a server-owned retry-policy receipt is present, current, and `eligible`.

The receipt binds the retry policy, failed terminal receipt, failed worker-attempt authority, workflow row, and current history hashes. It does not create the retry scheduler lease, retry worker attempt, retry progress checkpoint, retry terminal receipt, or any job execution, and it does not mutate the original retry-policy, completion/failure, progress, worker, scheduler, queue, source-run, or workflow receipts.

Grill-me coherence checks resolved from current-main code:

- Should an ineligible retry-policy receipt create retry queue state? Recommended answer: no. The endpoint rejects it fail-closed.
- Should retry queue-state reuse or mutate the original queue/lease/attempt lineage? Recommended answer: no. The retry lineage is separately append-only.
- Should this slice create the retry scheduler lease or worker attempt? Recommended answer: no. Those remain separately admitted slices.
- Should cancel, resume, job execution, connector/provider writes, RAG/model runtime, default expansion, or full mockup activation be bundled here? Recommended answer: no.
