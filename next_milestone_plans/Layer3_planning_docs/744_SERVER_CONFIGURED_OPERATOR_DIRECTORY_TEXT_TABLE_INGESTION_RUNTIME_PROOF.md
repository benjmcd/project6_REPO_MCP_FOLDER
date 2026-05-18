# 744 - Server Configured Operator Directory Text/Table Ingestion Runtime Proof

## Status

Status: branch-local runtime proof for `server_configured_operator_directory_text_table_ingestion`.

Doc: `744_SERVER_CONFIGURED_OPERATOR_DIRECTORY_TEXT_TABLE_INGESTION_RUNTIME_PROOF.md`.

Predecessor current-main sync doc: `743_SOURCE_EXPANSION_INGESTION_SOURCE_FAMILY_SELECTION_FREEZE_CURRENT_MAIN_SYNC.md`.

Implementation branch: `codex/l3-source-directory-ingestion`.

Current-main checkpoint before implementation: `f371f2c43d9578e9f909c6c705b35ac48ffc24fb`.

Selected source family: `server_configured_operator_directory_text_table_source_family`.

Runtime mode: `server_configured_operator_directory_text_table_ingestion`.

Config authority: `LAYER3_SOURCE_INGESTION_DIR`.

Runtime behavior change in this pass: `true`.

## Implemented Authority

The canonical durable authority is now:

- `L3SourceDirectoryIngestionBatch`; and
- `L3SourceDirectoryIngestionFile`.

The migration is `backend/alembic/versions/0034_layer3_source_directory_ingestion.py`.

The service owner is `backend/app/services/layer3_source_directory_ingestion.py`.

The API owner is `backend/app/api/layer3.py`.

The scan route is `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`.

The status route is `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`.

The boundary contract owner is `backend/app/services/layer3_source_boundary.py`.

The focused proof is `backend/tests/test_layer3_source_directory_ingestion.py`.

## Runtime Scope

The runtime records a server-configured operator directory batch and direct child file authorities only. It admits `.csv`, `.json`, `.txt`, and `.md` files under `LAYER3_SOURCE_INGESTION_DIR`.

The request contract admits only `client_request_id`, `operator_decision`, optional `source_family`, and optional `ingestion_mode`. Caller-supplied paths, URLs, glob patterns, recursive flags, and browser-supplied file bytes are rejected before runtime authority is written.

The service fails closed when `LAYER3_SOURCE_INGESTION_DIR` is unset, relative, missing, not a directory, inside app-owned storage, inside local-outbox staging, or inside external local export staging. It also fails closed on non-file direct children, symlinks, unsupported extensions, empty directories, empty files, oversized files, oversized batches, UTF-8 decode failure, JSON parse failure, duplicate conflicting relative names, and stale file identity while hashing.

Responses and status surfaces expose redacted refs only. They expose `server-configured://LAYER3_SOURCE_INGESTION_DIR`, relative names, hashes, sizes, media types, and durable authority IDs. They do not expose the configured root path, absolute local file paths, file bytes, source package payloads, provider URLs, tokens, connector credentials, or browser durable state.

The runtime proves same-request replay and same-basis new-request replay as `already_recorded`.

## Validation

Observed branch validation passed:

```powershell
python -m py_compile .\backend\app\services\layer3_source_directory_ingestion.py .\backend\app\api\layer3.py .\backend\app\models\models.py .\backend\alembic\versions\0034_layer3_source_directory_ingestion.py
python -m pytest .\backend\tests\test_layer3_source_directory_ingestion.py .\backend\tests\test_layer3_source_boundary.py .\backend\tests\test_layer3_source_intake.py .\backend\tests\test_layer3_model_exports.py .\backend\tests\test_layer3_api.py::test_layer3_forbidden_sentinel_openapi_fields_are_impossible -q
```

Observed results: compile pass; `29 passed`.

## Still Blocked

This runtime does not admit PDFs, OCR, Office documents, arbitrary binaries, archives, executable files, web connectors, arbitrary recursive ingestion, caller-supplied paths/URLs/globs, browser-supplied file bytes, local upload expansion, package construction, package payload rewrite, source `L3OutputPackage` mutation, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, RAG/vector indexing, qualitative-hybrid analysis runtime, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, or hidden LLM planning.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_server_configured_operator_directory_text_table_ingestion_runtime_proof`.

After current-main sync, the next exact posture is `select_source_directory_ingestion_downstream_material_or_index_authority_after_runtime_sync`.
