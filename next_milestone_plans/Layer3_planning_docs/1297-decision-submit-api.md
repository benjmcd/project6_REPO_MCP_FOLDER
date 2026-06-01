# 1297 - SEC XBRL Operator Review Decision Submit API Freeze

Milestone: `sec_xbrl_operator_review_decision_submit_api_freeze_v1`

Prior implementation: `next_milestone_plans/Layer3_planning_docs/1296-decision-receipt-impl.md`

## Status

Tier-2 risk-assessed API-contract freeze plus branch-local route implementation.

This document freezes the next route-level submission boundary over the existing
`record_redacted_operator_review_decision` owner service. The implementation pass adds
only the frozen FastAPI wrapper and focused API proof. It does not change schema, widen
persistence beyond the existing decision receipt service, add UI, reveal values,
export/deliver packets, invoke SEC/Arelle/source acquisition, change defaults, or claim
production readiness.

## Route Boundary

Frozen and implemented route:

`POST /api/v1/layer3/sec-xbrl/operator-review/workflow/decision/submit`

The route must:

- require the existing FastAPI database dependency;
- use `extra="forbid"` on the request model;
- call only `record_redacted_operator_review_decision`;
- pass only the bounded request fields listed below to the owner service;
- use the existing SEC XBRL operator-review workflow error mapper;
- return a route projection that marks the submit API route as enabled while preserving
  the owner service's non-goal flags for rendered UI, value reveal, delivery/export,
  source acquisition, Arelle invocation, default-on behavior, and production readiness.

## Request Contract

Required:

- `client_request_id`: non-empty string.
- `submit_mode`: literal `sec_xbrl_operator_review_decision_submit_v1`.
- `operator_decision`: literal `submit_sec_xbrl_operator_review_decision`.
- `review_decision`: one of `approved`, `changes_requested`, `rejected`, `blocked`.
- `decision_reason_code`: one of `ready_for_next_freeze`, `needs_packet_revision`,
  `authority_gap`, `redaction_gap`, `operator_blocked`.

Authority selector:

- `sec_xbrl_operator_review_workflow_id`: optional non-empty string.
- `workflow_basis_hash`: optional 64-character hash.

At least one authority selector must be supplied; if both are supplied, both must match
the same existing workflow row through the owner service.

Optional:

- `decision_notes`: optional string. The owner service must continue to require notes
  for `changes_requested`, `rejected`, and `blocked`, hash accepted notes, and never
  persist raw notes.

The request must not admit caller-supplied raw values, raw issuer identity, raw
accessions, raw period dates, SEC URLs, local paths, raw resolved-fact authority,
operator contact fields, source-acquisition fields, Arelle fields, delivery/export
fields, default-on fields, rendered-control fields, or residual magnitude fields.

## Response Contract

The route returns the owner-service decision receipt projection plus these
API-specific flags:

- `decision_submit_api_route_enabled=true`;
- `rendered_ui_enabled=false`;
- `workflow_open_api_route_enabled=false`;
- `value_reveal_performed=false`;
- `delivery_export_enabled=false`;
- `source_acquisition_performed=false`;
- `arelle_invoked=false`;
- `runtime_default_enabled=false`;
- `production_readiness_claimed=false`.

The response must not include raw notes, raw values, raw issuer identity, accessions,
period dates, SEC URLs, local paths, raw resolved-fact authority, operator contact
fields, residual magnitudes, source-acquisition artifacts, Arelle artifacts, delivery
payloads, or rendered-control state.

## Implementation Boundary

This implementation slice may touch:

- `backend/app/api/layer3.py`;
- `backend/tests/test_sec_xbrl_operator_review_workflow.py`;
- this planning doc and Layer 3 progress/proof manifests.

It must not touch:

- `backend/app/models/models.py`;
- Alembic migrations;
- schema or durable persistence beyond using the existing decision receipt service;
- rendered UI;
- browser-visible submit controls;
- workflow-open route;
- value reveal;
- delivery/export;
- source acquisition;
- live SEC network;
- Arelle subprocess invocation;
- default-on behavior;
- raw runtime artifacts;
- production-readiness or final financial-statement semantics claims.

## Required Implementation Proof

The implementation PR must prove:

- successful submit over an existing workflow records one decision receipt;
- request model rejects extra fields;
- missing authority fails closed;
- missing notes for non-approved decisions fails closed;
- raw note contact/value strings fail closed through the owner service;
- same `client_request_id` and basis replays idempotently;
- second decision for the same workflow fails closed;
- API response contains no raw notes, values, accessions, period dates, SEC URLs, local
  paths, identities, operator contacts, residual magnitudes, source-acquisition fields,
  Arelle controls, enabled delivery/export controls, enabled value-reveal controls, or
  default-on controls; blocked-control evidence may still name blocked controls;
- no workflow, statement-packet, or projection row is mutated by the route.

Minimum verification:

- focused operator-review workflow tests;
- full `backend/tests/test_sec_xbrl*.py` suite;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- py_compile on touched Python files;
- JSON validation for changed manifests;
- redaction/residual scans over changed SEC XBRL proof artifacts if any are changed;
- `git diff --check`.

## Implementation Result

Branch-local implementation posture:

- `backend/app/api/layer3.py` adds
  `POST /api/v1/layer3/sec-xbrl/operator-review/workflow/decision/submit`.
- The request model uses `extra="forbid"` and admits only the frozen submit mode,
  operator decision, review decision, reason code, optional workflow selectors, and
  optional notes.
- The route calls only `record_redacted_operator_review_decision`, uses the existing
  SEC XBRL operator-review workflow error mapper, and returns the standard API envelope
  plus the owner-service decision receipt projection.
- The response sets `decision_submit_api_route_enabled=true` while preserving
  `api_route_enabled=false` from the owner-service receipt and keeping rendered UI,
  workflow-open API, value reveal, delivery/export, source acquisition, Arelle,
  runtime-default, and production-readiness flags false.
- Focused API proof covers successful receipt creation, extra-field rejection, missing
  authority failure, non-approved missing-notes failure, raw note/contact/value-string
  rejection, idempotent replay, second-decision rejection, response redaction, and
  workflow/statement-packet/projection non-mutation.
- Branch-local test evidence: focused operator-review workflow tests returned
  `34 passed, 3 warnings`; full SEC XBRL suite returned `254 passed, 4 warnings`.

## Next Posture

After this route implementation lands and current-main verification is clean, the next
bounded posture is:

`sec_xbrl_operator_review_decision_status_api_v1`
