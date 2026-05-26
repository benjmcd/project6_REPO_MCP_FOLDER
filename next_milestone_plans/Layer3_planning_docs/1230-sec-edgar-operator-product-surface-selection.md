# SEC EDGAR Operator Product Surface Selection

```yaml
milestone: sec_edgar_operator_product_surface_selection_v1
source_semantic_profile_runtime: next_milestone_plans/Layer3_planning_docs/1229-sec-edgar-semantic-profile-runtime.md
source_operator_inspection_runtime: next_milestone_plans/Layer3_planning_docs/1224-sec-edgar-operator-inspection-runtime.md
entry_main_commit: 0235496e1e73aed5f2e4ff84c329b94384d27579
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: sec_edgar_operator_product_surface_runtime_v1
selected_future_rendered_mode: rendered_sec_edgar_operator_product_surface_control
selected_surface_scope: redacted_operator_product_surface_over_sec_edgar_validation_delivery_operator_inspection_quality_and_semantic_profile_authority
selected_required_authority_chain: validation_receipt_hash,delivery_status_provenance_receipt_hash,operator_inspection_receipt_hash,quality_evidence_hash,semantic_profile_inventory_hash
selected_product_views: company_form_matrix,filing_identity,source_family,statement_candidates,fact_inventory,semantic_profile,extension_unclassified_facts,quality_gaps,diagnostics_loss_report,package_review_handoff_state,operator_inspection_status_links
selected_server_sources: real_company_corpus_validation,delivery_status_provenance,operator_inspection
selected_client_authority: none
selected_rendered_authority: server_receipt_projection_only
operator_product_surface_runtime_in_this_freeze: false
backend_route_behavior_change: false
frontend_runtime_behavior_change: false
financial_statement_semantics_finalized: false
cross_company_comparability_admitted: false
taxonomy_network_resolution_performed: false
sec_companyfacts_api_called: false
raw_url_path_accession_company_value_leakage_allowed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
frontend_durable_authority_enabled: false
candidate_b_pdf_only_routing_for_sec_filings_enabled: false
verification_progress_check: python ./tools/l3-progress-check.py PASS
verification_target_selection: python ./tools/l3-target-selection-validate.py --expect frozen PASS
next_exact_posture: sec_edgar_operator_product_surface_runtime_v1
```

## Purpose

Select the next SEC/EDGAR product-facing surface now that product-quality, broader-breadth, and semantic-profile evidence are durable on current main.

The future runtime should expose a rendered operator product surface over existing server-owned receipts. It should make the current SEC product path inspectable as a product, not just as individual receipt APIs.

Required operator views:

- company/form matrix
- filing identity and source family
- statement candidates
- fact inventory
- semantic profile
- extension and unclassified facts
- quality gaps
- diagnostics/loss report
- package/review/handoff state
- operator inspection status links

## Boundary

This is a planning/control selection only. It does not add a rendered runtime, backend route behavior, parser behavior, delivery behavior, provider write, connector dispatch, model/RAG runtime, or durable frontend authority.

The future rendered surface must be a server-receipt projection. Browser state may help operators enter receipt ids and hashes, but it must never become product authority.

## Non-Admissions

The selected surface must preserve the current SEC/EDGAR non-admissions:

- no final financial-statement semantics claim
- no cross-company comparability claim
- no taxonomy-network resolution runtime
- no SEC companyfacts runtime
- no raw URL, local path, accession, company-name, artifact-byte, or raw fact-value leakage
- no Candidate B/PDF-only routing for SEC filing semantics

## Coherence Checks

1. Should this pass implement the rendered operator surface?
   Recommended answer: no. This pass freezes the selected product surface contract first.

2. Should the rendered surface compute semantics in the browser?
   Recommended answer: no. It should project server-owned receipt evidence only.

3. Should the next runtime broaden issuer coverage before operator visibility?
   Recommended answer: no. The product evidence is now durable enough to expose first; broader validation can follow after the operator surface shows what is understandable and what remains unclear.
