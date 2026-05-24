# Candidate B Broader Eligible Corpus Scope Readiness Audit

```yaml
milestone: candidate_b_broader_eligible_corpus_scope_readiness_audit_v1
source_broader_eligible_corpus_default_scope_selection: next_milestone_plans/Layer3_planning_docs/1068-cb-broader-eligible-corpus-default-scope-selection.md
current_main_entry: 4d1ab21446428d4f38ddb439e3e6f63c06b05730
runtime_status: broader_scope_readiness_audit_implemented
implemented_schema_id: layer3.candidate_b_broader_eligible_corpus_scope_readiness_audit.v1
implemented_audit_mode: candidate_b_broader_eligible_corpus_scope_readiness_audit_v1
implemented_endpoint: /api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/scope-readiness-audit
implemented_ready_state: candidate_b_broader_eligible_corpus_scope_ready_for_separate_selection
implemented_blocked_state: candidate_b_broader_eligible_corpus_scope_readiness_blocked
implemented_scope_classes: office_documents,images_or_ocr,zip_members,structured_json_or_csv_or_xlsx,sec_edgar,web_or_database_sources,mixed_corpus_batches
implemented_required_scope_evidence: current_parser_or_engine_authority,baseline_rollback_behavior,candidate_a_interaction,candidate_b_runtime_compatibility,layer3_material_authority_bridge_compatibility,artifact_family_preservation,redaction_and_status_projection,corpus_scale_proof,fail_closed_stale_or_missing_authority,regression_disposition
implemented_required_exclusions: selector_mutation_without_separate_freeze,source_expansion_without_separate_freeze,runtime_db_or_storage_expansion,pdf_or_image_text_material_ingestion,provider_object_writes,connector_dispatch,rag_vector_model_runtime,auth_security_expansion,full_mockup_activation,frontend_durable_authority,browser_storage_authority
implemented_contract_exposure: readiness_contract,bootstrap_contract,openapi
ready_state_meaning: ready_for_later_separately_frozen_default_scope_selection_only
default_scope_expansion_admitted: false
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
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_current_default_scope_preserved: eligible_effective_pdfs_only
verification_py_compile: python -m py_compile ./backend/app/services/layer3_candidate_b_broader_scope_readiness.py ./backend/app/api/layer3.py ./backend/app/services/layer3_readiness_contract.py ./backend/app/services/layer3_bootstrap_contract.py PASS
verification_focused_pytest: python -m pytest ./backend/tests/test_layer3_candidate_b_broader_scope_readiness.py ./backend/tests/test_layer3_readiness_contract.py ./backend/tests/test_layer3_bootstrap_contract.py -q PASS 6 passed
proof_status: local_passed
next_exact_posture: candidate_b_broader_eligible_corpus_default_scope_runtime_selection_v1
```

This slice implements the broader eligible-corpus scope readiness audit selected by `1068`. The audit is server-side and read-only. It can return a ready state only when the operator supplies the exact current-main scope-class list, the required exclusion list, at least one proposed class, per-class evidence for every class, rollback confirmation, and operator confirmation. The ready state only means a later default-scope runtime selection can be frozen for exact ready classes; it does not admit or perform selector mutation.

The audit fails closed for missing scope classes, missing required evidence, missing exclusions, missing rollback confirmation, nested path/URL/selector authority, runtime DB/storage expansion, source expansion, PDF/image material-text ingestion, provider writes, connector dispatch, RAG/vector/model runtime, auth/security expansion, browser-storage authority, frontend-only durable authority, and full mockup activation.

## Coherence Check

- Does this broaden Candidate B beyond eligible/effective PDFs? Recommended answer: no. It evaluates evidence for later separate selection while preserving the current PDF-only default.
- Does this accept frontend or caller-local authority? Recommended answer: no. Nested path, URL, selector, storage, connector, and browser-authority fields are rejected before audit evaluation.
- Does this make non-PDF classes ready automatically? Recommended answer: no. Each proposed class needs explicit per-class evidence and fail-closed proof before the audit can return ready.
- What comes next? Recommended answer: freeze a separate default-scope runtime selection only for exact classes that this audit proves ready; otherwise keep Candidate B PDF-only and report missing evidence.
