# SEC EDGAR Product Quality Matrix Runtime

```yaml
milestone: sec_edgar_product_quality_matrix_runtime_v1
source_current_main_sync: next_milestone_plans/Layer3_planning_docs/1226-sec-edgar-current-main-sync.md
entry_main_commit: 0005c18d4099ca9f669c9234f795e9acde801230
runtime_status: implemented_on_branch
service_primary: backend/app/services/layer3_sec_edgar_real_company_corpus_validation.py
service_delivery_projection: backend/app/services/layer3_sec_edgar_delivery_status_provenance.py
service_operator_projection: backend/app/services/layer3_sec_edgar_operator_inspection.py
focused_test: backend/tests/test_layer3_api.py
quality_matrix_surface: product_quality_matrix
quality_evidence_scope: redacted_hash_count_and_status_projection
raw_url_path_value_leakage_blocked: true
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
financial_statement_semantics_finalized: false
cross_company_comparability_admitted: false
next_exact_posture: sec_edgar_product_quality_matrix_verification_v1
```

## Purpose

Move the landed SEC/EDGAR real-company path from coarse readiness proof toward product-grade quality assessment. The prior `product_utility_matrix` proved that each selected filing reached the admitted product path. This pass adds a first-class `product_quality_matrix` and carries the same redacted quality signal through delivery/status/provenance and operator inspection.

## Runtime Shape

Each supported filing now records redacted product-quality evidence for:

- filing identity correctness
- section/order preservation
- fact/context/unit preservation
- extension fact handling
- statement candidate usefulness
- diagnostics quality
- package/review/handoff coherence
- financial statement semantic maturity
- cross-company comparability admission

The quality surface uses receipt hashes, inventory hashes, counts, statuses, and known-gap labels. It does not expose raw filing URLs, accessions, company names, local paths, artifact bytes, or raw fact values.

## Current Quality Finding

The path is ready for governed quality inspection, but it still does not claim product-grade semantics. The matrix explicitly records:

- `financial_statement_semantics_not_finalized`
- `cross_company_comparability_not_admitted`
- `unclassified_fact_candidates_present` where the current classifier cannot confidently map facts

That is intentional. The current branch improves the product-quality evidence surface without overstating that arbitrary SEC filings, taxonomy networks, statement semantics, or cross-company comparability are solved.

## Coherence Checks

1. Should this pass broaden SEC parser support?
   Recommended answer: no. It records quality evidence over the admitted path and exposes concrete semantic gaps without admitting new parser families.

2. Does this make the SEC product platform complete?
   Recommended answer: no. It makes the next quality layer inspectable; broader issuer/form coverage, semantic hardening, operator UI, durable delivery, and production hardening remain future work.

3. Should quality evidence expose raw values so operators can inspect accuracy?
   Recommended answer: not in this slice. The admitted surface remains redacted and hash/count based. Any raw-value or artifact inspection requires a separately admitted authority boundary.

4. Does carrying quality evidence into operator inspection create frontend durable authority?
   Recommended answer: no. Operator inspection remains server-side, read-only, receipt-bound, and redacted.
