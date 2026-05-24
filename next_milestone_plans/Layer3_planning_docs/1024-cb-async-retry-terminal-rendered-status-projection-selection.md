# Candidate B Async Retry Terminal Rendered Status Projection Selection

```yaml
milestone: candidate_b_async_retry_terminal_rendered_status_projection_selection_v1
source_retry_terminal_status_projection_runtime: next_milestone_plans/Layer3_planning_docs/1023-cb-async-retry-terminal-status-projection-runtime.md
current_main_entry: 0297917e4b45dcca9d9e4153cc14b61e61e440ee
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_async_retry_terminal_rendered_status_projection_v1
selected_rendered_retry_terminal_projection_scope: operator_visible_read_only_status_history_projection_of_retry_terminal_status_projection
selected_rendered_retry_terminal_projection_mode: rendered_read_only_projection_without_receipt_creation_lineage_mutation_or_frontend_authority
selected_rendered_retry_terminal_projection_surfaces: status,history
existing_status_endpoint_reused_for_rendered_projection: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
existing_history_endpoint_reused_for_rendered_projection: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_rendered_status_control_reused: candidate-b-full-corpus-workflow-status-form
existing_rendered_status_mode_reused: rendered_candidate_b_full_corpus_operator_workflow_status_control
existing_rendered_history_control_reused: candidate-b-full-corpus-workflow-history-form
existing_rendered_history_mode_reused: rendered_candidate_b_full_corpus_operator_workflow_run_history_control
existing_rendered_status_e2e_target: e2e/layer3-workbench.spec.js::Layer 3 workbench inspects Candidate B full-corpus workflow status through rendered read-only control
selected_rendered_retry_terminal_status_fields: retry_terminal_projection_state,retry_completion_failure_receipt_id,retry_completion_failure_receipt_hash,retry_completion_failure_authority_hash,retry_worker_attempt_receipt_id,retry_worker_attempt_authority_hash,latest_retry_progress_checkpoint_receipt_id,latest_retry_progress_checkpoint_authority_hash,retry_terminal_outcome,retry_terminal_outcome_hash
selected_rendered_retry_terminal_failure_fields: operator_safe_retry_terminal_failure_code,operator_safe_retry_terminal_failure_phase
missing_retry_terminal_receipt_renders_not_recorded: true
completed_retry_terminal_receipt_renders_completed: true
failed_retry_terminal_receipt_renders_failed: true
stale_retry_terminal_receipt_must_fail_closed_server_side: true
ambiguous_retry_terminal_receipt_must_fail_closed_server_side: true
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
retry_terminal_receipt_creation_admitted_now: false
retry_completion_failure_receipt_mutation_admitted: false
retry_progress_checkpoint_receipt_mutation_admitted: false
retry_worker_attempt_receipt_mutation_admitted: false
retry_scheduler_lease_receipt_mutation_admitted: false
retry_queue_state_receipt_mutation_admitted: false
retry_policy_receipt_mutation_admitted: false
source_run_receipt_mutation_admitted: false
background_process_runtime_selected_now: false
job_execution_runtime_selected_now: false
cancel_runtime_selected_now: false
resume_runtime_selected_now: false
expiry_enforcement_runtime_selected_now: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
proof_required_headless_chrome: true
proof_required_headed_chrome: true
selector_mutation_performed: false
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_async_retry_terminal_rendered_status_projection_v1
```

This freeze selects the rendered operator proof for the retry terminal status projection that current main already exposes through the Candidate B workflow status and history APIs. The implementation target is intentionally narrow: show the existing `retry_terminal_status_projection` in the already-rendered read-only status/history controls so operators do not need raw API inspection to verify retry completion or failure authority.

The implementation must reuse existing status and history endpoints and controls. Missing retry terminal authority should render `not_recorded`; completed and failed retry terminal receipts should render only redacted receipt, outcome, progress-checkpoint, worker-attempt, and operator-safe failure fields; stale or ambiguous retry terminal authority must remain a server-side fail-closed response.

This slice does not admit new receipt creation, retry-lineage mutation, job execution, background processing, cancel/resume, expiry enforcement, broader Candidate B default scope, provider object writes, connector dispatch, RAG/vector/model runtime, full mockup activation, raw path or URL exposure, artifact bytes, browser storage authority, or frontend durable authority.

## Coherence Check

- Should the browser compute or repair retry terminal authority? Recommended answer: no. It should render only the server-provided projection.
- Should the rendered proof add a new API route? Recommended answer: no. It should reuse the existing status and history endpoints.
- Should missing terminal authority block the rendered status/history controls? Recommended answer: no. Missing authority renders `not_recorded`; stale or ambiguous authority fails closed server-side.
- Should this selection admit cancel, resume, background execution, or job execution? Recommended answer: no. This is a read-only rendered projection over already-recorded terminal authority.
