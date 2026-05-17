# 662 - Rendered Replacement Package Namespace Control Runtime Proof

## Status

Status: branch-local implementation proof for `rendered_replacement_package_namespace_control`.

This implementation follows current-main sync doc `661_RENDERED_REPLACEMENT_PACKAGE_NAMESPACE_CONTROL_FREEZE_CURRENT_MAIN_SYNC.md`.

Implementation branch: `codex/l3-rendered-namespace-control-runtime`.

Current-main checkpoint before implementation: `c3b48c0b602e9527fed3be567d7eeaab8cebbce3`.

Selected surface: `package_mutation_reconstruction`.

Selected exact operator action: `record_replacement_package_namespace_row`.

Selected implementation-entry mode: `rendered_replacement_package_namespace_control`.

Existing backend surface: `POST /api/v1/layer3/package/replacement-namespace/record`.

Owner service already live: `backend/app/services/layer3_replacement_package_namespace.py`.

Server runtime mode already live: `replacement_package_namespace_rows`.

Source gate: `131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE`.

Layer 3 placement: Data Structuring & Processing package lifecycle boundary.

## Implemented Slice

The rendered `/review/layer3` package review area now includes a bounded `Record Namespace` control and read-only `replacement-package-namespace-panel`.

The control performs exactly one server-authoritative call:

1. `POST /api/v1/layer3/package/replacement-namespace/record`.

The browser request is assembled only from existing server response authority:

- `State.replacementPackageArtifactManifest`;
- `State.replacementPackageSetAuthority`;
- `State.packageSupersessionCommit`;
- existing source package row authority.

The implementation files are:

- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.css`;
- `backend/app/review_ui/static/layer3.js`;
- `backend/app/services/layer3_replacement_package_namespace.py`;
- `backend/tests/test_layer3_page.py`;
- `backend/tests/test_layer3_replacement_package_namespace.py`;
- `e2e/layer3-workbench.spec.js`.

The progress/proof owner files for this pass are:

- `next_milestone_plans/Layer3_planning_docs/662_RENDERED_REPLACEMENT_PACKAGE_NAMESPACE_CONTROL_RUNTIME_PROOF.md`;
- `next_milestone_plans/layer3_progress_board.md`;
- `next_milestone_plans/layer3_progress_manifest.json`;
- `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `tools/l3-progress-check.py`.

No backend route, DTO, response model, database model, migration, package rebuild service, package payload write service, source expansion service, connector service, provider-public service, RAG/vector service, auth/security behavior, or frontend-durable authority changed in this pass.

The only backend service alignment is inside `backend/app/services/layer3_replacement_package_namespace.py`: the namespace service now validates response-safe `artifact://replacement-package-artifacts/{manifest_id}/{package_kind}` refs while continuing to verify artifact hashes against server-held manifest artifact authority. This preserves the raw local path boundary for the rendered control.

## Request Boundary

The rendered namespace control submits only:

- `client_request_id`;
- `session_id`;
- `replacement_artifact_manifest_id`;
- `replacement_package_set_authority_id`;
- `package_supersession_commit_id`;
- `source_output_package_id`;
- `package_kind`;
- `package_schema_id`;
- `artifact_ref`;
- `artifact_hash`;
- `authority_basis_hash`;
- `operator_decision`.

The browser implementation owner is `replacementPackageNamespacePayload`.

The rendered status/history projection owner is `renderReplacementPackageNamespacePanel`.

The rendered control does not submit browser-supplied package bytes, replacement bytes, artifact bytes, raw local paths, arbitrary artifact refs, arbitrary hashes, arbitrary URLs, arbitrary destination ids, package rebuild fields, package payload rewrite fields, source `L3OutputPackage` mutation fields, connector ids, connector run ids, provider-public fields, source expansion fields, RAG/vector fields, auth/security fields, hidden LLM fields, retry/rerun/cancel fields, or frontend-durable state.

## Rendered State

The rendered state uses:

- `REPLACEMENT_PACKAGE_NAMESPACE_RENDERED_MODE = rendered_replacement_package_namespace_control`;
- `REPLACEMENT_PACKAGE_NAMESPACE_USE_CASE = operator_records_replacement_package_namespace_row_from_manifest_authority`;
- `REPLACEMENT_PACKAGE_NAMESPACE_RESPONSE_AUTHORITY = State.replacementPackageNamespace`;
- `REPLACEMENT_PACKAGE_NAMESPACE_OPERATOR_DECISION = record_replacement_package_namespace`.

Rendered selectors: `#replacement-package-namespace-submit` and `#replacement-package-namespace-panel`.

The panel renders unavailable, ready, recording, recorded, already-recorded, and failed states from response-safe data.

The panel displays only response-safe status, schema id, namespace ids, selected package kind, package schema id, source package id, response-safe artifact ref, artifact hash, basis hashes, disabled capability flags, deferred downstream locks, and redacted failure codes. It does not expose raw local paths, package payload bytes, browser-provided arbitrary refs/hashes/bytes, or durable frontend authority.

## Proof

Static proof:

- `backend/tests/test_layer3_page.py` asserts the rendered button, panel, rendered mode, JavaScript payload builder, endpoint call, operator decision, ready state, panel renderer, and CSS selectors.
- `backend/tests/test_layer3_replacement_package_namespace.py` asserts response-safe namespace artifact refs remain valid while the service still verifies hashes against server-owned manifest artifact authority.

Rendered E2E proof:

- `e2e/layer3-workbench.spec.js` adds `Layer 3 workbench records rendered replacement package namespace control`.
- The test drives source intake, plan approval, execution selection/start, result review, package preview, package construction, package review submit, supersession preview, replacement package-set authority, package supersession commit, replacement package artifact manifest recording, and replacement package namespace recording.
- It proves the rendered request body contains only admitted fields.
- It proves forbidden fields are absent.
- It proves failure-state projection with `replacement_package_namespace_authority_basis_hash_mismatch`.
- It proves the namespace row is persisted by `/api/v1/layer3/package/replacement-namespace/record`.
- It proves the rendered request uses response-safe `artifact://replacement-package-artifacts/...` refs rather than raw local paths.
- It proves disabled side-effect flags remain false.
- It proves the rendered control does not trigger handoff/export, connector dispatch, source expansion, package payload write, package row mutation, provider-public delivery/use, RAG/vector, or broad downstream runtime requests.

## Non-Admission Boundary

This pass does not admit package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, connector-run creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-durable authority.

No browser/operator path editing, caller-supplied arbitrary path/URL, browser file read, package payload byte edit, replacement payload byte edit, destination write, connector run, provider-public URL, source row mutation, vector index, credential, or frontend durable authority is created by this rendered control.

## Required Validation

This implementation branch must pass:

```powershell
node --check .\backend\app\review_ui\static\layer3.js
python -m py_compile .\backend\tests\test_layer3_page.py
python -m pytest .\backend\tests\test_layer3_page.py .\backend\tests\test_layer3_replacement_package_namespace.py -q
npx playwright test e2e/layer3-workbench.spec.js --project=chromium -g "replacement package namespace"
npx playwright test e2e/layer3-workbench.spec.js --project=chromium --headed -g "replacement package namespace"
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

## Next Posture

After this implementation merges, a current-main sync must record the PR, checks, comments, reviews, reviewThreads, merge commit, validation, and next posture.

The next exact posture is `await_current_main_sync_for_rendered_replacement_package_namespace_control_runtime`.

After that current-main sync, the next capability decision must remain inside current-main-selected authority. Any package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector, auth/security, full mockup activation, or frontend-durable authority requires a separate named freeze before implementation.
