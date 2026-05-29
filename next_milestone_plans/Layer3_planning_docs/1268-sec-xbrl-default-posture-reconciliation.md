# 1268 - SEC XBRL Default-Posture Reconciliation

## Target

`sec_edgar_arelle_default_posture_decision_v1`

## Purpose

This packet reconciles three now-current facts that can otherwise be misread as conflicting:

- broader real-corpus product-path reliability is admitted by the current reliability gate;
- governed value reveal has been proven for two bounded live filings through coherent sidecar, value-store, bridge, dataset, provenance, and receipt authority;
- committed runtime defaults remain off after governance remediation.

This is a planning/control reconciliation. It does not acquire filings, run Arelle, expose values, mutate defaults, stage a runtime cutover, or change product/UI behavior.

## Current Decision

Current posture:

`explicit_operator_only_default_off`

The project has enough evidence to proceed to a default-posture decision. That decision is recorded in follow-up packet `1269-sec-xbrl-default-posture-decision.md`, which selects the explicit-operator-only default-off posture.

## Evidence Now Available

- `diagnostics/assessment/sec-xbrl-broader-corpus-reliability-gate-report.json` admits broader real-product reliability using the current live real-product runner report, not fake-client evidence alone.
- `diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json` proves broad live real-product path behavior by counts, hashes, forms, sidecar authority, handoff/export readiness, CompanyFacts match rate, and redaction/non-admission evidence.
- `diagnostics/assessment/sec-xbrl-value-reveal-live-proof-report.json` proves two bounded governed live value-reveal exercises with coherent authority bundles, idempotent receipt reuse, status redaction, flag-off blocking, and audit receipt redaction.
- `diagnostics/assessment/sec-xbrl-default-on-runtime-report.json` remains the current runtime-default authority and keeps the runtime default disabled by governance remediation.

## Next Pass

The explicit default-posture decision pass is now complete in `1269-sec-xbrl-default-posture-decision.md`. It chose:

- keep `explicit_operator_only_default_off` as the governed product posture.

It did not choose:

- design a new default-on admission gate with rollback, CI/local/Arelle-absent behavior, and operator-surface boundaries;
- design a staged default-on experiment with a narrow corpus, bounded operators, and a separate rollback plan.

The decision pass did not silently treat the broader reliability admission as a runtime default change.

## Required Checks Before Any Runtime Default Change

- committed defaults are still off before the pass begins;
- flag-off behavior still blocks with current reason codes;
- default status/product surfaces remain value-redacted;
- redacted reports contain no raw identity, accession, URL, local path, storage root, operator actor, contact, raw value, or retained filing payload;
- Arelle-absent behavior fails closed rather than silently falling back to incomplete parsing;
- rollback steps and owner/operator confirmation are documented before any default change;
- CI/local behavior is defined without depending on live SEC network or shared seeded state.

## Non-Goals Preserved

- no default-on Arelle cutover in this reconciliation;
- no default-on value reveal in this reconciliation;
- no production-readiness claim;
- no final financial-statement semantics claim;
- no cross-company comparability claim;
- no Candidate B SEC routing;
- no RAG, model, provider, auth, or UI expansion.
