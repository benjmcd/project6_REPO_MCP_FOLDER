# 659 - Rendered Replacement Package Artifact Manifest Control Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `rendered_replacement_package_artifact_manifest_control_runtime`.

Doc: `659_RENDERED_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_CONTROL_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `658_RENDERED_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_CONTROL_RUNTIME_PROOF.md`.

Runtime PR: `#1262`.

Runtime branch: `codex/l3-rendered-manifest-control-runtime`.

Runtime branch commit: `1b7f3af8006dd964732e1c99f51d13de90d7fe6e`.

Runtime merge commit: `669d80788e86f1aecf293b55de830a2f77d9df97`.

Current-main checkpoint after merge: `669d80788e86f1aecf293b55de830a2f77d9df97`.

Selected implementation-entry mode now synced: `rendered_replacement_package_artifact_manifest_control`.

Selected operator action now synced: `record_replacement_package_artifact_manifest_from_authority`.

Selected route now synced: `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`.

Synced result: `current_main_synced_rendered_replacement_package_artifact_manifest_control_runtime`.

Sync live behavior change: false.

Runtime/rendered behavior change in this sync: false.

## Merge Gate

GitHub PR: `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1262`.

PR state: `MERGED`.

Checks:

- `backend-layer3-api`: `SUCCESS` in `2m39s`.
- `test`: `SUCCESS` in `3m32s`.

Review/comment gate:

- PR comments: empty.
- PR reviews: empty.
- PR reviewThreads totalCount: `0`.
- PR unresolved reviewThreads: `0`.
- Mergeability before merge: `MERGEABLE`.
- Merge state before merge: `CLEAN`.

## Current-Main Validation

Post-merge `project6-origin/main` authority:

- `project6-origin/main`: `669d80788e86f1aecf293b55de830a2f77d9df97`.
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

No headed/headless E2E run is required for this sync because it records an already-merged rendered runtime and changes only planning/control metadata.

## Synced Result

The rendered replacement package artifact manifest control runtime is now current-main synced.

Synced result: `current_main_synced_rendered_replacement_package_artifact_manifest_control_runtime`.

Current main now exposes `#replacement-package-artifact-manifest-submit` and `#replacement-package-artifact-manifest-panel` in `/review/layer3`. The rendered control submits only authority ids and basis hashes from `State.replacementPackageArtifactMaterialization`, `State.replacementPackageSetAuthority`, and `State.packageSupersessionCommit` to the server-computed record-from-authority route. The server computes manifest hashes, verified byte-size basis, and redacted `artifact://replacement-package-artifacts/...` refs; the browser records only response-safe `State.replacementPackageArtifactManifest` status/history.

## Non-Admission Boundary

This sync admits no new runtime or rendered behavior beyond merged PR #1262. It does not add backend route changes, DTO changes, response model changes, service behavior changes, database model changes, migrations, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement namespace rendered control, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied artifact refs, browser-supplied replacement hashes, browser-supplied manifest hashes, browser-supplied byte sizes, browser-supplied package bytes, browser-supplied replacement bytes, or browser-supplied artifact bytes.

## Next Posture

The next exact current-main posture is `freeze_rendered_replacement_package_namespace_control_after_manifest_control_runtime_sync`.

That next pass may freeze only the rendered control for the existing bounded replacement namespace API runtime: `POST /api/v1/layer3/package/replacement-namespace/record`, owned by `backend/app/services/layer3_replacement_package_namespace.py`. It may not implement runtime in the freeze pass unless current-main authority already admits that exact slice. Any package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, or browser-supplied artifact refs/hashes/bytes remains blocked.
