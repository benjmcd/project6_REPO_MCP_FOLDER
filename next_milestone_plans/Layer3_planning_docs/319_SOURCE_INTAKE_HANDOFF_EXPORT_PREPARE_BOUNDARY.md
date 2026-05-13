# 319 - Source Intake Handoff Export Prepare Boundary

Status: branch-local implementation for `source_intake_handoff_export_prepare_boundary`.

Branch: `codex/l3-source-intake-handoff-export`
Predecessor freeze: `318_SOURCE_INTAKE_HANDOFF_EXPORT_PREPARE_BOUNDARY_FREEZE.md`
Owner service: `backend/app/services/layer3_workbench.py`
Targeted test: `backend/tests/test_layer3_workbench.py`

## Canonical source of truth

The canonical source is the server-owned source-intake package-review submit state, the durable `L3ReconciliationRecord`, the three `L3OutputPackage` rows, package payload refs/hashes, `source_intake_record_id`, `candidate_id`, and the underlying `layer3.source_intake_execution_output.v1` output hash.

No new route, rendered UI, model, migration, auth/security, connector, provider, RAG/vector, broad source-upload, local path/directory, APS dispatch, external export/download delivery, or broad qualitative authority is introduced by this boundary.

## Implemented runtime behavior

`handoff_export_prepare` now admits only the exact source-intake authority proven by `_source_intake_result_review_source_admitted` plus the durable source-intake package-review submit and package construction source gates. The admitted request still uses the existing handoff/export prepare request contract and must provide matching `construction_basis_hash`, reconciliation record id, package-review submit record ref, package-review submit schema id, output package ids, payload refs, and payload hashes.

The successful response uses schema `layer3.source_intake_handoff_export_prepare.v1`, records `analysis_run_id: null`, preserves `source_intake_record_id`, `candidate_id`, `output_payload_ref`, `output_payload_hash`, package payload refs, and package payload hashes, and records bounded internal export-envelope prepare state with persistence mode `durable_source_intake_handoff_export_prepare`.

APS handoff dispatch remains blocked by `source_intake_aps_handoff_dispatch_not_admitted`, and the next boundary is `source_intake_aps_handoff_dispatch_boundary_freeze`.

## Proof obligations covered

- `source_intake_package_review_submit_can_prepare_internal_export_envelope`
- `source_intake_handoff_export_prepare_identity_is_deterministic_and_server_derived`
- `source_intake_identity_preserved_in_handoff_export_prepare_state`
- `package_payload_refs_and_hashes_match_durable_package_state`
- `package_review_submit_record_ref_matches_durable_submit_state`
- `no_analysis_run_required_or_created`
- `duplicate_or_conflicting_handoff_export_prepare_requests_fail_closed_or_replay_idempotently`
- `mismatched_construction_basis_hash_fails_closed`
- `mismatched_package_review_submit_record_ref_fails_closed`
- `mismatched_package_review_state_fails_closed`
- `mismatched_package_review_submit_schema_id_fails_closed`
- `mismatched_output_package_ids_or_payload_hashes_fail_closed`
- `aps_handoff_dispatch_remains_blocked`

## Targeted validation

Targeted validation for this branch is `pytest .\backend\tests\test_layer3_workbench.py` plus `python .\tools\l3-progress-check.py` and `git diff --check`.

Expected test coverage is through `test_execution_start_runs_source_intake_selected_pass_without_analysis_run`, including source-intake handoff/export prepare authorization, idempotent replay, construction-basis mismatch rejection, and unchanged no-`AnalysisRun` fail-closed behavior.

## Explicitly deferred

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
