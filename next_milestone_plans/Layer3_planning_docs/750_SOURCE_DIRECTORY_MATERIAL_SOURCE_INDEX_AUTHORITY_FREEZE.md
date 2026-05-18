# 750 - Source Directory Material Source Index Authority Freeze

## Status

Status: branch-local source/index authority selection freeze for `source_directory_material_source_index_authority`.

Doc: `750_SOURCE_DIRECTORY_MATERIAL_SOURCE_INDEX_AUTHORITY_FREEZE.md`.

Planning branch: `codex/l3-source-index-freeze`.

Current-main checkpoint before freeze: `11a027b3f8a97b9b628a09c0acc6d08ba547c3b6`.

Predecessor current-main sync doc: `749_SOURCE_DIRECTORY_INGESTION_GATE_B_MATERIAL_ADMISSION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_source_directory_ingestion_gate_b_material_admission_runtime`.

Selected next posture from predecessor: `select_rag_vector_or_qualitative_hybrid_authority_after_source_directory_material_admission_sync`.

Selected exact next authority question: `source_directory_material_source_index_authority_contract`.

Runtime behavior introduced by this freeze: `false`.

## Repo-Confirmed Authority

Current main proves bounded source-directory material admission through:

- canonical upstream authorities `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile`;
- material authority `L3MaterialSnapshot` with source shape `server_configured_directory_file`;
- material-preview route `POST /api/v1/layer3/source/ingestion/server-configured-directory/material-preview`;
- Gate B route reuse `POST /api/v1/layer3/gate-b/decision`; and
- Gate C typing as `document_chunks` / `qualitative`.

Current main also proves the next source/index surface is not yet admitted:

- `backend/app/services/layer3_source_boundary.py` still reports `rag_vector_enabled: False`;
- `backend/app/services/layer3_source_directory_material_admission.py` still reports `eligible_for_rag_vector_index: False`;
- `backend/app/services/layer3_qual_aps_execution.py` still reports `hybrid_execution_enabled: False` and `rag_vector_retrieval_enabled: False`; and
- `backend/app/services/aps_retrieval_plane_contract.py` is APS-specific retrieval authority over `ApsRetrievalChunk`, not a source-directory `server_configured_directory_file` index authority.

## Frozen Selection

This freeze selects `source_directory_material_source_index_authority_contract` as the next exact planning/control artifact.

That contract must select the source/index authority before any RAG/vector or qualitative-hybrid runtime work. At minimum it must decide:

- canonical source/index inputs for `server_configured_directory_file` material snapshots;
- whether the first source/index substrate is deterministic lexical/text authority, vector authority, or no-runtime blocked state;
- the durable owner, if any, for source/index identity, source hashes, material snapshot references, and stale-authority checks;
- whether a route, service, model, migration, or validate-only helper is admitted;
- how source/index rows, if admitted later, remain tied to `L3SourceDirectoryIngestionFile` and `L3MaterialSnapshot` authority;
- how the contract prevents embeddings, provider/model calls, hidden LLM planning, arbitrary source expansion, and frontend-only durable authority; and
- the exact proof stack required before any later RAG/vector or qualitative-hybrid runtime.

## Still Blocked

This freeze admits no runtime behavior, backend route behavior, service behavior, model change, migration, rendered UI control, source/index rows, vector index, embedding generation, retrieval query, qualitative-hybrid analysis runtime, qualitative broadening, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, or source `L3OutputPackage` mutation.

## Next Posture

The next exact posture after merge is `current_main_sync_source_directory_material_source_index_authority_freeze`.

After that sync, the next exact posture is `write_source_directory_material_source_index_authority_contract_before_rag_vector_or_qualitative_hybrid_runtime`.
