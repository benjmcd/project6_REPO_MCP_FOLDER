# 641 - Replacement Package-Set Request Source Authority Selection Current-Main Sync

## Status

Status: current-main sync for `server_owned_replacement_package_artifact_materialization_request_source` selection freeze.

Doc: `641_REPLACEMENT_PACKAGE_SET_REQUEST_SOURCE_AUTHORITY_SELECTION_CURRENT_MAIN_SYNC.md`.

Freeze doc: `640_REPLACEMENT_PACKAGE_SET_REQUEST_SOURCE_AUTHORITY_SELECTION_FREEZE.md`.

Freeze PR: `#1244`.

Freeze branch: `codex/l3-replacement-request-source-selection`.

Freeze branch commit: `b97d1f42a63e381b42b5c53b92098e5186a97df2`.

Freeze merge commit: `a8dcd9640e6767c17b730b66b043d87db0e42739`.

Current-main checkpoint after merge: `a8dcd9640e6767c17b730b66b043d87db0e42739`.

Selected surface: `package_mutation_reconstruction`.

Selected request-source authority: `server_owned_replacement_package_artifact_materialization_from_supersession_preview`.

Selected operator action: `materialize_replacement_package_artifacts_from_supersession_preview`.

Selected implementation-entry mode: `server_owned_replacement_package_artifact_materialization_request_source`.

Future owner service: `backend/app/services/layer3_replacement_package_materialization.py`.

Future route: `/api/v1/layer3/package/replacement-artifact/materialize`.

Sync status: `current_main_synced_replacement_package_set_request_source_authority_selection_freeze`.

Layer 3 placement: Data Structuring & Processing package lifecycle boundary.

Sync live behavior change: false.

Runtime behavior already merged: false.

Rendered UI behavior already merged: false.

## Merge Gate

GitHub PR: `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1244`.

PR state: `MERGED`.

Checks:

- `backend-layer3-api`: `SUCCESS` in `2m56s`.
- `test`: `SUCCESS` in `3m6s`.

Review/comment gate:

- PR comments: empty.
- PR reviews: empty.
- PR reviewThreads totalCount: `0`.
- PR unresolved reviewThreads: `0`.
- Mergeability before merge: `MERGEABLE`.
- Merge state before merge: `CLEAN`.

## Current-Main Validation

Post-merge `project6-origin/main` authority:

- `project6-origin/main`: `a8dcd9640e6767c17b730b66b043d87db0e42739`.
- `python .\tools\l3-progress-check.py`: `PASS`.

This sync branch must additionally pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

No headed/headless E2E run is required for this sync because it records already-merged planning/control selection state and changes only planning/control metadata.

## Synced Result

The replacement package-set request-source authority selection freeze is now current-main synced.

Synced result: `current_main_synced_replacement_package_set_request_source_authority_selection_freeze`.

The synced current-main selection names exactly one governed upstream source for replacement package-set request fields: `server_owned_replacement_package_artifact_materialization_from_supersession_preview`. This preserves the blocker that `rendered_replacement_package_set_authority_control` cannot resume until the materialization source is implemented and proven.

The next exact posture is `implement_server_owned_replacement_package_artifact_materialization_request_source_after_selection_sync`.

## Non-Admission Boundary

This sync admits no new runtime behavior beyond the merged PR #1244 planning/control selection freeze. It does not add backend route, DTO, response model, model, migration, service behavior, executable backend test behavior, rendered UI control, package supersession commit control, package row mutation, source `L3OutputPackage` row mutation, source package payload rewrite, browser-provided package bytes, browser-provided replacement refs/hashes, arbitrary caller-supplied paths/URLs, replacement output package namespace rows, replacement artifact manifest recording before materialization exists, connector/destination dispatch, connector-run creation, credentials, external network egress, provider-public delivery/use, raw public URL exposure, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, or frontend-durable authority.

## Next Posture

The next exact current-main posture is `implement_server_owned_replacement_package_artifact_materialization_request_source_after_selection_sync`.

Implementation may start only for the exact selected materialization source and must stay within the future owner service/route selected by doc 640.
