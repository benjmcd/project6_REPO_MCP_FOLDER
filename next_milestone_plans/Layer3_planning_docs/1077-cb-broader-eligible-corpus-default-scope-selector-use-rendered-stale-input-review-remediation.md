# Candidate B Broader Eligible Corpus Default Scope Selector-Use Rendered Stale Input Review Remediation

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_selector_use_rendered_stale_input_review_remediation_v1
source_broader_eligible_corpus_default_scope_selector_use_rendered_status: next_milestone_plans/Layer3_planning_docs/1076-cb-broader-eligible-corpus-default-scope-selector-use-rendered-status.md
current_main_entry: 8147bed5c661a4ac6fd10821879f92c0edf34c7a
source_review_pr: "#1779"
source_review_thread_total_count: 1
source_review_unresolved_before_remediation: 1
source_review_path: backend/app/review_ui/static/layer3.js
source_review_line: 8334
review_disposition: remediated_in_followup_slice
remediation_status: implemented
remediated_failure_mode: selector_use_payload_reuses_stale_runtime_receipt_or_classes_after_runtime_re_record
runtime_defaults_source: latest_selected_candidate_b_broader_scope_runtime_receipt
operator_edit_tracking: candidateBBroaderScopeSelectorUseInputEdited
runtime_default_helper: candidateBBroaderScopeSelectorUseRuntimeDefaults
runtime_success_resets_selector_use_input: true
runtime_success_clears_stale_selector_use_status: true
operator_edited_fields_preserved_after_explicit_edit: true
selector_use_payload_prefers_latest_runtime_unless_operator_edited: true
second_runtime_receipt_proof: cb-broader-scope-runtime-rendered-proof-2
second_runtime_receipt_hash_proof: "7777777777777777777777777777777777777777777777777777777777777777"
rendered_selector_use_latest_runtime_payload_proof: true
selected_state_preserved: candidate_b_broader_eligible_corpus_default_scope_selector_use_selected
blocked_state_preserved: candidate_b_broader_eligible_corpus_default_scope_selector_use_blocked
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
selector_mutation_performed: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
verification_node_check: node --check ./backend/app/review_ui/static/layer3.js PASS
headless_rendered_status_proof: npx playwright test layer3-workbench.spec.js --grep "Candidate B broader eligible-corpus runtime status" --project=chromium PASS 1 passed
headed_rendered_status_proof: npx playwright test layer3-workbench.spec.js --grep "Candidate B broader eligible-corpus runtime status" --project=chromium --headed PASS 1 passed
proof_status: local_passed
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_selector_use_current_main_sync_v1
```

PR `#1779` exposed Candidate B broader eligible-corpus selector-use receipt recording in the rendered operator panel. The merged review thread found that the selector-use form could keep stale receipt id/hash/classes after the broader-scope runtime was re-recorded with a new selected runtime receipt. This remediation makes the latest selected runtime receipt the default selector-use authority unless the operator explicitly edits the fields.

On successful runtime re-record, the rendered panel clears stale selector-use status, resets selector-use input to the new runtime receipt id/hash/classes, and marks the selector-use input as not operator-edited. Explicit operator edits are still tracked and preserved. The browser proof records a second selected runtime receipt and verifies the next selector-use payload submits that latest receipt instead of the previous one.

## Coherence Check

- Does this remediation mutate the default selector? Recommended answer: no. It only corrects rendered selector-use input derivation.
- Does it make the browser durable selector authority? Recommended answer: no. The server-owned runtime receipt remains the authority, and selector-use still records through the admitted server endpoint.
- What remains blocked? Recommended answer: raw paths/URLs, receipt JSON, runtime roots, source expansion, provider writes, connector dispatch, RAG/model runtime, full mockup activation, browser storage authority, and frontend durable authority.
