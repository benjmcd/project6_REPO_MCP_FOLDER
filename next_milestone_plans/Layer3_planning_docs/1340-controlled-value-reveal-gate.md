# 1340 SEC XBRL controlled value reveal gate

Target: `sec_xbrl_controlled_value_reveal_gate_v1`.

This slice defines the validate-only gate for controlled value reveal. It does
not reveal values, enable a route, toggle runtime defaults, or mutate production
state. It specifies the evidence needed before a controlled release path can
count toward production-admission review.

## Required behavior

Controlled value reveal must prove:

- operator review decision is present;
- server-owned reveal authority is present;
- auth binding is required;
- operator reveal confirmation is required;
- values are transient only;
- audit receipts are hash/count-only;
- status surfaces are hash/count/state-only;
- default behavior remains off without a receipt;
- identity-like values are redacted;
- auth-binding failures roll back the reveal receipt;
- sidecar and value-store authority are resolved server-side.

Controlled value reveal must not:

- persist raw values;
- expose raw values in status;
- return raw sidecar payloads;
- return raw storage payloads;
- admit client-supplied sidecars;
- admit client-supplied value stores;
- acquire SEC sources;
- invoke Arelle;
- enable runtime defaults;
- perform reveal during gate inspection.

## Current boundary

The service `layer3_sec_xbrl_controlled_value_reveal_gate.py` reports
`sec_xbrl_controlled_value_reveal_gate_ready` only as a contract/admission input.
It still reports:

- `value_reveal_performed=false`;
- `runtime_default_enabled=false`;
- `api_route_enabled=false`;
- `rendered_ui_enabled=false`;
- `production_database_touched=false`;
- `production_readiness_claimed=false`.

## Sequencing

This gate depends on the operator UI controls gate, an operator review decision
gate, and a server-owned value reveal authority gate. It should feed the
production-admission gate as `controlled_value_reveal`, but it is not sufficient
for production admission by itself. Rollback, monitoring, runbooks, multi-filing
authority, and targeted validation still need independent evidence.
