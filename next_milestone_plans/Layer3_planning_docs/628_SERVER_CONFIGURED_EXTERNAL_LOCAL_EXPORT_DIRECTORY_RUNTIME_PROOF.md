# 628 - Server-Configured External Local Export Directory Runtime Proof

## Status

Status: runtime implementation proof for `server_configured_external_local_export_directory`.

Doc: `628_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_RUNTIME_PROOF.md`.

Implementation-entry freeze: `626_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_FREEZE.md`.

Freeze current-main sync: `627_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_FREEZE_CURRENT_MAIN_SYNC.md`.

Runtime branch: `codex/l3-external-local-export-runtime`.

Current-main checkpoint before implementation: `98a8e3657dcd0ea375838c56a94d1dd3e6d91fd9`.

Selected implementation action: `implement_server_configured_external_local_export_directory_after_freeze_sync`.

Selected next external surface: `server_configured_external_local_export_directory`.

Selected next external surface class: `server_configured_external_destination_write`.

Runtime status after implementation: `server_configured_external_local_export_directory_runtime_implemented_branch_local`.

Layer 3 placement: Data Structuring & Processing export/write boundary.

Live behavior change in this pass: true, limited to the admitted server-configured external local export directory runtime.

## Implemented Runtime Slice

This pass implements exactly the runtime tranche admitted by doc `626` and synced by doc `627`:

- service `backend/app/services/layer3_external_local_export.py`;
- route/model wiring in `backend/app/api/layer3.py`;
- config setting `LAYER3_EXTERNAL_LOCAL_EXPORT_DIR` in `backend/app/core/config.py`;
- durable receipt model/table `l3_external_local_export_receipt`;
- durable audit model/table `l3_external_local_export_audit_event`;
- Alembic migration `backend/alembic/versions/0030_layer3_external_local_export.py`;
- read-only session summary/status/history projection through `backend/app/services/layer3_workbench.py`; and
- targeted API/backend proof in `backend/tests/test_layer3_api.py`.

No rendered write/status UI was changed in this pass, so headed/headless E2E proof was not required for rendered behavior.

## Runtime Contract Proven

The write route is:

`POST /api/v1/layer3/handoff/connector/local-outbox/external-local-export/write`

The status route is:

`GET /api/v1/layer3/handoff/connector/local-outbox/external-local-export/status/{external_local_export_receipt_id}`

The admitted target identity is `server_configured_external_local_export_directory`.

The admitted target class is `server_configured_external_destination_write`.

The admitted dispatch mode is `server_configured_external_local_export_directory_write`.

The admitted operator decision is `write_server_configured_external_local_export_directory`.

Responses expose only redacted refs such as `external-local-export://<receipt_id>/artifact.json` and `external-local-export://<receipt_id>/manifest.json`; they do not expose raw local paths.

The service requires existing external export/download readiness, connector-local durable receipt authority, server-owned local outbox target/write authority, and provider-private local-outbox handoff authority where applicable.

## Lifecycle, Idempotency, And Failure Proof

The targeted backend proof covers:

- `test_layer3_api_external_local_export_write_status_and_idempotency`;
- `test_layer3_api_external_local_export_prechecks_fail_closed`;
- write success from existing server-owned local outbox write authority;
- status success from the durable external local export receipt;
- read-only session summary projection with `read_only_external_local_export_status_history`;
- same `client_request_id` plus same basis returning the same receipt/status as `external_local_export_replay`;
- same `client_request_id` plus different basis failing closed as `external_local_export_client_request_conflict`;
- same basis plus different `client_request_id` returning the existing receipt/status instead of duplicate output;
- missing provider-private handoff where applicable failing closed as `external_local_export_requires_provider_private_handoff`;
- stale/tampered artifact authority failing closed as `external_local_export_stale_authority`;
- unavailable configured destination failing closed as `external_local_export_directory_unavailable`;
- duplicate target conflicting output failing closed as `external_local_export_existing_output_conflict`;
- no raw path exposure in responses, status, summary, or configured-directory failures; and
- database counts proving no `ConnectorRun`, `ConnectorRunTarget`, package, source, or RAG/vector side effects.

## Non-Admission Boundary

This implementation does not add real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credentials, network egress, provider-public delivery/use, raw public URL exposure, raw token exposure, arbitrary caller-supplied path or URL support, package mutation/reconstruction, source expansion/ingestion, RAG/vector behavior, qualitative-hybrid analysis runtime, broad auth/security behavior, full mockup activation, frontend-durable authority, or generic downstream dispatch.

Explicit no-go terms remain active: no real connector invocation, no source expansion/ingestion, no RAG/vector behavior, and no qualitative-hybrid analysis runtime.

Requests containing `destination_path`, `destination_url`, credentials, connector-run ids, package payloads, source expansion fields, RAG/vector fields, prompt/model payloads, auth/security overrides, retry/rerun/cancel fields, or frontend-durable authority fields fail closed.

## Validation

The implementation-bearing branch must pass:

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

## Next Posture

The next whole-project posture after this runtime proof merges is `await_current_main_sync_for_server_configured_external_local_export_directory_runtime`.

After current-main sync, the next product decision should choose one separately frozen action from the remaining operator direction: package mutation/reconstruction, source expansion/ingestion, RAG/vector or qualitative-hybrid analysis, provider-public delivery/use, or a real connector/destination target. None of those are admitted by this runtime proof.
