# 671 - Source L3 Output Package Active Authority Handoff Export Prepare Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_l3_output_package_active_authority_handoff_export_prepare_runtime`.

Doc: `671_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_HANDOFF_EXPORT_PREPARE_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime doc: `670_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_HANDOFF_EXPORT_PREPARE_RUNTIME_PROOF.md`.

Runtime PR: `#1275`.

Runtime branch: `codex/l3-active-authority-handoff-impl`.

Runtime branch commit: `9cda786716f7ebc99ba5f9f26020c123919f730d`.

Runtime merge commit: `36b38332d5cbb23271e22e27cd59b0aa17903d55`.

Current-main checkpoint after merge: `36b38332d5cbb23271e22e27cd59b0aa17903d55`.

Selected follow-on surface now synced: `downstream_active_package_authority_read_adoption`.

Selected reader path now synced: `handoff_export_prepare`.

Selected route now synced: `POST /api/v1/layer3/handoff/export/prepare`.

Selected resolver now synced: `resolve_active_replacement_package_authority`.

Selected operator action now synced: `adopt_active_replacement_package_authority_for_handoff_export_prepare`.

Synced result: `current_main_synced_source_l3_output_package_active_authority_handoff_export_prepare_runtime`.

Sync live behavior change: false.

Runtime/rendered behavior change in this sync: false.

## Merge Gate

GitHub PR: `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1275`.

PR state: `MERGED`.

Checks:

- `backend-layer3-api`: `SUCCESS` in `2m44s`.
- `test`: `SUCCESS` in `3m47s`.

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

- `project6-origin/main`: `36b38332d5cbb23271e22e27cd59b0aa17903d55`.
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

No headed/headless E2E run is required for this sync because it records an already-merged backend/API reader-adoption runtime and changes only planning/control metadata.

## Synced Result

The source L3 output package active authority handoff/export prepare runtime is now current-main synced.

Synced result: `current_main_synced_source_l3_output_package_active_authority_handoff_export_prepare_runtime`.

Current main now makes the `handoff_export_prepare` reader consume active replacement package authority for `POST /api/v1/layer3/handoff/export/prepare` when a valid `L3PackageReplacementActivation` exists.

The reader uses `resolve_active_replacement_package_authority`, validates package kinds, source package ids, and source payload hashes against the handoff/export prepare basis, then projects response-safe `artifact://replacement-package-artifacts/...` active refs/hashes into the prepare response, persisted prepare state, internal export envelope, and authority basis.

The implementation preserves the indirection boundary: source `L3OutputPackage` rows, source package payload refs/hashes, package ids, and `uq_l3_output_package_session_kind` remain unchanged.

The active authority projection includes `active_package_authority_applied`, `package_replacement_activation_id`, `source_output_package_ids`, `source_payload_hashes`, `active_replacement_output_package_ids`, `active_payload_refs`, `active_payload_hashes`, and `replacement_activation_basis_hash`.

The runtime also keeps active authority fields caller-forbidden on the handoff/export prepare request and fails closed on wrong package kinds, wrong source package ids, stale source payload hashes, incomplete active authority, non-response-safe active refs, missing activation id, or missing replacement activation basis hash.

Current main still does not rebind APS handoff dispatch, external export/download, server-owned local outbox, provider-private handoff, external local export, rendered activation controls, or any other downstream reader to active package authority.

## Non-Admission Boundary

This sync admits no new runtime or rendered behavior beyond merged PR #1275. It does not add rendered activation controls, APS handoff dispatch adoption, external export/download adoption, server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact current-main posture is `select_next_active_package_authority_reader_or_rendered_activation_control_after_handoff_export_prepare_runtime_sync`.

That next decision should choose exactly one of these package-lifecycle follow-on surfaces before implementation:

- another downstream active-package-authority read adoption for one named reader path, such as APS handoff dispatch, external export/download, server-owned local outbox, provider-private handoff, or external local export;
- rendered activation controls for the existing backend/API activation runtime;
- a separately frozen package rebuild/payload rewrite action if the operator decides activation by indirection is insufficient.

The highest-utility next path is another named downstream reader adoption if the immediate goal is making end-to-end delivery consume the activated package authority. Rendered activation controls are higher utility if the immediate goal is operator usability for selecting/seeing the active package authority. Package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, broad auth/security behavior, full mockup activation, frontend-durable authority, and caller-supplied arbitrary paths or URLs remain blocked until separately selected and frozen.
