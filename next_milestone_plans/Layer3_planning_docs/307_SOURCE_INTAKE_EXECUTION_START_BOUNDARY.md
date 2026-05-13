# 307 Source Intake Execution Start Boundary

## Status

Status: branch-local implementation with targeted validation passed for `source_intake_execution_start_boundary`.

Implementation branch: `codex/l3-source-intake-exec-start`.

Implementation predecessor: `306_SOURCE_INTAKE_EXECUTION_START_BOUNDARY_FREEZE.md`.

Canonical source of truth: server-owned selected `L3PassRun` shell whose `planned_pass` comes from the approved source-intake `L3AnalysisPlan`, plus the server-owned `L3SourceIntakeRecord` identity preserved by the plan-preview, plan-approval, and execution-selection chain.

Owner service: `backend/app/services/layer3_workbench.py`.

## Implemented Boundary

This slice implements exactly the source-intake execution-start boundary selected by doc 306:

- `analysis_execution_start` recognizes only the frozen source-intake selected pass identity: `source_intake_qualitative_preview`, `qualitative_single_item_operator_uploaded_source`, `operator_uploaded_source_review_preview`, and `299_SOURCE_INTAKE_PLAN_PREVIEW_BOUNDARY_FREEZE`.
- The selected pass run must still belong to the current execution selection and approved preview identity enforced by the existing `analysis_execution_start` path.
- The source-intake record is loaded from server-owned `L3SourceIntakeRecord` state using the preserved `source_intake_record_id`; no execution-start payload field can supply replacement source authority.
- The pass run is completed with deterministic `layer3.source_intake_execution_output.v1` metadata.
- The output preserves `source_intake_record_id`, `candidate_id`, source identity, provenance, storage pointer metadata, and the no-absolute-path exposure invariant.
- `AnalysisRun` remains absent for this source-intake execution-start slice.
- Idempotent replay with the same `client_request_id` returns `already_completed`.

No route, DTO, model, migration, rendered UI, package, handoff, export, connector, provider, RAG/vector, auth/security, local-directory, source-expansion, frontend-only durable authority, broad qualitative execution, or hidden LLM planning behavior is added.

## Proof

Targeted validation run:

```text
pytest .\backend\tests\test_layer3_workbench.py
```

Result: `22 passed`.

The focused test coverage proves:

- `test_execution_start_runs_source_intake_selected_pass_without_analysis_run` covers the source-intake execution-start path.
- Source-intake approved plans still create exactly one selected-not-started `L3PassRun` shell through `execution_selection`.
- Source-intake execution start completes the selected pass run without creating `AnalysisRun`.
- The output payload uses `layer3.source_intake_execution_output.v1` and preserves source-intake identity.
- No `L3OutputPackage` is created.
- Idempotent execution-start replay returns `already_completed`.
- Existing workbench behavior covered by the focused suite remains passing.

## Blocked Scope

The following remain blocked after this implementation:

- execution result/status for source-intake output
- execution result review
- package construction or mutation
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

## Next Boundary

Next required decision: `source_intake_execution_result_status_boundary_freeze` before the source-intake execution output may be inspected through result/status or downstream review/package surfaces.

The next allowed implementation must be selected by a separate freeze. This implementation only lets an already selected source-intake pass run start and complete deterministic execution-start metadata without `AnalysisRun` or downstream artifacts.
