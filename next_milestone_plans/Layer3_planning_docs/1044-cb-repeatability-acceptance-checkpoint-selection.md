# Candidate B Full-Corpus Repeatability Acceptance Checkpoint Selection

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_checkpoint_selection_v1
source_repeatability_rerun_trial_rendered_runtime: next_milestone_plans/Layer3_planning_docs/1043-cb-repeatability-rerun-trial-rendered-runtime.md
current_main_entry: 49875df0079e79984877f27fabbc38e9b38ec57a
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_repeatability_acceptance_checkpoint_v1
selected_acceptance_checkpoint_scope: append_only_operator_acceptance_checkpoint_over_original_repeatability_checkpoint_and_rerun_trial_receipts
selected_acceptance_checkpoint_mode: append_only_acceptance_checkpoint_receipt_without_process_execution_or_authority_mutation
selected_acceptance_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-checkpoint
selected_acceptance_checkpoint_action: record_candidate_b_full_corpus_repeatability_acceptance_checkpoint
selected_acceptance_checkpoint_model: bind_original_checkpoint_rerun_trial_comparison_and_operator_acceptance_decision
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
artifact_family_hash_comparison_required: true
layer3_downstream_projection_comparison_required: true
retained_artifact_role_counts_comparison_required: true
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
acceptance_checkpoint_receipt_required: true
operator_acceptance_decision_required: true
operator_runbook_repeatability_steps_required: true
stale_original_checkpoint_must_reject: true
stale_rerun_trial_must_reject: true
stale_workflow_status_or_monitor_must_reject: true
missing_original_checkpoint_must_reject: true
missing_rerun_trial_must_reject: true
mismatched_corpus_identity_must_reject: true
mismatched_compare_target_set_must_reject: true
mismatched_material_must_reject: true
regression_detected_must_block_acceptance: true
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
acceptance_checkpoint_receipt_mutation_admitted: false
original_repeatability_checkpoint_receipt_mutation_admitted: false
repeatability_rerun_trial_receipt_mutation_admitted: false
original_workflow_receipt_mutation_admitted: false
rerun_workflow_receipt_mutation_admitted: false
process_execution_receipt_mutation_admitted: false
process_completion_result_mutation_admitted: false
adopted_result_downstream_proof_mutation_admitted: false
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
process_kill_cancel_retry_resume_admitted: false
browser_triggered_process_start_admitted: false
operator_supplied_command_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
raw_pid_admitted: false
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
default_scope_expansion_admitted: false
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_checkpoint_v1
```

This selection freezes the first acceptance checkpoint after the rendered rerun-trial control. The operator now has enough server-owned evidence to record a repeatability acceptance decision only after an original repeatability checkpoint and a rerun-trial receipt both exist for the same eligible PDF corpus, compare target set, material, and runtime-root policy.

The checkpoint must be append-only. It should bind the original checkpoint receipt, the rerun-trial receipt, the comparison summary, the regression or delta disposition, and bounded repeatability runbook steps into one operator acceptance receipt. It must not rerun Candidate B, rerun Layer 3, spawn or control processes, mutate prior receipts, accept raw local paths or URLs, expose raw process output, broaden Candidate B default scope, add provider writes, dispatch connectors, activate RAG/vector/model runtime, activate the full mockup, or create frontend durable authority.

## Acceptance Semantics

The next runtime may record an accepted checkpoint only when the rerun-trial authority is current and the disposition is `no_regression_observed` or `delta_reviewed_no_regression`. A `regression_detected_blocked` disposition must produce a blocked acceptance outcome, not a successful repeatability acceptance.

The server must re-read the original checkpoint, rerun-trial receipt, workflow statuses, completion monitors, and comparison projections before deciding. Browser-provided values can identify server receipts, but they cannot prove acceptance by themselves.

## Next Runtime Requirements

1. Add the `record_candidate_b_full_corpus_repeatability_acceptance_checkpoint` server endpoint.
2. Load and validate the original repeatability checkpoint receipt.
3. Load and validate the repeatability rerun-trial receipt and its comparison summary.
4. Revalidate the original and rerun workflow status/completion-monitor authority.
5. Require matching corpus identity, compare target set, material name, and runtime-root lifecycle policy.
6. Accept only `no_regression_observed` or `delta_reviewed_no_regression` dispositions.
7. Block acceptance on `regression_detected_blocked`, stale authority, missing receipts, mismatches, raw leaks, or ambiguous comparison state.
8. Write one append-only acceptance checkpoint receipt with stable receipt hash and redacted provenance.
9. Preserve baseline rollback, Candidate A semantics, Candidate B eligible-PDF default scope, and full mockup non-activation.
10. Keep process execution, provider writes, connector dispatch, RAG/model runtime, browser-storage authority, and frontend durable authority out of scope.

## Grill-Me Coherence Check

- Does this checkpoint prove repeatability without a rerun-trial receipt? Recommended answer: no. It requires the original checkpoint plus the separately recorded rerun-trial receipt.
- Can an operator mark a detected regression as accepted repeatability? Recommended answer: no. `regression_detected_blocked` must block acceptance.
- Is this a process runner or rendered start control? Recommended answer: no. It is an append-only acceptance checkpoint over existing server-owned receipts.
