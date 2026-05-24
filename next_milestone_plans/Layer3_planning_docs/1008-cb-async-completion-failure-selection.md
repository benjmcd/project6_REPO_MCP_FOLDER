# Candidate B Async Completion/Failure Authority Selection

```yaml
milestone: candidate_b_async_completion_failure_authority_selection_v1
source_progress_checkpoint_runtime: next_milestone_plans/Layer3_planning_docs/1007-cb-async-progress-checkpoint-runtime.md
current_main_entry: 2d439e6b98786d38ba7d846c3ab1415d7abe0439
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_completion_failure_receipt_v1
selected_completion_failure_scope: server_owned_candidate_b_full_corpus_operator_workflow_worker_attempts_with_progress_checkpoint_receipts
selected_completion_failure_mode: append_only_completion_failure_receipt_without_cancel_retry_resume_or_source_receipt_mutation
selected_completion_failure_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/completion/failure
existing_progress_checkpoint_endpoint_reused_for_checkpoint_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/progress/checkpoint
existing_worker_attempt_endpoint_reused_for_attempt_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt
existing_scheduler_lease_endpoint_reused_for_lease_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease
existing_queue_state_endpoint_reused_for_queue_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state
existing_history_endpoint_reused_for_run_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_run_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_completion_failure_receipt_model: append_only_terminal_receipt_without_mutating_progress_checkpoint_worker_attempt_scheduler_lease_queue_state_or_source_run_receipt
selected_completion_failure_receipt_binding: worker_attempt_receipt_id,worker_attempt_receipt_hash,worker_attempt_authority_hash,latest_progress_checkpoint_receipt_id,latest_progress_checkpoint_receipt_hash,latest_progress_checkpoint_authority_hash,progress_checkpoint_sequence,scheduler_lease_receipt_id,queue_state_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,terminal_outcome,terminal_outcome_hash
selected_completion_failure_idempotency_basis: client_request_id_plus_completion_failure_authority_hash
selected_terminal_outcomes: completed,failed
minimum_progress_checkpoint_required: true
pre_checkpoint_failure_runtime_selected_now: false
terminal_failure_payload_must_be_operator_safe: true
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
stale_progress_checkpoint_receipt_must_reject: true
stale_worker_attempt_receipt_must_reject: true
stale_scheduler_lease_receipt_must_reject: true
stale_queue_state_receipt_must_reject: true
stale_run_receipt_must_reject: true
stale_history_row_must_reject: true
missing_progress_checkpoint_receipt_must_reject: true
progress_checkpoint_receipt_mutation_admitted: false
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
completion_failure_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_completion_failure_receipt_v1
```

This freeze selects append-only terminal completion/failure receipts as the next runtime-bearing slice after progress-checkpoint receipts. Current main can record queue state, scheduler lease, worker attempt, and progress checkpoints, but it still has no terminal outcome receipt that lets downstream status distinguish a completed attempt from an operator-safe failure.

The next runtime must bind one existing worker-attempt receipt and the latest progress-checkpoint receipt for that attempt. It must write a separate terminal receipt and leave progress-checkpoint, worker-attempt, scheduler-lease, queue-state, and source workflow-run receipts unchanged.

## Coherence Check

- Should completion/failure execute Candidate B work? Recommended answer: no. It records terminal authority over already selected async lineage; job execution remains separately unselected.
- Should terminal receipt mutation change the original workflow-run or worker-attempt receipt? Recommended answer: no. The receipt must be append-only and status/history can project it later.
- Should failure payloads include raw traces, raw logs, local paths, URLs, provider refs, connector destinations, or artifact bytes? Recommended answer: no. Failures must use operator-safe codes, phases, hashes, and redacted refs.
- Should cancel, retry, or resume be implemented in this slice? Recommended answer: no. Cancel needs active execution semantics, retry needs terminal failure policy and new attempt admission, and resume needs a separate checkpoint resume contract.
