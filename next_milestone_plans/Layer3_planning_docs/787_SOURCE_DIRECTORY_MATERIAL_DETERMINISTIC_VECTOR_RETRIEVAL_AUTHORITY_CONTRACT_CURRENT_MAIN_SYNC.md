# 787 - Source Directory Material Deterministic Vector Retrieval Authority Contract Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_material_deterministic_vector_retrieval_authority_contract`.

Sync doc: `787_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_VECTOR_RETRIEVAL_AUTHORITY_CONTRACT_CURRENT_MAIN_SYNC.md`.

Sync branch: `codex/l3-vector-retrieval-contract-sync`.

Contract doc: `786_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_VECTOR_RETRIEVAL_AUTHORITY_CONTRACT.md`.

Contract PR: `#1391`.

Contract branch: `codex/l3-vector-retrieval-contract`.

Contract branch commit: `3725dc334c21007e1eac3a923f6a9fe6849df7ad`.

Contract merge commit: `526b428a1a16f10ae6c5fe1ce4431cd466ab7266`.

Current-main checkpoint after merge: `526b428a1a16f10ae6c5fe1ce4431cd466ab7266`.

Synced result: `current_main_synced_source_directory_material_deterministic_vector_retrieval_authority_contract`.

Runtime behavior introduced by contract PR: `false`.

Runtime behavior introduced by this sync: `false`.

## Merge Gate Evidence

PR `#1391` was review/check clear before merge:

- `backend-layer3-api`: `SUCCESS` in `3m10s`;
- `test`: `SUCCESS` in `3m26s`;
- comments totalCount: `0`;
- reviews totalCount: `0`;
- latestReviews totalCount: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`; and
- merge state before merge: `CLEAN`.

## Current-Main Sync Result

Current main now includes `786_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_VECTOR_RETRIEVAL_AUTHORITY_CONTRACT.md`.

Current main now records `source_directory_material_deterministic_vector_retrieval_authority` as the future vector retrieval authority.

Current main now records `deterministic_local_hash_vector_similarity_retrieval` as the future retrieval mode.

Current main now records `source_directory_material_deterministic_embedding_vector_index_authority`, `layer3.source_directory_embedding_vector_index.v1`, and `safe_vector_descriptors` as required future inputs.

Current main now records `backend/app/services/layer3_source_directory_vector_retrieval.py` and `backend/tests/test_layer3_source_directory_vector_retrieval.py` as the selected future implementation/proof surfaces.

Current main now records `layer3.source_directory_vector_retrieval.v1` as the future response schema.

Current main now records that the future runtime must call `source_directory_material_embedding_vector_index(db, vector_index_payload)` before scoring, validate `embedding_index_authority_hash`, use `source-directory-hash-vector-v1`, require `vector_dimensions == 4096`, compute deterministic normalized query-to-segment dot product scores, omit `vector_score <= 0` results without fallback, and keep row-write flags and negative invariants false.

## Validation

The current-main sync branch validated:

- JSON manifest load: `PASS`;
- `python -m py_compile .\tools\l3-progress-check.py`: `PASS`;
- `python .\tools\l3-progress-check.py`: `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`: `PASS`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_index.py -q`: `PASS`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_index.py .\backend\tests\test_layer3_source_directory_qualitative_analysis.py .\backend\tests\test_layer3_source_directory_context_packet.py .\backend\tests\test_layer3_source_directory_text_retrieval.py .\backend\tests\test_layer3_source_directory_ingestion.py -q`: `PASS`; and
- `git diff --check`: `PASS`.

## Non-Admission

No runtime behavior, backend route, API DTO, response model, database model, migration, durable vector-store row write, durable embedding row write, durable retrieval row write, vector database, persistent vector store, RAG execution, context-packet mutation, qualitative generation runtime, prompt/model/provider runtime, hidden LLM planning, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, source expansion, arbitrary source ingestion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, web connectors, raw local path exposure, or source `L3OutputPackage` mutation is admitted by this sync.

## Next Posture

The next exact current-main posture is `implement_source_directory_material_deterministic_vector_retrieval_authority_after_contract_sync`.

That next posture admits only the already-frozen deterministic local source-directory vector retrieval runtime slice, after current-main sync and review clearance.

Do not broaden into RAG execution, prompt/model/provider runtime, durable retrieval rows, vector stores, backend routes, package construction, package mutation, source expansion, rendered controls, provider/public delivery/use, connector/destination dispatch, network egress, credentials, auth/security broadening, or frontend-durable authority from this sync.
