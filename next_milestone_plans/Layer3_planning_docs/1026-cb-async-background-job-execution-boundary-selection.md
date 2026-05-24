# Candidate B Async Background Job Execution Boundary Selection

```yaml
milestone: candidate_b_async_background_job_execution_boundary_selection_v1
source_rendered_retry_terminal_projection_runtime: next_milestone_plans/Layer3_planning_docs/1025-cb-async-retry-terminal-rendered-status-projection-runtime.md
current_main_entry: 9c88315b06839c921ac5fbecc616b8dc4591be18
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_background_job_execution_boundary_v1
selected_background_execution_boundary_scope: server_owned_candidate_b_full_corpus_workflow_execution_boundary_over_existing_queue_lease_attempt_progress_terminal_receipts
selected_background_execution_boundary_mode: execution_boundary_receipt_without_process_start_or_job_execution
selected_background_execution_boundary_source_lineage: operator_workflow_receipt,queue_state_receipt,scheduler_lease_receipt,worker_attempt_receipt,progress_checkpoint_receipt,completion_failure_receipt,retry_policy_receipt,retry_queue_state_receipt,retry_scheduler_lease_receipt,retry_worker_attempt_receipt,retry_progress_checkpoint_receipt,retry_completion_failure_receipt
selected_background_execution_boundary_preconditions: configured_receipt_authority,current_history_row,current_scheduler_lease,current_worker_attempt,latest_progress_checkpoint,terminal_projection_visibility
selected_background_execution_boundary_outputs: execution_boundary_receipt,execution_boundary_receipt_hash,execution_boundary_authority_hash,operator_safe_execution_state,status_history_projection_fields
selected_background_execution_boundary_state_values: not_started,boundary_recorded,blocked
status_history_projection_required_after_boundary: true
rendered_operator_projection_required_after_boundary: true
headless_rendered_proof_required_after_boundary: true
headed_rendered_proof_required_after_boundary: true
live_http_or_isolated_runtime_proof_required_after_boundary: true
stale_history_row_must_reject: true
stale_scheduler_lease_must_reject: true
stale_worker_attempt_must_reject: true
stale_progress_checkpoint_must_reject: true
terminal_receipt_conflict_must_reject: true
background_process_runtime_selected_after_sync: true
job_execution_runtime_selected_after_sync: true
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
actual_subprocess_spawn_admitted_now: false
actual_corpus_processing_execution_admitted_now: false
browser_triggered_process_start_admitted: false
operator_supplied_command_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
default_scope_expansion_admitted: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_background_job_execution_boundary_v1
```

This freeze selects the first Candidate B background execution boundary before any real worker/process runtime is added. Current main has server-owned queue-state, scheduler-lease, worker-attempt, progress-checkpoint, completion/failure, retry lineage, retry terminal projection, and rendered operator inspection authority, but it still does not admit a background process or actual job execution.

The selected next runtime should record a server-owned execution-boundary receipt over the existing async lineage. It should prove that the current workflow row, queue/lease/attempt/progress/terminal authority, and retry terminal projection are coherent enough to become a future execution target. It must fail closed for stale or conflicting history rows, scheduler leases, worker attempts, progress checkpoints, or terminal receipts.

This selection does not admit actual subprocess spawning, corpus processing execution, browser-triggered process start, operator-supplied commands, operator-supplied paths or URLs, provider writes, connector dispatch, RAG/vector/model runtime, full mockup activation, cancel/resume, expiry enforcement, raw traces/logs, raw refs, artifact bytes, browser storage authority, or frontend durable authority.

## Coherence Check

- Should this selection start a background worker? Recommended answer: no. It selects the boundary that must land before any process runtime.
- Should the boundary mutate workflow, queue, lease, worker-attempt, progress, terminal, or retry receipts? Recommended answer: no. It should write a separate boundary receipt.
- Should the browser provide commands, paths, URLs, or runtime roots? Recommended answer: no. The server must resolve authority from configured receipt state.
- What should come next? Recommended answer: implement the server-owned background job execution boundary receipt and projection, then separately select real worker/process execution only if that boundary is proven.
