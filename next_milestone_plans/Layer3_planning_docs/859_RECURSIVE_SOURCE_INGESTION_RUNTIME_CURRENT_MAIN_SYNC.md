# 859 - Recursive Source Ingestion Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `recursive_server_configured_directory_text_table_policy_v1` runtime implementation.

Sync doc: `859_RECURSIVE_SOURCE_INGESTION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Synced implementation proof doc: `858_RECURSIVE_SOURCE_INGESTION_RUNTIME_PROOF.md`.

Implementation PR: `#1468`.

Implementation branch: `codex/l3-recursive-source-ingestion-runtime`.

Implementation branch commit: `e50f65bf873e00f299bb3fb73c55c9c200db7c6e`.

Implementation merge commit: `2fa84f5f`.

Sync branch: `codex/l3-recursive-source-ingestion-runtime-sync`.

Synced result: `current_main_synced_recursive_source_ingestion_runtime_implementation`.

Runtime behavior introduced by implementation: `true`.

Runtime behavior introduced by this sync: `false`.

Implementation-entry allowed next: false for recursive source ingestion unless current-main evidence names a concrete defect, failed check, stale sync, unresolved review item, or operator-flow blocker.

## Current-Main Result

Current main now implements `recursive_server_configured_directory_text_table_policy_v1`.

The server-configured source-directory scan route now records recursive normalized relative file authority under the existing source-directory ingestion model:

- owner service: `backend/app/services/layer3_source_directory_ingestion.py`;
- scan route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- status route: `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`;
- source root authority: `LAYER3_SOURCE_INGESTION_DIR`;
- allowed extensions: `.csv`, `.json`, `.txt`, and `.md`;
- runtime policy id: `recursive_server_configured_directory_text_table_policy_v1`;
- direct-child-only posture: `direct_child_only: False`;
- recursive traversal posture: `recursive_traversal_admitted: True`;
- maximum recursion depth: `2`;
- maximum normalized relative path segments: `3`, including filename;
- maximum file count: `100`;
- caller-selected recursive flag allowed: `false`;
- path exposure: normalized relative paths only; and
- downstream compatibility: existing source-directory material preview and deterministic text indexing accept recorded nested relative authority.

The implementation keeps the existing durable authority surface:

- `L3SourceDirectoryIngestionBatch`;
- `L3SourceDirectoryIngestionFile`;
- schema family `layer3.source_directory_ingestion_batch.v1`;
- directory fingerprint and authority-basis hashing; and
- idempotent replay behavior for matching request and authority basis.

## Merge Gate

PR `#1468` merged on 2026-05-19 at merge commit `2fa84f5f`.

PR `#1468` checks before merge:

- `backend-layer3-api`: `SUCCESS`, `3m27s`;
- `test`: `SUCCESS`, `3m52s`;
- comments: `0`;
- reviews: `0`;
- latestReviews: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`;
- merge state before merge: `CLEAN`.

Post-merge validation passed on current main at `2fa84f5f`:

```powershell
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
python .\tools\l3-fixture-validate.py --expect pending
python .\tools\l3-fixture-validate.py .\next_milestone_plans\Layer3_planning_docs\851_FIXTURE_CHECKPOINT.md --expect checkpoint
```

Observed results: Layer 3 progress state check `PASS`; Layer 3 target-selection validation `PASS (frozen)`; Layer 3 fixture-authority validation `PASS (pending)`; Layer 3 fixture-authority validation `PASS (checkpoint)`.

## Non-Admission Boundary

This current-main sync introduces no runtime behavior. It records current-main adoption of the recursive source-directory runtime implementation from PR `#1468`.

Still not admitted:

- caller-provided paths, URLs, globs, file bytes, or recursive flags;
- rendered control changes;
- source authority promotion;
- package/handoff/export/download behavior changes;
- connector dispatch changes;
- provider-private or provider-public URL behavior;
- credentials or network behavior;
- semantic/vector RAG widening beyond current deterministic local source-directory surfaces;
- prompt/model/provider qualitative generation;
- TabPFN runtime;
- NRC RAG runtime;
- optional-tool Gate C/pass-entry admission;
- broad auth/security behavior;
- PDFs, OCR, Office documents, images, archives, or arbitrary binaries;
- browser uploads;
- web connectors; and
- database connectors.

## Next Posture

The recursive source-ingestion runtime implementation is current-main synced.

The next exact posture is `select_next_major_layer3_end_to_end_gap_from_current_main_evidence`.

Do not continue recursive source-ingestion polish unless current-main evidence names a concrete defect, failed check, stale sync, unresolved review item, or operator-flow blocker.
