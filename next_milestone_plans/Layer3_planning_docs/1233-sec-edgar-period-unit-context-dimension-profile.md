# SEC EDGAR Period Unit Context Dimension Profile

```yaml
milestone: sec_edgar_period_unit_context_dimension_profile_hardening_v1
source_rendered_ui: next_milestone_plans/Layer3_planning_docs/1232-sec-edgar-operator-product-surface-rendered-ui.md
entry_main_commit: 6b4574c448c8b8fedcbb095a2441ba1007b153e0
runtime_status: implemented_branch_local
classifier: backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.py
validation_quality_matrix: backend/app/services/layer3_sec_edgar_real_company_corpus_validation.py
operator_product_surface: backend/app/services/layer3_sec_edgar_operator_product_surface.py
profile_version: sec_edgar_period_unit_context_dimension_profile_v1
profile_scope: redacted_context_unit_precision_scale_hash_profile
context_period_resolution_performed: false
dimension_member_resolution_performed: false
unit_normalization_performed: false
financial_statement_semantics_finalized: false
cross_company_comparability_admitted: false
next_exact_posture: sec_edgar_statement_role_quality_profile_v1
```

## Scope

This pass hardens the bounded SEC/EDGAR semantic profile by adding a redacted period/unit/context/dimension subprofile to each classified iXBRL fact. The profile records whether context, unit, precision/decimals, and scale/format evidence is present, then rolls those counts into the real-company quality matrix and operator product surface.

## Boundary

This is still not period normalization, unit normalization, dimension-member resolution, final financial-statement semantics, or cross-company comparability admission. It keeps all evidence hash-bound and redacted, and it does not call taxonomy networks, SEC companyfacts, providers, connectors, model/RAG runtime, or frontend durable authority.

## Product Effect

Operators can now distinguish:

- `bounded_hash_profile_available_not_resolved`
- `context_ref_hash_bound_period_not_resolved`
- `unit_ref_hash_bound`
- `dimension_members_not_resolved`

without seeing raw context refs, unit refs, fact values, SEC URLs, local paths, accessions, tickers, or company names.

## Coherence Checks

1. Does this resolve XBRL periods or dimensions?
   Recommended answer: no. It only proves the redacted context/unit/dimension-adjacent profile is present and hash-bound.

2. Does this make cross-company financial statements comparable?
   Recommended answer: no. Comparability remains explicitly not admitted.

3. What comes next?
   Recommended answer: statement-role quality profiling, then extension taxonomy, standard concept mapping, fact de-duplication/conflict diagnostics, and comparability-readiness audit.
