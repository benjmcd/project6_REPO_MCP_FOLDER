# 789 - Source Directory Material Deterministic Vector Retrieval Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_material_deterministic_vector_retrieval_runtime_proof`.

Sync doc: `789_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_VECTOR_RETRIEVAL_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `788_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_VECTOR_RETRIEVAL_RUNTIME_PROOF.md`.

Runtime PR: `#1393`.

Runtime branch: `codex/l3-vector-retrieval-runtime`.

Runtime branch commit: `1428cac062ae3f4a4ea52d2dea10c73d004595b5`.

Runtime merge commit and current-main checkpoint: `261c995c7330952bf01fa5b43202fd4445dbb5ea`.

Sync branch: `codex/l3-vector-retrieval-runtime-sync`.

Synced result: `current_main_synced_source_directory_material_deterministic_vector_retrieval_runtime`.

Runtime behavior already merged by runtime PR: `true`.

Runtime behavior introduced by this sync: `false`.

## Merge Gate

PR `#1393` merged cleanly after adding `source_directory_material_deterministic_vector_retrieval_runtime_proof`.

The merge gate was:

- `backend-layer3-api`: `SUCCESS`, `3m15s`;
- `test`: `SUCCESS`, `3m38s`;
- comments totalCount: `0`;
- reviews totalCount: `0`;
- latestReviews totalCount: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`; and
- merge state before merge: `CLEAN`.

## Current-Main Result

Current main now includes `788_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_VECTOR_RETRIEVAL_RUNTIME_PROOF.md`.

Current main now includes `backend/app/services/layer3_source_directory_vector_retrieval.py` and `backend/tests/test_layer3_source_directory_vector_retrieval.py`.

Current main now implements `source_directory_material_vector_retrieval(db, payload)`.

Current main now records deterministic local vector retrieval over `source_directory_material_deterministic_embedding_vector_index_authority`, `layer3.source_directory_embedding_vector_index.v1`, `source-directory-hash-vector-v1`, and `vector_dimensions == 4096`.

Current main now validates `embedding_index_authority_hash`, rejects stale index/source/material authority through the vector-index/text-index authority path, scores admitted text-index segments with deterministic normalized query-to-segment dot product, omits `vector_score <= 0` results without fallback, and returns `layer3.source_directory_vector_retrieval.v1`.

Current main still selects no backend route, API DTO, response model, database model, migration, durable vector-store row write, durable embedding row write, durable retrieval row write, vector database, persistent vector store, RAG execution, context-packet mutation, qualitative generation runtime, prompt/model/provider runtime, network egress, provider-public delivery/use, package construction, connector dispatch, rendered control, or frontend-durable authority.

## Post-Merge Validation

Post-merge validation at `261c995c7330952bf01fa5b43202fd4445dbb5ea` passed:

- JSON manifest load;
- `python -m py_compile .\tools\l3-progress-check.py .\backend\app\services\layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_source_directory_vector_retrieval.py`;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py -q`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_source_directory_vector_index.py .\backend\tests\test_layer3_source_directory_qualitative_analysis.py .\backend\tests\test_layer3_source_directory_context_packet.py .\backend\tests\test_layer3_source_directory_text_retrieval.py .\backend\tests\test_layer3_source_directory_ingestion.py -q`; and
- `git diff --check`.

## Still Blocked

This sync admits no new runtime behavior beyond the already-merged deterministic local vector retrieval service, and admits no backend route, API DTO, response model, database model, migration, durable vector-store row write, durable embedding row write, durable retrieval row write, vector database, persistent vector store, RAG execution, context-packet mutation, qualitative generation runtime, prompt/model/provider runtime, hidden LLM planning, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, source expansion, arbitrary source ingestion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, web connectors, raw local path exposure, or source `L3OutputPackage` mutation.

## Next Posture

The next exact current-main posture is `select_provider_public_delivery_use_exposure_security_revocation_runtime_authority_after_source_directory_vector_retrieval_runtime_sync`.

That posture must be selection/freeze only unless a later current-main contract explicitly admits runtime. It must not add provider-public delivery/use routes, raw public URL exposure, provider credentials/adapters/object writes, rendered controls, connector dispatch, network egress, package mutation/reconstruction, source expansion, RAG/vector expansion, auth/security broadening, full mockup activation, frontend-durable authority, or raw local path exposure.

Do not continue additional same-family source-directory vector retrieval proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader.
