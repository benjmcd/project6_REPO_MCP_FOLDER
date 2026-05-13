# 305 Source Intake Execution Selection Boundary

## Status

Status: branch-local implementation with targeted validation passed for `source_intake_execution_selection_boundary`.

Implementation branch: `codex/l3-source-intake-exec-selection`.

Implementation predecessor: `304_SOURCE_INTAKE_EXECUTION_SELECTION_BOUNDARY_FREEZE.md`.

Canonical source of truth: server-owned approved `L3AnalysisPlan` payload derived from `L3SourceIntakeRecord` Gate C and plan-preview state, plus existing `L3Session` execution-selection summary state.

## Implemented Boundary

This slice implements exactly the selected-not-started shell boundary selected by doc 304:

- `backend/app/services/layer3_workbench.py` allows source-intake approved planned passes through `execution_selection`.
- The created `L3PassRun` shell has status `selected_not_started`.
- The pass-run shell preserves preview identity through `source_preview_id` and `source_preview_hash`.
- The pass-run shell preserves source-intake planned-pass identity through `planned_pass`, including `source_intake_record_id`, `candidate_id`, `pass_scope`, `source_gate`, `engine_family` (`source_intake_qualitative_preview`), and `selected_method_name`.
- Idempotent replay for the same `client_request_id` returns `already_selected` and does not create another pass run.
- `analysis_execution_start` still rejects the source-intake selected pass run with `unsupported_analysis_execution_engine`.

No route, DTO, model, migration, rendered UI, execution start, package, connector, provider, RAG/vector, auth/security, local-directory, or frontend-only durable authority behavior is added.

## Proof

Targeted validation run:

```text
pytest .ackend	ests	est_layer3_workbench.py
```

Result: `22 passed`. Validation literal: `pytest .\backend\tests\test_layer3_workbench.py`.

The focused test coverage proves:

- Source-intake approved plans create one selected-not-started `L3PassRun` shell through `execution_selection`.
- The selected pass-run shell preserves preview identity and source-intake planned-pass identity.
- Idempotent replay does not create a duplicate pass run.
- Source-intake execution start remains blocked after selection.
- Existing workbench behavior covered by the focused suite remains passing.

## Blocked Scope

The following remain blocked after this implementation:

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

Next required decision: `source_intake_execution_start_boundary_freeze` before a selected source-intake pass run may start execution.

The next allowed implementation must be selected by a separate freeze. This implementation only lets an approved source-intake plan become selected-not-started pass-run shell state.
