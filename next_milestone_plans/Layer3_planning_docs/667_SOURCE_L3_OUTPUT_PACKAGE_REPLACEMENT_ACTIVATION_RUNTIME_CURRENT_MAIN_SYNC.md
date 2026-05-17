# 667 - Source L3 Output Package Replacement Activation Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_l3_output_package_replacement_activation_runtime`.

Doc: `667_SOURCE_L3_OUTPUT_PACKAGE_REPLACEMENT_ACTIVATION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime doc: `666_SOURCE_L3_OUTPUT_PACKAGE_REPLACEMENT_ACTIVATION_RUNTIME_PROOF.md`.

Runtime PR: `#1271`.

Runtime branch: `codex/l3-package-activation-runtime`.

Runtime branch commit: `7b2bf2241fefac6f03029f9bb6e9d95b58eba391`.

Runtime merge commit: `ea01ebd6840bca750f1de2ca716b205f6dcb6896`.

Current-main checkpoint after merge: `ea01ebd6840bca750f1de2ca716b205f6dcb6896`.

Selected implementation-entry mode now synced: `source_l3_output_package_replacement_activation`.

Selected package lifecycle action now synced: `activate_replacement_output_package_namespace`.

Selected route now synced: `POST /api/v1/layer3/package/replacement-activation/commit`.

Selected owner service now synced: `backend/app/services/layer3_package_replacement_activation.py`.

Selected durable state now synced: `L3PackageReplacementActivation` / `l3_package_replacement_activation`.

Synced result: `current_main_synced_source_l3_output_package_replacement_activation_runtime`.

Sync live behavior change: false.

Runtime/rendered behavior change in this sync: false.

## Merge Gate

GitHub PR: `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1271`.

PR state: `MERGED`.

Checks:

- `backend-layer3-api`: `SUCCESS` in `2m24s`.
- `test`: `SUCCESS` in `3m37s`.

Review/comment gate:

- PR comments: empty.
- PR reviews: empty.
- PR latestReviews: empty.
- PR reviewThreads totalCount: `0`.
- PR unresolved reviewThreads: `0`.
- Mergeability before merge: `MERGEABLE`.
- Merge state before merge: `CLEAN`.

## Current-Main Validation

Post-merge `project6-origin/main` authority:

- `project6-origin/main`: `ea01ebd6840bca750f1de2ca716b205f6dcb6896`.
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

No headed/headless E2E run is required for this sync because it records an already-merged backend/API runtime proof and changes only planning/control metadata.

## Synced Result

The source L3 output package replacement activation runtime is now current-main synced.

Synced result: `current_main_synced_source_l3_output_package_replacement_activation_runtime`.

Current main now provides `POST /api/v1/layer3/package/replacement-activation/commit`, backed by `backend/app/services/layer3_package_replacement_activation.py`, `L3PackageReplacementActivation`, migration `0032_layer3_package_replacement_activation.py`, and the durable table `l3_package_replacement_activation`.

The runtime records one durable activation receipt/state row selecting one complete already-recorded replacement namespace set as active package authority for a session. It preserves the dedicated activation-table boundary: source `L3OutputPackage` rows, source package payload refs/hashes, and `uq_l3_output_package_session_kind` are not mutated.

Current main also preserves the idempotency basis boundary: `client_request_id` is the idempotency key and is not part of canonical `replacement_activation_basis_hash`.

The resolver `resolve_active_replacement_package_authority` is now available for a later separately frozen downstream adoption slice. Existing handoff/export readers are not rebound by this sync.

## Non-Admission Boundary

This sync admits no new runtime or rendered behavior beyond merged PR #1271. It does not add rendered activation controls, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, downstream handoff/export re-binding, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact current-main posture is `select_post_activation_package_lifecycle_use_surface_after_runtime_sync`.

That next decision should choose exactly one of these package-lifecycle follow-on surfaces before implementation:

- rendered activation controls for the existing backend/API activation runtime;
- downstream active-package-authority read adoption for a named reader path;
- a separately frozen package rebuild/payload rewrite action if the operator decides activation by indirection is insufficient.

The highest-velocity next path is rendered activation controls if the immediate need is operator usability, or downstream active-package-authority read adoption if the immediate need is making later handoff/export readers consume the activated replacement authority. Package rebuild, package payload rewrite, downstream invalidation, re-delivery, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, broad auth/security behavior, full mockup activation, frontend-durable authority, and caller-supplied arbitrary paths or URLs remain blocked until separately selected and frozen.
