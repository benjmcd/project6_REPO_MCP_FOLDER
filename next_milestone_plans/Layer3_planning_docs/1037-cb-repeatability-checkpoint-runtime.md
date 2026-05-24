# Candidate B Full-Corpus Operator Repeatability Checkpoint Runtime

```yaml
milestone: candidate_b_full_corpus_operator_repeatability_checkpoint_v1
source_repeatability_checkpoint_selection: next_milestone_plans/Layer3_planning_docs/1036-cb-repeatability-checkpoint-selection.md
current_main_entry: 194fd3c3bd225736869c4152b9e1e0d6d9859763
runtime_status: implemented
selected_repeatability_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/checkpoint
selected_repeatability_checkpoint_mode: append_only_repeatability_checkpoint_receipt_without_rerun_process_control_or_authority_mutation
selected_repeatability_checkpoint_action: record_candidate_b_full_corpus_operator_repeatability_checkpoint
selected_repeatability_checkpoint_model: bind_workflow_history_status_completion_monitor_and_downstream_receipts_to_repeatability_checkpoint
repeatability_checkpoint_runtime_selected: true
append_only_repeatability_checkpoint_receipt: true
exclusive_repeatability_checkpoint_per_authority: true
workflow_history_row_required: true
workflow_status_projection_required: true
workflow_status_required: proven
completion_monitor_projection_required: true
completion_monitor_state_required: completed_downstream_proven
runtime_root_lifecycle_receipt_required: true
bridge_receipt_required: true
downstream_proof_required: true
baseline_run_id_required: true
candidate_a_run_id_required: true
candidate_b_run_id_required: true
compare_target_set_hash_required: true
material_relative_name_required: true
operator_runbook_repeatability_steps_required: true
stale_history_hash_rejects: true
stale_row_hash_rejects: true
stale_workflow_status_rejects: true
stale_completion_monitor_rejects: true
non_downstream_proven_monitor_rejects: true
missing_or_mismatched_runtime_root_lifecycle_rejects: true
missing_or_mismatched_bridge_receipt_rejects: true
missing_or_mismatched_downstream_proof_rejects: true
repeatability_checkpoint_receipt_mutation_admitted: false
workflow_receipt_mutation_admitted: false
process_execution_receipt_mutation_admitted: false
process_completion_result_mutation_admitted: false
adopted_result_downstream_proof_mutation_admitted: false
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
process_kill_cancel_retry_resume_admitted: false
operator_supplied_command_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
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
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_operator_repeatability_checkpoint_rendered_control_selection_v1
```

The runtime records a server-owned, append-only repeatability checkpoint only after reloading current workflow history, rechecking the selected row, recomputing the workflow status projection, and recomputing the completion-monitor projection. It requires a proven workflow status and a `completed_downstream_proven` completion monitor before binding runtime-root lifecycle, bridge, downstream proof, compare target set, material name, baseline/Candidate A/Candidate B run ids, and the operator repeatability runbook steps.

This runtime does not rerun Candidate B, rerun Layer 3, spawn or control processes, mutate prior workflow/process/result/proof receipts, accept caller paths or URLs, expose raw process output, broaden Candidate B default scope, add provider writes, dispatch connectors, activate RAG/vector/model runtime, activate full mockup behavior, or create frontend durable authority.

## Grill-Me Coherence Check

1. Did this accidentally turn repeatability checkpointing into a corpus rerun?
   Recommended answer: no. The runtime only writes a checkpoint receipt after current server-owned receipt projections prove the selected run is downstream-proven.

2. Does the checkpoint depend on browser or operator-supplied local authority?
   Recommended answer: no. The request binds hashes and receipt ids; the server recomputes history, status, and completion-monitor authority and rejects raw path, URL, command, process, stdout, stderr, provider, connector, RAG/model, full mockup, and selector-mutation fields.

3. Is the selected next posture implementation or rendered operator control?
   Recommended answer: rendered operator control selection. The API/runtime is now present; a rendered checkpoint control remains a separate slice so browser surfaces stay server-projection consumers.
