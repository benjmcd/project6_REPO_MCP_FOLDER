# 814 Source Directory External Export Download Delivery Runtime Entry Freeze

## Status

Branch-local runtime implementation entry for `source_directory_external_export_download_delivery_runtime`.

This freeze follows `813_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RUNTIME_CURRENT_MAIN_SYNC.md`, where current main selected `select_next_named_layer3_end_to_end_gap_after_source_directory_external_export_download_prepare_sync`.

## Selected Slice

Admit exactly one same-origin delivery reader for the already prepared source-directory external export/download package authority:

- Route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/deliver`
- Schema: `layer3.source_directory_qualitative_analysis_external_export_download_delivery.v1`
- Mode: `source_directory_qualitative_analysis_external_export_download_delivery_authority`
- Source gate: `814_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RUNTIME_ENTRY_FREEZE`
- Operator decision: `deliver_source_directory_external_export_download`
- Delivery mode: `same_origin_artifact_stream`
- Delivered state: `external_export_download_delivered`

The route may stream exactly one existing `L3OutputPackage` JSON artifact selected by `output_package_id`, `package_kind`, and `package_payload_hash`.

## Authority Checks

Delivery must revalidate the complete prepared source-directory chain before streaming:

- server-configured source-directory material and source authority
- deterministic qualitative analysis hash
- source-directory package review preview hash
- package construction basis hash
- approved package-review submit record
- source-directory handoff/export prepare record and envelope ref
- source-directory external export/download prepare record and descriptor ref
- package ids, package kinds, and payload hashes
- selected package row membership in the prepared package set
- server-owned artifact path under `settings.artifact_storage_dir`
- stored artifact content hash against the selected package payload hash

Delivery is read-only with respect to package state. It streams an existing artifact and does not write package payloads, mutate source package rows, or generate new package material.

## Non-Admission Boundary

This freeze does not admit:

- provider-public delivery
- private signed URLs
- real connector dispatch
- credential handling
- network egress
- package payload rewrite or reconstruction
- source package row mutation
- raw payload path exposure
- frontend durable controls
- broader source expansion
- RAG/vector indexing beyond already admitted source-directory authority

## Proof Target

The focused API regression proves:

- prepare authority can be reused by the delivery reader
- selected package bytes are streamed unchanged
- response headers expose only governed delivery metadata
- raw local source and storage paths remain absent from response headers
- repeat delivery re-streams the same artifact
- stale package payload hash fails closed

Validation completed:

- `python -m py_compile .\backend\app\services\layer3_source_directory_qualitative_analysis.py .\backend\app\api\layer3.py .\backend\app\services\layer3_bootstrap_contract.py .\backend\app\services\layer3_readiness_contract.py .\backend\tests\test_layer3_source_directory_qualitative_analysis.py .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py`
- `python -m pytest .\backend\tests\test_layer3_source_directory_qualitative_analysis.py::test_source_directory_qualitative_analysis_external_export_download_prepare_records_readiness -q`
- `python -m pytest .\backend\tests\test_layer3_source_directory_qualitative_analysis.py .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py -q`
- `python .\tools\l3-progress-check.py`
- `python .\tools\l3-target-selection-validate.py --expect frozen`

## Next Posture

After implementation proof and review clearance, sync this branch to current main as `await_current_main_sync_for_source_directory_external_export_download_delivery_runtime`.

After that sync, pivot to the next named Layer 3 end-to-end gap instead of repeating same-family package/export/active-authority proof loops unless current-main evidence names a concrete unresolved downstream reader or defect.
