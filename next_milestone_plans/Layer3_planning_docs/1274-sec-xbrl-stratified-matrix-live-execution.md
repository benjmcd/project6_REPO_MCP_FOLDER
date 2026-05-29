# 1274 - SEC XBRL Stratified Matrix Live Execution

## Target

`sec_edgar_stratified_real_filing_validation_matrix_live_execution_v1`

## Purpose

This packet records the authorized live SEC/Arelle stratified real-filing matrix execution after the default-off operator posture, validate-only preflight, external-plan harness, and run-readiness hardening were in place.

The live operator artifacts, raw SEC payloads, taxonomy/cache state, matrix plan, retained bytes, local runtime database, and full runner output remain outside the repo. The committed evidence is a redacted proof report only.

## Proof Report

Report:

`diagnostics/assessment/sec-xbrl-stratified-real-filing-validation-matrix-live-report.json`

The report records:

- current live main SHA used;
- preflight decision and preflight report hash;
- product-runner decision, gate verdict, source report hash, and byte count;
- external matrix plan mode/state and chunk count;
- forms/counts/readiness results;
- stratum-level readiness;
- default-off posture preservation;
- redaction and non-goal evidence.

## Result

Decision: `stratified_matrix_live_execution_ready`.

The live matrix used an off-repo duplicate-free external plan and passed the current product-runner gate. It produced 32 real filings across 16 issuer hashes, all required forms, all required strata ready, zero unexpected blocked/degraded records, zero unexpected zero-inline records, and CompanyFacts value-correctness match rate above the configured threshold.

The runner's historical default-on gate wording remains source-local to the diagnostic runner; this packet does not apply that default decision. The committed operating posture remains `explicit_operator_only_default_off`.

## Boundaries

This packet does not:

- enable SEC live network by default;
- enable Arelle fact-authority cutover by default;
- enable Arelle value reveal by default;
- commit raw issuer identity, accession numbers, SEC URLs, retained bytes, local paths, operator contact strings, or raw values;
- claim production readiness;
- claim final financial-statement semantics;
- claim cross-company comparability;
- expand Candidate B, UI, RAG, model, provider, connector, auth, or package behavior.

## Next Slice

`sec_edgar_stratified_matrix_result_reconciliation_and_default_off_operator_readiness_decision_v1`

The next pass should reconcile the live matrix evidence against the selected default-off posture and decide whether the project is ready for broader explicit-operator use, needs a second matrix run, or needs targeted remediation before any broader default or product-surface admission.
