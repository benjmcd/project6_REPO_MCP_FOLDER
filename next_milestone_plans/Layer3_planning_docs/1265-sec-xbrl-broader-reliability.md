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

`broader_corpus_reliability_blocked`

The inherited real-corpus extraction/value gate remains strong:

- 12 real filings
- 6 issuer hashes
- forms `10-K`, `10-Q`, `20-F`, `40-F`, `6-K`, and `8-K`
- 18,156 Arelle resolved facts
- 18,156 bridge facts
- 23,102 value-bridge facts
- CompanyFacts effective-value match rate `0.9923`

The focused product-chain smoke proof also remains valid:

- 8 fake-client corpus records
- forms `10-K`, `10-Q`, `8-K`, `20-F`, `40-F`, and `6-K`
- sidecar selected as fact authority
- delivery/status, operator inspection, product surface, and durable archive ready
- operator value exposure still disabled

But broader real product-path reliability is not admitted, because the product-chain proof currently uses fake SEC client evidence and not a retained/live real-filing corpus product-chain run.

## Why This Blocks

The long-term SEC product objective requires operator-useful reliability over real heterogeneous filings. The current evidence proves:

- real extraction, completeness, bridge parity, and value correctness on a real corpus;
- product-chain continuity on a fake-client corpus.

It does not yet prove:

- product-chain readiness over a broader retained real corpus;
- operator inspection/product/archive readiness on those real retained filing receipts;
- redaction and non-admissions under that broader real product-chain run.

The gate therefore blocks instead of converting fake-client product smoke proof into a broader real-corpus claim.

## Next Slice

`sec_edgar_real_corpus_product_path_runner_v1`

Scope:

- acquire or reuse retained real SEC filing source bytes through the governed connector/source-artifact path;
- run the default-on Arelle sidecar product path over at least the 12-filing real corpus shape already admitted by the extraction/value gate;
- require forms `10-K`, `10-Q`, `20-F`, `40-F`, `6-K`, and `8-K`;
- prove validation, bridge, statement classification, statement product, package/review, handoff/export, delivery/status/provenance, operator inspection, operator product surface, and durable archive readiness;
- record a redacted per-filing product-path report by hash only;
- keep operator value reveal disabled;
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
