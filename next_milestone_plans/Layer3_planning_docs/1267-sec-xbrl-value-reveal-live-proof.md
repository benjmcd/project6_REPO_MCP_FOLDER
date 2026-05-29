# 1267 - SEC XBRL Value-Reveal Live Proof

## Target

`sec_edgar_arelle_value_reveal_live_authority_and_operator_exercise_v1`

## Purpose

This packet records the first current-main live authority-provisioning plus governed value-reveal proof after the Arelle IXDS and IFRS correctness fixes landed in PR `#1982`.

The proof was executed from current `project6-origin/main` at commit `f2f7efaf2f9bc5317d59d6134e3693b7e8fe125a`, using a clean worktree and isolated runtime state. The root checkout was not used as execution authority.

## Proof Report

Report:

`diagnostics/assessment/sec-xbrl-value-reveal-live-proof-report.json`

Current decision:

`value_reveal_live_authority_and_operator_exercise_proven_for_two_bounded_filings`

## What Was Proven

Two bounded domestic inline-XBRL filings were provisioned and exercised through the existing governed services:

- FY2025 `10-K`, using a matching `us-gaap-2025` taxonomy package.
- FY2026 `10-Q`, using a matching `us-gaap-2026` taxonomy package.

For each filing, the run produced one coherent authority bundle:

- READY Arelle resolved-fact sidecar receipt.
- Persisted internal value store.
- Bridge receipt with dataset version id/hash.
- Runtime dataset row and dataset-source provenance bound to the dataset hash.
- Governed value-reveal receipt.

For each filing, the value-reveal exercise proved:

- reveal request returned `ready`;
- idempotent replay with the same request reused the same receipt id/hash;
- replay did not create a second receipt;
- status/default projection remained value-redacted;
- flag-off reveal and status requests blocked with `sec_edgar_arelle_value_reveal_feature_flag_disabled`;
- persisted audit receipt did not contain raw value records or effective-value fields.

## Redaction Boundary

The report intentionally records only forms, fiscal labels, taxonomy-package match, counts, hashes, and reason codes.

It does not commit issuer identity, ticker, accession, SEC URL, local path, storage root, raw SEC payload, raw financial values, actor text, or operator contact.

Reportable bundle references and reveal receipts were scanned for identity/accession/URL/path/contact/value-record leakage before this packet was written.

## Defaults

Committed defaults remain off:

- `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED=false`
- `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED=false`
- `LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED=false`

This proof does not admit default-on runtime behavior by itself.

## Non-Goals Preserved

- no default-on Arelle cutover claim;
- no default-on value-reveal claim;
- no production-readiness claim;
- no final financial-statement semantics claim;
- no cross-company comparability claim;
- no Candidate B routing for SEC semantics;
- no RAG, model, provider, auth, or UI expansion.

## Next Slice

`sec_edgar_stratified_real_filing_validation_matrix_v1`

The default-posture reconciliation, decision, and operator runbook/matrix selection are now recorded in `1268-sec-xbrl-default-posture-reconciliation.md`, `1269-sec-xbrl-default-posture-decision.md`, and `1270-sec-xbrl-operator-runbook-matrix-selection.md`. The selected posture is explicit-operator-only and default-off. The next pass should execute or prepare the selected stratified validation matrix without weakening the default-off governance boundary.
