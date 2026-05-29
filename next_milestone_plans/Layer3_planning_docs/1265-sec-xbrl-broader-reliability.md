# 1265 - SEC XBRL Broader Corpus Reliability Gate

## Target

`sec_edgar_default_on_broader_corpus_reliability_gate_v1`

## Governing Posture

This is a reliability gate, not a runtime expansion.

It reads committed redacted reports only. It does not acquire filings, run Arelle, mutate bridge/Gate B/product/package/UI behavior, expose values, add a new source shape, or infer real-corpus product reliability from fake-client evidence.

## Current Decision

Report:

`diagnostics/assessment/sec-xbrl-broader-corpus-reliability-gate-report.json`

Decision:

`broader_corpus_reliability_admitted`

The inherited real-corpus extraction/value gate remains strong:

- 12 real filings
- 6 issuer hashes
- forms `10-K`, `10-Q`, `20-F`, `40-F`, `6-K`, and `8-K`
- 18,156 Arelle resolved facts
- 18,156 bridge facts
- 23,102 value-bridge facts
- CompanyFacts effective-value match rate `0.9923`

The focused product-chain smoke proof also remains valid as a continuity check:

- 8 fake-client corpus records
- forms `10-K`, `10-Q`, `8-K`, `20-F`, `40-F`, and `6-K`
- sidecar selected as fact authority
- delivery/status, operator inspection, product surface, and durable archive ready
- operator value exposure still disabled

Broader real product-path reliability is now admitted because the gate also reads the current committed live real-product runner report:

- 32 real filings
- 16 issuer hashes
- forms `10-K`, `10-K/A`, `10-Q`, `20-F`, `40-F`, `6-K`, and `8-K`
- 30 supported inline-XBRL filings reached sidecar authority, selected that sidecar as fact authority, and reached handoff/export
- 2 genuine no-inline-marker filings were diagnosed as zero-fact records rather than silently treated as product failures
- Arelle resolved facts matched the independent inline lower bound: `52,558/52,558`
- CompanyFacts effective-value correctness was `9,040/9,131`, match rate `0.99`, above the `0.98` gate
- operator value exposure remained disabled
- raw identities, accessions, URLs, values, and local storage roots remain uncommitted

## Why This Is Admitted

The long-term SEC product objective requires operator-useful reliability over real heterogeneous filings. The current evidence now proves both:

- real extraction, completeness, bridge parity, and value correctness on a real corpus;
- focused product-chain continuity on a fake-client corpus;
- broader product-path readiness over a retained/live real-filing corpus;
- redaction and non-admissions under that broader real product-chain run.

The gate does not convert fake-client evidence into a real-corpus claim. It admits broader reliability only because the current real-product runner report independently proves live-network, non-fake-client product-path evidence with supported-record, fact-count, CompanyFacts, and redaction floors.

## Next Slice

`sec_edgar_stratified_real_filing_validation_matrix_v1`

Scope:

- use the default-posture decision recorded in `1269-sec-xbrl-default-posture-decision.md`;
- use the operator runbook and matrix selection recorded in `1270-sec-xbrl-operator-runbook-matrix-selection.md`;
- execute or prepare the selected stratified validation matrix under the explicit-operator-only default-off posture;
- preserve current committed defaults unless and until a separate reviewed runtime-default decision is made;
- keep value reveal gated and default-off;
- preserve no final financial-statement semantics and no cross-company comparability admissions.

## Non-Goals Preserved

- no runtime default change
- no operator value reveal
- no Candidate-B routing for SEC semantics
- no final financial-statement semantics claim
- no cross-company comparability claim
- no Gate B decision-logic redesign
- no product/package/UI redesign
- no RAG/vector/model/provider/auth behavior
- no new Layer 3 source shape
