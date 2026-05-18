# 747 - Source Directory Ingestion Downstream Material Authority Freeze Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_ingestion_downstream_material_authority_freeze`.

Doc: `747_SOURCE_DIRECTORY_INGESTION_DOWNSTREAM_MATERIAL_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC.md`.

Synced freeze doc: `746_SOURCE_DIRECTORY_INGESTION_DOWNSTREAM_MATERIAL_AUTHORITY_FREEZE.md`.

Freeze PR: `#1351`.

Freeze branch: `codex/l3-source-directory-downstream-selection`.

Freeze branch commit: `7044b977ce350cf989dda42909f92c8791c69e6c`.

Freeze merge commit: `950a419e25474bf64354cdfdaff066ac7b786744`.

Current-main checkpoint after merge: `950a419e25474bf64354cdfdaff066ac7b786744`.

Sync branch: `codex/l3-source-directory-downstream-selection-sync`.

Synced result: `current_main_synced_source_directory_ingestion_downstream_material_authority_freeze`.

Runtime behavior introduced by freeze: `false`.

Runtime behavior in this sync: `false`.

## Merge Gate

Current external PR evidence for `#1351` after merge shows:

- state: `MERGED`;
- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- comments: `0`;
- reviews: `0`;
- latest reviews: `0`;
- reviewThreads: `0`;
- head commit: `7044b977ce350cf989dda42909f92c8791c69e6c`; and
- merge commit: `950a419e25474bf64354cdfdaff066ac7b786744`.

Post-merge current-main validation at `950a419e25474bf64354cdfdaff066ac7b786744` passed:

```powershell
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
```

Observed results: Layer 3 progress state check `PASS`; Layer 3 target-selection validation `PASS (frozen)`.

## Current-Main Result

Current main now records `source_directory_ingestion_gate_b_material_admission` as the selected downstream material authority after server-configured source-directory ingestion runtime.

The selected upstream runtime remains `server_configured_operator_directory_text_table_ingestion`.

The selected source family remains `server_configured_operator_directory_text_table_source_family`.

The selected downstream family is `source_directory_ingestion_material_authority`.

The selected downstream authority is `gate_b_material_candidate_from_source_directory_ingestion_file`.

The canonical upstream authorities are `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile`.

The future owner service is `backend/app/services/layer3_source_directory_material_admission.py`.

The future API owner is `backend/app/api/layer3.py`.

The future material-preview route is `POST /api/v1/layer3/source/ingestion/server-configured-directory/material-preview`.

The future Gate B route reuse is `POST /api/v1/layer3/gate-b/decision`.

## Still Blocked

This sync admits no runtime behavior, backend route behavior, service behavior, model change, migration, rendered UI control, source package row mutation, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, RAG/vector indexing, qualitative-hybrid analysis runtime, auth/security broadening, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, or source `L3OutputPackage` mutation.

## Next Posture

The next exact current-main posture is `implement_source_directory_ingestion_gate_b_material_admission_after_downstream_selection_sync`.

That posture may implement only the selected downstream material authority over persisted `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile` rows. It must not implement RAG/vector indexing, qualitative-hybrid analysis, package construction, rendered controls, frontend-durable authority, connector dispatch, provider URL behavior, recursive ingestion, arbitrary path access, or source-family expansion beyond the persisted source-directory batch/file authorities.
