# 1299 - SEC XBRL Operator Review Decision Rendered Submit Freeze

Milestone: `sec_xbrl_operator_review_decision_rendered_submit_freeze_v1`

Prior implementation: `next_milestone_plans/Layer3_planning_docs/1298-decision-status-api.md`

## Status

Planning/control-only Tier-1 freeze.

This document admits no rendered behavior by itself. It does not change `models.py`,
Alembic migrations, schema, durable persistence, backend API contracts, workflow-open
behavior, value reveal, default-on behavior, source acquisition, Arelle invocation,
delivery/export, raw runtime artifacts, authorization behavior, redaction posture, or
production-readiness claims.

## Authority

Canonical governance is
`next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md`.
This freeze is Tier 1 because it is documentation and planning control only.

Current repo authority before this freeze:

- `1295-decision-submit.md` selected a durable decision receipt before any rendered
  submit control.
- `1296-decision-receipt-impl.md` landed the decision receipt table and owner-service
  materializer.
- `1297-decision-submit-api.md` landed
  `POST /api/v1/layer3/sec-xbrl/operator-review/workflow/decision/submit`.
- `1298-decision-status-api.md` landed
  `POST /api/v1/layer3/sec-xbrl/operator-review/workflow/decision/status`.
- `backend/app/services/layer3_sec_xbrl_operator_review_workflow.py` validates existing
  workflow and decision authority before returning redacted projections.
- `backend/app/api/layer3.py` exposes the submit and status routes.
- `1293-ui-freeze.md` and `1294-rendered-status.md` establish the `/review/layer3`
  rendered-control pattern: the browser is not durable authority and stable DOM markers
  prove the admitted rendered surface.

## Selected Next Slice

The next implementation slice, after this freeze lands and current main is verified, may
add a browser-visible SEC XBRL operator-review decision submit/status panel under
`/review/layer3`.

Admitted future implementation surfaces:

- `backend/app/review_ui/static/layer3.html`: static panel/form anchors only if needed.
- `backend/app/review_ui/static/layer3.js`: submit/status request wiring and redacted
  receipt rendering.
- `backend/app/review_ui/static/layer3.css`: minimal existing-style layout only if
  needed.
- `e2e/layer3-workbench.spec.js`: headed and headless browser proof for the rendered
  decision submit/status flow.
- Planning/progress/proof docs for that implementation.

The future implementation must not add a backend route, model, migration, schema, durable
browser authority, workflow-open behavior, value reveal path, delivery/export path,
source acquisition path, Arelle invocation, default-on behavior, raw runtime artifact, or
production-readiness claim.

The future implementation should not change existing backend response flags only to
claim rendered UI. Existing API fields such as `rendered_ui_enabled=false` remain backend
non-goal evidence. The browser admission is proven by this freeze, the later rendered
implementation proof, and the required DOM markers below.

## Rendered Request Contract

The rendered submit form may submit only the already-admitted decision submit API fields:

- `client_request_id`
- `submit_mode=sec_xbrl_operator_review_decision_submit_v1`
- `operator_decision=submit_sec_xbrl_operator_review_decision`
- `review_decision`: one of `approved`, `changes_requested`, `rejected`, `blocked`
- `decision_reason_code`: one of `ready_for_next_freeze`, `needs_packet_revision`,
  `authority_gap`, `redaction_gap`, `operator_blocked`
- `sec_xbrl_operator_review_workflow_id`
- `workflow_basis_hash`
- `decision_notes`: optional and only sent when the operator supplies bounded notes

At least one of `sec_xbrl_operator_review_workflow_id` or `workflow_basis_hash` must be
supplied before submit is enabled. If both are supplied, the backend remains the
authority for whether they identify the same workflow row.

The rendered status form may submit only the already-admitted decision status API fields:

- `client_request_id`
- `status_mode=sec_xbrl_operator_review_decision_status_v1`
- `operator_decision=inspect_sec_xbrl_operator_review_decision_status`
- `sec_xbrl_operator_review_decision_id`
- `decision_basis_hash`

The browser must not pre-authorize, derive, repair, mutate, cache as durable authority,
or replay workflow/decision authority outside the server-owned APIs.

## Rendered Response Contract

The rendered surface may display only server-returned redacted fields from the submit and
status APIs, including:

- decision, workflow, packet, and projection identifiers/hashes returned by the server;
- bounded decision value, reason code, and recorded status;
- `decision_notes_present` and `decision_notes_hash`, never raw notes;
- decision summary counts and redaction policy;
- authority refs;
- permitted and blocked control vocabulary;
- negative invariants and next allowed actions.

The rendered response must not display, preserve, log, or store raw notes, raw values,
raw issuer identity, raw accessions, raw period dates, raw resolved fact authorities, SEC
URLs, local paths, operator contact fields, sidecar payloads, value-store payloads,
residual magnitudes, source-acquisition parameters, Arelle artifacts, delivery/export
payloads, or default-on controls.

Client-side validation may prevent obvious malformed input, but it is not authority. The
backend remains the authority for notes policy, raw-reference rejection, idempotency,
already-decided workflows, and selector coherence.

## Required Rendered Markers

The future panel/form must declare:

- `data-rendered-mode="rendered_sec_xbrl_operator_review_decision_submit_control"`
- `data-frontend-durable-authority="false"`
- `data-operator-decision-submit="true"` on the submit form or equivalent stable marker
- `data-read-only="true"` on the decision-status projection container or equivalent
  stable marker
- `data-value-reveal-enabled="false"`
- `data-delivery-export-enabled="false"`
- `data-source-acquisition-enabled="false"`
- `data-arelle-invocation-enabled="false"`
- `data-runtime-default-enabled="false"`

The rendered implementation must use stable selectors for the panel, submit form, status
form, submit control, status/receipt output, and error output so browser proof can assert
the exact authority and redaction posture.

## Blocked Controls

The rendered submit/status slice may admit only decision submit and decision status
inspection over the existing APIs. It must leave these unavailable:

- `open_operator_review_workflow`
- `reveal_values`
- `export_statement_packet`
- `deliver_statement_packet`
- `refresh_from_sec_source`
- `invoke_arelle`
- `edit_statement_packet`
- `change_runtime_default`
- any value-reveal, delivery/export, source-acquisition, Arelle, or default-on follow-up

No visible button, link, field, client action, API call, event-log message, or status
phrase may imply that those controls are live.

## Proof Required For Future Implementation

Minimum verification for the next implementation slice:

- focused operator-review workflow tests remain green:
  `python -m pytest ./backend/tests/test_sec_xbrl_operator_review_workflow.py -q`;
- full SEC XBRL suite remains green:
  `python -m pytest` over `backend/tests/test_sec_xbrl*.py`;
- static/browser tests prove the rendered submit form sends only admitted submit fields;
- static/browser tests prove the rendered status form sends only admitted status fields;
- headed and headless Playwright proof shows the panel can submit a decision over an
  existing workflow and inspect the resulting decision status without frontend durable
  authority;
- browser proof asserts the rendered markers listed above;
- browser proof asserts raw operator notes are not displayed, logged, persisted, or
  stored after submit; only `decision_notes_present` and `decision_notes_hash` may render;
- browser proof asserts no raw values, identities, accessions, period dates, SEC URLs,
  local paths, operator contact fields, residual magnitudes, source acquisition fields,
  Arelle controls, delivery/export controls, value-reveal controls, or default-on
  controls render;
- browser proof asserts missing authority, backend notes-policy errors, already-decided
  workflow errors, and raw-reference rejection render as blocked/error states without
  partial frontend state becoming authority;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- `node --check ./backend/app/review_ui/static/layer3.js` if JavaScript is touched;
- py_compile on any touched Python files;
- JSON parse for changed manifests/reports;
- redaction scan across changed committed SEC XBRL reports or proof artifacts;
- `git diff --check`.

## Follow-On After Rendered Decision Submit

Only after the rendered decision submit/status panel lands and current-main verification
is clean should the project select the separate value-reveal authority lane:

`sec_xbrl_value_reveal_authority_design_v1`

That later lane must address operator authentication/authorization, explicit approved
decision eligibility, value-reveal authority, auditability, containment/rollback, and
default-off posture before any revealed-value or default-on behavior is admitted.
