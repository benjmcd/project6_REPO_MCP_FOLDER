# Layer 3 Cohort Result Review UI State Contract

Status: planning-only UI/state companion for `84_COHORT_RESULT_REVIEW_UI_FREEZE.md`.

This document defines the state, data, control, request, and proof contract for a future bounded rendered `/review/layer3` selected-pass associated-cohort `descriptive_summary` result-review UI tranche. It does not make UI behavior live by itself and does not admit new backend behavior, package, handoff, export, connector, schema/runtime/source widening, retry/recovery, pass-entry changes, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Authority Order

The UI must use this authority order:

1. durable `L3Session` state returned by `GET /api/v1/layer3/session/{session_id}`
2. approved plan identity and approved preview id/hash from server state
3. server-selected `L3PassRun` identity, pass type, pass scope, and status
4. PR `#432` selected-pass associated-cohort execution-start/result-status server authority
5. result/status response for the selected terminal associated-cohort pass
6. PR `#438` result-review response or already-recorded result-review state
7. browser state as display/cache/in-flight state only
8. operator input as review intent only

The UI must not treat local component state, disabled step chips, URL fragments, DOM attributes, typed pass ids, cached prior responses, or row order as authority to review, approve, package, hand off, export, rerun, recover, or infer cohort provenance.

## UI State Model

The future UI implementation may introduce only these UI-visible states:

| UI state | Authority source | Enabled controls | Disabled downstream controls |
| --- | --- | --- | --- |
| `cohort_result_review_ui_unavailable` | no session, no approved plan, or no server-selected associated-cohort pass | none | result review, package, handoff, export, retry/recovery |
| `cohort_result_review_ui_waiting_for_execution` | selected associated-cohort pass exists but execution-start/result-status authority is absent or non-terminal | status refresh only when backend admits it | result review, package, handoff, export, retry/recovery |
| `cohort_result_review_ui_status_available` | result/status response is available for one selected terminal associated-cohort pass | review decision entry if trace/output gates are satisfied | package, handoff, export, retry/recovery |
| `cohort_result_review_ui_review_ready` | readable output metadata, source gate, cohort provenance, requested method provenance, and trace posture are available | submit one bounded result-review decision | package, handoff, export, retry/recovery, amendment |
| `cohort_result_review_ui_recording` | one result-review submission is in flight | none beyond browser-local in-flight guard | duplicate submit, package, handoff, export |
| `cohort_result_review_ui_recorded` | server has an existing review record | inspect review state | conflicting review, package, handoff, export, amendment |
| `cohort_result_review_ui_blocked` | server returned authority, status, output, trace, duplicate, conflict, or payload block | inspect block reason and upstream next action | result review submit, package, handoff, export, retry/recovery |

UI state names are presentation labels. Backend `execution_result_*` and session-summary states remain authoritative.

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
| `pass_type` | cohort admission indicator | must equal `associated_cohort` when displayed as available |
| `pass_scope` | selected cohort scope | must equal `quantitative_associated_cohort_dataset_version` when displayed as available |
| `selected_method_name` or `requested_method_name` | method authority | must be exactly `descriptive_summary` from server authority |
| `requested_method_source` | provenance display | must identify `analysis_set.formation_basis_json.requested_method_name` when supplied |
| `source_gate` | freeze/provenance display | must reflect `78_COHORT_FREEZE` when supplied by server state |
| `cohort_shape` | cohort basis display | must reflect `aligned_wide_table` when supplied |
| `source_dataset_version_ids` | source provenance | display only from server authority; no browser inference |
| `output_metadata_ref` | output reference | display only; no browser-side rewrite |
| `result_status_available` | review precondition | must be true before enabling review submission |
| `trace_summary` | audit basis | display summary; missing trace blocks approval when server says unresolved |
| `unresolved_trace_count` | block indicator | must be displayed when present and nonzero |
| `review_state` | recorded review posture | server response/session summary only |
| `operator_decision` | review intent/result | operator input before submit, server response after submit |
| `downstream_unavailable` | no-go boundary | must keep package/handoff/export unavailable |

Any field missing from server state must be rendered as unavailable or unknown. The UI must not infer missing authority fields from labels, local arrays, previous sessions, or visible text.

## Control Contract

The future UI may expose:

- a result/status refresh or inspect action for the current selected terminal associated-cohort pass
- a result-review decision selector with `approved`, `changes_requested`, `rejected`, and `blocked`
- a bounded review-notes input
- a submit result-review action gated by server authority
- a read-only recorded-review display
- disabled or unavailable package, handoff, export, connector, retry/recovery, and full mockup indicators

The future UI must not expose:

- pass-run id free text fields
- multi-pass checkboxes
- execution selection/start buttons
- package preview/commit/submit buttons for this associated-cohort path
- handoff/export/download buttons
- connector dispatch or destination controls
- rerun/retry/recovery/cancel buttons
- source-expansion pickers
- local upload or directory selectors
- raw output editing or rewrite controls
- qualitative/hybrid/RAG/vector controls

## Request Construction

When submitting result/status or result-review requests, the UI may include only fields already admitted by docs `82`/`83` and current backend behavior.

For result/status, the UI may submit only the selected-pass identity fields required by docs `80`/`81` and current backend behavior.

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

The UI must never submit package, handoff, export, connector, rerun, retry, recover, cancel, selected pass arrays, new analysis plan data, source expansion, local upload, local directory, schema migration, runtime DB write, artifact manifest, package variant, APS handoff, edited findings, output rewrite, method override, source gate override, source dataset-version override, or pass-entry mutation fields.

## Display Contract

The associated-cohort result-review panel must display:

- the current selected pass identity or a clear unavailable state
- the approved plan and preview identity used for authority
- pass type/scope/method/source-gate provenance when available
- source dataset-version ids and cohort shape when available
- terminal pass status when known
- output metadata reference when known
- result/status availability
- trace summary and unresolved trace count when present
- current review state
- package, handoff, export, connector, retry/recovery, and full mockup unavailable posture
- backend block/error reason when the server fails closed

The panel must avoid:

- implying associated-cohort result review is available before server authority is available
- implying an approved associated-cohort review creates a package
- implying an approved associated-cohort review triggers handoff/export
- implying failed, missing-output, malformed-provenance, or untraceable output can be approved
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
- selected associated-cohort pass state is missing or inconsistent
- execution start is missing
- selected pass is not terminal
- result/status authority is missing
- pass type/scope/method/source-gate/source dataset-version provenance is missing, malformed, or inconsistent
- output metadata is missing or unreadable
- trace requirements are unresolved
- result review is already recorded
- server returns duplicate/conflict
- request payload is rejected as non-admitted
- package/handoff/export/connector/rerun/retry/recovery/source/schema/runtime/pass-entry behavior is requested

For any server error, the UI must preserve the existing session and panel state unless the server returns a newer authoritative state. It must not clear authority fields and replace them with guessed local values.

## Styling And Layout Boundary

The implementation should extend the existing Layer 3 workbench visual language rather than introduce a separate dashboard. The associated-cohort result-review panel should sit in the existing result/review progression and clearly distinguish single-item result review from associated-cohort result review when both states are visible.

The panel must be usable on the same desktop and mobile breakpoints as the current workbench page. Text must not overflow buttons/cards, controls must not shift layout on state changes, and disabled downstream controls must remain visibly distinct from active result-review controls.

## Tests Required Before Merge

Implementation tests must cover:

- no associated-cohort result-review controls before a session exists
- no associated-cohort result-review controls before approved plan and selected pass authority exist
- blocked associated-cohort review state when result/status is missing
- associated-cohort review controls enabled only after server-authoritative result/status availability
- request payload contains only admitted fields
- successful `approved`, `changes_requested`, `rejected`, or `blocked` review renders server response and keeps package/handoff/export unavailable
- already-recorded associated-cohort review state renders as read-only
- duplicate/conflict response renders blocked/unavailable state
- missing output metadata, malformed provenance, and unresolved trace block approval
- package/handoff/export/connector/rerun/retry/recovery/source/schema/runtime/pass-entry controls remain absent or disabled
- existing single-item result-review UI still renders
- both headed and headless Chrome browser proof pass because rendered UI behavior changes

## Relationship To Backend Contracts

This contract depends on:

- `80_COHORT_EXECUTION_FREEZE.md`
- `81_COHORT_EXECUTION_CONTRACT.md`
- `82_COHORT_RESULT_REVIEW_FREEZE.md`
- `83_COHORT_RESULT_REVIEW_CONTRACT.md`
- `46_L3_WB_RESULT_REVIEW_UI_FREEZE.md`
- `47_L3_WB_RESULT_REVIEW_UI_STATE_CONTRACT.md`

If backend state is insufficient for the UI contract, add or revise a backend API/state freeze before implementation. Do not expand backend behavior through the UI implementation PR.
