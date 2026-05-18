# 786 - Source Directory Material Deterministic Vector Retrieval Authority Contract

## Status

Status: branch-local vector retrieval authority contract for `source_directory_material_deterministic_vector_retrieval_authority_contract`.

Contract doc: `786_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_VECTOR_RETRIEVAL_AUTHORITY_CONTRACT.md`.

Contract branch: `codex/l3-vector-retrieval-contract`.

Current-main checkpoint before contract: `000cd409f7e1af3c59f8160cdffbcd45711dda73`.

Predecessor current-main sync doc: `785_SOURCE_DIRECTORY_MATERIAL_VECTOR_RETRIEVAL_AUTHORITY_SELECTION_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_source_directory_material_vector_retrieval_authority_selection_after_embedding_vector_index_runtime_sync`.

Selected from posture: `write_source_directory_material_deterministic_vector_retrieval_authority_contract_before_runtime`.

Runtime behavior introduced by this contract: `false`.

## Contract Decision

Selected contract: `source_directory_material_deterministic_vector_retrieval_authority`.

Selected retrieval mode: `deterministic_local_hash_vector_similarity_retrieval`.

Selected input authority: `source_directory_material_deterministic_embedding_vector_index_authority`.

Selected input schema: `layer3.source_directory_embedding_vector_index.v1`.

Selected vector-index source: `safe_vector_descriptors`.

Selected source scope: already-admitted `server_configured_directory_file` material snapshots from the server-configured operator directory text/table source family.

Selected future owner service: `backend/app/services/layer3_source_directory_vector_retrieval.py`.

Selected future proof test: `backend/tests/test_layer3_source_directory_vector_retrieval.py`.

Selected future implementation action: `implement_source_directory_material_deterministic_vector_retrieval_authority_after_contract_sync`.

Future response schema: `layer3.source_directory_vector_retrieval.v1`.

Future runtime character: deterministic local hashed-vector similarity retrieval over already-admitted source-directory embedding/vector-index authority only.

Vector query runtime selected for the future implementation: `deterministic_local_only`.

RAG execution selected: `false`.

Context-packet mutation selected: `false`.

Qualitative generation runtime selected: `false`.

Prompt/model/provider runtime selected: `false`.

Network egress selected: `false`.

Provider-public delivery/use selected: `false`.

Durable vector-store rows selected: `false`.

Durable embedding rows selected: `false`.

Durable retrieval rows selected: `false`.

Backend route selected: `false`.

Rendered/frontend-durable authority selected: `false`.

## Authority Order

The future implementation must resolve authority in this order:

1. Live `project6-origin/main` source, tests, models, migrations, routes, service code, and checker behavior.
2. `backend/app/services/layer3_source_directory_ingestion.py`.
3. `backend/app/services/layer3_source_directory_material_admission.py`.
4. `backend/app/services/layer3_source_directory_text_index.py`.
5. `backend/app/services/layer3_source_directory_vector_index.py`.
6. `backend/tests/test_layer3_source_directory_vector_index.py`.
7. Docs `750` through `785`.
8. This contract.

Planning prose, browser state, mockup screenshots, copied prompts, model output, external vector databases, provider embeddings, local fixture state, connector history, package text, provider logs, or prior PR titles are not sufficient authority for implementation.

## Future Request Contract

The future service function is `source_directory_material_vector_retrieval(db, payload)`.

The future request must be limited to:

- `client_request_id`;
- `material_snapshot_id`;
- `source_ingestion_batch_id`;
- `source_ingestion_file_id`;
- `content_sha256`;
- `file_identity_hash`;
- `authority_basis_hash`;
- `payload_hash`;
- `index_authority_hash`;
- `embedding_index_authority_hash`;
- `query_text`; and
- optional `top_k`.

`top_k` must be an integer between `1` and `20`, defaulting to `10`.

`query_text` is deterministic local vector-retrieval query text only. It is not a prompt, model instruction, provider request, hidden analysis plan, package payload, connector target, local path, URL, glob, file byte input, or frontend state.

The future request must reject unknown fields and forbidden fields before invoking vector-index authority. Forbidden fields include `prompt`, `model`, `provider_model`, `provider_url`, `embedding_model`, `embedding_options`, `vector`, `vector_index`, `rag_index`, `rag_prompt`, `semantic_score`, `package_payload`, `connector_target`, `destination`, `public_url`, `local_path`, `path`, `absolute_path`, `file_bytes`, `glob`, `recursive`, `url`, `web_connector`, `frontend_state`, `runtime_db_write`, `analysis_run_id`, `pass_run_id`, `output_package_id`, `rewrite_output`, and `durable_write`.

## Future Authority And Scoring Contract

The future runtime must call `source_directory_material_embedding_vector_index(db, vector_index_payload)` before scoring any retrieval results, where `vector_index_payload` contains only the admitted source/material identity fields plus `index_authority_hash`.

The future runtime must validate the vector-index response:

- `schema_id == layer3.source_directory_embedding_vector_index.v1`;
- `embedding_contract_id == source_directory_material_deterministic_embedding_vector_index_authority`;
- `embedding_mode == deterministic_local_hashing_vector_embedding`;
- `vector_index_mode == deterministic_source_directory_segment_vector_index`;
- `feature_hash_version == source-directory-hash-vector-v1`;
- `vector_dimensions == 4096`;
- returned `index_authority_hash` matches the request;
- returned `embedding_index_authority_hash` matches the request; and
- returned row-write flags and negative invariants keep retrieval, vector-store, provider, package, connector, frontend-durable, and network behavior blocked.

The future runtime may reconstruct segment scoring features only from the already-admitted text-index authority and the same deterministic vectorization parameters used by `source_directory_material_embedding_vector_index(db, payload)`. It must not expose raw dense vectors, normalized feature arrays, provider embeddings, vector database identifiers, or persistent vector-store handles.

The future query vector must use:

- token source: `nrc_aps_content_index.normalize_query_tokens` or the implementation-equivalent tokenizer used by vector-index authority;
- feature weight: token frequency;
- bucket assignment: stable SHA-256 token hash modulo `4096`;
- vector normalization: L2 normalization for cosine-compatible dot-product scoring; and
- empty normalized query failure with `source_directory_vector_retrieval_empty_query`.

The future segment score must be the deterministic dot product between normalized query buckets and normalized segment buckets. Items with `vector_score <= 0` must be omitted rather than falling back to lexical retrieval, prompt/model generation, source expansion, connector dispatch, or package behavior.

Stable ranking must sort by:

1. descending `vector_score`;
2. descending `matched_unique_query_terms`;
3. descending `summed_query_term_frequency`;
4. ascending `segment_sequence`; and
5. ascending `segment_id`.

## Future Response Contract

The future response schema is `layer3.source_directory_vector_retrieval.v1`.

The future response must include:

- `schema_id`;
- `schema_version`;
- `request_id`;
- `server_time`;
- `mode`;
- `status`;
- `retrieval_contract_id`;
- `retrieval_mode`;
- `query_tokens`;
- `top_k`;
- `total`;
- `items`;
- `embedding_contract_id`;
- `embedding_mode`;
- `vector_index_mode`;
- `feature_hash_version`;
- `vector_dimensions`;
- `embedding_index_authority_hash`;
- `index_contract_id`;
- `index_mode`;
- `segmentation_version`;
- `index_authority_hash`;
- source/material/index authority ids and hashes;
- row-write flags; and
- negative invariants.

Each result item may include only `segment_id`, `segment_sequence`, `line_start`, `line_end`, `char_start`, `char_end`, `segment_hash`, `embedding_vector_hash`, bounded `text`, `vector_score`, `matched_unique_query_terms`, and `summed_query_term_frequency`.

The response must not expose raw local paths, configured root paths, arbitrary source paths, provider URLs, public URLs, connector targets, credentials, tokens, prompt text, model settings, raw vector arrays, normalized feature arrays, package payloads, browser-owned state, or frontend-only durable state.

The future runtime must return `source_index_rows_written: False`, `embedding_vector_rows_written: False`, `vector_index_rows_written: False`, `retrieval_rows_written: False`, `context_packet_rows_written: False`, `qualitative_analysis_rows_written: False`, `analysis_run_rows_written: False`, `package_rows_written: False`, and `connector_rows_written: False`.

The future runtime must not create or update `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `ConnectorRun`, `ConnectorRunTarget`, provider delivery state, package review state, handoff/export state, durable vector stores, durable embedding rows, durable retrieval rows, prompt/model/provider rows, durable qualitative analysis rows, source ingestion rows, material snapshot rows, or rendered/frontend durable state.

## Future Proof Contract

The future proof test must cover:

- successful deterministic vector retrieval over an admitted source-directory embedding/vector index;
- deterministic replay of result ordering and `vector_score`;
- validation of stale `embedding_index_authority_hash`;
- stale `index_authority_hash` rejection through vector-index authority;
- stale source/material authority rejection through the vector-index/text-index path;
- empty-query rejection;
- forbidden prompt/model/provider/vector-store/RAG/package/connector/path/runtime-db-write fields;
- unknown field rejection;
- bounded `top_k` behavior;
- no-match response behavior without fallback;
- no raw vector or normalized feature exposure in the response;
- no `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `ConnectorRun`, or `ConnectorRunTarget` side effects; and
- row-write flags and negative invariants remaining false.

No headed or headless browser proof is required unless a later freeze admits rendered UI changes.

## Runtime Non-Admission

This contract admits no runtime behavior, backend route, API DTO, response model, database model, migration, durable vector-store row write, durable embedding row write, durable retrieval row write, vector database, persistent vector store, RAG execution, context-packet mutation, qualitative generation runtime, prompt/model/provider runtime, hidden LLM planning, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, source expansion, arbitrary source ingestion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, web connectors, raw local path exposure, or source `L3OutputPackage` mutation.

## Next Posture

The next exact posture after merge is `current_main_sync_source_directory_material_deterministic_vector_retrieval_authority_contract`.

After sync, the next exact posture is `implement_source_directory_material_deterministic_vector_retrieval_authority_after_contract_sync`.

Do not implement vector retrieval runtime, RAG execution, prompt/model/provider runtime, durable retrieval rows, vector stores, backend routes, package construction, package mutation, source expansion, rendered controls, provider/public delivery/use, connector/destination dispatch, network egress, credentials, auth/security broadening, or frontend-durable authority from this contract.
