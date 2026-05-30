# 1271 - SEC XBRL Stratified Real-Filing Validation Matrix Preflight

## Target

`sec_edgar_stratified_real_filing_validation_matrix_preflight_v1`

## Purpose

This packet prepares the next live stratified real-filing validation matrix without running it. It is a validate-only guardrail between the selected operator runbook in `1270-sec-xbrl-operator-runbook-matrix-selection.md` and any live SEC/Arelle matrix execution.

The preflight does not fetch SEC data, invoke Arelle, acquire sources, create sidecars, create datasets, create audit receipts, reveal values, or change runtime defaults.

## Diagnostic

Script:

`diagnostics/assessment/sec-xbrl-stratified-real-filing-validation-matrix-preflight.py`

Report:

`diagnostics/assessment/sec-xbrl-stratified-real-filing-validation-matrix-preflight-report.json`

Current decision:

`stratified_matrix_preflight_requires_authorization_or_environment`

The committed report is expected to block until a future operator supplies all live-run conditions in an isolated environment:

- explicit matrix live-run authorization via `SEC_XBRL_STRATIFIED_MATRIX_LIVE_AUTHORIZED`;
- a descriptive SEC user agent through `LAYER3_SEC_EDGAR_USER_AGENT`;
- existing Arelle executable, taxonomy package files, and cache directory through the existing `SEC_XBRL_ARELLE_*` variables;
- existing off-repo runtime storage through `SEC_XBRL_STRATIFIED_MATRIX_STORAGE_DIR`.

## Checks

The diagnostic verifies:

- the operator runbook report selected `sec_edgar_stratified_real_filing_validation_matrix_v1`;
- committed SEC live network, Arelle fact-authority cutover, and Arelle value-reveal defaults remain off;
- the selected matrix still covers large domestic US-GAAP, small/mid domestic US-GAAP, foreign-private IFRS `20-F`, Canadian `40-F`, sparse `8-K`, sparse `6-K`, amendment/restatement-like filings, and no-inline/zero-fact diagnostics;
- committed matrix evidence uses strata, hashes, counts, forms, and reason-code posture, not raw issuer identities;
- the committed real-product runner baseline remains admitted before expansion;
- any future live execution has explicit authorization, user-agent, isolated off-repo storage, and Arelle environment readiness.

## Next Execution Tranche

`sec_edgar_stratified_real_filing_validation_matrix_v1`

The next live pass should use the existing governed SEC connector/source-artifact path and the existing Arelle subprocess isolation. It should run the selected strata in bounded chunks, retain raw SEC payloads and runtime artifacts outside the repo, and commit only redacted hashes, counts, forms, reason codes, readiness states, and non-admission evidence.

The real-corpus product runner now accepts an off-repo external plan through `--matrix-plan` or `SEC_XBRL_STRATIFIED_MATRIX_PLAN`. For this stratified tranche, the preflight requires that plan to be present and admitted; omitting it is a stop condition because the live runner otherwise falls back to the built-in broader-corpus matrix instead of the selected stratified plan. The plan must use schema `diagnostics.sec_xbrl_stratified_real_filing_validation_matrix_plan.v1`, mode `sec_edgar_stratified_real_filing_validation_matrix_v1`, and bounded chunks with admitted company identifiers plus required strata. The runner and preflight reject missing, unreadable, in-repo, or incomplete plans and keep issuer identities out of committed reports.

Large domestic companies such as major technology or semiconductor issuers may be useful inside the large-domestic stratum, but they are not sufficient by themselves. The matrix must also keep foreign, Canadian, sparse-report, amendment/restatement-like, small/mid-size, and no-inline diagnostic coverage.

## Stop Conditions

Stop before live execution if:

- explicit live SEC authorization is absent;
- the SEC user agent is absent;
- Arelle executable, taxonomy packages, or cache are missing;
- runtime storage is absent or inside the repo;
- an external matrix plan is missing, unreadable, inside the repo, has an unadmitted schema/mode, contains unadmitted issuer identifiers, or fails to cover every required stratum;
- committed defaults are no longer off;
- the selected matrix loses a required stratum;
- any report would expose raw issuer identity, accession, SEC URL, local path, retained bytes, raw values, operator contact, or actor text.

## Non-Goals Preserved

- no live SEC network run in this preflight;
- no Arelle subprocess invocation in this preflight;
- no source acquisition, sidecar creation, dataset creation, audit receipt creation, or value reveal request;
- no runtime default change;
- no production-readiness claim;
- no final financial-statement semantics claim;
- no cross-company comparability claim;
- no Candidate B routing, UI redesign, RAG, model, provider, or auth expansion.
