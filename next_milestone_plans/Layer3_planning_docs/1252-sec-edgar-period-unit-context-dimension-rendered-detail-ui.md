# SEC EDGAR Period Unit Context Dimension Rendered Detail UI

```yaml
milestone: sec_edgar_period_unit_context_dimension_rendered_detail_ui_v1
source_profile: next_milestone_plans/Layer3_planning_docs/1233-sec-edgar-period-unit-context-dimension-profile.md
source_operator_surface: next_milestone_plans/Layer3_planning_docs/1232-sec-edgar-operator-product-surface-rendered-ui.md
source_archive_status_ui: next_milestone_plans/Layer3_planning_docs/1251-sec-edgar-durable-delivery-archive-status-rendered-ui.md
entry_main_commit: dfb150c54cc9c5c4c796e450c24bee8ab8624eae
runtime_status: implemented_branch_local
rendered_ui_surface: backend/app/review_ui/static/layer3.html
rendered_ui_controller: backend/app/review_ui/static/layer3.js
rendered_mode: rendered_sec_edgar_operator_product_surface_control
profile_version: sec_edgar_period_unit_context_dimension_profile_v1
profile_scope: redacted_context_unit_precision_scale_hash_profile
server_receipt_projection_only: true
frontend_durable_authority_enabled: false
context_period_resolution_performed: false
dimension_member_resolution_performed: false
unit_normalization_performed: false
financial_statement_semantics_finalized: false
cross_company_comparability_admitted: false
next_exact_posture: sec_edgar_statement_role_quality_profile_rendered_detail_ui_v1
```

## Purpose

Render the already server-owned SEC EDGAR period/unit/context/dimension profile as an operator-inspectable detail card instead of only a rollup count. The card reads the existing operator product-surface response and shows profile version, receipt-bound profile hash, assigned count, redacted context/unit/precision/scale presence counts, and explicit non-resolution flags.

## Boundary

This pass does not change classification, rerun parsers, fetch SEC content, resolve XBRL contexts, normalize units, resolve dimension members, call taxonomy networks, call SEC CompanyFacts, write provider objects, dispatch connectors, create frontend durable authority, finalize financial-statement semantics, or admit cross-company comparability.

## Coherence Checks

1. Does this deepen runtime semantics?
   Recommended answer: no. Runtime period/unit/context/dimension profiling already exists; this pass makes the current server-owned profile inspectable in the operator surface.

2. Does this expose raw context refs, unit refs, fact values, SEC URLs, accessions, tickers, company names, or local paths?
   Recommended answer: no. The rendered card only shows hash/status/count fields already present in the redacted product-surface response.

3. What comes next?
   Recommended answer: render the statement-role quality profile details with the same receipt-bound, non-finalized semantics posture.
