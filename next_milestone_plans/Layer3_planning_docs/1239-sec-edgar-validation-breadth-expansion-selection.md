# SEC EDGAR Validation Breadth Expansion Selection

```yaml
milestone: sec_edgar_validation_breadth_expansion_selection_v1
source_comparability_readiness_audit: next_milestone_plans/Layer3_planning_docs/1238-sec-edgar-cross-company-comparability-readiness-audit.md
entry_main_commit: 33e9c4ed16bb5b59d0645de6b0ad3b9c648c0ab7
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: sec_edgar_validation_breadth_expansion_runtime_v1
selected_expansion_matrix: XOM,PFE,UAL,T
selected_expansion_profile_tags: energy_major,pharmaceutical_life_sciences,airline_transport,telecom_media,debt_intensive,commodity_exposure
selected_validation_scope: validation_product_quality_matrix_only
runtime_admission_in_this_freeze: false
delivery_status_provenance_broadened: false
operator_inspection_broadened: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
frontend_durable_authority_enabled: false
financial_statement_semantics_finalized: false
cross_company_comparability_ready: false
cross_company_comparability_admitted: false
comparability_normalization_performed: false
next_exact_posture: sec_edgar_validation_breadth_expansion_runtime_v1
```

## Purpose

Select the next SEC/EDGAR validation breadth expansion now that the semantic profile stack includes period/unit/context/dimension, statement-role, extension-retention, standard-concept, de-duplication/conflict, and comparability-readiness evidence.

The current broadened validation matrix already covers:

- financial institution
- insurance
- REIT
- small cap
- amended filing

The selected next matrix targets different issuer economics and filing-shape pressure:

- XOM: energy major / commodity exposure
- PFE: pharmaceutical and life sciences
- UAL: airline and transportation
- T: telecom/media and debt-intensive issuer

## Boundary

This is a planning/control selection only. It records the selected expansion target in code and documentation, but it does not admit the selected matrix into the live SEC connector CIK map, does not run broader validation, does not broaden delivery/status/provenance, does not broaden operator inspection, and does not change provider, connector-dispatch, model/RAG, or frontend authority.

The runtime pass must add the selected companies as an explicit bounded validation-only matrix, preserve redaction, and keep the current non-admissions:

- no final financial-statement semantics claim
- no cross-company comparability readiness/admission claim
- no comparability normalization
- no taxonomy-network or SEC Companyfacts runtime
- no raw URL, accession, company-name, local-path, artifact-byte, or raw fact-value leakage

## Coherence Checks

1. Is the selected matrix admitted at runtime in this pass?
   Recommended answer: no. `VALIDATION_BREADTH_EXPANSION_RUNTIME_ENABLED` remains false.

2. Does this pass broaden delivery or operator inspection?
   Recommended answer: no. It selects a validation/product-quality runtime slice only.

3. Why select more breadth after comparability-readiness showed blockers?
   Recommended answer: because the next product-grade step needs more issuer-shape evidence while preserving explicit non-admission of comparability and final semantics.
