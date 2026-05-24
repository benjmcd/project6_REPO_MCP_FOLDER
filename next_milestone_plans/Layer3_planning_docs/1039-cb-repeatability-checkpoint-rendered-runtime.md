# Candidate B Full-Corpus Operator Repeatability Checkpoint Rendered Control Runtime

```yaml
milestone: candidate_b_full_corpus_operator_repeatability_checkpoint_rendered_control_v1
source_repeatability_checkpoint_rendered_selection: next_milestone_plans/Layer3_planning_docs/1038-cb-repeatability-checkpoint-rendered-selection.md
current_main_entry: e216becebf2745a976e6b92a1b57b1907bc0b939
runtime_status: implemented
selected_rendered_control_mode: rendered_candidate_b_full_corpus_operator_repeatability_checkpoint_control
selected_repeatability_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/checkpoint
selected_repeatability_checkpoint_action: record_candidate_b_full_corpus_operator_repeatability_checkpoint
rendered_control_runtime_selected: true
rendered_control_button_label: Record Repeatability Checkpoint
history_status_completion_monitor_projection_required: true
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
stale_status_or_completion_monitor_disables_or_fails_closed: true
non_downstream_proven_monitor_disables_or_fails_closed: true
headless_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability checkpoint" --project=chromium PASS
headed_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability checkpoint" --project=chromium --headed PASS
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_repeatability_rerun_trial_selection_v1
```

The rendered workbench now exposes the already admitted Candidate B repeatability checkpoint as a per-history-row operator control. The button remains disabled until the selected row has a current proven workflow-status projection and a current downstream-proven completion-monitor projection. The browser submits only receipt ids, hashes, run ids, material name, and the fixed repeatability runbook steps; the server still reloads history, status, and completion monitor authority before writing any append-only checkpoint receipt.

This runtime does not rerun Candidate B, start or control any process, mutate earlier workflow/process/proof receipts, accept browser-supplied local paths or URLs, expose raw output, write provider objects, dispatch connectors, activate RAG/vector/model runtime, activate full mockup behavior, broaden default scope, or grant frontend durable authority.
