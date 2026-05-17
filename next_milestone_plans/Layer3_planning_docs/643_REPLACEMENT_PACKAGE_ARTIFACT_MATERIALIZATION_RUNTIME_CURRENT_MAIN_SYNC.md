# 643 - Replacement Package Artifact Materialization Runtime Current-Main Sync

## Status

Status: current-main sync for `server_owned_replacement_package_artifact_materialization_request_source` runtime proof.

Doc: `643_REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `642_REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_RUNTIME_PROOF.md`.

Implementation-entry freeze: `640_REPLACEMENT_PACKAGE_SET_REQUEST_SOURCE_AUTHORITY_SELECTION_FREEZE.md`.

Runtime PR: `#1246`.

Runtime branch: `codex/l3-replacement-materialization-source`.

Runtime branch commit: `44c8b994bd67a167c983815c5c4fb988af9f2787`.

Runtime merge commit: `afb3d0ff5675d2b506fcef73d41f076302620fb4`.

Current-main checkpoint after merge: `afb3d0ff5675d2b506fcef73d41f076302620fb4`.

Selected implementation-entry mode now synced: `server_owned_replacement_package_artifact_materialization_request_source`.

Runtime service now on current main: `backend/app/services/layer3_replacement_package_materialization.py`.

Runtime route now on current main: `POST /api/v1/layer3/package/replacement-artifact/materialize`.

Runtime receipt table now on current main: `l3_replacement_package_artifact_materialization`.

Runtime artifact namespace now on current main: `replacement-package-artifacts`.

Synced result: `current_main_synced_replacement_package_artifact_materialization_runtime`.

Layer 3 placement: Data Structuring & Processing package lifecycle boundary.

Sync live behavior change: false.

Runtime behavior already merged: true.

Rendered UI behavior already merged: false.

## Merge Gate

GitHub PR: `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1246`.

PR state: `MERGED`.

Checks:

- `backend-layer3-api`: `SUCCESS` in `2m47s`.
- `test`: `SUCCESS` in `3m4s`.

Review/comment gate:

- PR comments: empty.
- PR reviews: empty.
- PR reviewThreads totalCount: `0`.
- PR unresolved reviewThreads: `0`.
- Mergeability before merge: `MERGEABLE`.
- Merge state before merge: `CLEAN`.

## Current-Main Validation

Post-merge `project6-origin/main` authority:

- `project6-origin/main`: `afb3d0ff5675d2b506fcef73d41f076302620fb4`.
- `python .\tools\l3-progress-check.py`: `PASS`.
- `python .\tools\l3-target-selection-validate.py --expect frozen`: `PASS`.

This sync branch must additionally pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

No headed/headless E2E run is required for this sync because it records already-merged backend/API runtime proof and changes only planning/control metadata.

## Synced Result

The replacement package artifact materialization runtime is now current-main synced.

Synced result: `current_main_synced_replacement_package_artifact_materialization_runtime`.

The synced current-main runtime now provides the governed request-source authority needed by rendered replacement package-set authority control. The materialization runtime computes `replacement_package_set_id`, `replacement_package_set_hash`, `replacement_package_kinds`, `replacement_payload_refs`, `replacement_payload_hashes`, and `authority_basis_hash` from existing package supersession preview authority and server-owned package artifacts.

The prior blocker `rendered_replacement_package_set_authority_control_blocked_by_missing_governed_replacement_request_source` is satisfied by the merged runtime proof, but only for the current admitted materialization route and server-owned artifact namespace.

## Non-Admission Boundary

This sync admits no new runtime behavior beyond the merged PR #1246 runtime. It does not add rendered replacement package-set authority control, package supersession commit control, package row mutation, source `L3OutputPackage` row mutation, source package payload rewrite, browser-provided package bytes, browser-provided replacement refs/hashes, arbitrary caller-supplied local paths or URLs, replacement output package namespace rows, replacement artifact manifest recording beyond existing freezes, connector or destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, provider-public delivery/use, raw public URL exposure, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, or frontend-durable authority.

## Next Posture

The next exact current-main posture is `implement_rendered_replacement_package_set_authority_control_after_materialization_runtime_sync`.

That next pass may implement only the previously frozen `rendered_replacement_package_set_authority_control` slice using the now-current-main materialization runtime as governed request-source authority. Package supersession commit control, package row mutation, source expansion, RAG/vector behavior, provider-public delivery/use, connector/destination dispatch, auth/security behavior, full mockup activation, and frontend-durable authority remain blocked unless separately selected and frozen.
