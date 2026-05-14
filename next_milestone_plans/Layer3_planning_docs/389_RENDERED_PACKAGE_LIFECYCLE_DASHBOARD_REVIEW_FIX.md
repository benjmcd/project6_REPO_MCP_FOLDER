# 389 - Rendered Package Lifecycle Dashboard Review Fix

## Status

Status: branch-local review fix for `rendered_package_lifecycle_read_only_dashboard`.

This proof addresses PR `#983` review threads:

- `PRRT_kwDORzuv8M6B-1Ee`: prioritize submit errors before ready state.
- `PRRT_kwDORzuv8M6B-1Ei`: prioritize construction errors before preview state.
- `PRRT_kwDORzuv8M6B-1En`: preserve non-approved submit states after refresh.

## Fix

`packageLifecycleDashboardState` now evaluates package lifecycle state in this order:

1. pending submit/construction/preview states;
2. recorded package-review submit state or submit record ref;
3. package-review preview, construction, or submit error state;
4. ready/constructed/preview fallbacks;
5. waiting state.

This preserves `package_review_changes_requested`, `package_review_rejected`, and `package_review_blocked` style states from refreshed server/session state, and prevents stale ready state from hiding failed commit or submit attempts.

`packageReviewSubmitState` also prefers a recorded `State.sessionSummary.package_review_submit` before synthesizing `package_review_submit_ready` from local package-construction state. That prevents a refreshed recorded submit decision from being hidden by stale local construction state.

## Scope

Changed files:

- `backend/app/review_ui/static/layer3.js`
- `e2e/layer3-workbench.spec.js`
- `tools/l3-progress-check.py`
- `next_milestone_plans/Layer3_planning_docs/389_RENDERED_PACKAGE_LIFECYCLE_DASHBOARD_REVIEW_FIX.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`

No backend route, DTO, model, migration, service behavior, schema shape, package mutation authority, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, or frontend-only durable authority changed.

## Proof

Focused E2E coverage:

- `Layer 3 package lifecycle dashboard prioritizes recorded and error states`

The test asserts:

- `package_lifecycle_blocked` after `State.packageConstructionError` while package preview state remains present;
- `package_lifecycle_blocked` after `State.packageReviewSubmitError` while package construction state remains ready;
- `package_review_changes_requested` when session state contains a recorded non-approved package-review submit record.
- recorded `State.sessionSummary.package_review_submit` takes precedence over synthetic construction-ready state.

Required validation before merge:

- `node --check .\backend\app\review_ui\static\layer3.js`
- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "Layer 3 package lifecycle dashboard prioritizes recorded and error states"`
- `python .\tools\l3-progress-check.py`
- `git diff --check`

## Remaining Gate

The review-fix PR must pass GitHub `backend-layer3-api` and `test`, settle comments/reviews/reviewThreads, merge, pass post-merge `project6-origin/main` progress validation, and then be current-main synced.
