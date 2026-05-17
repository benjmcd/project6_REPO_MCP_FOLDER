# 658 - Rendered Replacement Package Artifact Manifest Control Runtime Proof

## Status

Status: branch-local implementation proof for `rendered_replacement_package_artifact_manifest_control`.

This implementation follows current-main sync doc `657_RENDERED_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_CONTROL_FREEZE_CURRENT_MAIN_SYNC.md`.

Implementation branch: `codex/l3-rendered-manifest-control-runtime`.

Current-main checkpoint before implementation: `44d5598890625ee0c4dda880ea6e3cb86a2b22aa`.

Selected surface: `package_mutation_reconstruction`.

Selected exact operator action: `record_replacement_package_artifact_manifest_from_authority`.

Selected implementation-entry mode: `rendered_replacement_package_artifact_manifest_control`.

Existing backend surface: `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`.

Owner service already live: `backend/app/services/layer3_replacement_package_artifact_manifest.py`.

Server runtime mode already live: `server_computed_replacement_package_artifact_manifest_record_from_authority`.

Source gate: `652_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUEST_AUTHORITY_SOURCE_SELECTION_FREEZE`.

Layer 3 placement: Data Structuring & Processing package lifecycle boundary.

## Implemented Slice

The rendered `/review/layer3` package review area now includes a bounded `Record Manifest` control and read-only `replacement-package-artifact-manifest-panel`.

The control performs exactly one server-authoritative call:

1. `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`.

The browser request is assembled only from existing server response authority:

- `State.replacementPackageArtifactMaterialization`;
- `State.replacementPackageSetAuthority`;
- `State.packageSupersessionCommit`.

The implementation files are:

- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.css`;
- `backend/app/review_ui/static/layer3.js`;
- `backend/tests/test_layer3_page.py`;
- `e2e/layer3-workbench.spec.js`.

The progress/proof owner files for this pass are:

- `next_milestone_plans/Layer3_planning_docs/658_RENDERED_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_CONTROL_RUNTIME_PROOF.md`;
- `next_milestone_plans/layer3_progress_board.md`;
- `next_milestone_plans/layer3_progress_manifest.json`;
- `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `tools/l3-progress-check.py`.

No backend route, DTO, response model, service, database model, migration, package row mutation service, package payload write service, source expansion service, connector service, provider-public service, RAG/vector service, auth/security behavior, or frontend-durable authority changed in this pass.

## Request Boundary

The rendered manifest control submits only:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `replacement_artifact_materialization_id`;
- `materialization_basis_hash`;
- `replacement_package_set_authority_id`;
- `replacement_authority_basis_hash`;
- `package_supersession_commit_id`;
- `package_supersession_commit_basis_hash`;
- `operator_decision`.

The browser implementation owner is `replacementPackageArtifactManifestPayload`.

The rendered status/history projection owner is `renderReplacementPackageArtifactManifestPanel`.

The rendered control does not submit browser-supplied artifact refs, replacement refs, replacement hashes, verified byte sizes, artifact manifest hashes, authority basis hashes, manifest snapshots, package payload bytes, package rebuild fields, package payload rewrite fields, replacement namespace fields, arbitrary destination ids or URLs, connector ids, connector run ids, provider-public fields, source expansion fields, RAG/vector fields, auth/security fields, hidden LLM fields, retry/rerun/cancel fields, or frontend-durable state.

## Rendered State

The rendered state uses:

- `REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_RENDERED_MODE = rendered_replacement_package_artifact_manifest_control`;
- `REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_USE_CASE = operator_records_replacement_package_artifact_manifest_from_server_computed_authority`;
- `REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_RESPONSE_AUTHORITY = State.replacementPackageArtifactManifest`;
- `REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_OPERATOR_DECISION = record_replacement_package_artifact_manifest_from_authority`.

The panel renders unavailable, ready, recording, recorded, already-recorded, and failed states from response-safe data.

The panel displays only response-safe status, schema id, ids, basis hashes, redacted `artifact://replacement-package-artifacts/...` refs, verified byte sizes, disabled capability flags, deferred downstream locks, and redacted failure codes. It does not expose raw local paths, package payload bytes, browser-provided refs/hashes/bytes, or durable frontend authority.

## Proof

Static proof:

- `backend/tests/test_layer3_page.py` asserts the rendered button, panel, rendered mode, JavaScript payload builder, endpoint call, operator decision, ready state, panel renderer, and CSS selectors.

Rendered E2E proof:

- `e2e/layer3-workbench.spec.js` adds `Layer 3 workbench records rendered replacement package artifact manifest control`.
- The test drives source intake, plan approval, execution selection/start, result review, package preview, package construction, package review submit, supersession preview, replacement package-set authority, package supersession commit, and replacement package artifact manifest recording.
- It proves the rendered request body contains only admitted fields.
- It proves forbidden fields are absent.
- It proves failure-state projection with `replacement_package_artifact_manifest_from_authority_materialization_basis_hash_mismatch`.
- It proves the manifest record is persisted by `/api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`.
- It proves returned refs are redacted `artifact://replacement-package-artifacts/...` refs rather than raw local paths.
- It proves disabled side-effect flags remain false.
- It proves the rendered control does not trigger handoff/export, direct manifest record, replacement namespace, connector dispatch, source expansion, package payload write, package row mutation, provider-public delivery/use, RAG/vector, or broad downstream runtime requests.

## Non-Admission Boundary

This pass does not admit package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement output package namespace rows, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, connector-run creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-durable authority.

No browser/operator path editing, caller-supplied arbitrary path/URL, browser file read, package payload byte edit, replacement payload byte edit, destination write, connector run, provider-public URL, source row, vector index, credential, or frontend durable authority is created by this rendered control.

## Required Validation

This implementation branch must pass:

```powershell
node --check .\backend\app\review_ui\static\layer3.js
python -m py_compile .\backend\tests\test_layer3_page.py
python -m pytest .\backend\tests\test_layer3_page.py -q
npx playwright test e2e/layer3-workbench.spec.js --project=chromium -g "replacement package artifact manifest"
npx playwright test e2e/layer3-workbench.spec.js --project=chromium --headed -g "replacement package artifact manifest"
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

## Next Posture

After this implementation merges, a current-main sync must record the PR, checks, comments, reviews, reviewThreads, merge commit, validation, and next posture.

The next exact posture is `await_current_main_sync_for_rendered_replacement_package_artifact_manifest_control_runtime`.

After that current-main sync, the next capability decision must remain inside current-main-selected authority. Any replacement namespace row creation, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector, auth/security, full mockup activation, or frontend-durable authority requires a separate named freeze before implementation.
