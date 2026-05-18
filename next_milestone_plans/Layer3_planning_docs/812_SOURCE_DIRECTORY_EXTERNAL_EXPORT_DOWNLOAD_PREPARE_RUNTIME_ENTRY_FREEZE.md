# 812 - Source Directory External Export Download Prepare Runtime Entry Freeze

## Status

Status: branch-local implementation-entry freeze and runtime proof for `source_directory_external_export_download_prepare_runtime`.

Planning artifact: `812_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RUNTIME_ENTRY_FREEZE.md`.

Predecessor current-main posture: `select_next_named_layer3_end_to_end_gap_after_source_directory_package_handoff_operator_status_surface_sync`.

Runtime branch: `codex/l3-next-gap`.

Selected implementation action: `implement_source_directory_external_export_download_prepare_after_package_handoff_operator_status_surface_sync`.

Runtime status after implementation: `source_directory_external_export_download_prepare_runtime_implemented_branch_local`.

Runtime behavior introduced by this pass: `true`.

## Selected Behavior

This pass admits exactly one source-directory external export/download readiness step after the existing source-directory qualitative-analysis handoff/export prepare authority.

The new route is `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/prepare`.

The response uses schema `layer3.source_directory_qualitative_analysis_external_export_download_prepare.v1`.

The runtime mode is `source_directory_qualitative_analysis_external_export_download_prepare_authority`.

The runtime source gate is `812_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RUNTIME_ENTRY_FREEZE`.

The durable reconciliation state uses schema `layer3.external_export_download_prepare_state.v1` with `external_export_download_prepare_schema_id` set to `layer3.source_directory_qualitative_analysis_external_export_download_prepare.v1`.

The target is `source_directory_qualitative_analysis_package_download_reference`.

The mode is `reference_only_prepare`.

The operator decision is `prepare_source_directory_external_export_download`.

## Authority Requirements

The runtime requires existing source-directory package construction, approved package-review submit, and source-directory handoff/export prepare authority.

The runtime validates the server-recomputed qualitative-analysis hash, source-directory package-review preview hash, construction basis hash, reconciliation id, package-review submit record ref, prepare record ref, handoff export state, handoff export envelope ref, output package ids, package kinds, and payload hashes.

The runtime records `external_export_download_prepared` readiness in the existing reconciliation summary and session summary.

The runtime supports idempotent replay as `already_prepared`.

The runtime keeps package payload refs redacted from the API response and readiness descriptor.

## Non-Admission Boundary

This pass does not add models, migrations, package rows, package payload writes, package payload rewrites, package mutation/reconstruction, source package row mutation, replacement package rows, APS handoff dispatch, same-origin delivery/streaming, browser download, provider-public delivery/use, provider-private signed URL behavior, connector/destination dispatch, real connector invocation, credentials, network egress, auth/security broadening, frontend-durable authority, frontend-rendered controls, prompt/model/provider runtime, qualitative generation runtime, a new source family, arbitrary source ingestion, vector indexing expansion, embedding generation expansion, persistent vector store, raw local path exposure, full segment text exposure, raw vector exposure, or full mockup activation.

## Validation

Branch-local validation:

- `python -m py_compile .\backend\app\services\layer3_source_directory_qualitative_analysis.py .\backend\app\api\layer3.py .\backend\app\services\layer3_bootstrap_contract.py .\backend\app\services\layer3_readiness_contract.py .\backend\tests\test_layer3_source_directory_qualitative_analysis.py .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_qualitative_analysis.py .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py -q` - `PASS`, `14 passed`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_qualitative_analysis.py -q` - `PASS`, `12 passed`.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_source_directory_external_export_download_prepare_runtime`.

After sync, pivot to `select_next_named_layer3_end_to_end_gap_after_source_directory_external_export_download_prepare_sync` unless current-main evidence shows a concrete unresolved source-directory external export/download prepare defect or named downstream reader.
