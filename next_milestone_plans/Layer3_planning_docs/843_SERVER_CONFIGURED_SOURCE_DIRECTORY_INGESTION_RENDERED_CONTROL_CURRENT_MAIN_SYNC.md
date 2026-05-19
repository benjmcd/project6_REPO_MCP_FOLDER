# 843 - Server Configured Source Directory Ingestion Rendered Control Current-Main Sync

## Status

Status: current-main proof/control sync for `server_configured_source_directory_ingestion_rendered_control_runtime`.

Sync doc: `843_SERVER_CONFIGURED_SOURCE_DIRECTORY_INGESTION_RENDERED_CONTROL_CURRENT_MAIN_SYNC.md`.

Runtime doc: `842_SERVER_CONFIGURED_SOURCE_DIRECTORY_INGESTION_RENDERED_CONTROL_RUNTIME_ENTRY.md`.

Runtime PR: `#1448`.

Runtime branch: `codex/l3-source-ingestion-runtime`.

Runtime branch commit: `63f6c2ebf98ce849aad14b02c67e8dc79a2cdd03`.

Runtime merge commit: `d27b0e1282e95b1ab3b85e232aa0e0d8c34b5d42`.

Sync branch: `codex/l3-source-ingestion-runtime-sync`.

Synced result: `current_main_synced_server_configured_source_directory_ingestion_rendered_control_runtime`.

Runtime behavior introduced by implementation PR: `true`.

Runtime behavior introduced by this sync: `false`.

## Current-Main Evidence

Current main now includes bounded rendered `/review/layer3` scan/status controls for the already current-main server-configured operator directory text/table ingestion backend.

The rendered control is `rendered_server_configured_source_directory_ingestion_control`.

Current main includes:

- section `#source-directory-ingestion-rendered-controls`;
- form `#source-directory-ingestion-scan-form`;
- input `#source-directory-ingestion-client-request-id`;
- input `#source-directory-ingestion-batch-id`;
- button `#source-directory-ingestion-status`;
- button `#source-directory-ingestion-scan-submit`;
- panel `#source-directory-ingestion-panel`.

The current-main control submits only fixed server-authority scan fields:

- `operator_decision: scan_server_configured_operator_directory`;
- `source_family: server_configured_operator_directory_text_table_source_family`;
- `ingestion_mode: server_configured_operator_directory_text_table_ingestion`.

The current-main control calls only the already-synced source-directory ingestion backend routes:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`.

The already current-main backend runtime authority remains `745_SERVER_CONFIGURED_OPERATOR_DIRECTORY_TEXT_TABLE_INGESTION_RUNTIME_CURRENT_MAIN_SYNC.md`.

## Merge Gate

PR `#1448` merged on 2026-05-19 at merge commit `d27b0e1282e95b1ab3b85e232aa0e0d8c34b5d42`.

PR `#1448` checks before merge:

- `backend-layer3-api`: `SUCCESS`, `3m13s`;
- `test`: `SUCCESS`, `3m32s`;
- comments: `0`;
- reviews: `0`;
- latestReviews: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`;
- merge state before merge: `CLEAN`.

## Non-Admission Boundary

This current-main sync introduces no additional runtime behavior. It records current-main adoption of the already-merged rendered server-configured source-directory ingestion scan/status control only.

Still not admitted:

- Additional source ingestion widening without a named current-main defect or downstream reader.
- Caller-supplied paths, URLs, globs, directories, recursive flags, or browser file bytes.
- PDFs, OCR, Office documents, arbitrary binaries, archives, executable files, web connectors, or arbitrary recursive ingestion.
- RAG/vector indexing, vector retrieval, persistent vector store, raw vector exposure, or qualitative-hybrid analysis runtime.
- Provider-public delivery/use, provider-private signed URL behavior, connector dispatch, real connector invocation, destination writes, credentials, receipts, or network egress.
- Package construction, package mutation/reconstruction, package payload rewrite, source package row mutation, replacement package rows, or supersession commit.
- Raw local path exposure, raw payload ref exposure, full segment text exposure, prompt/model/provider runtime, auth/security broadening, full mockup activation, or frontend durable authority.

## Validation

Runtime PR branch-local validation:

- `node --check .\backend\app\review_ui\static\layer3.js` - `PASS`;
- `python -m py_compile .\tools\l3-progress-check.py` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_page.py -q` - `PASS`, `5 passed`, `3 warnings`;
- `python -m pytest .\backend\tests\test_layer3_page.py .\backend\tests\test_layer3_source_directory_ingestion.py -q` - `PASS`, `18 passed`, `3 warnings`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`;
- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json` - `PASS`;
- `python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json` - `PASS`;
- `git diff --check` - `PASS` with CRLF normalization warnings only.

Current-main sync validation:

- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`.

## Next Posture

The server-configured source-directory ingestion rendered control runtime is current-main synced.

Do not continue additional same-family source-ingestion proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader.

The next exact current-main posture is `select_next_major_layer3_end_to_end_gap_from_current_main_evidence`.
