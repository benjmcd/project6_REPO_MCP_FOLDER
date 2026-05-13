# 312 Source Intake Package Review Preview Boundary Freeze

## Status

Status: planning/control freeze for `source_intake_package_review_preview_boundary`.

Branch: `codex/l3-source-intake-package-review-freeze`.

Current-main predecessor commit: `2c616d8d6a7ebfb204bbb54c3c72f51e94f9d28c`.

Runtime predecessor: `source_intake_execution_result_review_boundary`.

Predecessor doc: `311_SOURCE_INTAKE_EXECUTION_RESULT_REVIEW_BOUNDARY.md`.

Selected runtime family: `source_breadth_runtime`.

Selected runtime mode: `source_intake_package_review_preview_boundary`.

Named operator/product use case: `operator_uploaded_single_source_previews_package_readiness_after_result_review`.

Canonical source of truth: server-owned completed `L3PassRun`, deterministic `layer3.source_intake_execution_output.v1` payload, admitted `execution_result_status` response, and approved `execution_result_review` state for the same source-intake pass identity.

Owner service: `backend/app/services/layer3_workbench.py`.

Current repo-confirmed failure boundary: `package_review_preview` rejects source-intake reviewed output with `source_intake_package_review_preview_not_admitted`.

Next allowed code-bearing action: `implement_source_intake_package_review_preview_boundary` only.

## Frozen Admission Question

The next implementation may decide whether a source-intake reviewed output can reach the existing `package_review_preview` read-only readiness surface.

The future admitted case, if implemented, must require:

- existing `package_review_preview` request contract
- available source-intake `execution_result_status`
- approved source-intake `execution_result_review` state
- no `AnalysisRun`
- pass type `single_item`
- pass scope `qualitative_single_item_operator_uploaded_source`
- selected method `operator_uploaded_source_review_preview`
- engine family `source_intake_qualitative_preview`
- source gate `306_SOURCE_INTAKE_EXECUTION_START_BOUNDARY_FREEZE`
- output metadata schema `layer3.source_intake_execution_output.v1`
- preserved `source_intake_record_id`, `candidate_id`, output hash, preview id, and preview hash
- no unresolved trace references
- no existing package or reconciliation rows for the session
- storage pointer with `absolute_path_exposed = false`

## Required Future Proof

The implementation proof must show:

- source-intake approved result review can produce package-review preview readiness
- package-review preview hash or identity is deterministic and server-derived
- source-intake identity is preserved in the preview response
- no `AnalysisRun` is required or created
- no `L3OutputPackage` or `L3ReconciliationRecord` is created
- package construction remains blocked behind a later boundary
- package review submit remains blocked behind a later boundary
- handoff/export prepare remains blocked behind a later boundary
- APS handoff dispatch remains blocked behind a later boundary
- external export/download remains blocked behind a later boundary
- missing or unavailable source-intake result/status fails closed
- missing, unapproved, mismatched, or trace-unresolved result-review state fails closed
- existing package/reconciliation state fails closed
- source-intake `AnalysisRun` references fail closed
- existing associated-cohort and single-APS package-review preview behavior remains unchanged

## Explicit Non-Goals

This freeze does not admit:

- package construction or mutation
- package review submit or commit
- handoff/export prepare or dispatch
- APS handoff dispatch
- external export/download prepare or delivery
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

## Stop Condition

If the future implementation cannot prove source-intake package-review preview readiness using only server-owned result/status plus approved result-review state, it must remain blocked with `source_intake_package_review_preview_not_admitted` or a narrower fail-closed error. It must not bypass the existing `package_review_preview` request contract or seed package/reconciliation state during validate-only proof.

## Next Required Decision

After this freeze, the next code-bearing step is `implement_source_intake_package_review_preview_boundary` only.

No package construction, package review submit, handoff/export, connector, provider, RAG/vector, source expansion, route, UI, model, migration, auth/security, or broad qualitative execution work is admitted without a separate freeze.
