# 751 - Source Directory Material Source Index Authority Freeze Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_material_source_index_authority_freeze`.

Doc: `751_SOURCE_DIRECTORY_MATERIAL_SOURCE_INDEX_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC.md`.

Synced freeze doc: `750_SOURCE_DIRECTORY_MATERIAL_SOURCE_INDEX_AUTHORITY_FREEZE.md`.

Freeze PR: `#1355`.

Freeze branch: `codex/l3-source-index-freeze`.

Freeze branch commit: `ba773ab5`.

Freeze merge commit: `ab50df882fd2a28563df0f56f20351251757775c`.

Current-main checkpoint after merge: `ab50df882fd2a28563df0f56f20351251757775c`.

Sync branch: `codex/l3-source-index-sync`.

Synced result: `current_main_synced_source_directory_material_source_index_authority_freeze`.

Runtime behavior introduced by freeze: `false`.

Runtime behavior in this sync: `false`.

## Merge Gate

External PR evidence for `#1355` after review and checks showed:

- state: `MERGED`;
- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- comments: `0`;
- reviews: `0`;
- reviewThreads totalCount: `0`;
- merge state before merge: `CLEAN`; and
- merge commit: `ab50df882fd2a28563df0f56f20351251757775c`.

## Sync Validation

Post-merge current-main validation at `ab50df882fd2a28563df0f56f20351251757775c` passed:

- `python -c "import json; json.load(open('next_milestone_plans/layer3_progress_manifest.json')); json.load(open('next_milestone_plans/layer3_workbench_proof_manifest.json')); print('json ok')"`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`; and
- `git diff --check`.

## Current-Main Result

Current main now records `source_directory_material_source_index_authority` as the selected source/index authority-selection freeze after `current_main_synced_source_directory_ingestion_gate_b_material_admission_runtime`.

The selected next authority artifact remains `source_directory_material_source_index_authority_contract`.

Current main proves:

- source-directory material reaches `L3MaterialSnapshot` with source shape `server_configured_directory_file`;
- Gate C types `server_configured_directory_file` as `document_chunks` / `qualitative`;
- `backend/app/services/layer3_source_boundary.py` still reports `rag_vector_enabled: False`;
- `backend/app/services/layer3_source_directory_material_admission.py` still reports `eligible_for_rag_vector_index: False`;
- `backend/app/services/layer3_qual_aps_execution.py` still reports `hybrid_execution_enabled: False` and `rag_vector_retrieval_enabled: False`; and
- `backend/app/services/aps_retrieval_plane_contract.py` remains APS-specific `ApsRetrievalChunk` authority, not source-directory `server_configured_directory_file` source/index authority.

## Still Blocked

This sync admits no runtime behavior, backend route behavior, service behavior, model change, migration, rendered UI control, source/index rows, vector index, embedding generation, retrieval query, qualitative-hybrid analysis runtime, qualitative broadening, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, or source `L3OutputPackage` mutation.

## Next Posture

The exact source/index authority-selection freeze is now synced through current main.

The next exact posture is `write_source_directory_material_source_index_authority_contract_before_rag_vector_or_qualitative_hybrid_runtime`.

Do not implement RAG/vector indexing, qualitative-hybrid runtime, source/index rows, embeddings, retrieval queries, or new routes until that contract is written, reviewed, merged, current-main synced, and explicitly admits a code-bearing surface.
