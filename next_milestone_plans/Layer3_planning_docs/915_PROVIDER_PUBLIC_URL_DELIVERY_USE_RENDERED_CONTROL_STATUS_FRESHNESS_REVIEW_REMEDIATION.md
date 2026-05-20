# 915 - Provider-Public URL Delivery/Use Rendered Control Status-Freshness Review Remediation

## Status

Status: review-remediation implementation for `remediate_provider_public_url_delivery_use_rendered_control_status_freshness_review_threads`.

Doc: `915_PROVIDER_PUBLIC_URL_DELIVERY_USE_RENDERED_CONTROL_STATUS_FRESHNESS_REVIEW_REMEDIATION.md`.

Predecessor proof doc: `914_PROVIDER_PUBLIC_URL_DELIVERY_USE_RENDERED_CONTROL_EXTENSION.md`.

Current-main preflight commit: `77ce23e85edcfdea601b51488adeac3f83a10ab6`.

Branch: `codex/l3-provider-use-review-remediation`.

Source review threads:

- PR `#1528`, `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1528#discussion_r3273964977`
- PR `#1528`, `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1528#discussion_r3273964981`
- PR `#1528`, `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1528#discussion_r3273964990`

## Review Assessment

The findings are valid against the merged PR `#1528` provider-public URL delivery/use rendered-control implementation.

The rendered use decision is intentionally a redacted, non-durable server decision over the existing provider-public URL use route. However, after the use decision is cached in `State.providerPublicUrlUse`, later operator status refreshes must be able to override that cached use snapshot for lifecycle state, panel rows, and lifecycle dashboards. Otherwise the UI can keep presenting stale use-time `provider_public_url_prepared` state after the server reports a newer `expired` or `revoked` status.

## Remediation

The changed rendered owner remains `backend/app/review_ui/static/layer3.js`.

The remediation:

- reorders provider-public receipt/state selection so `State.providerPublicUrlStatus` wins over `State.providerPublicUrlUse` after `State.providerPublicUrlRevoke`;
- adds `providerPublicUrlLatestSnapshot()` and uses it for downstream access lifecycle rows, Layer 3 governance lifecycle rows, and the provider-public panel;
- computes the use payload before clearing stale status, preserving expected authority/source checks from the latest server state;
- clears the pre-use status snapshot when the operator records a use decision, so the immediate redacted use result remains visible until the next status refresh;
- extends the focused browser proof to inspect status after a successful use decision and verify the panel renders status-derived rows instead of stale use-derived rows.

## Validation

Focused validation passed:

- `node --check ./backend/app/review_ui/static/layer3.js`;
- `python -m pytest ./backend/tests/test_layer3_page.py::test_layer3_static_assets_are_mounted ./backend/tests/test_layer3_page.py::test_layer3_provider_public_url_use_rendered_control_is_bounded -q` with `2 passed, 3 warnings`;
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "provider-public URL prepare status use revoke" --project=chromium` with `1 passed`;
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "provider-public URL prepare status use revoke" --project=chromium --headed` with `1 passed`;
- `python -m json.tool ./next_milestone_plans/layer3_progress_manifest.json` passed;
- `python -m json.tool ./next_milestone_plans/layer3_workbench_proof_manifest.json` passed;
- `python -m py_compile ./tools/l3-progress-check.py` passed;
- `python ./tools/l3-progress-check.py` passed;
- `git diff --check` passed.

## Non-Admission Boundary

This remediation changes only provider-public rendered state freshness inside the already-admitted Doc 914 rendered use-decision control.

It admits no runtime behavior, backend behavior, route/API/DTO/model/migration/service behavior, raw provider-public URL delivery, public proxy behavior, byte streaming, provider network or object writes, real connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector behavior, auth/security behavior, browser-storage authority, frontend-only durable authority, mockup-frame write controls, or full mockup program activation.

## Next Posture

After this remediation merges, the required next action is `current_main_sync_provider_public_url_delivery_use_rendered_control_status_freshness_review_remediation_then_select_next_blocker_retirement_lane`.

After that sync, the next whole-project posture remains to select the next separately frozen blocker-retirement lane. Do not admit real connector/destination dispatch, package mutation/reconstruction, raw provider-public URL delivery, RAG/vector runtime, auth/security behavior, or full mockup program activation without an exact route/state/durable-authority/test/security contract.
