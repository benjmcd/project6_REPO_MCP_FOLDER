# Candidate B Full-Corpus Repeatability Rerun Trial Selection

```yaml
milestone: candidate_b_full_corpus_repeatability_rerun_trial_selection_v1
source_repeatability_checkpoint_rendered_runtime: next_milestone_plans/Layer3_planning_docs/1039-cb-repeatability-checkpoint-rendered-runtime.md
current_main_entry: 963774f0545917dd9ae0e5cc7bdba35cb84012db
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_repeatability_rerun_trial_v1
selected_repeatability_trial_scope: compare_two_server_owned_candidate_b_full_corpus_operator_workflows_for_same_eligible_pdf_corpus
selected_repeatability_trial_model: append_only_trial_receipt_over_original_checkpoint_and_second_downstream_proven_workflow
selected_repeatability_trial_action: record_candidate_b_full_corpus_repeatability_rerun_trial
selected_repeatability_trial_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/rerun-trial
original_repeatability_checkpoint_required: true
original_workflow_receipt_required: true
original_workflow_status_required: proven
original_completion_monitor_state_required: completed_downstream_proven
rerun_workflow_receipt_required: true
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
operator_runbook_repeatability_steps_required: true
append_only_repeatability_trial_receipt_required: true
stale_original_checkpoint_must_reject: true
stale_original_status_or_monitor_must_reject: true
stale_rerun_status_or_monitor_must_reject: true
non_downstream_proven_original_or_rerun_must_reject: true
mismatched_corpus_identity_must_reject: true
mismatched_compare_target_set_must_reject: true
regression_or_delta_disposition_required: true
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
browser_supplied_local_authority_admitted: false
browser_supplied_raw_url_admitted: false
browser_supplied_command_admitted: false
browser_supplied_process_control_admitted: false
browser_supplied_stdout_stderr_admitted: false
browser_storage_authority_admitted: false
frontend_durable_authority_enabled: false
actual_corpus_processing_execution_admitted_by_trial_endpoint: false
actual_subprocess_spawn_admitted_by_trial_endpoint: false
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
next_exact_posture: candidate_b_full_corpus_repeatability_rerun_trial_v1
```

This selection admits the smallest repeatability trial after the rendered checkpoint control. The trial should not start a new Candidate B process or rerun corpus processing by itself. It should compare an original checkpointed Candidate B full-corpus operator workflow with a separately produced second Candidate B workflow run for the same eligible PDF corpus, then write an append-only repeatability trial receipt if both sides are current, downstream-proven, and bound to the same corpus identity and compare target set.

The second workflow run must come from already admitted server-owned workflow-run authority. The browser may supply only opaque receipt ids/hashes and operator decision constants needed to identify the original checkpoint and the rerun workflow; the server must reload workflow history, status, completion-monitor, checkpoint, and retained-artifact/downstream projections before deciding the trial.

## Next Runtime Requirements

The next runtime implementation must:

1. Add a server endpoint for `record_candidate_b_full_corpus_repeatability_rerun_trial`.
2. Load and validate the original repeatability checkpoint receipt.
3. Load and validate the original workflow status and completion-monitor projections.
4. Load and validate the rerun workflow status and completion-monitor projections.
5. Require both workflows to be proven and downstream-proven.
6. Require same corpus identity, compare target set, material relative name, and runtime-root lifecycle policy.
7. Compare retained artifact-family hashes, artifact role counts, Layer 3 downstream projections, and runbook repeatability steps.
8. Record regression/delta disposition in an append-only trial receipt without mutating either workflow or checkpoint receipt.
9. Reject stale, missing, mismatched, raw-leaking, or non-downstream-proven authority.
10. Preserve baseline rollback, Candidate A semantics, Candidate B eligible-PDF default scope, and full mockup non-activation.

## Coherence Check

- Is this endpoint the process rerunner? Recommended answer: no. It is the repeatability comparator and receipt writer over two already server-owned workflow runs.
- Can the browser provide file paths, URLs, commands, stdout/stderr, or artifact bytes to prove repeatability? Recommended answer: no. It can only identify server receipts; the server reloads authority.
- Does this promote Candidate B beyond eligible PDFs? Recommended answer: no. Broader corpus/default scope remains a later decision after repeatability evidence exists.
