# Candidate B Full-Corpus Repeatability Acceptance Checkpoint Runtime

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_checkpoint_v1
source_repeatability_acceptance_checkpoint_selection: next_milestone_plans/Layer3_planning_docs/1044-cb-repeatability-acceptance-checkpoint-selection.md
current_main_entry: a928e288ee3a5aa32ad0a43a3ebe7eab11588caa
runtime_status: implemented
selected_acceptance_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-checkpoint
selected_acceptance_checkpoint_mode: append_only_acceptance_checkpoint_receipt_without_process_execution_or_authority_mutation
selected_acceptance_checkpoint_action: record_candidate_b_full_corpus_repeatability_acceptance_checkpoint
repeatability_acceptance_checkpoint_runtime_selected: true
original_repeatability_checkpoint_required: true
repeatability_rerun_trial_receipt_required: true
rerun_trial_state_required: repeatability_rerun_trial_recorded
original_workflow_status_required: proven
original_completion_monitor_state_required: completed_downstream_proven
rerun_workflow_status_required: proven
rerun_completion_monitor_state_required: completed_downstream_proven
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
regression_detected_must_block_acceptance: true
append_only_repeatability_acceptance_checkpoint_receipt: true
stale_original_checkpoint_rejects: true
stale_rerun_trial_rejects: true
mismatched_corpus_identity_rejects: true
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
raw_stdout_admitted: false
raw_stderr_admitted: false
raw_local_path_exposed: false
raw_url_exposed: false
frontend_durable_authority_enabled: false
default_scope_expansion_admitted: false
focused_pytest: py -3.12 -m pytest .\backend\tests\test_layer3_candidate_b_full_corpus_repeatability_acceptance_checkpoint.py -q PASS
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_rendered_control_selection_v1
```

The acceptance-checkpoint runtime records a server-owned append-only receipt over the original repeatability checkpoint and rerun-trial receipt. It reloads the rerun-trial receipt from receipt storage, validates the original checkpoint, revalidates original and rerun workflow status and completion-monitor projections, confirms the comparison disposition, and rejects stale, missing, raw-leaking, mismatched, or regression-blocked authority.

The endpoint is not a process runner or rendered start control. It does not execute Candidate B, spawn or control processes, mutate original checkpoint/rerun/workflow/process/downstream receipts, accept raw local paths or URLs, expose raw output, broaden Candidate B default scope, add provider writes, dispatch connectors, activate RAG/vector/model runtime, activate the full mockup, or create frontend durable authority.

## Coherence Check

- Does the acceptance checkpoint replace the rerun trial? Recommended answer: no. It requires the rerun-trial receipt and records a later acceptance receipt.
- Can `regression_detected_blocked` produce an accepted checkpoint? Recommended answer: no. It fails closed and blocks acceptance.
- Does this admit rendered acceptance controls? Recommended answer: no. The next exact posture is a separate rendered-control selection.
