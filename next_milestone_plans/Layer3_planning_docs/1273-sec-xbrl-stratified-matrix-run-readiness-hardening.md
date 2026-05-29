# 1273 - SEC XBRL Stratified Matrix Run-Readiness Hardening

## Target

`sec_edgar_stratified_real_filing_validation_matrix_run_readiness_hardening_v1`

## Purpose

This packet hardens the external stratified matrix harness before the next live SEC/Arelle execution. The goal is to prevent a future live report from overstating matrix coverage by counting repeated issuer chunks or by treating plan-level stratum coverage as post-run proof.

It does not run live SEC network, invoke Arelle, acquire sources, create sidecars, create datasets, create audit receipts, reveal values, or change runtime defaults.

## Runner Change

Script:

`diagnostics/assessment/sec-xbrl-real-corpus-product-runner.py`

The external plan validator now rejects plans that repeat an admitted issuer across chunks. This keeps the operator-selected matrix from satisfying breadth through duplicate issuer evidence.

When an external stratified plan is used, the report now includes `summary.strata_readiness` with:

- required strata;
- ready strata;
- missing strata;
- not-ready strata;
- blocked strata;
- unknown strata;
- per-stratum chunk counts and redacted matrix hashes.

The gate now includes `stratified_matrix_required_strata_readiness` and blocks unless every required stratum has ready post-run evidence and no required stratum has a blocked chunk.

## Current Status

The live matrix remains unrun by this packet. The next authorized live execution should use a duplicate-free off-repo plan and must satisfy both matrix-plan validation and stratum-level post-run readiness.

## Next Slice

`sec_edgar_stratified_real_filing_validation_matrix_live_execution_v1`

The next live pass should:

- use a fresh clean current-main worktree;
- use explicit live authorization, SEC user agent, Arelle env, taxonomy packages, cache, and isolated off-repo storage;
- use an off-repo duplicate-free stratified matrix plan;
- execute `diagnostics/assessment/sec-xbrl-real-corpus-product-runner.py --live --matrix-plan`;
- commit only redacted hashes, counts, forms, reason codes, readiness states, and non-admission evidence;
- stop on any redaction, default, completeness, matrix-plan, stratum-readiness, or product-path blocker.

## Non-Goals Preserved

- no runtime default change;
- no default-on Arelle cutover;
- no default-on value reveal;
- no committed raw issuer list;
- no production-readiness claim;
- no final financial-statement semantics claim;
- no cross-company comparability claim;
- no Candidate B routing, UI redesign, RAG, model, provider, or auth expansion.
