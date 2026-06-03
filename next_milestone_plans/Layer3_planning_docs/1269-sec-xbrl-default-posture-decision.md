# 1269 - SEC XBRL Default-Posture Decision

> Superseded by 1313-1317: this file is retained as historical pre-cutover posture evidence; current posture is governed by the default-on admission restatement and runtime design lineage.


## Target

`sec_edgar_arelle_default_posture_decision_v1`

## Decision

Selected posture:

`explicit_operator_only_default_off`

This decision keeps SEC live network, Arelle fact-authority cutover, and Arelle value reveal disabled by default while allowing value reveal only through explicit governed operator action.

## Decision Report

Report:

`diagnostics/assessment/sec-xbrl-default-posture-decision-report.json`

Decision:

`explicit_operator_only_default_off_selected`

## Basis

The decision report proves all required inputs for this posture:

- committed defaults remain off in source and in the live proof packet;
- broader real-product reliability is admitted by the current broader reliability gate;
- the live real-product runner proves product-path behavior over 32 filings, 16 issuer hashes, 30 supported records, sidecar authority selection, handoff/export readiness, and CompanyFacts match rate `0.99`;
- the bounded governed live value-reveal proof covers one FY2025 `10-K` and one FY2026 `10-Q`;
- reveal idempotency, status redaction, flag-off blocking, and audit receipt redaction are proven for both bounded filings;
- the current runtime-default report remains default-off;
- the default-on admission review does not currently admit a runtime default-on slice;
- raw identities, accessions, URLs, local paths, contact strings, raw value records, and raw values remain uncommitted.

## Deferred Postures

The broader reliability admission is not converted into a runtime default change.

The following remain deferred:

- default-on Arelle fact-authority cutover, pending a separate reviewed admission gate and rollback plan;
- default-on value reveal, pending a separate operator policy, auth, retention, and audit review;
- staged default-on experiment, pending a bounded operator cohort and rollback plan.

## Next Slice

`sec_edgar_stratified_real_filing_validation_matrix_v1`

The operator runbook and matrix-selection packet is recorded in `1270-sec-xbrl-operator-runbook-matrix-selection.md`.

Scope for the next execution tranche:

- execute or prepare the selected stratified matrix under the explicit-operator-only default-off posture;
- retain raw inputs and runtime artifacts outside the repo;
- commit only redacted hashes, counts, forms, reason codes, and readiness results;
- keep live-network, Arelle cutover, and value reveal defaults off.

## Non-Goals Preserved

- no runtime default change;
- no live SEC network run in this decision pass;
- no Arelle subprocess invocation in this decision pass;
- no value reveal request in this decision pass;
- no source acquisition, dataset creation, audit receipt creation, or UI change;
- no production-readiness claim;
- no final financial-statement semantics claim;
- no cross-company comparability claim;
- no Candidate B SEC routing;
- no RAG, model, provider, auth, or UI expansion.
