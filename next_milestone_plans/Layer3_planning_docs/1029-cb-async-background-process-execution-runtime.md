# Candidate B Async Background Process Execution Runtime

```yaml
milestone: candidate_b_async_background_process_execution_v1
source_process_execution_selection: next_milestone_plans/Layer3_planning_docs/1028-cb-async-background-process-execution-selection.md
current_main_entry: 826b27131f26d7fdcbb5da00e9151f6ab8fe6549
runtime_status: implemented
selected_process_execution_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/process/execution
selected_process_execution_mode: server_owned_allowlisted_process_start_with_redacted_receipt_and_no_browser_command_authority
selected_process_execution_action: record_candidate_b_async_background_process_execution
selected_process_execution_scope: server_owned_candidate_b_full_corpus_operator_workflow_process_over_existing_execution_boundary_receipt
selected_process_execution_allowlisted_command_family: tools/run_candidate_b_full_corpus_operator_workflow.py
selected_process_execution_arguments_authority: server_resolved_receipt_ids_and_configured_runtime_roots_only
selected_process_execution_outputs: process_execution_receipt,process_execution_receipt_hash,process_execution_authority_hash,redacted_process_status_projection
status_history_projection_after_process_start: true
rendered_operator_projection_after_process_start: true
stale_history_row_must_reject: true
stale_execution_boundary_must_reject: true
missing_execution_boundary_must_reject: true
missing_runtime_dependency_must_reject: true
non_allowlisted_command_must_reject: true
source_run_receipt_mutation_admitted: false
execution_boundary_receipt_mutation_admitted: false
background_process_runtime_selected_now: true
job_execution_runtime_selected_now: false
actual_subprocess_spawn_admitted_now: true
actual_corpus_processing_execution_admitted_now: false
browser_triggered_process_start_admitted: false
operator_supplied_command_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_exception_trace_admitted: false
raw_log_excerpt_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
selector_mutation_performed: false
implementation_scope: backend_service_api_readiness_status_history_rendered_operator_control_focused_tests
next_exact_posture: candidate_b_async_process_completion_result_adoption_selection_v1
```

This runtime implements the selected process-start slice. A browser/operator request can select only a current workflow row and its current execution-boundary receipt. The server derives the allowlisted process command from current-main code, configured receipt authority, and server-owned runtime context, then writes an append-only process-execution receipt plus a redacted status projection.

The implementation intentionally stops before job completion or result adoption. It proves that a real server-owned subprocess start is admitted and visible without exposing raw paths, URLs, stdout, stderr, exception traces, local roots, provider keys, connector destinations, model/RAG controls, browser storage authority, or frontend durable authority.

## Coherence Check

- What authority starts the process? The server-owned allowlisted `tools/run_candidate_b_full_corpus_operator_workflow.py` command family, not a browser-supplied command.
- What does the receipt prove? It proves process-start authority, process-start receipt persistence, status/history projection, rendered operator visibility, and fail-closed stale-boundary behavior.
- What does it not prove? It does not prove job completion, result adoption, new Candidate B corpus generation, broader default scope, provider object writes, connector dispatch, RAG/vector/model runtime, or full mockup activation.
- What comes next? Select `candidate_b_async_process_completion_result_adoption_selection_v1` only after process-start receipts and redacted projections are stable.
