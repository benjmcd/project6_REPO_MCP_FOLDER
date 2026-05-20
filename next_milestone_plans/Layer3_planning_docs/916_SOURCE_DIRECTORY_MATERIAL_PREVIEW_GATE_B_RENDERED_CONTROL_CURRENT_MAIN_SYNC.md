# 916 - Source-Directory Material Preview Gate B Rendered Control Current-Main Sync

## Status

Status: current-main sync for `source_directory_material_preview_gate_b_rendered_control_current_main_sync`.

Doc: `916_SOURCE_DIRECTORY_MATERIAL_PREVIEW_GATE_B_RENDERED_CONTROL_CURRENT_MAIN_SYNC.md`.

Predecessor control doc: `915_PROVIDER_PUBLIC_URL_DELIVERY_USE_RENDERED_CONTROL_STATUS_FRESHNESS_REVIEW_REMEDIATION.md`.

Merged PR: `#1530`.

Source branch: `codex/l3-mockup-activation-inventory`.

Implementation commit: `4d59536808122914a2286afeb4586f6a22ee929e`.

Merge commit: `7b5322a93b83762f656db79fe79acd4b320e1efb`.

Sync branch: `codex/l3-source-dir-gateb-sync`.

Base authority: `project6-origin/main` at `7b5322a93b83762f656db79fe79acd4b320e1efb`.

## Current-Main Authority

PR `#1530` is current-main truth for a bounded rendered source-directory material-preview and Gate B control extension.

The live rendered surface is `/review/layer3 #source-directory-ingestion-rendered-controls`.

The server authority remains the existing source-directory scan/status, material-preview, and Gate B decision chain:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`
- `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/material-preview`
- `POST /api/v1/layer3/gate-b/decision`

The durable authority remains `L3SourceDirectoryIngestionBatch`, `L3SourceDirectoryIngestionFile`, `L3MaterialSnapshot`, and existing Gate B/session state. The rendered control posts only server-returned, response-safe material-preview authority. It does not accept caller paths, file bytes, URLs, glob patterns, recursive traversal controls, or browser-local durable state.

## Validation Preserved

Local validation before merge passed:

- `git diff --check project6-origin/main..HEAD`
- `node --check ./backend/app/review_ui/static/layer3.js`
- `python -m pytest ./backend/tests/test_layer3_page.py::test_layer3_source_directory_ingestion_rendered_control_is_bounded ./backend/tests/test_layer3_source_directory_ingestion.py::test_layer3_source_directory_material_preview_reaches_gate_b_without_broad_outputs -q`
- `python -m py_compile ./tools/l3-progress-check.py; python ./tools/l3-progress-check.py`
- `npx playwright test --project=chromium ./e2e/layer3-workbench.spec.js -g "Layer 3 workbench renders source-directory scan and status authority fields"`
- `npx playwright test --project=chromium --headed ./e2e/layer3-workbench.spec.js -g "Layer 3 workbench renders source-directory scan and status authority fields"`

GitHub validation before merge passed:

- `backend-layer3-api` success
- `test` success
- PR comments, reviews, latestReviews, and reviewThreads were empty before merge

## Non-Admission Boundary

This sync introduces no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior, executable test behavior, production UI behavior, server-authoritative full mockup activation, or frontend-only durable authority.

The merged implementation introduced only the already-landed rendered source-directory material-preview and Gate B controls over existing backend authority. This sync does not admit full mockup program activation, mockup-frame write controls without complete route/state/proof contracts, source expansion beyond server-configured ingestion, caller path/directory/file-byte/URL/glob/recursive controls, connector/destination dispatch, provider/public URL runtime, package mutation/reconstruction expansion, RAG/vector/model/provider runtime, optional-tool runtime, auth/security behavior, browser-storage authority, or frontend-only durable authority.

## Next Posture

Next exact posture: `select_next_blocker_retirement_lane_after_source_directory_material_preview_gate_b_rendered_control_current_main_sync`.

The next code-bearing lane should be selected only after this current-main sync is preserved by the progress/control artifacts. The adequate next target remains a separately frozen blocker-retirement lane, not full mockup activation. Full mockup activation remains blocked until every critical mockup operator journey is proven live, read-only, intentionally excluded, or explicitly blocked by a route/state/durable-authority/headed/headless/security contract.
