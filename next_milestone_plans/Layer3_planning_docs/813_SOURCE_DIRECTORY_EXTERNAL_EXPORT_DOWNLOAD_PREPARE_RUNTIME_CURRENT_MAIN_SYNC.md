# 813 - Source Directory External Export Download Prepare Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_external_export_download_prepare_runtime`.

Sync doc: `813_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime doc: `812_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RUNTIME_ENTRY_FREEZE.md`.

Runtime PR: `#1417`.

Runtime branch: `codex/l3-next-gap`.

Runtime branch commit: `38bb55594d6c1129a4d11e872f884ebd865e218f`.

Runtime merge commit: `061a65074d91c86815e5dfe28a6deaad7f896184`.

Sync branch: `codex/l3-next-gap-sync`.

Synced result: `current_main_synced_source_directory_external_export_download_prepare_runtime`.

Runtime behavior introduced by implementation PR: `true`.

Runtime behavior introduced by this sync: `false`.

## Current-Main Evidence

Current main now includes the source-directory external export/download prepare runtime at `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/prepare`.

Current main also includes bootstrap/readiness exposure for `source_directory_external_export_download_prepare` and `source_directory_external_export_download_prepare_admitted`.

The route records `external_export_download_prepared` readiness over existing source-directory package construction, approved package-review submit, and source-directory handoff/export prepare authority.

The response uses schema `layer3.source_directory_qualitative_analysis_external_export_download_prepare.v1`, runtime mode `source_directory_qualitative_analysis_external_export_download_prepare_authority`, source gate `812_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RUNTIME_ENTRY_FREEZE`, target `source_directory_qualitative_analysis_package_download_reference`, and mode `reference_only_prepare`.

The durable reconciliation state uses schema `layer3.external_export_download_prepare_state.v1`, keeps payload refs redacted, and supports idempotent replay as `already_prepared`.

## Merge Gate

PR `#1417` merged on 2026-05-18 at merge commit `061a65074d91c86815e5dfe28a6deaad7f896184`.

Review/check state before merge:

- `backend-layer3-api`: `SUCCESS`, `2m59s`;
- `test`: `SUCCESS`, `3m40s`;
- comments: `0`;
- reviews: `0`;
- latestReviews: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`;
- merge state: `CLEAN`.

## Non-Admission Boundary

This sync introduces no runtime behavior. It does not add models, migrations, package rows, package payload writes, package payload rewrites, package mutation/reconstruction, source package row mutation, replacement package rows, APS handoff dispatch, same-origin delivery/streaming, browser download, provider-public delivery/use, provider-private signed URL behavior, connector/destination dispatch, real connector invocation, credentials, network egress, auth/security broadening, frontend-durable authority, frontend-rendered controls, prompt/model/provider runtime, qualitative generation runtime, a new source family, arbitrary source ingestion, vector indexing expansion, embedding generation expansion, persistent vector store, raw local path exposure, full segment text exposure, raw vector exposure, or full mockup activation.

## Validation

Current-main sync validation:

- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null; python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null` - `PASS`;
- `python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py` - `PASS`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py .\backend\tests\test_layer3_api.py::test_layer3_api_full_first_slice_flow -q` - `PASS`, `3 passed`;
- `git diff --check` - `PASS` with CRLF normalization warnings only.

## Next Posture

The source-directory external export/download prepare runtime is current-main synced.

Do not continue additional same-family package/export/active-authority proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader.

The next exact current-main posture is `select_next_named_layer3_end_to_end_gap_after_source_directory_external_export_download_prepare_sync`.
