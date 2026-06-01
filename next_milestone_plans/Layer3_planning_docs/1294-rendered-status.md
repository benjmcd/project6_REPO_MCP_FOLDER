# 1294 - SEC XBRL Operator Review Rendered Status

Milestone:

`sec_xbrl_operator_review_workflow_rendered_status_v1`

## Status

Tier-1 read-only rendered status implementation.

This slice adds a `/review/layer3` SEC XBRL operator-review workflow status panel
over the already-landed status API:

`POST /api/v1/layer3/sec-xbrl/operator-review/workflow/status`

It does not add or change `models.py`, Alembic migrations, schema, durable
persistence, backend API contracts, workflow-open behavior, submitted operator
review decisions, delivery/export, value reveal, default-on behavior, source
acquisition, SEC network execution, Arelle invocation, raw runtime artifacts,
authorization behavior, redaction posture, or production-readiness claims.

## Authority Boundary

Canonical governance remains
`next_milestone_plans/Layer3_planning_docs/SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md`.
The immediate freeze authority for this rendered slice is
`next_milestone_plans/Layer3_planning_docs/1293-ui-freeze.md`.

The browser is not durable authority. It only submits:

- `client_request_id`
- `status_mode=sec_xbrl_operator_review_workflow_status_v1`
- `operator_decision=inspect_sec_xbrl_operator_review_workflow_status`
- `sec_xbrl_operator_review_workflow_id`
- `workflow_basis_hash`

At least one workflow authority identifier must be supplied before submit is enabled.
The backend remains authority for whether the workflow id and basis hash identify
existing coherent workflow authority.

## Implementation

Touched implementation surfaces:

- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.js`
- `e2e/layer3-workbench.spec.js`

Rendered markers:

- `data-rendered-mode="rendered_sec_xbrl_operator_review_workflow_status_control"`
- `data-frontend-durable-authority="false"`
- `data-read-only="true"`

The rendered status output displays only server-returned redacted identifiers,
hashes, counts, readiness state, permitted read-only controls, blocked controls,
authority refs, review summary, negative invariants, and next allowed actions.

Blocked rendered controls remain unavailable:

- `submit_operator_review_decision`
- `open_operator_review_workflow`
- `reveal_values`
- `export_statement_packet`
- `deliver_statement_packet`
- `refresh_from_sec_source`
- `invoke_arelle`
- `edit_statement_packet`
- `change_runtime_default`

## Verification

Branch-local verification already run for the implemented slice:

- `node --check ./backend/app/review_ui/static/layer3.js` -> passed
- `npm run test:e2e -- --grep "SEC XBRL operator-review workflow status"` -> 1 passed
- `npm run test:e2e:headed -- --grep "SEC XBRL operator-review workflow status"` -> 1 passed
- `python -m pytest ./backend/tests/test_sec_xbrl_operator_review_workflow.py -q` -> 17 passed
- `$files = Get-ChildItem ./backend/tests/test_sec_xbrl*.py | ForEach-Object { $_.FullName }; python -m pytest $files -q` -> 237 passed

Remaining closeout verification is recorded in the PR and final turn evidence:

- `python ./tools/l3-target-selection-validate.py --expect frozen`
- `python ./tools/l3-progress-check.py`
- JSON parse for changed manifests
- redaction/residual scans across the diff
- `git diff --check`

## Follow-On

The next bounded lane after merge and current-main verification is:

`sec_xbrl_operator_review_decision_submit_design_v1`

That later lane is separate and must decide durable operator decision identity,
idempotency, rollback/containment, admitted controls, and redaction preservation.
It must not reveal values, change defaults, export/deliver packets, invoke SEC/Arelle
source acquisition, or claim production readiness without a separate freeze and proof.
