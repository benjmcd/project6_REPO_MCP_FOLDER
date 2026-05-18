# 767 - Source Directory Material Retrieval-Augmented Context Packet Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_material_retrieval_augmented_context_packet_runtime_proof`.

Sync doc: `767_SOURCE_DIRECTORY_MATERIAL_RETRIEVAL_AUGMENTED_CONTEXT_PACKET_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime doc: `766_SOURCE_DIRECTORY_MATERIAL_RETRIEVAL_AUGMENTED_CONTEXT_PACKET_RUNTIME_PROOF.md`.

Runtime PR: `#1371`.

Runtime branch: `codex/l3-rag-qual-impl`.

Runtime branch commit: `94bf690283d1d7c0eda734bd4ecd11486292dfeb`.

Runtime merge commit and current-main checkpoint: `22d8ff1bbf1f38f8dfc64d07ca153b5df6239e69`.

Sync branch: `codex/l3-rag-qual-impl-sync`.

Synced result: `current_main_synced_source_directory_material_retrieval_augmented_context_packet_runtime`.

Runtime behavior already merged by runtime PR: `true`.

Runtime behavior introduced by this sync: `false`.

## Merge Gate

PR `#1371` merged cleanly after adding `source_directory_material_retrieval_augmented_context_packet_runtime_proof`.

The merge gate was:

- `backend-layer3-api`: `SUCCESS`, `3m11s`;
- `test`: `SUCCESS`, `3m24s`;
- comments totalCount: `0`;
- reviews totalCount: `0`;
- latestReviews totalCount: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`; and
- merge state before merge: `CLEAN`.

## Current-Main Result

Current main now includes `backend/app/services/layer3_source_directory_context_packet.py` and `backend/tests/test_layer3_source_directory_context_packet.py`.

Current main now implements `source_directory_material_retrieval_augmented_context_packet(db, payload)` over current `source_directory_material_text_retrieval(db, payload)`.

The synced runtime validates `retrieval_contract_id`, validates `retrieval_mode`, returns `layer3.source_directory_context_packet.v1`, computes deterministic `context_packet_hash`, exposes bounded `text_excerpt` items, and keeps `source_index_rows_written`, `retrieval_rows_written`, `context_packet_rows_written`, `qualitative_generation_rows_written`, `analysis_run_rows_written`, and `package_rows_written` false.

The synced proof covers deterministic replay, stale `index_authority_hash` rejection through retrieval, stale source/material authority rejection through text-index, empty-query rejection, forbidden prompt/vector/runtime-db-write fields, unknown fields, bounded `limit` and `offset`, no-match preservation, and no `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `ConnectorRun`, or `ConnectorRunTarget` side effects.

## Post-Merge Validation

Post-merge validation at `22d8ff1bbf1f38f8dfc64d07ca153b5df6239e69` passed:

- JSON manifest load;
- `python -m py_compile .\tools\l3-progress-check.py .\backend\app\services\layer3_source_directory_context_packet.py .\backend\tests\test_layer3_source_directory_context_packet.py`;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_context_packet.py .\backend\tests\test_layer3_source_directory_text_retrieval.py .\backend\tests\test_layer3_source_directory_ingestion.py -q`, `21 passed`; and
- `git diff --check`.

## Still Blocked

This sync admits no new runtime behavior beyond the already-merged context-packet service, and admits no backend route, API DTO, response model, database model, migration, source-index durable row write, retrieval durable row write, durable context-packet row write, vector indexing, embedding generation, qualitative generation runtime, prompt/model/provider runtime, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered control, full mockup activation, frontend-durable authority, source expansion, arbitrary source ingestion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, web connectors, raw local path exposure, or source `L3OutputPackage` mutation.

## Next Posture

The next exact current-main posture is `select_next_qualitative_hybrid_analysis_authority_after_context_packet_runtime_sync`.

Do not continue additional same-family context-packet proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader.
