# 759 - Source Directory Material Lexical Retrieval Authority Contract Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_material_lexical_retrieval_authority_contract`.

Sync doc: `759_SOURCE_DIRECTORY_MATERIAL_LEXICAL_RETRIEVAL_AUTHORITY_CONTRACT_CURRENT_MAIN_SYNC.md`.

Contract doc: `758_SOURCE_DIRECTORY_MATERIAL_LEXICAL_RETRIEVAL_AUTHORITY_CONTRACT.md`.

Contract PR: `#1363`.

Contract branch: `codex/l3-retrieval-contract`.

Contract branch commit: `c08dc222372100b431232946c3ede818731312e2`.

Contract merge commit and current-main checkpoint: `f22439007ae958d704932d4a3fb7c0cac0848d3b`.

Sync branch: `codex/l3-retrieval-contract-sync`.

Synced result: `current_main_synced_source_directory_material_lexical_retrieval_authority_contract`.

Runtime behavior introduced by contract PR: `false`.

Runtime behavior introduced by this sync: `false`.

## Merge Gate

PR `#1363` merged cleanly after the contract branch selected `source_directory_material_deterministic_lexical_retrieval_authority`.

The merge gate was:

- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- comments totalCount: `0`;
- reviews totalCount: `0`;
- latestReviews totalCount: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`; and
- merge state before merge: `CLEAN`.

## Current-Main Result

Current main now records `source_directory_material_deterministic_lexical_retrieval_authority` as the selected source-directory material lexical retrieval contract.

The selected retrieval mode remains `deterministic_lexical_segment_retrieval`.

The selected future owner service remains `backend/app/services/layer3_source_directory_text_retrieval.py`.

The selected future proof test remains `backend/tests/test_layer3_source_directory_text_retrieval.py`.

The future retrieval service must read the already-synced deterministic text index authority from `backend/app/services/layer3_source_directory_text_index.py` and remain bound to `source_directory_material_deterministic_text_index_authority`, `deterministic_text_segments`, `line-window-v1`, and `index_authority_hash`.

The contracted request remains authority-bound deterministic lexical retrieval only: source/material/index identity fields, `index_authority_hash`, deterministic `query_text`, bounded `limit`, and bounded `offset`.

The contracted response remains `layer3.source_directory_text_retrieval.v1`, with deterministic result items ranked by `matched_unique_query_terms`, `summed_term_frequency`, segment length, `segment_sequence`, and `segment_id`.

## Validation

Sync validation from current-main checkpoint `f22439007ae958d704932d4a3fb7c0cac0848d3b` must pass:

- JSON manifest load;
- `python -m py_compile .\tools\l3-progress-check.py`;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`; and
- `git diff --check`.

## Still Blocked

This sync admits no runtime behavior, backend route behavior, API DTO, model change, migration, source-index durable row write, retrieval durable row write, vector indexing, embedding generation, qualitative-hybrid analysis runtime, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, raw local path exposure, prompt/model/provider runtime, or source `L3OutputPackage` mutation.

## Next Posture

The next exact current-main posture is `implement_source_directory_material_deterministic_lexical_retrieval_authority_after_contract_sync`.

That implementation may add only `backend/app/services/layer3_source_directory_text_retrieval.py` and `backend/tests/test_layer3_source_directory_text_retrieval.py` unless current-main evidence names a concrete unresolved defect in an existing admitted surface.
