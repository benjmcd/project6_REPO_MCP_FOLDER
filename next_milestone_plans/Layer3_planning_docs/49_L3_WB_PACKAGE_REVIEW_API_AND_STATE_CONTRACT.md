# Layer 3 Workbench Package Review API And State Contract

Status: governing API/state companion for `48_L3_WB_PACKAGE_REVIEW_FREEZE.md`.

This document defines the state, data, endpoint, and proof contract for a future bounded package-review preview/readiness implementation after PR `#232`. It does not make package review live by itself and does not admit durable package construction, package-review submission, handoff/export, rerun/recovery, source expansion, schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Authority Order

Package-review preview must use this authority order:

1. durable `L3Session` state returned by the Layer 3 API
2. approved plan identity and approved preview id/hash from server state
3. execution-selection summary from server state
4. selected `L3PassRun` identity and terminal status from server state
5. analysis-execution-start state from server state
6. result/status response or summary for the selected terminal pass
7. existing selected-pass output metadata reference and readable metadata
8. recorded selected-pass result-review state from server state
9. existing package owner-service contracts as compatibility constraints
10. request payload as preview intent only
11. browser state as display/cache only

Browser state must not approve, revise, select, run, retry, cancel, package, export, hand off, or recover output.

## Optional Endpoint

If existing session summary data is insufficient for a safe preview, a future implementation may add at most one read-only endpoint:

`POST /api/v1/layer3/package/review/preview`

The endpoint may compute package-review readiness for one current approved selected-pass result review. It must not write durable package, reconciliation, artifact, handoff, runtime, schema, source-ingestion, or execution state.

Minimum request fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `session_id` | yes | Existing Layer 3 workbench session |
| `analysis_plan_id` | yes | Current approved plan for the session |
| `pass_run_id` | yes | Existing selected terminal pass run for the session and approved plan |
| `preview_id` | yes | Must match approved plan and selected-pass preview identity |
| `preview_hash` | yes | Must match approved plan and selected-pass preview hash |
| `result_review_record_ref` | conditional | Required when server summary cannot uniquely identify the recorded approved review |
| `analysis_run_id` | no | If supplied, must match selected pass state |

Forbidden request fields include:

- `package`
- `package_review_decision`
- `create_package`
- `package_variant`
- `output_package_id`
- `reconciliation_record_id`
- `handoff`
- `export`
- `rerun`
- `retry`
- `recover`
- `cancel`
- `selected_pass_ids`
- `pass_run_ids`
- `new_analysis_plan`
- `plan_revision`
- `source_expansion`
- `local_upload`
- `local_directory`
- `schema_migration`
- `runtime_db_write`
- `artifact_manifest`
- `aps_handoff`
- `edited_findings`
- `rewrite_output`

## Response Contract

Minimum response fields:

| Field | Meaning |
| --- | --- |
| `schema_id` | `layer3.package_review_preview.v1` or later frozen replacement |
| `status` | `available`, `blocked`, or fail-closed error status |
| `session_id` | session authority |
| `analysis_plan_id` | approved-plan authority |
| `pass_run_id` | selected pass-run authority |
| `preview_identity` | matched preview id/hash metadata |
| `analysis_run_id` | wrapped quantitative `AnalysisRun` id for the selected pass, when present |
| `result_status_available` | `true` only when result/status authority is satisfied |
| `result_review_state` | must be `execution_result_review_approved` for an available preview |
| `result_review_record_ref` | bounded reference to the existing result-review record |
| `package_review_preview_enabled` | `true` only for read-only preview availability |
| `package_review_enabled` | always `false` for submit/commit behavior in this tranche |
| `candidate_package_kinds` | preview-only candidate list, limited to `canonical_internal`, `user_facing`, and `review_facing` |
| `package_owner_compatibility` | compatibility status against existing package owner-service preconditions |
| `blocked_reasons` | machine-readable reasons when preview is blocked |
| `downstream_unavailable` | must include `package_commit`, `package_review_submit`, `handoff`, and `export` |

The response must not include package payload bodies that imply emitted package artifacts. It may include bounded summaries and trace references only when those values are already available from current server authority.

## State Model Delta

The implementation may add only these state meanings:

| State | Authority source | Allowed next actions | Forbidden downstream actions |
| --- | --- | --- | --- |
| `package_review_preview_unavailable` | missing session, plan, selected pass, terminal status, result/status, or result-review authority | inspect upstream state | package preview, package construction, handoff |
| `package_review_preview_blocked` | server fail-closed check, missing approved result review, owner-service incompatibility, missing output, unresolved trace, or forbidden payload | inspect block reasons | package construction, package-review submit, handoff, rerun |
| `package_review_preview_ready` | approved selected-pass result review plus compatible preview basis | inspect package candidates | package construction, package-review submit, handoff/export |
| `package_review_preview_inspected` | preview response has been displayed | inspect again | package construction, package-review submit, handoff/export |

These states are preview/readiness states only. They are not package construction states and do not authorize `L3OutputPackage` or `L3ReconciliationRecord` writes.

## Write Boundary

The endpoint and any UI governed by this contract must not create or update:

- `L3OutputPackage`
- `L3ReconciliationRecord`
- `L3AnalysisPlan`
- `L3PassRun`
- `AnalysisRun`
- `AnalysisArtifact`
- package payload files
- package-review rows
- handoff rows or handoff artifacts
- runtime snapshot DB rows
- source-ingestion rows for local upload, local directory, RAG, or vector retrieval
- schema/migration files

If implementation cannot provide a useful package-review preview without one of those writes, it must stop and require a separate package-construction or package-review-commit freeze.

## Package Candidate Projection

The preview may name only these package kinds:

- `canonical_internal`
- `user_facing`
- `review_facing`

The preview may show:

- selected-pass identity and result-review state
- existing output metadata reference
- trace summary and unresolved-trace count
- package-owner compatibility status
- candidate package kind labels and short readiness reasons
- explicit blocked downstream posture

The preview must not show:

- package payload file paths that do not exist
- generated package payload content
- package ids
- reconciliation record ids
- handoff ids
- export ids
- editable output rewrites
- active package variant tabs

## Failure Behavior

The endpoint must fail closed when:

- approved plan or preview identity is missing or stale
- selected pass is missing, foreign, non-selected, or non-terminal
- result/status authority is unavailable
- result review is missing, not approved, blocked, rejected, or changes requested
- output metadata is missing or unreadable
- trace requirements are unresolved for the approved review
- existing package rows already exist for the session and would make preview ambiguous
- package owner-service compatibility cannot be assessed
- request payload asks for package creation, package-review submission, handoff/export, rerun, recovery, source expansion, schema migration, runtime DB write, output rewrite, or full mockup activation

For server errors, the UI must preserve existing upstream state and display the block reason. It must not replace missing authority with guessed local values.

## UI Boundary

If a later implementation changes `/review/layer3`, the UI may only expose:

- read-only package-review preview status after an approved selected-pass result review
- package candidate kind labels as preview-only
- package owner-service compatibility posture
- blocked reasons and upstream next action
- disabled package construction, package-review submit, handoff, and export indicators

The UI must not expose:

- package creation buttons
- package-review decision controls
- active package variant tabs
- handoff/export controls
- rerun/retry/recovery/cancel controls
- source-expansion pickers
- local upload or directory selectors
- raw output editing or rewrite controls
- qualitative/hybrid/RAG/vector controls

## Tests Required Before Merge

Implementation tests must cover:

- no package-review preview before a session exists
- no package-review preview before approved plan, selected pass, result/status, and approved result-review authority exist
- non-approved result-review states fail closed
- stale preview id/hash fails closed
- missing output metadata and unresolved trace fail closed
- forbidden package/handoff/rerun/source/schema/runtime/output-rewrite fields fail closed
- existing package rows block or return a deterministic unavailable state without mutation
- no `L3OutputPackage`, `L3ReconciliationRecord`, `AnalysisArtifact`, package payload file, handoff artifact, runtime DB row, schema migration, or source-ingestion row is created
- package candidate kinds are limited to `canonical_internal`, `user_facing`, and `review_facing`
- existing result/status and result-review flows still pass
- both headed and headless Chrome browser proof pass if rendered UI behavior changes

## Still Deferred

Still deferred after this contract:

- package construction
- package-review submission or decision state
- package variant tabs as live controls
- `canonical_internal`, `user_facing`, and `review_facing` payload emission from the workbench route
- handoff/export trigger policy
- APS handoff behavior
- result-review amendment or supersession
- rerun, retry, cancellation, or recovery workflows
- approved-plan correction or supersession
- source-breadth expansion
- local upload or local-directory ingestion
- qualitative/hybrid/RAG/vector execution
- broad UI/full mockup activation
