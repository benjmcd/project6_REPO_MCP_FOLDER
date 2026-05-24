# Candidate B Async Progress Checkpoint Authority Selection

```yaml
milestone: candidate_b_async_progress_checkpoint_authority_selection_v1
source_worker_attempt_runtime: next_milestone_plans/Layer3_planning_docs/1005-cb-async-worker-attempt-runtime.md
current_main_entry: 7ff4bbea39d6b989f0e6d50a7d1a844107125798
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_progress_checkpoint_receipt_v1
selected_progress_checkpoint_scope: server_owned_candidate_b_full_corpus_operator_workflow_worker_attempt_receipts
selected_progress_checkpoint_mode: append_only_progress_checkpoint_receipt_without_completion_or_cancel_retry_resume
selected_progress_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/progress/checkpoint
existing_worker_attempt_endpoint_reused_for_source_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/worker/attempt
existing_scheduler_lease_endpoint_reused_for_lease_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/scheduler/lease
existing_queue_state_endpoint_reused_for_queue_authority: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/queue/state
existing_history_endpoint_reused_for_run_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_run_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_progress_checkpoint_receipt_model: append_only_progress_checkpoint_receipt_without_mutating_worker_attempt_scheduler_lease_queue_state_or_source_run_receipt
selected_progress_checkpoint_receipt_binding: worker_attempt_receipt_id,worker_attempt_receipt_hash,worker_attempt_authority_hash,scheduler_lease_receipt_id,queue_state_receipt_id,operator_workflow_receipt_id,operator_workflow_receipt_hash,progress_checkpoint_sequence,progress_checkpoint_hash
selected_progress_checkpoint_sequence_model: monotonically_increasing_append_only_sequence_per_worker_attempt
selected_progress_checkpoint_idempotency_basis: client_request_id_plus_progress_checkpoint_authority_hash
stale_worker_attempt_receipt_must_reject: true
stale_scheduler_lease_receipt_must_reject: true
stale_queue_state_receipt_must_reject: true
stale_run_receipt_must_reject: true
stale_history_row_must_reject: true
missing_worker_attempt_receipt_must_reject: true
worker_attempt_receipt_mutation_admitted: false
scheduler_lease_receipt_mutation_admitted: false
queue_state_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
progress_checkpoint_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
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
next_exact_posture: candidate_b_async_progress_checkpoint_receipt_v1
```

This freeze selects progress-checkpoint receipts as the next runtime-bearing slice after worker-attempt receipts. Current main can now record an initial worker-attempt identity, but it still has no append-only checkpoint sequence that can project running progress before terminal completion, cancellation, retry, or resume authority is admitted.

The next runtime must create server-owned append-only progress-checkpoint receipts over an existing worker-attempt receipt. It must bind worker-attempt, scheduler-lease, queue-state, current workflow-run history, and operator workflow-run authority without mutating any prior receipt or completing the job.

## Coherence Check

- Should a progress checkpoint execute Candidate B work? Recommended answer: no. It records bounded progress authority and lineage; job execution remains separately selected.
- Should a progress checkpoint complete the workflow? Recommended answer: no. Completion/failure needs terminal-state authority after checkpoint receipts exist.
- Should cancel, retry, or resume be implemented in this slice? Recommended answer: no. They need checkpoint and terminal-state semantics before mutation behavior is admitted.
- Should checkpoint payloads expose raw paths, URLs, provider refs, connector destinations, RAG/vector/model inputs, or browser storage authority? Recommended answer: no. Progress must remain redacted server-owned authority.
