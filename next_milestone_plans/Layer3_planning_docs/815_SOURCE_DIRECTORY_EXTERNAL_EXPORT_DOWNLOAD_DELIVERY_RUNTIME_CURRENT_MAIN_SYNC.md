# 815 - Source Directory External Export Download Delivery Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_directory_external_export_download_delivery_runtime`.

Sync doc: `815_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime doc: `814_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RUNTIME_ENTRY_FREEZE.md`.

Runtime PR: `#1419`.

Runtime branch: `codex/l3-source-expansion`.

Runtime branch commit: `a7c7658c44a0bb82f4bf88e20a6f792a1cda6ffb`.

Runtime merge commit: `a2f35bd934b026f8eeabfbccb0dcf788d41cb1ea`.

Sync branch: `codex/l3-source-expansion-sync`.

Synced result: `current_main_synced_source_directory_external_export_download_delivery_runtime`.

Runtime behavior introduced by implementation PR: `true`.

Runtime behavior introduced by this sync: `false`.

## Current-Main Evidence

Current main now includes the source-directory external export/download delivery runtime at `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/deliver`.

Current main also includes bootstrap/readiness exposure for `source_directory_external_export_download_deliver` and `source_directory_external_export_download_deliver_admitted`.

The route streams exactly one already constructed `L3OutputPackage` JSON artifact after revalidating source-directory material authority, qualitative-analysis hash, package-review preview hash, construction basis hash, approved package-review submit state, handoff/export prepare state, external export/download prepare state, package identity lists, selected package kind, selected package payload hash, server-owned artifact path, and stored artifact content hash.

The response uses schema `layer3.source_directory_qualitative_analysis_external_export_download_delivery.v1`, runtime mode `source_directory_qualitative_analysis_external_export_download_delivery_authority`, source gate `814_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RUNTIME_ENTRY_FREEZE`, target `source_directory_qualitative_analysis_package_download_reference`, download mode `reference_only_prepare`, delivery mode `same_origin_artifact_stream`, and delivered state `external_export_download_delivered`.

The delivery path is read-only for package state. It streams the existing package artifact and does not write package payloads, rewrite packages, mutate source package rows, expose raw local paths, or generate provider/connector delivery records.

## Merge Gate

PR `#1419` merged on 2026-05-18 at merge commit `a2f35bd934b026f8eeabfbccb0dcf788d41cb1ea`.

Review/check state before merge:

- `backend-layer3-api`: `SUCCESS`, `3m1s`;
- `test`: `SUCCESS`, `8m33s`;
- comments: `0`;
- reviews: `0`;
- latestReviews: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`;
- merge state: `CLEAN`.

## Non-Admission Boundary

This sync introduces no runtime behavior. It does not add models, migrations, package rows, package payload writes, package payload rewrites, package mutation/reconstruction, source package row mutation, replacement package rows, APS handoff dispatch, provider-public delivery/use, provider-private signed URL behavior, connector/destination dispatch, real connector invocation, credentials, network egress, auth/security broadening, frontend-durable authority, frontend-rendered controls, prompt/model/provider runtime, qualitative generation runtime, a new source family, arbitrary source ingestion, vector indexing expansion, embedding generation expansion, persistent vector store, raw local path exposure, full segment text exposure, raw vector exposure, or full mockup activation.

## Validation

Current-main sync validation:

- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null; python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null` - `PASS`;
- `python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py` - `PASS`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_bootstrap_contract.py .\backend\tests\test_layer3_readiness_contract.py .\backend\tests\test_layer3_api.py::test_layer3_api_full_first_slice_flow -q` - `PASS`, `3 passed`;
- `git diff --check` - `PASS` with CRLF normalization warning only.

## Next Posture

The source-directory external export/download delivery runtime is current-main synced.

Do not continue additional same-family package/export/active-authority proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader.

The next exact current-main posture is `select_next_named_layer3_end_to_end_gap_after_source_directory_external_export_download_delivery_sync`.
