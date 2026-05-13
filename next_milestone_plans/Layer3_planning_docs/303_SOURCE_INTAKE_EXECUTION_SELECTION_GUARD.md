# 303 Source Intake Execution Selection Guard

## Status

Status: current-main corrective guard with targeted validation passed for `source_intake_execution_selection_guard`.

Implementation branch: `codex/l3-source-intake-exec-selection-guard`.

Implementation commit: `609b6262f13163a4043c76c9b4f952ecc3eeb9fc`.

Merged PR: `#890`.

Merge commit/current-main authority: `c0c8defd169d3132bbed9fa202f829794f86b32f`.

Merged at: `2026-05-13T08:03:58Z`.

GitHub checks: `backend-layer3-api` success and `test` success.

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

## Supersession Note

The fail-closed execution-selection guard in this corrective closeout is superseded by `305_SOURCE_INTAKE_EXECUTION_SELECTION_BOUNDARY.md` on branch `codex/l3-source-intake-exec-selection`. The guard remains the current-main predecessor that proved the boundary was closed before the freeze; the later implementation admits only selected-not-started `L3PassRun` shell creation and still does not admit execution start or downstream state.
