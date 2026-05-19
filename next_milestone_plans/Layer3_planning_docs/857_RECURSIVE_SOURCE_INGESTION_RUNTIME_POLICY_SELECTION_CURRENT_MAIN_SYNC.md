# 857 - Recursive Source Ingestion Runtime Policy Selection Current-Main Sync

## Status

Status: current-main proof/control sync for `recursive_server_configured_directory_text_table_policy_v1`.

Sync doc: `857_RECURSIVE_SOURCE_INGESTION_RUNTIME_POLICY_SELECTION_CURRENT_MAIN_SYNC.md`.

Synced freeze doc: `856_RECURSIVE_SOURCE_INGESTION_RUNTIME_POLICY_SELECTION_FREEZE.md`.

Freeze PR: `#1466`.

Freeze branch: `codex/l3-recursive-source-ingestion-policy`.

Freeze branch commit: `106d6c97f0cdd03bf94e4fd44db1bf0cdc9c25f0`.

Freeze merge commit: `4afd496541649f68812b2c148817dd8e84259b83`.

Sync branch: `codex/l3-recursive-source-ingestion-policy-sync`.

Synced result: `current_main_synced_recursive_source_ingestion_runtime_policy_selection_freeze`.

Runtime behavior introduced by freeze: `false`.

Runtime behavior introduced by this sync: `false`.

Implementation-entry allowed next: true, for only `implement_recursive_server_configured_operator_directory_text_table_ingestion` under `recursive_server_configured_directory_text_table_policy_v1`.

## Current-Main Result

Current main now records `recursive_server_configured_directory_text_table_policy_v1` as the selected recursive source-ingestion runtime policy.

Current main does not implement recursive traversal.

The existing direct-child source-directory ingestion runtime remains unchanged:

- current owner service: `backend/app/services/layer3_source_directory_ingestion.py`;
- current scan route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- current status route: `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`;
- current source root authority: `LAYER3_SOURCE_INGESTION_DIR`;
- current file family: `.csv`, `.json`, `.txt`, and `.md`;
- current direct-child posture: `direct_child_only: True`; and
- current recursive posture: `recursive_traversal_admitted: False`.

The selected future implementation policy is:

- source root authority: `LAYER3_SOURCE_INGESTION_DIR`;
- allowed extensions: `.csv`, `.json`, `.txt`, and `.md`;
- maximum recursion depth: `2`;
- maximum normalized relative path segments: `3`, including the filename;
- maximum file count: `100`;
- maximum per-file bytes: `MAX_UPLOAD_MB * 1024 * 1024`;
- maximum aggregate bytes: `MAX_UPLOAD_MB * 1024 * 1024 * 100`;
- ordering: deterministic lexical normalized relative path order;
- caller-selected recursive flag allowed: `false`;
- path exposure: normalized relative paths only; and
- raw configured root and raw local nested paths remain redacted.

## Merge Gate

PR `#1466` merged on 2026-05-19 at merge commit `4afd496541649f68812b2c148817dd8e84259b83`.

PR `#1466` checks before merge:

- `backend-layer3-api`: `SUCCESS`, `4m1s`;
- `test`: `SUCCESS`, `3m56s`;
- comments: `0`;
- reviews: `0`;
- latestReviews: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`;
- merge state before merge: `CLEAN`.

Post-merge validation passed on current main at `4afd496541649f68812b2c148817dd8e84259b83`:

```powershell
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
python .\tools\l3-fixture-validate.py --expect pending
python .\tools\l3-fixture-validate.py .\next_milestone_plans\Layer3_planning_docs\851_FIXTURE_CHECKPOINT.md --expect checkpoint
```

Observed results: Layer 3 progress state check `PASS`; Layer 3 target-selection validation `PASS (frozen)`; Layer 3 fixture-authority validation `PASS (pending)`; Layer 3 fixture-authority validation `PASS (checkpoint)`.

## Non-Admission Boundary

This current-main sync introduces no runtime behavior. It records current-main adoption of the no-runtime recursive source-ingestion runtime policy selection only.

Still not admitted:

- recursive traversal before the implementation pass;
- request-schema changes before implementation;
- caller-provided paths, URLs, globs, file bytes, or recursive flags;
- rendered control changes;
- source authority promotion;
- package/handoff/export/download integration changes;
- connector dispatch;
- provider-private or provider-public URL behavior;
- credentials or network behavior;
- semantic/vector RAG widening;
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

The recursive source-ingestion runtime policy selection is current-main synced.

The next exact posture is `implement_recursive_server_configured_operator_directory_text_table_ingestion`.

Implementation must stay inside `recursive_server_configured_directory_text_table_policy_v1` and prove the fail-closed traversal, redaction, durable authority, idempotency, stale-authority, direct-child regression, and no-forbidden-adjacent-behavior requirements selected by doc `856`.
