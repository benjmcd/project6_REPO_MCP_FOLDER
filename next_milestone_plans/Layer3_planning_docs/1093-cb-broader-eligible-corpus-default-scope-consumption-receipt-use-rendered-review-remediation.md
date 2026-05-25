# Candidate B Broader Eligible Corpus Default Scope Consumption Receipt Use Rendered Review Remediation

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_rendered_review_remediation_v1
source_consumption_receipt_use_rendered_status: next_milestone_plans/Layer3_planning_docs/1092-cb-broader-eligible-corpus-default-scope-consumption-receipt-use-rendered-status.md
current_main_entry: 1c78fde1b42169bf64201842f148c26b4ee73fbf
source_review_pr: "#1795"
source_review_threads_total_count: 3
source_review_threads_unresolved_before_remediation: 3
entry_decision: review_remediation
runtime_status: already_implemented
rendered_status: remediated
remediated_rendered_mode: rendered_candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_status_control
remediated_runtime_mode: candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_runtime_v1
remediated_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/consumption-receipt/use
source_consumption_authority_preferred_after_new_consumption_response: true
stale_dom_or_stored_use_values_rejected_after_new_consumption_response: true
server_selected_scope_classes_preferred_after_new_consumption_response: true
operator_edit_still_allowed_after_rehydration: true
operator_edit_clears_source_authority_preference: true
empty_parsed_selected_scope_classes_submit_disabled: true
selected_scope_classes_parser_shared_by_activation_consumption_and_consumption_use: true
positive_consumption_receipt_use_still_proven: true
stale_consumption_receipt_hash_fail_closed_still_proven: true
rehydrated_consumption_receipt_use_payload_proven: true
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
selector_mutation_performed: false
default_scope_mutation_performed: false
source_expansion_admitted: false
runtime_db_or_storage_expansion_admitted: false
pdf_or_image_text_material_ingestion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
auth_security_expansion_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
verification_js_syntax: node --check ./backend/app/review_ui/static/layer3.js PASS
verification_headless_rendered_status_proof: npx playwright test ./e2e/layer3-workbench.spec.js --grep "Layer 3 workbench records Candidate B broader eligible-corpus runtime status through rendered control" --project=chromium PASS 1 passed
verification_headed_rendered_status_proof: npx playwright test ./e2e/layer3-workbench.spec.js --grep "Layer 3 workbench records Candidate B broader eligible-corpus runtime status through rendered control" --project=chromium --headed PASS 1 passed
verification_progress_check: python ./tools/l3-progress-check.py PASS
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_current_main_sync_v1
```

This remediation closes PR `#1795` review debt without changing backend runtime authority. After a newly selected activation-consumption receipt is returned by the server, the rendered use form prefers the new server-owned consumption receipt bindings and selected classes over stale DOM or stored defaults. The preference is short-lived and clears on the next operator edit, so deliberate edits can still be submitted through the existing fail-closed server endpoint.

The submit gate now checks parsed selected classes, not just the raw text field. Inputs that normalize to an empty class list remain disabled in the rendered surface instead of reaching the server as avoidable invalid use requests.
