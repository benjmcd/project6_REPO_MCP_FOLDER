# 303 Source Intake Execution Selection Guard

## Status

Status: branch-local corrective guard with targeted validation passed for `source_intake_execution_selection_guard`.

Implementation branch: `codex/l3-source-intake-exec-selection-guard`.

Corrective predecessor: `302_SOURCE_INTAKE_PLAN_APPROVAL_BOUNDARY.md`.

Canonical source of truth: server-owned approved `L3AnalysisPlan` payload derived from `L3SourceIntakeRecord` Gate C and plan-preview state.

## Corrected Boundary

This slice restores the blocked scope declared by doc 302:

- `backend/app/services/layer3_workbench.py` now rejects execution selection for approved planned passes whose `pass_scope` is `qualitative_single_item_operator_uploaded_source` or whose `engine_family` is `source_intake_qualitative_preview`.
- The guard runs before any `L3PassRun` shell is created.
- The emitted workbench error is `source_intake_execution_selection_not_admitted` with blocked field `analysis_plan_id` and next action `freeze_source_intake_execution_selection_boundary`.
- Existing quantitative and other admitted execution-selection behavior remains outside this corrective guard.

No route, DTO, model, migration, rendered UI, execution start, package, connector, provider, RAG/vector, auth/security, local-directory, or frontend-only durable authority behavior is added.

## Proof

Targeted validation run:

```text
pytest .ackend	ests	est_layer3_workbench.py
```

Result: `22 passed`. Validation literal: `pytest .\backend\tests\test_layer3_workbench.py`.

The focused test coverage proves:

- A source-intake approved plan is rejected by `execution_selection` before selected pass-run shell creation.
- The rejection uses `source_intake_execution_selection_not_admitted`.
- No `L3PassRun` is created for the source-intake approved plan.
- The existing workbench suite remains passing after the guard.

## Blocked Scope

The following remain blocked after this corrective guard:

- source-intake execution selection
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

## Next Boundary

Next required decision remains `source_intake_execution_selection_boundary_freeze` before a source-intake approved plan may create selected pass-run state or start any execution.
