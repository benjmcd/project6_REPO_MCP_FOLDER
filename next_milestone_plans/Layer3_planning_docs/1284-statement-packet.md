# 1284 - Statement Packet

Milestone:

`sec_xbrl_statement_assembly_deferred_pending_linkbase_emission_v1`

## Scope

This implementation slice adds a redacted, reviewable SEC XBRL statement packet over existing canonical projection and statement-organization authority. It does not claim final financial-statement semantics.

Files in this slice:

- `backend/app/services/layer3_sec_xbrl_statement_assembly.py`
- `backend/tests/test_sec_xbrl_statement_assembly.py`
- `diagnostics/assessment/sec-xbrl-statement-assembly.py`
- `diagnostics/assessment/sec-xbrl-statement-assembly-report.json`
- `next_milestone_plans/Layer3_planning_docs/1284-statement-packet.md`

## Authority Chain

The packet consumes:

- canonical projection rows from Lineage B,
- the canonical statement-organization contract from the B-authoritative/A-corroborating organization slice,
- public identity residual magnitudes when supplied.

It groups non-absent canonical projection rows into `income`, `balance`, and `cashflow` packets. Rows keep canonical id, basis, family, statement, public standard source qname, status, mapping method, provenance completeness, and review exception state. Raw values and raw resolved fact authorities are not emitted in the committed report.

## Guardrails

The runtime blocks when projection rows are empty, when the organization contract fails, or when a row has no recognized statement. `oracle_absent` and unconfirmed rows are review exceptions, not silent successes.

The packet remains validate-only:

- no runtime default enablement,
- no live SEC network,
- no Arelle invocation,
- no value reveal,
- no persistence,
- no provider or connector dispatch,
- no linkbase emission,
- no per-period projection,
- no production-readiness claim,
- no final financial-statement semantics claim.

## Proof

Focused test:

`python -m pytest ./backend/tests/test_sec_xbrl_statement_assembly.py`

Result: `8 passed`.

Committed report:

`diagnostics/assessment/sec-xbrl-statement-assembly-report.json`

Report decision:

`sec_xbrl_statement_assembly_validate_only_ready`

## Next Posture

`sec_xbrl_multi_period_projection_design_v1`

Follow-on implementation is tracked in `next_milestone_plans/Layer3_planning_docs/1285-multi-period.md`.
