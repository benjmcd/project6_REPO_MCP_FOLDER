# 304 Source Intake Execution Selection Boundary Freeze

## Status

Status: planning/control freeze for `source_intake_execution_selection_boundary`.

Branch: `codex/l3-source-intake-exec-selection-freeze-2`.

Runtime predecessor: `source_intake_execution_selection_guard`.

Selected runtime family: `source_breadth_runtime`.

Selected runtime mode: `source_intake_execution_selection_boundary`.

Named operator/product use case: `operator_uploaded_single_source_selects_approved_plan_for_execution_shell`.

Canonical source of truth: server-owned approved `L3AnalysisPlan` payload derived from `L3SourceIntakeRecord` Gate C and plan-preview state, plus existing `L3Session` execution-selection summary state.

Implementation predecessor: `303_SOURCE_INTAKE_EXECUTION_SELECTION_GUARD.md`.

## Repo-Confirmed Failure Boundary

`backend/app/services/layer3_workbench.py` currently rejects source-intake approved planned passes in `execution_selection` before `L3PassRun` shell creation with `source_intake_execution_selection_not_admitted`.

The existing execution-selection path already validates `client_request_id`, `session_id`, `analysis_plan_id`, `preview_id`, `preview_hash`, forbidden fields, current approved-plan identity, preview identity, idempotency, and absence of existing pass runs before creating selected-not-started `L3PassRun` shell rows. The missing boundary is therefore not execution start, package construction, route creation, UI work, or schema work; it is the narrow owner-service rule that may allow exactly source-intake approved planned passes to become selected-not-started pass-run shells while preserving the same approval/preview/idempotency contract.

## Future Selection Semantics

The next implementation may allow `execution_selection` to create selected-not-started `L3PassRun` shell rows only for source-intake approved planned passes whose approved plan payload came from `source_intake_plan_approval_boundary`.

Required future behavior:

- Reuse the existing `execution_selection` request contract; do not add route fields.
- Require current approved `L3AnalysisPlan` identity and matching approved preview id/hash.
- Preserve the source-intake planned pass identity in the selected pass-run shell summary, including `source_intake_record_id`, `candidate_id`, `pass_scope`, `source_gate`, `engine_family`, and `selected_method_name`.
- Create only `L3PassRun` rows with status `selected_not_started`.
- Preserve idempotent replay behavior for the same `client_request_id` and reject conflicting replay.
- Create no `AnalysisRun`, `AnalysisArtifact`, `L3OutputPackage`, package, connector, provider, RAG/vector, local-authority, auth/security, or frontend-only durable state.
- Keep execution start blocked behind a later named freeze.

## Required Future Proof

The next implementation must prove:

- Source-intake approved plans create selected-not-started `L3PassRun` shell rows through `execution_selection`.
- The selected pass-run shell preserves preview identity and source-intake source identity.
- Preview id/hash mismatch still fails closed before `L3PassRun` creation.
- Missing or conflicting `client_request_id` behavior remains fail-closed/idempotent.
- No `AnalysisRun`, `AnalysisArtifact`, or `L3OutputPackage` is created.
- Source-intake execution start remains blocked after selection.
- Existing quantitative and associated-cohort execution-selection behavior remains unchanged.

## Blocked Scope

This freeze does not admit:

- execution start
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

## Next Allowed Action

Next allowed code-bearing action: `implement_source_intake_execution_selection_boundary` only.

That implementation must stay in `backend/app/services/layer3_workbench.py` and focused workbench execution-selection tests unless live repo evidence proves a narrower supporting contract file is already the canonical selection seam. Any execution start, package, connector, provider, RAG/vector, source expansion, route, UI, model, or migration work requires a separate freeze.
