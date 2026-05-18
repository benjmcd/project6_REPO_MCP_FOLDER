# 788 - Source Directory Material Deterministic Vector Retrieval Runtime Proof

## Status

Status: branch-local runtime proof for `source_directory_material_deterministic_vector_retrieval_runtime_proof`.

Runtime proof doc: `788_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_VECTOR_RETRIEVAL_RUNTIME_PROOF.md`.

Runtime branch: `codex/l3-vector-retrieval-runtime`.

Current-main checkpoint before implementation: `fb37896f56843c6abcc7b1ebb9d98c59ea323230`.

Predecessor current-main sync doc: `787_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_VECTOR_RETRIEVAL_AUTHORITY_CONTRACT_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_source_directory_material_deterministic_vector_retrieval_authority_contract`.

Selected implementation action: `implement_source_directory_material_deterministic_vector_retrieval_authority_after_contract_sync`.

Runtime status after implementation: `source_directory_material_deterministic_vector_retrieval_runtime_implemented_branch_local`.

Runtime behavior introduced by this pass: `true`.

## Implemented Surface

The implementation adds `backend/app/services/layer3_source_directory_vector_retrieval.py`.

The proof adds `backend/tests/test_layer3_source_directory_vector_retrieval.py`.

No backend route, API DTO, response model, database model, migration, durable vector-store row write, durable embedding row write, durable retrieval row write, vector database, persistent vector store, RAG execution, context-packet mutation, qualitative generation runtime, prompt/model/provider runtime, hidden LLM planning, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered control, full mockup activation, frontend-durable authority, source expansion, arbitrary source ingestion, raw local path exposure, or source `L3OutputPackage` mutation is added.

## Runtime Behavior

The new service function is `source_directory_material_vector_retrieval(db, payload)`.

The service first validates the exact deterministic vector retrieval request field set, including `index_authority_hash`, `embedding_index_authority_hash`, `query_text`, and optional `top_k`.

The service calls `source_directory_material_embedding_vector_index(db, vector_index_payload)` before scoring any retrieval result.

The service validates the returned vector-index authority as `layer3.source_directory_embedding_vector_index.v1`, `source_directory_material_deterministic_embedding_vector_index_authority`, `deterministic_local_hashing_vector_embedding`, `deterministic_source_directory_segment_vector_index`, `source-directory-hash-vector-v1`, and `vector_dimensions == 4096`.

The service validates the supplied `embedding_index_authority_hash` against the recomputed embedding/vector-index authority before returning retrieval results, and stale embedding authority fails closed with `source_directory_vector_retrieval_stale_embedding_index_authority`.

The service uses text-index authority only to recover already-admitted segment text for deterministic local scoring; it validates that text-index authority matches the same `index_authority_hash` used by vector index.

The response schema is `layer3.source_directory_vector_retrieval.v1`, with `retrieval_contract_id: source_directory_material_deterministic_vector_retrieval_authority`, `retrieval_mode: deterministic_local_hash_vector_similarity_retrieval`, deterministic query tokens, `top_k`, `total`, ranked result `items`, embedding/vector-index authority fields, source/material/index authority IDs and hashes, row-write flags, and negative invariants.

Each result item exposes only segment ID, sequence, line/character bounds, `segment_hash`, `embedding_vector_hash`, bounded `text`, `vector_score`, `matched_unique_query_terms`, and `summed_query_term_frequency`.

The deterministic local scoring uses `nrc_aps_content_index.normalize_query_tokens`, stable SHA-256 token hash modulo `4096`, token-frequency weights, L2-normalized sparse feature maps from source-directory vector-index authority, and deterministic normalized query-to-segment dot product.

Items with `vector_score <= 0` are omitted without lexical fallback, RAG fallback, prompt/model generation, source expansion, connector dispatch, or package behavior.

Ranking sorts by descending `vector_score`, descending `matched_unique_query_terms`, descending `summed_query_term_frequency`, ascending `segment_sequence`, and ascending `segment_id`.

The service returns `source_index_rows_written: False`, `embedding_vector_rows_written: False`, `vector_index_rows_written: False`, `retrieval_rows_written: False`, `context_packet_rows_written: False`, `qualitative_analysis_rows_written: False`, `analysis_run_rows_written: False`, `package_rows_written: False`, and `connector_rows_written: False`.

No raw vector arrays, normalized feature arrays, raw local paths, credentials, provider/model values, package payloads, connector targets, public URLs, source expansion inputs, or frontend-durable state are returned.

## Proof Coverage

Focused test `backend/tests/test_layer3_source_directory_vector_retrieval.py` proves:

- successful deterministic vector retrieval over admitted source-directory embedding/vector-index authority;
- deterministic replay of score-ordered result items and `vector_score`;
- validation of stale `embedding_index_authority_hash`;
- stale `index_authority_hash` rejection through vector-index authority;
- stale source/material authority rejection through the vector-index/text-index path;
- empty-query rejection;
- forbidden prompt/model/provider/RAG/vector field rejection;
- unknown field rejection;
- bounded `top_k` behavior;
- no-match response behavior without fallback;
- no raw vector or normalized feature exposure in the response; and
- no `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `ConnectorRun`, or `ConnectorRunTarget` side effects.

Validation:

- JSON manifest load PASS;
- `python -m py_compile .\tools\l3-progress-check.py .\backend\app\services\layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_source_directory_vector_retrieval.py` PASS;
- `python .\tools\l3-progress-check.py` PASS;
- `python .\tools\l3-target-selection-validate.py --expect frozen` PASS;
- `python -m py_compile .\backend\app\services\layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_source_directory_vector_retrieval.py` PASS;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py -q` PASS, `4 passed`; and
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_source_directory_vector_index.py .\backend\tests\test_layer3_source_directory_qualitative_analysis.py .\backend\tests\test_layer3_source_directory_context_packet.py .\backend\tests\test_layer3_source_directory_text_retrieval.py .\backend\tests\test_layer3_source_directory_ingestion.py -q` PASS, `33 passed`; and
- `git diff --check` PASS.

## Still Blocked

Backend route behavior, API DTOs, response models, database models, migrations, durable vector-store rows, durable embedding rows, durable retrieval rows, vector databases, persistent vector stores, RAG execution, context-packet mutation, qualitative generation runtime, prompt/model/provider runtime, hidden LLM planning, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, raw local path exposure, and source `L3OutputPackage` mutation remain blocked.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_source_directory_material_deterministic_vector_retrieval_runtime_proof`.

After that sync, pivot to the next major deferred lane only if current-main evidence confirms this runtime is cleanly synced and no concrete same-family vector retrieval defect remains.
