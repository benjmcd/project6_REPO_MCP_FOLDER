# 716 - Corrected Artifact Replacement Manifest Runtime Proof

## Status

Status: implementation proof for `corrected_artifact_replacement_manifest_from_supersession_authority`.

Doc: `716_CORRECTED_ARTIFACT_REPLACEMENT_MANIFEST_RUNTIME_PROOF.md`.

Predecessor current-main sync: `715_CORRECTED_ARTIFACT_REPLACEMENT_MANIFEST_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC.md`.

Runtime branch: `codex/l3-corrected-artifact-manifest-runtime`.

Current-main checkpoint before implementation: `8f57d3e5e82f199f48dceea86ce146b6c653f6c8`.

Selected runtime route: `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-corrected-artifact-set-authority`.

Owner service: `backend/app/services/layer3_replacement_package_artifact_manifest.py`.

API owner: `backend/app/api/layer3.py`.

Durable target: `L3ReplacementPackageArtifactManifest` / `l3_replacement_package_artifact_manifest`.

Required source authority: `L3CorrectedPackageArtifactSet`.

Required upstream replacement authority: `L3ReplacementPackageSetAuthority` with mode `replacement_package_set_authority_from_corrected_artifact_set`.

Required supersession authority: `L3PackageSupersessionCommit` produced by `package_supersession_commit_from_corrected_artifact_set_authority`.

Request mode: `replacement_package_artifact_manifest_from_corrected_artifact_set_authority`.

Operator decision: `record_replacement_package_artifact_manifest_from_corrected_artifact_set_authority`.

Response schema id: `layer3.replacement_package_artifact_manifest_from_corrected_artifact_set_authority.v1`.

Runtime behavior change: `true`.

## Implemented Slice

This runtime adds exactly one server-computed replacement artifact manifest bridge from corrected-artifact supersession authority into existing replacement artifact manifest persistence.

The new request accepts only:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `corrected_package_artifact_set_id`;
- `corrected_artifact_basis_hash`;
- `replacement_package_set_authority_id`;
- `replacement_authority_basis_hash`;
- `package_supersession_commit_id`;
- `package_supersession_commit_basis_hash`; and
- `operator_decision`.

The service derives replacement package set id/hash, replacement package kinds, replacement artifact refs, replacement artifact hashes, verified byte sizes, artifact manifest hash, and authority basis hash server-side from `L3CorrectedPackageArtifactSet`, corrected-artifact `L3ReplacementPackageSetAuthority`, and corrected-artifact `L3PackageSupersessionCommit`.

It reuses the existing `L3ReplacementPackageArtifactManifest` table and the existing internal manifest persistence path. The response redacts replacement artifact refs as `artifact://replacement-package-artifacts/...`; it also redacts the returned `manifest_snapshot` refs and records `raw_artifact_refs_exposed: false`.

## Proof

Targeted validation passed:

```powershell
python -m py_compile .\backend\app\services\layer3_replacement_package_artifact_manifest.py .\backend\app\api\layer3.py
python -m pytest .\backend\tests\test_layer3_replacement_package_artifact_manifest.py -q -k "corrected_artifact_set"
python -m pytest .\backend\tests\test_layer3_api.py -q -k "corrected_artifact_set or openapi_contracts or workbench_error_responses"
```

Observed results:

- targeted `test_layer3_replacement_package_artifact_manifest.py`: `2 passed, 5 deselected`;
- targeted `test_layer3_api.py`: `16 passed, 164 deselected`; and
- py_compile passed.

Coverage added:

- service success from `L3CorrectedPackageArtifactSet`, corrected-artifact `L3ReplacementPackageSetAuthority`, and corrected-artifact `L3PackageSupersessionCommit`;
- redacted replacement artifact refs in response and returned manifest snapshot;
- durable manifest row preserves server-owned raw refs only inside backend persistence;
- same-key replay;
- same-basis/new-key replay;
- forbidden caller-supplied replacement refs and destination URL failure;
- stale corrected artifact basis failure;
- stale replacement authority basis failure;
- stale supersession commit basis failure;
- tampered corrected artifact hash failure;
- API OpenAPI request/response contract exposure;
- API error-envelope behavior for the new route;
- no source `L3OutputPackage` mutation;
- no replacement namespace/output package rows;
- no package activation rows;
- no `ConnectorRun` or `ConnectorRunTarget` creation;
- no package payload rewrite;
- no source expansion; and
- no RAG/vector behavior.

## Non-Admission Boundary

This runtime does not record replacement namespace rows, activate packages, rewrite package payloads, mutate source `L3OutputPackage` rows, invalidate downstream artifacts, re-run handoff/export or delivery, dispatch connectors or destinations, create `ConnectorRun` or `ConnectorRunTarget` rows, use credentials, perform network egress, expose provider-public delivery/use, expose raw public URLs, add source expansion, add RAG/vector or qualitative-hybrid execution, broaden auth/security behavior, activate the full mockup, create frontend-durable authority, add rendered controls, accept caller-supplied arbitrary paths or URLs, accept browser-supplied refs/hashes/bytes, or expose raw local paths.

## Next Posture

After this implementation merges, the next exact posture is `await_current_main_sync_for_corrected_artifact_replacement_manifest_runtime`.
