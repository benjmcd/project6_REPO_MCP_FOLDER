# 654 - Replacement Package Artifact Manifest Record-From-Authority Runtime

## Status

Status: branch-local runtime implementation for `server_computed_replacement_package_artifact_manifest_record_from_authority`.

Doc: `654_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_RECORD_FROM_AUTHORITY_RUNTIME.md`.

Predecessor doc: `653_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUEST_AUTHORITY_SOURCE_SELECTION_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `60dba1a6c65d21d668099e5ca704e0c7438aa3a5`.

Branch: `codex/l3-replacement-manifest-record-authority-runtime`.

Selected surface: `package_mutation_reconstruction`.

Implemented route: `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`.

Owner service: `backend/app/services/layer3_replacement_package_artifact_manifest.py`.

Request DTO: `Layer3ReplacementPackageArtifactManifestFromAuthorityRequest`.

Response DTO: `Layer3ReplacementPackageArtifactManifestResponse`.

Response schema id: `layer3.replacement_package_artifact_manifest_from_authority.v1`.

Runtime status in this pass: `implemented_branch_local`.

Implementation result: `server_computed_replacement_package_artifact_manifest_record_from_authority_runtime_implemented`.

## Implemented Runtime

This pass implements the current-main-selected request-authority source for replacement package artifact manifest recording.

The new route accepts only stable server-owned authority identifiers and three existing-row basis hashes:

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

The service resolves the existing replacement artifact materialization row, replacement package-set authority row, and package supersession commit row server-side. It verifies their session, plan, pass, reconciliation, source-package vectors, replacement-package vectors, and basis hashes before computing `artifact_manifest_hash`, computing the manifest `authority_basis_hash`, verifying artifact byte sizes, and recording the existing durable `L3ReplacementPackageArtifactManifest` row.

The implementation reuses the existing manifest persistence model and preserves the existing caller-supplied `/api/v1/layer3/package/replacement-artifact/manifest/record` contract. The new route returns redacted `artifact://replacement-package-artifacts/{manifest_id}/{package_kind}` refs in the response and redacted manifest snapshot while preserving raw server-owned artifact refs only inside the durable backend row.

## Positive Proof

The targeted backend proof covers:

- OpenAPI request schema for `/package/replacement-artifact/manifest/record-from-authority`;
- workbench error envelope registration for the new route;
- API boundary monkeypatch proof for `record_replacement_package_artifact_manifest_from_authority`;
- successful server-computed manifest record from materialization, replacement authority, and supersession commit authority;
- redacted response refs and redacted response manifest snapshot;
- computed manifest hash and computed authority basis hash;
- idempotent same-key replay;
- same computed basis with new `client_request_id` returning existing manifest status;
- no connector run or connector-run-target creation;
- no replacement namespace row;
- no `L3OutputPackage` row mutation;
- no package payload write;
- no provider-public delivery/use;
- no source expansion;
- no RAG/vector behavior.

## Negative Proof

The targeted fail-closed proof covers:

- missing required fields;
- forbidden browser-supplied replacement refs;
- forbidden browser-supplied `artifact_manifest_hash`;
- forbidden browser-supplied manifest `authority_basis_hash`;
- forbidden destination URL;
- unsupported operator decision;
- missing materialization row;
- stale `materialization_basis_hash`;
- stale `replacement_authority_basis_hash`;
- stale `package_supersession_commit_basis_hash`;
- tampered replacement artifact hash mismatch.

## Non-Admission Boundary

This runtime does not add rendered UI controls, replacement namespace rows, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector or destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied artifact refs, browser-supplied replacement hashes, browser-supplied manifest hashes, browser-supplied byte sizes, browser-supplied package bytes, browser-supplied replacement bytes, or browser-supplied artifact bytes.

## Validation

Branch-local validation:

```powershell
python -m py_compile .\backend\app\services\layer3_replacement_package_artifact_manifest.py .\backend\app\api\layer3.py .\backend\tests\test_layer3_api.py
python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_package_openapi_contracts .\backend\tests\test_layer3_api.py::test_layer3_json_workbench_error_openapi_contracts .\backend\tests\test_layer3_api.py::test_layer3_replacement_package_artifact_manifest_from_authority_api_boundary_returns_workbench_error_envelope .\backend\tests\test_layer3_api.py::test_layer3_api_replacement_package_artifact_manifest_record_from_authority_computes_and_redacts_refs .\backend\tests\test_layer3_api.py::test_layer3_api_replacement_package_artifact_manifest_record_from_authority_prechecks_fail_closed -q
```

This branch must still pass final control validation before PR:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

No headed/headless E2E run is required in this pass because no rendered behavior changed.

## Next Posture

After merge, the next required action is `current_main_sync_replacement_package_artifact_manifest_record_from_authority_runtime`.

After current-main sync, the next exact Layer 3 posture is to determine whether the rendered replacement package artifact manifest control can be safely admitted against the new server-computed request-authority route, or whether another package lifecycle guardrail is still the higher-value current-main-selected step.
