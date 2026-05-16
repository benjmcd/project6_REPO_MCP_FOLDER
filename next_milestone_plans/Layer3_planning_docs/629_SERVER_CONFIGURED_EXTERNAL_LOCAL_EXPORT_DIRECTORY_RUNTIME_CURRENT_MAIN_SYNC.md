# 629 - Server-Configured External Local Export Directory Runtime Current-Main Sync

## Status

Status: current-main sync for `server_configured_external_local_export_directory_runtime`.

Doc: `629_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `628_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_RUNTIME_PROOF.md`.

Implementation-entry freeze: `626_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_FREEZE.md`.

Freeze current-main sync: `627_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_FREEZE_CURRENT_MAIN_SYNC.md`.

Runtime PR: `#1232`.

Runtime branch: `codex/l3-external-local-export-runtime`.

Runtime branch commit: `eb5b0a29d8e7810cbc1a6d917cd920d0e9995d34`.

Runtime merge commit: `a47b1b2c0c7d2c611443a7bb0adbcbaa7f1997c7`.

Current-main checkpoint after merge: `a47b1b2c0c7d2c611443a7bb0adbcbaa7f1997c7`.

Selected next external surface: `server_configured_external_local_export_directory`.

Selected next external surface class: `server_configured_external_destination_write`.

Selected implementation action completed: `implement_server_configured_external_local_export_directory_after_freeze_sync`.

Runtime status: `current_main_synced_server_configured_external_local_export_directory_runtime`.

Layer 3 placement: Data Structuring & Processing export/write boundary.

Live behavior change in sync: false.

## Merge Gate

GitHub `backend-layer3-api` passed in `2m29s`.

GitHub `test` passed in `3m0s`.

PR comments were empty.

PR reviews were empty.

PR reviewThreads totalCount was `0`.

Unresolved reviewThreads were `0`.

Mergeability before merge was `MERGEABLE`.

Merge state before merge was `CLEAN`.

## Current-Main Result

Current main now contains the selected server-configured external local export directory runtime:

```yaml
runtime_service: backend/app/services/layer3_external_local_export.py
write_route: POST /api/v1/layer3/handoff/connector/local-outbox/external-local-export/write
status_route: GET /api/v1/layer3/handoff/connector/local-outbox/external-local-export/status/{external_local_export_receipt_id}
config_authority: LAYER3_EXTERNAL_LOCAL_EXPORT_DIR
receipt_table: l3_external_local_export_receipt
audit_table: l3_external_local_export_audit_event
migration: backend/alembic/versions/0030_layer3_external_local_export.py
status_surface: read_only_external_local_export_status_history
redacted_ref_scheme: external-local-export://
```

The current-main runtime writes the finalized Layer 3 outbox artifact and manifest to one server-configured external local filesystem export directory outside app-owned staging after external export/download readiness, connector-local receipt, server-owned local outbox write receipt, and provider-private local-outbox handoff receipt where applicable.

The current-main proof covers write/status, OpenAPI schema, read-only status/history projection, idempotency, stale authority, missing provider-private handoff where applicable, unavailable configured destination as `external_local_export_directory_unavailable`, conflicting existing target output as `external_local_export_existing_output_conflict`, and redaction of raw local paths.

## Post-Merge Validation

These validations passed on the implementation branch before merge:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
python -m py_compile .\backend\app\services\layer3_external_local_export.py .\backend\app\services\layer3_workbench.py .\backend\app\api\layer3.py .\backend\app\models\models.py .\backend\app\core\config.py .\backend\alembic\versions\0030_layer3_external_local_export.py .\backend\tests\test_layer3_api.py
python -m pytest .\backend\tests\test_layer3_api.py -k "external_local_export or provider_private_signed_url_openapi_prepare_status_schema or forbidden_sentinel_openapi_fields_are_impossible" -q
git diff --check
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

This sync admits no new runtime behavior beyond PR `#1232`. It does not add real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credentials, network egress, provider-public delivery/use, raw public URL exposure, raw token exposure, caller-supplied destination paths or URLs, package mutation/reconstruction, source expansion/ingestion, RAG/vector behavior, qualitative-hybrid analysis runtime, broad auth/security behavior, full mockup activation, frontend-durable authority, or generic downstream dispatch.

## Next Posture

The next whole-project posture is `await_named_next_layer3_action_after_external_local_export_runtime_current_main_sync`.

The next implementation-bearing pass must name and freeze exactly one next action before code. The likely remaining operator directions are package mutation/reconstruction, source expansion/ingestion, RAG/vector or qualitative-hybrid analysis, provider-public delivery/use, or a real connector/destination target. None of those are admitted by this sync.
