# Candidate B Broader Eligible Corpus Default Scope Selector-Use Runtime

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_selector_use_runtime_v1
source_broader_eligible_corpus_default_scope_selector_use_selection: next_milestone_plans/Layer3_planning_docs/1074-cb-broader-eligible-corpus-default-scope-selector-use-selection.md
current_main_entry: 82ee2274710edad3decbbffaac2028b983098634
runtime_status: selector_use_runtime_implemented
implemented_schema_id: layer3.candidate_b_broader_eligible_corpus_default_scope_selector_use.v1
implemented_runtime_mode: candidate_b_broader_eligible_corpus_default_scope_selector_use_runtime_v1
implemented_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use
implemented_selected_state: candidate_b_broader_eligible_corpus_default_scope_selector_use_selected
implemented_blocked_state: candidate_b_broader_eligible_corpus_default_scope_selector_use_blocked
implemented_selector_authority_source: redacted_candidate_b_broader_scope_runtime_receipt
implemented_source_runtime_required_state: candidate_b_broader_eligible_corpus_default_scope_runtime_selected
implemented_source_runtime_schema_id: layer3.candidate_b_broader_eligible_corpus_default_scope_runtime.v1
implemented_source_runtime_mode: candidate_b_broader_eligible_corpus_default_scope_runtime_v1
implemented_selected_scope_classes_source: selected_scope_classes_from_matching_runtime_receipt
implemented_receipt_binding_required: runtime_selection_receipt_id_and_hash
implemented_readiness_binding_required: readiness_audit_id_and_hash_from_source_runtime_receipt
implemented_receipt_root: configured_layer3_candidate_b_runtime_bridge_dir
implemented_receipt_family: broader-scope-selector-use
implemented_receipt_ref_scheme: candidate-b-broader-scope-selector-use
implemented_status_surface: api_response_redacted_selector_status
current_default_scope_before_use: eligible_effective_pdfs_only
default_scope_enabled_for_selected_classes: receipt_bound_only
non_selected_class_default_preserved: baseline
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_document_processing_engine_preserved: candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only
candidate_b_visual_lane_preserved: candidate_b_opendataloader_page_evidence_v1_explicit_only
bundle_and_runtime_authority_remain_distinct: true
missing_runtime_receipt_blocks_selector_use: true
blocked_runtime_receipt_blocks_selector_use: true
stale_runtime_receipt_hash_blocks_selector_use: true
stale_readiness_audit_hash_blocks_selector_use: true
unknown_scope_class_blocks_selector_use: true
unselected_scope_class_blocks_selector_use: true
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
provider_or_connector_secret_exposed: false
verification_backend_py_compile: python -m py_compile ./backend/app/services/layer3_candidate_b_broader_scope_selector_use.py ./backend/app/api/layer3.py ./backend/app/services/layer3_readiness_contract.py ./backend/app/services/layer3_bootstrap_contract.py PASS
verification_focused_pytest: python -m pytest ./backend/tests/test_layer3_candidate_b_broader_scope_selector_use.py ./backend/tests/test_layer3_candidate_b_broader_scope_runtime.py ./backend/tests/test_layer3_candidate_b_broader_scope_readiness.py ./backend/tests/test_layer3_readiness_contract.py ./backend/tests/test_layer3_bootstrap_contract.py -q PASS 16 passed
proof_status: local_passed
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_selector_use_rendered_status_v1
```

The selector-use runtime records a redacted server-owned selector-use receipt only after reloading a selected broader-scope runtime receipt from the configured Candidate B runtime bridge root. The browser supplies only receipt id/hash, exact selected classes, operator confirmation, and rollback confirmation. The server rejects missing, blocked, stale, unknown, or unselected authority without writing a selector-use receipt.

This runtime makes the selected receipt usable as bounded selector authority for exact selected broader classes, but it does not mutate omitted-engine defaults in place and does not add source expansion, runtime DB/storage expansion, PDF/image text material ingestion, provider writes, connector dispatch, RAG/model runtime, full mockup activation, browser storage authority, frontend durable authority, raw local path exposure, or raw URL exposure.

## Coherence Check

- Does this runtime trust browser-provided receipt JSON? Recommended answer: no. It reads the source runtime receipt from the configured server-owned receipt root using receipt id/hash.
- What fails closed? Recommended answer: missing receipt, blocked receipt, stale receipt hash, stale readiness hash, unknown class, unselected class, missing operator confirmation, and missing rollback confirmation.
- Does this mutate the global default selector? Recommended answer: no. It records a redacted selector-use authority receipt for exact selected classes; omitted-engine/default mutation remains separate.
- What comes next? Recommended answer: add a rendered status/control surface for selector-use receipts, then prove selected classes through downstream operator-visible status before any broader default-promotion closeout.
