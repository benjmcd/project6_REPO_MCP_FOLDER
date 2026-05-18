# 782 - Source Directory Material Deterministic Embedding Vector Index Runtime Proof

## Status

Status: branch-local runtime proof for `source_directory_material_deterministic_embedding_vector_index_runtime_proof`.

Runtime proof doc: `782_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_EMBEDDING_VECTOR_INDEX_RUNTIME_PROOF.md`.

Runtime branch: `codex/l3-vector-runtime`.

Current-main checkpoint before implementation: `d3acf9f078a495bc09d40ee39477d1b09bbde1bf`.

Predecessor current-main sync doc: `781_SOURCE_DIRECTORY_MATERIAL_EMBEDDING_VECTOR_INDEX_AUTHORITY_CONTRACT_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_source_directory_material_embedding_vector_index_authority_contract`.

Selected implementation action: `implement_source_directory_material_deterministic_embedding_vector_index_authority_after_contract_sync`.

Runtime status after implementation: `source_directory_material_deterministic_embedding_vector_index_runtime_implemented_branch_local`.

Runtime behavior introduced by this pass: `true`.

## Implemented Surface

The implementation adds `backend/app/services/layer3_source_directory_vector_index.py`.

The proof adds `backend/tests/test_layer3_source_directory_vector_index.py`.

No backend route, API DTO, response model, database model, migration, durable vector-store row write, durable embedding row write, vector database, persistent vector store, vector query runtime, semantic retrieval ranking, RAG execution, context-packet mutation, qualitative generation runtime, prompt/model/provider runtime, hidden LLM planning, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered control, full mockup activation, frontend-durable authority, source expansion, arbitrary source ingestion, raw local path exposure, or source `L3OutputPackage` mutation is added.

## Runtime Behavior

The new service function is `source_directory_material_embedding_vector_index(db, payload)`.

The service first validates the exact deterministic embedding/vector-index request field set, then calls `source_directory_material_text_index(db, payload)` through authority-bound request fields before assembling any vector descriptor response.

The service validates the returned text-index authority as `layer3.source_directory_text_index.v1`, `source_directory_material_deterministic_text_index_authority`, `deterministic_text_segments`, and `line-window-v1`.

The service validates the supplied `index_authority_hash` against the recomputed text-index authority before building descriptors, and stale text-index authority fails closed with `source_directory_vector_index_stale_index_authority`.

The response schema is `layer3.source_directory_embedding_vector_index.v1`, with `embedding_contract_id: source_directory_material_deterministic_embedding_vector_index_authority`, `embedding_mode: deterministic_local_hashing_vector_embedding`, `vector_index_mode: deterministic_source_directory_segment_vector_index`, `feature_hash_version: source-directory-hash-vector-v1`, `vector_dimensions: 4096`, deterministic `embedding_index_authority_hash`, source/material/index authority IDs and hashes, `segment_count`, and safe `vector_descriptors`.

Each vector descriptor exposes only segment ID, sequence, line/character bounds, `segment_hash`, `embedding_vector_hash`, `nonzero_feature_count`, `token_count`, and `vector_l2_norm`.

The deterministic local feature contract uses `nrc_aps_content_index.normalize_query_tokens`, stable SHA-256 token hash modulo `vector_dimensions`, segment token-frequency weights, and L2 normalization for cosine-compatible dot-product scoring.

The service returns `source_index_rows_written: False`, `embedding_vector_rows_written: False`, `vector_index_rows_written: False`, `retrieval_rows_written: False`, `context_packet_rows_written: False`, `qualitative_analysis_rows_written: False`, `analysis_run_rows_written: False`, `package_rows_written: False`, and `connector_rows_written: False`.

No raw vector arrays, normalized feature arrays, full segment text, raw local paths, credentials, provider/model values, package payloads, connector targets, public URLs, source expansion inputs, or frontend-durable state are returned.

## Proof Coverage

Focused test `backend/tests/test_layer3_source_directory_vector_index.py` proves:

- successful deterministic embedding/vector-index descriptor construction over admitted source-directory text-index authority;
- deterministic replay of `embedding_index_authority_hash` and `embedding_vector_hash`;
- safe descriptors without raw text, raw vectors, or feature arrays;
- stale `index_authority_hash` rejection;
- stale source/material authority rejection through the text-index path;
- forbidden query/provider/vector field rejection;
- unknown field rejection;
- required field rejection; and
- no `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `ConnectorRun`, or `ConnectorRunTarget` side effects.

Validation:

- `python -m py_compile .\backend\app\services\layer3_source_directory_vector_index.py .\backend\tests\test_layer3_source_directory_vector_index.py` PASS;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_index.py -q` PASS, `4 passed`; and
- branch-local planning/progress/checker validation must pass before PR.

## Still Blocked

Backend route behavior, API DTOs, response models, database models, migrations, durable vector-store rows, durable embedding rows, vector databases, persistent vector stores, vector query runtime, semantic retrieval ranking, RAG execution, context-packet mutation, qualitative generation runtime, prompt/model/provider runtime, hidden LLM planning, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, raw local path exposure, and source `L3OutputPackage` mutation remain blocked.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_source_directory_material_deterministic_embedding_vector_index_runtime_proof`.

After that sync, pivot to `select_next_rag_vector_retrieval_authority_after_source_directory_embedding_vector_index_runtime_sync` only if current-main evidence confirms this runtime is cleanly synced and no concrete same-family vector-index defect remains.
