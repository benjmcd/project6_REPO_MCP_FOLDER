# 1264 - SEC XBRL Product Path Corpus Validation

## Target

`sec_edgar_arelle_default_on_product_path_corpus_validation_v1`

## Decision Boundary

This slice proves the default-on Arelle resolved-fact authority path across the existing SEC real-company product chain after the bridge/classification cutover.

The change is deliberately bounded:

- real-company corpus validation derives a persisted Arelle sidecar for each HTML/iXBRL filing when the cutover flag is enabled;
- the fact-material bridge consumes the persisted sidecar receipt, never a synchronous Arelle run;
- statement classification, statement product, package/review, handoff/export, delivery/status, operator inspection, operator product surface, and durable archive consume the selected sidecar-backed fact authority;
- the legacy regex fact-authority receipt remains recorded for rollback/comparison;
- operator value exposure remains gated and is not enabled by this slice.

## Runtime Evidence

Report:

`diagnostics/assessment/sec-xbrl-product-path-corpus-validation-report.json`

Focused proof added:

- `test_layer3_api_runs_sec_edgar_default_on_arelle_product_path_through_archive`
- validates 8 fake-client real-company corpus records over the redacted core matrix and forms `10-K`, `10-Q`, `8-K`, `20-F`, `40-F`, and `6-K`;
- verifies each supported record includes `arelle_resolved_fact_authority_sidecar`;
- verifies selected `fact_authority_receipt_hash` equals the Arelle sidecar hash while the regex authority hash remains available;
- verifies delivery provenance carries the sidecar selected fact-authority hash;
- verifies operator inspection, product surface, and durable archive remain ready;
- verifies effective values are not exposed on validation, delivery, operator, product-surface, or archive responses.

## Runtime Adjustment

Statement product authority reading now follows the material bridge fact-authority input mode. Regex-backed bridges still read the regex authority receipt. Arelle-backed bridges read the persisted sidecar receipt through the existing sidecar fact-authority view.

This is not a product redesign. It is the same selected-authority read boundary already used by statement classification, extended to the next downstream product step.

## Non-Goals Preserved

- no operator value reveal default-on behavior
- no Candidate-B routing for SEC semantics
- no final financial-statement semantics claim
- no cross-company comparability claim
- no Gate B decision-logic redesign
- no product/package/UI redesign
- no RAG/vector/model/provider/auth behavior
- no new Layer 3 source shape

## Next Slice

`sec_edgar_default_on_broader_corpus_reliability_gate_v1`

Scope:

- expand default-on proof beyond the current small fake-client product-path corpus and inherited 12-filing measurement corpus;
- keep Arelle as the extraction authority and CompanyFacts/raw-inline counts as independent oracles;
- prove product-chain readiness and redaction over additional heterogeneous real filings before broader default-on reliance;
- keep operator value reveal explicit and gated.
