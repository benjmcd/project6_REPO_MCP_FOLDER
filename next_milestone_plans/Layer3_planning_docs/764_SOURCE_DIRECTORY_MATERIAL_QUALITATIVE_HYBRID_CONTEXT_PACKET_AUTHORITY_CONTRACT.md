# 764 - Source Directory Material Qualitative Hybrid Context Packet Authority Contract

## Status

Status: branch-local qualitative-hybrid context-packet authority contract for `source_directory_material_qualitative_hybrid_context_packet_authority_contract`.

Contract doc: `764_SOURCE_DIRECTORY_MATERIAL_QUALITATIVE_HYBRID_CONTEXT_PACKET_AUTHORITY_CONTRACT.md`.

Contract branch: `codex/l3-rag-qual-contract`.

Current-main checkpoint before contract: `933a1d0753cee6c62888cf907291ad4c54f3af17`.

Predecessor sync doc: `763_SOURCE_DIRECTORY_MATERIAL_QUALITATIVE_HYBRID_CONTEXT_PACKET_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_source_directory_material_qualitative_hybrid_context_packet_authority_freeze`.

Selected from posture: `write_source_directory_material_qualitative_hybrid_context_packet_authority_contract_before_prompt_model_provider_or_vector_runtime`.

Runtime behavior introduced by this contract: `false`.

## Contract Decision

Selected contract: `source_directory_material_retrieval_augmented_context_packet_authority`.

Selected context-packet mode: `retrieval_augmented_qualitative_context_packet`.

Selected source scope: already-admitted `server_configured_directory_file` material snapshots from the server-configured operator directory text/table source family.

Selected retrieval authority: `source_directory_material_deterministic_lexical_retrieval_authority`.

Selected future owner service: `backend/app/services/layer3_source_directory_context_packet.py`.

Selected future proof test: `backend/tests/test_layer3_source_directory_context_packet.py`.

Selected future implementation action: `implement_source_directory_material_retrieval_augmented_context_packet_authority_after_contract_sync`.

Vector runtime selected: `false`.

Embedding generation selected: `false`.

Prompt/model/provider runtime selected: `false`.

Qualitative generation runtime selected: `false`.

Durable context-packet row writes selected: `false`.

## Authority Order

1. Live `project6-origin/main` source, tests, models, migrations, routes, service code, and checker behavior.
2. `backend/app/services/layer3_source_directory_ingestion.py`.
3. `backend/app/services/layer3_source_directory_material_admission.py`.
4. `backend/app/services/layer3_source_directory_text_index.py`.
5. `backend/app/services/layer3_source_directory_text_retrieval.py`.
6. Docs `750` through `763`.
7. This contract.

Planning prose, browser state, mockup screenshots, copied prompts, model output, vector index state, local fixture state, connector history, package text, or prior PR titles are not sufficient authority for runtime implementation.

## Future Request Contract

The future request is limited to:

- `client_request_id`;
- `material_snapshot_id`;
- `source_ingestion_batch_id`;
- `source_ingestion_file_id`;
- `content_sha256`;
- `file_identity_hash`;
- `authority_basis_hash`;
- `payload_hash`;
- `index_authority_hash`;
- deterministic `query_text`;
- bounded `limit`; and
- bounded `offset`.

The future runtime must reject unknown fields and forbidden fields before invoking retrieval authority. Forbidden fields include `prompt`, `model`, `provider_model`, `provider_url`, `embedding`, `embedding_model`, `embedding_options`, `vector`, `vector_index`, `rag_index`, `semantic_score`, `package_payload`, `connector_target`, `destination`, `public_url`, `local_path`, `path`, `absolute_path`, `file_bytes`, `glob`, `recursive`, `url`, `web_connector`, `frontend_state`, and `runtime_db_write`.

## Future Runtime Contract

The future runtime must call `source_directory_material_text_retrieval(db, payload)` before assembling context packet output.

The future runtime must validate the returned `retrieval_contract_id` as `source_directory_material_deterministic_lexical_retrieval_authority` and the returned `retrieval_mode` as `deterministic_lexical_segment_retrieval`.

The future runtime must build a deterministic context packet only from retrieval response fields, segment ids, segment hashes, line ranges, query tokens, rank metadata, source/material authority ids, and bounded response-safe text excerpts.

The future runtime must compute a stable `context_packet_hash` from source/material/index/retrieval authority fields, query tokens, retrieved segment refs, segment hashes, and context-packet metadata.

The future runtime must return `source_index_rows_written: False`, `retrieval_rows_written: False`, `context_packet_rows_written: False`, `qualitative_generation_rows_written: False`, `analysis_run_rows_written: False`, and `package_rows_written: False`.

The future runtime must not create or update `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `ConnectorRun`, `ConnectorRunTarget`, provider delivery state, package review state, handoff/export state, vector indexes, embedding rows, prompt/model/provider rows, or rendered/frontend durable state.

## Future Response Contract

The future response schema is `layer3.source_directory_context_packet.v1`.

The future response must include response-safe metadata only:

- `schema_id`;
- `schema_version`;
- `request_id`;
- `server_time`;
- `mode`;
- `status`;
- `context_packet_contract_id`;
- `context_packet_mode`;
- `retrieval_contract_id`;
- `retrieval_mode`;
- `context_packet_hash`;
- `query_tokens`;
- `total`;
- `limit`;
- `offset`;
- `items`;
- `index_authority_hash`;
- source/material authority ids and hashes;
- row-write flags; and
- negative invariants.

The `items` list may include only segment ids, segment sequence, line range, char range, segment hash, bounded text excerpt, matched unique query term count, summed term frequency, and deterministic rank position.

The response must not expose prompt text, model credentials, provider keys, embedding vectors, raw vector contents, local filesystem paths, bearer tokens, raw provider URLs, connector targets, destination targets, package payload bodies, hidden LLM state, auth internals, or browser-owned durable state.

## Future Proof Contract

The future proof test must cover:

- successful context packet construction over deterministic lexical retrieval output;
- deterministic replay of `context_packet_hash`;
- stale `index_authority_hash` rejection through the retrieval path;
- stale source/material authority rejection through the text-index path;
- empty query rejection;
- forbidden prompt/model/provider/vector/package/connector/path fields;
- unknown field rejection;
- bounded `limit` and `offset`;
- no-match response preservation;
- no `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `ConnectorRun`, or `ConnectorRunTarget` side effects; and
- row-write flags remaining false.

## Runtime Non-Admission

This contract admits no runtime behavior, backend route, API DTO, response model, database model, migration, source-index durable row write, retrieval durable row write, context-packet durable row write, vector indexing, embedding generation, qualitative generation runtime, prompt/model/provider runtime, hidden LLM planning, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, source expansion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, web connectors, raw local path exposure, or source `L3OutputPackage` mutation.

## Next Posture

The next exact posture after merge is `current_main_sync_source_directory_material_qualitative_hybrid_context_packet_authority_contract`.

After sync, the next exact posture is `implement_source_directory_material_retrieval_augmented_context_packet_authority_after_contract_sync`.

Do not implement vector indexing, embedding generation, prompt/model/provider runtime, qualitative generation, package construction, package mutation, source expansion, rendered controls, provider/public delivery/use, connector/destination dispatch, network egress, credentials, auth/security broadening, or frontend-durable authority from this contract.
