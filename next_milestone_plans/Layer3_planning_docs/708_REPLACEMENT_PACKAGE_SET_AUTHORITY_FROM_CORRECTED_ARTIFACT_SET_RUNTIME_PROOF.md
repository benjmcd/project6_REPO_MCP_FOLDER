# 708 - Replacement Package Set Authority From Corrected Artifact Set Runtime Proof

## Status

Status: branch-local implementation proof for `replacement_package_set_authority_from_corrected_artifact_set_runtime`.

Doc: `708_REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_RUNTIME_PROOF.md`.

Predecessor current-main sync: `707_PACKAGE_REBUILD_FROM_CORRECTED_ARTIFACT_SET_ENTRY_FREEZE_CURRENT_MAIN_SYNC.md`.

Runtime branch: `codex/l3-corrected-artifact-replacement-authority-runtime`.

Current-main checkpoint before implementation: `94886ea4b787ea1696f97ff1e31aca49a7891379`.

Selected implementation posture: `implement_replacement_package_set_authority_from_corrected_artifact_set_after_entry_freeze_sync`.

Runtime behavior change: true.

## Implemented Runtime Slice

This branch implements only the admitted replacement package-set authority bridge from an existing corrected package artifact set:

- route: `POST /api/v1/layer3/package/replacement-set/record-from-corrected-artifact-set`;
- owner service: `backend/app/services/layer3_replacement_package_set_authority.py`;
- API owner: `backend/app/api/layer3.py`;
- durable target: `L3ReplacementPackageSetAuthority` / `l3_replacement_package_set_authority`;
- source authority: `L3CorrectedPackageArtifactSet` / `l3_corrected_package_artifact_set`;
- request mode: `replacement_package_set_authority_from_corrected_artifact_set`;
- operator decision: `record_replacement_package_set_authority`; and
- response schema id: `layer3.replacement_package_set_authority.v1`.

The new API accepts only identity and basis fields for the corrected artifact set authority. It validates `corrected_package_artifact_set_id`, `corrected_artifact_basis_hash`, session, plan, pass, reconciliation, and `source_package_set_hash`; derives replacement package-set id, hash, kinds, payload refs, and payload hashes server-side from the corrected artifact set authority; computes the replacement authority basis hash server-side; and records or replays `L3ReplacementPackageSetAuthority` without widening the existing table constraint.

## Proof Coverage

Targeted proof covers:

- successful replacement package-set authority recording from `L3CorrectedPackageArtifactSet`;
- response redaction for source and replacement payload refs, with no raw local path exposure;
- same-key/same-basis replay;
- same-basis/new-key replay;
- same-key/different-basis failure through fail-closed basis validation;
- stale corrected artifact basis hash failure;
- missing corrected artifact set failure;
- wrong session and source package basis failure;
- forbidden package bytes, replacement refs, destination URL, RAG/vector, auth/security, and adjacent payload fields failing closed;
- OpenAPI request/response contract exposure;
- API error-envelope behavior; and
- no source `L3OutputPackage` row mutation, no replacement artifact manifest rows, no replacement namespace rows, and no package activation rows.

Validation run before PR:

- `python -m py_compile .\backend\app\services\layer3_replacement_package_set_authority.py .\backend\app\api\layer3.py .\backend\tests\test_layer3_replacement_package_set_authority.py .\backend\tests\test_layer3_api.py` passed;
- `python -m pytest .\backend\tests\test_layer3_replacement_package_set_authority.py -q` passed with `4 passed`;
- `python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_package_openapi_contracts .\backend\tests\test_layer3_api.py::test_layer3_replacement_package_set_from_corrected_artifact_set_api_boundary_returns_workbench_error_envelope -q` passed with `2 passed`.

## Boundary Still Blocked

This runtime does not implement direct source `L3OutputPackage` row mutation, package payload rewrite, package activation, downstream invalidation, handoff/export rerun, replacement namespace row creation, replacement artifact manifest recording, package supersession commit, connector/destination dispatch, `ConnectorRun` creation, `ConnectorRunTarget` creation, credentials, external network egress, provider-public delivery/use, raw public URL exposure, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, raw local path exposure, hidden LLM planning, or rendered UI authority.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_replacement_package_set_authority_from_corrected_artifact_set_runtime`.

After sync, the next pass should decide whether existing package supersession commit, replacement artifact manifest, namespace, activation, and downstream active-authority lanes already satisfy the corrected-artifact rebuild path, or whether a separate current-main-admitted bridge/freeze is required for the next exact missing posture.
