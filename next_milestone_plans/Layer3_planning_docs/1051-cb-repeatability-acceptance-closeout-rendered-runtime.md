# Candidate B Full-Corpus Repeatability Acceptance Closeout Rendered Control Runtime

```yaml
milestone: candidate_b_full_corpus_repeatability_acceptance_closeout_rendered_control_v1
source_repeatability_acceptance_closeout_rendered_selection: next_milestone_plans/Layer3_planning_docs/1050-cb-repeatability-acceptance-closeout-rendered-selection.md
current_main_entry: e098ee10223f6f6edac6c6026ae4d26bad88cfeb
runtime_status: implemented
selected_rendered_control_mode: rendered_candidate_b_full_corpus_repeatability_acceptance_closeout_control
selected_rendered_control_scope: operator_visible_record_and_inspect_acceptance_closeout_receipt
rendered_control_button_label: Record Acceptance Closeout
source_closeout_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/repeatability/acceptance-closeout
selected_closeout_action: record_candidate_b_full_corpus_repeatability_acceptance_operator_closeout
repeatability_acceptance_checkpoint_receipt_required: true
acceptance_checkpoint_state_required: repeatability_acceptance_checkpoint_recorded
acceptance_closeout_state_required_after_submit: repeatability_acceptance_operator_closeout_recorded
accepted_dispositions: no_regression_observed,delta_reviewed_no_regression
blocked_disposition: regression_detected_blocked
regression_detected_must_disable_or_fail_closed: true
rendered_acceptance_control_proof_state_submitted: headed_and_headless_passed
headless_rendered_proof_label_submitted: candidate_b_repeatability_acceptance_rendered_control_headless_chromium_pass
headed_rendered_proof_label_submitted: candidate_b_repeatability_acceptance_rendered_control_headed_chromium_pass
operator_runbook_closeout_steps_submitted: true
negative_invariant_attestations_submitted: true
server_owned_closeout_receipt_required: true
append_only_closeout_receipt_required: true
closeout_receipt_ref_rendered_redacted: true
raw_receipt_path_rendered: false
raw_local_path_rendered: false
raw_url_rendered: false
raw_stdout_rendered: false
raw_stderr_rendered: false
artifact_bytes_rendered: false
browser_storage_authority_admitted: false
frontend_durable_authority_enabled: false
actual_corpus_processing_execution_admitted_now: false
actual_subprocess_spawn_admitted_now: false
process_control_admitted: false
process_kill_cancel_retry_resume_admitted: false
browser_triggered_process_start_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_admitted: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
headless_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability rerun trial, acceptance checkpoint, and closeout" --project=chromium PASS
headed_rendered_proof: npx playwright test layer3-workbench.spec.js --grep "records Candidate B repeatability rerun trial, acceptance checkpoint, and closeout" --project=chromium --headed PASS
next_exact_posture: candidate_b_full_corpus_repeatability_acceptance_closeout_status_selection_v1
```

Operators can now record the server-owned repeatability acceptance closeout receipt through the rendered Candidate B workflow surface. The control is enabled only after the acceptance checkpoint exists with a non-regression disposition and matching corpus/material policy, then posts bounded receipt ids/hashes, admitted rendered-proof labels, closeout runbook constants, and the exact negative invariant attestation set to the closeout endpoint.

The rendered response shows the closeout state, redacted closeout receipt ref, hashes, comparison summary, proof labels, and negative invariants without raw filesystem paths, raw URLs, stdout/stderr, artifact bytes, process control, provider writes, connector dispatch, RAG/model runtime, default-scope expansion, full mockup activation, browser-storage authority, or frontend durable authority.

## Coherence Check

- Does the rendered control run Candidate B or Layer 3? Recommended answer: no. It records closeout over an existing server-owned acceptance checkpoint chain.
- Can a missing or regression-blocked acceptance checkpoint be closed out from the UI? Recommended answer: no. The control disables or fails closed.
- Does this finish production-grade monitoring? Recommended answer: no. The next useful posture is a read-only closeout status/review selection so operators can inspect persisted closeout receipts after recording.
