# Candidate B Broader Eligible Corpus Default Scope Runtime Rendered Status

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_runtime_rendered_status_v1
source_broader_eligible_corpus_default_scope_runtime: next_milestone_plans/Layer3_planning_docs/1071-cb-broader-eligible-corpus-default-scope-runtime.md
current_main_entry: e3007dd8824770585d442916067c9a40f3343927
rendered_status: broader_scope_default_scope_runtime_rendered_status_implemented
rendered_mode: rendered_candidate_b_broader_eligible_corpus_default_scope_runtime_status_control
runtime_mode: candidate_b_broader_eligible_corpus_default_scope_runtime_v1
runtime_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/runtime
selected_state_visible: candidate_b_broader_eligible_corpus_default_scope_runtime_selected
blocked_state_visible: candidate_b_broader_eligible_corpus_default_scope_runtime_blocked
ready_audit_json_required: true
selected_scope_classes_required: true
readiness_audit_id_hash_bound: true
redacted_selection_receipt_visible: true
operator_visible_scope_status_visible: true
current_default_scope_preserved: eligible_effective_pdfs_only
non_pdf_default_preserved: baseline
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_document_processing_engine_preserved: candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only
candidate_b_visual_lane_preserved: candidate_b_opendataloader_page_evidence_v1_explicit_only
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
rendered_contract_proof: e2e/layer3-workbench.spec.js::Layer 3 workbench renders Candidate B default-promotion status contract without route calls
rendered_runtime_status_proof: e2e/layer3-workbench.spec.js::Layer 3 workbench records Candidate B broader eligible-corpus runtime status through rendered control
verification_node_check: node --check ./backend/app/review_ui/static/layer3.js PASS
headless_rendered_status_proof: npx playwright test layer3-workbench.spec.js --grep "Candidate B broader eligible-corpus runtime status|Candidate B default-promotion status contract" --project=chromium PASS 2 passed
headed_rendered_status_proof: npx playwright test layer3-workbench.spec.js --grep "Candidate B broader eligible-corpus runtime status|Candidate B default-promotion status contract" --project=chromium --headed PASS 2 passed
proof_status: local_passed
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_runtime_current_main_sync_v1
```

This slice exposes the already-admitted broader eligible-corpus default-scope runtime to the operator status panel. The browser submits only the server-produced broader-scope readiness audit JSON plus exact selected scope classes; the server remains responsible for audit id/hash binding, fail-closed evaluation, redacted receipt authority, and selector-safe status projection.

The rendered control shows selected and blocked states, readiness binding, receipt id/hash/ref status, selected class count, baseline rollback, preserved current PDF default, baseline non-PDF fallback, and negative authority flags. It does not make broader classes default by itself and does not add source expansion, runtime DB/storage expansion, provider writes, connector dispatch, RAG/model runtime, full mockup activation, browser storage authority, or frontend durable authority.

## Coherence Check

- Does this turn broader corpus classes into the default selector? Recommended answer: no. It renders and records the server-owned runtime receipt only after a ready audit and exact class selection.
- Does the browser own durable authority? Recommended answer: no. The browser provides input to the admitted endpoint; durable authority is the server response and redacted receipt.
- What fails closed? Recommended answer: missing or invalid audit JSON, stale audit id/hash, unproposed or unready selected classes, missing rollback/operator confirmation, and any raw path/URL or forbidden authority in the server runtime.
- What comes next? Recommended answer: current-main sync after merge, then a separately frozen selector-use/default-scope adoption pass only if product authority admits using the broader-scope runtime receipt.
