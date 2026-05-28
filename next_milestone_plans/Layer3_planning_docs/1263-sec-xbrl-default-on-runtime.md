# 1263 - SEC XBRL Default-On Runtime

## Target

`sec_edgar_arelle_fact_authority_default_on_runtime_v1`

## Decision Boundary

This slice makes the already-admitted Arelle resolved-fact authority path the default SEC HTML/iXBRL fact-material bridge input. The broader real-corpus gate in `1266-sec-xbrl-real-product-runner.md` first rolled that default back to `false` after a live 32-filing gate failure, then restored it to `true` only after the same broader gate passed with corrected gate mechanics and redacted CompanyFacts evidence. The regex path remains available as an explicit rollback flag.

The change is deliberately narrow:

- `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED` now defaults to `true` after the broader gate pass.
- With the flag explicitly enabled, the bridge requires an explicit persisted Arelle sidecar receipt id and hash.
- The bridge still never invokes Arelle synchronously.
- Missing, stale, blocked, or lineage-mismatched sidecars fail closed.
- The regex authority path remains available as an explicit rollback by setting the flag to `false`.
- Statement classification now resolves its fact authority from the bridge input mode so a sidecar-backed bridge can continue into downstream product/package flow.

## Runtime Evidence

Report:

`diagnostics/assessment/sec-xbrl-default-on-runtime-report.json`

Decision: `default_on_runtime_enabled`.

Broader gate evidence:

- broader live gate target: `sec_edgar_real_corpus_product_path_runner_v1`
- live gate corpus: 32 filings, 16 issuer hashes, required forms present, including `10-K/A`
- live gate decision: `real_corpus_default_on_validated`
- Arelle resolved facts: `52,558`
- independent raw-inline facts: `52,558`
- completeness guard failures: `0`
- CompanyFacts effective-value correctness: `9,040/9,131`, match rate `0.99`
- no unexpected blocked/degraded records; 2 no-inline-marker filings are explicitly diagnosed
- resulting default decision: `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED=true`

Inherited real-corpus gate evidence remains:

- 12 real filings in the core default-on gate corpus.
- 6 issuer hashes.
- Forms: `10-K`, `10-Q`, `20-F`, `40-F`, `6-K`, `8-K`.
- Arelle resolved facts: `18,156`.
- Bridge facts: `18,156`.
- Expanded value materialization facts: `23,102`.
- CompanyFacts effective-value correctness: `3,761/3,790`, match rate `0.9923`.

Focused runtime proof retained behind the explicit flag:

- local deployment defaults admit the Arelle cutover only after the broader gate pass.
- legacy regex bridge behavior remains available with the flag explicitly disabled.
- default-on bridge still blocks without a persisted sidecar and performs no regex fallback.
- sidecar lineage mismatch still blocks.
- sidecar-backed bridge output can feed statement classification as the selected fact authority.

## Rollback

Rollback remains:

`LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED=false`

Rollback restores the regex fact-authority bridge path without deleting the Arelle sidecar path.

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

`sec_edgar_operator_surface_gated_value_reveal_v1`

Scope:

- add the explicit governed operator-surface value reveal path;
- keep values hidden from status/default surfaces;
- preserve audit/redaction and rollback boundaries;
- preserve no final financial-statement semantics and no cross-company comparability claims.
