# 315 - Source Intake Package Construction Commit Boundary

Status: branch-local implementation for `source_intake_package_construction_commit_boundary`.

Branch: `codex/l3-source-intake-package-construction`
Predecessor freeze: `314_SOURCE_INTAKE_PACKAGE_CONSTRUCTION_COMMIT_BOUNDARY_FREEZE.md`
Owner service: `backend/app/services/layer3_workbench.py`
Targeted test: `backend/tests/test_layer3_workbench.py`

## Canonical source of truth

The canonical source is the server-owned completed `L3PassRun` source-intake execution output, the approved source-intake result-review state, the server-recomputed `layer3.source_intake_package_review_preview.v1` identity, and the durable package/reconciliation state written through the existing `materialize_workbench_package_commit` owner path.

No UI, route, model, migration, auth/security, connector, provider, RAG/vector, broad source-upload, or broad qualitative authority is introduced by this boundary.

## Implemented runtime behavior

`package_construction_commit` now admits only the exact source-intake authority proven by `_source_intake_result_review_source_admitted`. The admitted request must still use the existing package-construction request contract and reference the current server-recomputed source-intake package-review preview hash.

The successful response uses schema `layer3.source_intake_package_construction_commit.v1`, records `analysis_run_id: null`, preserves `source_intake_record_id`, `candidate_id`, `output_payload_hash`, package payload refs, package payload hashes, and the source-intake package construction source gate `314_SOURCE_INTAKE_PACKAGE_CONSTRUCTION_COMMIT_BOUNDARY_FREEZE`.

The persistence mode is `durable_source_intake_package_construction`. Package review submit remains blocked by `source_intake_package_review_submit_not_admitted`, and the next boundary is `source_intake_package_review_submit_boundary_freeze`.

## Proof obligations covered

- `source_intake_package_review_preview_can_commit_package_construction`
- `package_construction_identity_is_deterministic_and_server_derived`
- `source_intake_identity_preserved_in_package_and_reconciliation_state`
- `package_payload_refs_and_hashes_are_server_derived`
- `no_analysis_run_required_or_created`
- `duplicate_or_conflicting_construction_requests_fail_closed_or_replay_idempotently`
- `mismatched_package_review_preview_hash_fails_closed`
- `source_intake_analysis_run_reference_fails_closed`
- `package_review_submit_remains_blocked`
- `handoff_export_remains_blocked`
- `aps_handoff_dispatch_remains_blocked`
- `external_export_download_remains_blocked`

## Targeted validation

Targeted validation for this branch is `pytest .\backend\tests\test_layer3_workbench.py` plus `python .\tools\l3-progress-check.py` and `git diff --check`.

Expected test coverage is through `test_execution_start_runs_source_intake_selected_pass_without_analysis_run`, including source-intake package construction commit, idempotent replay, mismatched package-preview hash rejection, source-intake package-review submit block, and unchanged no-`AnalysisRun` fail-closed behavior.

## Explicitly deferred

- package-review submit approval
- handoff/export prepare or dispatch
- APS handoff dispatch
- external export/download readiness or delivery
- connector destination dispatch
- provider public/private URL behavior
- RAG/vector retrieval or hybrid qualitative analysis
- generic source upload or local path/directory authority
- rendered UI changes
- model or migration changes
- auth/security behavior changes
- broad qualitative execution
