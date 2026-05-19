# 875 - Internal Webhook Rendered Status Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `implement_internal_webhook_rendered_read_only_status_projection` runtime.

Sync doc: `875_INTERNAL_WEBHOOK_RENDERED_STATUS_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `874_INTERNAL_WEBHOOK_RENDERED_STATUS_RUNTIME_PROOF.md`.

Runtime PR: `#1490`.

Runtime branch: `codex/l3-internal-webhook-rendered-status-runtime`.

Runtime branch commit: `572f147781433ffe920410f5c77ba7ea5ba9ecd4`.

Runtime merge commit: `61bb8338176e704877b1883dfaa1b0ee04874ffc`.

Synced result: `current_main_synced_internal_webhook_rendered_status_runtime`.

Runtime behavior introduced by this sync: `false`.

Rendered behavior introduced by this sync: `false`.

Dispatch behavior introduced by this sync: `false`.

## Current-Main Authority

Current `main` now includes the bounded runtime/rendered implementation from PR `#1490`:

- existing `GET /api/v1/layer3/session/{session_id}` exposes `Layer3SessionSummaryResponse.internal_webhook_dispatch`;
- durable `L3InternalWebhookDispatchReceipt` and `L3InternalWebhookDispatchAuditEvent` remain canonical authority;
- `/review/layer3` renders `#internal-webhook-dispatch-panel` from `State.sessionSummary.internal_webhook_dispatch`;
- rendered mode remains `rendered_internal_webhook_dispatch_read_only_status_surface`.

This sync doc adds no new implementation, model, migration, route, dispatch behavior, rendered control, or destination authority.

## GitHub Proof

PR `#1490` merged on 2026-05-19 with these checks:

- `backend-layer3-api`: `SUCCESS`, `3m24s`;
- `test`: `SUCCESS`, `3m30s`;
- reviewThreads totalCount: `0`;
- PR comments: `0`;
- latest reviews: `0`.

Post-merge local validation passed on current main at `61bb8338176e704877b1883dfaa1b0ee04874ffc`:

- `python .\tools\l3-progress-check.py`;
- `python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_internal_webhook_dispatch_success_idempotent_and_redacted .\backend\tests\test_layer3_page.py::test_layer3_page_route_serves_workbench_shell .\backend\tests\test_layer3_page.py::test_layer3_static_assets_are_mounted -q`.

## Boundaries Preserved

Do not render this sync as internal webhook dispatch rerun/retry/cancel/queue/background-worker behavior, rendered dispatch/submit controls, URL/credential inputs, destination selection, operator-supplied destination URL authority, raw URL/token/header/local-path/package exposure, `ConnectorRun`/`ConnectorRunTarget` creation, provider URL behavior, optional-tool runtime, frontend-only durable authority, or any additional runtime beyond PR `#1490`.

## Next Posture

The next exact posture is `select_next_major_layer3_end_to_end_gap_after_internal_webhook_rendered_status_runtime_sync`.
