# Candidate B Broader Eligible Corpus Default Scope Runtime

```yaml
milestone: candidate_b_broader_eligible_corpus_default_scope_runtime_v1
source_broader_eligible_corpus_default_scope_runtime_selection: next_milestone_plans/Layer3_planning_docs/1070-cb-broader-eligible-corpus-default-scope-runtime-selection.md
current_main_entry: 798c3e279a97af14444da7e6210cd6cd1cd4c723
runtime_status: broader_scope_default_scope_runtime_implemented
implemented_schema_id: layer3.candidate_b_broader_eligible_corpus_default_scope_runtime.v1
implemented_runtime_mode: candidate_b_broader_eligible_corpus_default_scope_runtime_v1
implemented_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/runtime
implemented_selected_state: candidate_b_broader_eligible_corpus_default_scope_runtime_selected
implemented_blocked_state: candidate_b_broader_eligible_corpus_default_scope_runtime_blocked
implemented_scope_binding_authority: candidate_b_broader_eligible_corpus_scope_readiness_audit_ready_state
implemented_scope_binding_state_required: candidate_b_broader_eligible_corpus_scope_ready_for_separate_selection
implemented_scope_classes_source: proposed_default_scope_classes_from_matching_ready_audit
implemented_audit_hash_binding_required: true
implemented_audit_id_binding_required: true
implemented_redacted_selection_receipt: true
implemented_contract_exposure: readiness_contract,bootstrap_contract,openapi
missing_audit_fail_closed_proven: true
stale_audit_hash_fail_closed_proven: true
unready_or_unproposed_scope_class_fail_closed_proven: true
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
current_default_scope_preserved: eligible_effective_pdfs_only
non_pdf_default_preserved_until_selection: baseline
candidate_b_document_processing_engine_preserved: candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only
candidate_b_visual_lane_preserved: candidate_b_opendataloader_page_evidence_v1_explicit_only
bundle_and_runtime_authority_remain_distinct: true
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
verification_py_compile: python -m py_compile ./backend/app/services/layer3_candidate_b_broader_scope_runtime.py ./backend/app/api/layer3.py ./backend/app/services/layer3_readiness_contract.py ./backend/app/services/layer3_bootstrap_contract.py PASS
verification_focused_pytest: python -m pytest ./backend/tests/test_layer3_candidate_b_broader_scope_runtime.py ./backend/tests/test_layer3_candidate_b_broader_scope_readiness.py ./backend/tests/test_layer3_readiness_contract.py ./backend/tests/test_layer3_bootstrap_contract.py -q PASS 11 passed
proof_status: local_passed
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_runtime_rendered_status_v1
```

This slice implements the runtime selected by `1070` without silently changing Candidate B processing defaults. The runtime accepts a full ready broader-scope audit result plus matching audit id/hash and exact selected scope classes. It selects only the classes proposed by the ready audit, writes a redacted selection receipt under the existing Candidate B runtime bridge receipt root, and projects operator-visible scope status without raw paths, URLs, provider secrets, connector authority, browser authority, or frontend durable authority.

The runtime fails closed when the ready audit is missing, stale, hash-mismatched, not in the required ready state, missing the selected class, not proposing the selected class, or reporting an unready selected class. It also preserves the current eligible/effective PDF default, baseline rollback/non-PDF default posture, Candidate A semantics, Candidate B document-processing engine scope, and explicit Candidate B visual lane scope.

## Coherence Check

- Does this make arbitrary non-PDF classes Candidate B default? Recommended answer: no. It only records a redacted selection receipt for exact classes proven by a ready audit.
- Does this mutate the document-processing selector directly? Recommended answer: no. Selector mutation remains false; the receipt becomes bounded authority for a later current-main-admitted selector use.
- What fails closed? Recommended answer: missing audit, stale audit hash, non-ready audit, unproposed scope class, unready scope class, missing rollback confirmation, raw path/URL/selector authority, and forbidden provider/connector/RAG/model/browser/frontend authority.
- What comes next? Recommended answer: add rendered/operator status controls for this broader-scope runtime receipt so operators can inspect selected, blocked, and redacted authority states before any selector-use pass.
