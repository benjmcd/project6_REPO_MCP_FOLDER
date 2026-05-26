# SEC EDGAR Operator Product Surface Runtime

```yaml
milestone: sec_edgar_operator_product_surface_runtime_v1
source_selection: next_milestone_plans/Layer3_planning_docs/1230-sec-edgar-operator-product-surface-selection.md
entry_main_commit: 48eba17b3adb97c484b42df5bcaf50f26f830306
runtime_status: implemented_branch_local
surface_mode: sec_edgar_operator_product_surface_runtime_v1
rendered_mode: rendered_sec_edgar_operator_product_surface_control
route: /api/v1/layer3/source/sec-edgar/real-company-corpus/operator-product-surface
status_route: /api/v1/layer3/source/sec-edgar/real-company-corpus/operator-product-surface/status/{sec_edgar_operator_product_surface_receipt_id}
request_schema_id: layer3.sec_edgar_operator_product_surface_request.v1
response_schema_id: layer3.sec_edgar_operator_product_surface.v1
status_schema_id: layer3.sec_edgar_operator_product_surface_status.v1
service: backend/app/services/layer3_sec_edgar_operator_product_surface.py
api: backend/app/api/layer3.py
test: backend/tests/test_layer3_api.py::test_layer3_api_reports_sec_edgar_operator_product_surface_for_real_company_corpus
authority_chain: validation_receipt_hash,delivery_status_provenance_receipt_hash,operator_inspection_receipt_hash,quality_evidence_hash,semantic_profile_inventory_hash
product_views: company_form_matrix,filing_identity,source_family,statement_candidates,fact_inventory,semantic_profile,extension_unclassified_facts,quality_gaps,diagnostics_loss_report,package_review_handoff_state,operator_inspection_status_links
server_sources: real_company_corpus_validation,delivery_status_provenance,operator_inspection
server_receipt_projection_only: true
frontend_durable_authority_enabled: false
sec_network_fetch_performed: false
parser_rerun_performed: false
package_mutation_performed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
taxonomy_network_resolution_performed: false
sec_companyfacts_api_called: false
financial_statement_semantics_finalized: false
cross_company_comparability_admitted: false
candidate_b_pdf_only_routing_for_sec_filings_enabled: false
next_exact_posture: sec_edgar_operator_product_surface_rendered_ui_v1
```

## Scope

This runtime turns the already-landed SEC/EDGAR validation, delivery/status/provenance, and operator-inspection receipts into one redacted operator product surface API. It is a server-owned receipt projection, not a new parser, acquisition path, package mutation path, provider delivery path, browser authority, rendered workbench implementation, or semantic-normalization runtime.

The surface projects:

- company/form matrix
- filing identity hashes and source family
- statement-candidate inventory hashes and role counts
- fact-inventory hashes and counts
- semantic-profile hashes and bounded counts
- extension and unclassified fact counts
- quality gaps and non-admissions
- diagnostics/loss report hashes
- package/review/handoff receipt state
- operator-inspection status hashes

## Non-Admissions

This pass keeps the SEC/EDGAR product surface bounded:

- no raw URL, local path, accession, ticker, company-name, artifact-byte, or raw fact-value leakage
- no final financial-statement semantics claim
- no cross-company comparability claim
- no taxonomy-network resolution runtime
- no SEC companyfacts runtime
- no Candidate B/PDF-only routing for SEC filing semantics
- no frontend durable authority

## Coherence Checks

1. Does the product surface broaden SEC acquisition or issuer coverage?
   Answer: no. It reads existing validation, delivery/status/provenance, and operator-inspection receipts only.

2. Does the product surface compute final financial-statement semantics?
   Answer: no. It exposes existing bounded semantic-profile evidence and preserves the non-admission.

3. Does the product surface make the browser authoritative?
   Answer: no. Browser/rendered state may display the server response, but the runtime authority is the server receipt projection.
