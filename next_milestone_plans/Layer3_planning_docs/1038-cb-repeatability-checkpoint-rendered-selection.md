# Candidate B Full-Corpus Operator Repeatability Checkpoint Rendered Control Selection

```yaml
milestone: candidate_b_full_corpus_operator_repeatability_checkpoint_rendered_control_selection_v1
source_repeatability_checkpoint_runtime: next_milestone_plans/Layer3_planning_docs/1037-cb-repeatability-checkpoint-runtime.md
current_main_entry: 349fb54afc70a86b3339718d1d18f35801211eef
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_operator_repeatability_checkpoint_rendered_control_v1
selected_rendered_control_scope: server_projection_consumer_for_candidate_b_repeatability_checkpoint_receipts
selected_repeatability_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/checkpoint
selected_repeatability_checkpoint_mode: append_only_repeatability_checkpoint_receipt_without_rerun_process_control_or_authority_mutation
selected_repeatability_checkpoint_action: record_candidate_b_full_corpus_operator_repeatability_checkpoint
selected_rendered_control_action: record_candidate_b_full_corpus_operator_repeatability_checkpoint_from_current_history_status_and_completion_monitor_projection
selected_rendered_control_model: per_workflow_history_row_button_enabled_only_when_status_and_completion_monitor_projection_are_current_and_downstream_proven
existing_history_panel_reused: true
existing_status_projection_reused: true
existing_completion_monitor_projection_reused: true
rendered_payload_binding: operator_workflow_receipt_id,operator_workflow_receipt_hash,row_hash,authority_basis_hash,history_hash,workflow_status_hash,completion_monitor_hash,runtime_root_lifecycle_receipt_id,bridge_receipt_id,downstream_proof_id,baseline_run_id,candidate_a_run_id,candidate_b_run_id,compare_target_set_hash,material_relative_name,operator_runbook_repeatability_steps
rendered_control_button_label: Record Repeatability Checkpoint
rendered_panel_required: true
headless_rendered_proof_required: true
headed_rendered_proof_required: true
response_model_validation_required: true
stale_status_or_completion_monitor_must_disable_or_fail_closed: true
non_downstream_proven_completion_monitor_must_disable_or_fail_closed: true
missing_runtime_root_lifecycle_must_disable_or_fail_closed: true
missing_bridge_or_downstream_proof_must_disable_or_fail_closed: true
operator_runbook_repeatability_steps_must_be_server_bounded: true
browser_supplied_local_authority_admitted: false
browser_supplied_raw_url_admitted: false
browser_supplied_command_admitted: false
browser_supplied_process_control_admitted: false
browser_supplied_stdout_stderr_admitted: false
browser_storage_authority_admitted: false
frontend_durable_authority_enabled: false
repeatability_checkpoint_receipt_mutation_admitted: false
workflow_receipt_mutation_admitted: false
process_execution_receipt_mutation_admitted: false
process_completion_result_mutation_admitted: false
adopted_result_downstream_proof_mutation_admitted: false
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
process_kill_cancel_retry_resume_admitted: false
raw_pid_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_operator_repeatability_checkpoint_rendered_control_v1
```

This selection admits the smallest rendered operator slice after the repeatability-checkpoint runtime. The control should live with the existing Candidate B full-corpus workflow history/status/completion-monitor surface, add a per-row `Record Repeatability Checkpoint` action only when the current server projections are sufficient, and render the checkpoint receipt/projection in an operator-safe panel.

The browser must remain a server-projection consumer. It can submit the already projected receipt ids and hashes needed by the admitted API, but it must not provide local paths, raw URLs, commands, process identifiers, stdout/stderr, artifact bytes, provider refs, connector destinations, model/RAG controls, selector mutations, browser-storage authority, or frontend durable authority.

## Next Runtime Requirements

The next rendered-control implementation must:

1. Add a contract endpoint resolver for `candidate_b_full_corpus_operator_repeatability_checkpoint_endpoint`.
2. Build the checkpoint payload from the selected workflow history row, current workflow status projection, current completion-monitor projection, runtime-root lifecycle projection, and bounded runbook step constants.
3. Disable or fail closed when status or completion-monitor projections are missing, stale, non-downstream-proven, or not bound to the selected row.
4. Record the checkpoint through the server endpoint only; no rerun, process control, or receipt mutation is admitted.
5. Render the checkpoint receipt hash/ref, authority hash, checkpoint state, and negative invariants without raw local paths or raw URLs.
6. Prove the rendered control in headless and headed Chrome.
7. Preserve baseline rollback, Candidate A semantics, current Candidate B eligible-PDF default scope, and full mockup non-activation.

## Coherence Check

- Is this a second checkpoint runtime? Recommended answer: no. The server runtime already exists; this selection only admits the rendered operator control that consumes it.
- Can the frontend decide repeatability on its own? Recommended answer: no. It can only submit projected hashes and display server receipts.
- Should the control run the corpus again to prove repeatability? Recommended answer: no. Corpus reruns remain a later operational trial slice if separately selected.
