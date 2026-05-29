# 1272 - SEC XBRL Stratified Matrix External Plan Harness

## Target

`sec_edgar_stratified_real_filing_validation_matrix_external_plan_harness_v1`

## Purpose

This packet wires the existing real-corpus product-path runner so the next authorized live matrix can use a stratified operator-selected plan without committing raw issuer identities.

It does not run live SEC network, invoke Arelle, acquire sources, create sidecars, create datasets, create audit receipts, reveal values, or change runtime defaults.

## Runner Change

Script:

`diagnostics/assessment/sec-xbrl-real-corpus-product-runner.py`

The runner now accepts an optional external plan through:

- `--matrix-plan`
- `SEC_XBRL_STRATIFIED_MATRIX_PLAN`

The plan must be outside the repo and outside OneDrive when supplied as a file. The runner records only a plan-path marker, chunk hashes, issuer counts, strata, strata hashes, forms, readiness counts, and reason codes.

## Plan Contract

External plan schema:

`diagnostics.sec_xbrl_stratified_real_filing_validation_matrix_plan.v1`

External plan mode:

`sec_edgar_stratified_real_filing_validation_matrix_v1`

Each chunk must include a bounded `matrix_label`, an admitted `company_matrix`, and one or more required strata. The plan is rejected if it is missing, unreadable, stored inside the repo/OneDrive, uses an unadmitted schema or mode, contains unadmitted issuer identifiers, has duplicate or missing labels, exceeds the chunk limit, or fails to cover every required stratum selected in `1270-sec-xbrl-operator-runbook-matrix-selection.md`.

## Current Status

The default runner path still supports the previous built-in broader-corpus matrix. The stratified path is opt-in and requires the external plan plus the existing live preflight requirements.

No raw issuer identities, accessions, SEC URLs, retained bytes, local paths, user-agent strings, actor text, or values are committed by this harness.

## Next Slice

`sec_edgar_stratified_real_filing_validation_matrix_v1`

The next live pass should:

- rerun `1271` preflight with explicit live authorization, SEC user agent, Arelle env, off-repo storage, and an off-repo stratified matrix plan;
- execute the real-corpus product runner with `--live --matrix-plan`;
- retain raw plan, raw SEC payloads, cache, taxonomy packages, values, and runtime artifacts off-repo;
- commit only redacted report evidence;
- stop on any redaction, default, completeness, plan, or product-path blocker.

## Non-Goals Preserved

- no runtime default change;
- no default-on Arelle cutover;
- no default-on value reveal;
- no new committed raw issuer list;
- no production-readiness claim;
- no final financial-statement semantics claim;
- no cross-company comparability claim;
- no Candidate B routing, UI redesign, RAG, model, provider, or auth expansion.
