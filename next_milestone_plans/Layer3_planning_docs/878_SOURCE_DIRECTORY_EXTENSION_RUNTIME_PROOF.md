# 878 - Source Directory Extension Runtime Proof

## Status

Status: branch-local runtime/rendered proof for `extend_source_directory_ingestion_scan_status_rendered_control`.

Proof doc: `878_SOURCE_DIRECTORY_EXTENSION_RUNTIME_PROOF.md`.

Predecessor freeze doc: `877_SOURCE_DIRECTORY_EXTENSION_FREEZE.md`.

Current-main checkpoint before implementation: `4a715e4c57206a0b3c30adbde9a27f9c94863bb9`.

Implementation branch: `codex/l3-source-directory-rendered-authority-extension`.

Implemented action: `extend_source_directory_ingestion_scan_status_rendered_control`.

Selected activation mode: `single_existing_rendered_control_extension`.

Selected target: `source_directory_ingestion_scan_status_rendered_control`.

Backend runtime behavior change: `false`.

Rendered behavior change: `true`.

Route/API/DTO/model/migration/service behavior change: `false`.

Full mockup program activation: `false`.

## Implemented Surface

The existing `/review/layer3` `#source-directory-ingestion-rendered-controls` panel now renders additional server-authority fields from the existing source-directory scan/status responses:

- `runtime_policy_id`;
- `recursive_traversal_admitted`;
- `max_recursion_depth`;
- `max_relative_path_segments`;
- `caller_selected_recursive_flag_allowed`;
- response schema;
- response status;
- idempotency/replay status;
- fail-closed blocked scan/status display.

The browser still submits only:

- `client_request_id`;
- `operator_decision`;
- `source_family`;
- `ingestion_mode`.

No caller path, directory, URL, glob, file bytes, recursive flag, connector, provider, package, RAG/vector, prompt/model, browser-storage, or auth/security authority is accepted.

## Changed Files

- `backend/app/review_ui/static/layer3.js`;
- `backend/tests/test_layer3_page.py`;
- `e2e/layer3-workbench.spec.js`.

Planning/proof/checker files were also updated to record this branch-local proof.

## Validation

Passed:

- `node --check .\backend\app\review_ui\static\layer3.js`;
- `python -m pytest .\backend\tests\test_layer3_page.py::test_layer3_source_directory_ingestion_rendered_control_is_bounded -q`;
- `PLAYWRIGHT_PYTHON=python npx playwright test --project=chromium -g "Layer 3 workbench renders source-directory scan and status authority fields"`;
- `PLAYWRIGHT_PYTHON=python npx playwright test --project=chromium --headed -g "Layer 3 workbench renders source-directory scan and status authority fields"`.

The first attempted path-scoped Playwright invocation did not run any tests because the Windows path argument did not match Playwright's selector parsing. The successful headless and headed commands above reran the same focused test by grep.

## Browser Proof

The focused Playwright proof verifies:

- the source-directory rendered control is visible;
- the scan response renders `runtime_policy_id`;
- recursive traversal status renders as response authority;
- max recursion depth and max relative path segment limits render;
- caller-selected recursive flag status renders as blocked;
- response schema and response status render;
- idempotency/replay status renders;
- the rendered panel does not expose `C:\` or `/Users/` raw local paths;
- the scan payload contains only the existing bounded request fields;
- no `path`, `directory`, `recursive`, or `file_bytes` fields are submitted;
- the status button loads the status schema projection;
- page horizontal overflow is false;
- console errors are empty;
- page errors are empty;
- no package mutation, connector dispatch, provider-private signed URL prepare, mixed-corpus materialization, or execution-start request is made.

Headless Chromium result: passed.

Headed Chromium result: passed.

## Non-Admission Boundary

This proof admits no backend runtime behavior, route/API/DTO/model/migration/service behavior change, source traversal behavior change, caller path support, browser file-byte support, URL/glob support, source expansion, package mutation/construction, connector/destination dispatch, provider URL behavior, cloud object-store write, RAG/vector widening, prompt/model/provider qualitative generation, hidden LLM planning, optional-tool runtime, auth/security behavior, browser-storage authority, frontend-only durable authority, single mockup screen activation, or full mockup program activation.

## Next Posture

The next exact posture is `current_main_sync_source_directory_extension_runtime`.

After merge, create a current-main sync packet for this branch-local proof before selecting any mockup-screen projection target.
