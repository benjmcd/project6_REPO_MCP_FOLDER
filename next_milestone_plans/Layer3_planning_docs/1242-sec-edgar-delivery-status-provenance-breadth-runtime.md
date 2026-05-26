# SEC EDGAR Delivery Status Provenance Breadth Runtime

```yaml
milestone: sec_edgar_delivery_status_provenance_breadth_runtime_v1
source_selection: next_milestone_plans/Layer3_planning_docs/1241-sec-edgar-delivery-status-provenance-breadth-selection.md
source_validation_breadth_runtime: next_milestone_plans/Layer3_planning_docs/1240-sec-edgar-validation-breadth-expansion-runtime.md
runtime_version: sec_edgar_delivery_status_provenance_breadth_runtime_v1
runtime_status: implemented
service: backend/app/services/layer3_sec_edgar_delivery_status_provenance.py
endpoint: /api/v1/layer3/source/sec-edgar/real-company-corpus/delivery-status/provenance
status_endpoint: /api/v1/layer3/source/sec-edgar/real-company-corpus/delivery-status/provenance/status/{sec_edgar_delivery_status_provenance_receipt_id}
status_mode: sec_edgar_delivery_status_provenance_v1
operator_decision: inspect_sec_edgar_real_company_delivery_status_provenance
expanded_validation_matrix_admitted: XOM,PFE,UAL,T
expanded_profile_tags: energy_major,pharmaceutical_life_sciences,airline_transport,telecom_media,debt_intensive,commodity_exposure
default_delivery_matrix_preserved: MSFT,STLD,SONY,CCJ
required_filing_count: 8
delivery_status_projection: validation_receipt_status,handoff_export_prepare_status,delivery_readiness_status,provenance_hash_matrix,blocked_or_degraded_delivery_gaps,next_operator_actions
provenance_hash_bindings: validation_receipt_hash,connector_receipt_hash,parser_receipt_hash,fact_authority_receipt_hash,fact_material_bridge_receipt_hash,statement_classification_receipt_hash,statement_candidate_product_receipt_hash,package_review_preview_receipt_hash,package_construction_receipt_hash,package_review_submit_receipt_hash,handoff_export_prepare_receipt_hash,delivery_status_provenance_hash
delivery_boundary_enforced: inspect_delivery_readiness_and_provenance_without_serving_artifact_bytes_or_creating_provider_objects
fail_closed_conditions_covered: missing_validation_receipt,validation_hash_mismatch,validation_not_ready,company_matrix_mismatch,filing_count_mismatch,missing_handoff_export_prepare_output,raw_url_path_value_or_artifact_bytes_detected,unknown_or_unadmitted_request_field,operator_confirmation_missing
raw_url_path_value_leakage_blocked: true
sec_network_fetch_performed: false
parser_rerun_performed: false
package_mutation_performed: false
delivery_file_response_served: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
frontend_durable_authority_enabled: false
financial_statement_semantics_finalized: false
cross_company_comparability_ready: false
cross_company_comparability_admitted: false
comparability_normalization_performed: false
operator_inspection_broadened: false
operator_product_surface_broadened: false
next_exact_posture: sec_edgar_operator_inspection_breadth_selection_v1
```

## Purpose

Admit delivery/status/provenance projection for the expanded XOM/PFE/UAL/T validation matrix. This runtime accepts the expanded validation receipt chain and projects redacted delivery readiness plus provenance hashes without refetching SEC data, rerunning parsers, mutating packages, serving files, or creating provider objects.

## Runtime Boundary

The runtime now admits two bounded receipt matrices:

- default closeout matrix: MSFT/STLD/SONY/CCJ
- expanded breadth matrix: XOM/PFE/UAL/T

Both matrices must still provide eight validation records and `handoff_export_prepare` authority hashes. Other company matrices remain blocked by the existing company-matrix mismatch reason.

## Non-Admissions

This runtime does not broaden:

- operator inspection
- operator product surface
- provider object writing
- connector dispatch
- RAG/vector/model runtime
- frontend durable authority
- final financial-statement semantics
- cross-company comparability admission
- comparability normalization

The status response remains a receipt-bound projection only. It must not expose raw SEC URLs, accessions, company names, local paths, artifact bytes, or raw fact values.

## Coherence Checks

1. Does admitting delivery breadth create provider delivery?
   Recommended answer: no. The runtime continues to report `delivery_file_response_served: false` and `provider_object_write_enabled: false`.

2. Does admitting XOM/PFE/UAL/T make operator inspection ready for that matrix?
   Recommended answer: not yet. Operator inspection still needs its own breadth selection/runtime pass over the new delivery/status/provenance receipts.

3. Does this prove cross-company comparability?
   Recommended answer: no. The delivery matrix carries the existing quality evidence and keeps comparability readiness as `bounded_readiness_audit_available_not_comparable`.
