# 758 - Source Directory Material Lexical Retrieval Authority Contract

## Status

Status: branch-local retrieval authority contract for `source_directory_material_lexical_retrieval_authority_contract`.

Doc: `758_SOURCE_DIRECTORY_MATERIAL_LEXICAL_RETRIEVAL_AUTHORITY_CONTRACT.md`.

Contract branch: `codex/l3-retrieval-contract`.

Current-main checkpoint before contract: `206b1be98daa243e3faa036b2f7052afbe047044`.

Predecessor current-main sync doc: `757_SOURCE_DIRECTORY_MATERIAL_LEXICAL_RETRIEVAL_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_source_directory_material_lexical_retrieval_authority_freeze`.

Selected contract: `source_directory_material_deterministic_lexical_retrieval_authority`.

Selected retrieval mode: `deterministic_lexical_segment_retrieval`.

Selected future owner service: `backend/app/services/layer3_source_directory_text_retrieval.py`.

Selected future proof test: `backend/tests/test_layer3_source_directory_text_retrieval.py`.

Runtime behavior introduced by this contract: `false`.

## Canonical Authority

The future retrieval service must read the already-synced deterministic text index authority from `backend/app/services/layer3_source_directory_text_index.py`.

Canonical input authority remains:

- `L3SourceDirectoryIngestionBatch`;
- `L3SourceDirectoryIngestionFile`;
- `L3MaterialSnapshot`;
- `server_configured_directory_file`;
- `source_directory_material_deterministic_text_index_authority`;
- `deterministic_text_segments`;
- `line-window-v1`; and
- `index_authority_hash`.

The future retrieval service must call or otherwise reuse the deterministic text-index authority path before ranking segments so stale material payload hashes, stale live file identity, wrong source shape, and forbidden source/index fields fail closed exactly as the synced text-index runtime already proves.

## Contracted Request

The future service function is `source_directory_material_text_retrieval(db, payload)`.

The required future request fields are:

- `client_request_id`;
- `material_snapshot_id`;
- `source_ingestion_batch_id`;
- `source_ingestion_file_id`;
- `content_sha256`;
- `file_identity_hash`;
- `authority_basis_hash`;
- `payload_hash`;
- `index_authority_hash`; and
- `query_text`.

The optional future request fields are `limit` and `offset`.

`query_text` is deterministic lexical query text only. It is not a prompt, model instruction, provider request, embedding input, vector query, hidden analysis plan, package payload, connector target, local path, URL, glob, or frontend state.

`limit` must be bounded to `1..50`, defaulting to `20`. `offset` must be an integer greater than or equal to `0`, defaulting to `0`. Empty normalized query tokens fail closed with `source_directory_text_retrieval_empty_query`.

The request must reject any non-contract field with `source_directory_text_retrieval_unknown_field`. It must reject deferred or forbidden fields with `source_directory_text_retrieval_forbidden_field_not_admitted`.

## Contracted Matching And Ranking

The future retrieval service must normalize query text with the same deterministic token rules used by the current APS lexical precedent: Unicode NFC, lowercase, alphanumeric tokens, non-alphanumeric separator collapse, and duplicate query-token removal.

The APS helper `nrc_aps_content_index.normalize_query_tokens` may be reused as a lexical utility only. Reuse of that helper does not make `ApsRetrievalChunk`, APS run scope, APS artifacts, APS rows, or APS routes source-directory retrieval authority.

For each deterministic text segment:

- tokenize segment text with the same normalization rules;
- require every unique query token to occur at least once;
- compute `matched_unique_query_terms`;
- compute `summed_term_frequency`;
- compute `segment_length`;
- keep `segment_sequence`, line/character bounds, `segment_hash`, and `segment_id`; and
- do not compute embeddings, vector distances, prompt scores, semantic scores, model summaries, or qualitative labels.

Stable ranking must sort by:

1. descending `matched_unique_query_terms`;
2. descending `summed_term_frequency`;
3. ascending `segment_length`;
4. ascending `segment_sequence`; and
5. ascending `segment_id`.

No-match results are valid deterministic retrieval responses with `total: 0`; they are not qualitative failures and do not trigger fallback to vector, prompt/model, source expansion, connector, or package behavior.

## Contracted Response

The future response schema is `layer3.source_directory_text_retrieval.v1`.

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
- `total`;
- `limit`;
- `offset`;
- `items`;
- `index_contract_id`;
- `index_mode`;
- `segmentation_version`;
- `index_authority_hash`;
- `source_ingestion_batch_id`;
- `source_ingestion_file_id`;
- `material_snapshot_id`;
- `source_shape`;
- `content_sha256`;
- `file_identity_hash`;
- `authority_basis_hash`;
- `payload_hash`;
- `source_index_rows_written: False`;
- `retrieval_rows_written: False`; and
- `negative_invariants`.

Each result item must include `segment_id`, `segment_sequence`, `line_start`, `line_end`, `char_start`, `char_end`, `segment_hash`, `text`, `matched_unique_query_terms`, and `summed_term_frequency`.

The response must not expose raw local paths, configured root paths, arbitrary source paths, provider URLs, public URLs, connector targets, credentials, tokens, prompt text, model settings, embeddings, vectors, package payloads, or frontend-only state.

## Future Implementation Admission

After this contract is review-cleared and current-main synced, the next implementation may add only:

- `backend/app/services/layer3_source_directory_text_retrieval.py`; and
- `backend/tests/test_layer3_source_directory_text_retrieval.py`.

The future implementation must prove successful deterministic retrieval, deterministic replay, stale `index_authority_hash` rejection, stale source/material authority rejection through the text-index path, empty-query rejection, forbidden-field rejection, bounded limit/offset behavior, no-match response behavior, and no `ConnectorRun`, `ConnectorRunTarget`, `L3OutputPackage`, source-index durable row, retrieval durable row, vector, embedding, package, connector, provider, credential, network, route, or frontend-durable side effects.

## Still Blocked

This contract admits no runtime behavior, backend route behavior, API DTO, model change, migration, source-index durable row writes, retrieval durable row writes, vector indexing, embedding generation, qualitative-hybrid analysis runtime, qualitative broadening, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, raw local path exposure, prompt/model/provider runtime, or source `L3OutputPackage` mutation.

## Next Posture

The next exact posture after merge is `current_main_sync_source_directory_material_lexical_retrieval_authority_contract`.

After that sync, the next exact posture is `implement_source_directory_material_deterministic_lexical_retrieval_authority_after_contract_sync`.
