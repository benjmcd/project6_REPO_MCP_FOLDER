# 306 Source Intake Execution Start Boundary Freeze

## Status

Status: planning/control freeze for `source_intake_execution_start_boundary`.

Branch: `codex/l3-source-intake-exec-start-freeze`.

Runtime predecessor: `source_intake_execution_selection_boundary`.

Selected runtime family: `source_breadth_runtime`.

Selected runtime mode: `source_intake_execution_start_boundary`.

Named operator/product use case: `operator_uploaded_single_source_starts_selected_source_intake_pass`.

Canonical source of truth: server-owned selected `L3PassRun` shell whose `planned_pass` comes from the approved source-intake `L3AnalysisPlan`, plus the server-owned `L3SourceIntakeRecord` identity preserved by the plan-preview, plan-approval, and execution-selection chain.

Implementation predecessor: `305_SOURCE_INTAKE_EXECUTION_SELECTION_BOUNDARY.md`.

Current-main predecessor commit: `b33c11269597df0e30f1ff4b79fbd03929a1e493`.

## Repo-Confirmed Failure Boundary

`backend/app/services/layer3_workbench.py` currently admits analysis execution start only for wrapped quantitative pass runs or the frozen single APS-document qualitative pass.

For a source-intake selected pass run, the current `analysis_execution_start` path rejects before execution with `unsupported_analysis_execution_engine`.

The existing execution-start path already validates:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- forbidden request fields
- current approved-plan identity
- approved preview identity
- prior execution-selection state
- selected pass-run membership
- idempotent existing-start state
- `selected_not_started` pass-run state

The missing boundary is therefore not route creation, broad execution orchestration, package construction, connector dispatch, provider URL work, source expansion, model/migration work, or rendered UI work. The missing boundary is the narrow owner-service rule and deterministic output contract that may allow exactly the source-intake selected pass-run shell to start.

## Future Execution-Start Semantics

The next implementation may allow `analysis_execution_start` to start exactly one selected source-intake pass run when all of the following are true:

- The request uses the existing `analysis_execution_start` request contract; no route fields are added.
- The selected `L3PassRun` belongs to the current execution selection for the same `session_id`, `analysis_plan_id`, `preview_id`, and `preview_hash`.
- The pass run has status `selected_not_started`.
- The pass run has no `analysis_run_id`.
- The pass run has no `output_payload_ref`.
- The preserved `planned_pass` has `engine_family` equal to `source_intake_qualitative_preview`.
- The preserved `planned_pass` has `pass_scope` equal to `qualitative_single_item_operator_uploaded_source`.
- The preserved `planned_pass` has `selected_method_name` equal to `operator_uploaded_source_review_preview`.
- The preserved `planned_pass` carries `source_intake_record_id` and `candidate_id`.
- The source-intake record identity is resolved from server-owned source-intake state, not client-supplied execution-start payload fields.

Required future behavior:

- Mark the selected source-intake pass run as execution-started through the same server-owned execution state model used by existing selected-pass execution.
- Produce only deterministic source-intake review output metadata derived from the selected pass-run summary and server-owned source-intake record identity.
- Preserve `source_preview_id`, `source_preview_hash`, `source_intake_record_id`, `candidate_id`, `pass_scope`, `source_gate`, `engine_family`, and `selected_method_name` in the execution-start response/state.
- Keep `AnalysisRun` absent for this source-intake execution-start slice unless a later freeze proves an actual analysis-run authority model for operator-uploaded source review.
- Keep package, handoff, export, connector, provider, RAG/vector, source-expansion, UI, model, migration, and auth/security behavior blocked.
- Keep result/status, result-review, package-review, package-construction, handoff/export, and external-export transitions blocked unless later freezes admit them.

## Required Future Proof

The next implementation must prove:

- A source-intake selected pass run can start through `analysis_execution_start`.
- The started pass run was selected by `execution_selection` and still matches the current approved plan and preview identity.
- Source-intake execution start preserves source-intake planned-pass identity.
- Source-intake execution start creates no `AnalysisRun`.
- Source-intake execution start creates no package, handoff, export, connector, provider, RAG/vector, route, UI, model, or migration behavior.
- Preview id/hash mismatch still fails closed.
- Missing or conflicting `client_request_id` behavior remains fail-closed/idempotent.
- Non-source-intake unsupported engines still fail closed.
- Existing wrapped quantitative and single APS-document qualitative execution-start behavior remains unchanged.

## Blocked Scope

This freeze does not admit:

- package construction or mutation
- result review
- handoff/export prepare or dispatch
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

## Next Allowed Action

Next allowed code-bearing action: `implement_source_intake_execution_start_boundary` only.

That implementation must stay in `backend/app/services/layer3_workbench.py` and focused workbench execution-start tests unless live repo evidence proves a narrower supporting source-intake execution contract file is already the canonical seam. Any result-review, package, connector, provider, RAG/vector, source expansion, route, UI, model, migration, auth/security, or broad qualitative execution work requires a separate freeze.
