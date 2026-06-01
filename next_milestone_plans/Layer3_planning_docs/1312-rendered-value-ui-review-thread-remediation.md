# 1312 - SEC XBRL Rendered Value UI Review-Thread Remediation

Milestone: `sec_xbrl_rendered_controlled_value_reveal_ui_review_thread_remediation_v1`

Base authority: `project6-origin/main` at `da21a6b3ad54b1122056eb60419ff387d4178ee9`

Prior milestones:

- `next_milestone_plans/Layer3_planning_docs/1310-rendered-value-ui-proof.md`
- `next_milestone_plans/Layer3_planning_docs/1311-rendered-value-ui-post-merge-audit-closure.md`

## Status

Branch-local review-thread remediation over the merged rendered controlled
value-reveal UI proof.

## Review Findings Addressed

Repo-confirmed late automated review threads:

- PR `#2055`, `backend/app/review_ui/static/layer3.js`: reject uppercase
  SHA-256 hashes in the rendered authority-prepare and controlled-submit gates
  before POST, matching the lowercase-only backend validators.
- PR `#2055`, `backend/app/review_ui/static/layer3.js`: reject raw 10-digit
  CIK attestations before authority prepare POST, matching the backend raw
  authority guard.
- PR `#2055`, `backend/app/review_ui/static/layer3.js`: clear stale controlled
  reveal submit/status output when a new authority receipt is prepared.
- PR `#2055`, `backend/app/review_ui/static/layer3.js`: reject raw
  accession-like ids and bare 10-digit CIK ids before constructing the rendered
  status GET path.
- PR `#2056`, `next_milestone_plans/layer3_progress_board.md`: align the
  rendered UI proof posture with the closed post-merge audit and downstream
  gate-design selection posture.

## Scope

Runtime remediation is limited to the rendered `/review/layer3` client guard
surface. It narrows client admission before existing backend calls and clears
stale UI state; it does not add a backend route, schema, migration, durable
persistence, source acquisition, Arelle invocation, export/delivery,
provider/connector dispatch, default-on behavior, operator-authentication
claim, production-readiness claim, or final financial-statement semantics.

## Verification Result

Branch-local verification:

- `node --check ./backend/app/review_ui/static/layer3.js`: PASS.
- `python -m pytest ./backend/tests/test_layer3_page.py -k controlled_value_reveal -q`:
  PASS, `1 passed, 20 deselected, 3 warnings`.
- `python -m pytest ./backend/tests/test_layer3_page.py -q`: PASS,
  `21 passed, 3 warnings`.
- `python -m pytest <backend/tests/test_sec_xbrl*.py files> -q`: PASS,
  `299 passed, 4 warnings`.
- `npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --grep "SEC XBRL controlled value reveal"`:
  PASS, `1 passed`.
- `npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --headed --grep "SEC XBRL controlled value reveal"`:
  PASS, `1 passed`.
- `python ./tools/l3-target-selection-validate.py --expect frozen`: PASS.
- `python ./tools/l3-progress-check.py`: PASS.
- `python -m py_compile ./backend/tests/test_layer3_page.py`: PASS.
- UTF-8-SIG JSON validation: PASS for `53` committed SEC XBRL
  report/corpus JSON files plus the two Layer 3 manifests.
- Redaction scan across committed SEC XBRL report/corpus JSON files: PASS,
  `0` local path/URL/raw accession hits and `0` exact raw-value field hits.
- Residual-magnitude scan across committed SEC XBRL report/corpus JSON files:
  PASS, `0` nonzero residual-magnitude hits.
- `git diff --check`: PASS, no whitespace errors.

## Next Posture

After this remediation lands and the original review threads are resolved, the
next admissible movement remains
`sec_xbrl_next_downstream_gate_design_selection_before_any_default_on_export_or_production_implementation`.
