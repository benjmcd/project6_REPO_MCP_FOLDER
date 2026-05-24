# Candidate B Async Cancel/Retry/Resume Policy Selection

```yaml
milestone: candidate_b_async_cancel_retry_resume_policy_selection_v1
source_completion_failure_runtime: next_milestone_plans/Layer3_planning_docs/1009-cb-async-completion-failure-runtime.md
current_main_entry: e14ec1f9a78cb3ca85db2a3a83754de5413bf209
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_retry_policy_receipt_v1
selected_retry_policy_scope: server_owned_candidate_b_full_corpus_operator_workflow_failed_terminal_receipts
selected_retry_policy_mode: append_only_retry_policy_receipt_without_creating_retry_attempt_or_mutating_terminal_receipts
selected_retry_policy_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/retry/policy
existing_completion_failure_endpoint_reused_for_terminal_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/failure
existing_progress_checkpoint_endpoint_reused_for_checkpoint_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/progress/checkpoint
existing_worker_attempt_endpoint_reused_for_attempt_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt
existing_scheduler_lease_endpoint_reused_for_lease_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease
existing_queue_state_endpoint_reused_for_queue_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state
existing_history_endpoint_reused_for_run_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_run_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_retry_policy_receipt_model: append_only_retry_policy_receipt_without_mutating_completion_failure_progress_checkpoint_worker_attempt_scheduler_lease_queue_state_or_source_run_receipts
selected_retry_policy_receipt_binding: completion_failure_receipt_id,completion_failure_receipt_hash,completion_failure_authority_hash,terminal_outcome,terminal_outcome_hash,worker_attempt_receipt_id,worker_attempt_receipt_hash,worker_attempt_authority_hash,latest_progress_checkpoint_receipt_id,latest_progress_checkpoint_receipt_hash,queue_state_receipt_id,scheduler_lease_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,retry_policy_hash
selected_retry_policy_idempotency_basis: client_request_id_plus_retry_policy_authority_hash
terminal_outcome_required_for_retry: failed
completed_terminal_receipt_retry_rejected: true
missing_terminal_receipt_retry_rejected: true
stale_terminal_receipt_retry_rejected: true
terminal_conflict_retry_rejected: true
retry_attempt_creation_admitted_now: false
retry_queue_state_creation_admitted_now: false
retry_scheduler_lease_creation_admitted_now: false
retry_worker_attempt_creation_admitted_now: false
completion_failure_receipt_mutation_admitted: false
progress_checkpoint_receipt_mutation_admitted: false
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
cancel_runtime_selected_now: false
retry_policy_runtime_selected_after_sync: true
retry_attempt_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_retry_policy_receipt_v1
```

This freeze selects retry-policy authority as the next runtime-bearing slice after terminal completion/failure receipts. Current main can now record queue state, scheduler lease, worker attempt, progress checkpoint, and terminal completion/failure receipts. It still does not admit lifecycle mutation for cancel, retry, or resume.

The smallest useful next runtime is not a retry attempt. It is an append-only retry-policy receipt over an existing failed terminal receipt. The policy receipt should prove that a failed attempt is eligible or ineligible for retry using server-owned authority, without creating a new queue state, scheduler lease, worker attempt, progress checkpoint, terminal receipt, or source workflow-run mutation.

## Coherence Check

- Should cancel be first? Recommended answer: no. Current main has receipt authority but no admitted interruptible background execution target.
- Should resume be first? Recommended answer: no. Resume needs a checkpoint restart contract and must not be inferred from progress checkpoints alone.
- Should retry immediately create a new worker attempt? Recommended answer: no. First record retry-policy authority over a failed terminal receipt; retry-attempt lineage is a later slice.
- Should completed terminal receipts be retryable? Recommended answer: no. Retry policy applies only to failed terminal receipts and must reject completed terminal outcomes.
- Should retry policy inspect raw traces, raw logs, local paths, URLs, provider refs, connector destinations, or artifact bytes? Recommended answer: no. It should use operator-safe failure codes, phases, hashes, and redacted authority refs.
