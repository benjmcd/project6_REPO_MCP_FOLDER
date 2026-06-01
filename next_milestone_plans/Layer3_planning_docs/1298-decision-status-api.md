# 1298 - SEC XBRL Operator Review Decision Status API

Milestone: `sec_xbrl_operator_review_decision_status_api_v1`

Prior implementation: `next_milestone_plans/Layer3_planning_docs/1297-decision-submit-api.md`

## Status

Tier-2 risk-assessed read-only API implementation plus fail-closed residual-alias guard
hardening.

This pass adds a read-only decision-status projection over the existing
`l3_sec_xbrl_operator_review_decision` receipt authority and exposes it through a bounded
FastAPI wrapper. It also strengthens the existing operator-review redaction guard so
previously reported residual/magnitude aliases (`mean`, `median`, `max`, `ratio`, plus
closely related aggregate aliases) fail closed before any exposed/persisted public JSON
surface can project them.

The pass does not change schema, migrations, durable persistence shape, rendered UI,
operator workflow opening, value reveal, delivery/export, source acquisition, Arelle
execution, runtime defaults, raw runtime artifacts, or production-readiness posture.

## Route Boundary

Implemented route:

`POST /api/v1/layer3/sec-xbrl/operator-review/workflow/decision/status`

The route:

- requires the existing FastAPI database dependency;
- uses `extra="forbid"` on the request model;
- calls only `inspect_redacted_operator_review_decision_status`;
- passes only bounded request fields and existing decision authority selectors;
- uses the existing SEC XBRL operator-review workflow error mapper;
- returns a read-only status projection with non-goal flags preserved as false.

## Request Contract

Required:

- `client_request_id`: non-empty string.
- `status_mode`: literal `sec_xbrl_operator_review_decision_status_v1`.
- `operator_decision`: literal `inspect_sec_xbrl_operator_review_decision_status`.

Authority selector:

- `sec_xbrl_operator_review_decision_id`: optional non-empty string.
- `decision_basis_hash`: optional 64-character hash.

At least one authority selector must be supplied; if both are supplied, both must match
the same existing decision row.

The request must not admit caller-supplied raw values, raw issuer identity, raw
accessions, raw period dates, SEC URLs, local paths, raw resolved-fact authority,
operator contact fields, source-acquisition fields, Arelle fields, delivery/export
fields, default-on fields, rendered-control fields, raw notes, or residual magnitude
fields.

## Response Contract

The route returns the standard API envelope plus a server-owned decision-status
projection:

- `decision_status_api_route_enabled=true`;
- `read_only_status_surface=true`;
- `durable_decision_authority_used=true`;
- `operator_review_decision_recorded=true`;
- `decision_submit_api_route_enabled=false`;
- `workflow_open_api_route_enabled=false`;
- `rendered_ui_enabled=false`;
- `runtime_default_enabled=false`;
- `value_reveal_performed=false`;
- `delivery_export_enabled=false`;
- `source_acquisition_performed=false`;
- `arelle_invoked=false`.

The response must not include raw notes, raw values, raw issuer identity, accessions,
period dates, SEC URLs, local paths, raw resolved-fact authority, operator contact
fields, residual magnitudes, source-acquisition artifacts, Arelle artifacts, delivery
payloads, or rendered-control state.

## Authority Validation

Before projection, the owner service validates:

- the decision row uses the governed decision schema, mode, status, redaction policy,
  decision value, and reason-code vocabulary;
- the related workflow row still validates through the existing workflow-status guard;
- decision workflow/source/packet hashes match the workflow authority;
- decision summary JSON is allowlisted, raw-reference scanned, and matches the persisted
  decision plus workflow counts;
- decision authority refs JSON is allowlisted, raw-reference scanned, and matches the
  persisted decision plus workflow packet id;
- post-decision permitted and blocked controls match the governed vocabularies;
- notes are never exposed raw, and notes hashes are present only when notes were accepted.

## Risk Assessment

Tier-2 surfaces touched:

- API route implementation in `backend/app/api/layer3.py`.
- Service status projection and stricter redaction guard in
  `backend/app/services/layer3_sec_xbrl_operator_review_workflow.py`.

Why self-verification is adequate for this pass:

- the route is read-only and records no new decision rows;
- the redaction guard change is stricter and fail-closed;
- focused tests cover success, missing authority, selector mismatch, extra-field
  rejection, tampered receipt JSON, residual-alias rejection, notes-hash validation,
  controlled-vocabulary validation, response redaction, and non-mutation;
- full SEC XBRL tests and Layer 3 validators are required before merge.

Follow-up would be forced by any failed required check, raw value/identity/path leak,
unresolved critical review finding, default-on/value-reveal drift, schema/persistence
drift, or unclear authority boundary.

## Implementation Boundary

This implementation slice may touch:

- `backend/app/services/layer3_sec_xbrl_operator_review_workflow.py`;
- `backend/app/api/layer3.py`;
- `backend/tests/test_sec_xbrl_operator_review_workflow.py`;
- this planning doc and Layer 3 progress/proof manifests.

It must not touch:

- `backend/app/models/models.py`;
- Alembic migrations;
- schema or durable persistence shape;
- rendered UI;
- browser-visible submit/status controls;
- workflow-open behavior;
- value reveal;
- delivery/export;
- source acquisition;
- live SEC network;
- Arelle subprocess invocation;
- default-on behavior;
- raw runtime artifacts;
- production-readiness or final financial-statement semantics claims.

## Implementation Result

Branch-local implementation posture:

- `backend/app/services/layer3_sec_xbrl_operator_review_workflow.py` adds
  `inspect_redacted_operator_review_decision_status`.
- `backend/app/api/layer3.py` adds
  `POST /api/v1/layer3/sec-xbrl/operator-review/workflow/decision/status`.
- The request model uses `extra="forbid"` and admits only the frozen status mode,
  operator decision, and decision authority selectors.
- The response returns a read-only status projection over the existing decision receipt;
  rendered UI, workflow-open API, value reveal, delivery/export, source acquisition,
  Arelle, runtime-default, and production-readiness flags remain false.
- The residual magnitude guard now rejects `mean`, `median`, `max`, `ratio`, `stddev`,
  `sum`, `total`, and `quartile` in addition to the earlier residual key set.
- Focused branch-local proof returned `45 passed, 3 warnings`.
- Full SEC XBRL suite returned `265 passed, 4 warnings`; target-selection frozen check,
  progress check, py_compile, JSON validation, SEC XBRL report redaction scan, and
  residual magnitude scan, and `git diff --check` passed. The residual scan excluded exact-zero identity
  residual fields and residual count/boolean evidence fields already present in
  unchanged committed reports.

## Next Posture

After this route implementation lands and current-main verification is clean, the next
bounded posture is:

`sec_xbrl_operator_review_decision_rendered_submit_freeze_v1`
