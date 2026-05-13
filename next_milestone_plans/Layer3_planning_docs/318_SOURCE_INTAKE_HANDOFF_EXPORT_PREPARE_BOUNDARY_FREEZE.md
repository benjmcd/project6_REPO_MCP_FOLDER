# 318 - Source Intake Handoff Export Prepare Boundary Freeze

Status: planning/control freeze for `source_intake_handoff_export_prepare_boundary`.

Branch: `codex/l3-source-intake-handoff-export-freeze`
Current-main predecessor commit: `bf46340d200d8807aae3279dcf597d23298c0641`
Predecessor implementation: `317_SOURCE_INTAKE_PACKAGE_REVIEW_SUBMIT_BOUNDARY.md`
Owner service: `backend/app/services/layer3_workbench.py`
Current failure boundary: `source_intake_handoff_export_prepare_not_admitted`

## Canonical source of truth

The canonical source of truth for the next implementation is the server-owned source-intake package-review submit state produced by `package_review_submit`, including `layer3.source_intake_package_review_submit.v1`, the durable `L3ReconciliationRecord`, the three `L3OutputPackage` rows, package payload refs/hashes, `source_intake_record_id`, `candidate_id`, and source-intake output payload hash.

The live failure boundary is repo-confirmed in `backend/app/services/layer3_workbench.py`: `handoff_export_prepare` still calls `_raise_if_source_intake_downstream_not_admitted` and returns `source_intake_handoff_export_prepare_not_admitted` for source-intake status authority after the existing handoff/export request contract checks pass.

## Frozen next code-bearing action

The next code-bearing action is `implement_source_intake_handoff_export_prepare_boundary` only.

That implementation must reuse the existing `handoff_export_prepare` request contract. It must require source-intake package-review submit authority from `layer3.source_intake_package_review_submit.v1`, require package construction authority from `layer3.source_intake_package_construction_commit.v1`, require the supplied reconciliation record, submit record ref, package-review state, output package ids, payload refs, and payload hashes to match durable server-owned state, and produce only bounded source-intake internal export-envelope preparation state.

The implementation must not create `AnalysisRun`, new route, rendered UI, model, migration, auth/security, connector, provider URL, RAG/vector, generic source upload, local path/directory, APS dispatch, external export/download delivery, or broad qualitative behavior.

## Required future proofs

- `source_intake_package_review_submit_can_prepare_internal_export_envelope`
- `source_intake_handoff_export_prepare_identity_is_deterministic_and_server_derived`
- `source_intake_identity_preserved_in_handoff_export_prepare_state`
- `package_payload_refs_and_hashes_match_durable_package_state`
- `package_review_submit_record_ref_matches_durable_submit_state`
- `no_analysis_run_required_or_created`
- `duplicate_or_conflicting_handoff_export_prepare_requests_fail_closed_or_replay_idempotently`
- `mismatched_package_review_submit_record_ref_fails_closed`
- `mismatched_package_review_state_fails_closed`
- `mismatched_package_review_submit_schema_id_fails_closed`
- `mismatched_output_package_ids_or_payload_hashes_fail_closed`
- `aps_handoff_dispatch_remains_blocked`
- `external_export_download_remains_blocked`
- `existing_associated_cohort_and_single_aps_handoff_export_prepare_unchanged`

## Explicit non-goals

- APS handoff dispatch
- external export/download readiness or delivery
- connector destination dispatch
- provider public/private URL behavior
- RAG/vector retrieval or hybrid qualitative analysis
- generic source upload or local path/directory authority
- rendered UI changes
- backend route changes
- model or migration changes
- auth/security behavior changes
- broad qualitative execution

## Stop condition for this freeze

This freeze is complete when the planning doc, progress board, progress manifest, proof manifest, and `tools/l3-progress-check.py` all agree that `source_intake_handoff_export_prepare_boundary` is selected as the next exact runtime boundary and that no runtime behavior is admitted by this branch.
