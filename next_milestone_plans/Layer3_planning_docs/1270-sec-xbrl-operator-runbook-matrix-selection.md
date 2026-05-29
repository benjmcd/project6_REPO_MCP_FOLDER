# 1270 - SEC XBRL Operator Runbook and Stratified Matrix Selection

## Target

`sec_edgar_operator_readiness_runbook_and_stratified_matrix_selection_v1`

## Decision

Decision report:

`diagnostics/assessment/sec-xbrl-operator-runbook-matrix-selection-report.json`

Decision:

`operator_runbook_and_stratified_matrix_selection_ready`

This packet makes the explicit-operator-only default-off posture operationally usable for the next validation tranche. It does not run live SEC network, invoke Arelle, reveal values, acquire sources, create datasets, create audit receipts, or change runtime defaults.

## Operator Runbook Controls

The next live/operator pass must:

- start from a clean worktree on current `project6-origin/main`;
- keep committed SEC live network, Arelle cutover, and value-reveal defaults off;
- require explicit live SEC authorization before any network call;
- use an isolated off-repo Arelle environment, taxonomy package set, cache, retained bytes, and runtime artifacts;
- run validate-only preflight before live work;
- use the governed SEC connector and source-artifact path;
- require one coherent sidecar, value-store, bridge, dataset, and provenance bundle before reveal;
- use explicit operator confirmation for value reveal;
- preserve status and default-surface redaction;
- run redaction scans before reporting;
- record only hashes, counts, forms, and reason codes in committed artifacts;
- stop on Arelle, taxonomy, redaction, identity-leak, or coherent-bundle failure;
- never change runtime defaults as part of the operator run.

## Stratified Matrix

The next matrix should not be a list of prominent companies alone. Large domestic issuers are useful as one stratum, but they must not replace foreign, amendment, sparse-report, small/mid-size, and no-inline diagnostic coverage.

Selected strata:

- large domestic US-GAAP `10-K`/`10-Q`;
- small or mid-size domestic US-GAAP `10-K`/`10-Q`;
- foreign-private IFRS `20-F`;
- Canadian `40-F`;
- sparse current-report `8-K`;
- sparse foreign-report `6-K`;
- amended or restatement-like `10-K/A`, `10-Q/A`, or `20-F/A`;
- diagnosed no-inline or zero-fact filings.

Named issuer examples may be used by an operator during live selection, but committed reports should keep issuer identity redacted or hash-only. For example, large domestic technology/software/semiconductor issuers can be useful inside the first stratum, but they are not sufficient as the matrix.

## Next Slice

`sec_edgar_stratified_real_filing_validation_matrix_v1`

The validate-only preflight for this slice is recorded in `1271-sec-xbrl-stratified-real-filing-validation-matrix-preflight.md`. The live matrix remains blocked until that preflight has explicit authorization and isolated runtime evidence.

Scope:

- run or prepare a bounded live matrix using the selected strata;
- keep default-off and explicit-operator-only posture;
- retain raw SEC payloads, cache, taxonomy packages, local paths, and values outside the repo;
- commit only redacted hashes, counts, forms, reason codes, and readiness results;
- prove sidecar authority, product-path readiness, redaction, and non-admissions for the expanded matrix;
- do not claim production readiness, final financial-statement semantics, or cross-company comparability.

## Non-Goals Preserved

- no runtime default change;
- no live SEC network run in this selection pass;
- no Arelle subprocess invocation in this selection pass;
- no value reveal request in this selection pass;
- no source acquisition, dataset creation, or audit receipt creation in this selection pass;
- no raw issuer identity, accession, SEC URL, local path, storage root, retained payload, or value committed;
- no production-readiness claim;
- no final financial-statement semantics claim;
- no cross-company comparability claim.
