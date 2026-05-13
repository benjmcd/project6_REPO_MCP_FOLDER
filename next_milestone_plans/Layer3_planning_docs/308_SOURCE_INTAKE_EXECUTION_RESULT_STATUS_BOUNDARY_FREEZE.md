# 308 Source Intake Execution Result Status Boundary Freeze

## Status

Status: planning/control freeze for `source_intake_execution_result_status_boundary`.

Branch: `codex/l3-source-intake-result-status-freeze`.

Runtime predecessor: `source_intake_execution_start_boundary`.

Selected runtime family: `source_breadth_runtime`.

Selected runtime mode: `source_intake_execution_result_status_boundary`.

Named operator/product use case: `operator_uploaded_single_source_inspects_completed_source_intake_execution_status`.

Canonical source of truth: server-owned completed `L3PassRun` whose `summary_json.analysis_execution_start` and `output_payload_ref` were produced by `source_intake_execution_start_boundary`, plus the deterministic `layer3.source_intake_execution_output.v1` payload and preserved `L3SourceIntakeRecord` identity.

Implementation predecessor: `307_SOURCE_INTAKE_EXECUTION_START_BOUNDARY.md`.

Current-main predecessor commit: `82fb2078484a6bd627986198e6c6c9c4c9f53253`.

## Repo-Confirmed Failure Boundary

`backend/app/services/layer3_workbench.py` currently admits execution result/status inspection only for wrapped quantitative pass runs or the frozen single APS-document qualitative pass.

For a completed source-intake pass run, the current `execution_result_status` path rejects before status payload construction with `unsupported_execution_result_status_engine`.

The existing result/status path already validates:

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
- prior analysis-execution-start state

The missing boundary is therefore not source-intake execution start, result review, package construction, handoff/export, connector dispatch, provider URLs, RAG/vector indexing, route creation, rendered UI, model/migration work, or auth/security behavior. The missing boundary is the narrow owner-service rule that may allow result/status read-only inspection of exactly the deterministic source-intake execution output already produced by the selected pass run.

## Future Result/Status Semantics

The next implementation may allow `execution_result_status` to inspect exactly one completed source-intake pass run when all of the following are true:

- The request uses the existing `execution_result_status` request contract; no route fields are added.
- The selected `L3PassRun` belongs to the current execution selection for the same `session_id`, `analysis_plan_id`, `preview_id`, and `preview_hash`.
- The pass run has prior `analysis_execution_start` state from `306_SOURCE_INTAKE_EXECUTION_START_BOUNDARY_FREEZE`.
- The pass run has status `completed`.
- The pass run has no `analysis_run_id`.
- The pass run has an `output_payload_ref` pointing to deterministic `layer3.source_intake_execution_output.v1` metadata.
- The pass run has engine family `source_intake_qualitative_preview`.
- The output payload preserves `source_intake_record_id`, `candidate_id`, `source_identity`, `source_provenance`, and `storage_pointer.absolute_path_exposed = false`.
- The pass run and output payload agree on source-intake identity, method, engine family, pass scope, and source gate.

Required future behavior:

- Return read-only result/status state for the source-intake execution output.
- Preserve the no-`AnalysisRun` invariant in the response.
- Preserve source-intake identity and preview identity in the response.
- Keep result-review, package-review, package-construction, handoff/export, connector, provider, RAG/vector, route, UI, model, migration, auth/security, and broad qualitative behavior blocked.
- Fail closed if the output payload is missing, malformed, mismatched, outside the admitted schema, or inconsistent with the selected pass run.

## Required Future Proof

The next implementation must prove:

- Source-intake completed pass runs can be inspected through `execution_result_status`.
- The response reads deterministic `layer3.source_intake_execution_output.v1` metadata and preserves source identity.
- No `AnalysisRun` is required or created.
- No package, handoff, export, connector, provider, RAG/vector, route, UI, model, migration, or auth/security behavior is added.
- Preview id/hash mismatch still fails closed.
- Missing output payload fails closed.
- Mismatched output source identity fails closed.
- Non-source-intake unsupported engines remain blocked.
- Existing wrapped quantitative and single APS-document qualitative result/status behavior remains unchanged.

## Blocked Scope

This freeze does not admit:

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

## Next Allowed Action

Next allowed code-bearing action: `implement_source_intake_execution_result_status_boundary` only.

That implementation must stay in `backend/app/services/layer3_workbench.py` and focused workbench result/status tests unless live repo evidence proves a narrower supporting source-intake result/status contract file is already the canonical seam. Any result-review, package, connector, provider, RAG/vector, source expansion, route, UI, model, migration, auth/security, or broad qualitative execution work requires a separate freeze.
