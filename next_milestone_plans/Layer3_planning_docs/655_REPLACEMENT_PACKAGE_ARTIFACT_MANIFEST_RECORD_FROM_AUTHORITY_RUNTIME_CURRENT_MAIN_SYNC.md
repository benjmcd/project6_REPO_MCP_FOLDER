# 655 - Replacement Package Artifact Manifest Record-From-Authority Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `server_computed_replacement_package_artifact_manifest_record_from_authority_runtime`.

Doc: `655_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_RECORD_FROM_AUTHORITY_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `654_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_RECORD_FROM_AUTHORITY_RUNTIME.md`.

Runtime PR: `#1258`.

Runtime branch: `codex/l3-replacement-manifest-record-authority-runtime`.

Runtime branch commit: `b59ab3be7897ae2eda5379dab53d61aa2644a2fc`.

Runtime merge commit: `d559d42d99d50314007e5f7daa73d60cb9f8592c`.

Current-main checkpoint after merge: `d559d42d99d50314007e5f7daa73d60cb9f8592c`.

Synced route: `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`.

Synced service: `backend/app/services/layer3_replacement_package_artifact_manifest.py`.

Synced request DTO: `Layer3ReplacementPackageArtifactManifestFromAuthorityRequest`.

Synced response schema id: `layer3.replacement_package_artifact_manifest_from_authority.v1`.

Synced result: `current_main_synced_replacement_package_artifact_manifest_record_from_authority_runtime`.

Sync live behavior change: false.

Runtime/rendered behavior change in this sync: false.

## Merge Gate

GitHub PR: `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1258`.

PR state: `MERGED`.

Checks:

- `backend-layer3-api`: `SUCCESS` in `2m40s`.
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

- `project6-origin/main`: `d559d42d99d50314007e5f7daa73d60cb9f8592c`.
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

No headed/headless E2E run is required for this sync because it records an already-merged backend/API runtime and changes only planning/control metadata.

## Synced Result

The server-computed replacement package artifact manifest record-from-authority runtime is now current-main synced.

Synced result: `current_main_synced_replacement_package_artifact_manifest_record_from_authority_runtime`.

Current main now includes `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`. The route accepts only server-owned authority ids plus `materialization_basis_hash`, `replacement_authority_basis_hash`, and `package_supersession_commit_basis_hash`; resolves existing replacement artifact materialization, replacement package-set authority, and package supersession commit rows server-side; computes `artifact_manifest_hash`, manifest `authority_basis_hash`, and verified byte-size basis server-side; persists the existing durable manifest row; and returns only redacted artifact refs.

## Non-Admission Boundary

This sync admits no new runtime behavior beyond merged PR #1258. It does not add rendered replacement artifact manifest submit controls, replacement namespace rows, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied artifact refs, browser-supplied replacement hashes, browser-supplied manifest hashes, browser-supplied byte sizes, browser-supplied package bytes, browser-supplied replacement bytes, or browser-supplied artifact bytes.

## Next Posture

The next exact current-main posture is `determine_rendered_replacement_package_artifact_manifest_control_admission_or_next_package_lifecycle_guardrail`.

The next pass should decide whether the rendered replacement package artifact manifest control can be safely admitted against the synced server-computed request-authority route, or whether another package lifecycle guardrail remains higher value. No implementation begins from this sync unless that next posture is separately frozen by current-main authority.
