# 1293 - SEC XBRL Operator Review Rendered Read-Only UI Freeze

Milestone:

`sec_xbrl_operator_review_workflow_rendered_read_only_ui_freeze_v1`

## Status

Planning/control-only Tier-1 freeze.

This document admits no rendered behavior by itself. It does not change
`models.py`, Alembic migrations, schema, durable persistence, API contracts,
operator-submitted decisions, value reveal, default-on behavior, source acquisition,
Arelle invocation, delivery/export, raw runtime artifacts, authorization behavior, or
production-readiness claims.

## Authority

Canonical governance is `SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md`. This is Tier 1
because it is documentation and planning control only. A later rendered read-only UI
implementation may remain Tier 1 only if it consumes the already-landed status API
without adding persistence, schema, value reveal, default-on behavior, redaction-posture
changes, source acquisition, Arelle, delivery/export, or submitted operator decisions.

Current repo authority before this freeze:

- `1290-operator-review-workflow.md` names a later rendered `/review/layer3` surface
  over server-returned redacted workflow status.
- `1291-operator-review-workflow-impl.md` landed the durable server-owned workflow
  control envelope.
- `1292-operator-review-workflow-status-api.md` landed the read-only status API:
  `POST /api/v1/layer3/sec-xbrl/operator-review/workflow/status`.
- `backend/app/services/layer3_sec_xbrl_operator_review_workflow.py` revalidates the
  persisted workflow row before returning status.
- `backend/app/api/layer3.py` exposes the status route and response model.
- Existing `/review/layer3` patterns use static rendered controls with
  `data-frontend-durable-authority="false"` and prove headed/headless browser behavior
  when rendered workflow behavior changes.

## Selected Next Slice

The next implementation slice, after this freeze lands and current main is verified,
may add a read-only SEC XBRL operator-review workflow status panel under
`/review/layer3`.

Admitted future implementation surfaces:

- `backend/app/review_ui/static/layer3.html`: static panel/form anchor only if needed.
- `backend/app/review_ui/static/layer3.js`: read-only status request wiring and
  redacted status rendering.
- `backend/app/review_ui/static/layer3.css`: minimal existing-style layout only if
  needed.
- `e2e/layer3-workbench.spec.js`: headed and headless browser proof for the rendered
  status flow.
- Planning/progress/proof docs for that implementation.

The rendered slice must not add a new route, new model, migration, durable browser
authority, workflow-open API, workflow decision submit API, delivery/export path, value
reveal path, source acquisition path, or Arelle invocation.

## Rendered Contract

The rendered surface may submit only the already-admitted status API request fields:

- `client_request_id`
- `status_mode=sec_xbrl_operator_review_workflow_status_v1`
- `operator_decision=inspect_sec_xbrl_operator_review_workflow_status`
- `sec_xbrl_operator_review_workflow_id`
- `workflow_basis_hash`

At least one of `sec_xbrl_operator_review_workflow_id` or `workflow_basis_hash` must be
supplied by the operator. If both are supplied, the backend remains the authority for
whether they identify the same workflow row. The browser must not pre-authorize,
derive, mutate, cache as durable authority, or repair workflow authority.

The rendered response may display only server-returned redacted status fields from the
status API, including:

- workflow and packet identifiers/hashes returned by the server;
- review counts and readiness state;
- permitted and blocked control vocabulary;
- redacted authority refs;
- negative invariants and next allowed actions.

The rendered response must not display or preserve raw values, raw issuer identity, raw
accessions, raw period dates, raw resolved fact authorities, SEC URLs, local paths,
operator contact fields, sidecar payloads, value-store payloads, residual magnitudes,
or source-acquisition parameters.

## Required Rendered Markers

The future panel/form must declare:

- `data-rendered-mode="rendered_sec_xbrl_operator_review_workflow_status_control"`
- `data-frontend-durable-authority="false"`
- `data-read-only="true"` on the status projection container or equivalent stable
  read-only marker.

The rendered implementation must use stable selectors for the panel, form, submit
control, status output, and error output so browser proof can assert the exact authority
and redaction posture.

## Blocked Controls

The rendered slice must leave these unavailable:

- `submit_operator_review_decision`
- `open_operator_review_workflow`
- `reveal_values`
- `export_statement_packet`
- `deliver_statement_packet`
- `refresh_from_sec_source`
- `invoke_arelle`
- `edit_statement_packet`
- `change_runtime_default`

No visible button, link, field, client action, API call, or status phrase may imply that
those controls are live.

## Proof Required For Future Implementation

Minimum verification for the next implementation slice:

- focused backend status API test remains green:
  `python -m pytest ./backend/tests/test_sec_xbrl_operator_review_workflow.py -q`;
- full SEC XBRL suite remains green:
  `python -m pytest` over `backend/tests/test_sec_xbrl*.py`;
- static/browser tests prove the rendered form submits only admitted fields;
- headed and headless Playwright proof shows the panel can inspect an existing workflow
  status without mutating state or relying on frontend durable authority;
- browser proof asserts the rendered markers listed above;
- browser proof asserts no raw values, identities, accessions, period dates, SEC URLs,
  local paths, operator contact fields, residual magnitudes, source acquisition fields,
  Arelle controls, delivery/export controls, or decision-submit controls render;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- py_compile on any touched Python files;
- JSON parse for changed manifests/reports;
- redaction scan across changed committed SEC XBRL reports or proof artifacts;
- `git diff --check`.

## Follow-On After Rendered Read-Only UI

Only after the rendered read-only status panel lands and is verified on current main
should the project select a separate operator-review decision design lane:

`sec_xbrl_operator_review_decision_submit_design_v1`

That later lane must decide whether submitted operator decisions are durable state,
which controls are admitted, how decision identity and idempotency work, what rollback
or containment is required, and how redaction is preserved. It must not reveal values,
change defaults, export/deliver packets, invoke SEC/Arelle/source acquisition, or claim
production readiness without a separate freeze and proof.
