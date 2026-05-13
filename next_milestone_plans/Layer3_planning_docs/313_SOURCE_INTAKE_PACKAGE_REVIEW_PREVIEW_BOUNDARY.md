# 313 Source Intake Package Review Preview Boundary

## Status

Status: current-main implementation/proof for `source_intake_package_review_preview_boundary`.

Branch: `codex/l3-source-intake-package-review-preview`.

Implementation commit: `6f69f9fba57c805b7b10c9492749302f43f014cc`.

Merged PR: `#905`.

Merge commit/current-main authority: `bf6539c85212f7f0b4d3e08d9b8c4c6344dec5ab`.

GitHub checks: `backend-layer3-api` success and `test` success.

Review threads: empty; no comments or reviews required action.

Freeze predecessor: `312_SOURCE_INTAKE_PACKAGE_REVIEW_PREVIEW_BOUNDARY_FREEZE.md`.

Runtime predecessor: `source_intake_execution_result_review_boundary`.

Selected runtime family: `source_breadth_runtime`.

Selected runtime mode: `source_intake_package_review_preview_boundary`.

Named operator/product use case: `operator_uploaded_single_source_previews_package_readiness_after_result_review`.

Canonical source of truth: server-owned completed `L3PassRun`, deterministic `layer3.source_intake_execution_output.v1` payload, admitted `execution_result_status` response, approved `execution_result_review` state, and deterministic source-intake package-review preview identity.

Owner service: `backend/app/services/layer3_workbench.py`.

Targeted proof: `backend/tests/test_layer3_workbench.py`.

## Implemented Boundary

`package_review_preview` now admits the frozen source-intake result-review authority as a read-only package-review preview readiness response.

The admitted source-intake package-review preview case requires:

- existing `package_review_preview` request contract
- available source-intake `execution_result_status`
- approved source-intake `execution_result_review` state
- no `AnalysisRun`
- pass type `single_item`
- pass scope `qualitative_single_item_operator_uploaded_source`
- selected method `operator_uploaded_source_review_preview`
- engine family `source_intake_qualitative_preview`
- source gate `306_SOURCE_INTAKE_EXECUTION_START_BOUNDARY_FREEZE`
- output metadata schema `layer3.source_intake_execution_output.v1`
- preserved `source_intake_record_id`, `candidate_id`, output hash, preview id, and preview hash
- no unresolved trace references
- no existing package or reconciliation rows for the session
- storage pointer with `absolute_path_exposed = false`

The response uses `layer3.source_intake_package_review_preview.v1` and deterministic `layer3.source_intake_package_review_preview_hash.v1` identity while keeping package construction and every later downstream surface disabled.

## Downstream Guard

This implementation keeps later source-intake surfaces blocked by preserving existing source-intake downstream guards in:

- `package_construction_commit` with `source_intake_package_construction_commit_not_admitted`
- `package_review_submit` with `source_intake_package_review_submit_not_admitted`
- `handoff_export_prepare` with `source_intake_handoff_export_prepare_not_admitted`
- `aps_handoff_dispatch` with `source_intake_aps_handoff_dispatch_not_admitted`
- `external_export_download_prepare` with `source_intake_external_export_download_prepare_not_admitted`

The source-intake package-preview response reports `package_commit_enabled = false`, `package_review_submit_enabled = false`, and downstream unavailable state including `package_construction`.

## Proof

Focused test coverage in `test_execution_start_runs_source_intake_selected_pass_without_analysis_run` proves:

- source-intake approved result review can produce source-intake package-review preview readiness
- package-review preview schema is `layer3.source_intake_package_review_preview.v1`
- preview response preserves `source_intake_record_id`
- preview response preserves `candidate_id`
- preview response preserves output hash authority
- package construction remains blocked with `source_intake_package_construction_commit_not_admitted`
- source-intake `AnalysisRun` references fail closed before package preview
- no `AnalysisRun` is created
- no `L3OutputPackage` is created
- no `L3ReconciliationRecord` is created

Targeted validation: `pytest .\backend\tests\test_layer3_workbench.py` passed with 22 tests.

Current-main validation: PR `#905` merged at `bf6539c85212f7f0b4d3e08d9b8c4c6344dec5ab` with `backend-layer3-api` and `test` checks successful, no comments/reviews/reviewThreads requiring action, and `python .\tools\l3-progress-check.py` passing after fast-forwarding local `main`.

## Explicit Non-Goals

This boundary does not admit:

- package construction or mutation
- package review submit or commit
- handoff/export prepare or dispatch
- APS handoff dispatch
- external export/download prepare or delivery
- connector/destination dispatch
- provider/private signed URL prepare
- web connector retrieval
- RAG/vector indexing
- generic source upload
- broad file upload
- local path or local directory authority
- model or migration changes
- new backend route
- rendered UI changes
- auth/security behavior
- non-text binary preview
- frontend-only durable authority
- broad qualitative execution
- hidden LLM planning

## Next Required Decision

The next decision is whether source-intake may progress from read-only package-review preview into `source_intake_package_construction_commit_boundary_freeze`.

No package construction, package review submit, handoff/export, connector, provider, RAG/vector, source expansion, route, UI, model, migration, auth/security, or broad qualitative execution work is admitted without a separate freeze.
