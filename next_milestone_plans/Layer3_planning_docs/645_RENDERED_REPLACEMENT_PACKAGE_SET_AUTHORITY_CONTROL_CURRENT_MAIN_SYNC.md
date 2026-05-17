# 645 - Rendered Replacement Package-Set Authority Control Current-Main Sync

## Status

Status: current-main sync for `rendered_replacement_package_set_authority_control` runtime proof.

Doc: `645_RENDERED_REPLACEMENT_PACKAGE_SET_AUTHORITY_CONTROL_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `644_RENDERED_REPLACEMENT_PACKAGE_SET_AUTHORITY_CONTROL_RUNTIME_PROOF.md`.

Runtime PR: `#1248`.

Runtime branch: `codex/l3-rendered-replacement-set-authority-control-2`.

Runtime branch commit: `33c5197811e19b32e3d6cda3aeb974f24dfddede`.

Runtime merge commit: `2625952499ecd0883f06171ad2a793bbb3dd005d`.

Current-main checkpoint after merge: `2625952499ecd0883f06171ad2a793bbb3dd005d`.

Selected implementation-entry mode now synced: `rendered_replacement_package_set_authority_control`.

Rendered submit control now on current main: `#replacement-package-set-authority-submit`.

Rendered status panel now on current main: `#replacement-package-set-authority-panel`.

Existing materialization route used by the rendered control: `POST /api/v1/layer3/package/replacement-artifact/materialize`.

Existing authority route used by the rendered control: `POST /api/v1/layer3/package/replacement-set/record`.

Synced result: `current_main_synced_rendered_replacement_package_set_authority_control_runtime`.

Layer 3 placement: Data Structuring & Processing package lifecycle boundary.

Sync live behavior change: false.

Runtime/rendered behavior already merged: true.

Backend behavior already merged before this UI pass: true.

## Merge Gate

GitHub PR: `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1248`.

PR state: `MERGED`.

Checks:

- `backend-layer3-api`: `SUCCESS` in `2m29s`.
- `test`: `SUCCESS` in `3m19s`.

Review/comment gate:

- PR comments: empty.
- PR reviews: empty.
- PR reviewThreads totalCount: `0`.
- PR unresolved reviewThreads: `0`.
- Merge state before merge: `CLEAN`.

## Current-Main Validation

Post-merge `project6-origin/main` authority:

- `project6-origin/main`: `2625952499ecd0883f06171ad2a793bbb3dd005d`.
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

The rendered replacement package-set authority control is now current-main synced.

Synced result: `current_main_synced_rendered_replacement_package_set_authority_control_runtime`.

The synced current-main UI now lets the operator drive the previously frozen `record_replacement_package_set_authority_after_supersession_preview` action from `/review/layer3`. The browser first calls the server-owned replacement artifact materialization route from package supersession preview authority, then records replacement package-set authority only from the server materialization response.

The rendered control is not durable authority. The durable authority remains the server-owned materialization receipt and replacement package-set authority record.

## Non-Admission Boundary

This sync admits no new runtime behavior beyond the merged PR #1248 rendered control. It does not add package supersession commit control, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement output package namespace row creation, replacement artifact manifest recording, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, or browser-provided replacement refs/hashes.

## Next Posture

The next exact current-main posture is `freeze_rendered_package_supersession_commit_control_after_replacement_package_set_authority_control_sync`.

That next pass may write only the implementation-entry freeze for a rendered package supersession commit control that submits to the already-existing `POST /api/v1/layer3/package/supersession/commit` lineage route from the current server-owned replacement package-set authority. It must not implement runtime in the same pass unless a current-main freeze already admits that exact slice.

Package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement output package namespace rows, replacement artifact manifest recording, downstream invalidation, re-delivery runtime, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, and frontend-durable authority remain blocked unless separately selected and frozen.
