# 879 - Source Directory Extension Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `extend_source_directory_ingestion_scan_status_rendered_control`.

Sync doc: `879_SOURCE_DIRECTORY_EXTENSION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `878_SOURCE_DIRECTORY_EXTENSION_RUNTIME_PROOF.md`.

Runtime PR: `#1492`.

Runtime branch: `codex/l3-source-directory-rendered-authority-extension`.

Runtime branch commit: `108e5e18`.

Runtime merge commit: `7281432b976f434b94a5ee034a9210dccb88bcc0`.

Synced result: `current_main_synced_source_directory_extension_runtime`.

Runtime behavior introduced by this sync: `false`.

Rendered behavior introduced by this sync: `false`.

Route/API/DTO/model/migration/service behavior introduced by this sync: `false`.

Full mockup program activation introduced by this sync: `false`.

## Current-Main Authority

Current `main` now includes the bounded rendered-control implementation from PR `#1492`:

- the existing `/review/layer3` source-directory scan/status panel renders `runtime_policy_id`;
- the same rendered panel displays `recursive_traversal_admitted`, `max_recursion_depth`, and `max_relative_path_segments`;
- caller-selected recursive flag authority renders as blocked from existing scan/status response fields;
- response schema, response status, and idempotency/replay state render as server response authority;
- scan requests still submit only `client_request_id`, `operator_decision`, `source_family`, and `ingestion_mode`;
- raw local paths, caller paths, directory fields, recursive flags, and file bytes remain blocked.

This sync doc adds no new implementation, route, API, DTO, model, migration, service behavior, rendered control, source traversal behavior, package behavior, connector/destination behavior, provider URL behavior, RAG/vector behavior, browser-state authority, auth/security behavior, mockup-screen activation, or full mockup program activation.

## GitHub Proof

PR `#1492` merged on 2026-05-20 with these checks:

- `backend-layer3-api`: `SUCCESS`, `3m37s`;
- `test`: `SUCCESS`, `3m39s`;
- reviewThreads totalCount: `0`;
- PR comments: `0`;
- latest reviews: `0`.

Post-merge local validation passed on current main at `7281432b976f434b94a5ee034a9210dccb88bcc0`:

- `node --check .\backend\app\review_ui\static\layer3.js`;
- `python .\tools\l3-progress-check.py`;
- `python -m pytest .\backend\tests\test_layer3_page.py::test_layer3_source_directory_ingestion_rendered_control_is_bounded -q`.
- `PLAYWRIGHT_PYTHON=python npx playwright test --project=chromium -g "Layer 3 workbench renders source-directory scan and status authority fields"`;
- `PLAYWRIGHT_PYTHON=python npx playwright test --project=chromium --headed -g "Layer 3 workbench renders source-directory scan and status authority fields"`.

## Boundaries Preserved

Do not render this sync as backend runtime behavior, route/API/DTO/model/migration/service behavior change, source traversal behavior change, caller path support, browser file-byte support, URL/glob support, caller-selected recursive flag support, source expansion, package mutation/construction, connector/destination dispatch, provider URL behavior, cloud object-store write, RAG/vector widening, prompt/model/provider qualitative generation, hidden LLM planning, optional-tool runtime, auth/security behavior, browser-storage authority, frontend-only durable authority, single mockup screen activation, or full mockup program activation.

## Next Posture

The next exact posture is `select_first_read_only_mockup_screen_projection_after_source_directory_extension_runtime_sync`.
