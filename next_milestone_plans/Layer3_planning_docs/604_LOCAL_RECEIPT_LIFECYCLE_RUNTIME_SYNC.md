# 604 - Local Receipt Lifecycle Runtime Sync

## Status

Status: current-main sync for `implement_layer3_local_receipt_lifecycle_hardening_after_real_target_missing_decision_sync`.

Doc: `604_LOCAL_RECEIPT_LIFECYCLE_RUNTIME_SYNC.md`.

Implementation PR: `#1201`.

Implementation merge commit: `5d71f153f0e19a02075d8ccc6a08143b5bbb4049`.

Prior freeze sync doc: `603_LOCAL_RECEIPT_LIFECYCLE_HARDENING_CURRENT_MAIN_SYNC.md`.

Branch: `codex/l3-local-receipt-lifecycle-impl`.

## Current-Main Result

Current main now includes the local receipt lifecycle-hardening implementation selected by doc `602` and synced by doc `603`.

The admitted runtime remains limited to the internal fake/local connector destination receipt lifecycle. Current main now projects:

- read-only local receipt lifecycle/status surface;
- receipt history/listing for the current session/reconciliation authority;
- ready, recorded, unavailable, and guardrail-oriented failure-state projection;
- idempotency and retry policy text;
- duplicate/replay/conflict status for local receipt authority; and
- rendered `/review/layer3` proof over the existing handoff/export readiness path.

## Proof Gate

PR `#1201` merged cleanly after GitHub checks passed:

- `backend-layer3-api`: success;
- `test`: success.

Post-merge validation was run on `project6-origin/main` at `5d71f153f0e19a02075d8ccc6a08143b5bbb4049`:

- `python -m py_compile .\backend\app\services\layer3_workbench.py .\backend\tests\test_layer3_api.py .\backend\tests\test_layer3_bounded_e2e.py .\backend\tests\test_layer3_page.py`;
- `node --check .\backend\app\review_ui\static\layer3.js`;
- `python .\tools\l3-progress-check.py`;
- `python -m pytest .\backend\tests\test_layer3_api.py -k "connector_local_destination_receipt"`;
- `python -m pytest .\backend\tests\test_layer3_page.py`;
- `python -m pytest .\backend\tests\test_layer3_bounded_e2e.py -k "associated_cohort_reaches_download_delivery"`;
- `npx playwright test e2e/layer3-workbench.spec.js -g "Layer 3 workbench drives raw mixed rendered external export download delivery" --project=chromium`; and
- `npx playwright test e2e/layer3-workbench.spec.js -g "Layer 3 workbench drives raw mixed rendered external export download delivery" --project=chromium --headed`.

The headed/headless Playwright checks must be run sequentially unless the harness is configured with separate ports/state; both use fixed `127.0.0.1:8031`.

## Non-Admission Boundary

This sync admits no real connector invocation, destination write, connector-run creation, credential handling, provider-public delivery/use, package mutation/reconstruction, source expansion, RAG/vector behavior, auth/security behavior change, full mockup activation, frontend-durable authority, generic downstream dispatch, rendered write controls, or real external destination integration.

## Next Posture

The next whole-project posture is `await_real_connector_destination_named_target_decision_after_local_receipt_lifecycle_runtime_sync`.
