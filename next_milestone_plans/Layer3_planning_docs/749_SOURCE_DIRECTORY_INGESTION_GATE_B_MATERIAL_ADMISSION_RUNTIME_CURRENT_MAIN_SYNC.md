# 749 - Source Directory Ingestion Gate B Material Admission Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_ingestion_gate_b_material_admission_runtime_proof`.

Doc: `749_SOURCE_DIRECTORY_INGESTION_GATE_B_MATERIAL_ADMISSION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Synced runtime doc: `748_SOURCE_DIRECTORY_INGESTION_GATE_B_MATERIAL_ADMISSION_RUNTIME_PROOF.md`.

Runtime PR: `#1353`.

Runtime branch: `codex/l3-source-directory-material-admission`.

Runtime branch commits: `ae0c085ac507065650b3b0a10a4cd09cd7be9c09`, `61af65dde27ca4a6190b162b7d27ad6311e52ec7`.

Runtime merge commit: `8e5a2814d4c63e0ee092169b124a26e1271ae2fc`.

Current-main checkpoint after merge: `8e5a2814d4c63e0ee092169b124a26e1271ae2fc`.

Sync branch: `codex/l3-source-directory-material-admission-sync`.

Synced result: `current_main_synced_source_directory_ingestion_gate_b_material_admission_runtime`.

Runtime behavior introduced by runtime proof: `true`.

Runtime behavior in this sync: `false`.

## Merge Gate

Current external PR evidence for `#1353` after merge shows:

- state: `MERGED`;
- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- comments: `0`;
- review threads: `3`, all resolved;
- head commit: `61af65dde27ca4a6190b162b7d27ad6311e52ec7`; and
- merge commit: `8e5a2814d4c63e0ee092169b124a26e1271ae2fc`.

The first CI run stalled during `Install Playwright Browsers`; it was canceled and rerun. The rerun passed both checks.

## Sync Validation

This sync is guarded by `python .\tools\l3-progress-check.py` and `python .\tools\l3-target-selection-validate.py --expect frozen`.

## Current-Main Result

Current main now includes bounded source-directory Gate B material admission.

The source-directory material-preview route is `POST /api/v1/layer3/source/ingestion/server-configured-directory/material-preview`.

The reused Gate B route is `POST /api/v1/layer3/gate-b/decision`.

The runtime owner service is `backend/app/services/layer3_source_directory_material_admission.py`.

The source-boundary owner is `backend/app/services/layer3_source_boundary.py`.

The typing owner is `backend/app/services/layer3_typing_entry.py`.

The canonical upstream authorities are `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile`.

The admitted material candidate source class is `server_configured_directory_file`.

Current main proves:

- material preview requires persisted batch/file ids plus `file_identity_hash` and `authority_basis_hash`;
- material preview revalidates live file identity before emitting Gate B basis;
- source-directory configuration drift and live file read errors fail closed as material-admission errors;
- Gate B validates `server_configured_directory_file` decision basis before commit;
- Gate B persists a `server_configured_directory_file` `L3MaterialSnapshot`;
- Gate C preview types `server_configured_directory_file` as `document_chunks` / `qualitative`; and
- no `ConnectorRun`, `ConnectorRunTarget`, or `L3OutputPackage` rows are created by the material-admission proof.

## Still Blocked

This sync admits no additional runtime behavior, backend route behavior, service behavior, model change, migration, rendered UI control, source package row mutation, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, RAG/vector indexing, qualitative-hybrid analysis runtime, auth/security broadening, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, or source `L3OutputPackage` mutation.

## Next Posture

The exact source-directory material-admission reader is now cleanly synced through current main.

Under the pivot rule, do not continue additional same-family source-directory package/export/active-authority proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader.

The next major deferred lane is `select_rag_vector_or_qualitative_hybrid_authority_after_source_directory_material_admission_sync` only if current-main authority explicitly selects the source/index authority for that next requirement. Otherwise, first freeze the next exact source/index or qualitative-hybrid authority before any implementation.
