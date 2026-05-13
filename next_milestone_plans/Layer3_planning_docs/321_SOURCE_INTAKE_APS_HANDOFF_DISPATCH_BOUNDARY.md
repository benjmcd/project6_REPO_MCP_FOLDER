# 321 - Source Intake APS Handoff Dispatch Boundary

Status: branch-local implementation for `source_intake_aps_handoff_dispatch_boundary`.

Branch: `codex/l3-source-intake-aps-dispatch`
Predecessor freeze: `320_SOURCE_INTAKE_APS_HANDOFF_DISPATCH_BOUNDARY_FREEZE.md`
Owner service: `backend/app/services/layer3_workbench.py`
Targeted test: `backend/tests/test_layer3_workbench.py`

## Canonical source of truth

The canonical source is the server-owned source-intake handoff/export prepare state from `layer3.source_intake_handoff_export_prepare.v1`, plus its upstream source-intake package-review submit, package-construction commit, source package refs/hashes, `source_intake_record_id`, `candidate_id`, and `layer3.source_intake_execution_output.v1` output hash.

No new route, rendered UI, model, migration, auth/security, connector, provider, RAG/vector, broad source-upload, local path/directory, external export/download delivery, package mutation/reconstruction, or broad qualitative authority is introduced by this boundary.

## Implemented runtime behavior

`aps_handoff_dispatch` now admits source-intake authority only when `_source_intake_result_review_source_admitted` proves the exact source-intake result/status output and recorded handoff/export prepare state proves `layer3.source_intake_handoff_export_prepare.v1` authority. The request still uses the existing APS handoff dispatch contract and must provide matching package-review submit ref/state, prepare ref, internal envelope ref, output package ids, package kinds, payload refs, and payload hashes.

The successful response uses schema `layer3.source_intake_aps_handoff_dispatch.v1`, records `analysis_run_id: null`, preserves `source_intake_record_id`, `candidate_id`, `output_payload_ref`, `output_payload_hash`, source package refs/hashes, and records bounded APS evidence-bundle handoff dispatch state with persistence mode `durable_source_intake_aps_handoff_dispatch`.

External export/download, connector/destination dispatch, provider URL behavior, package mutation/reconstruction, source expansion, rendered UI, model/migration, auth/security, and broad qualitative/RAG/vector behavior remain blocked. The next boundary is `source_intake_external_export_download_boundary_freeze` only if source-intake export/download remains desired after APS dispatch proof.

## Proof obligations covered

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
- `external_export_download_remains_blocked`
- `connector_destination_dispatch_remains_blocked`

## Targeted validation

Targeted validation for this branch is `pytest .\backend\tests\test_layer3_workbench.py` plus `python .\tools\l3-progress-check.py` and `git diff --check`.

Expected test coverage is through `test_execution_start_runs_source_intake_selected_pass_without_analysis_run`, including source-intake APS dispatch authorization, idempotent replay, prepare-ref mismatch rejection, unchanged no-`AnalysisRun` behavior, exactly one APS handoff output package, and no mutation of the three source package refs/hashes.

## Explicitly deferred

- external export/download readiness or delivery
- connector dispatch or destination selection
- provider public/private URL behavior
- rendered APS dispatch UI controls
- package mutation, copying, reconstruction, amendment, or supersession
- generic source upload or local path/directory authority
- RAG/vector retrieval or hybrid qualitative analysis
- backend route changes
- model or migration changes
- auth/security behavior changes
- broad qualitative execution
- full mockup activation
