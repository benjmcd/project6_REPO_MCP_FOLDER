# 644 - Rendered Replacement Package-Set Authority Control Runtime Proof

## Status

Status: branch-local implementation proof for `rendered_replacement_package_set_authority_control`.

This implementation follows current-main sync doc `643_REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Implementation branch: `codex/l3-rendered-replacement-set-authority-control-2`.

Current-main checkpoint before implementation: `698970d713abfc7e7a786e6f66d8a5010112439f`.

Selected surface: `package_mutation_reconstruction`.

Selected exact operator action: `record_replacement_package_set_authority_after_supersession_preview`.

Selected implementation-entry mode: `rendered_replacement_package_set_authority_control`.

Existing materialization surface: `/api/v1/layer3/package/replacement-artifact/materialize`.

Existing authority surface: `/api/v1/layer3/package/replacement-set/record`.

Owner services:

- `backend/app/services/layer3_replacement_package_materialization.py`;
- `backend/app/services/layer3_replacement_package_set_authority.py`.

Layer 3 placement: Data Structuring & Processing package lifecycle boundary.

## Implemented Slice

The rendered `/review/layer3` package review area now includes a bounded `Record Replacement Set` control and read-only `replacement-package-set-authority-panel`.

The control performs exactly two server-authoritative calls:

1. `POST /api/v1/layer3/package/replacement-artifact/materialize`;
2. `POST /api/v1/layer3/package/replacement-set/record`.

The browser derives the materialization request from existing package supersession preview authority, then derives the replacement package-set authority request only from the server-owned materialization response. It does not accept operator path, ref, hash, byte, payload, destination, connector, source, RAG, or credential edits.

The implementation files are:

- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.css`;
- `backend/app/review_ui/static/layer3.js`;
- `backend/tests/test_layer3_page.py`;
- `e2e/layer3-workbench.spec.js`.

The progress/proof owner files for this pass are:

- `next_milestone_plans/Layer3_planning_docs/644_RENDERED_REPLACEMENT_PACKAGE_SET_AUTHORITY_CONTROL_RUNTIME_PROOF.md`;
- `next_milestone_plans/layer3_progress_board.md`;
- `next_milestone_plans/layer3_progress_manifest.json`;
- `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `tools/l3-progress-check.py`.

No backend route, DTO, response model, database model, migration, materialization service, or replacement package-set authority service behavior changed in this pass.

## Request Boundary

The materialization request submits only:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `package_supersession_preview_hash`;
- `source_package_set_hash`;
- `source_output_package_ids`;
- `source_package_kinds`;
- `source_payload_refs`;
- `source_payload_hashes`;
- `operator_decision`.

The replacement package-set authority request submits only:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `source_package_set_hash`;
- `source_output_package_ids`;
- `source_package_kinds`;
- `source_payload_refs`;
- `source_payload_hashes`;
- `replacement_package_set_id`;
- `replacement_package_set_hash`;
- `replacement_package_kinds`;
- `replacement_payload_refs`;
- `replacement_payload_hashes`;
- `authority_basis_hash`;
- `operator_decision`.

The browser implementation owners are `replacementPackageArtifactMaterializationPayload` and `replacementPackageSetAuthorityPayload`. Browser state is transient request assembly only and is not durable authority.

The rendered control does not submit package payload bytes, browser-provided replacement refs or hashes, package row mutation fields, package supersession commit fields, arbitrary destination ids or URLs, connector ids, connector run ids, source expansion fields, RAG/vector fields, auth/security fields, hidden LLM fields, retry/rerun/cancel fields, or frontend-durable state.

## Rendered State

The rendered state uses:

- `REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_MODE = rendered_replacement_package_set_authority_control`;
- `REPLACEMENT_PACKAGE_SET_AUTHORITY_USE_CASE = operator_records_replacement_package_set_authority_from_server_owned_materialization`;
- `REPLACEMENT_PACKAGE_SET_AUTHORITY_RESPONSE_AUTHORITY = State.replacementPackageSetAuthority`;
- `REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_OPERATOR_DECISION = materialize_replacement_package_artifacts_from_supersession_preview`;
- `REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION = record_replacement_package_set_authority`.

The panel renders unavailable, ready, recording, materialized, recorded, and failed states from response-safe data.

The display helper `safePackagePayloadRefForDisplay` redacts raw local path-shaped source and replacement payload refs as `redacted_local_payload_ref`.

The panel displays only response-safe status, ids, hashes, package kind rows, disabled capability flags, deferred downstream locks, and redacted failure codes. It does not expose package payload bytes or create durable frontend authority.

## Proof

Static proof:

- `backend/tests/test_layer3_page.py` asserts the rendered button, panel, mode, JavaScript payload builders, endpoint calls, operator decision, and CSS selectors.

API proof:

- `backend/tests/test_layer3_api.py -k "replacement_package_artifact_materialization or replacement_package_set_authority"` continues to prove the existing server-authoritative materialization and authority APIs, idempotency, failure guardrails, and disabled side effects without backend widening.

Rendered E2E proof:

- `e2e/layer3-workbench.spec.js` adds `Layer 3 workbench records rendered replacement package-set authority control`.
- The test drives source intake, plan approval, execution selection/start, result review, package preview, package construction, package review submit, supersession preview, server-owned replacement artifact materialization, and replacement package-set authority recording.
- It proves both rendered request bodies contain only admitted fields.
- It proves forbidden fields are absent.
- It proves materialization writes only through the admitted server-owned materialization endpoint and returns governed replacement request fields.
- It proves the authority record is persisted by `/api/v1/layer3/package/replacement-set/record`.
- It proves the rendered panel redacts local path-shaped refs and displays recorded/failure state.
- It proves the rendered control does not trigger handoff/export, supersession commit, replacement artifact manifest, replacement namespace, connector dispatch, source expansion, or broad downstream runtime requests.

## Non-Admission Boundary

This pass does not admit package supersession commit, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement output package namespace rows, replacement artifact manifest recording, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, connector-run creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-durable authority.

No browser/operator path editing, caller-supplied arbitrary path/URL, package payload byte edit, replacement payload byte edit, destination write, connector run, provider-public URL, source row, vector index, credential, or frontend durable authority is created by this rendered control.

## Required Validation

This implementation branch must pass:

```powershell
node --check .\backend\app\review_ui\static\layer3.js
python -m py_compile .\backend\tests\test_layer3_page.py
python -m pytest .\backend\tests\test_layer3_page.py -q
python -m pytest .\backend\tests\test_layer3_api.py -k "replacement_package_artifact_materialization or replacement_package_set_authority" -q
npx playwright test e2e/layer3-workbench.spec.js --project=chromium -g "Layer 3 workbench records rendered replacement package-set authority control"
npx playwright test e2e/layer3-workbench.spec.js --project=chromium --headed -g "Layer 3 workbench records rendered replacement package-set authority control"
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

## Next Posture

After this implementation merges, a current-main sync must record the PR, checks, comments, reviews, reviewThreads, merge commit, validation, and next posture.

The next exact posture is `await_current_main_sync_for_rendered_replacement_package_set_authority_control`.

After that current-main sync, the next capability decision must remain inside current-main-selected authority. Any package supersession commit, package rebuild, source expansion, RAG/vector, connector/destination, provider-public, auth/security, or full mockup activation requires a separate named freeze before implementation.
