# 1341 SEC XBRL rollback and monitoring gate

Target: `sec_xbrl_rollback_monitoring_gate_v1`.

This slice defines the validate-only rollback and monitoring gate for Layer 3
SEC XBRL production-admission review. It does not start monitors, enable alerts,
mutate runtime defaults, or touch production data.

## Required rollback evidence

The gate requires proof that:

- atomic projection faults roll back;
- atomic statement-packet faults roll back;
- atomic workflow faults roll back;
- API auth-binding failure rolls back;
- operator decision auth-binding failure rolls back;
- value reveal auth-binding failure rolls back;
- no partial projection rows remain;
- no partial statement-packet rows remain;
- no partial workflow rows remain;
- no partial decision rows remain;
- no partial reveal receipts remain.

## Required monitoring coverage

The gate requires hash/count/state-only event coverage for:

- `offline_evidence_proof_blocked`;
- `atomic_persistence_rollback`;
- `redaction_containment_blocked`;
- `evidence_authority_gap`;
- `operator_decision_recorded`;
- `value_reveal_attempt`;
- `value_reveal_denied`;
- `production_admission_denied`.

Monitoring evidence must prove:

- events are hash/count/state-only;
- metrics are hash/count/state-only;
- alerts carry runbook references;
- monitoring remains default-off until configured;
- raw values are not logged;
- local paths are not logged;
- raw authority references are not logged.

## Current boundary

The service `layer3_sec_xbrl_rollback_monitoring_gate.py` can report
`sec_xbrl_rollback_monitoring_gate_ready` as a production-admission input, but
it still reports:

- `monitoring_started=false`;
- `alerts_enabled=false`;
- `runtime_default_enabled=false`;
- `api_route_enabled=false`;
- `rendered_ui_enabled=false`;
- `value_reveal_performed=false`;
- `production_database_touched=false`;
- `production_readiness_claimed=false`.

This means the gate proves the required operational contract shape without
turning on operational behavior.

## Sequencing

This gate depends on controlled value reveal gate readiness and feeds the
production-admission gate as `rollback_monitoring`. It is still not sufficient
for production admission by itself. Runbooks, multi-filing authority, targeted
validation, actual API/UI implementation, and final release review still need
direct evidence.
