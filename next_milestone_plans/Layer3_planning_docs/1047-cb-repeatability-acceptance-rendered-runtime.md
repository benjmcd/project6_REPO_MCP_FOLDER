# Candidate B Full-Corpus Repeatability Acceptance Rendered Control Runtime

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_rendered_control_v1
source_repeatability_acceptance_rendered_selection: next_milestone_plans/Layer3_planning_docs/1046-cb-repeatability-acceptance-rendered-selection.md
current_main_entry: 35113ed4ba52f9193c21f45737ba0b1e79165ab5
runtime_status: implemented
selected_rendered_control_mode: rendered_candidate_b_full_corpus_repeatability_acceptance_checkpoint_control
selected_acceptance_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-checkpoint
selected_acceptance_checkpoint_mode: append_only_acceptance_checkpoint_receipt_without_process_execution_or_authority_mutation
selected_acceptance_checkpoint_action: record_candidate_b_full_corpus_repeatability_acceptance_checkpoint
rendered_control_runtime_selected: true
rendered_control_button_label: Record Acceptance Checkpoint
original_repeatability_checkpoint_required: true
repeatability_rerun_trial_receipt_required: true
rerun_trial_state_required: repeatability_rerun_trial_recorded
original_workflow_status_required: proven
original_completion_monitor_state_required: completed_downstream_proven
rerun_workflow_status_required: proven
rerun_completion_monitor_state_required: completed_downstream_proven
same_eligible_corpus_identity_required: true
same_compare_target_set_hash_required: true
same_material_relative_name_required: true
same_runtime_root_lifecycle_policy_required: true
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
regression_detected_must_disable_or_fail_closed: true
stale_original_checkpoint_must_disable_or_fail_closed: true
stale_rerun_trial_must_disable_or_fail_closed: true
operator_runbook_repeatability_steps_must_be_server_bounded: true
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
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_operator_closeout_selection_v1
```

Operators can now record the final repeatability acceptance-checkpoint receipt through the rendered Candidate B workflow history/status/monitor surface. The sequence is: refresh workflow history, inspect the original workflow status and completion monitor, record the original repeatability checkpoint, inspect the rerun workflow status and completion monitor, record the rerun-trial receipt, then click `Record Acceptance Checkpoint`.

The rendered control submits only server-projected checkpoint and rerun-trial receipt ids/hashes, original/rerun status and monitor hashes, an admitted non-regression disposition, the operator acceptance decision, and bounded runbook constants. The server writes the receipt and returns acceptance state, comparison summary, bound projections, and negative invariants.

## Coherence Check

- Does this control run Candidate B or Layer 3 again? Recommended answer: no. It records acceptance over existing server-owned receipts only.
- Can it accept `regression_detected_blocked`? Recommended answer: no. The UI disables or fails closed because only non-regression dispositions are admitted.
- Does it create frontend durable authority? Recommended answer: no. The browser is a projection consumer and posts bounded receipt/hash identifiers to the server endpoint.
