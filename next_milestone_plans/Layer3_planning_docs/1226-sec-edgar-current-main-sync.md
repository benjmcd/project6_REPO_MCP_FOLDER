# SEC EDGAR Current Main Sync

## Purpose

Record the current-main proof after PR #1920 landed the governed SEC/EDGAR real-company validation, delivery/status/provenance, operator inspection, and completion-audit path.

```yaml
milestone: sec_edgar_current_main_sync_v1
source_completion_audit: next_milestone_plans/Layer3_planning_docs/1225-sec-edgar-completion-audit.md
source_pr: "#1920"
source_pr_status: merged
source_pr_head_commit: 8de74feb4521241b5db65dd19e120c3e00d4c95d
source_pr_merge_commit: 2f27ecdc928d8f4532c1f7c1eaad229ca0262aa9
current_main_observed_commit: 2f27ecdc928d8f4532c1f7c1eaad229ca0262aa9
current_main_sync_status: verified
completion_status: governed_sec_edgar_objective_satisfied_on_current_main
real_company_validation_current_main: true
delivery_status_provenance_current_main: true
operator_inspection_current_main: true
completion_audit_current_main: true
server_owned_connector_authority_current_main: true
real_company_matrix: MSFT,STLD,SONY,CCJ
filing_count_under_test: 8
form_families_under_test: 10-K,10-Q,8-K,20-F,40-F,6-K
validated_processing_path_current_main: sec_connector_acquisition,source_family_classification,html_inline_xbrl_parser,fact_authority,fact_material_bridge,statement_classification,statement_candidate_product,package_review_preview,package_construction_commit,package_review_submit,handoff_export_prepare,delivery_status_provenance,operator_inspection
identity_order_fact_context_taxonomy_extension_provenance_preserved_current_main: true
explicit_degraded_or_blocked_source_family_handling_current_main: true
raw_url_path_value_leakage_blocked_current_main: true
candidate_b_pdf_only_routing_for_sec_filings_enabled: false
unauthorized_source_or_parser_expansion_enabled: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
latest_pr_ci: gh pr checks 1920 PASS backend-layer3-api,test
verification_progress_check_on_current_main: python ./tools/l3-progress-check.py PASS
verification_target_selection_on_current_main: python ./tools/l3-target-selection-validate.py --expect frozen PASS
next_exact_posture: sec_edgar_goal_complete_v1
```

PR #1920 landed the SEC/EDGAR real-company path on current main at `2f27ecdc928d8f4532c1f7c1eaad229ca0262aa9`. The landed path includes server-owned connector authority, real-company filing diversity, SEC source authority normalization, provenance-carrying HTML/iXBRL processing, statement-candidate product, package review, package construction, review submit, handoff/export, delivery/status/provenance, and operator inspection.

The current-main path keeps raw URL/path/value leakage blocked and does not admit Candidate B PDF-only routing for SEC filings, unauthorized source/parser expansion, provider writes, connector dispatch, RAG/model runtime, full mockup activation, or frontend-only durable authority.
