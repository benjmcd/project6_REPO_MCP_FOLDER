# 745 - Server Configured Operator Directory Text/Table Ingestion Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `server_configured_operator_directory_text_table_ingestion_runtime_proof`.

Doc: `745_SERVER_CONFIGURED_OPERATOR_DIRECTORY_TEXT_TABLE_INGESTION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Synced runtime doc: `744_SERVER_CONFIGURED_OPERATOR_DIRECTORY_TEXT_TABLE_INGESTION_RUNTIME_PROOF.md`.

Runtime PR: `#1349`.

Runtime branch: `codex/l3-source-directory-ingestion`.

Runtime branch commit: `903462a80082aa2b7489d867f249e72f6589c6ce`.

Runtime merge commit: `be89cd042af5e39e23cdbf01d092799d13b83767`.

Current-main checkpoint after merge: `be89cd042af5e39e23cdbf01d092799d13b83767`.

Sync branch: `codex/l3-source-directory-ingestion-sync`.

Synced result: `current_main_synced_server_configured_operator_directory_text_table_ingestion_runtime`.

Runtime behavior introduced by runtime proof: `true`.

Runtime behavior in this sync: `false`.

## Merge Gate

Current external PR evidence for `#1349` after merge shows:

- state: `MERGED`;
- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- comments: `0`;
- reviews: `0`;
- latest reviews: `0`;
- reviewThreads: `0`;
- head commit: `903462a80082aa2b7489d867f249e72f6589c6ce`; and
- merge commit: `be89cd042af5e39e23cdbf01d092799d13b83767`.

Post-merge current-main validation at `be89cd042af5e39e23cdbf01d092799d13b83767` passed:

```powershell
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
python -m pytest .\backend\tests\test_layer3_source_directory_ingestion.py .\backend\tests\test_layer3_source_boundary.py .\backend\tests\test_layer3_source_intake.py .\backend\tests\test_layer3_model_exports.py .\backend\tests\test_layer3_api.py::test_layer3_forbidden_sentinel_openapi_fields_are_impossible -q
```

Observed results: Layer 3 progress state check `PASS`; Layer 3 target-selection validation `PASS (frozen)`; focused runtime/API tests `29 passed`.

## Current-Main Result

Current main now includes bounded server-configured operator directory text/table ingestion runtime.

The canonical durable authorities are `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile`.

The migration is `backend/alembic/versions/0034_layer3_source_directory_ingestion.py`.

The canonical service authority is `backend/app/services/layer3_source_directory_ingestion.py`.

The API owner is `backend/app/api/layer3.py`.

The admitted scan route is `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`.

The admitted status route is `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`.

The runtime remains bounded to direct child `.csv`, `.json`, `.txt`, and `.md` files under server/operator-configured `LAYER3_SOURCE_INGESTION_DIR`. It exposes redacted `server-configured://LAYER3_SOURCE_INGESTION_DIR` refs, relative names, hashes, sizes, media types, and durable authority IDs, not raw local paths or file bytes.

The synced runtime proves same-request replay and same-basis new-request replay as `already_recorded`, creates no `ConnectorRun`, `ConnectorRunTarget`, or `L3OutputPackage` rows, and keeps downstream material/index authority separate.

## Still Blocked

This sync admits no additional runtime or rendered behavior. PDFs, OCR, Office documents, arbitrary binaries, archives, executable files, web connectors, arbitrary recursive ingestion, caller-supplied paths/URLs/globs, browser-supplied file bytes, local upload expansion, package construction, package payload rewrite, source `L3OutputPackage` mutation, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, RAG/vector indexing, qualitative-hybrid analysis runtime, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, and hidden LLM planning remain blocked.

## Next Posture

The next exact current-main posture is `select_source_directory_ingestion_downstream_material_or_index_authority_after_runtime_sync`.

That posture should select the next source-directory-ingestion downstream authority before any material admission, RAG/vector indexing, qualitative-hybrid analysis, package construction, rendered controls, or frontend-durable authority is implemented.
