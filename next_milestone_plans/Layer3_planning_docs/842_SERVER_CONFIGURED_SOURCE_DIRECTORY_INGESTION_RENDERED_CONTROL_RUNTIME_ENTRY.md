# 842 - Server Configured Source Directory Ingestion Rendered Control Runtime Entry

## Status

Status: branch-local rendered control runtime entry for `server_configured_source_directory_ingestion_rendered_control_runtime`.

Doc: `842_SERVER_CONFIGURED_SOURCE_DIRECTORY_INGESTION_RENDERED_CONTROL_RUNTIME_ENTRY.md`.

Branch: `codex/l3-source-ingestion-runtime`.

Selected predecessor posture: `select_server_configured_local_source_directory_ingestion_runtime_after_hybrid_delivery_rendered_control_sync`.

Predecessor current-main sync: `841_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_EXTERNAL_EXPORT_DOWNLOAD_RENDERED_DELIVERY_CONTROL_CURRENT_MAIN_SYNC.md`.

Already-synced backend runtime authority: `745_SERVER_CONFIGURED_OPERATOR_DIRECTORY_TEXT_TABLE_INGESTION_RUNTIME_CURRENT_MAIN_SYNC.md`.

## Scope Decision

The selected current-main posture names server-configured local source-directory ingestion runtime after the source-directory hybrid delivery rendered-control sync.

Current main already contains the backend ingestion runtime through docs `744` and `745`, so this pass does not duplicate scanner, model, migration, or API route behavior.

This pass implements only the missing operator-visible rendered scan/status control over that already current-main backend authority.

The rendered control is `rendered_server_configured_source_directory_ingestion_control`.

Runtime behavior introduced by this pass: `true`.

Frontend rendered controls introduced by this pass: `true`.

Frontend durable authority introduced by this pass: `false`.

Backend route behavior introduced by this pass: `false`.

Database model or migration behavior introduced by this pass: `false`.

## Runtime Surface

The rendered `/review/layer3` control adds:

- section `#source-directory-ingestion-rendered-controls`;
- form `#source-directory-ingestion-scan-form`;
- client request input `#source-directory-ingestion-client-request-id`;
- batch id input `#source-directory-ingestion-batch-id`;
- status button `#source-directory-ingestion-status`;
- scan button `#source-directory-ingestion-scan-submit`;
- status/proof panel `#source-directory-ingestion-panel`.

The UI submits only fixed server-authority scan fields:

- `operator_decision: scan_server_configured_operator_directory`;
- `source_family: server_configured_operator_directory_text_table_source_family`;
- `ingestion_mode: server_configured_operator_directory_text_table_ingestion`.

The UI calls only the already current-main source-directory ingestion API routes:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`.

The rendered proof panel reports schema `layer3.source_directory_ingestion_batch.v1`, source root ref, redacted raw-path posture, direct-child-only posture, allowed extension set, eligible file count, admitted file summaries, and blocked downstream runtime locks.

## Non-Admission Boundary

This pass does not add backend routes, models, migrations, durable table behavior, scanner behavior, or source-family breadth.

Still not admitted:

- caller-supplied paths, URLs, globs, directories, or recursive flags;
- browser-supplied file bytes or local upload expansion;
- PDFs, OCR, Office documents, arbitrary binaries, archives, or executable files;
- web connector retrieval, real connector invocation, connector dispatch, destination writes, credentials, receipts, or network egress;
- RAG/vector indexing, vector retrieval, persistent vector store, raw vector exposure, or qualitative-hybrid analysis runtime;
- provider-public delivery/use or provider-private signed URL behavior;
- package construction, package mutation/reconstruction, package payload rewrite, source package row mutation, replacement package rows, or supersession commit;
- raw local path exposure, raw payload ref exposure, full segment text exposure, prompt/model/provider runtime, auth/security broadening, full mockup activation, or frontend durable authority.

## Validation

Branch-local validation:

- `node --check .\backend\app\review_ui\static\layer3.js` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_page.py -q` - `PASS`, `5 passed`, `3 warnings`;
- `python -m py_compile .\tools\l3-progress-check.py` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_page.py .\backend\tests\test_layer3_source_directory_ingestion.py -q` - `PASS`, `18 passed`, `3 warnings`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`;
- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json` - `PASS`;
- `python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json` - `PASS`;
- `git diff --check` - `PASS` with CRLF normalization warnings only.

## Next Posture

The next required action after merge is `current_main_sync_server_configured_source_directory_ingestion_rendered_control_runtime`.

After that sync, do not continue additional same-family package/export/active-authority proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader.

The next major deferred lane posture is `select_next_major_layer3_end_to_end_gap_from_current_main_evidence`, selected from the current-main Layer 3 end-to-end gap list rather than reopening source ingestion by default.
