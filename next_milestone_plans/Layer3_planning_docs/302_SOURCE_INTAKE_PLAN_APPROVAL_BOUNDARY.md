# 302 Source Intake Plan Approval Boundary

## Status

Status: branch-local implementation with targeted validation passed for `source_intake_plan_approval_boundary`.

Implementation branch: `codex/l3-source-intake-plan-approval`.

Implementation predecessor: `301_SOURCE_INTAKE_PLAN_APPROVAL_BOUNDARY_FREEZE.md`.

Canonical source of truth: server-owned Gate C and plan-preview state derived from `L3SourceIntakeRecord`, specifically finalized `L3Session`, qualitative `L3AnalysisSet`, `L3AnalysisUnit`, `L3MaterialSnapshot`, and the service-owned source-intake plan preview hash/payload emitted by `backend/app/services/layer3_pass_entry.py`.

## Implemented Boundary

This slice implements exactly the approval-only boundary selected by doc 301:

- `backend/app/services/layer3_pass_entry.py` now allows source-intake qualitative preview candidates to use the existing `approve_pass_entry_plan` approval path.
- Operator confirmation remains required before persistence.
- Preview-hash revalidation remains required when a preview hash is supplied.
- Approval persists only an `L3AnalysisPlan` with `approval_only` true and `execution_started` false.
- The approved owner plan payload preserves `material_snapshot_id`, `source_intake_record_id`, `candidate_id`, `pass_scope`, `source_gate`, `engine_family`, and `selected_method_name`, including selected method marker `operator_uploaded_source_review_preview`.
- Source-intake execution remains blocked because selected-pass execution still rejects `source_intake_qualitative_preview` as an unsupported execution engine family.

No route, DTO, model, migration, rendered UI, provider URL, connector, execution, package, RAG/vector, auth/security, local-directory, or frontend-only durable authority behavior is added.

## Proof

Targeted validation run:

```text
pytest .ackend	ests	est_layer3_pass_entry.py
```

Result: `24 passed`. Validation literal: `pytest .\backend\tests\test_layer3_pass_entry.py`.

The focused test coverage proves:

- Source-intake preview-only planned pass can become an approval-only `L3AnalysisPlan`.
- Source-intake approval preserves server-owned preview identity and source-intake source identity.
- Preview hash mismatch fails closed before persistence.
- Missing operator confirmation fails closed before persistence.
- Plan approval creates no `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, or `L3OutputPackage`.
- Source-intake selected-pass execution remains blocked and creates no downstream artifact state.
- Existing pass-entry preview/approval/execution tests for quantitative and APS-adjacent behavior remain covered by the focused suite.

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

Next required decision: `source_intake_execution_selection_boundary_freeze` before a source-intake approved plan may create selected pass-run state or start any execution.

The next allowed implementation must be selected by a separate freeze. This implementation only lets the existing preview-only source-intake plan become an approval-only plan.
