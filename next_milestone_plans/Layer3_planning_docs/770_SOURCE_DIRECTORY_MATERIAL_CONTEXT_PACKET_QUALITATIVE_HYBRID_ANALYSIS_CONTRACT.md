# 770 - Source Directory Material Context-Packet Qualitative-Hybrid Analysis Contract

## Status

Status: branch-local qualitative-hybrid analysis contract for `source_directory_material_context_packet_qualitative_hybrid_analysis_contract`.

Contract doc: `770_SOURCE_DIRECTORY_MATERIAL_CONTEXT_PACKET_QUALITATIVE_HYBRID_ANALYSIS_CONTRACT.md`.

Contract branch: `codex/l3-qual-analysis-contract`.

Current-main checkpoint before contract: `2fb5ace714eac8c3b1fa509a1fd9dd3afb0068b2`.

Predecessor current-main sync doc: `769_SOURCE_DIRECTORY_MATERIAL_QUALITATIVE_HYBRID_ANALYSIS_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_source_directory_material_qualitative_hybrid_analysis_authority_freeze`.

Selected from posture: `write_source_directory_material_context_packet_qualitative_hybrid_analysis_contract_before_runtime`.

Runtime behavior introduced by this contract: `false`.

## Contract Decision

Selected contract: `source_directory_material_context_packet_qualitative_hybrid_analysis_authority`.

Selected analysis mode: `context_packet_grounded_qualitative_hybrid_analysis`.

Selected input authority: `source_directory_material_retrieval_augmented_context_packet_authority`.

Selected input schema: `layer3.source_directory_context_packet.v1`.

Selected source scope: already-admitted `server_configured_directory_file` material snapshots from the server-configured operator directory text/table source family.

Selected future owner service: `backend/app/services/layer3_source_directory_qualitative_analysis.py`.

Selected future proof test: `backend/tests/test_layer3_source_directory_qualitative_analysis.py`.

Selected future implementation action: `implement_source_directory_material_context_packet_qualitative_hybrid_analysis_after_contract_sync`.

Future response schema: `layer3.source_directory_qualitative_analysis.v1`.

Future runtime character: deterministic extractive analysis over context-packet items only.

Vector runtime selected: `false`.

Embedding generation selected: `false`.

Prompt/model/provider runtime selected: `false`.

Network egress selected: `false`.

Provider-public delivery/use selected: `false`.

Durable qualitative analysis rows selected: `false`.

Backend route selected: `false`.

Rendered/frontend-durable authority selected: `false`.

## Authority Order

1. Live `project6-origin/main` source, tests, models, migrations, routes, service code, and checker behavior.
2. `backend/app/services/layer3_source_directory_ingestion.py`.
3. `backend/app/services/layer3_source_directory_material_admission.py`.
4. `backend/app/services/layer3_source_directory_text_index.py`.
5. `backend/app/services/layer3_source_directory_text_retrieval.py`.
6. `backend/app/services/layer3_source_directory_context_packet.py`.
7. Docs `750` through `769`.
8. This contract.

Planning prose, browser state, mockup screenshots, copied prompts, model output, vector index state, local fixture state, connector history, package text, or prior PR titles are not sufficient authority for runtime implementation.

## Future Request Contract

The future request must be limited to:

- `client_request_id`;
- `analysis_question`;
- `analysis_focus`;
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

The future runtime must derive its context packet by calling `source_directory_material_retrieval_augmented_context_packet(db, payload)` with the admitted source/material/index/retrieval authority fields and deterministic `query_text`.

The future runtime must reject unknown fields and forbidden fields before invoking context-packet authority. Forbidden fields include `prompt`, `model`, `provider_model`, `provider_url`, `embedding`, `embedding_model`, `embedding_options`, `vector`, `vector_index`, `rag_index`, `semantic_score`, `package_payload`, `connector_target`, `destination`, `public_url`, `local_path`, `path`, `absolute_path`, `file_bytes`, `glob`, `recursive`, `url`, `web_connector`, `frontend_state`, `runtime_db_write`, `analysis_run_id`, `pass_run_id`, `output_package_id`, `rewrite_output`, and `durable_write`.

## Future Runtime Contract

The future runtime must call `source_directory_material_retrieval_augmented_context_packet(db, payload)` before assembling any qualitative-hybrid analysis response.

The future runtime must validate the returned `context_packet_contract_id` as `source_directory_material_retrieval_augmented_context_packet_authority`, the returned `context_packet_mode` as `retrieval_augmented_qualitative_context_packet`, and the returned `schema_id` as `layer3.source_directory_context_packet.v1`.

The future runtime must build deterministic extractive analysis only from response-safe context-packet fields: source/material/index/retrieval/context authority ids and hashes, `context_packet_hash`, query tokens, item rank positions, segment ids, segment hashes, line ranges, bounded `text_excerpt`, matched unique query term counts, and summed term frequencies.

The future runtime must compute a stable `qualitative_analysis_hash` from the request contract, context-packet authority fields, `context_packet_hash`, ordered evidence refs, analysis sections, negative invariants, and response schema metadata.

The future runtime may classify response-safe evidence into deterministic sections such as `evidence_summary`, `salient_terms`, `supporting_segments`, `coverage_notes`, and `analysis_limits`. Those sections must be generated by deterministic extraction, counts, ranking, and templated statements over context-packet items only.

The future runtime must return `context_packet_rows_written: False`, `qualitative_analysis_rows_written: False`, `qualitative_generation_rows_written: False`, `analysis_run_rows_written: False`, `package_rows_written: False`, and `connector_rows_written: False`.

The future runtime must not create or update `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `ConnectorRun`, `ConnectorRunTarget`, provider delivery state, package review state, handoff/export state, vector indexes, embedding rows, prompt/model/provider rows, durable qualitative analysis rows, or rendered/frontend durable state.

## Future Response Contract

The future response schema is `layer3.source_directory_qualitative_analysis.v1`.

The future response must include response-safe metadata only:

- `schema_id`;
- `schema_version`;
- `request_id`;
- `server_time`;
- `mode`;
- `status`;
- `analysis_contract_id`;
- `analysis_mode`;
- `qualitative_analysis_hash`;
- `context_packet_contract_id`;
- `context_packet_mode`;
- `context_packet_hash`;
- `analysis_question`;
- `analysis_focus`;
- `query_tokens`;
- `evidence_summary`;
- `salient_terms`;
- `supporting_segments`;
- `coverage_notes`;
- `analysis_limits`;
- source/material/index authority ids and hashes;
- row-write flags; and
- negative invariants.

The `supporting_segments` list may include only segment ids, rank position, segment sequence, line range, segment hash, bounded quote excerpts copied from `text_excerpt`, matched unique query term count, summed term frequency, and deterministic support labels.

The response must not expose prompt text, model credentials, provider keys, embedding vectors, raw vector contents, local filesystem paths, bearer tokens, raw provider URLs, connector targets, destination targets, package payload bodies, hidden LLM state, auth internals, browser-owned durable state, or source `L3OutputPackage` payloads.

## Future Proof Contract

The future proof test must cover:

- successful deterministic qualitative-hybrid analysis over an admitted context packet;
- deterministic replay of `qualitative_analysis_hash`;
- stale `index_authority_hash` rejection through the context-packet and retrieval path;
- stale source/material authority rejection through the text-index path;
- empty or whitespace-only `analysis_question` rejection;
- empty query rejection through context-packet authority;
- forbidden prompt/model/provider/vector/package/connector/path/runtime-db-write fields;
- unknown field rejection;
- bounded `limit` and `offset` propagation into context-packet authority;
- no-match response preservation with explicit `analysis_limits`;
- no `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `ConnectorRun`, or `ConnectorRunTarget` side effects; and
- row-write flags and negative invariants remaining false.

## Runtime Non-Admission

This contract admits no runtime behavior, backend route, API DTO, response model, database model, migration, source-index durable row write, retrieval durable row write, durable context-packet row write, durable qualitative analysis row write, vector indexing, embedding generation, qualitative generation runtime, prompt/model/provider runtime, hidden LLM planning, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, source expansion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, web connectors, raw local path exposure, or source `L3OutputPackage` mutation.

## Next Posture

The next exact posture after merge is `current_main_sync_source_directory_material_context_packet_qualitative_hybrid_analysis_contract`.

After sync, the next exact posture is `implement_source_directory_material_context_packet_qualitative_hybrid_analysis_after_contract_sync`.

Do not implement qualitative analysis runtime, prompt/model/provider runtime, vector indexing, embedding generation, durable analysis rows, backend routes, package construction, package mutation, source expansion, rendered controls, provider/public delivery/use, connector/destination dispatch, network egress, credentials, auth/security broadening, or frontend-durable authority from this contract.
