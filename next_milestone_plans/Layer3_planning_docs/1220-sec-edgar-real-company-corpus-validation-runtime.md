# SEC EDGAR Real Company Corpus Validation Runtime

```yaml
milestone: sec_edgar_real_company_corpus_validation_runtime_v1
source_selection: next_milestone_plans/Layer3_planning_docs/1219-sec-edgar-real-company-corpus-validation-selection.md
entry_main_commit: 275ae95e3a11303f73e2da07cf01d16f9c3b2387
entry_pr: "#1919"
runtime_status: implemented
service: backend/app/services/layer3_sec_edgar_real_company_corpus_validation.py
endpoint: /api/v1/layer3/source/sec-edgar/real-company-corpus/validation
status_endpoint: /api/v1/layer3/source/sec-edgar/real-company-corpus/validation/status/{sec_edgar_real_company_corpus_validation_receipt_id}
schema_id: layer3.sec_edgar_real_company_corpus_validation.v1
status_schema_id: layer3.sec_edgar_real_company_corpus_validation_status.v1
validation_mode: sec_edgar_real_company_corpus_validation_v1
operator_decision: validate_sec_edgar_real_company_corpus_product_path
connector_selection_policy: real_company_recent_annual_and_interim_or_current_v1
company_matrix: MSFT,STLD,SONY,CCJ
discovered_form_families_under_test: 10-K,10-Q,8-K,20-F,40-F,6-K
path_validated: sec_connector_acquisition,source_family_classification,html_inline_xbrl_parser,fact_authority,fact_material_bridge,statement_classification,statement_candidate_product,package_review_preview,package_construction_commit,package_review_submit,handoff_export_prepare,status
product_utility_matrix_recorded: true
order_evidence_recorded: document_order_hash,fact_source_order_inventory,statement_candidate_order,package_artifact_order_hash
extension_policy_runtime_covered: company_specific_extension_concepts_are_retained_as_redacted_fact_authority_and_classification_evidence
unsupported_or_degraded_behavior: per_filing_blocked_or_degraded_records_preserve_diagnostics_without_generic_text_downgrade
raw_url_path_value_leakage_blocked: true
candidate_b_pdf_only_routing_for_sec_filings_enabled: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
verification_focused_api: python -m pytest ./backend/tests/test_layer3_api.py -k "real_company_corpus_product_path" -q PASS
next_exact_posture: sec_edgar_delivery_status_provenance_selection_v1
```

This runtime implements the selected real-company corpus validation path. It uses the existing SEC acquisition client and connector receipt authority, discovers annual plus interim/current filings for the selected company matrix from SEC submissions metadata, and drives each HTML/iXBRL-supported filing through the admitted parser, fact authority, material bridge, statement-candidate product, package review, package construction, package-review submit, and handoff/export prepare chain.

The runtime records a company-by-filing product utility matrix with supported/degraded/blocked disposition, output hashes, order evidence, and failure classification. It does not claim full SEC support, does not downgrade unsupported source families into generic text, does not route SEC filing semantics through Candidate B PDF-only handling, and does not introduce provider writes, connector dispatch, RAG/model runtime, full mockup activation, or frontend durable authority.
