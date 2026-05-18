# 806 Source Directory Qualitative Analysis Package Review Submit Runtime Entry Freeze

Status: branch-local implementation-entry freeze and runtime proof for `source_directory_qualitative_analysis_package_review_submit_runtime`.

Doc: `806_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_ENTRY_FREEZE.md`

## Current Authority

- Runtime branch: `codex/l3-source-package-review-submit`
- Current-main preflight checkpoint: `4f4c6229f456a2c8482b7e94e595bac5db5bc079`
- Predecessor current-main sync doc: `805_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_CONSTRUCTION_RUNTIME_CURRENT_MAIN_SYNC.md`
- Selected from posture: `select_next_named_layer3_end_to_end_gap_after_source_directory_package_construction_commit_sync`
- Selected implementation action: `implement_source_directory_qualitative_analysis_package_review_submit_after_package_construction_commit_sync`
- Runtime status after implementation: `source_directory_qualitative_analysis_package_review_submit_runtime_implemented_branch_local`

## Admitted Runtime

This slice admits only bounded package-review submit authority for the already constructed `server_configured_operator_directory_text_table_source_family` qualitative-analysis package set.

The runtime route is:

`POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/review/submit`

The request must reference the current server-recomputed qualitative-analysis hash, the current source-directory package-review preview hash, the persisted construction basis hash, one reconciliation record, exactly three output package ids, exactly three package kinds, exactly three payload hashes, and one operator decision from `approved`, `changes_requested`, `rejected`, or `blocked`.

The response schema is `layer3.source_directory_qualitative_analysis_package_review_submit.v1`.

The runtime mode is `source_directory_qualitative_analysis_package_review_submit_authority`.

The package-review submit source gate is `806_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_ENTRY_FREEZE`.

The durable review state uses `layer3.package_review_submit_state.v1`, records `state` and `package_review_state`, records `submit_record_ref`, writes the state into the existing reconciliation/session JSON state, and keeps payload refs redacted.

## Implemented Owners

- `backend/app/services/layer3_source_directory_qualitative_analysis.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_source_directory_qualitative_analysis.py`

## Proof

Focused proof command:

`python -m pytest backend/tests/test_layer3_source_directory_qualitative_analysis.py -q`

Focused proof result:

`9 passed`

Focused proof coverage:

- `test_source_directory_qualitative_analysis_package_review_submit_records_bounded_authority`
- `test_source_directory_qualitative_analysis_package_review_submit_rejects_stale_construction`
- submit records `package_review_approved`
- replay returns `already_submitted`
- stale `construction_basis_hash` is rejected with `source_directory_package_review_submit_construction_mismatch`
- no `L3PassRun`, `AnalysisRun`, `ConnectorRun`, or `ConnectorRunTarget` rows are written
- package rows remain the existing constructed `canonical_internal`, `user_facing`, and `review_facing` rows
- API response keeps `payload_refs_redacted: True`

## Non-Admissions

This runtime does not admit handoff/export rerun, external export/download delivery, provider-public delivery/use, provider-private signed URL behavior, connector/destination dispatch, real connector invocation, credentials, network egress, auth/security broadening, frontend-durable authority, frontend-rendered controls, prompt/model/provider runtime, qualitative generation runtime, new source family, arbitrary source ingestion, vector indexing expansion, embedding generation expansion, persistent vector store, raw local path exposure, full segment text exposure, raw vector exposure, package payload rewrite, package mutation/reconstruction, source package row mutation, replacement package row creation, or full mockup activation.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_source_directory_qualitative_analysis_package_review_submit_runtime`.

After sync, pivot to `select_next_named_layer3_end_to_end_gap_after_source_directory_package_review_submit_sync` unless current-main evidence shows a concrete unresolved package-review submit defect or named downstream reader.
