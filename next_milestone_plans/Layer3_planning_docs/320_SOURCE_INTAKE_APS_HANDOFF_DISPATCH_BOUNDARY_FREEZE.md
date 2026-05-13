# 320 - Source Intake APS Handoff Dispatch Boundary Freeze

Status: planning/control freeze for `source_intake_aps_handoff_dispatch_boundary`.

Branch: `codex/l3-source-intake-aps-dispatch-freeze`
Current-main predecessor commit: `d80b68687a293232945cd6cded51ab6b675e5b7f`
Predecessor implementation: `319_SOURCE_INTAKE_HANDOFF_EXPORT_PREPARE_BOUNDARY.md`
Owner service: `backend/app/services/layer3_workbench.py`
Current failure boundary: `source_intake_aps_handoff_dispatch_not_admitted`

## Canonical source of truth

The canonical source of truth for the next implementation is the server-owned source-intake handoff/export prepare state produced by `handoff_export_prepare`, including schema `layer3.source_intake_handoff_export_prepare.v1`, the prepared internal export-envelope ref, the prepare record ref, the durable `L3ReconciliationRecord`, the three source package `L3OutputPackage` rows, package payload refs/hashes, `source_intake_record_id`, `candidate_id`, and source-intake output payload hash.

The implementation must also preserve the upstream package-review submit authority from `layer3.source_intake_package_review_submit.v1`, package construction authority from `layer3.source_intake_package_construction_commit.v1`, and output authority from `layer3.source_intake_execution_output.v1`.

The live failure boundary is repo-confirmed in `backend/app/services/layer3_workbench.py`: `aps_handoff_dispatch` still calls `_raise_if_source_intake_downstream_not_admitted` and returns `source_intake_aps_handoff_dispatch_not_admitted` for source-intake result/status authority after the existing APS handoff dispatch request contract checks pass.

## Frozen next code-bearing action

The next code-bearing action is `implement_source_intake_aps_handoff_dispatch_boundary` only.

That implementation must reuse the existing `aps_handoff_dispatch` request contract unless audit proves a source-intake-specific route is required to avoid ambiguity. It must require source-intake handoff/export prepare authority from `layer3.source_intake_handoff_export_prepare.v1`, require the supplied reconciliation record, package-review submit ref/state, prepare ref, handoff/export state, internal envelope ref, output package ids, package kinds, payload refs, and payload hashes to match durable server-owned state, and then dispatch only one server-side APS evidence-bundle handoff.

The implementation may materialize exactly one APS-facing `L3OutputPackage` row of kind `aps_evidence_bundle_handoff` only through the existing APS evidence-bundle owner-service contract. It may record exactly one APS handoff dispatch summary in existing JSON-bearing workbench state if needed for idempotency and session/reconciliation visibility.

The implementation must not create `AnalysisRun`, new `L3AnalysisPlan`, new `L3PassRun`, new `L3ReconciliationRecord`, source package rows, source rows, new route unless required by the audit, rendered UI, model, migration, auth/security behavior, connector or destination dispatch, provider URL, external export/download readiness or delivery, RAG/vector retrieval, generic source upload, local path/directory authority, package mutation/reconstruction, broad qualitative behavior, or full mockup behavior.

## Required future proofs

- `source_intake_handoff_export_prepare_can_dispatch_aps_evidence_bundle`
- `source_intake_aps_dispatch_identity_is_deterministic_and_server_derived`
- `source_intake_identity_preserved_in_aps_handoff_dispatch_state`
- `prepare_record_ref_matches_durable_handoff_export_prepare_state`
- `handoff_export_envelope_ref_matches_durable_prepare_state`
- `package_review_submit_record_ref_matches_durable_submit_state`
- `package_payload_refs_and_hashes_match_durable_package_state`
- `no_analysis_run_required_or_created`
- `exactly_one_aps_handoff_package_row_created_on_success`
- `no_source_package_rows_or_payloads_mutated`
- `duplicate_or_conflicting_aps_dispatch_requests_fail_closed_or_replay_idempotently`
- `mismatched_prepare_record_ref_fails_closed`
- `mismatched_handoff_export_state_fails_closed`
- `mismatched_handoff_export_envelope_ref_fails_closed`
- `mismatched_package_review_submit_record_ref_fails_closed`
- `mismatched_output_package_ids_or_payload_hashes_fail_closed`
- `external_export_download_remains_blocked`
- `connector_destination_dispatch_remains_blocked`
- `existing_associated_cohort_single_aps_and_qualitative_aps_dispatch_unchanged`

## Explicit non-goals

- external export/download readiness or delivery
- rendered APS dispatch UI controls
- connector dispatch or destination selection
- provider public/private URL behavior
- non-APS downstream dispatch
- package mutation, copying, reconstruction, amendment, or supersession
- generic source upload, local file selection, or local directory ingestion
- source adapter registry or source-family expansion
- RAG/vector retrieval or hybrid qualitative analysis
- backend route changes unless route reuse is proven ambiguous
- model or migration changes
- auth/security behavior changes
- broad qualitative execution
- full mockup activation

## Stop condition for this freeze

This freeze is complete when the planning doc, progress board, progress manifest, proof manifest, and `tools/l3-progress-check.py` all agree that `source_intake_aps_handoff_dispatch_boundary` is selected as the next exact runtime boundary and that no runtime behavior is admitted by this branch.
