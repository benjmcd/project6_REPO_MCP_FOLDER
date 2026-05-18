# 797 - Source Directory Vector Retrieval API Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_material_vector_retrieval_api_runtime`.

Sync doc: `797_SOURCE_DIRECTORY_VECTOR_RETRIEVAL_API_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime doc: `796_SOURCE_DIRECTORY_VECTOR_RETRIEVAL_API_RUNTIME_ENTRY_FREEZE.md`.

Runtime PR: `#1401`.

Runtime branch: `codex/l3-source-ingest-family`.

Runtime branch commit: `96e0b7ef72aeb89bbadc7b3b2e729bf207c3a25b`.

Runtime merge commit: `9c546460f2dd46c6d7a44479fa5a7c6ced3cc469`.

Sync branch: `codex/l3-vector-api-sync`.

Synced result: `current_main_synced_source_directory_material_vector_retrieval_api_runtime`.

Next posture: `select_source_directory_qualitative_hybrid_analysis_api_surface_after_vector_retrieval_api_sync`.

## Current-Main Result

Current main now includes the bounded source-directory vector retrieval API runtime from doc `796`.

Current main includes:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/vector-retrieval`;
- `Layer3SourceDirectoryVectorRetrievalRequest`;
- `Layer3SourceDirectoryVectorRetrievalResponse`;
- response schema `layer3.source_directory_vector_retrieval.v1`;
- API owner `backend/app/api/layer3.py`; and
- proof owner `backend/tests/test_layer3_source_directory_vector_retrieval.py`.

The current-main runtime is only a backend API wrapper over the already-synced deterministic local vector retrieval service `source_directory_material_vector_retrieval(db, payload)`.

The selected source family remains `server_configured_operator_directory_text_table_source_family`.

The selected retrieval authority remains `source_directory_material_deterministic_vector_retrieval_authority`.

## Merge Gate

PR `#1401` merged on 2026-05-18 at merge commit `9c546460f2dd46c6d7a44479fa5a7c6ced3cc469`.

Before merge:

- `backend-layer3-api`: `SUCCESS`, `3m2s`;
- `test`: `SUCCESS`, `3m28s`;
- PR comments: `0`;
- PR reviews: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`; and
- merge state: `CLEAN`.

## Runtime Behavior

Runtime behavior introduced by implementation PR: `true`.

Runtime behavior introduced by this sync: `false`.

The current-main synced runtime preserves:

- `raw_local_path_exposed: False`;
- `raw_vector_exposed: False`;
- `normalized_features_exposed: False`;
- `durable_vector_store_rows_written: False`;
- `durable_embedding_rows_written: False`;
- `durable_retrieval_rows_written: False`;
- `rag_execution_enabled: False`;
- `prompt_model_provider_runtime_enabled: False`;
- `connector_dispatch_enabled: False`;
- `package_mutation_enabled: False`;
- `network_egress_enabled: False`; and
- `frontend_durable_authority_enabled: False`.

The current-main synced runtime rejects stale embedding authority, preserves text/vector/source-material authority checks through the service path, rejects forbidden prompt/provider request fields, and does not expose raw local paths, raw vectors, normalized feature maps, prompt payloads, provider payloads, package payloads, connector payloads, source file bytes, or frontend state.

## Non-Admission Boundary

This current-main sync admits no new source family, arbitrary source ingestion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, archives, web connectors, caller-supplied paths, caller-supplied URLs, browser-supplied file bytes, local upload expansion, durable vector-store row write, durable embedding row write, durable retrieval row write, vector database, persistent vector store, RAG execution, context-packet mutation, qualitative generation runtime, prompt/model/provider runtime, provider-public delivery/use broadening, provider-private signed URL generation/use, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, raw local path exposure, or source `L3OutputPackage` mutation.

## Validation

Current-main sync validation:

- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py -q` - `PASS`, `5 passed`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_source_directory_vector_index.py .\backend\tests\test_layer3_source_directory_qualitative_analysis.py .\backend\tests\test_layer3_source_directory_context_packet.py .\backend\tests\test_layer3_source_directory_text_retrieval.py .\backend\tests\test_layer3_source_directory_ingestion.py -q` - `PASS`, `34 passed`;
- `python -m pytest .\backend\tests\test_layer3_api.py -q` - `PASS`, `187 passed`;
- `python -c "import json; [json.load(open(p, encoding='utf-8')) for p in ['next_milestone_plans/layer3_progress_manifest.json','next_milestone_plans/layer3_workbench_proof_manifest.json']]; print('json manifests ok')"` - `PASS`;
- `python -m py_compile .\tools\l3-progress-check.py .\backend\app\api\layer3.py .\backend\tests\test_layer3_source_directory_vector_retrieval.py` - `PASS`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`; and
- `git diff --check` - `PASS`.

## Next Posture

The source-directory vector retrieval API runtime lane is current-main synced.

Do not continue additional same-family source-directory vector retrieval API proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader.

The next major implementation-bearing lane is `select_source_directory_qualitative_hybrid_analysis_api_surface_after_vector_retrieval_api_sync`, because current main already has service-level qualitative-hybrid analysis over source-directory context packets but no backend API surface for that analysis runtime.
