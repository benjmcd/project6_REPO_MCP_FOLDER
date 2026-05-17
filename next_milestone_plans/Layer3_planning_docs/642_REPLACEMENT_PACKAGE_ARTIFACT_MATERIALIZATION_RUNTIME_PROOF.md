# 642 - Replacement Package Artifact Materialization Runtime Proof

## Status

Status: runtime implementation proof for `server_owned_replacement_package_artifact_materialization_request_source`.

Doc: `642_REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_RUNTIME_PROOF.md`.

Implementation-entry freeze: `640_REPLACEMENT_PACKAGE_SET_REQUEST_SOURCE_AUTHORITY_SELECTION_FREEZE.md`.

Freeze current-main sync: `641_REPLACEMENT_PACKAGE_SET_REQUEST_SOURCE_AUTHORITY_SELECTION_CURRENT_MAIN_SYNC.md`.

Runtime branch: `codex/l3-replacement-materialization-source`.

Current-main checkpoint before implementation: `e98bab8ae624b41b40a9c9c0149f5304690e457c`.

Selected implementation action: `implement_server_owned_replacement_package_artifact_materialization_request_source_after_selection_sync`.

Selected request-source authority: `server_owned_replacement_package_artifact_materialization_from_supersession_preview`.

Selected operator decision: `materialize_replacement_package_artifacts_from_supersession_preview`.

Runtime status after implementation: `replacement_package_artifact_materialization_runtime_implemented_branch_local`.

Layer 3 placement: Data Structuring & Processing package lifecycle boundary.

Live behavior change in this pass: true, limited to the admitted server-owned replacement artifact materialization request source.

## Implemented Runtime Slice

This pass implements exactly the runtime tranche admitted by doc `640` and synced by doc `641`:

- service `backend/app/services/layer3_replacement_package_materialization.py`;
- route/model wiring in `backend/app/api/layer3.py`;
- durable receipt model/table `l3_replacement_package_artifact_materialization`;
- Alembic migration `backend/alembic/versions/0031_layer3_replacement_package_materialization.py`;
- readiness/action-contract exposure through `backend/app/services/layer3_bootstrap_contract.py`, `backend/app/services/layer3_readiness_contract.py`, `backend/app/services/layer3_state_action_contract.py`, `backend/app/services/layer3_state_model_contract.py`, and `backend/app/services/layer3_workbench.py`; and
- targeted API/backend proof in `backend/tests/test_layer3_api.py`.

No rendered write/status UI was changed in this pass, so headed/headless E2E proof was not required for rendered behavior.

## Runtime Contract Proven

The materialization route is:

`POST /api/v1/layer3/package/replacement-artifact/materialize`

The schema id is `layer3.replacement_package_artifact_materialization.v1`.

The admitted mode is `server_owned_replacement_package_artifact_materialization_request_source`.

The admitted operator decision is `materialize_replacement_package_artifacts_from_supersession_preview`.

The service requires existing session, plan, pass, reconciliation, package-construction provenance, package supersession preview hash, source package set hash, source package ids/kinds/refs/hashes, and immutable source package payload files.

The service writes deterministic replacement artifacts only under the server-owned `replacement-package-artifacts` namespace rooted at `settings.artifact_storage_dir/layer3/replacement-package-artifacts`.

The API response returns the exact downstream request-source fields required by `/api/v1/layer3/package/replacement-set/record`: `replacement_package_set_id`, `replacement_package_set_hash`, `replacement_package_kinds`, `replacement_payload_refs`, `replacement_payload_hashes`, and `authority_basis_hash`.

API responses may carry server-owned replacement artifact refs for subsequent server calls. No rendered UI was changed, and raw local paths are not newly exposed in rendered UI.

## Lifecycle, Idempotency, And Failure Proof

The targeted backend proof covers:

- `test_layer3_api_replacement_package_artifact_materialization_writes_server_owned_artifacts_only`;
- `test_layer3_api_replacement_package_artifact_materialization_prechecks_fail_closed`;
- `test_layer3_replacement_package_artifact_materialization_api_boundary_returns_workbench_error_envelope`;
- `test_layer3_package_openapi_contracts`;
- `test_layer3_bootstrap_readiness_openapi_contracts`;
- `test_layer3_json_workbench_error_openapi_contracts`;
- materialization success from existing package supersession preview/source package authority;
- deterministic server-owned replacement artifact writes;
- same `client_request_id` plus same basis returning the same materialization receipt as `already_materialized`;
- same `client_request_id` plus different basis failing closed as `replacement_package_artifact_materialization_client_request_conflict`;
- same basis plus a new `client_request_id` returning the existing materialization status instead of duplicate output;
- stale package supersession preview hash failing closed;
- stale source package-set hash failing closed;
- stale source payload hash failing closed;
- missing source package payload ref failing closed;
- unsupported operator decision failing closed;
- browser-provided package payload, replacement refs, and arbitrary destination URL fields failing closed;
- existing `L3OutputPackage` rows unchanged;
- existing source package payload files unchanged;
- no replacement package-set authority, package supersession commit, replacement artifact manifest, or replacement namespace row recorded by materialization itself; and
- database counts proving no `ConnectorRun` or `ConnectorRunTarget` side effects.

## Non-Admission Boundary

This implementation does not add rendered replacement package-set authority control, package supersession commit control, package row mutation, source `L3OutputPackage` row mutation, source package payload rewrite, browser-provided package bytes, browser-provided replacement refs/hashes, arbitrary caller-supplied local paths or URLs, replacement output package namespace rows, replacement artifact manifest recording before replacement authority/commit exist, connector or destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, provider-public delivery/use, raw public URL exposure, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, or frontend-durable authority.

## Validation

The implementation-bearing branch must pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
python -m py_compile .\backend\app\services\layer3_replacement_package_materialization.py .\backend\app\api\layer3.py .\backend\app\models\models.py .\backend\app\services\layer3_bootstrap_contract.py .\backend\app\services\layer3_readiness_contract.py .\backend\app\services\layer3_state_action_contract.py .\backend\app\services\layer3_state_model_contract.py .\backend\app\services\layer3_workbench.py .\backend\alembic\versions\0031_layer3_replacement_package_materialization.py .\backend\tests\test_layer3_api.py
python -m pytest .\backend\tests\test_layer3_api.py -k "replacement_package_artifact_materialization or package_openapi_contracts or bootstrap_readiness_openapi_contracts or json_workbench_error_openapi_contracts" -q
git diff --check
```

## Next Posture

The next whole-project posture after this runtime proof merges is `await_current_main_sync_for_replacement_package_artifact_materialization_runtime`.

After current-main sync, the next implementation-bearing pass may resume `rendered_replacement_package_set_authority_control` using the materialization output as governed request-source authority. Package supersession commit control, package row mutation, source expansion, RAG/vector behavior, provider-public delivery/use, connector/destination dispatch, auth/security behavior, full mockup activation, and frontend-durable authority remain blocked unless separately selected and frozen.
