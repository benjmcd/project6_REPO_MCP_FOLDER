# 1266 - SEC XBRL Real-Corpus Product-Path Runner

## Target

`sec_edgar_real_corpus_product_path_runner_v1`

## Governing Posture

This is a diagnostic runner and gate report for the real-corpus product path. It changes the Arelle cutover runtime default only when invoked with `--apply-default-decision`; the gate has teeth. It does not change product/package/UI behavior, Gate B logic, operator value exposure, source shapes, or SEC routing.

The runner uses the existing governed SEC acquisition/source-artifact/receipt spine and the existing Arelle sidecar, bridge, statement classification, statement product, package/review, and handoff/export services for every supported filing. For matrices already admitted by the delivery/operator/archive services it also drives delivery/status/provenance, operator inspection, operator product surface, and durable archive. Broader extraction-gate matrices are not allowed to fail the default-on gate merely because the later archive surface admits a narrower matrix.

It fails closed unless a live run is explicitly requested with:

- a descriptive SEC user agent;
- the pinned Arelle execution environment;
- the offline taxonomy package configuration as explicit package files, not a package directory;
- an Arelle cache directory outside the repo and outside OneDrive, matching the sidecar containment contract;
- the default-off Arelle cutover enabled only inside the diagnostic run.

## Current Committed Report

Report:

`diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json`

Current decision:

`real_corpus_default_on_validated`

The committed report now records a live broader-corpus gate rerun after remediation. Breadth passed: 32 filings, 16 issuer hashes, all required forms present, and one `10-K/A` amended form observed. The product-path reliability gate passed:

- 30 supported inline-XBRL filings emitted Arelle sidecar authority and selected that sidecar as fact authority.
- 2 genuine no-inline-marker filings were diagnosed and allowed as zero-fact records.
- Arelle resolved facts matched the independent raw-inline lower-bound count: `52,558/52,558`.
- CompanyFacts effective-value correctness was `9,040/9,131`, match rate `0.99`, above the `0.98` gate.
- Operator value exposure remained disabled.
- The report records the diagnostic gate's default-decision artifact from that run. Current committed main remains default-off after the later governance remediation and live value-reveal proof; this report is not current runtime default-on admission by itself.

The remediation fixed the gate mechanics rather than weakening criteria: mixed taxonomy zip directories now load valid Arelle packages while reporting invalid package hashes/counts, the runner reads independent raw-inline counts from sidecar diagnostics, allowed no-inline records do not fail the extraction gate, and CompanyFacts identity is reconstructed only inside the diagnostic process without committing raw identities.

## Runner Behavior

Script:

`diagnostics/assessment/sec-xbrl-real-corpus-product-runner.py`

When run with `--live`, the runner:

- uses a gitignored diagnostic storage directory unless an explicit storage directory is supplied;
- enables SEC live network only inside the diagnostic process;
- applies a one-request-per-second SEC access posture;
- enables the Arelle resolved-fact authority cutover only inside the diagnostic process;
- runs the existing validation/product path over four four-issuer matrix chunks, targeting at least 30 filings across at least 15 distinct issuer hashes;
- can optionally use an off-repo `--matrix-plan` / `SEC_XBRL_STRATIFIED_MATRIX_PLAN` JSON file for the stratified real-filing matrix, while committed reports record only chunk hashes, issuer counts, strata, and readiness evidence;
- records only redacted matrix hashes, form counts, filing counts, issuer hashes, per-filing completeness counts, CompanyFacts value match rates, receipt hashes, readiness states, and non-admission evidence;
- computes CompanyFacts effective-value correctness over the standardized `us-gaap`, `dei`, and `ifrs-full` non-dimensional numeric intersection without committing raw values;
- records the gate verdict and, when explicitly invoked with `--apply-default-decision`, may apply that verdict in the diagnostic lane; later governance/current-main runtime authority can supersede that default decision;
- keeps operator value reveal disabled;
- restores settings after the diagnostic run.

## Gate Criteria

The report admits only if all criteria pass:

- live preflight satisfied;
- at least 30 real filings observed;
- at least 15 issuer hashes observed;
- required forms observed: `10-K`, `10-Q`, `20-F`, `40-F`, `6-K`, and `8-K`;
- every supported record uses the Arelle sidecar as the selected fact authority;
- every supported record reaches handoff/export through the Arelle-selected bridge path;
- completeness holds per supported filing: Arelle resolved fact count is greater than or equal to the independent raw inline fact count, with zero silent truncations;
- CompanyFacts effective-value match rate is at least `0.98` across the broader corpus, with mismatches diagnosed by count and raw values redacted;
- no unexpected blocked rows exist; genuine no-iXBRL filings may be zero-fact and diagnosed;
- operator values remain unexposed;
- final financial-statement semantics and cross-company comparability remain non-admitted.

## Non-Goals Preserved

- no runtime network default change;
- no operator value reveal;
- no Candidate-B routing for SEC semantics;
- no final financial-statement semantics claim;
- no cross-company comparability claim;
- no Gate B decision-logic redesign;
- no product/package/UI redesign;
- no RAG/vector/model/provider/auth behavior;
- no new Layer 3 source shape.

## Next Action

Next slice:

`sec_edgar_stratified_real_filing_validation_matrix_v1`

Scope:

- use the explicit-operator-only default-off posture selected by `1269-sec-xbrl-default-posture-decision.md`;
- use the operator runbook and matrix selection recorded in `1270-sec-xbrl-operator-runbook-matrix-selection.md`;
- execute or prepare the selected stratified validation matrix;
- preserve redaction and audit boundaries by default;
- preserve no final financial-statement semantics and no cross-company comparability claims.
