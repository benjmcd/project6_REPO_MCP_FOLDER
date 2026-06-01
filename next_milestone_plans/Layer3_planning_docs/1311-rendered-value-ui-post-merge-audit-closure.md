# 1311 - SEC XBRL Rendered Value UI Post-Merge Audit Closure

Milestone: `sec_xbrl_rendered_controlled_value_reveal_ui_post_merge_audit_closure_v1`

Base authority: `project6-origin/main` at `f59cf53f367e036d9c9e8b7029b98cbbe8ea07ce`

Prior milestone: `next_milestone_plans/Layer3_planning_docs/1310-rendered-value-ui-proof.md`

Merged authority under audit: PR `#2055` at `f59cf53f367e036d9c9e8b7029b98cbbe8ea07ce`

## Status

Current-main Tier-1 documentation/proof closure over the already-merged Tier-2
rendered controlled value-reveal UI proof.

This pass changes no runtime behavior. It records that the rendered value-reveal
UI proof landed, passed CI after the rendered label hardening, has no current
review threads, and passes post-merge verification on current main.

## Audit Findings

Repo-confirmed:

- PR `#2055` is merged at `f59cf53f367e036d9c9e8b7029b98cbbe8ea07ce`.
- The final PR head before squash was
  `816543ff20c2ce613648bf99fe5d3a31d61d24e9`.
- GitHub CI for the final PR head passed all backend and Playwright shards.
- GitHub review-thread audit returned `total_threads=0` and
  `current_unresolved_threads=0`.
- No submitted independent review was recorded before merge; independent review
  was requested and the merge used the softened Tier-2 policy with documented
  self-verification, CI evidence, containment notes, and follow-up triggers.
- The first CI run caught a rendered label issue: `Prepare Authority` matched an
  existing broad `/auth/` deferred-control regex. The fix changed only the
  rendered button label to `Prepare Receipt`; payloads, endpoint paths, authority
  mode, and receipt semantics remained unchanged.

## Scope Confirmed

Merged #2055 touched only:

- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.js`;
- `backend/tests/test_layer3_page.py`;
- `e2e/layer3-workbench.spec.js`;
- `next_milestone_plans/Layer3_planning_docs/1310-rendered-value-ui-proof.md`;
- `next_milestone_plans/layer3_progress_board.md`;
- `next_milestone_plans/layer3_progress_manifest.json`;
- `next_milestone_plans/layer3_workbench_proof_manifest.json`.

No `models.py`, Alembic migration, schema, durable persistence, backend API
route, backend service behavior, source acquisition, Arelle subprocess,
export/delivery, provider/connector dispatch, default-on behavior, raw runtime
artifact, production-readiness, or final financial-statement semantics surface
was changed.

## Current-Main Verification

Post-merge verification on current main at
`f59cf53f367e036d9c9e8b7029b98cbbe8ea07ce`:

- `node --check ./backend/app/review_ui/static/layer3.js`: PASS.
- `python -m pytest ./backend/tests/test_layer3_page.py -q`: PASS,
  `21 passed, 3 warnings`.
- `python -m pytest <backend/tests/test_sec_xbrl*.py files> -q`: PASS,
  `299 passed, 4 warnings`.
- `npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --grep "SEC XBRL controlled value reveal|external export download signed reference"`:
  PASS, `2 passed`.
- `python ./tools/l3-target-selection-validate.py --expect frozen`: PASS.
- `python ./tools/l3-progress-check.py`: PASS.
- `python -m py_compile ./backend/tests/test_layer3_page.py`: PASS.
- UTF-8-SIG JSON parse for the progress/proof manifests and 55 committed SEC
  XBRL JSON files: PASS.
- Redaction scan across 55 committed SEC XBRL JSON files: PASS, `0` accession,
  SEC URL, Windows path, file URI, or operator-email hits.
- Residual-magnitude scan across 55 committed SEC XBRL JSON files: PASS, `0`
  nonzero residual-magnitude hits.
- `git diff --check`: PASS.

## Non-Goals

This closure does not admit default-on behavior, automatic value reveal,
export/delivery, source acquisition, Arelle invocation, provider/connector
dispatch, new API/UI beyond the already-merged rendered proof, schema,
persistence, operator-authentication claims, production readiness, or final
financial-statement semantics.

## Next Posture

The next admissible movement is a design/admission-selection pass for exactly
one downstream gate, with default-on readiness, export/delivery, operator-auth
hardening, and production-readiness controls treated as separate candidates.
Do not proceed directly to implementation until the chosen candidate has a
bounded design, explicit authority boundary, containment/rollback notes, and
proof obligations.
