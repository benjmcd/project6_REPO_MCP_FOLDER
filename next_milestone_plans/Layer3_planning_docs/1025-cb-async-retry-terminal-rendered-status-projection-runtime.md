# Candidate B Async Retry Terminal Rendered Status Projection Runtime

```yaml
milestone: candidate_b_async_retry_terminal_rendered_status_projection_v1
source_rendered_retry_terminal_projection_selection: next_milestone_plans/Layer3_planning_docs/1024-cb-async-retry-terminal-rendered-status-projection-selection.md
current_main_entry: e9f6b3c5d8dd0d32daf7dcced74904cc9d1ce143
runtime_status: implemented
selected_rendered_retry_terminal_projection_scope: operator_visible_read_only_status_history_projection_of_retry_terminal_status_projection
selected_rendered_retry_terminal_projection_mode: rendered_read_only_projection_without_receipt_creation_lineage_mutation_or_frontend_authority
selected_rendered_retry_terminal_projection_surfaces: status,history
existing_status_endpoint_reused_for_rendered_projection: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
existing_history_endpoint_reused_for_rendered_projection: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_rendered_status_control_reused: candidate-b-full-corpus-workflow-status-form
existing_rendered_status_mode_reused: rendered_candidate_b_full_corpus_operator_workflow_status_control
existing_rendered_history_control_reused: candidate-b-full-corpus-workflow-history-form
existing_rendered_history_mode_reused: rendered_candidate_b_full_corpus_operator_workflow_run_history_control
rendered_retry_terminal_projection_helper: candidateBRetryTerminalProjectionItems
rendered_status_projection_card: Retry Terminal Projection
rendered_status_e2e_target: e2e/layer3-workbench.spec.js::Layer 3 workbench inspects Candidate B full-corpus workflow status through rendered read-only control
rendered_history_e2e_target: e2e/layer3-workbench.spec.js::Layer 3 workbench refreshes Candidate B workflow history and inspects a selected run
rendered_retry_terminal_status_fields: retry_terminal_projection_state,retry_terminal_outcome,retry_completion_failure_receipt_id,retry_completion_failure_receipt_hash,retry_completion_failure_authority_hash,retry_worker_attempt_receipt_id,latest_retry_progress_checkpoint_receipt_id,terminal_failure_code,terminal_failure_phase
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
next_exact_posture: candidate_b_async_background_job_execution_boundary_selection_v1
```

The rendered Candidate B workflow status and history surfaces now display the server-provided retry terminal projection. Operators can inspect `not_recorded`, `completed`, and operator-safe `failed` terminal authority without raw API calls, and the browser does not compute, create, repair, or mutate retry authority.

The implementation reuses the existing read-only status/history controls and endpoints. It adds only rendered projection rows for server-provided retry terminal state, receipt ids/hashes, worker-attempt and progress-checkpoint authority, terminal outcome, operator-safe failure code/phase, and negative guardrails.

## Coherence Check

- Did this add a new API route or receipt mutation? Recommended answer: no. It is a rendered read-only projection over existing server responses.
- Does the browser become durable authority for retry terminal state? Recommended answer: no. It displays only server-provided fields.
- Does this admit background job execution, cancel, resume, provider writes, connector dispatch, model runtime, or full mockup activation? Recommended answer: no.
- What should come next? Recommended answer: select the bounded background job execution boundary before adding any real worker/process runtime.
