# 840 - Source Directory Hybrid Context Qualitative Analysis External Export Download Rendered Delivery Control Runtime Entry

## Status

Status: branch-local rendered delivery control runtime entry for `source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_rendered_delivery_control_runtime`.

Runtime doc: `840_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_EXTERNAL_EXPORT_DOWNLOAD_RENDERED_DELIVERY_CONTROL_RUNTIME_ENTRY.md`.

Branch: `codex/l3-next-gap-after-hybrid-delivery`.

Current-main predecessor: `839_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CURRENT_MAIN_SYNC.md`.

Selected posture satisfied: `select_next_named_layer3_end_to_end_gap_after_source_directory_hybrid_external_export_download_delivery_sync`.

Runtime behavior introduced by this pass: `true`.

Frontend rendered controls introduced by this pass: `true`.

Frontend durable authority introduced by this pass: `false`.

## Selected Runtime

This pass admits only a bounded rendered `/review/layer3` operator control for the already current-main source-directory hybrid external export/download delivery backend.

The rendered control is `rendered_source_directory_hybrid_external_export_download_delivery_control`.

The control accepts a server-derived source-directory hybrid external export/download delivery authority JSON payload, sanitizes it through an allowlist, verifies a validate-only delivery-status response, and then submits one browser-managed same-origin attachment request to the already admitted delivery route.

The selected routes are unchanged current-main routes:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver/status`
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver`

The rendered control requires:

- `operator_decision`: `deliver_source_directory_hybrid_external_export_download`
- `external_export_download_target`: `source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference`
- `download_mode`: `reference_only_prepare`
- `external_export_download_state`: `external_export_download_prepared`
- `delivery_mode`: `same_origin_artifact_stream`
- status schema `layer3.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status.v1`
- delivery schema `layer3.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery.v1`

## Authority Chain

The browser control does not mint delivery authority. It accepts a server-derived authority packet from the operator, selects an already described package id/kind/hash, and calls the delivery-status route before enabling submit.

Submit is enabled only when the latest status response matches the payload's readiness refs, selected package identity, package payload hash, same-origin delivery flags, blocked provider-public/provider-private/connector/network/front-end-durable flags, blocked package rewrite/source row mutation flags, and blocked raw local path exposure.

The final delivery request still goes through the backend delivery reader and streams only as a browser-managed same-origin attachment.

## Non-Admission Boundary

This pass does not admit:

- Provider-public delivery/use.
- Provider-private signed URL behavior or signed-reference use.
- Connector dispatch, real connector invocation, credentials, destination writes, receipts, or network egress.
- Frontend durable authority.
- Durable delivery rows or delivery audit rows.
- Package mutation, package payload rewrite, source package row mutation, replacement package rows, or supersession commit.
- New source family expansion, arbitrary ingestion, recursive ingestion, persistent vector store, embedding generation expansion, prompt/model/provider runtime, or qualitative generation runtime.
- Raw local path, raw payload ref, raw package payload path, full segment text, or raw vector exposure.

## Validation

- `node --check .\backend\app\review_ui\static\layer3.js` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_page.py -q` - `PASS`, `4 passed`, `3 warnings`;
- `python -m py_compile .\tools\l3-progress-check.py` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_page.py .\backend\tests\test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivers_selected_package -q` - `PASS`, `5 passed`, `3 warnings`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`;
- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json` - `PASS`;
- `python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json` - `PASS`;
- `git diff --check` - `PASS` with CRLF normalization warnings only.

## Next Posture

After merge, the next required action is `current_main_sync_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_rendered_delivery_control_runtime`.

After that sync, pivot to `select_server_configured_local_source_directory_ingestion_runtime_after_hybrid_delivery_rendered_control_sync` unless current-main evidence names a concrete unresolved rendered delivery-control defect or a required downstream reader.
