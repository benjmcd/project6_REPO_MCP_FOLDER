# 760 - Source Directory Material Deterministic Lexical Retrieval Runtime Proof

## Status

Status: branch-local runtime proof for `source_directory_material_deterministic_lexical_retrieval_runtime_proof`.

Runtime branch: `codex/l3-retrieval-impl`.

Current-main checkpoint before implementation: `65953dfd0dc3e76886239aaa4495a65b7c7ab21c`.

Predecessor current-main sync doc: `759_SOURCE_DIRECTORY_MATERIAL_LEXICAL_RETRIEVAL_AUTHORITY_CONTRACT_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_source_directory_material_lexical_retrieval_authority_contract`.

Selected implementation action: `implement_source_directory_material_deterministic_lexical_retrieval_authority_after_contract_sync`.

Runtime status after implementation: `source_directory_material_deterministic_lexical_retrieval_runtime_implemented_branch_local`.

Runtime behavior introduced by this pass: `true`.

## Implemented Surface

The implementation adds `backend/app/services/layer3_source_directory_text_retrieval.py`.

The proof adds `backend/tests/test_layer3_source_directory_text_retrieval.py`.

No backend route, API DTO, response model, database model, migration, source-index durable row, retrieval durable row, vector index, embedding generation, qualitative-hybrid runtime, package construction, package mutation/reconstruction, connector/destination dispatch, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered control, full mockup activation, frontend-durable authority, source expansion, credential, network egress, prompt/model/provider runtime, raw local path exposure, or source `L3OutputPackage` mutation is added.

## Runtime Behavior

The new service function is `source_directory_material_text_retrieval(db, payload)`.

The service first calls `source_directory_material_text_index(db, payload)` through the authority-bound request fields, so stale source/material authority continues to fail closed through the already-synced deterministic text-index path.

The service admits only deterministic lexical `query_text` over existing `deterministic_text_segments`.

The service validates the supplied `index_authority_hash` against the recomputed text-index authority before ranking any segments, and stale index authority fails closed with `source_directory_text_retrieval_stale_index_authority`.

The service rejects empty normalized queries with `source_directory_text_retrieval_empty_query`, forbidden deferred fields with `source_directory_text_retrieval_forbidden_field_not_admitted`, unknown non-contract fields with `source_directory_text_retrieval_unknown_field`, and invalid paging with bounded `limit` and non-negative `offset` checks.

The service normalizes lexical terms through `nrc_aps_content_index.normalize_query_tokens`, removes duplicate query tokens deterministically, requires every unique query token to appear in a segment, and ranks matches by:

1. descending `matched_unique_query_terms`;
2. descending `summed_term_frequency`;
3. ascending segment length;
4. ascending `segment_sequence`; and
5. ascending `segment_id`.

No-match results return `total: 0` and `items: []` without falling back to vector, prompt/model, source expansion, connector, package, or qualitative behavior.

The response schema is `layer3.source_directory_text_retrieval.v1`, with `retrieval_contract_id: source_directory_material_deterministic_lexical_retrieval_authority`, `retrieval_mode: deterministic_lexical_segment_retrieval`, `source_index_rows_written: False`, `retrieval_rows_written: False`, and negative invariants for the still-blocked surfaces.

## Proof Coverage

Focused test `backend/tests/test_layer3_source_directory_text_retrieval.py` proves:

- successful deterministic retrieval and stable replay;
- deterministic ranking by matched unique lexical terms and summed term frequency;
- stale `index_authority_hash` rejection;
- stale source/material authority rejection through the text-index path;
- empty-query rejection;
- forbidden-field rejection;
- unknown-field rejection;
- bounded `limit` and `offset` behavior;
- no-match response behavior; and
- no `ConnectorRun`, `ConnectorRunTarget`, or `L3OutputPackage` side effects.

Validation:

- `python -m py_compile .\backend\app\services\layer3_source_directory_text_retrieval.py .\backend\tests\test_layer3_source_directory_text_retrieval.py` PASS;
- `python -m pytest .\backend\tests\test_layer3_source_directory_text_retrieval.py -q` PASS, `4 passed`; and
- branch-local planning/progress/checker validation must pass before PR.

## Still Blocked

Backend route behavior, API DTOs, response models, database models, migrations, source-index durable rows, retrieval durable rows, vector indexing, embedding generation, qualitative-hybrid analysis runtime, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, raw local path exposure, prompt/model/provider runtime, and source `L3OutputPackage` mutation remain blocked.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_source_directory_material_deterministic_lexical_retrieval_runtime_proof`.

After that sync, pivot to `select_rag_vector_or_qualitative_hybrid_authority_after_source_directory_material_lexical_retrieval_runtime_sync` only if current-main evidence confirms this runtime is cleanly synced and no concrete same-family lexical retrieval defect remains.
