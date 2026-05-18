# 802 - Source Directory Qualitative Analysis Package Preview Runtime Entry Freeze

## Status

Status: branch-local implementation-entry freeze and runtime proof for `source_directory_qualitative_analysis_package_preview_runtime`.

Runtime doc: `802_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_PREVIEW_RUNTIME_ENTRY_FREEZE.md`.

Runtime branch: `codex/l3-source-package-preview`.

Current-main preflight checkpoint: `7da0b5bd3f4d992f24de250956360d1515bdfa65`.

Predecessor current-main sync doc: `801_SOURCE_DIRECTORY_OPERATOR_READINESS_STATUS_SURFACE_RUNTIME_CURRENT_MAIN_SYNC.md`.

Selected from posture: `select_next_named_layer3_end_to_end_gap_after_source_directory_operator_status_surface_sync`.

Selected implementation action: `implement_source_directory_qualitative_analysis_read_only_package_review_preview_after_operator_status_surface_sync`.

Runtime status after implementation: `source_directory_qualitative_analysis_package_preview_runtime_implemented_branch_local`.

## Selected Runtime

This slice adds a read-only package-review preview descriptor to the already-admitted source-directory qualitative-hybrid analysis API response.

Runtime owner:

- `backend/app/services/layer3_source_directory_qualitative_analysis.py`
- `backend/app/api/layer3.py`

Proof owner:

- `backend/tests/test_layer3_source_directory_qualitative_analysis.py`

The runtime exposes:

- `source_directory_package_review_preview_enabled: True`;
- `source_directory_package_review_preview_hash`;
- `source_directory_package_review_preview`;
- candidate package kinds `canonical_internal`, `user_facing`, and `review_facing`; and
- package-lifecycle flags showing package commit, package-review submit, handoff, and external export/download are still disabled.

The package preview schema is `layer3.source_directory_qualitative_analysis_package_review_preview.v1`.

The package preview mode is `read_only_source_directory_qualitative_analysis_package_review_preview`.

The source gate is `802_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_PREVIEW_RUNTIME_ENTRY_FREEZE`.

## Authority Chain

The package preview is computed from the source-directory qualitative-analysis response authority:

- `server_configured_operator_directory_text_table_source_family`;
- `source_directory_material_retrieval_augmented_context_packet_authority`;
- `source_directory_material_context_packet_qualitative_hybrid_analysis_authority`;
- `qualitative_analysis_hash`;
- `context_packet_hash`;
- `index_authority_hash`;
- `material_snapshot_id`;
- `source_ingestion_batch_id`; and
- `source_ingestion_file_id`.

The preview is deterministic and read-only. It does not create an `L3PassRun`, `AnalysisRun`, `L3OutputPackage`, `L3ReconciliationRecord`, connector row, provider row, delivery receipt, frontend state, or any package payload.

## Non-Admission Boundary

This runtime does not admit package construction, package-review submit, package payload write, package payload rewrite, source package row mutation, package mutation/reconstruction, replacement package row creation, handoff/export rerun, provider-public delivery/use, provider-private signed URL behavior, connector/destination dispatch, real connector invocation, credentials, network egress, auth/security broadening, frontend-durable authority, frontend-rendered controls, prompt/model/provider runtime, qualitative generation runtime, new source family, arbitrary source ingestion, vector indexing expansion, embedding generation expansion, persistent vector store, raw local path exposure, full segment text exposure, raw vector exposure, or full mockup activation.

## Validation

Branch-local validation:

- `python -m pytest .\backend\tests\test_layer3_source_directory_qualitative_analysis.py -q` - `PASS`, `5 passed`.

Additional validation before merge must include:

- JSON manifest load;
- `python -m py_compile` over changed runtime, API, test, and checker files;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- focused Layer 3 API regression as needed; and
- `git diff --check`.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_source_directory_qualitative_analysis_package_preview_runtime`.

After sync, pivot to the next named Layer 3 end-to-end gap unless current-main evidence shows a concrete unresolved package-preview defect or named downstream reader.
