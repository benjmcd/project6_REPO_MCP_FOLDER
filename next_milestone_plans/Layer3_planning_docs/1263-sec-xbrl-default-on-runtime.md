# 1263 - SEC XBRL Default-On Runtime (Superseded)

## Target

`sec_edgar_arelle_fact_authority_default_on_runtime_v1`

## Superseded Posture

> Superseded by 1313-1317 for current default-on posture: retained as historical candidate evidence, not live posture authority.


This packet is historical candidate/default-on runtime planning. It is superseded by PR #1966 and `1261-sec-xbrl-arelle-governance-remediation.md`.

Current main restores:

- `LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED=false`
- Arelle resolved-fact authority remains implemented and explicitly flag-gated
- the regex authority path remains the default bridge input unless an operator explicitly enables the Arelle cutover flag
- value reveal remains default-off and is available only through the governed sibling endpoint

This file must not be read as the live runtime posture. Runtime default-on is not currently enabled.

## Retained Candidate Evidence

The earlier default-on candidate evidence remains useful as evidence, not as live admission:

- core default-on gate corpus: 12 real filings, 6 issuer hashes
- forms included `10-K`, `10-Q`, `20-F`, `40-F`, `6-K`, and `8-K`
- Arelle resolved facts: `18,156`
- bridge facts: `18,156`
- expanded value materialization facts: `23,102`
- CompanyFacts effective-value correctness: `3,761/3,790`, match rate `0.9923`

The broader real-corpus product-path evidence also remains retained evidence, not current default-on admission:

- 32 filings
- 16 issuer hashes
- required form diversity present
- completeness and value-correctness evidence recorded in the generated diagnostics

## Current Runtime Report

Report:

`diagnostics/assessment/sec-xbrl-default-on-runtime-report.json`

Current decision:

`default_on_runtime_disabled_by_governance_remediation`

The current runtime report records that the Arelle bridge remains implemented, persisted-sidecar-based, fail-closed, and reversible, but not default-on.

## Required Before Any Future Default-On Attempt

Before any future default-on runtime slice can be selected again, a follow-up packet must restate current evidence for:

- sidecar selected for every supported record
- product-path readiness across all validation chunks
- completeness aggregate and unexpected zero-inline handling
- CompanyFacts oracle coverage and mismatch framing
- no silent regex fallback while the flag is on
- no synchronous Arelle invocation in bridge, Gate B, product, or package paths
- no raw identity, SEC URL, local path, storage root, or contact disclosure

The required next governance posture is:

`sec_edgar_arelle_governance_remediation_followups_v1`

## Non-Goals Preserved

- no default-on Arelle cutover in current main
- no default-on value reveal
- no Candidate-B routing for SEC semantics
- no final financial-statement semantics claim
- no cross-company comparability claim
- no Gate B decision-logic redesign
- no product/package/UI redesign
- no RAG/vector/model/provider/auth behavior
- no new Layer 3 source shape
