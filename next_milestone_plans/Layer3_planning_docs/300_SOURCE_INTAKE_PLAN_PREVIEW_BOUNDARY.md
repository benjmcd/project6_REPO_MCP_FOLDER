# 300 Source Intake Plan Preview Boundary

## Status

Status: current-main implementation with targeted validation passed for `source_intake_plan_preview_boundary`.

Implementation branch: `codex/l3-source-intake-plan-preview`.

Implementation commit: `46af1d10828ef1bbe0eb7459a1dca6c5a3e1a0fc`.

Merged PR: `#885`.

Merge commit/current-main authority: `28ab25cc0dc1d8e2e1d92f017f817990dc5ed05c`.

Merged at: `2026-05-13T06:48:29Z`.

GitHub checks: `backend-layer3-api` success and `test` success.

Implementation predecessor: `299_SOURCE_INTAKE_PLAN_PREVIEW_BOUNDARY_FREEZE.md`.

Canonical source of truth: server-owned Gate C state derived from `L3SourceIntakeRecord`, specifically finalized `L3Session` state plus qualitative `L3AnalysisSet`, `L3AnalysisUnit`, and `L3MaterialSnapshot` rows whose `source_shape` is `operator_uploaded_single_source`.

## Implemented Boundary

This slice implements exactly the plan-preview boundary selected by doc 299:

- `backend/app/services/layer3_pass_entry.py` admits `operator_uploaded_single_source` qualitative single-item analysis sets for preview-only plan material.
- The source-intake planned pass uses pass scope `qualitative_single_item_operator_uploaded_source`.
- The source gate is `299_SOURCE_INTAKE_PLAN_PREVIEW_BOUNDARY_FREEZE`.
- The preview engine family is `source_intake_qualitative_preview`.
- The selected method marker is `operator_uploaded_source_review_preview`.
- Source-intake source identity remains in the owner plan payload through `material_snapshot_id`, `source_intake_record_id`, and `candidate_id`.
- `approve_pass_entry_plan` fails closed for source-intake preview candidates with `source-intake plan approval is not admitted by this preview-only boundary`.

No route, DTO, model, migration, rendered UI, provider URL, connector, execution, package, RAG/vector, auth/security, local-directory, or frontend-only durable authority behavior is added.

## Proof

Targeted validation run:

```text
pytest .\backend\tests\test_layer3_pass_entry.py
```

Result: `22 passed`.

The focused test coverage proves:

- Existing quantitative dataset-version preview behavior remains covered.
- Existing APS qualitative preview behavior remains covered by the pass-entry suite.
- `operator_uploaded_single_source` Gate C output produces one preview-only planned pass.
- The preview source summary reports `operator_uploaded_single_source`.
- The source-intake planned pass uses source-intake-specific pass scope, source gate, engine family, and method marker.
- The preview hash is stable across repeated preview calls for the same server-owned source-intake basis.
- Plan preview creates no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, or `L3OutputPackage`.
- Source-intake plan approval remains blocked before creating an approved plan or downstream state.

## Blocked Scope

The following remain blocked after this implementation:

- source-intake plan approval
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

Next required decision: `source_intake_plan_approval_boundary_freeze` before source-intake preview-only plan material is allowed to become an approved plan.

The next allowed implementation must be selected by a separate freeze. This implementation only makes source-intake Gate C output visible to plan preview as preview-only plan material.
