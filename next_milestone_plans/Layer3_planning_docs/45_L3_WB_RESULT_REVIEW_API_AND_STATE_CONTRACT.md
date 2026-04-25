# Layer 3 Workbench Result Review API And State Contract

Status: governing API/state companion for `44_L3_WB_RESULT_REVIEW_FREEZE.md`.

This document defines the route, state, write boundary, response contract, and proof requirements for a future selected-pass result-review implementation. It does not make result review live by itself and does not admit package review, handoff, rerun/recovery, source expansion, schema/runtime widening, UI/full mockup activation, or qualitative/hybrid/RAG/vector execution.

## Authority Order

Selected-pass result review must use this authority order:

1. durable `L3Session` state
2. current server-backed plan-preview identity
3. current approved preview id/hash
4. durable approved `L3AnalysisPlan`
5. durable execution-selection summary from PR `#216`
6. durable selected `L3PassRun` shell state
7. PR `#218` analysis-execution-start state stored on the selected pass/session
8. PR `#222` result/status availability for the selected pass
9. existing selected-pass output metadata reference and readable metadata
10. result-review request payload as operator intent only
11. browser state as display/cache only

Browser state must not approve, revise, select, run, retry, cancel, package, export, or hand off result-review output.

## Endpoint

The bounded implementation may add one endpoint:

`POST /api/v1/layer3/execution/result/review`

The endpoint may record exactly one bounded review decision for one terminal selected pass-run result. It must not create package review, handoff, source-expansion, rerun/recovery, or full mockup state.

Minimum request fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `session_id` | yes | Must identify an existing Layer 3 workbench session |
| `analysis_plan_id` | yes | Must identify the current approved plan for the session |
| `pass_run_id` | yes | Must identify an existing selected terminal pass run for the session and approved plan |
| `preview_id` | yes | Must match the approved plan and execution-selection preview identity |
| `preview_hash` | yes | Must match the approved plan and execution-selection preview hash |
| `operator_decision` | yes | Must be `approved`, `changes_requested`, `rejected`, or `blocked` |
| `client_request_id` | yes | Required to make duplicate review submissions deterministic |
| `review_notes` | conditional | Required for `changes_requested`, `rejected`, or `blocked`; optional for `approved` |
| `reviewed_output_items` | no | Optional bounded list of item-level review references; each item must be traceable to existing output metadata |
| `analysis_run_id` | no | If supplied, must match the selected pass-run summary |

Forbidden request fields include:

- `package`
- `package_review`
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
- `package_variant`
- `aps_handoff`
- `edited_findings`
- `rewrite_output`

## Response Contract

Minimum response fields:

| Field | Meaning |
| --- | --- |
| `schema_id` | `layer3.execution_result_review.v1` or later frozen replacement |
| `status` | `recorded`, `already_recorded`, `blocked`, or fail-closed error status |
| `session_id` | session authority |
| `analysis_plan_id` | approved-plan authority |
| `pass_run_id` | selected pass-run authority |
| `preview_identity` | matched preview id/hash metadata |
| `analysis_run_id` | wrapped quantitative `AnalysisRun` id for the selected pass, when present |
| `result_status_available` | `true` only when PR `#222` result/status authority is satisfied |
| `result_review_enabled` | `true` only for this bounded result-review response after authority checks pass |
| `review_state` | `execution_result_review_approved`, `execution_result_review_changes_requested`, `execution_result_review_rejected`, or `execution_result_review_blocked` |
| `operator_decision` | normalized decision value |
| `review_record_ref` | bounded reference to the durable review metadata envelope, if recorded |
| `trace_summary` | selected pass/output metadata/analysis run/material-unit references used for review |
| `unresolved_trace_count` | count of reviewed output items lacking required trace references |
| `package_review_enabled` | always `false` for this tranche |
| `handoff_enabled` | always `false` for this tranche |
| `downstream_unavailable` | must include `package` and `handoff`; may include `package_review` until a later package-review freeze replaces it |

## State Model Delta

The implementation may add only these state meanings:

| State | Authority source | Allowed next actions | Forbidden downstream actions |
| --- | --- | --- | --- |
| `execution_result_review_ready` | PR `#222` result/status available for one selected terminal pass with readable output metadata | submit result review; inspect status again | package, handoff, rerun, source expansion, approved-plan supersession |
| `execution_result_review_approved` | bounded operator decision recorded for the selected pass | later separately frozen package step may consume approval | package creation by this endpoint, handoff, source expansion, approved-plan supersession |
| `execution_result_review_changes_requested` | bounded operator decision requiring revision or clarification | later separately frozen revision/recovery path may act | package, handoff, rerun by this endpoint, source expansion |
| `execution_result_review_rejected` | bounded operator rejection recorded for the selected pass | inspect status/review record only unless a later freeze admits recovery | package, handoff, rerun by this endpoint, source expansion |
| `execution_result_review_blocked` | authority, status, output metadata, trace, duplicate, or payload checks fail | fix upstream state through later admitted path | package, handoff, rerun, source expansion, approved-plan supersession |

Existing states keep their current behavior:

- `execution_result_status_available` is eligible for result review only after all authority and output metadata checks pass.
- `execution_result_status_missing_output` is not eligible for approval.
- `execution_result_status_blocked` is not eligible for review.
- `execution_selected_not_started`, `execution_pass_running`, and non-terminal pass states are not eligible for result review.
- `plan_approved`, `plan_rejected`, and `plan_revision_requested` are not result-review states.

## Write Boundary

The endpoint may write only:

- a bounded result-review envelope in an existing Layer 3 workbench-owned JSON summary field, such as the selected `L3PassRun` summary or session summary, if implementation proves that is the repo-local owner boundary
- normalized review decision
- `client_request_id`
- operator notes/caveats
- trace summary
- timestamps using existing repo patterns
- review-state marker for the selected pass only

The endpoint must not create or update:

- `L3AnalysisPlan`
- new `L3PassRun`
- new `AnalysisRun`
- `AnalysisArtifact`
- `L3OutputPackage`
- `L3ReconciliationRecord`
- package-review rows or package artifacts
- handoff rows or handoff artifacts
- runtime snapshot DB rows
- source-ingestion rows for local upload, local directory, RAG, or vector retrieval
- schema/migration files

If implementation cannot record a durable review decision without a new table, migration, package artifact, or cross-service audit row, it must stop and require a separate freeze.

## Output Review And Trace Contract

The result-review layer may classify reviewed output only with a minimal projection:

- `datum`
- `fact`
- `finding`
- `insight`
- `caveat`
- `contradiction`
- `unsupported_claim`
- `generated_narrative`

This projection is not a complete result taxonomy. It is a review-time label set used to avoid collapsing all output into a generic result.

Every approved reviewed output item must be traceable to:

- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `analysis_run_id`, when present
- selected-pass output metadata reference
- source/material/unit/group/set identifiers when present in existing metadata
- warning/error/caveat flags when present

If a required trace field is absent for an item that the operator wants to approve, the endpoint must block approval or record a non-approval decision. It must not invent trace references or silently approve untraceable output.

## Idempotency And Concurrency

Rules:

- `client_request_id` is required.
- repeated identical review submissions for the same session, plan, preview hash, pass, decision, and client request id must return the existing review record or fail closed in a deterministic way.
- conflicting review submissions for the same selected pass must fail closed unless a later freeze admits review amendment/supersession.
- the implementation must preserve the repo's existing transaction/locking patterns for session, plan, and pass state.
- no duplicate request may create package, handoff, execution, source-ingestion, or schema state.

## Failure Behavior

The endpoint must fail closed when:

- authority checks fail
- preview identity/hash is stale
- the pass is missing, foreign, non-selected, or non-terminal
- PR `#222` result/status authority is unavailable
- output metadata is absent or unreadable and the requested decision is `approved`
- trace requirements are unsatisfied for approved items
- supplied `analysis_run_id` does not match the selected pass
- `client_request_id` is missing
- duplicate or conflicting review state exists
- request payload asks for package, handoff, export, rerun, cancellation, recovery, source expansion, schema migration, runtime DB write, output rewrite, or UI/full mockup activation

For terminal failed selected passes, the endpoint may only record `blocked`, `changes_requested`, or `rejected` if implementation explicitly proves this is useful and safe. It must not approve a failed selected pass by default.

## UI Boundary

If a later implementation changes `/review/layer3`, the UI may only expose:

- a result-review panel gated by `execution_result_status_available`
- selected terminal pass status
- raw output metadata reference
- bounded trace summary
- operator decision control for `approved`, `changes_requested`, `rejected`, or `blocked`
- operator notes/caveats
- disabled package/handoff indicators
- blocked states for stale preview, missing output metadata, unresolved trace, duplicate conflict, unsupported source breadth, or authority mismatch

The UI must not show:

- package variant tabs
- package review controls
- handoff/export controls
- rerun, retry, cancel, or recovery controls
- editable raw findings or output-file rewrite controls
- RAG/vector retrieval controls
- qualitative/hybrid execution controls
- broad source-picker controls

Browser proof must include both headed and headless Chrome when rendered UI behavior changes.

## Tests Required Before Merge

Implementation tests must cover:

- successful approval review for a completed selected pass with readable output metadata and trace
- successful non-approval review for changes requested/rejected/blocked
- stale approved-plan preview id/hash fails closed
- missing result/status authority fails closed
- missing execution-start metadata fails closed unless already handled by result/status as terminal failure metadata
- missing output metadata cannot be approved
- unreadable or malformed output metadata cannot be approved
- unresolved trace blocks approval
- non-terminal selected pass fails closed
- foreign-session or foreign-plan pass fails closed
- missing `client_request_id` fails closed
- duplicate identical request behavior is deterministic
- conflicting duplicate request fails closed
- forbidden package/handoff/rerun/source/schema/runtime/output-rewrite fields fail closed
- no new `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, `L3OutputPackage`, `L3ReconciliationRecord`, package, handoff, runtime snapshot DB, or schema state is created
- package review and handoff remain disabled in response/session summary posture
- all relevant Layer 3 focused backend tests pass
- headed and headless browser proof if UI changes

## Still Deferred

Still deferred after this contract:

- complete output taxonomy beyond the minimal review projection
- package construction
- package variant review
- `canonical_internal`, `user_facing`, `review_facing`, and APS handoff package UI
- handoff/export trigger policy
- review amendment or supersession
- rerun, retry, cancellation, or recovery workflows
- approved-plan correction or supersession
- source-breadth expansion
- local upload or local-directory ingestion
- qualitative/hybrid/RAG/vector execution
- broad UI/full mockup activation
