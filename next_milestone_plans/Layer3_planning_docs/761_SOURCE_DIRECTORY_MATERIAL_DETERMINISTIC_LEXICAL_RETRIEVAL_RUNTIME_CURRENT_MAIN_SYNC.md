# 761 - Source Directory Material Deterministic Lexical Retrieval Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_material_deterministic_lexical_retrieval_runtime_proof`.

Sync doc: `761_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_LEXICAL_RETRIEVAL_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `760_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_LEXICAL_RETRIEVAL_RUNTIME_PROOF.md`.

Runtime PR: `#1365`.

Runtime branch: `codex/l3-retrieval-impl`.

Runtime branch commit: `8483d79e16f59e51759dbf2724d7a397bf817b0f`.

Runtime merge commit and current-main checkpoint: `8275da065e0f7dabbb603dbaecb84445c8b10a45`.

Sync branch: `codex/l3-retrieval-impl-sync`.

Synced result: `current_main_synced_source_directory_material_deterministic_lexical_retrieval_runtime`.

Runtime behavior already merged: `true`.

Runtime behavior introduced by this sync: `false`.

## Merge Gate

PR `#1365` merged cleanly after implementing `source_directory_material_deterministic_lexical_retrieval_authority`.

The merge gate was:

- `backend-layer3-api`: `SUCCESS`, `2m56s`;
- `test`: `SUCCESS`, `3m28s`;
- comments totalCount: `0`;
- reviews totalCount: `0`;
- latestReviews totalCount: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`; and
- merge state before merge: `CLEAN`.

## Current-Main Result

Current main now includes `backend/app/services/layer3_source_directory_text_retrieval.py` as the bounded deterministic lexical retrieval authority runtime for already-admitted source-directory deterministic text segments.

Current main now includes `backend/tests/test_layer3_source_directory_text_retrieval.py` as focused proof for deterministic retrieval, stable replay, stale index authority rejection, stale source/material authority rejection through the text-index path, empty query rejection, forbidden and unknown field rejection, bounded paging, no-match behavior, and no connector/package side effects.

The runtime reads `backend/app/services/layer3_source_directory_text_index.py` through `source_directory_material_text_index(db, payload)` before ranking, validates `index_authority_hash`, admits deterministic lexical `query_text`, and ranks only `deterministic_text_segments` with `matched_unique_query_terms`, `summed_term_frequency`, segment length, `segment_sequence`, and `segment_id`.

The synced response schema is `layer3.source_directory_text_retrieval.v1`, with `retrieval_contract_id: source_directory_material_deterministic_lexical_retrieval_authority`, `retrieval_mode: deterministic_lexical_segment_retrieval`, `source_index_rows_written: False`, and `retrieval_rows_written: False`.

## Validation

Post-merge validation at `8275da065e0f7dabbb603dbaecb84445c8b10a45` must pass:

- JSON manifest load;
- `python -m py_compile .\tools\l3-progress-check.py .\backend\app\services\layer3_source_directory_text_retrieval.py .\backend\tests\test_layer3_source_directory_text_retrieval.py`;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_text_retrieval.py -q`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_ingestion.py -q`; and
- `git diff --check`.

## Still Blocked

This sync admits no new runtime behavior beyond the already-merged deterministic lexical retrieval service. Backend route behavior, API DTOs, response models, database models, migrations, source-index durable rows, retrieval durable rows, vector indexing, embedding generation, qualitative-hybrid analysis runtime, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, raw local path exposure, prompt/model/provider runtime, and source `L3OutputPackage` mutation remain blocked.

## Next Posture

The next exact current-main posture is `select_rag_vector_or_qualitative_hybrid_authority_after_source_directory_material_lexical_retrieval_runtime_sync`.

Do not continue same-family source-directory lexical retrieval proof loops unless current-main evidence names a concrete unresolved defect or downstream reader.
