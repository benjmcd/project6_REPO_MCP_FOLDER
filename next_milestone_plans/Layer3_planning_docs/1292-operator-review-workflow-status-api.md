# 1292 - SEC XBRL Operator Review Workflow Status API

Milestone:

`sec_xbrl_operator_review_workflow_status_api_v1`

## Scope

This Tier-1 read-only API/status slice exposes server-owned status over the
already-persisted `l3_sec_xbrl_operator_review_workflow` control envelope.

Files in this slice:

- `backend/app/services/layer3_sec_xbrl_operator_review_workflow.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_sec_xbrl_operator_review_workflow.py`
- `next_milestone_plans/Layer3_planning_docs/1292-operator-review-workflow-status-api.md`
- progress/proof tracking docs

## Runtime Contract

The route is:

`POST /api/v1/layer3/sec-xbrl/operator-review/workflow/status`

The request admits only:

- `client_request_id`
- `status_mode=sec_xbrl_operator_review_workflow_status_v1`
- `operator_decision=inspect_sec_xbrl_operator_review_workflow_status`
- `sec_xbrl_operator_review_workflow_id`
- `workflow_basis_hash`

At least one of `sec_xbrl_operator_review_workflow_id` or `workflow_basis_hash`
is required. If both are present, they must identify the same existing
server-owned workflow row. The response is a read-only redacted projection of
the workflow envelope and includes the governed allowed/blocked control
vocabulary, redacted authority refs, review counts, readiness state, and
negative invariants.

The status service revalidates the persisted workflow row before returning it.
It fails closed on missing authority, mismatched id/hash authority, invalid
schema/control/status/redaction vocabulary, non-positive row counts, non-ready
state, mutated permitted/blocked control vocabularies, raw values, raw resolved
fact authority, raw identity/accession/date/path/URL/operator-contact fields,
or residual magnitudes in copied JSON.

## Tier Classification

This slice is Tier 1 under the softened SEC XBRL merge policy: additive
read-only service/API/test/docs over existing persisted authority, with no
`models.py`, Alembic migration, schema change, durable persistence expansion,
value reveal, default-on behavior, or redaction-posture change.

## Containment

This implementation does not admit:

- opening workflows through API;
- rendered UI, browser controls, or operator-submitted review decisions;
- delivery/export, connector dispatch, provider/public URLs, or handoff;
- source acquisition, live SEC network, or Arelle invocation;
- value reveal or persisted raw values;
- raw issuer identity, raw accessions, raw period dates, raw resolved fact
  authorities, SEC URLs, local paths, raw sidecar payloads, value-store payloads,
  operator contact fields, or residual magnitude rows;
- default-on behavior;
- production-readiness or final financial-statement semantics claims.

## Proof

Focused test:

`python -m pytest ./backend/tests/test_sec_xbrl_operator_review_workflow.py -q`

Result: `15 passed`.

The focused proof covers direct service status projection, fail-closed missing
authority, fail-closed tampered raw status JSON, API route success, and API
route missing-authority failure, in addition to the existing workflow envelope
materialization coverage.

## Next Posture

After this slice lands and is verified on current main, the next design lane is
`sec_xbrl_operator_review_workflow_rendered_read_only_ui_freeze_v1`.

That lane may freeze a rendered read-only `/review/layer3` status panel over the
status API. It must not submit operator decisions, open workflows, reveal values,
deliver/export packets, invoke SEC/Arelle/source acquisition, change defaults, or
claim production readiness without a separate freeze and proof.
