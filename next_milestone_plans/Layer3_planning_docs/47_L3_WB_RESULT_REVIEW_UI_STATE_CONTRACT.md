# Layer 3 Workbench Result Review UI State Contract

Status: governing UI/state companion for `46_L3_WB_RESULT_REVIEW_UI_FREEZE.md`.

This document defines the state, data, control, and proof contract for a future bounded `/review/layer3` result-review presentation slice. It does not make UI behavior live by itself and does not admit new backend behavior, execution selection/start UI, package review, handoff/export, rerun/recovery, source expansion, schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Authority Order

The UI must use this authority order:

1. durable `L3Session` state returned by `GET /api/v1/layer3/session/{session_id}`
2. approved plan identity and approved preview id/hash from server state
3. execution-selection summary from server state
4. selected `L3PassRun` identity and status from server state
5. analysis-execution-start state from server state
6. result/status response for the selected terminal pass
7. result-review response or already-recorded result-review state from server state
8. browser state as display/cache only
9. operator input as review intent only

The UI must not treat local component state, disabled step chips, URL fragments, DOM attributes, typed pass ids, or cached prior responses as authority to review, approve, package, hand off, rerun, or recover output.

## UI State Model

The future UI implementation may introduce only these UI-visible states:

| UI state | Authority source | Enabled controls | Disabled downstream controls |
| --- | --- | --- | --- |
| `result_review_ui_unavailable` | no session, no approved plan, or no server-selected pass | none | execution start, results, review, package, handoff |
| `result_review_ui_waiting_for_selection` | session exists but execution selection is absent or not selected | status refresh only if existing API admits it; otherwise none | result review, package, handoff, rerun |
| `result_review_ui_waiting_for_execution_start` | selected pass exists but execution-start state is absent or not terminal | none | result review, package, handoff, rerun |
| `result_review_ui_status_available` | result/status response is available for one selected terminal pass | result review decision entry | package, handoff, rerun, source expansion |
| `result_review_ui_review_ready` | readable output metadata and trace posture are available | submit one bounded result-review decision | package, handoff, rerun, amendment |
| `result_review_ui_recording` | one result-review submission is in flight | none beyond in-flight cancellation of browser action | duplicate submit, package, handoff |
| `result_review_ui_recorded` | server has an existing review record | inspect review state | conflicting review, package, handoff, amendment |
| `result_review_ui_blocked` | server returned authority, status, output, trace, duplicate, or payload block | inspect block reason and upstream next action | result review submit, package, handoff, rerun |

UI state names are presentation labels. The server's `execution_result_*` states remain authoritative.

## Required Data Projection

The UI may display only data supplied by server summary/status/review responses or by already-rendered earlier workbench state:

| Field | Use | Requirement |
| --- | --- | --- |
| `session_id` | session identity | must come from current workbench session/server summary |
| `analysis_plan_id` | approved-plan identity | must match server-approved plan |
| `preview_id` | preview identity | must match approved preview and request payload |
| `preview_hash` | preview authority | must match approved preview and request payload |
| `pass_run_id` | selected pass identity | must come from server-selected pass state; no free-form operator entry |
| `analysis_run_id` | wrapped run identity | display/request only when server state exposes it |
| `pass_status` | terminal pass state | must come from selected pass or result/status response |
| `output_metadata_ref` | output reference | display only; no browser-side rewrite |
| `result_status_available` | review precondition | must be true before enabling review submission |
| `trace_summary` | audit basis | display summary; missing trace blocks approval when server says unresolved |
| `unresolved_trace_count` | block indicator | must be displayed when present and nonzero |
| `review_state` | recorded review posture | server response/session summary only |
| `operator_decision` | review intent/result | operator input before submit, server response after submit |
| `downstream_unavailable` | package/handoff boundary | must keep package/handoff unavailable |

Any field missing from server state must be rendered as unavailable or unknown. The UI must not infer missing authority fields from labels, row order, local arrays, or previous sessions.

## Control Contract

The future UI may expose:

- a result/status refresh or inspect action for the current selected terminal pass
- a result-review decision selector with `approved`, `changes_requested`, `rejected`, and `blocked`
- a bounded review-notes input
- a submit result-review action gated by server authority
- a read-only recorded-review display
- disabled package-review and handoff indicators

The future UI must not expose:

- pass-run id free text fields
- multi-pass checkboxes
- execution selection/start buttons
- package variant tabs
- package creation buttons
- handoff/export buttons
- rerun/retry/recovery/cancel buttons
- source-expansion pickers
- local upload or directory selectors
- raw output editing or rewrite controls
- qualitative/hybrid/RAG/vector controls

## Request Construction

When submitting result/status or result-review requests, the UI may include only fields already admitted by the backend contracts.

For result/status, the UI may submit only the selected-pass identity fields required by `42`/`43` and current backend behavior.

For result review, the UI may submit only:

- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `operator_decision`
- `client_request_id`
- `review_notes`
- `reviewed_output_items` when traceable references are present and bounded
- `analysis_run_id` when server state exposes it

The UI must never submit package, handoff, export, rerun, retry, recover, cancel, selected pass arrays, new analysis plan data, source expansion, local upload, local directory, schema migration, runtime DB write, artifact manifest, package variant, APS handoff, edited findings, or output rewrite fields.

## Display Contract

The result-review panel must display:

- the current selected pass identity or a clear unavailable state
- the approved plan and preview identity used for authority
- terminal pass status when known
- output metadata reference when known
- result/status availability
- trace summary and unresolved trace count when present
- current review state
- package-review unavailable posture
- handoff unavailable posture
- backend block/error reason when the server fails closed

The result-review panel must avoid:

- implying result review is available before server authority is available
- implying an approved review creates a package
- implying an approved review triggers APS handoff
- implying failed/missing-output/untraceable output can be approved
- hiding downstream unavailable posture after a successful review

## Idempotency And Concurrency

The UI must:

- generate one `client_request_id` for each operator submit attempt
- prevent duplicate in-flight submissions from the same browser interaction
- render an `already_recorded` or equivalent server response as server truth
- treat conflicting duplicate responses as blocked or unavailable
- avoid offering amendment/supersession controls after a review is recorded

Browser-side in-flight locking is only a usability guard. It is not the authority boundary.

## Failure Behavior

The UI must show a blocked/unavailable state when:

- session summary cannot be loaded
- approved plan or preview identity is missing
- execution selection is missing or inconsistent
- execution start is missing
- selected pass is not terminal
- result/status authority is missing
- output metadata is missing or unreadable
- trace requirements are unresolved
- result review is already recorded
- server returns duplicate/conflict
- request payload is rejected as non-admitted
- package/handoff/rerun/source/schema/runtime behavior is requested

For any server error, the UI must preserve the existing session and panel state unless the server returns a newer authoritative state. It must not clear authority fields and replace them with guessed local values.

## Styling And Layout Boundary

The implementation should extend the existing Layer 3 workbench visual language instead of introducing a separate dashboard. The result-review panel should be placed after the plan panel and before any package/handoff region, with the stepper reflecting server state. Existing disabled execution/results/package chips may be updated only to communicate availability accurately; they must not become broad execution or package controls.

The panel must be usable on the same desktop and mobile breakpoints as the current workbench page. Text must not overflow buttons/cards, controls must not shift layout on state changes, and disabled downstream controls must remain visibly distinct from active result-review controls.

## Tests Required Before Merge

Implementation tests must cover:

- no result-review controls before a session exists
- no result-review controls before approved plan and selected pass authority exist
- blocked result-review state when result/status is missing
- result-review controls enabled only after server-authoritative result/status availability
- request payload contains only admitted fields
- successful `approved`, `changes_requested`, `rejected`, or `blocked` review renders server response and keeps package/handoff unavailable
- already-recorded review state renders as read-only
- duplicate/conflict response renders blocked/unavailable state
- missing output metadata and unresolved trace block approval
- package/handoff/rerun/source/schema/runtime controls remain absent or disabled
- existing plan-preview, approval, and revision flows still render
- both headed and headless Chrome browser proof pass because rendered UI behavior changes

## Relationship To Backend Contracts

This contract depends on:

- `42_L3_WB_RESULT_STATUS_FREEZE.md`
- `43_L3_WB_RESULT_STATUS_API_AND_STATE_CONTRACT.md`
- `44_L3_WB_RESULT_REVIEW_FREEZE.md`
- `45_L3_WB_RESULT_REVIEW_API_AND_STATE_CONTRACT.md`

If backend state is insufficient for the UI contract, add or revise a backend API/state freeze before implementation. Do not expand backend behavior through the UI implementation PR.
