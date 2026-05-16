# 634 - Package Supersession Preview Rendered Control

## Status

Status: branch-local implementation proof for `rendered_package_supersession_preview_control`.

This implementation follows current-main sync doc `633_PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_ACTION_CURRENT_MAIN_SYNC.md`.

Implementation branch: `codex/l3-package-supersession-preview-control`.

Current-main checkpoint before implementation: `31966bce3fa8462cf918bf0c518359b0a51239b3`.

Selected surface: `package_mutation_reconstruction`.

Selected exact operator action: `supersede_package_preview`.

Selected implementation-entry mode: `rendered_package_supersession_preview_control`.

Existing backend surface: `/api/v1/layer3/package/mutation/preview`.

Owner service: `backend/app/services/layer3_package_mutation_entry.py`.

Server runtime mode: `package_supersession_preview_only`.

Operator decision: `preview_package_supersession`.

Layer 3 placement: Data Structuring & Processing package lifecycle boundary.

## Implemented Slice

The rendered `/review/layer3` package review area now includes a bounded `Preview Supersession` control and a read-only `package-supersession-preview-panel`.

The control assembles a transient browser request from already-rendered server authority and calls only `/api/v1/layer3/package/mutation/preview`.

The implementation files are:

- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.css`;
- `backend/app/review_ui/static/layer3.js`;
- `backend/tests/test_layer3_page.py`;
- `e2e/layer3-workbench.spec.js`.

The progress/proof owner files for this pass are:

- `next_milestone_plans/Layer3_planning_docs/634_PACKAGE_SUPERSESSION_PREVIEW_RENDERED_CONTROL.md`;
- `next_milestone_plans/layer3_progress_board.md`;
- `next_milestone_plans/layer3_progress_manifest.json`;
- `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `tools/l3-progress-check.py`.

No backend route, DTO, response model, database model, migration, or package mutation service behavior changed in this pass.

## Request Boundary

The rendered control submits only these required fields:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `output_package_ids`;
- `package_kinds`;
- `payload_refs`;
- `payload_hashes`;
- `package_review_preview_hash`;
- `operator_decision`.

The rendered control may include only these optional downstream record refs when they already exist in response state:

- `package_review_submit_record_ref`;
- `handoff_export_record_ref`;
- `aps_handoff_record_ref`;
- `external_export_download_record_ref`;
- `connector_dispatch_record_ref`.

The browser implementation owner is `packageSupersessionPreviewPayload`. Browser state is transient request assembly only and is not durable authority.

The rendered control does not submit `preview_id`, `preview_hash`, `analysis_run_id`, `result_review_record_ref`, package commit fields, package row mutation fields, replacement package fields, edited package content, arbitrary destination ids or URLs, connector ids, connector run ids, source expansion fields, RAG/vector fields, auth/security fields, hidden LLM fields, retry/rerun/cancel fields, or frontend-durable state.

## Rendered State

The rendered state uses:

- `PACKAGE_SUPERSESSION_PREVIEW_RENDERED_MODE = rendered_package_supersession_preview_control`;
- `PACKAGE_SUPERSESSION_PREVIEW_USE_CASE = operator_previews_package_supersession_without_package_row_or_payload_mutation`;
- `PACKAGE_SUPERSESSION_PREVIEW_RESPONSE_AUTHORITY = State.packageSupersessionPreview`;
- `PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION = preview_package_supersession`.

The panel renders ready, submitting, previewed, and failed states from response-safe data.

The display helper `safePackagePayloadRefForDisplay` redacts raw local path-shaped payload refs as `redacted_local_payload_ref`.

The panel displays only response-safe status, hashes, immutable package rows, dependency rows, disabled capability flags, and failure codes. It does not expose package payload bytes or create durable frontend authority.

## Proof

Static proof:

- `backend/tests/test_layer3_page.py` asserts the rendered button, panel, mode, JavaScript constants, payload builder, API call, ready-state term, redaction term, and CSS selectors.

API proof:

- `backend/tests/test_layer3_api.py -k package_supersession_preview` continues to prove the existing server-authoritative preview API and its failure guardrails without backend widening.

Rendered E2E proof:

- `e2e/layer3-workbench.spec.js` adds `Layer 3 workbench drives rendered package supersession preview control`.
- The test drives source intake, plan approval, execution selection/start, result review, package preview, package construction, package review submit, and supersession preview.
- It proves the request contains only admitted fields.
- It proves forbidden fields are absent.
- It proves `package_supersession_preview_only`, `package_supersession_previewed`, package hashes, immutable package rows, downstream dependency status, and disabled mutation/source/connector/provider/RAG flags render.
- It proves the failed state with `package_supersession_preview_package_review_preview_hash_mismatch`.
- It proves no package supersession commit request, replacement package request, connector dispatch, handoff dispatch, source expansion, or broad downstream lane is triggered by this control.

Headless Chromium passed for `Layer 3 workbench drives rendered package supersession preview control`.

Headed Chromium passed for `Layer 3 workbench drives rendered package supersession preview control`.

## Non-Admission Boundary

This pass does not admit package supersession commit, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement payload generation, replacement package-set creation, replacement namespace review, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, connector-run creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-durable authority.

`package_supersession_commit_enabled` remains false.

No package write, filesystem write, database write, destination write, connector run, provider-public URL, source row, vector index, or credential is created by this rendered control.

## Required Validation

This implementation branch must pass:

```powershell
node --check .\backend\app\review_ui\static\layer3.js
python -m py_compile .\backend\tests\test_layer3_page.py
python -m pytest .\backend\tests\test_layer3_page.py -q
python -m pytest .\backend\tests\test_layer3_api.py -k "package_supersession_preview" -q
npx playwright test e2e/layer3-workbench.spec.js --project=chromium -g "Layer 3 workbench drives rendered package supersession preview control"
npx playwright test e2e/layer3-workbench.spec.js --project=chromium --headed -g "Layer 3 workbench drives rendered package supersession preview control"
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

## Next Posture

After this implementation merges, a current-main sync must record the PR, checks, comments, reviews, reviewThreads, merge commit, validation, and next posture.

The next exact posture is `await_current_main_sync_for_package_supersession_preview_rendered_control`.

After that current-main sync, the next capability decision must remain inside current-main-selected authority. Any package supersession commit, package rebuild, source expansion, RAG/vector, connector/destination, provider-public, auth/security, or full mockup activation requires a separate named freeze before implementation.
