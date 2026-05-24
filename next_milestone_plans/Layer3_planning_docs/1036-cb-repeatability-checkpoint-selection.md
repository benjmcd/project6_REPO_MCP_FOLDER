# Candidate B Full-Corpus Operator Repeatability Checkpoint Selection

```yaml
milestone: candidate_b_full_corpus_operator_repeatability_checkpoint_selection_v1
source_completion_monitor_runtime: next_milestone_plans/Layer3_planning_docs/1035-cb-async-operator-workflow-completion-monitor-runtime.md
prior_repeatability_completion_audit: next_milestone_plans/Layer3_planning_docs/989-cb-repeatability-completion-audit.md
current_main_entry: 89682c0dd533977bdd13e5e18f6fa34f757a8002
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_full_corpus_operator_repeatability_checkpoint_v1
selected_repeatability_checkpoint_scope: append_only_operator_repeatability_checkpoint_over_server_owned_candidate_b_workflow_receipts
selected_repeatability_checkpoint_mode: append_only_repeatability_checkpoint_receipt_without_rerun_process_control_or_authority_mutation
selected_repeatability_checkpoint_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/checkpoint
selected_repeatability_checkpoint_action: record_candidate_b_full_corpus_operator_repeatability_checkpoint
selected_repeatability_checkpoint_model: bind_workflow_history_status_completion_monitor_and_downstream_receipts_to_repeatability_checkpoint
historical_repeatability_completion_audit_remains_valid: true
post_monitor_repeatability_checkpoint_required: true
workflow_history_row_required: true
workflow_status_projection_required: true
completion_monitor_projection_required: true
completion_monitor_state_required: completed_downstream_proven
process_execution_projection_required: true
process_completion_result_projection_required: true
adopted_result_downstream_proof_projection_required: true
runtime_root_lifecycle_receipt_required: true
bridge_receipt_required: true
downstream_proof_required: true
baseline_run_id_required: true
candidate_a_run_id_required: true
candidate_b_run_id_required: true
compare_target_set_hash_required: true
material_relative_name_required: true
artifact_family_summary_if_present_required: true
operator_runbook_repeatability_steps_required: true
stale_history_hash_must_reject: true
stale_row_hash_must_reject: true
stale_workflow_status_must_reject: true
stale_completion_monitor_must_reject: true
missing_completion_monitor_must_reject: true
non_downstream_proven_monitor_must_reject: true
missing_or_mismatched_runtime_root_lifecycle_must_reject: true
missing_or_mismatched_bridge_receipt_must_reject: true
missing_or_mismatched_downstream_proof_must_reject: true
repeatability_checkpoint_receipt_mutation_admitted: false
workflow_receipt_mutation_admitted: false
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
next_exact_posture: candidate_b_full_corpus_operator_repeatability_checkpoint_v1
```

This selection does not reopen generic Candidate B proof churn. The older repeatability completion audit remains valid for its admitted live HTTP/operator-status scope. The new requirement is narrower: after the async process-execution, process-completion/result, adopted-result downstream proof, and read-only completion monitor chain, the operator needs one receipt-bound checkpoint that proves the currently selected workflow row is repeatable from server-owned evidence.

The checkpoint runtime should bind the workflow history row, workflow status projection, completion monitor projection, runtime-root lifecycle receipt, bridge receipt, downstream proof, compare target set, baseline/Candidate A/Candidate B run ids, and operator runbook repeatability steps. It should write only an append-only checkpoint receipt after revalidating current server authority. It should not rerun Candidate B, rerun Layer 3, spawn or control processes, mutate prior receipts, accept local paths or raw URLs, expose raw process output, broaden Candidate B default scope, add provider writes, dispatch connectors, activate RAG/vector/model runtime, activate the full mockup, or create frontend durable authority.

## Relationship To Prior Repeatability Audit

`989-cb-repeatability-completion-audit.md` closed the earlier full-corpus repeatability scope around the live HTTP runner, durable workflow receipts, status endpoint, and rendered status control. That completion remains true for the prior admitted scope.

`1035-cb-async-operator-workflow-completion-monitor-runtime.md` adds a newer async completion-monitor projection over the richer server-owned workflow receipt chain. This selection records the smallest next checkpoint needed to make that newer chain repeatability-auditable without redoing corpus execution or weakening the prior completion audit.

## Next Runtime Requirements

The next runtime must:

1. Read the current server-owned workflow history and selected row.
2. Revalidate the row against the submitted workflow receipt hash, row hash, authority-basis hash, and history hash.
3. Revalidate the existing workflow status projection and completion monitor projection.
4. Require `completion_monitor_state: completed_downstream_proven`.
5. Bind runtime-root lifecycle, bridge, downstream proof, compare target set, material name, and baseline/Candidate A/Candidate B run ids.
6. Produce one append-only repeatability checkpoint receipt with a stable receipt hash and redacted provenance.
7. Fail closed on stale, missing, mismatched, non-downstream-proven, raw-leaking, or ambiguous authority.
8. Preserve baseline rollback, Candidate A semantics, and Candidate B eligible-PDF default scope.
9. Preserve rendered/operator surfaces as server-projection consumers only.
10. Keep all process control, rerun, provider, connector, RAG/model, full mockup, browser-storage, and frontend durable authority out of scope.

## Grill-Me Coherence Check

1. Does this contradict the earlier repeatability completion audit?
   Recommended answer: no. The earlier audit remains complete for its admitted live HTTP/status scope. This selection covers the newer async completion-monitor chain added afterward.

2. Should the checkpoint rerun the full corpus to prove repeatability?
   Recommended answer: no. This slice is receipt-bound repeatability checkpointing, not a corpus rerun. Corpus-scale reruns remain a later operational trial if separately selected.

3. Should the browser be allowed to provide runtime roots or local paths for repeatability?
   Recommended answer: no. The checkpoint must revalidate server-owned receipt authority and fail closed on browser-supplied local authority.

4. Is this selecting broader Candidate B default behavior?
   Recommended answer: no. Candidate B remains limited to the current eligible/effective PDF scope with baseline rollback and Candidate A semantics preserved.

## Stop Condition

Stop after this selection unless current main is synced and the exact runtime slice `candidate_b_full_corpus_operator_repeatability_checkpoint_v1` is selected for implementation.
