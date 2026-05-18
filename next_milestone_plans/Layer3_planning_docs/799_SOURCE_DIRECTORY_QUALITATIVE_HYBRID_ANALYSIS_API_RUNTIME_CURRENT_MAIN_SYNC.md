# 799 - Source Directory Qualitative-Hybrid Analysis API Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_material_context_packet_qualitative_hybrid_analysis_api_runtime`.

Sync doc: `799_SOURCE_DIRECTORY_QUALITATIVE_HYBRID_ANALYSIS_API_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime doc: `798_SOURCE_DIRECTORY_QUALITATIVE_HYBRID_ANALYSIS_API_RUNTIME_ENTRY_FREEZE.md`.

Runtime PR: `#1403`.

Runtime branch: `codex/l3-qual-api`.

Runtime branch commit: `39dc407c91f70c811d8754f4ed22d4e3020e8610`.

Runtime merge commit: `578880feee19c69e9f2a70afce47e8a0d7822c48`.

Sync branch: `codex/l3-qual-api-sync`.

Synced result: `current_main_synced_source_directory_material_context_packet_qualitative_hybrid_analysis_api_runtime`.

Next posture: `select_next_named_layer3_end_to_end_gap_after_qualitative_hybrid_analysis_api_sync`.

## Current-Main Result

Current main now includes the bounded source-directory qualitative-hybrid analysis API runtime from doc `798`.

Current main includes:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis`;
- `Layer3SourceDirectoryQualitativeAnalysisRequest`;
- `Layer3SourceDirectoryQualitativeAnalysisResponse`;
- response schema `layer3.source_directory_qualitative_analysis.v1`;
- API owner `backend/app/api/layer3.py`; and
- proof owner `backend/tests/test_layer3_source_directory_qualitative_analysis.py`.

The current-main runtime is only a backend API wrapper over the already-synced deterministic extractive qualitative-hybrid analysis service `source_directory_material_context_packet_qualitative_hybrid_analysis(db, payload)`.

The selected source family remains `server_configured_operator_directory_text_table_source_family`.

The selected context-packet authority remains `source_directory_material_retrieval_augmented_context_packet_authority`.

The selected qualitative-hybrid authority remains `source_directory_material_context_packet_qualitative_hybrid_analysis_authority`.

## Merge Gate

PR `#1403` merged on 2026-05-18 at merge commit `578880feee19c69e9f2a70afce47e8a0d7822c48`.

Before merge:

- `backend-layer3-api`: `SUCCESS`, `3m11s`;
- `test`: `SUCCESS`, `3m39s`;
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
- `full_segment_text_exposed: False`;
- `raw_vector_exposed: False`;
- `embedding_exposed: False`;
- `durable_context_packet_rows_written: False`;
- `durable_qualitative_analysis_rows_written: False`;
- `durable_qualitative_generation_rows_written: False`;
- `durable_retrieval_rows_written: False`;
- `durable_vector_store_rows_written: False`;
- `durable_embedding_rows_written: False`;
- `new_rag_execution_enabled: False`;
- `vector_indexing_enabled: False`;
- `embedding_generation_enabled: False`;
- `prompt_model_provider_runtime_enabled: False`;
- `connector_dispatch_enabled: False`;
- `package_mutation_enabled: False`;
- `network_egress_enabled: False`; and
- `frontend_durable_authority_enabled: False`.

The current-main synced runtime rejects stale index authority, preserves text-index/source-material authority checks through the service path, rejects forbidden prompt/provider request fields, and does not expose raw local paths, full segment text, raw vectors, embeddings, prompt payloads, provider payloads, package payloads, connector payloads, source file bytes, or frontend state.

## Non-Admission Boundary

This current-main sync admits no new source family, arbitrary source ingestion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, archives, web connectors, caller-supplied paths, caller-supplied URLs, browser-supplied file bytes, local upload expansion, durable context-packet row write, durable qualitative-analysis row write, durable qualitative-generation row write, durable retrieval row write, durable vector-store row write, durable embedding row write, vector database, persistent vector store, new RAG execution, vector indexing, embedding generation, prompt/model/provider runtime, provider-public delivery/use broadening, provider-private signed URL generation/use, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, raw local path exposure, or source `L3OutputPackage` mutation.

## Validation

Current-main sync validation:

- `python -m pytest .\backend\tests\test_layer3_source_directory_qualitative_analysis.py -q` - `PASS`, `5 passed`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_qualitative_analysis.py .\backend\tests\test_layer3_source_directory_context_packet.py .\backend\tests\test_layer3_source_directory_text_retrieval.py .\backend\tests\test_layer3_source_directory_ingestion.py -q` - `PASS`, `26 passed`;
- `python -m pytest .\backend\tests\test_layer3_api.py -q` - `PASS`, `187 passed`;
- `python -c "import json; [json.load(open(p, encoding='utf-8')) for p in ['next_milestone_plans/layer3_progress_manifest.json','next_milestone_plans/layer3_workbench_proof_manifest.json']]; print('json manifests ok')"` - `PASS`;
- `python -m py_compile .\tools\l3-progress-check.py .\backend\app\api\layer3.py .\backend\tests\test_layer3_source_directory_qualitative_analysis.py` - `PASS`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`; and
- `git diff --check` - `PASS`.

## Next Posture

The source-directory qualitative-hybrid analysis API runtime lane is current-main synced.

Do not continue additional same-family source-directory qualitative-hybrid analysis API proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader.

The next major implementation-bearing lane should be selected from the remaining Layer 3 end-to-end gaps: package lifecycle/mutation/reconstruction, controlled handoff/export/delivery readers that are not yet synced, operator-visible review/status surfaces, provider-public real exposure only after exposure/security/revocation authority, real connector dispatch only after target/credential/network/receipt/auth authority, or retrieval/indexing expansion only after a new source/index authority is selected.
