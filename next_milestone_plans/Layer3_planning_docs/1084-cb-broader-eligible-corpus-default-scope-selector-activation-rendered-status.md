# Candidate B Broader Eligible Corpus Default Scope Selector Activation Rendered Status

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_selector_activation_runtime_rendered_status_v1
source_selector_activation_runtime: next_milestone_plans/Layer3_planning_docs/1083-cb-broader-eligible-corpus-default-scope-selector-activation-runtime.md
current_main_entry: bf295b1bae80fb041e4f1254facca4b5858bdc7e
runtime_status: already_implemented
rendered_status: implemented
rendered_mode: rendered_candidate_b_broader_eligible_corpus_default_scope_selector_activation_status_control
runtime_mode: candidate_b_broader_eligible_corpus_default_scope_selector_activation_runtime_v1
runtime_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-activation
selected_state_visible: candidate_b_broader_eligible_corpus_default_scope_selector_activation_selected
blocked_state_visible: candidate_b_broader_eligible_corpus_default_scope_selector_activation_blocked
response_authority: State.candidateBBroaderScopeSelectorActivation
source_status_authority: State.candidateBBroaderScopeSelectorUseStatus
selector_use_status_hash_required: true
selector_use_receipt_id_hash_required: true
runtime_selection_receipt_id_hash_required: true
selected_scope_classes_required: true
readiness_binding_displayed: true
activation_authority_source_displayed: server_revalidated_selector_use_status
operator_visible_activation_status_displayed: true
redacted_activation_receipt_displayed: true
stale_status_hash_fail_closed_rendered: true
stale_runtime_or_selector_use_state_clears_activation: true
browser_frontend_authority: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
selector_mutation_performed: false
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
verification_headless_rendered_status_proof: npx playwright test e2e/layer3-workbench.spec.js --grep "Candidate B broader eligible-corpus runtime status|Candidate B default-promotion status contract" --project=chromium PASS 2 passed
verification_headed_rendered_status_proof: npx playwright test e2e/layer3-workbench.spec.js --grep "Candidate B broader eligible-corpus runtime status|Candidate B default-promotion status contract" --project=chromium --headed PASS 2 passed
verification_progress_check: python ./tools/l3-progress-check.py PASS
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_selector_activation_current_main_sync_v1
```

This slice adds the rendered operator control for the already-admitted selector activation runtime. The browser can only submit the selector-use status hash, selector-use receipt id/hash, runtime receipt id/hash, and exact selected classes surfaced from the server-inspected selector-use status. The server remains the durable authority: the rendered panel records no selector mutation, no source or runtime expansion, and no provider, connector, RAG/model, full-mockup, browser-storage, or frontend-durable authority.
