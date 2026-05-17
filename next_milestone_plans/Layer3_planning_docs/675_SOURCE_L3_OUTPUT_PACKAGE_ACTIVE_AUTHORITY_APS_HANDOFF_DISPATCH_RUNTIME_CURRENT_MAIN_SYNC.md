# 675 - Source L3 Output Package Active Authority APS Handoff Dispatch Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_l3_output_package_active_authority_aps_handoff_dispatch_runtime`.

Doc: `675_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_APS_HANDOFF_DISPATCH_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime doc: `674_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_APS_HANDOFF_DISPATCH_RUNTIME_PROOF.md`.

Runtime PR: `#1279`.

Runtime branch: `codex/l3-active-authority-aps-dispatch-impl`.

Runtime branch commit: `fa2a3650b0ddf1d05ef33604e565c8de197d15c4`.

Runtime merge commit: `e3bd196aa4bb3d40e1948e998a9d97ebc6eef8b9`.

Current-main checkpoint after merge: `e3bd196aa4bb3d40e1948e998a9d97ebc6eef8b9`.

Selected follow-on surface now synced: `downstream_active_package_authority_read_adoption`.

Selected reader path now synced: `aps_handoff_dispatch`.

Selected route now synced: `POST /api/v1/layer3/handoff/aps/dispatch`.

Selected resolver now synced: `resolve_active_replacement_package_payload_authority`.

Selected operator action now synced: `adopt_active_replacement_package_authority_for_aps_handoff_dispatch`.

Synced result: `current_main_synced_source_l3_output_package_active_authority_aps_handoff_dispatch_runtime`.

Sync live behavior change: false.

Runtime/rendered behavior change in this sync: false.

## Merge Gate

GitHub PR: `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1279`.

PR state: `MERGED`.

Checks:

- `backend-layer3-api`: `SUCCESS` in `2m50s`.
- `test`: `SUCCESS` in `3m34s`.

Review/comment gate:

- PR comments: empty.
- PR latestReviews: one `COMMENTED` automated Codex review by `chatgpt-codex-connector`.
- PR reviewDecision: empty.
- PR reviewThreads totalCount: `3`.
- PR unresolved reviewThreads: `3`.
- PR outdated unresolved reviewThreads: `2`.
- PR unresolved non-outdated reviewThreads: `1`.
- The remaining non-outdated thread is the automated P2 `Preserve source refs for external readiness` thread on `backend/app/services/layer3_workbench.py`.
- The thread was treated as addressed by the merged code and validation because the runtime preserves source package refs/hashes separately from effective active refs/hashes, accepts the active dispatch state in existing external export/download prepare, and proves that follow-up path through backend/API and rendered E2E validation. The thread was not resolved or commented on during this pass.
- Merge state before merge: `CLEAN`.

## Current-Main Validation

Post-merge `project6-origin/main` authority:

- `project6-origin/main`: `e3bd196aa4bb3d40e1948e998a9d97ebc6eef8b9`.
- `python .\tools\l3-progress-check.py`: `PASS`.
- `python .\tools\l3-target-selection-validate.py --expect frozen`: `PASS`.

Runtime branch validation before merge included:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\backend\app\services\layer3_workbench.py .\backend\tests\review_browser_server.py .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
$files = Get-ChildItem .\backend\tests\test_layer3_*.py | ForEach-Object { ".\backend\tests\$($_.Name)" }
python -m pytest @files -q
npm run test:e2e:chromium
git diff --check
```

This sync branch must additionally pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

No headed/headless E2E run is required for this sync because it records an already-merged runtime and changes only planning/control metadata.

## Synced Result

The source L3 output package active authority APS handoff dispatch runtime is now current-main synced.

Synced result: `current_main_synced_source_l3_output_package_active_authority_aps_handoff_dispatch_runtime`.

Current main now makes the `aps_handoff_dispatch` reader consume active replacement package artifact authority for `POST /api/v1/layer3/handoff/aps/dispatch` when a valid active replacement package authority exists.

The reader uses `resolve_active_replacement_package_payload_authority` after validating package kinds, source output package ids, source payload hashes, replacement output package ids, active artifact refs, active artifact hashes, replacement activation basis hash, replacement namespace, replacement artifact manifest authority, and matching handoff/export prepare state.

Source package refs/hashes remain the immutable package-review source basis, while active refs/hashes become the effective APS handoff payload basis only after active authority validation.

Current main also preserves downstream compatibility: existing external export/download prepare accepts the active APS dispatch state and projects active refs/hashes without admitting a new external export/download runtime surface.

Rendered proof remains limited to existing controls. The merged runtime preserves rendered status refresh for the existing APS handoff path after handoff/export prepare, but it adds no new rendered activation controls.

## Non-Admission Boundary

This sync admits no new runtime or rendered behavior beyond merged PR #1279. It does not add rendered activation controls, new external export/download adoption beyond compatibility with the already-existing readiness lane, server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact current-main posture is `select_next_active_package_authority_reader_or_rendered_activation_control_after_aps_handoff_dispatch_runtime_sync`.

That next decision should choose exactly one implementation-bearing package-lifecycle follow-on:

- another downstream active-package-authority reader adoption if current evidence shows a remaining delivery reader still consumes stale source package authority;
- rendered activation controls if the immediate operator need is selecting, seeing, and reviewing the active package authority from the existing workbench;
- a separately frozen package rebuild or payload rewrite action only if the operator decides activation by indirection is insufficient.

Do not restart broad no-runtime audits. External export/download adoption beyond the already-proven compatibility path, local outbox adoption, provider-private handoff adoption, external local export adoption, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, and raw local path exposure remain blocked until exactly selected and frozen.
