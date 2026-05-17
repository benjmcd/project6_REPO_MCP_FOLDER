# 663 - Rendered Replacement Package Namespace Control Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `rendered_replacement_package_namespace_control_runtime`.

Doc: `663_RENDERED_REPLACEMENT_PACKAGE_NAMESPACE_CONTROL_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime doc: `662_RENDERED_REPLACEMENT_PACKAGE_NAMESPACE_CONTROL_RUNTIME_PROOF.md`.

Runtime PR: `#1266`.

Runtime branch: `codex/l3-rendered-namespace-control-runtime`.

Runtime branch commit: `1d5224f7c4996d2b04f6c68c13d00fdf77518874`.

Runtime merge commit: `d10b4ccfa123a9cbf268943b8b365ae539a6369e`.

Current-main checkpoint after merge: `d10b4ccfa123a9cbf268943b8b365ae539a6369e`.

Selected implementation-entry mode now synced: `rendered_replacement_package_namespace_control`.

Selected operator action now synced: `record_replacement_package_namespace_row`.

Selected route now synced: `POST /api/v1/layer3/package/replacement-namespace/record`.

Synced result: `current_main_synced_rendered_replacement_package_namespace_control_runtime`.

Sync live behavior change: false.

Runtime/rendered behavior change in this sync: false.

## Merge Gate

GitHub PR: `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1266`.

PR state: `MERGED`.

Checks:

- `backend-layer3-api`: `SUCCESS` in `2m42s`.
- `test`: `SUCCESS` in `3m28s`.

Review/comment gate:

- PR comments: empty.
- PR reviews: empty.
- PR reviewThreads totalCount: `0`.
- PR unresolved reviewThreads: `0`.
- Mergeability before merge: `MERGEABLE`.
- Merge state before merge: `CLEAN`.

## Current-Main Validation

Post-merge `project6-origin/main` authority:

- `project6-origin/main`: `d10b4ccfa123a9cbf268943b8b365ae539a6369e`.
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

No headed/headless E2E run is required for this sync because it records an already-merged implementation/runtime proof and changes only planning/control metadata.

## Synced Result

The rendered replacement package namespace control runtime is now current-main synced.

Synced result: `current_main_synced_rendered_replacement_package_namespace_control_runtime`.

Current main now exposes `#replacement-package-namespace-submit` and `#replacement-package-namespace-panel`, calls `POST /api/v1/layer3/package/replacement-namespace/record` from manifest authority, replacement package-set authority, package supersession commit authority, and source package row authority, and renders response-safe `State.replacementPackageNamespace` status/history.

Current main also preserves the namespace service alignment from doc `662`: response-safe `artifact://replacement-package-artifacts/{manifest_id}/{package_kind}` refs are accepted at the rendered/API boundary while server-held manifest artifact hashes remain the verification authority.

## Non-Admission Boundary

This sync admits no new runtime or rendered behavior beyond merged PR #1266. It does not add package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, source package row reuse, weakening `uq_l3_output_package_session_kind`, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, or hidden LLM planning.

## Next Posture

The next exact current-main posture is `select_next_package_lifecycle_mutating_action_after_namespace_control_runtime_sync`.

That next pass must choose exactly one named package lifecycle action before any implementation. The current candidate set is package rebuild from corrected artifacts, package payload rewrite, source `L3OutputPackage` replacement/activation, downstream invalidation, or re-delivery. Any selected action must freeze authority source, request/response contract, stale-authority behavior, idempotency, failure lifecycle, redaction, proof requirements, and non-admitted boundaries before implementation. Provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, and browser-supplied arbitrary artifact refs/hashes/bytes remain blocked.
