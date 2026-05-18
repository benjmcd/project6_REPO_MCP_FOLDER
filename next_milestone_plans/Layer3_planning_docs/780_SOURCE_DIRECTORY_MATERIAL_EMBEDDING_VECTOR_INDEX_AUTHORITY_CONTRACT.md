# 780 - Source Directory Material Embedding Vector Index Authority Contract

## Status

Status: branch-local embedding/vector-index authority contract for `source_directory_material_embedding_vector_index_authority_contract`.

Contract doc: `780_SOURCE_DIRECTORY_MATERIAL_EMBEDDING_VECTOR_INDEX_AUTHORITY_CONTRACT.md`.

Contract branch: `codex/l3-vector-contract`.

Current-main checkpoint before contract: `3f17fa3903e4e177505fcbc60cd31688a9c8dd5a`.

Predecessor current-main sync doc: `779_RAG_VECTOR_AUTH_SYNC.md`.

Predecessor synced result: `current_main_synced_rag_vector_retrieval_authority_selection_after_provider_public_no_runtime_sync`.

Selected from posture: `write_source_directory_material_embedding_vector_index_authority_contract_before_runtime`.

Runtime behavior introduced by this contract: `false`.

## Contract Decision

Selected contract: `source_directory_material_deterministic_embedding_vector_index_authority`.

Selected embedding mode: `deterministic_local_hashing_vector_embedding`.

Selected vector index mode: `deterministic_source_directory_segment_vector_index`.

Selected input authority: `source_directory_material_deterministic_text_index_authority`.

Selected input schema: `layer3.source_directory_text_index.v1`.

Selected source scope: already-admitted `server_configured_directory_file` material snapshots from the server-configured operator directory text/table source family.

Selected future owner service: `backend/app/services/layer3_source_directory_vector_index.py`.

Selected future proof test: `backend/tests/test_layer3_source_directory_vector_index.py`.

Selected future implementation action: `implement_source_directory_material_deterministic_embedding_vector_index_authority_after_contract_sync`.

Future response schema: `layer3.source_directory_embedding_vector_index.v1`.

Future runtime character: deterministic local hashed lexical vectors over already-admitted text-index segments only.

Vector source selected: `deterministic_text_segments`.

Embedding generation selected for the future implementation: `deterministic_local_only`.

Embedding model/provider selected: `false`.

Prompt/model/provider runtime selected: `false`.

Network egress selected: `false`.

Provider-public delivery/use selected: `false`.

Durable vector-store rows selected: `false`.

Durable embedding rows selected: `false`.

Backend route selected: `false`.

Rendered/frontend-durable authority selected: `false`.

## Authority Order

The future implementation must resolve authority in this order:

1. Live `project6-origin/main` source, tests, models, migrations, routes, service code, and checker behavior.
2. `backend/app/services/layer3_source_directory_ingestion.py`.
3. `backend/app/services/layer3_source_directory_material_admission.py`.
4. `backend/app/services/layer3_source_directory_text_index.py`.
5. Docs `750` through `779`.
6. This contract.

Planning prose, browser state, mockup screenshots, copied prompts, model output, vector index state from another runtime, local fixture state, connector history, package text, provider logs, or prior PR titles are not sufficient authority for implementation.

The standard implementation pattern checked for this contract is stateless text hashing with explicit vector dimensions, normalization, feature hashing version, and cosine-compatible scoring. Current repo dependencies already include `scikit-learn>=1.5` and `numpy>=1.26`, but this contract does not require using a provider, fitting a model, downloading weights, or adding a new dependency.

## Future Request Contract

The future service function is `source_directory_material_embedding_vector_index(db, payload)`.

The future request must be limited to:

- `client_request_id`;
- `material_snapshot_id`;
- `source_ingestion_batch_id`;
- `source_ingestion_file_id`;
- `content_sha256`;
- `file_identity_hash`;
- `authority_basis_hash`;
- `payload_hash`; and
- `index_authority_hash`.

The future runtime must derive the segment source by calling `source_directory_material_text_index(db, payload)` with the admitted source/material identity fields and then validating that the returned `index_authority_hash` matches the request.

The future request must reject unknown fields and forbidden fields before invoking text-index authority. Forbidden fields include `query_text`, `prompt`, `model`, `provider_model`, `provider_url`, `embedding_model`, `embedding_options`, `vector`, `vector_index`, `rag_index`, `semantic_score`, `package_payload`, `connector_target`, `destination`, `public_url`, `local_path`, `path`, `absolute_path`, `file_bytes`, `glob`, `recursive`, `url`, `web_connector`, `frontend_state`, `runtime_db_write`, `analysis_run_id`, `pass_run_id`, `output_package_id`, `rewrite_output`, and `durable_write`.

## Future Vectorization Contract

The future implementation must compute deterministic local vectors from text-index segments only.

The selected parameter identity is:

- `embedding_contract_id == source_directory_material_deterministic_embedding_vector_index_authority`;
- `embedding_mode == deterministic_local_hashing_vector_embedding`;
- `vector_index_mode == deterministic_source_directory_segment_vector_index`;
- `feature_hash_version == source-directory-hash-vector-v1`;
- `vector_dimensions == 4096`;
- token source: `nrc_aps_content_index.normalize_query_tokens` or an implementation-equivalent deterministic tokenizer;
- feature weight: segment token frequency;
- bucket assignment: stable SHA-256 token hash modulo `vector_dimensions`;
- vector normalization: L2 normalization for cosine-compatible dot-product scoring; and
- vector storage posture: reconstructable service response and internal computation only, not a durable vector store.

The future implementation must build vector descriptors for each deterministic text segment. The descriptor may include `segment_id`, `segment_sequence`, `segment_hash`, `embedding_vector_hash`, `nonzero_feature_count`, `vector_l2_norm`, and source/index authority fields. It must not expose raw dense vectors, local paths, configured roots, credentials, provider URLs, package payload bodies, hidden prompts, browser state, or frontend-only durable state.

The future implementation must compute a stable `embedding_index_authority_hash` from source/material/index identity, segmentation version, ordered segment ids and hashes, vectorization parameters, ordered segment vector hashes, response schema metadata, and negative invariants.

## Future Runtime Contract

The future runtime must call `source_directory_material_text_index(db, payload)` before assembling any embedding/vector-index response.

The future runtime must validate the returned `index_contract_id` as `source_directory_material_deterministic_text_index_authority`, `index_mode` as `deterministic_text_segments`, and `schema_id` as `layer3.source_directory_text_index.v1`.

The future runtime must return `source_index_rows_written: False`, `embedding_vector_rows_written: False`, `vector_index_rows_written: False`, `retrieval_rows_written: False`, `context_packet_rows_written: False`, `qualitative_analysis_rows_written: False`, `analysis_run_rows_written: False`, `package_rows_written: False`, and `connector_rows_written: False`.

The future runtime must not create or update `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `ConnectorRun`, `ConnectorRunTarget`, provider delivery state, package review state, handoff/export state, durable vector stores, durable embedding rows, prompt/model/provider rows, durable qualitative analysis rows, source ingestion rows, material snapshot rows, or rendered/frontend durable state.

## Future Response Contract

The future response schema is `layer3.source_directory_embedding_vector_index.v1`.

The future response must include response-safe metadata only:

- `schema_id`;
- `schema_version`;
- `request_id`;
- `server_time`;
- `mode`;
- `status`;
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
- `segment_count`;
- `vector_descriptors`;
- row-write flags; and
- negative invariants.

The `vector_descriptors` list may include only segment ids, segment sequence, segment hash, `embedding_vector_hash`, `nonzero_feature_count`, `vector_l2_norm`, and bounded source/index metadata. It must not include raw vector arrays, full text segments, local paths, provider objects, public URLs, connector destinations, credentials, prompt/model settings, package payloads, or browser-owned state.

## Future Proof Contract

The future proof test must cover:

- successful deterministic vector index construction over an admitted source-directory text index;
- deterministic replay of `embedding_index_authority_hash`;
- stable segment-level `embedding_vector_hash` values for unchanged segment text and vectorization parameters;
- stale `index_authority_hash` rejection;
- stale source/material authority rejection through the text-index path;
- empty text-index or no-segment failure through the admitted text-index authority;
- forbidden prompt/model/provider/vector-query/package/connector/path/runtime-db-write fields;
- unknown field rejection;
- no raw vector exposure in the response;
- no `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `ConnectorRun`, or `ConnectorRunTarget` side effects; and
- row-write flags and negative invariants remaining false.

No headed or headless browser proof is required unless a later freeze admits rendered UI changes.

## Runtime Non-Admission

This contract admits no runtime behavior, backend route, API DTO, response model, database model, migration, durable vector-store row write, durable embedding row write, vector database, persistent vector store, vector query, semantic retrieval ranking, RAG execution, context-packet mutation, qualitative generation runtime, prompt/model/provider runtime, hidden LLM planning, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, source expansion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, web connectors, raw local path exposure, or source `L3OutputPackage` mutation.

## Next Posture

The next exact posture after merge is `current_main_sync_source_directory_material_embedding_vector_index_authority_contract`.

After sync, the next exact posture is `implement_source_directory_material_deterministic_embedding_vector_index_authority_after_contract_sync`.

Do not implement vector indexing runtime, vector retrieval query runtime, RAG execution, prompt/model/provider runtime, persistent vector stores, durable embedding rows, backend routes, package construction, package mutation, source expansion, rendered controls, provider/public delivery/use, connector/destination dispatch, network egress, credentials, auth/security broadening, or frontend-durable authority from this contract.
