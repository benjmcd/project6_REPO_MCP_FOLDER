# 301 Source Intake Plan Approval Boundary Freeze

## Status

Status: planning/control freeze for `source_intake_plan_approval_boundary`.

Branch: `codex/l3-source-intake-plan-approval-freeze`.

Runtime predecessor: `source_intake_plan_preview_boundary`.

Selected runtime family: `source_breadth_runtime`.

Selected runtime mode: `source_intake_plan_approval_boundary`.

Named operator/product use case: `operator_uploaded_single_source_approves_previewed_plan_after_gate_c_typing`.

Canonical source of truth: server-owned Gate C and plan-preview state derived from `L3SourceIntakeRecord`, specifically finalized `L3Session`, qualitative `L3AnalysisSet`, `L3AnalysisUnit`, `L3MaterialSnapshot`, and the service-owned source-intake plan preview hash/payload emitted by `backend/app/services/layer3_pass_entry.py`.

Implementation predecessor: `300_SOURCE_INTAKE_PLAN_PREVIEW_BOUNDARY.md`.

## Repo-Confirmed Failure Boundary

`backend/app/services/layer3_pass_entry.py` currently admits `operator_uploaded_single_source` qualitative single-item material into preview-only plan material, but `approve_pass_entry_plan` intentionally fails closed for source-intake candidates with `source-intake plan approval is not admitted by this preview-only boundary`.

The existing approval path already persists an `L3AnalysisPlan` for admitted non-source-intake candidates after operator confirmation and preview-hash revalidation, with `approval_only` set and execution still not started. The missing source-intake boundary is therefore not route creation, execution, package construction, or UI work; it is the narrow owner-service rule that permits exactly this source-intake preview payload to become an approved plan while preserving the same fail-closed preview-hash and operator-confirmation semantics.

## Future Approval Semantics

The next implementation may allow `POST /api/v1/layer3/plan/approve` to approve only the existing source-intake preview candidate emitted by `source_intake_plan_preview_boundary`.

Required future behavior:

- Revalidate the supplied preview hash against the current server-owned plan preview basis.
- Require explicit operator confirmation exactly as the existing approval path does.
- Persist an approval-only `L3AnalysisPlan` for the source-intake planned pass.
- Preserve `material_snapshot_id`, `source_intake_record_id`, `candidate_id`, `pass_scope`, `source_gate`, `engine_family`, and `selected_method_name` in the approved owner plan payload.
- Mark approved sets as approved, not executed.
- Create no `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, `L3OutputPackage`, package, connector, provider, RAG/vector, local-authority, auth/security, or frontend-only durable state.
- Keep execution start blocked behind a later named freeze.

## Required Future Proof

The next implementation must prove:

- Source-intake preview-only planned pass can become an approval-only `L3AnalysisPlan`.
- Source-intake approval preserves server-owned preview identity and source-intake source identity.
- Preview hash mismatch still fails closed before persistence.
- Missing operator confirmation still fails closed before persistence.
- Plan approval does not create `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, or `L3OutputPackage`.
- Execution start remains blocked for source-intake approved plans.
- Existing quantitative dataset-version approval behavior remains unchanged.
- Existing APS qualitative approval behavior remains unchanged.
- Unsupported adjacent qualitative source shapes remain blocked.

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

Next allowed code-bearing action: `implement_source_intake_plan_approval_boundary` only.

That implementation must stay in `backend/app/services/layer3_pass_entry.py` and focused pass-entry approval tests unless live repo evidence proves a narrower supporting contract file is already the canonical approval seam. Any execution, package, connector, provider, RAG/vector, source expansion, route, UI, model, or migration work requires a separate freeze.
