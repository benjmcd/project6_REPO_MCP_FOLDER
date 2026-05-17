# 653 - Replacement Package Artifact Manifest Request Authority Source Selection Current-Main Sync

## Status

Status: current-main sync for `server_computed_replacement_package_artifact_manifest_record_from_authority` request-authority source selection.

Doc: `653_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUEST_AUTHORITY_SOURCE_SELECTION_CURRENT_MAIN_SYNC.md`.

Selection freeze doc: `652_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUEST_AUTHORITY_SOURCE_SELECTION_FREEZE.md`.

Selection freeze PR: `#1256`.

Selection freeze branch: `codex/l3-replacement-manifest-request-authority-freeze`.

Selection freeze branch commit: `771378280ed8a35cc8dbe87f61ce863e6e6a0c11`.

Selection freeze merge commit: `1042a20f8176938ee5987bc25bba0eb01f18e5f6`.

Current-main checkpoint after merge: `1042a20f8176938ee5987bc25bba0eb01f18e5f6`.

Selected request-authority source now synced: `server_computed_replacement_package_artifact_manifest_record_from_materialization_authority`.

Selected implementation-entry mode now synced: `server_computed_replacement_package_artifact_manifest_record_from_authority`.

Selected operator action now synced: `record_replacement_package_artifact_manifest_from_authority`.

Future owner service now synced: `backend/app/services/layer3_replacement_package_artifact_manifest.py`.

Future route now synced: `/api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`.

Synced result: `current_main_synced_replacement_package_artifact_manifest_request_authority_source_selection`.

Layer 3 placement: Data Structuring & Processing package lifecycle boundary.

Sync live behavior change: false.

Runtime/rendered behavior change in this sync: false.

## Merge Gate

GitHub PR: `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1256`.

PR state: `MERGED`.

Checks:

- `backend-layer3-api`: `SUCCESS` in `2m58s`.
- `test`: `SUCCESS` in `3m41s`.

Review/comment gate:

- PR comments: empty.
- PR reviews: empty.
- PR reviewThreads totalCount: `0`.
- PR unresolved reviewThreads: `0`.
- Mergeability before merge: `MERGEABLE`.
- Merge state before merge: `CLEAN`.

## Current-Main Validation

Post-merge `project6-origin/main` authority:

- `project6-origin/main`: `1042a20f8176938ee5987bc25bba0eb01f18e5f6`.
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

No headed/headless E2E run is required for this sync because it records an already-merged selection freeze and changes only planning/control metadata.

## Synced Result

The replacement package artifact manifest request-authority source selection is now current-main synced.

Synced result: `current_main_synced_replacement_package_artifact_manifest_request_authority_source_selection`.

Current main now selects `server_computed_replacement_package_artifact_manifest_record_from_authority` as the exact implementation-entry mode for the next runtime pass. That future pass may add only the server-computed `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-authority` backend/API slice, backed by existing replacement artifact materialization, replacement package-set authority, and package supersession commit rows.

The selected implementation must compute `artifact_manifest_hash`, `authority_basis_hash`, and verified byte-size basis server-side and must return only response-safe/redacted artifact refs. It must not accept browser-supplied replacement refs, replacement hashes, artifact manifest hashes, authority basis hashes, byte sizes, local paths, URLs, package bytes, replacement bytes, or artifact bytes.

## Non-Admission Boundary

This sync admits no new runtime behavior beyond the merged PR #1256 selection freeze. It does not add backend route behavior, DTO response model changes, model changes, migrations, service behavior changes, rendered replacement artifact manifest submit controls, modification of the existing caller-supplied manifest record request contract, browser-supplied replacement refs/hashes, browser-supplied manifest hashes, browser-supplied authority hashes, browser-supplied byte sizes, raw local path exposure, replacement namespace rows, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, frontend-durable authority, or browser/operator path editing.

## Next Posture

The next exact current-main posture is `implement_server_computed_replacement_package_artifact_manifest_record_from_authority_after_selection_sync`.

That next pass may implement only the selected backend/API record-from-authority slice. It may not add a rendered UI control in the same pass unless that control is separately frozen by current-main authority. It may not add replacement namespace rows, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, or browser-supplied artifact refs/hashes/bytes.
