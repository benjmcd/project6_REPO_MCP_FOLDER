# Candidate B Broader Eligible Corpus Default Scope Operator Repeatability Trial Selection

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial_selection_v1
source_consumption_chain_closeout_readiness: next_milestone_plans/Layer3_planning_docs/1099-cb-broader-eligible-corpus-default-scope-consumption-chain-closeout-readiness.md
current_main_entry: 5e47b48ee662eea610a146c2560a567af7302271
entry_decision: freeze_only
runtime_status: not_implemented
rendered_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_next_runtime_target: candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial_runtime_v1
selected_trial_scope: compare_two_server_owned_broader_default_scope_use_status_projections_for_same_receipt_bound_selected_classes
selected_trial_model: append_only_trial_receipt_over_original_and_repeat_use_status_authority_without_processing_execution
selected_trial_action: record_candidate_b_broader_scope_operator_repeatability_trial
selected_trial_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/operator-repeatability/trial
original_use_status_required: available
repeat_use_status_required: available
original_use_receipt_required: true
repeat_use_receipt_required: true
same_readiness_audit_id_required: true
same_readiness_audit_hash_required: true
same_runtime_selection_receipt_required: true
same_selector_use_receipt_required: true
same_selector_use_status_hash_required: true
same_selector_activation_receipt_required: true
same_activation_consumption_receipt_required: true
same_selected_scope_classes_required: true
same_selected_scope_classes_hash_required: true
use_status_hash_comparison_required: true
receipt_chain_hash_comparison_required: true
negative_invariants_hash_required: true
operator_repeatability_disposition_required: true
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
append_only_repeatability_trial_receipt_required: true
exclusive_trial_per_original_repeat_authority_pair_required: true
stale_original_use_status_must_reject: true
stale_repeat_use_status_must_reject: true
missing_use_receipt_must_reject: true
mismatched_selected_classes_must_reject: true
mismatched_readiness_audit_must_reject: true
mismatched_runtime_or_selector_receipts_must_reject: true
non_available_original_or_repeat_status_must_reject: true
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_document_processing_engine_preserved: candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only
candidate_b_visual_lane_preserved: candidate_b_opendataloader_page_evidence_v1_explicit_only
selected_classes_default_scope_only: true
non_selected_class_default: baseline
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
auth_security_expansion_enabled: false
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial_runtime_v1
```

This selection admits the smallest broader eligible-corpus default-scope repeatability trial after the consumption-chain closeout. The trial is not a process runner and does not broaden defaults. It should compare two server-owned use-status projections for the same receipt-bound selected classes, then write an append-only trial receipt only if both projections are current, available, redacted, and bound to the same readiness, runtime, selector-use, selector-activation, activation-consumption, consumption-use, and selected-class authority.

The browser may supply only opaque receipt ids, hashes, fixed operator decisions, selected-class identifiers, and disposition fields needed to identify the original and repeat status projections. The server must reload and revalidate all receipt/status authority before deciding the trial. Non-selected classes remain baseline, and the eligible/effective PDF Candidate B default remains unchanged outside separately selected broader-scope receipts.

## Next Runtime Requirements

The next runtime implementation must:

1. Add a server endpoint for `record_candidate_b_broader_scope_operator_repeatability_trial`.
2. Load and validate the original consumption-receipt use-status projection.
3. Load and validate the repeat consumption-receipt use-status projection.
4. Require both projections to be `available`.
5. Require the same readiness audit id/hash, runtime-selection receipt, selector-use receipt, selector-use status hash, selector-activation receipt, activation-consumption receipt, and exact selected scope classes.
6. Compare use-status hashes, receipt-chain hashes, selected-class hashes, and negative-invariant hashes.
7. Record an accepted or blocked operator disposition in an append-only trial receipt without mutating either use receipt or default-scope authority.
8. Reject stale, missing, mismatched, raw-leaking, non-available, or browser-owned authority.
9. Preserve baseline rollback, Candidate A semantics, Candidate B eligible/effective PDF default scope, and explicit Candidate B visual-lane semantics.
10. Avoid source/runtime expansion, process execution, provider writes, connector dispatch, RAG/vector/model runtime, auth/security expansion, and full mockup activation.

## Coherence Check

- Is this endpoint the broader-corpus process rerunner? Recommended answer: no. It is a repeatability comparator and receipt writer over two already server-owned broader-scope use-status projections.
- Does this make Candidate B broadly default for every corpus class? Recommended answer: no. It only evaluates receipt-bound selected classes; non-selected classes remain baseline.
- Can the browser provide paths, URLs, commands, stdout/stderr, artifact bytes, or process state to prove repeatability? Recommended answer: no. It can identify server receipts only; the server reloads authority.
- Why select this before rendered UI? Recommended answer: rendered repeatability controls would otherwise risk frontend authority. The server-owned append-only trial contract must exist first.
