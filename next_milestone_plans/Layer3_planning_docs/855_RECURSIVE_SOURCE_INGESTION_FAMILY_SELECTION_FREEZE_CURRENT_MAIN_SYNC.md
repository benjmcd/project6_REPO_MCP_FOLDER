# 855 - Recursive Source Ingestion Family Selection Freeze Current-Main Sync

## Status

Status: current-main proof/control sync for `recursive_server_configured_operator_directory_text_table_source_family`.

Sync doc: `855_RECURSIVE_SOURCE_INGESTION_FAMILY_SELECTION_FREEZE_CURRENT_MAIN_SYNC.md`.

Synced freeze doc: `854_RECURSIVE_SOURCE_INGESTION_FAMILY_SELECTION_FREEZE.md`.

Freeze PR: `#1464`.

Freeze branch: `codex/l3-recursive-source-ingestion-freeze`.

Freeze branch commit: `070a50ffade4c3d0d255c836e41b754152692ecb`.

Freeze merge commit: `cd7cd385710102724c572615b33105956a22d52b`.

Sync branch: `codex/l3-recursive-source-ingestion-freeze-sync`.

Synced result: `current_main_synced_recursive_source_ingestion_family_selection_freeze`.

Runtime behavior introduced by freeze: `false`.

Runtime behavior introduced by this sync: `false`.

Implementation-entry allowed next: false until a later runtime-entry freeze selects exact traversal limits, exclusion policy, stale-authority behavior, status/readiness projection, downstream material authority compatibility, and proof scope.

## Current-Main Result

Current main now records `recursive_server_configured_operator_directory_text_table_source_family` as the next broader source-ingestion family selection.

Current main does not implement recursive traversal.

The existing direct-child source-directory ingestion runtime remains unchanged:

- current owner service: `backend/app/services/layer3_source_directory_ingestion.py`;
- current scan route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- current status route: `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`;
- current source root authority: `LAYER3_SOURCE_INGESTION_DIR`;
- current file family: `.csv`, `.json`, `.txt`, and `.md`;
- current direct-child posture: `direct_child_only: True`; and
- current recursive posture: `recursive_traversal_admitted: False`.

The next runtime-entry freeze must still select maximum recursion depth, hidden file/directory policy, symlink/junction/device/path-escape rejection, duplicate/case-fold conflict handling, nested relative path redaction, nested directory fingerprint basis, stale nested-file identity behavior, file/count/byte caps, empty subtree behavior, exclusion policy, status/readiness projection, downstream material authority compatibility, and isolated proof scope.

## Merge Gate

PR `#1464` merged on 2026-05-19 at merge commit `cd7cd385710102724c572615b33105956a22d52b`.

PR `#1464` checks before merge:

- `backend-layer3-api`: `SUCCESS`, `3m26s`;
- `test`: `SUCCESS`, `4m30s`;
- comments: `0`;
- reviews: `0`;
- latestReviews: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`;
- merge state before merge: `CLEAN`.

Post-merge validation passed on a tree identical to `project6-origin/main` at `cd7cd385710102724c572615b33105956a22d52b`:

```powershell
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
python .\tools\l3-fixture-validate.py --expect pending
python .\tools\l3-fixture-validate.py .\next_milestone_plans\Layer3_planning_docs\851_FIXTURE_CHECKPOINT.md --expect checkpoint
```

Observed results: Layer 3 progress state check `PASS`; Layer 3 target-selection validation `PASS (frozen)`; Layer 3 fixture-authority validation `PASS (pending)`; Layer 3 fixture-authority validation `PASS (checkpoint)`.

## Non-Admission Boundary

This current-main sync introduces no runtime behavior. It records current-main adoption of the no-runtime recursive source-ingestion family selection only.

Still not admitted:

- recursive traversal in the live API;
- request-schema changes;
- rendered control changes;
- source authority promotion;
- package/handoff/export/download integration;
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
- web connectors;
- database connectors; and
- caller-provided paths, URLs, globs, or recursive flags.

## Next Posture

The recursive source-ingestion family selection is current-main synced.

The next exact posture is `select_recursive_source_ingestion_runtime_policy_before_implementation`.

Do not implement recursive traversal until a later runtime-entry freeze selects exact traversal limits, exclusion policy, stale-authority behavior, status/readiness projection, downstream material authority compatibility, and proof scope.
