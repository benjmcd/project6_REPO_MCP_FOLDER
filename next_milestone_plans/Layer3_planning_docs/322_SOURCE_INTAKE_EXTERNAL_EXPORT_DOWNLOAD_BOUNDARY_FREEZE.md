# 322 - Source Intake External Export Download Boundary Freeze

Status: planning/control freeze for `source_intake_external_export_download_boundary`.

Branch: `codex/l3-source-intake-export-download-freeze`
Current-main predecessor commit: `77878d000fd04f68192038d1be6ae43531b40f4e`
Predecessor implementation: `321_SOURCE_INTAKE_APS_HANDOFF_DISPATCH_BOUNDARY.md`
Owner service: `backend/app/services/layer3_workbench.py`
Current failure boundary: `source_intake_external_export_download_not_admitted`

## Canonical source of truth

The canonical source of truth for the next implementation is the server-owned source-intake APS handoff dispatch state produced by `aps_handoff_dispatch`, including schema `layer3.source_intake_aps_handoff_dispatch.v1`, persistence mode `durable_source_intake_aps_handoff_dispatch`, the dispatch record state, the APS evidence-bundle handoff package row, the durable handoff/export prepare state from `layer3.source_intake_handoff_export_prepare.v1`, source package refs/hashes, `source_intake_record_id`, `candidate_id`, and the source-intake output payload hash from `layer3.source_intake_execution_output.v1`.

The implementation must preserve the upstream package-review submit authority from `layer3.source_intake_package_review_submit.v1`, package construction authority from `layer3.source_intake_package_construction_commit.v1`, and handoff/export prepare authority from `layer3.source_intake_handoff_export_prepare.v1`.

The live failure boundary is repo-confirmed by the current progress/proof chain: source-intake APS handoff dispatch is admitted, while external export/download remains blocked with `source_intake_external_export_download_not_admitted`.

## Frozen next code-bearing action

The next code-bearing action is `implement_source_intake_external_export_download_boundary` only.

That implementation must reuse the existing external export/download request and delivery contract unless audit proves route reuse is ambiguous. It must require source-intake APS handoff dispatch authority from `layer3.source_intake_aps_handoff_dispatch.v1`, require the supplied dispatch, prepare, package-review submit, package construction, output package ids, package kinds, payload refs, payload hashes, and source identity fields to match durable server-owned state, and then prepare or deliver only the bounded same-origin export/download reference for the already-created APS evidence-bundle handoff package.

The implementation may record exactly one bounded external export/download readiness or delivery state using existing server-owned workbench state if that is required for idempotency and session visibility. It may not create new source packages, mutate existing source package payloads, reconstruct packages, dispatch to connectors, expose provider/public URLs, or use browser/local state as authority.

The implementation must not create `AnalysisRun`, new `L3AnalysisPlan`, new `L3PassRun`, new source rows, new broad source records, rendered UI, model, migration, auth/security behavior, connector or destination dispatch, provider URL behavior, RAG/vector retrieval, generic source upload, local path/directory authority, package mutation/reconstruction, broad qualitative behavior, or full mockup behavior.

## Required future proofs

- `source_intake_aps_handoff_dispatch_can_prepare_external_export_download`
- `source_intake_external_export_download_identity_is_deterministic_and_server_derived`
- `source_intake_identity_preserved_in_external_export_download_state`
- `aps_handoff_dispatch_record_ref_matches_durable_dispatch_state`
- `handoff_export_prepare_record_ref_matches_durable_prepare_state`
- `package_review_submit_record_ref_matches_durable_submit_state`
- `source_package_payload_refs_and_hashes_match_durable_package_state`
- `aps_evidence_bundle_payload_ref_and_hash_match_durable_dispatch_package`
- `no_analysis_run_required_or_created`
- `no_source_package_rows_or_payloads_mutated`
- `duplicate_or_conflicting_external_export_download_requests_fail_closed_or_replay_idempotently`
- `mismatched_dispatch_record_ref_fails_closed`
- `mismatched_prepare_record_ref_fails_closed`
- `mismatched_output_package_ids_or_payload_hashes_fail_closed`
- `connector_destination_dispatch_remains_blocked`
- `provider_public_private_url_remains_blocked`
- `existing_associated_cohort_single_aps_qualitative_aps_and_source_intake_dispatch_unchanged`

## Explicit non-goals

- connector dispatch or destination selection
- provider public/private URL behavior
- public object-store ACL behavior
- rendered external export/download UI controls
- non-APS downstream dispatch
- package mutation, copying, reconstruction, amendment, or supersession
- source package row mutation or source payload rewriting
- generic source upload, local file selection, or local directory ingestion
- source adapter registry or source-family expansion
- RAG/vector retrieval or hybrid qualitative analysis
- backend route changes unless route reuse is proven ambiguous
- model or migration changes
- auth/security behavior changes
- broad qualitative execution
- full mockup activation

## Stop condition for this freeze

This freeze is complete when the planning doc, progress board, progress manifest, proof manifest, and `tools/l3-progress-check.py` all agree that `source_intake_external_export_download_boundary` is selected as the next exact runtime boundary and that no runtime behavior is admitted by this branch.
