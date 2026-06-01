# 1300 - SEC XBRL Operator Review Decision Rendered Submit

Milestone: `sec_xbrl_operator_review_decision_rendered_submit_v1`

Prior control freeze: `next_milestone_plans/Layer3_planning_docs/1299-decision-rendered-submit-freeze.md`

Base authority: `project6-origin/main` at `c6e41498f44d2eb4ce030571f6840f26a340a419`

## Status

Implemented as a bounded rendered UI slice over already-admitted SEC XBRL operator-review
decision submit/status APIs.

Tier classification: Tier 1 rendered-control implementation. This pass changes only the
Layer 3 review UI static surface, Playwright proof, and planning/progress/proof docs. It
does not change `models.py`, Alembic migrations, schema, durable persistence, backend API
contracts, workflow-open behavior, value reveal, default-on behavior, source acquisition,
Arelle invocation, delivery/export, raw runtime artifacts, authorization behavior,
redaction posture, product-flow docs, or production-readiness claims.

## Implemented Surface

The `/review/layer3` page now renders
`#sec-xbrl-operator-review-decision-submit-panel` as a sibling to the existing
SEC XBRL operator-review workflow status panel.

Rendered markers:

- `data-rendered-mode="rendered_sec_xbrl_operator_review_decision_submit_control"`
- `data-frontend-durable-authority="false"`
- `data-operator-decision-submit="true"`
- `data-value-reveal-enabled="false"`
- `data-delivery-export-enabled="false"`
- `data-source-acquisition-enabled="false"`
- `data-arelle-invocation-enabled="false"`
- `data-runtime-default-enabled="false"`

The submit form sends only:

- `client_request_id`
- `submit_mode=sec_xbrl_operator_review_decision_submit_v1`
- `operator_decision=submit_sec_xbrl_operator_review_decision`
- `review_decision`
- `decision_reason_code`
- `sec_xbrl_operator_review_workflow_id`
- `workflow_basis_hash`
- optional `decision_notes`

The status form sends only:

- `client_request_id`
- `status_mode=sec_xbrl_operator_review_decision_status_v1`
- `operator_decision=inspect_sec_xbrl_operator_review_decision_status`
- `sec_xbrl_operator_review_decision_id`
- `decision_basis_hash`

## Redaction And Authority Boundaries

The browser remains non-authoritative. Client-side checks only disable obviously
incomplete requests. The server remains the authority for workflow existence, workflow
basis coherence, notes policy, idempotency, already-decided workflow handling, decision
receipt creation, and decision status projection.

Raw operator notes are allowed only as bounded submit input. After submit or submit
failure, the rendered form clears the note field. The rendered receipt/status surfaces
display `decision_notes_present` and `decision_notes_hash`, never raw notes.

The rendered panel does not create, display, or enable:

- workflow-open controls;
- value-reveal controls or revealed values;
- delivery/export controls;
- source-acquisition controls;
- Arelle invocation controls;
- packet mutation controls;
- default-on controls;
- frontend durable authority;
- production-readiness claims.

Existing backend response fields such as `rendered_ui_enabled=false` remain backend
non-goal evidence. Browser admission is proven by the planning freeze, this implementation
record, DOM markers, request allowlists, and headed/headless Playwright proof.

## Proof Added

`e2e/layer3-workbench.spec.js` now proves:

- the rendered panel and forms expose the required DOM markers;
- missing workflow authority leaves decision submit disabled;
- non-approved decisions without notes remain disabled before request;
- successful submit sends only the admitted submit fields;
- successful status inspection sends only the admitted status fields;
- submit and status output containers are read-only projections;
- raw notes are not rendered after submit and the notes input is cleared;
- backend notes-policy errors render blocked state without retaining raw notes;
- backend raw-reference rejection renders blocked state without retaining raw notes;
- already-decided workflow errors render blocked state without frontend authority;
- missing decision status authority and not-found status errors remain blocked;
- value reveal, delivery/export, source acquisition, Arelle, workflow-open, and default-on
  controls are not rendered.

## Verification

Initial focused proof:

- `node --check ./backend/app/review_ui/static/layer3.js` - PASS
- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium -g "SEC XBRL.*decision"` - PASS, 2 tests
- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --headed -g "SEC XBRL.*decision"` - PASS, 2 tests

Full closeout verification is recorded in
`next_milestone_plans/layer3_progress_manifest.json` and
`next_milestone_plans/layer3_workbench_proof_manifest.json`.

## Follow-On

After this PR lands and current-main verification is clean, the next safe posture is:

`sec_xbrl_value_reveal_authority_design_v1`

That follow-on remains design/pre-review first. It must address explicit approved-decision
eligibility, value-reveal authority, authorization/authentication, auditability,
containment and rollback, redaction posture, and default-off behavior before any value
reveal or default-on implementation is admitted.
