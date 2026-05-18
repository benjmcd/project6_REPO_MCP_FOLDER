# 755 - Source Directory Material Deterministic Text Index Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_material_deterministic_text_index_runtime_proof`.

Doc: `755_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_TEXT_INDEX_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `754_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_TEXT_INDEX_RUNTIME_PROOF.md`.

Runtime PR: `#1359`.

Runtime branch: `codex/l3-source-index-text-impl`.

Runtime branch commit: `9d3278112389e08ce280e61c8b02ae709d124214`.

Runtime merge commit: `c0403c860b3e8903b4ee1e80ab9fca04f92301ad`.

Current-main checkpoint after merge: `c0403c860b3e8903b4ee1e80ab9fca04f92301ad`.

Sync branch: `codex/l3-source-index-text-sync`.

Synced result: `current_main_synced_source_directory_material_deterministic_text_index_runtime`.

Runtime behavior already merged by runtime PR: `true`.

Runtime behavior introduced by this sync: `false`.

## Merge Gate

External PR evidence for `#1359` after checks showed:

- state: `MERGED`;
- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- comments: `0`;
- reviews: `0`;
- latestReviews: `0`;
- reviewThreads totalCount: `0`;
- merge state before merge: `CLEAN`; and
- merge commit: `c0403c860b3e8903b4ee1e80ab9fca04f92301ad`.

## Current-Main Validation

Post-merge current-main validation at `c0403c860b3e8903b4ee1e80ab9fca04f92301ad` passed:

- `python -c "import json; json.load(open('next_milestone_plans/layer3_progress_manifest.json')); json.load(open('next_milestone_plans/layer3_workbench_proof_manifest.json')); print('json ok')"`;
- `python -m py_compile .\tools\l3-progress-check.py .\backend\app\services\layer3_source_directory_text_index.py .\backend\tests\test_layer3_source_directory_ingestion.py`;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_ingestion.py -q` -> `13 passed`;
- `python -m pytest .\backend\tests\test_layer3_source_boundary.py .\backend\tests\test_layer3_source_intake.py .\backend\tests\test_layer3_model_exports.py .\backend\tests\test_layer3_api.py::test_layer3_forbidden_sentinel_openapi_fields_are_impossible -q` -> `24 passed`; and
- `git diff --check`.

## Current-Main Result

Current main now includes `source_directory_material_deterministic_text_index_authority` in `backend/app/services/layer3_source_directory_text_index.py`.

The synced runtime reads existing `L3SourceDirectoryIngestionBatch`, `L3SourceDirectoryIngestionFile`, and `L3MaterialSnapshot` authority for already admitted `server_configured_directory_file` material snapshots, verifies material payload hash and live direct-child file identity, rejects stale or forbidden request scope, and returns deterministic `deterministic_text_segments` with `line-window-v1` segmentation and replay-stable `index_authority_hash`.

Current main also proves `source_index_rows_written: False` and no `ConnectorRun`, `ConnectorRunTarget`, or `L3OutputPackage` side effects in the focused proof.

## Still Blocked

This sync admits no additional runtime behavior, backend route, API DTO, model change, migration, source-index durable row writes, vector indexing, embedding generation, retrieval query runtime, qualitative-hybrid analysis runtime, package construction, package mutation/reconstruction, package payload rewrite, source `L3OutputPackage` mutation, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, or raw local path exposure.

## Next Posture

The source-directory deterministic text source/index runtime is now cleanly synced through current main.

The next exact current-main posture is `select_next_retrieval_or_qualitative_hybrid_authority_after_text_index_runtime_sync`.

Do not continue additional source-directory ingestion/material/text-index proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader. The next lane must start with requirement selection and behavior freeze before any RAG/vector, retrieval, qualitative-hybrid runtime, route, source-index row persistence, frontend-durable authority, connector/provider behavior, credentials, or network surface is admitted.
