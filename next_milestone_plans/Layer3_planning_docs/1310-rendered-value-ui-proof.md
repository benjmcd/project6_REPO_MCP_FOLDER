# 1310 - SEC XBRL Rendered Value UI Proof

Milestone: `sec_xbrl_rendered_controlled_value_reveal_ui_proof_v1`

Base authority: `project6-origin/main` at `f861acb16677267cc58173c1f0b3fcf820e93bcc`

Prior milestone: `next_milestone_plans/Layer3_planning_docs/1309-rendered-value-ui-admission-selection.md`

Merged authority: PR `#2055` at `f59cf53f367e036d9c9e8b7029b98cbbe8ea07ce`

## Status

Merged current-main Tier-2 risk-assessed implementation entry, verified after
merge.

This slice renders the bounded SEC XBRL controlled value-reveal operator panel
selected by 1309. It uses only the existing backend authority prepare,
controlled submit, and submit-status APIs.

## Tier-2 Surfaces

Touched Tier-2 surfaces:

- `backend/app/review_ui/static/layer3.html`: adds the rendered controlled
  value-reveal panel shell.
- `backend/app/review_ui/static/layer3.js`: adds browser controls for authority
  prepare, explicit controlled submit, and status inspection over existing API
  routes.
- `e2e/layer3-workbench.spec.js`: proves browser disabled states, request
  payload allowlists, transient submit-response rendering, and value-free status
  rendering.

Supporting proof surface:

- `backend/tests/test_layer3_page.py`: adds a static rendered-surface boundary
  test for the new panel and payload builders.

## Authority Boundary

The browser may prepare value-reveal authority only from:

- `client_request_id`;
- `authority_mode=sec_xbrl_value_reveal_authority_receipt_v1`;
- `operator_decision=prepare_sec_xbrl_value_reveal_authority`;
- `sec_xbrl_operator_review_decision_id`;
- `decision_basis_hash`;
- optional bounded `operator_attestation`.

The browser may submit controlled value reveal only from:

- `client_request_id`;
- `submit_mode=sec_xbrl_controlled_value_reveal_submit_v1`;
- `operator_decision=submit_explicit_sec_xbrl_value_reveal_from_authority_receipt`;
- `sec_xbrl_value_reveal_authority_receipt_id`;
- `authority_basis_hash`;
- `operator_reveal_confirmation=true`;
- optional `max_records`.

The browser may inspect submit status only from:

- `sec_xbrl_controlled_value_reveal_submit_receipt_id`.

The panel renders controlled values only from the backend submit response. The
status projection is read-only and intentionally does not render
`revealed_facts` from the status response.

## Containment And Rollback

This slice does not touch schema, `models.py`, Alembic migrations, durable
persistence, backend API routes, backend value-reveal services, source
acquisition, Arelle subprocess invocation, export/delivery, default-on
behavior, or production-readiness posture.

Rollback is containment-only: remove or hide the rendered panel and JS handlers.
No database rollback is required because this slice adds no migration and writes
no new durable server state.

## Non-Goals

- no new backend route or service behavior;
- no schema, model, migration, or persistence change;
- no frontend durable authority;
- no browser-side reconstruction of server authority;
- no default-on behavior, automatic reveal, batch reveal, pagination, export, or
  delivery;
- no source acquisition, Arelle invocation, provider/connector dispatch, or raw
  runtime artifact;
- no value rendering from local browser state;
- no status-response value replay;
- no operator identity/authentication claim beyond existing backend authority;
- no production-readiness or final financial-statement semantics claim.

## Verification

Branch and post-merge current-main verification:

- `node --check ./backend/app/review_ui/static/layer3.js`: PASS.
- `python -m pytest ./backend/tests/test_layer3_page.py -k controlled_value_reveal -q`:
  PASS, `1 passed, 20 deselected, 3 warnings`.
- `python -m pytest ./backend/tests/test_layer3_page.py -q`: PASS,
  `21 passed, 3 warnings`.
- `npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --grep "SEC XBRL controlled value reveal"`:
  PASS, `1 passed`.
- `npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --headed --grep "SEC XBRL controlled value reveal"`:
  PASS, `1 passed`.
- `python -m pytest <backend/tests/test_sec_xbrl*.py files> -q`: PASS,
  `299 passed, 4 warnings`.
- `python ./tools/l3-target-selection-validate.py --expect frozen`: PASS.
- `python ./tools/l3-progress-check.py`: PASS.
- `python -m py_compile ./backend/tests/test_layer3_page.py`: PASS.
- UTF-8-SIG JSON parse of changed manifests and 55 committed SEC XBRL JSON
  files: PASS.
- committed SEC XBRL JSON redaction scan: PASS, `0` accession, SEC URL,
  Windows path, file URI, or operator-email hits across 55 files.
- residual-magnitude scan: PASS, `0` nonzero residual-magnitude hits across 55
  files.
- `git diff --check`: PASS.

Post-merge audit closure is recorded in
`next_milestone_plans/Layer3_planning_docs/1311-rendered-value-ui-post-merge-audit-closure.md`.

## Next Posture

The post-merge audit closure for this rendered proof is recorded in 1311. The
next admissible question is not default-on by default; it is a design/admission
selection pass for exactly one downstream gate, with default-on readiness,
export/delivery, operator-auth hardening, and production-readiness controls
treated as separate candidates.
