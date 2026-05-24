# Candidate B Full-Corpus Repeatability Rerun Trial Rendered Control Runtime

```yaml
milestone: candidate_b_full_corpus_repeatability_rerun_trial_rendered_control_v1
source_repeatability_rerun_trial_rendered_selection: next_milestone_plans/Layer3_planning_docs/1042-cb-repeatability-rerun-trial-rendered-selection.md
current_main_entry: 191140c8c2ad3da72fed5c209bf41d3c8e2ac6f1
runtime_status: implemented
selected_rendered_control_mode: rendered_candidate_b_full_corpus_repeatability_rerun_trial_control
selected_repeatability_trial_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/rerun-trial
selected_repeatability_trial_mode: append_only_repeatability_rerun_trial_receipt_without_process_execution_or_authority_mutation
selected_repeatability_trial_action: record_candidate_b_full_corpus_repeatability_rerun_trial
rendered_control_runtime_selected: true
rendered_control_button_label: Record Rerun Trial
original_repeatability_checkpoint_required: true
original_workflow_status_required: proven
original_completion_monitor_state_required: completed_downstream_proven
rerun_workflow_status_required: proven
rerun_completion_monitor_state_required: completed_downstream_proven
same_compare_target_set_hash_required: true
same_material_relative_name_required: true
artifact_family_hash_comparison_required: true
layer3_downstream_projection_comparison_required: true
retained_artifact_role_counts_comparison_required: true
regression_or_delta_disposition_required: true
headless_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability rerun trial" --project=chromium PASS
headed_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability rerun trial" --project=chromium --headed PASS
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_checkpoint_selection_v1
```

The rendered control now lets an operator record a Candidate B full-corpus repeatability rerun-trial receipt from the existing workflow history panel. The operator first records an original repeatability checkpoint, then inspects a second downstream-proven workflow status and completion monitor for the same eligible PDF corpus, chooses an admitted regression or delta disposition, and posts only projected ids, hashes, material identity, and bounded runbook steps to the server-owned rerun-trial endpoint.

The browser remains a projection consumer. It does not start Candidate B, rerun Layer 3, mutate workflow/checkpoint/process/downstream receipts, store durable authority, expose raw paths or URLs, submit stdout/stderr/PIDs/artifact bytes, or broaden provider, connector, RAG/vector/model, full mockup, or default-scope behavior.

## Coherence Check

- Does the rendered control decide repeatability? Recommended answer: no. The server compares current original checkpoint, original status/monitor, rerun status/monitor, corpus identity, artifact-family, Layer 3, and retained role-count projections before writing the receipt.
- Can the selected rerun row be the same workflow as the original checkpoint? Recommended answer: no. The rendered control disables the rerun-trial action unless the selected workflow receipt differs from the checkpointed original.
- Is `no_regression_observed` valid when compared projections differ? Recommended answer: no. The server requires an explicit delta or regression disposition when artifact-family, Layer 3, or role-count hashes differ.
