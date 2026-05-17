# 649 - Rendered Package Supersession Commit Control Runtime Current-Main Sync

## Status

Status: current-main sync for `rendered_package_supersession_commit_control` runtime proof.

Doc: `649_RENDERED_PACKAGE_SUPERSESSION_COMMIT_CONTROL_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `648_RENDERED_PACKAGE_SUPERSESSION_COMMIT_CONTROL_RUNTIME_PROOF.md`.

Runtime PR: `#1252`.

Runtime branch: `codex/l3-rendered-supersession-commit-control`.

Runtime branch commit: `f375657a40d3c780cb8e771fd210040000b017f8`.

Runtime merge commit: `fe6d93eaad95c768b930b384b592d00d5697c37e`.

Current-main checkpoint after merge: `fe6d93eaad95c768b930b384b592d00d5697c37e`.

Selected implementation-entry mode now synced: `rendered_package_supersession_commit_control`.

Selected operator action now synced: `commit_package_supersession_after_replacement_package_set_authority`.

Rendered submit control now on current main: `#package-supersession-commit-submit`.

Rendered status panel now on current main: `#package-supersession-commit-panel`.

Existing backend surface used by the rendered control: `POST /api/v1/layer3/package/supersession/commit`.

Owner service now aligned on current main: `backend/app/services/layer3_package_supersession_commit.py`.

Synced result: `current_main_synced_rendered_package_supersession_commit_control_runtime`.

Layer 3 placement: Data Structuring & Processing package lifecycle boundary.

Sync live behavior change: false.

Runtime/rendered behavior already merged: true.

Backend service behavior already merged: true.

## Merge Gate

GitHub PR: `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1252`.

PR state: `MERGED`.

Checks:

- `backend-layer3-api`: `SUCCESS` in `2m42s`.
- `test`: `SUCCESS` in `3m8s`.

Review/comment gate:

- PR comments: empty.
- PR reviews: empty.
- PR reviewThreads totalCount: `0`.
- PR unresolved reviewThreads: `0`.
- Mergeability before merge: `MERGEABLE`.
- Merge state before merge: `CLEAN`.

## Current-Main Validation

Post-merge `project6-origin/main` authority:

- `project6-origin/main`: `fe6d93eaad95c768b930b384b592d00d5697c37e`.
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

No headed/headless E2E run is required for this sync because it records already-merged rendered runtime proof and changes only planning/control metadata.

## Synced Result

The rendered package supersession commit control runtime is now current-main synced.

Synced result: `current_main_synced_rendered_package_supersession_commit_control_runtime`.

The synced current-main UI now lets the operator drive the previously frozen `commit_package_supersession_after_replacement_package_set_authority` action from `/review/layer3`. The rendered control submits only to `POST /api/v1/layer3/package/supersession/commit` from server-owned package supersession preview and replacement package-set authority.

The synced runtime also includes the narrow service projection alignment from PR #1252: `layer3_package_supersession_commit.py` preserves `schema_id` and `request_ref_field` in the current downstream dependency projection so the commit hash basis matches the existing package supersession preview dependency projection.

The rendered control is not durable authority. The durable authority remains the server-owned package supersession commit record and its lineage/audit fields.

## Non-Admission Boundary

This sync admits no new runtime behavior beyond the merged PR #1252 runtime. It does not add package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement output package namespace rows, replacement artifact manifest recording, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, or browser-provided replacement refs/hashes.

## Next Posture

The next exact current-main posture is `freeze_rendered_replacement_package_artifact_manifest_control_after_package_supersession_commit_control_sync`.

That next pass may write only the implementation-entry freeze for a rendered replacement package artifact manifest recording control. It may use the already-live `POST /api/v1/layer3/package/replacement-artifact/manifest/record` route and the current server-owned replacement package-set authority plus package supersession commit authority as proof architecture, but it must not implement runtime in the same pass unless a current-main freeze already admits that exact rendered slice.

Package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement output package namespace row creation, downstream invalidation, re-delivery runtime, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, and caller-supplied arbitrary paths or URLs remain blocked unless separately selected and frozen.
