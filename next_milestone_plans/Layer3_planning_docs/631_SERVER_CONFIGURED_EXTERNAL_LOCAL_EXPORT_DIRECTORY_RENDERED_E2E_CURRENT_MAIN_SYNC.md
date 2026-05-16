# 631 - Server-Configured External Local Export Directory Rendered E2E Current-Main Sync

## Status

Status: current-main sync for `server_configured_external_local_export_directory_rendered_e2e_proof`.

Doc: `631_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_RENDERED_E2E_CURRENT_MAIN_SYNC.md`.

Rendered E2E proof doc: `630_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_RENDERED_E2E_PROOF.md`.

Rendered E2E PR: `#1234`.

Rendered E2E branch: `codex/l3-external-local-export-e2e-proof`.

Rendered E2E branch commit: `bdf3fb82c4d90343619624d70e9d3330fbeca126`.

Rendered E2E merge commit: `99b85fe092a688505a5d47f44926a9b6cf138ed2`.

Current-main checkpoint after merge: `99b85fe092a688505a5d47f44926a9b6cf138ed2`.

Selected next external surface: `server_configured_external_local_export_directory`.

Selected next external surface class: `server_configured_external_destination_write`.

Selected proof action completed: `prove_server_configured_external_local_export_directory_rendered_status_history`.

Sync status: `current_main_synced_server_configured_external_local_export_directory_rendered_e2e_proof`.

Layer 3 placement: Data Structuring & Processing export/write boundary.

Sync live behavior change: false.

Runtime behavior already merged: true.

Rendered UI behavior already merged: true.

## Current-Main Evidence

PR `#1234` merged the focused rendered proof for the already-merged `server_configured_external_local_export_directory` runtime. Current main now contains:

- read-only rendered panel `#external-local-export-panel`;
- rendered mode `rendered_external_local_export_read_only_status_surface`;
- response authority `State.sessionSummary.external_local_export`;
- Playwright proof owner `e2e/layer3-handoff.spec.js`;
- review-browser temp server-owned external local export directory authority for proof;
- static page sentinel coverage in `backend/tests/test_layer3_page.py`;
- checker coverage in `tools/l3-progress-check.py`;
- proof/control record in `next_milestone_plans/layer3_progress_manifest.json`;
- proof/control record in `next_milestone_plans/layer3_workbench_proof_manifest.json`.

The proof validated `external_local_export_ready`, `external_local_export_written`, `external_local_export_replay`, status schema `layer3.external_local_export.status.v1`, durable history authority `durable_external_local_export_receipt_rows`, durable audit authority `durable_external_local_export_audit_event_rows`, idempotency conflict terms including `external_local_export_client_request_conflict` and `external_local_export_existing_output_conflict`, stale-authority and target-write-conflict projections, redacted `external-local-export://` refs, no rendered write controls, no raw local path exposure, and no caller-supplied destination path field.

## PR Review And Check State

- GitHub `backend-layer3-api` passed in `2m37s`.
- GitHub `test` passed in `3m23s`.
- PR comments were empty.
- PR reviews were empty.
- PR reviewThreads totalCount was `0`.
- Unresolved reviewThreads were `0`.
- Mergeability before merge was `MERGEABLE`.
- Merge state before merge was `CLEAN`.

## Non-Admission Boundary

This sync admits no new runtime behavior beyond PR `#1234` and no new rendered behavior beyond the read-only status/history proof already merged. It does not add real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credentials, network egress, provider-public delivery/use, raw public URL exposure, raw token exposure, caller-supplied destination paths or URLs, package mutation/reconstruction, source expansion/ingestion, RAG/vector behavior, qualitative-hybrid analysis runtime, broad auth/security behavior, full mockup activation, frontend-durable authority, or generic downstream dispatch.

## Required Sync Validation

This sync branch must pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

No headed/headless E2E rerun is required in this sync because PR `#1234` already supplied the rendered proof, and this sync changes only planning/control/checker metadata.

## Next Posture

The external local export lane is now ready to be treated as current-main proven after this sync merges. The next current-main-selected step is `select_package_mutation_reconstruction_named_operator_action_after_external_local_export_rendered_e2e_sync`.

That next pass must choose exactly one package mutation/reconstruction operator action before runtime, such as `revise_package`, `supersede_package`, or `rebuild_package_from_corrected_artifacts`, and must write the exact decision/freeze required by current-main authority before implementing any package mutation behavior.
