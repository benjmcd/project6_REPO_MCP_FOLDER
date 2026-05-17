# 720 - Corrected Artifact Replacement Namespace Runtime Proof

## Status

Status: branch-local runtime proof for `corrected_artifact_replacement_namespace_runtime`.

Doc: `720_CORRECTED_ARTIFACT_REPLACEMENT_NAMESPACE_RUNTIME_PROOF.md`.

Predecessor sync doc: `719_CORRECTED_ARTIFACT_REPLACEMENT_NAMESPACE_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC.md`.

Runtime branch: `codex/l3-corrected-artifact-namespace-runtime`.

Current-main checkpoint before runtime branch: `3232c2ad9b046091089eb15d3e98fbcb200e39e0`.

Implemented runtime: `server_computed_replacement_namespace_from_corrected_artifact_manifest_authority`.

Runtime route: `POST /api/v1/layer3/package/replacement-namespace/record-from-corrected-artifact-manifest-authority`.

Owner service: `backend/app/services/layer3_replacement_package_namespace.py`.

API owner: `backend/app/api/layer3.py`.

Durable target: `L3ReplacementOutputPackage` / `l3_replacement_output_package`.

Source authority: `L3CorrectedPackageArtifactSet`.

Replacement authority: `L3ReplacementPackageSetAuthority`.

Supersession authority: `L3PackageSupersessionCommit`.

Manifest authority: `L3ReplacementPackageArtifactManifest`.

Request mode: `replacement_package_namespace_from_corrected_artifact_manifest_authority`.

Operator decision: `record_replacement_package_namespace_from_corrected_artifact_manifest_authority`.

Response schema id: `layer3.replacement_package_namespace_from_corrected_artifact_manifest_authority.v1`.

Runtime behavior change: `true`.

## Runtime Behavior

The branch implements the exact Doc 719 freeze slice. The new route accepts only authority ids and basis hashes for the corrected-artifact package chain, loads the corrected artifact set, corrected-artifact replacement package-set authority, corrected-artifact supersession commit, and corrected-artifact replacement artifact manifest, then derives the complete replacement namespace set server-side.

For each package kind, the runtime derives:

- source output package id;
- package kind;
- canonical package schema id;
- response-safe replacement artifact ref;
- verified replacement artifact hash;
- stable authority basis hash; and
- deterministic per-kind row `client_request_id` from the top-level request id and package kind.

Because `l3_replacement_output_package.client_request_id` is unique per row, the bridge uses deterministic per-kind row idempotency keys while keeping the authority basis stable for same-basis replay under a new top-level request id.

The response returns the namespace set status, row ids, source ids, package kinds, response-safe `artifact://replacement-package-artifacts/...` refs, artifact hashes, nested namespace row records, and explicit disabled-surface flags.

## Proof

Targeted service proof covers:

- complete namespace-set row recording from corrected-artifact manifest authority;
- same-key same-payload replay returning existing row ids;
- same authority basis with a new top-level client request id returning existing row ids;
- fail-closed unsupported operator decision;
- fail-closed caller-supplied artifact ref;
- fail-closed caller-supplied public URL;
- fail-closed stale corrected artifact basis hash;
- fail-closed stale replacement artifact manifest authority basis hash;
- no source `L3OutputPackage` mutation;
- no source package payload rewrite; and
- no artifact file rewrite.

Targeted API proof covers:

- OpenAPI request schema for the new route;
- OpenAPI response schema `Layer3ReplacementPackageNamespaceSetResponse`;
- documented 400/404/409 Layer 3 workbench error envelopes;
- forced service boundary error returning `layer3.workbench_error.v1`; and
- known forbidden `public_url` returning `replacement_package_namespace_from_corrected_manifest_scope_not_admitted`.

Observed branch-local validation:

```powershell
python -m py_compile .\backend\app\services\layer3_replacement_package_namespace.py .\backend\app\api\layer3.py
python -m pytest .\backend\tests\test_layer3_replacement_package_namespace.py -q
python -m pytest .\backend\tests\test_layer3_api.py -q -k "package_openapi_contracts or json_workbench_error_openapi_contracts or replacement_package_namespace_from_corrected_manifest"
python -m pytest .\backend\tests\test_layer3_api.py -q
```

Results observed:

- `backend/tests/test_layer3_replacement_package_namespace.py`: `6 passed`;
- `backend/tests/test_layer3_api.py -k package_openapi_contracts_or_json_workbench_error_openapi_contracts_or_replacement_package_namespace_from_corrected_manifest`: `4 passed, 178 deselected`;
- `backend/tests/test_layer3_api.py`: `182 passed`.

## Still Blocked

Package replacement activation, package payload rewrite, package payload writes, source `L3OutputPackage` mutation, downstream invalidation, handoff/export rerun, delivery rerun, provider-public delivery/use, connector/destination dispatch, `ConnectorRun` creation, `ConnectorRunTarget` creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, rendered UI authority, caller-supplied arbitrary paths or URLs, browser-supplied refs/hashes/bytes, raw local path exposure, and hidden LLM planning remain blocked.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_corrected_artifact_replacement_namespace_runtime`.
