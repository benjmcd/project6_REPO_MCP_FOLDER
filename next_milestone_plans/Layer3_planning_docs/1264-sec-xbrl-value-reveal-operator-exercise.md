# 1264 - SEC XBRL Value-Reveal Operator Exercise

## Target

`sec_edgar_arelle_value_reveal_operator_exercise_v1`

## Current Authority

Current main has the governed Arelle value-reveal endpoint and audit receipt path implemented, while both deployment defaults remain off:

- `layer3_sec_edgar_arelle_fact_authority_cutover_enabled = False`
- `layer3_sec_edgar_arelle_value_reveal_enabled = False`

This packet does not change either default. It records the next admissible operator-utility step after the post-1966 governance remediation and before any reveal default-enablement or renewed default-on Arelle cutover attempt.

## Why This Comes Next

The value-reveal capability now exists, but the next product question is not more rendered detail or broader parser work. The next product question is whether an operator can deliberately reveal values for a bound filing, correlate that reveal with a persisted audit receipt, and still trust that every non-reveal surface remains redacted.

That makes this an operator exercise, not a new runtime expansion.

## Exercise Scope

The exercise may only use already-governed authorities:

- a READY persisted Arelle resolved-fact sidecar receipt id/hash
- a matching `dataset_version` id/hash
- bridge/source/parser/connector/source-artifact lineage hashes already carried by those receipts
- the existing sibling endpoint `POST /api/v1/layer3/source/sec-edgar/real-company-corpus/operator-value-reveal`
- the existing status endpoint `GET /api/v1/layer3/source/sec-edgar/real-company-corpus/operator-value-reveal/status/{reveal_receipt_id}`

The reveal flag may be enabled only in an isolated local/operator runtime for the exercise. The committed default stays off.

## Required Exercise Sequence

1. Verify current main, open PRs, and deployment defaults.
2. Enable `LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED=true` only for the isolated exercise runtime.
3. Submit a reveal request with:
   - `schema_id = layer3.sec_edgar_arelle_value_reveal_request.v1`
   - stable `client_request_id`
   - non-empty actor self-attestation
   - `operator_reveal_confirmation = true`
   - sidecar receipt id/hash
   - dataset version id/hash
4. Confirm the response returns effective Arelle values and resolved structural semantics for the bound filing.
5. Confirm identity-like fact values remain redacted in the reveal response.
6. Confirm the persisted audit receipt contains hashes/counts/lineage only, not raw values or raw actor text.
7. Re-submit the same request and confirm idempotent replay returns the same reveal receipt.
8. Read the audit-receipt status projection and confirm it returns no values.
9. Read the default operator product surface for the same filing and confirm `raw_values_returned` remains false.
10. Turn the reveal flag off and confirm both reveal and reveal-status requests block with `sec_edgar_arelle_value_reveal_feature_flag_disabled`.

## Proof Required

The proof packet for the actual exercise must report:

- current main SHA
- isolated runtime posture and confirmation that no committed defaults changed
- sidecar/dataset binding evidence by hash only
- revealed fact count
- audit receipt id/hash
- idempotent replay result
- redacted audit-status result
- default product-surface no-value result
- flag-off blocked result
- redaction scan over committed artifacts

The proof must not commit raw values, raw actor text, raw issuer identity, SEC URLs, accessions, tickers, local paths, storage roots, contact strings, or provider/browser authority.

## Diagnostics Packet

`diagnostics/assessment/sec-xbrl-value-reveal-operator-exercise.py` is a validate-only readiness check. It does not perform the operator exercise, enable flags, fetch SEC data, run Arelle, create sidecars, create audit receipts, or reveal values. It verifies that the current code, API route, tests, and planning surface are ready for the bounded operator exercise.

The committed report is:

`diagnostics/assessment/sec-xbrl-value-reveal-operator-exercise-report.json`

The separate run preflight is:

`diagnostics/assessment/sec-xbrl-value-reveal-operator-exercise-runner.py`

It must block, not fabricate, when the configured storage authority does not contain READY sidecar and bridge/dataset receipts. Its current blocked result is recorded in doc `1265`.

## Non-Goals

- no default-on Arelle cutover
- no default-on value reveal
- no broad corpus expansion
- no SEC network fetch by this planning/check packet
- no sidecar creation by this planning/check packet
- no new Layer 3 source shape
- no bridge, Gate B, package, archive, or product redesign
- no parser expansion
- no final financial-statement semantics claim
- no cross-company comparability claim
- no Candidate B routing for SEC semantics
- no RAG, model, provider, auth, or mockup behavior

## Next Slices

If the operator exercise succeeds:

1. `sec_edgar_arelle_value_reveal_default_enablement_gate_v1`
   Decide whether deployment-wide reveal-flag enablement is warranted, still separate from Arelle cutover default-on.

2. `sec_edgar_arelle_governance_remediation_followups_v1`
   Refresh the post-1966 default-on evidence before any renewed Arelle cutover default-on attempt.

If the operator exercise fails:

1. `sec_edgar_arelle_value_reveal_operator_exercise_remediation_v1`
   Patch only the failed reveal/audit/redaction/operator-utility criterion, then rerun the exercise.

If the operator exercise cannot start because persisted real-filing authorities are absent:

1. `sec_edgar_arelle_value_reveal_operator_exercise_authority_provisioning_v1`
   Point the isolated runtime at existing retained real-filing sidecar/dataset authorities, or run a separate governed authority-provisioning pass before submitting any reveal request.
