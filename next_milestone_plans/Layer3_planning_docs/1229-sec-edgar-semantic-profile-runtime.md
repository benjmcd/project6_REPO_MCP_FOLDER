# SEC EDGAR Semantic Profile Runtime

```yaml
milestone: sec_edgar_semantic_profile_runtime_v1
source_broader_quality_breadth_runtime: next_milestone_plans/Layer3_planning_docs/1228-sec-edgar-broader-quality-breadth-runtime.md
runtime_status: implemented_on_branch
service_classifier: backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.py
service_validation: backend/app/services/layer3_sec_edgar_real_company_corpus_validation.py
focused_test: backend/tests/test_layer3_api.py
semantic_profile_surface: semantic_profile
semantic_profile_version: sec_edgar_statement_semantic_profile_v1
semantic_profile_scope: bounded_taxonomy_class_concept_family_and_comparability_profile
financial_statement_semantics_finalized: false
taxonomy_network_resolution_performed: false
sec_companyfacts_api_called: false
cross_company_comparability_admitted: false
next_exact_posture: sec_edgar_operator_product_surface_selection_v1
```

## Purpose

Harden the SEC/EDGAR quality matrix after broader issuer/form validation by adding a bounded semantic profile to each HTML/iXBRL fact classification record.

The profile records redacted, deterministic evidence:

- taxonomy class
- concept family
- statement candidate role
- standard-taxonomy comparability scope
- company-extension retention status
- explicit non-use of taxonomy-network resolution and SEC companyfacts runtime

## Boundary

This is not final financial statement semantics and not broad cross-company comparability admission. It is a product-quality evidence layer over the existing statement-candidate classifier.

The slice does not add raw values, raw SEC URLs, accession exposure, artifact bytes, provider writes, connector dispatch, model/RAG runtime, or frontend durable authority.

## Current Finding

The quality matrix can now distinguish:

- `bounded_profile_available_not_finalized`
- `standard_taxonomy_profile_available_not_admitted`

while still preserving:

- `financial_statement_semantics_not_finalized`
- `cross_company_comparability_not_admitted`

That makes the next product pass clearer: use these profile metrics in an operator-facing product surface or select a deeper period/unit/dimension normalization lane.

## Coherence Checks

1. Does this make SEC statement semantics complete?
   Recommended answer: no. It adds bounded profile evidence and keeps final semantics false.

2. Does this admit taxonomy network resolution or SEC companyfacts runtime?
   Recommended answer: no. Both remain explicitly false.

3. Should the next pass add more issuer breadth?
   Recommended answer: not first. The next higher-value pass is an operator product surface that exposes the quality/profile evidence already collected.
