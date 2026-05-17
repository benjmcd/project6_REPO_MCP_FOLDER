# 712 - Corrected Artifact Package Supersession Commit Runtime Proof

## Status

Status: implementation proof for `server_computed_package_supersession_commit_from_corrected_artifact_replacement_authority`.

Doc: `712_CORRECTED_ARTIFACT_PACKAGE_SUPERSESSION_COMMIT_RUNTIME_PROOF.md`.

Predecessor current-main sync: `711_CORRECTED_ARTIFACT_PACKAGE_REBUILD_DOWNSTREAM_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC.md`.

Runtime branch: `codex/l3-corrected-artifact-supersession-commit`.

Current-main checkpoint before implementation: `4ed1c54693cda3785c3c38d60993cdf49fe0f51d`.

Selected runtime route: `POST /api/v1/layer3/package/supersession/commit-from-corrected-artifact-set-authority`.

Owner service: `backend/app/services/layer3_package_supersession_commit.py`.

API owner: `backend/app/api/layer3.py`.

Durable target: `L3PackageSupersessionCommit` / `l3_package_supersession_commit`.

Required source authority: `L3CorrectedPackageArtifactSet`.

Required upstream replacement authority: `L3ReplacementPackageSetAuthority` with mode `replacement_package_set_authority_from_corrected_artifact_set`.

Request mode: `package_supersession_commit_from_corrected_artifact_set_authority`.

Operator decision: `commit_package_supersession`.

Response schema id: `layer3.package_supersession_commit.v1`.

Runtime behavior change: `true`.

## Implemented Slice

This runtime adds exactly one server-computed commit bridge from corrected-artifact replacement authority into existing package supersession commit persistence.

The new request accepts only:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `corrected_package_artifact_set_id`;
- `corrected_artifact_basis_hash`;
- `replacement_package_set_authority_id`;
- `replacement_authority_basis_hash`; and
- `operator_decision`.

The service derives source package refs/hashes, replacement refs/hashes, downstream dependency hash, package supersession preview hash, and commit basis hash server-side. It reuses the existing `commit_package_supersession` persistence path so the durable table constraint remains compatible with `commit_package_supersession`.

The response redacts source and replacement refs as `artifact://source-output-package/...` and `artifact://package-supersession-commit-replacement/...`; it also redacts the returned `commit_snapshot` payload refs and records `raw_payload_refs_exposed: false`.

## Proof

Targeted validation passed:

```powershell
python -m py_compile .\backend\app\services\layer3_package_supersession_commit.py .\backend\app\api\layer3.py
python -m pytest .\backend\tests\test_layer3_package_supersession_commit.py -q
python -m pytest .\backend\tests\test_layer3_api.py -q -k "supersession_commit_from_corrected_artifact_set or openapi_contracts or package_supersession_commit_contract"
```

Observed results:

- `test_layer3_package_supersession_commit.py`: `4 passed`;
- targeted `test_layer3_api.py`: `12 passed, 165 deselected`; and
- py_compile passed.

Coverage added:

- service success from `L3CorrectedPackageArtifactSet` and corrected-artifact `L3ReplacementPackageSetAuthority`;
- redacted source and replacement refs;
- redacted returned commit snapshot;
- same-key replay;
- same-basis/new-key replay;
- forbidden caller-supplied replacement refs and destination URL failure;
- stale corrected artifact basis failure;
- stale replacement authority basis failure;
- missing replacement authority failure;
- wrong session failure;
- API OpenAPI request/response contract exposure;
- API error-envelope behavior;
- no source `L3OutputPackage` mutation;
- no replacement artifact manifest rows;
- no replacement namespace/output package rows;
- no package activation rows;
- no `ConnectorRun` or `ConnectorRunTarget` creation; and
- no package payload rewrite.

## Non-Admission Boundary

This runtime does not generate replacement artifacts, rewrite package payloads, mutate source `L3OutputPackage` rows, record replacement artifact manifests, record replacement namespace rows, activate packages, invalidate downstream artifacts, re-run handoff/export or delivery, create `ConnectorRun` or `ConnectorRunTarget` rows, use credentials, perform network egress, expose provider-public delivery/use, expose raw public URLs, add source expansion, add RAG/vector or qualitative-hybrid execution, broaden auth/security behavior, activate the full mockup, create frontend-durable authority, add rendered controls, accept caller-supplied arbitrary paths or URLs, accept browser-supplied refs/hashes/bytes, or expose raw local paths.

## Next Posture

After this implementation merges, the next exact posture is `await_current_main_sync_for_corrected_artifact_package_supersession_commit_runtime`.
