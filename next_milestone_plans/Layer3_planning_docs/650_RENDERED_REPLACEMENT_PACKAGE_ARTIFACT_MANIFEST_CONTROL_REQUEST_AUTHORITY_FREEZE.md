# 650 - Rendered Replacement Package Artifact Manifest Control Request Authority Freeze

## Status

Status: branch-local blocker/freeze for `replacement_package_artifact_manifest_request_authority_freeze`.

Doc: `650_RENDERED_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_CONTROL_REQUEST_AUTHORITY_FREEZE.md`.

Predecessor doc: `649_RENDERED_PACKAGE_SUPERSESSION_COMMIT_CONTROL_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `596d7319dd3bb06d2b973e383776286138e92d16`.

Selected surface: `package_mutation_reconstruction`.

Attempted implementation-entry mode: `rendered_replacement_package_artifact_manifest_control`.

Attempted operator action: `record_replacement_package_artifact_manifest_after_package_supersession_commit`.

Audit result: `rendered_replacement_package_artifact_manifest_control_blocked_by_missing_governed_manifest_request_authority`.

Required stop posture: `replacement_package_artifact_manifest_request_authority_freeze`.

Entry decision: `freeze_only`.

Runtime status in this pass: `not_implemented`.

## Source-Audit Finding

Current main cannot safely implement `rendered_replacement_package_artifact_manifest_control` as a UI-only pass.

The already-live backend runtime `backend/app/services/layer3_replacement_package_artifact_manifest.py` requires the browser request to include:

- `artifact_manifest_hash`;
- `authority_basis_hash`.

Those values are not simple echoes of rendered state. The service computes `artifact_manifest_hash` only after server-side artifact verification, including `verified_artifact_refs`, `verified_artifact_hashes`, and `verified_artifact_byte_sizes`. It computes `authority_basis_hash` from that server-verified manifest hash plus replacement package-set authority and package supersession commit authority.

Current rendered state can hold replacement package materialization, replacement package-set authority, and package supersession commit response state. It does not hold a governed server-computed replacement artifact manifest hash, authority basis hash, or verified artifact byte-size vector. The browser must not read raw server-local artifact paths or infer byte sizes from local filesystem refs.

## Evidence

- `backend/app/services/layer3_replacement_package_artifact_manifest.py` requires `artifact_manifest_hash` and `authority_basis_hash`, verifies replacement refs server-side, and includes `verified_artifact_byte_sizes` in the manifest hash basis.
- `backend/app/api/layer3.py` exposes `POST /api/v1/layer3/package/replacement-artifact/manifest/record` with strict request/response DTOs for the already-live manifest runtime.
- `backend/app/services/layer3_replacement_package_materialization.py` returns replacement refs, hashes, artifact namespace, and hash algorithm, but not a server-computed `artifact_manifest_hash`, manifest `authority_basis_hash`, or verified artifact byte-size vector for a later rendered manifest request.
- `backend/app/review_ui/static/layer3.js` currently owns `State.replacementPackageArtifactMaterialization`, `State.replacementPackageSetAuthority`, and `State.packageSupersessionCommit`; it has no `replacementPackageArtifactManifestPayload` owner and no governed manifest request-authority response state.
- Existing manifest tests fabricate the manifest request hash basis through test helpers. That proves backend guardrails, not live browser-safe request authority for a rendered submit control.

## Decision

Do not implement the rendered replacement package artifact manifest control in this pass.

Do not add browser/operator path editing, caller-supplied arbitrary refs, caller-supplied URLs, browser file reads, replacement payload generation, package payload rewrite, package row mutation, replacement namespace rows, downstream invalidation, re-delivery, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, or frontend-durable authority.

The next product/implementation-prep decision must name one governed server-owned source for replacement artifact manifest request authority before a rendered submit control can exist.

## Missing Authority To Resolve

One exact governed manifest request-authority source must be selected later. Acceptable future candidates must be separately frozen and may include only one named path, such as:

- server-computed replacement artifact manifest request-authority projection from existing materialization, replacement package-set authority, and package supersession commit authority;
- a server-owned manifest prepare helper that verifies replacement artifacts and returns response-safe `artifact_manifest_hash`, `authority_basis_hash`, and verified byte-size basis without recording the durable manifest;
- a narrowed manifest-record request shape that computes manifest hash and authority basis server-side from existing authority ids rather than requiring browser-supplied hash values.

This doc does not select any of those candidates. It records that current main lacks the request authority required to implement the rendered control safely.

## Non-Admission Boundary

This freeze admits no backend route, DTO, response model, model, migration, service behavior, executable backend test behavior, rendered UI control, replacement artifact manifest recording from the browser, replacement namespace rows, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement output package row creation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, or frontend-durable authority.

The already-live backend/API replacement artifact manifest runtime remains available only as server-authoritative runtime. This pass does not render or invoke it from `/review/layer3`.

## Required Future Selection

A later selection freeze must name exactly one request-authority source and prove:

- how `artifact_manifest_hash` is computed from server-verified artifact refs, hashes, and byte sizes;
- how `authority_basis_hash` is computed from replacement package-set authority, package supersession commit authority, and the server-verified manifest hash;
- how rendered state receives only response-safe fields and redacts raw local refs;
- how same-key replay, same-key conflict, same-basis/new-key replay, stale materialization, stale replacement authority, stale supersession commit, stale source package, missing artifact, hash mismatch, and outside-namespace refs fail closed;
- how the implementation avoids browser-supplied paths, URLs, package bytes, replacement bytes, artifact bytes, and frontend-durable authority.

## Required Validation

This branch must pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

No headed/headless E2E run is required for this freeze-only blocker because no rendered behavior is changed.

## Next Posture

The next required action after merge is `current_main_sync_replacement_package_artifact_manifest_request_authority_freeze`.

After current-main sync, the next exact posture is `select_one_governed_replacement_package_artifact_manifest_request_authority_after_blocker_sync`.
