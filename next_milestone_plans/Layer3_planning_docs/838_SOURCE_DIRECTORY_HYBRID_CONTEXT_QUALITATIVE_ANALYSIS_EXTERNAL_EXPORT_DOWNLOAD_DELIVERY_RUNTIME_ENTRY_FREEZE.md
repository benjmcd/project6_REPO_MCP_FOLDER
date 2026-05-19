# 838 - Source Directory Hybrid Context Qualitative Analysis External Export Download Delivery Runtime Entry Freeze

## Status

Status: branch-local runtime entry freeze and implementation for `source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_runtime`.

Runtime doc: `838_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RUNTIME_ENTRY_FREEZE.md`.

Branch: `codex/l3-hybrid-export-download-delivery`.

Current-main predecessor: `837_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_CURRENT_MAIN_SYNC.md`.

Selected posture satisfied: `select_next_named_layer3_end_to_end_gap_after_source_directory_hybrid_external_export_download_prepare_sync`.

Runtime behavior introduced by this pass: `true`.

## Selected Runtime

This pass admits only a same-origin attachment delivery reader and a validate-only delivery-status reader for an already prepared source-directory hybrid context-packet qualitative-analysis external export/download package.

The admitted routes are:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver/status`
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver`

The delivery request must reference the existing 836 prepare authority:

- `external_export_download_state`: `external_export_download_prepared`
- `external_export_download_target`: `source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference`
- `download_mode`: `reference_only_prepare`
- `delivery_mode`: `same_origin_artifact_stream`
- `operator_decision`: `deliver_source_directory_hybrid_external_export_download`

## Authority Chain

The delivery reader recomputes and validates the current source-directory hybrid qualitative-analysis authority, package-review preview hash, package construction basis, package-review submit state, handoff/export prepare authority, and external export/download prepare record before selecting a package payload.

The selected package must be one of the already constructed source-directory hybrid package rows for the reconciliation record. The reader validates `output_package_id`, `package_kind`, and `package_payload_hash`, then streams only the server-owned package payload under artifact storage.

The status route calls the same delivery authority reader but reports readiness without streaming the file.

## Non-Admission Boundary

This pass does not admit:

- Provider-public delivery/use.
- Provider-private signed URL behavior or signed-reference use.
- Connector dispatch, real connector invocation, credentials, destination writes, receipts, or network egress.
- Frontend durable authority or rendered controls.
- Durable delivery rows or delivery audit rows.
- Package mutation, package payload rewrite, source package row mutation, replacement package rows, or supersession commit.
- New source family expansion, arbitrary ingestion, persistent vector store, embedding generation expansion, prompt/model/provider runtime, or qualitative generation runtime.
- Raw local path, raw payload ref, raw package payload path, full segment text, or raw vector exposure.

## Validation

- `python -m py_compile .\backend\app\services\layer3_source_directory_hybrid_analysis.py .\backend\app\api\layer3.py .\backend\tests\test_layer3_source_directory_vector_retrieval.py` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivers_selected_package -q` - `PASS`, `1 passed`, `3 warnings`;
- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json` - `PASS`;
- `python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json` - `PASS`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py -q` - `PASS`, `19 passed`, `3 warnings`.

## Next Posture

After merge, the next required action is `current_main_sync_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_runtime`.

After that sync, the next whole-project posture should select the next named Layer 3 end-to-end gap. Do not continue same-family source-directory package/export loops unless current-main evidence names a concrete unresolved defect or downstream reader.
