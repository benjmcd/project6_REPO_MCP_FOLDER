# SEC EDGAR Broader Quality Breadth Runtime

```yaml
milestone: sec_edgar_broader_quality_breadth_runtime_v1
source_quality_matrix_runtime: next_milestone_plans/Layer3_planning_docs/1227-sec-edgar-product-quality-matrix-runtime.md
runtime_status: implemented_on_branch
service_connector: backend/app/services/layer3_sec_edgar_real_filing_acquisition_connector.py
service_validation: backend/app/services/layer3_sec_edgar_real_company_corpus_validation.py
focused_test: backend/tests/test_layer3_api.py
default_closeout_matrix_preserved: MSFT,STLD,SONY,CCJ
broader_quality_matrix: JPM,MET,PLD,FIZZ
broader_profile_tags: financial_institution,insurance,reit,small_cap,amended_filing
delivery_status_provenance_broadened: false
operator_inspection_broadened: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
frontend_durable_authority_enabled: false
financial_statement_semantics_finalized: false
cross_company_comparability_admitted: false
next_exact_posture: sec_edgar_financial_semantics_gap_selection_v1
```

## Purpose

Extend the SEC/EDGAR quality matrix beyond the original MSFT/STLD/SONY/CCJ closeout set without widening delivery/status/provenance, operator inspection, provider delivery, connector dispatch, model/RAG runtime, or frontend durable authority.

This pass adds a second bounded validation-only company matrix:

- JPM: financial institution
- MET: insurance
- PLD: REIT
- FIZZ: small-cap / consumer products

The validation runtime records redacted issuer/form profile tags and carries them into `product_quality_matrix` rows. This lets the quality matrix prove broader issuer/form coverage while still using hashes, counts, status labels, and known-gap labels instead of raw SEC URLs, accessions, company names, artifact bytes, or raw fact values.

## Boundary

The broader matrix is intentionally limited to validation/product-quality evidence. The landed delivery/status/provenance and operator inspection closeout path remains pinned to the prior MSFT/STLD/SONY/CCJ, eight-filing matrix. Broader delivery/operator admission is a separate future decision.

## Current Finding

The broader validation pass improves breadth evidence for product-quality scoring, but it still records the same product-grade gaps:

- `financial_statement_semantics_not_finalized`
- `cross_company_comparability_not_admitted`

Those gaps should drive the next semantic-hardening selection, not a generic delivery expansion.

## Coherence Checks

1. Did this broaden the production delivery surface?
   Recommended answer: no. It broadens validation quality evidence only.

2. Does this prove broad SEC product-grade support?
   Recommended answer: no. It proves another bounded breadth slice and preserves explicit semantic/comparability gaps.

3. Should the next pass be more company breadth or semantic hardening?
   Recommended answer: semantic hardening. The quality matrix now has enough breadth signal to select a concrete financial semantics gap.
