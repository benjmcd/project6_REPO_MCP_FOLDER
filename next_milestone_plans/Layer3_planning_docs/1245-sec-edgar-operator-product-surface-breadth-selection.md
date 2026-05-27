# SEC EDGAR Operator Product Surface Breadth Selection

```yaml
milestone: sec_edgar_operator_product_surface_breadth_selection_v1
source_operator_inspection_breadth_runtime: next_milestone_plans/Layer3_planning_docs/1244-sec-edgar-operator-inspection-breadth-runtime.md
entry_main_commit: 42c6401b03f7b72c09a329e29231d1fb592fb562
entry_decision: freeze_only_with_fail_closed_guard
runtime_status: not_implemented
selected_next_runtime_target: sec_edgar_operator_product_surface_breadth_runtime_v1
selected_runtime_service: backend/app/services/layer3_sec_edgar_operator_product_surface.py
selected_endpoint: /api/v1/layer3/source/sec-edgar/real-company-corpus/operator-product-surface
selected_status_endpoint: /api/v1/layer3/source/sec-edgar/real-company-corpus/operator-product-surface/status/{sec_edgar_operator_product_surface_receipt_id}
selected_surface_mode: sec_edgar_operator_product_surface_runtime_v1
selected_rendered_mode: rendered_sec_edgar_operator_product_surface_control
selected_operator_decision: render_sec_edgar_operator_product_surface
selected_input_authority: sec_edgar_operator_inspection_receipt_id,sec_edgar_operator_inspection_receipt_hash
selected_required_source_status: sec_edgar_operator_inspection_ready
selected_expanded_validation_matrix: XOM,PFE,UAL,T
selected_expanded_profile_tags: energy_major,pharmaceutical_life_sciences,airline_transport,telecom_media,debt_intensive,commodity_exposure
current_default_product_surface_matrix_preserved: MSFT,STLD,SONY,CCJ
selected_product_views: company_form_matrix,filing_identity,source_family,statement_candidates,fact_inventory,fact_deduplication_conflict_diagnostics,cross_company_comparability_readiness_audit,semantic_profile,statement_role_quality_profile,period_unit_context_dimension_profile,extension_taxonomy_retention_profile,standard_concept_mapping_profile,extension_unclassified_facts,quality_gaps,diagnostics_loss_report,package_review_handoff_state,operator_inspection_status_links
selected_read_only_boundary: render_redacted_operator_inspection_receipt_projection_without_mutating_validation_delivery_package_provider_connector_or_frontend_authority
selected_fail_closed_conditions: missing_operator_inspection_receipt,operator_inspection_hash_mismatch,operator_inspection_not_ready,company_matrix_mismatch,raw_url_path_value_or_artifact_bytes_detected,unknown_or_unadmitted_request_field,operator_confirmation_missing
selection_guard_added: sec_edgar_operator_product_surface_company_matrix_mismatch
operator_product_surface_breadth_runtime_in_this_freeze: false
expanded_product_surface_runtime_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
frontend_durable_authority_enabled: false
financial_statement_semantics_finalized: false
cross_company_comparability_ready: false
cross_company_comparability_admitted: false
comparability_normalization_performed: false
next_exact_posture: sec_edgar_operator_product_surface_breadth_runtime_v1
```

## Purpose

Select the product-surface breadth pass now that operator inspection admits the expanded XOM/PFE/UAL/T matrix. This pass also adds the explicit product-surface admission guard so expanded operator-inspection receipts cannot silently broaden the rendered product surface before the runtime pass.

## Boundary

Selection-only for the expanded product surface. The default MSFT/STLD/SONY/CCJ product surface remains admitted. The expanded XOM/PFE/UAL/T surface is blocked until `sec_edgar_operator_product_surface_breadth_runtime_v1` explicitly enables it.

## Non-Admissions

This selection does not broaden:

- expanded product-surface runtime
- provider object writing
- connector dispatch
- RAG/vector/model runtime
- frontend durable authority
- final financial-statement semantics
- cross-company comparability admission
- comparability normalization

## Coherence Checks

1. Can expanded operator-inspection receipts render through product surface in this pass?
   Recommended answer: no. They now fail closed with `sec_edgar_operator_product_surface_company_matrix_mismatch`.

2. Why add a guard in a selection pass?
   Recommended answer: operator-inspection breadth is already admitted, so product surface must own its own admission boundary instead of inheriting expanded behavior accidentally.

3. Does this prove final semantics or comparability?
   Recommended answer: no. It only selects the next product-surface breadth runtime and preserves existing non-admissions.
