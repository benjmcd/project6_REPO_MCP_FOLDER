# Candidate B Full-Corpus Repeatability Rerun Trial Runtime

```yaml
milestone: candidate_b_full_corpus_repeatability_rerun_trial_v1
source_repeatability_rerun_trial_selection: next_milestone_plans/Layer3_planning_docs/1040-cb-repeatability-rerun-trial-selection.md
current_main_entry: d5ca6cb22b4aa764207a7314d85ce6da2c4e10fe
runtime_status: implemented_branch_local
selected_repeatability_trial_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/rerun-trial
selected_repeatability_trial_mode: append_only_repeatability_rerun_trial_receipt_without_process_execution_or_authority_mutation
selected_repeatability_trial_action: record_candidate_b_full_corpus_repeatability_rerun_trial
selected_repeatability_trial_model: append_only_trial_receipt_over_original_checkpoint_and_second_downstream_proven_workflow
repeatability_rerun_trial_runtime_selected: true
original_repeatability_checkpoint_required: true
original_workflow_status_required: proven
original_completion_monitor_state_required: completed_downstream_proven
rerun_workflow_status_required: proven
rerun_completion_monitor_state_required: completed_downstream_proven
same_baseline_run_id_required: true
same_candidate_a_run_id_required: true
same_candidate_b_run_id_or_same_eligible_corpus_identity_required: true
same_compare_target_set_hash_required: true
same_material_relative_name_required: true
same_runtime_root_lifecycle_policy_required: true
artifact_family_hash_comparison_required: true
layer3_downstream_projection_comparison_required: true
retained_artifact_role_counts_comparison_required: true
regression_or_delta_disposition_required: true
append_only_repeatability_rerun_trial_receipt: true
exclusive_repeatability_rerun_trial_per_authority: true
stale_original_checkpoint_rejects: true
stale_original_status_or_monitor_rejects: true
stale_rerun_status_or_monitor_rejects: true
non_downstream_proven_original_or_rerun_rejects: true
mismatched_corpus_identity_rejects: true
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
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_repeatability_rerun_trial_rendered_control_selection_v1
```

This runtime adds the server-owned repeatability rerun-trial comparator. It does not run Candidate B, spawn a subprocess, control an existing process, or mutate either workflow. It reloads the original repeatability checkpoint, original workflow status and completion monitor, and rerun workflow status and completion monitor before writing one append-only trial receipt.

The trial binds both workflows to baseline and Candidate A run ids, compare target set hash, material relative name, and runtime-root lifecycle policy. Candidate B run ids may match directly; otherwise the eligible corpus identity must match. Artifact-family hash, retained artifact role counts, and Layer 3 downstream projection hashes are compared and recorded with an explicit regression or delta disposition.

## Runtime Proof

- `python -m py_compile .\backend\app\services\layer3_candidate_b_full_corpus_repeatability_rerun_trial.py .\backend\app\api\layer3.py .\backend\tests\test_layer3_candidate_b_full_corpus_repeatability_rerun_trial.py` PASS
- `pytest .\backend\tests\test_layer3_candidate_b_full_corpus_repeatability_rerun_trial.py .\backend\tests\test_layer3_readiness_contract.py .\backend\tests\test_layer3_bootstrap_contract.py -q` PASS

## Coherence Check

- Is the rerun-trial endpoint the rerun executor? Recommended answer: no. It is a comparator over two already server-owned, downstream-proven workflow receipts.
- Should a mismatch in corpus identity, compare target set, material name, or runtime-root lifecycle policy be recorded as a trial? Recommended answer: no. Those are authority mismatch blockers, not acceptable deltas.
- Can artifact-family or downstream projection deltas be recorded? Recommended answer: yes, but only with an explicit regression or delta disposition.
