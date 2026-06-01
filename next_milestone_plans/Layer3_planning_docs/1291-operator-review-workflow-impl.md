# 1291 - SEC XBRL Operator Review Workflow Implementation

Milestone:

`sec_xbrl_operator_review_workflow_control_envelope_v1`

## Scope

This Tier-2 implementation lands the first code-bearing slice selected by
`1290-operator-review-workflow.md`: additive redacted operator-review workflow control
envelope schema plus a deterministic owner service.

Files in this slice:

- `backend/app/models/models.py`
- `backend/app/models/__init__.py`
- `backend/alembic/versions/0040_layer3_sec_xbrl_operator_review_workflow.py`
- `backend/app/services/layer3_sec_xbrl_operator_review_workflow.py`
- `backend/tests/test_sec_xbrl_operator_review_workflow.py`
- `next_milestone_plans/Layer3_planning_docs/1291-operator-review-workflow-impl.md`
- progress/proof tracking docs

## Runtime Contract

The owner service accepts an existing persisted redacted statement-packet set and writes
one `l3_sec_xbrl_operator_review_workflow` row. The row is a server-owned control
envelope that binds the packet id, packet basis hash, source projection basis hash,
review-ready counts, redaction policy, and fixed allowed/blocked control vocabulary.

The service computes a stable `workflow_basis_hash`, is idempotent on
`client_request_id` and `workflow_basis_hash`, rejects missing, empty, not-ready, or
non-redacted packet sets, and scans copied JSON for raw values, raw resolved-fact
authority fields, raw accessions, raw issuer identity keys, operator contact fields,
raw period dates, SEC URLs, local paths, and residual magnitude fields before writing.

The service returns explicit non-action flags:

- `runtime_default_enabled=false`
- `value_reveal_performed=false`
- `source_acquisition_performed=false`
- `arelle_invoked=false`
- `delivery_export_enabled=false`
- `api_route_enabled=false`
- `rendered_ui_enabled=false`
- `operator_review_decision_recorded=false`

## Tier-2 Surfaces

Touched Tier-2 surfaces:

- `models.py` ORM schema additions;
- Alembic migration `0040_layer3_sec_xbrl_operator_review_workflow`;
- deterministic persistence service over persisted redacted statement-packet authority.

Why necessary:

The next SEC XBRL Layer 3 workflow needs server-owned review authority and control
vocabulary before API/UI status, rendered review, submitted decisions, delivery/export,
value reveal, or default-on behavior can be considered without bypassing persisted
statement-packet provenance.

## Containment

This implementation does not admit:

- API routes, rendered UI, browser controls, or operator-submitted review decisions;
- delivery/export, connector dispatch, provider/public URLs, or handoff;
- source acquisition, live SEC network, or Arelle invocation;
- value reveal or persisted raw values;
- raw issuer identity, raw accessions, raw period dates, raw resolved fact authorities,
  SEC URLs, local paths, raw sidecar payloads, value-store payloads, operator contact
  fields, or residual magnitude rows;
- default-on behavior;
- production-readiness or final financial-statement semantics claims.

Rollback/containment notes:

- migration downgrade drops only `l3_sec_xbrl_operator_review_workflow` plus its
  indexes;
- tests use isolated SQLite runtime state;
- invalid packet readiness, redaction, local path, residual magnitude, or missing
  packet input leaves no partial workflow row;
- replay of the same request or workflow basis does not duplicate rows;
- statement-packet persistence rows are read as authority inputs and are not mutated.

## Proof

Focused test:

`python -m pytest ./backend/tests/test_sec_xbrl_operator_review_workflow.py -q`

Result: `10 passed`.

Broader verification and CI state are recorded in the PR that lands this slice.

## Next Posture

After this implementation lands and is verified on current main, the next design lane is
`sec_xbrl_operator_review_workflow_status_api_v1`.

That lane may expose read-only API/status over the persisted workflow envelope. It must
not reveal values, add rendered UI, submit operator review decisions, deliver/export
packets, invoke SEC/Arelle/source acquisition, change defaults, or claim production
readiness without a separate freeze and proof.
