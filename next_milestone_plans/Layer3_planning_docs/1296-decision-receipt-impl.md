# 1296 - SEC XBRL Operator Review Decision Receipt Implementation

Milestone: `sec_xbrl_operator_review_decision_receipt_v1_tier2_risk_assessed_implementation`

Prior design: `next_milestone_plans/Layer3_planning_docs/1295-decision-submit.md`

## Status

Tier-2 risk-assessed schema/materializer implementation.

This slice implements the first code-bearing boundary selected in doc 1295: a durable,
redacted operator-review decision receipt over existing server-owned
`l3_sec_xbrl_operator_review_workflow` authority.

## Tier-2 Surfaces

- `backend/app/models/models.py`: adds `L3SecXbrlOperatorReviewDecision` and the
  relationship from `L3SecXbrlOperatorReviewWorkflow`.
- `backend/app/models/__init__.py`: exports the decision receipt model.
- `backend/alembic/versions/0042_layer3_sec_xbrl_operator_review_decision.py`: adds
  one additive decision receipt table, constraints, indexes, and downgrade cleanup.
- `backend/app/services/layer3_sec_xbrl_operator_review_workflow.py`: adds
  `record_redacted_operator_review_decision` as the owner-service materializer.
- `backend/tests/test_sec_xbrl_operator_review_workflow.py`: covers decision receipt
  persistence, idempotency, conflict handling, raw-reference rejection, workflow
  authority validation, non-mutation, metadata registration, and migration declaration.

The Tier-2 surface is necessary because the operator decision must become durable
authority before any later value-reveal, delivery/export, rendered submission, or
default-on decision can be considered without bypassing workflow provenance.

## Runtime Contract

`record_redacted_operator_review_decision` requires:

- an existing workflow id or workflow basis hash;
- a bounded `review_decision`;
- a bounded `decision_reason_code`;
- notes for non-approved decisions.

The materializer:

- validates the referenced workflow using the existing workflow status invariants;
- requires the pre-decision workflow to have `submit_operator_review_decision`
  explicitly blocked;
- writes one immutable decision receipt per workflow;
- persists only redacted counts, basis hashes, bounded enums, controls, and authority refs;
- stores `decision_notes_hash` only, never raw decision notes;
- rejects raw note contacts and raw decimal strings before persistence;
- rejects replay conflicts for a reused `client_request_id` with a different basis;
- replays only the identical `client_request_id` and `decision_basis_hash`; same-basis
  replay under a different request id fails closed until an alias policy is frozen;
- leaves workflow, statement-packet, and projection authority rows unmutated.

## Containment

This implementation does not add or enable:

- API route;
- rendered UI or browser-visible decision submit control;
- workflow-open route;
- value reveal;
- delivery/export;
- default-on behavior;
- source acquisition;
- live SEC network execution;
- Arelle subprocess invocation;
- raw runtime artifacts;
- raw values, issuer identity, accessions, period dates, SEC URLs, local paths,
  resolved-fact authority, operator contacts, or residual magnitudes;
- production-readiness or final financial-statement semantics claims.

## Rollback And Containment Notes

Rollback is bounded to dropping the additive decision receipt indexes and table through
the 0042 downgrade. Existing workflow, statement-packet, and projection tables are not
mutated by decision receipt creation. Service-level exceptions roll back the transaction
and leave no partial decision rows.

## Verification

Focused verification:

```text
python -m pytest ./backend/tests/test_sec_xbrl_operator_review_workflow.py -q
```

Expected result for this slice: `27 passed, 3 warnings`.

Observed branch closeout verification:

- full SEC XBRL test glob: `247 passed, 4 warnings`;
- target-selection frozen check: `PASS`;
- progress check: `PASS`;
- py_compile on touched Python files: `PASS`;
- JSON validation over SEC XBRL reports and Layer 3 manifests: `PASS`;
- SEC XBRL report redaction scan: `41 SEC XBRL reports` passed;
- residual magnitude scan: `41 SEC XBRL reports` passed with count fields and
  evidence-only tolerance booleans excluded;
- `git diff --check`: `PASS`.

## Next Posture

After merge and current-main verification, the next bounded posture is:

`sec_xbrl_operator_review_decision_submit_api_v1`

That future lane should be route-level submission over the owner service. It should still
exclude rendered decision controls, value reveal, delivery/export, source acquisition,
Arelle invocation, default-on behavior, and production-readiness claims unless separately
authorized and reclassified.
