# 753 - Source Directory Material Source Index Authority Contract Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_material_source_index_authority_contract`.

Doc: `753_SOURCE_DIRECTORY_MATERIAL_SOURCE_INDEX_AUTHORITY_CONTRACT_CURRENT_MAIN_SYNC.md`.

Synced contract doc: `752_SOURCE_DIRECTORY_MATERIAL_SOURCE_INDEX_AUTHORITY_CONTRACT.md`.

Contract PR: `#1357`.

Contract branch: `codex/l3-source-index-contract`.

Contract branch commit: `bf5d1cadcc99d609a67baac663a7974604af7f26`.

Contract merge commit: `341577839d279c9128c3203a06d5ec87ab1351f1`.

Current-main checkpoint after merge: `341577839d279c9128c3203a06d5ec87ab1351f1`.

Sync branch: `codex/l3-source-index-contract-sync`.

Synced result: `current_main_synced_source_directory_material_source_index_authority_contract`.

Runtime behavior introduced by contract: `false`.

Runtime behavior in this sync: `false`.

## Merge Gate

External PR evidence for `#1357` after checks showed:

- state: `MERGED`;
- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- comments: `0`;
- reviews: `0`;
- reviewThreads totalCount: `0`;
- merge state before merge: `CLEAN`; and
- merge commit: `341577839d279c9128c3203a06d5ec87ab1351f1`.

## Sync Validation

Post-merge current-main validation at `341577839d279c9128c3203a06d5ec87ab1351f1` passed:

- `python -c "import json; json.load(open('next_milestone_plans/layer3_progress_manifest.json')); json.load(open('next_milestone_plans/layer3_workbench_proof_manifest.json')); print('json ok')"`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`; and
- `git diff --check`.

## Current-Main Result

Current main now records `source_directory_material_deterministic_text_index_authority` as the selected source/index contract after `current_main_synced_source_directory_material_source_index_authority_freeze`.

Current main proves:

- the selected source/index substrate is deterministic lexical/text authority before RAG/vector or qualitative-hybrid runtime;
- the selected future owner service is `backend/app/services/layer3_source_directory_text_index.py`;
- the selected index mode is `deterministic_text_segments`;
- canonical future inputs are `L3SourceDirectoryIngestionBatch`, `L3SourceDirectoryIngestionFile`, and `L3MaterialSnapshot` with `source_shape == server_configured_directory_file`;
- identity must include `source_ingestion_batch_id`, `source_ingestion_file_id`, `material_snapshot_id`, `content_sha256`, `file_identity_hash`, `authority_basis_hash`, `payload_hash`, `index_contract_id`, `index_mode`, and segmentation version; and
- No route was admitted by the contract.

## Still Blocked

This sync admits no runtime behavior, backend route behavior, service behavior, model change, migration, rendered UI control, source/index rows, vector index, embedding generation, retrieval query, qualitative-hybrid analysis runtime, qualitative broadening, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, or source `L3OutputPackage` mutation.

## Next Posture

The source-directory material source/index authority contract is now synced through current main.

The next exact posture is `implement_source_directory_material_deterministic_text_index_authority_after_contract_sync`.

That implementation must remain bounded to deterministic text indexing over already admitted `server_configured_directory_file` material snapshots. Do not implement vector indexing, embedding generation, retrieval query runtime, qualitative-hybrid analysis runtime, routes, provider/model calls, connector dispatch, source expansion, package mutation, rendered controls, frontend-durable authority, or auth/security broadening unless a later current-main-selected freeze explicitly admits that behavior.
