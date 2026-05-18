# 743 - Source Expansion Ingestion Source Family Selection Freeze Current-Main Sync

## Status

Status: current-main proof/control sync for `source_expansion_ingestion_source_family_selection_freeze`.

Doc: `743_SOURCE_EXPANSION_INGESTION_SOURCE_FAMILY_SELECTION_FREEZE_CURRENT_MAIN_SYNC.md`.

Synced freeze doc: `742_SOURCE_EXPANSION_INGESTION_SOURCE_FAMILY_SELECTION_FREEZE.md`.

Freeze PR: `#1347`.

Freeze branch: `codex/l3-source-family-selection`.

Freeze branch commit: `3b9ebead55b72c52c25a88de3130436d84e81c61`.

Freeze merge commit: `cf014d39fd093050aa1bbc183323cb26906fb3f9`.

Current-main checkpoint after merge: `cf014d39fd093050aa1bbc183323cb26906fb3f9`.

Sync branch: `codex/l3-source-family-selection-sync`.

Synced result: `current_main_synced_source_expansion_ingestion_source_family_selection_freeze`.

Selected source family now synced: `server_configured_operator_directory_text_table_source_family`.

Runtime behavior introduced by freeze: `false`.

Runtime behavior in this sync: `false`.

## Merge Gate

Current external PR evidence for `#1347` after merge shows:

- state: `MERGED`;
- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- comments: `0`;
- reviews: `0`;
- latest reviews: `0`;
- reviewThreads: `0`;
- head commit: `3b9ebead55b72c52c25a88de3130436d84e81c61`; and
- merge commit: `cf014d39fd093050aa1bbc183323cb26906fb3f9`.

Post-merge current-main validation at `cf014d39fd093050aa1bbc183323cb26906fb3f9` passed:

```powershell
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
```

Observed results: Layer 3 progress state check `PASS`; Layer 3 target-selection validation `PASS (frozen)`.

## Current-Main Result

Current main now records `server_configured_operator_directory_text_table_source_family` as the selected source expansion/ingestion family.

Current main records that the next implementation entry is exactly `server_configured_operator_directory_text_table_ingestion`.

The selected config authority is `LAYER3_SOURCE_INGESTION_DIR`.

The candidate implementation owner remains `backend/app/services/layer3_source_directory_ingestion.py`.

The candidate API owner remains `backend/app/api/layer3.py`.

The candidate scan route remains `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`.

The candidate status route remains `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`.

The future durable authorities remain `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile`.

The synced freeze admits only direct child `.csv`, `.json`, `.txt`, and `.md` files under the server-configured operator directory. The source root must be selected by server/operator configuration, not by browser request or caller payload. Recursive traversal is not admitted.

The synced freeze requires future runtime to fail closed when `LAYER3_SOURCE_INGESTION_DIR` is unset, relative, missing, not a directory, inside app-owned storage, or inside local-outbox/export staging. It also requires rejection of caller-supplied paths, URLs, glob patterns, recursive flags, browser-supplied file bytes, unsupported file types, path escape, symlinks, empty eligible directories, stale file identity, oversized files/batches, and non-text decoding failure.

## Still Blocked

This sync admits no runtime behavior by itself. PDFs, OCR, Office documents, arbitrary binaries, archives, executable files, web connectors, arbitrary recursive ingestion, caller-supplied paths/URLs/globs, browser-supplied file bytes, local upload expansion, package construction, package payload rewrite, source `L3OutputPackage` mutation, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, RAG/vector indexing, qualitative-hybrid analysis runtime, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, and hidden LLM planning remain blocked.

## Next Posture

The next exact current-main posture is `implement_server_configured_operator_directory_text_table_ingestion_after_source_family_selection_sync`.

That implementation slice must stay bounded to the synced source family and must not admit PDFs, OCR, Office documents, arbitrary binaries, web connectors, arbitrary recursive ingestion, RAG/vector indexing, package mutation/rewrite, connector dispatch, provider-public behavior, credentialed network behavior, auth/security broadening, rendered controls, or frontend-durable authority unless separately selected and frozen.
