# 808 Source Directory Qualitative Analysis Handoff Export Prepare Runtime Entry Freeze

Status: branch-local implementation-entry freeze and runtime proof for `source_directory_qualitative_analysis_handoff_export_prepare_runtime`.

Doc: `808_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_HANDOFF_EXPORT_PREPARE_RUNTIME_ENTRY_FREEZE.md`

## Current Authority

- Runtime branch: `codex/l3-source-handoff-export-prepare`
- Current-main preflight checkpoint: `15e276104367627f0f886cb00a22c10dffd9492e`
- Predecessor current-main sync doc: `807_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_CURRENT_MAIN_SYNC.md`
- Selected from posture: `select_next_named_layer3_end_to_end_gap_after_source_directory_package_review_submit_sync`
- Selected implementation action: `implement_source_directory_qualitative_analysis_handoff_export_prepare_after_package_review_submit_sync`
- Runtime status after implementation: `source_directory_qualitative_analysis_handoff_export_prepare_runtime_implemented_branch_local`

## Admitted Runtime

This slice admits only bounded handoff/export prepare authority for an already approved `server_configured_operator_directory_text_table_source_family` qualitative-analysis package-review submit state.

The runtime route is:

`POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/prepare`

The request must reference the current server-recomputed qualitative-analysis hash, the current source-directory package-review preview hash, the persisted construction basis hash, one reconciliation record, exactly three output package ids, exactly three package kinds, exactly three payload hashes, the approved `package_review_submit_record_ref`, `package_review_state: package_review_approved`, `handoff_target: internal_export_envelope`, `export_mode: prepare_only`, and one operator decision from `authorize_prepare`, `hold`, `decline`, or `blocked`.

The response schema is `layer3.source_directory_qualitative_analysis_handoff_export_prepare.v1`.

The runtime mode is `source_directory_qualitative_analysis_handoff_export_prepare_authority`.

The handoff/export prepare source gate is `808_SOURCE_DIRECTORY_QUALITATIVE_ANALYSIS_HANDOFF_EXPORT_PREPARE_RUNTIME_ENTRY_FREEZE`.

The durable prepare state uses `layer3.handoff_export_prepare_state.v1`, records `state` and `handoff_export_state`, records `prepare_record_ref`, writes the state into the existing reconciliation/session JSON state, and keeps payload refs redacted.

The internal envelope uses `layer3.source_directory_internal_export_envelope.v1` and remains prepare-only; it carries package ids, package kinds, payload hashes, redaction metadata, and an internal envelope ref without exposing local paths or payload refs.

## Implemented Owners

- `backend/app/services/layer3_source_directory_qualitative_analysis.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_source_directory_qualitative_analysis.py`

## Proof

Focused proof command:

`python -m pytest backend/tests/test_layer3_source_directory_qualitative_analysis.py -q`

Focused proof result:

`11 passed`

Focused proof coverage:

- `test_source_directory_qualitative_analysis_handoff_export_prepare_records_bounded_authority`
- `test_source_directory_qualitative_analysis_handoff_export_prepare_requires_approved_submit`
- prepare requires stored `package_review_approved` submit state
- prepare records `handoff_export_prepared`
- replay returns `already_prepared`
- stored submit authority basis is used for qualitative-analysis hash validation
- no `L3PassRun`, `AnalysisRun`, `ConnectorRun`, or `ConnectorRunTarget` rows are written
- package rows remain the existing constructed `canonical_internal`, `user_facing`, and `review_facing` rows
- API response and envelope keep `payload_refs_redacted: True`

## Non-Admissions

This runtime does not admit APS handoff dispatch, external export/download delivery, provider-public delivery/use, provider-private signed URL behavior, connector/destination dispatch, real connector invocation, credentials, network egress, auth/security broadening, frontend-durable authority, frontend-rendered controls, prompt/model/provider runtime, qualitative generation runtime, new source family, arbitrary source ingestion, vector indexing expansion, embedding generation expansion, persistent vector store, raw local path exposure, full segment text exposure, raw vector exposure, package payload rewrite, package mutation/reconstruction, source package row mutation, replacement package row creation, or full mockup activation.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_source_directory_qualitative_analysis_handoff_export_prepare_runtime`.

After sync, pivot to `select_next_named_layer3_end_to_end_gap_after_source_directory_handoff_export_prepare_sync` unless current-main evidence shows a concrete unresolved handoff/export prepare defect or named downstream reader.
