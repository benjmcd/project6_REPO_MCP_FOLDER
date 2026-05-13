# 314 Source Intake Package Construction Commit Boundary Freeze

## Status

Status: planning/control freeze for `source_intake_package_construction_commit_boundary`.

Branch: `codex/l3-source-intake-package-construction-freeze`.

Current-main predecessor commit: `f31db456cd0a5beb5b446935cdb8a4ebdaa5ecde`.

Runtime predecessor: `source_intake_package_review_preview_boundary`.

Predecessor doc: `313_SOURCE_INTAKE_PACKAGE_REVIEW_PREVIEW_BOUNDARY.md`.

Selected runtime family: `source_breadth_runtime`.

Selected runtime mode: `source_intake_package_construction_commit_boundary`.

Named operator/product use case: `operator_uploaded_single_source_commits_reviewed_source_intake_package`.

Canonical source of truth: server-owned completed `L3PassRun`, deterministic `layer3.source_intake_execution_output.v1` payload, admitted `execution_result_status` response, approved `execution_result_review` state, and read-only `layer3.source_intake_package_review_preview.v1` readiness identity for the same source-intake pass.

Owner service: `backend/app/services/layer3_workbench.py`.

Current repo-confirmed failure boundary: `package_construction_commit` rejects source-intake package-preview readiness with `source_intake_package_construction_commit_not_admitted`.

Next allowed code-bearing action: `implement_source_intake_package_construction_commit_boundary` only.

## Frozen Admission Question

The next implementation may decide whether source-intake package-review preview readiness can create bounded package-construction state through the existing `package_construction_commit` surface.

The future admitted case, if implemented, must require:

- existing `package_construction_commit` request contract
- available source-intake `execution_result_status`
- approved source-intake `execution_result_review` state
- read-only source-intake `package_review_preview` readiness
- matching `package_review_preview_hash`
- no `AnalysisRun`
- pass type `single_item`
- pass scope `qualitative_single_item_operator_uploaded_source`
- selected method `operator_uploaded_source_review_preview`
- engine family `source_intake_qualitative_preview`
- source gate `306_SOURCE_INTAKE_EXECUTION_START_BOUNDARY_FREEZE`
- package-review preview schema `layer3.source_intake_package_review_preview.v1`
- output metadata schema `layer3.source_intake_execution_output.v1`
- preserved `source_intake_record_id`, `candidate_id`, output hash, preview id, and preview hash
- no unresolved trace references
- no pre-existing package or reconciliation rows for the session
- storage pointer with `absolute_path_exposed = false`

## Required Future Proof

The implementation proof must show:

- source-intake package-review preview readiness can create bounded package-construction state
- package construction identity is deterministic and server-derived
- source-intake identity is preserved in package/reconciliation state
- package payload refs and hashes are derived from server-owned source-intake output, not client-supplied payloads
- no `AnalysisRun` is required or created
- no unrelated package kinds are created
- duplicate or conflicting construction requests fail closed or replay idempotently
- stale, missing, or mismatched `package_review_preview_hash` fails closed
- missing, unapproved, mismatched, or trace-unresolved result-review state fails closed
- source-intake `AnalysisRun` references fail closed
- package review submit remains blocked behind a later boundary
- handoff/export prepare remains blocked behind a later boundary
- APS handoff dispatch remains blocked behind a later boundary
- external export/download remains blocked behind a later boundary
- existing associated-cohort and single-APS package-construction behavior remains unchanged

## Explicit Non-Goals

This freeze does not admit:

- package review submit or commit approval
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

If the future implementation cannot prove source-intake package construction using only server-owned package-review preview readiness, result/status, approved result-review state, and deterministic source-intake output authority, it must remain blocked with `source_intake_package_construction_commit_not_admitted` or a narrower fail-closed error. It must not bypass the existing `package_construction_commit` request contract or seed downstream submit/export state during validate-only proof.

## Next Required Decision

After this freeze, the next code-bearing step is `implement_source_intake_package_construction_commit_boundary` only.

No package review submit, handoff/export, connector, provider, RAG/vector, source expansion, route, UI, model, migration, auth/security, or broad qualitative execution work is admitted without a separate freeze.
