# 627 - Server-Configured External Local Export Directory Freeze Current-Main Sync

## Status

Status: current-main sync for `server_configured_external_local_export_directory_freeze`.

Doc: `627_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_FREEZE_CURRENT_MAIN_SYNC.md`.

Synced freeze doc: `626_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_FREEZE.md`.

Filled decision intake: `623_NEXT_EXTERNAL_SURFACE_DECISION_INTAKE.md`.

Prior objective audit: `625_LAYER3_OBJECTIVE_COMPLETION_AUDIT_AFTER_NEXT_EXTERNAL_SURFACE_INTAKE_SYNC.md`.

Freeze PR: `#1230`.

Freeze branch: `codex/l3-external-local-export-surface-freeze`.

Freeze branch commit: `cd4886c2f49ebd5c3a0356a00c7ebb62d3968b16`.

Freeze merge commit: `883cbeaf83e4922b91436f880697bca45ede97d9`.

Current-main checkpoint after merge: `883cbeaf83e4922b91436f880697bca45ede97d9`.

Runtime status: `current_main_synced_server_configured_external_local_export_directory_freeze_runtime_not_implemented`.

Selected next external surface: `server_configured_external_local_export_directory`.

Selected next external surface class: `server_configured_external_destination_write`.

Implementation-entry freeze written for next external surface: true.

Implementation-entry allowed next: true, but only for `implement_server_configured_external_local_export_directory_after_freeze_sync`.

Selected implementation action: `implement_server_configured_external_local_export_directory_after_freeze_sync`.

Live behavior change in sync: false.

## Merge Gate

GitHub `backend-layer3-api` passed in `2m40s`.

GitHub `test` passed in `3m7s`.

PR comments were empty.

PR reviews were empty.

PR reviewThreads totalCount was `0`.

Unresolved reviewThreads were `0`.

Mergeability before merge was `MERGEABLE`.

Merge state before merge was `CLEAN`.

## Current-Main Result

Current main now contains the operator-filled `623` next-surface decision and the separate `626` implementation-entry freeze for `server_configured_external_local_export_directory`.

The selected surface is a controlled server-configured local filesystem export directory outside app-owned staging for finalized Layer 3 Data Structuring & Processing outputs. The authority basis remains external export/download readiness plus connector-local durable receipt plus server-owned local outbox write receipt plus provider-private local-outbox handoff receipt where applicable.

The freeze now admits the next implementation pass, but only for the exact selected runtime slice:

```yaml
next_implementation_posture: implement_server_configured_external_local_export_directory_after_freeze_sync
owner_service_seam: backend/app/services/layer3_external_local_export.py
write_route: POST /api/v1/layer3/handoff/connector/local-outbox/external-local-export/write
status_route: GET /api/v1/layer3/handoff/connector/local-outbox/external-local-export/status/{external_local_export_receipt_id}
receipt_table: l3_external_local_export_receipt
audit_table: l3_external_local_export_audit_event
config_authority: LAYER3_EXTERNAL_LOCAL_EXPORT_DIR
```

This sync does not implement runtime. It only records that current-main authority now admits the bounded implementation slice above.

## Post-Merge Validation

These commands passed on merged current main before this sync branch was edited:

```powershell
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
```

This sync branch must also pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

## Non-Admission Boundary

This sync admits no runtime behavior, backend route behavior, service behavior, response-model shape change, schema/model/migration change, rendered UI behavior, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credential use, network egress, provider-public delivery/use, raw public URL exposure, raw token exposure, caller-supplied destination path/URL, package mutation/reconstruction, source expansion/ingestion, RAG/vector behavior, qualitative-hybrid analysis runtime, auth/security behavior, full mockup activation, frontend-durable authority, or generic downstream dispatch.

Blocked no-runtime terms remain explicit for the next implementation pass: no caller-supplied destination path/URL, no package mutation/reconstruction, no source expansion/ingestion, no RAG/vector behavior, and no qualitative-hybrid analysis runtime.

## Stop Conditions Before Implementation

Stop before implementation if the next pass:

- selects any surface beyond `server_configured_external_local_export_directory`;
- accepts caller-supplied local paths, destination paths, URLs, object keys, connector targets, credentials, or tokens;
- requires real connector invocation, ConnectorRun or ConnectorRunTarget creation, provider-public delivery/use, network egress, package mutation/reconstruction, source expansion/ingestion, RAG/vector behavior, qualitative-hybrid analysis runtime, broad auth/security behavior, full mockup activation, or frontend-durable authority;
- cannot identify the exact service, route, model, migration, config, and test owner files from the `626` freeze; or
- cannot prove redaction, idempotency, stale-authority failure, duplicate-output handling, disabled side effects, and isolated filesystem writes.

## Next Posture

The next whole-project posture is `implement_server_configured_external_local_export_directory_after_freeze_sync`.

Implementation is now admitted only for the exact selected server-configured external local export directory slice defined in `626_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_FREEZE.md`.
