# 1342 SEC XBRL runbook gate

Target: `sec_xbrl_runbook_gate_v1`.

This slice defines the validate-only runbook gate for Layer 3 SEC XBRL
production-admission review. It does not execute runbooks, enable monitoring,
toggle runtime defaults, or touch production state.

## Required runbooks

The gate requires runbooks for:

- `offline_evidence_proof_blocked`;
- `atomic_persistence_rollback`;
- `redaction_containment_blocked`;
- `evidence_authority_gap`;
- `operator_authority_resolver_failure`;
- `operator_decision_failure`;
- `value_reveal_denied`;
- `value_reveal_incident`;
- `monitoring_alert_response`;
- `production_admission_denied`;
- `production_release_rollback`.

## Required runbook fields

Each runbook must declare:

- owner;
- severity;
- trigger event;
- diagnostic command;
- rollback decision tree;
- escalation path;
- customer impact guidance;
- post-incident review;
- hash/count/state-only evidence policy.

Each runbook must not require:

- destructive commands;
- raw values;
- raw authority references;
- local paths;
- manual database mutation;
- runtime default toggles;
- source acquisition;
- Arelle invocation.

## Current boundary

The service `layer3_sec_xbrl_runbook_gate.py` can report
`sec_xbrl_runbook_gate_ready` as a production-admission input, but it still
reports:

- `runbooks_executed=false`;
- `monitoring_started=false`;
- `alerts_enabled=false`;
- `runtime_default_enabled=false`;
- `api_route_enabled=false`;
- `rendered_ui_enabled=false`;
- `value_reveal_performed=false`;
- `production_database_touched=false`;
- `production_readiness_claimed=false`.

This keeps operational documentation readiness separate from operational
execution.

## Sequencing

This gate depends on rollback/monitoring gate readiness and feeds the
production-admission gate as `runbook`. It is still not sufficient for production
admission by itself. Multi-filing authority, authority resolver evidence,
targeted validation, actual API/UI implementation, actual controlled reveal
implementation, and final release review still require direct evidence.
