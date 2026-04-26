# Layer 3 Workbench APS Handoff Dispatch UI State Contract

Status: planning-only UI/state companion for `60_L3_WB_APS_HANDOFF_DISPATCH_UI_FREEZE.md`.

This document defines the state, data, control, request, response-display, idempotency, failure, and proof contract for a future bounded `/review/layer3` APS handoff dispatch presentation slice. It does not make UI behavior live by itself and does not admit new backend behavior, external export/download, generic downstream dispatch, connector dispatch, destination selection, package payload mutation/reconstruction, execution selection/start UI expansion, source expansion, schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Authority Order

The UI must use this authority order:

1. durable `L3Session` state returned by `GET /api/v1/layer3/session/{session_id}`
2. approved `L3AnalysisPlan` identity and approved preview id/hash from server state
3. selected `L3PassRun` identity, terminal status, and result/status authority from server state
4. approved selected-pass result-review state from server state
5. package-review preview basis from server state
6. package-construction commit state from server state
7. package-review submit state from server state
8. handoff/export prepare summary from server state
9. APS handoff dispatch summary from server state
10. APS handoff dispatch endpoint response from server state
11. browser state as display/cache and in-flight-submit guard only
12. operator input as dispatch intent only

The UI must not treat local component state, disabled step chips, URL fragments, DOM attributes, typed ids, cached prior responses, or prepared-state labels as authority to dispatch, export, download, mutate, rebuild, rerun, recover, or rewrite output.

## UI State Model

A future bounded UI implementation may introduce only these UI-visible states:

| UI state | Authority source | Enabled controls | Disabled downstream controls |
| --- | --- | --- | --- |
| `aps_handoff_ui_unavailable` | no session, no approved plan, no selected terminal pass, missing result-review/package/prepare authority, or no APS dispatch summary | none | APS dispatch, external export/download, connector dispatch, destination selection |
| `aps_handoff_ui_waiting_for_prepare` | package-review submit exists but handoff/export prepare is absent or not `handoff_export_prepared` | inspect upstream state only | APS dispatch, external export/download, connector dispatch |
| `aps_handoff_ui_ready` | server summary reports `aps_handoff_dispatch.available == true` | submit one `dispatch_aps_handoff` decision | external export/download, connector dispatch, non-APS dispatch, package edit/rebuild |
| `aps_handoff_ui_dispatching` | one APS dispatch submission is in flight | none beyond browser-local in-flight guard | duplicate submit, external export/download, connector dispatch |
| `aps_handoff_ui_dispatched` | server recorded `aps_handoff_dispatched` | inspect APS output refs | conflicting dispatch, external export/download, connector dispatch, package edit/rebuild |
| `aps_handoff_ui_blocked` | server recorded or returned `aps_handoff_blocked` | inspect block reason and upstream next action | APS submit unless server later marks ready, external export/download, connector dispatch |
| `aps_handoff_ui_conflict` | server recorded or returned `aps_handoff_conflict` | inspect conflict reason and server state | duplicate/conflicting dispatch, external export/download, connector dispatch |
| `aps_handoff_ui_error` | request failed without newer server state | inspect error and refresh | local retry only after refresh if server still marks ready |

UI state names are presentation labels. The server's `aps_handoff_*` states remain authoritative.

## Required Data Projection

The UI may display and submit only data supplied by server summary or APS dispatch endpoint responses:

| Field | Use | Requirement |
| --- | --- | --- |
| `session_id` | session identity | current workbench session/server summary |
| `analysis_plan_id` | approved-plan identity | must match server-approved plan |
| `pass_run_id` | selected pass identity | server-selected pass state |
| `preview_id` | preview identity | server-approved preview |
| `preview_hash` | preview authority | server-approved preview hash |
| `result_review_record_ref` | result-review authority | server summary/dispatch summary only |
| `package_review_preview_hash` | package-preview authority | server summary/dispatch summary only |
| `reconciliation_record_id` | package-set anchor | server summary/dispatch summary only |
| `output_package_ids` | package row identity | server summary/dispatch summary only |
| `package_kinds` | package type proof | server supplied; must match expected source package kinds |
| `payload_refs` | package payload references | display/submit as refs only; no browser-side dereference or rewrite |
| `payload_hashes` | package immutability proof | display/submit as refs only; no browser-side hash rewrite |
| `package_review_submit_record_ref` | package-review approval authority | server summary/dispatch summary only |
| `package_review_state` | submit state | must equal `package_review_approved` before enabling dispatch |
| `prepare_record_ref` | prepare authority | server summary/dispatch summary only |
| `handoff_export_state` | prepare state | must equal `handoff_export_prepared` before enabling dispatch |
| `handoff_export_envelope_ref` | prepared-envelope ref | server summary/dispatch summary only |
| `handoff_target` | upstream handoff boundary | fixed display/request value `internal_export_envelope` |
| `export_mode` | upstream mode boundary | fixed display/request value `prepare_only` |
| `aps_handoff_target` | dispatch target boundary | fixed display/request value `aps_evidence_bundle` |
| `dispatch_mode` | dispatch mode boundary | fixed display/request value `server_side_aps_handoff` |
| `operator_decision` | intent/result | fixed request value `dispatch_aps_handoff`; server response after submit |
| `aps_handoff_state` | recorded APS dispatch posture | server response/session summary only |
| `aps_handoff_record_ref` | dispatch record ref | server response/session summary only |
| `aps_output_package_id` | APS output package row | server response/session summary only |
| `aps_output_package_kind` | APS output package kind | must be `aps_evidence_bundle_handoff` |
| `aps_bundle_ref` | APS bundle artifact ref | display only; no download URL inference |
| `aps_bundle_id` | APS bundle identity | server response/session summary only |
| `aps_schema_id` | APS bundle schema | server response/session summary only |
| `external_export_enabled` | downstream flag | must render false/disabled |
| `download_enabled` | downstream flag | must render false/disabled |
| `connector_dispatch_enabled` | downstream flag | must render false/disabled |
| `downstream_unavailable` | downstream boundary | must include external export, download, connector dispatch, and non-APS dispatch when APS dispatch is active |

Any field missing from server state must be rendered as unavailable or unknown. The UI must not infer missing authority fields from labels, row order, local arrays, package cards, or previous sessions.

## Control Contract

A future bounded UI implementation may expose:

- an APS handoff dispatch readiness panel driven by server summary
- a read-only prepared-envelope evidence summary
- a single dispatch submit button for `dispatch_aps_handoff`
- optional decision-notes input if the implementation chooses to display operator rationale, while preserving the backend request contract
- a read-only recorded-dispatch display
- reference-only APS output package and APS bundle metadata
- disabled external export/download, connector dispatch, non-APS dispatch, and destination indicators

The UI must not expose:

- external export or download buttons
- generic downstream dispatch buttons
- downstream destination selectors
- connector-run selectors or dispatch controls
- package payload editors
- package rebuild or reconstruction controls
- editable package variant tabs
- raw package payload body viewers for dispatch
- rerun, retry, recovery, cancel, or replay controls
- execution selection/start controls
- source-expansion pickers
- local upload or directory selectors
- raw output editing or rewrite controls
- schema/runtime write toggles
- qualitative/hybrid/RAG/vector controls

## Request Construction

When submitting APS handoff dispatch, the UI may include only fields admitted by docs `58`/`59` and current backend behavior:

- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `result_review_record_ref`
- `package_review_preview_hash`
- `reconciliation_record_id`
- `output_package_ids`
- `package_kinds`
- `payload_refs`
- `payload_hashes`
- `package_review_submit_record_ref`
- `package_review_state`
- `prepare_record_ref`
- `handoff_export_state`
- `handoff_export_envelope_ref`
- `handoff_target`
- `export_mode`
- `aps_handoff_target`
- `dispatch_mode`
- `operator_decision`
- `client_request_id`
- `decision_notes` when supplied
- `analysis_run_id` only when server state exposes it

The UI must never submit:

- `external_export`
- `external_target`
- `download`
- `download_url`
- `destination`
- `destination_selector`
- `connector_run_id`
- `connector_dispatch`
- `dispatch` as a generic field
- `send`
- `runtime_db_write`
- `analysis_artifact`
- `artifact_manifest`
- `create_package`
- `rebuild_package`
- `package_payload`
- `package_variant_content`
- `rewrite_output`
- `edited_findings`
- `result_review_amendment`
- `package_review_amendment`
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

## Response Display Contract

After successful dispatch, the UI must display:

- `aps_handoff_state`
- `aps_handoff_record_ref`
- `aps_output_package_id`
- `aps_output_package_kind`
- `aps_bundle_ref`
- `aps_bundle_id`
- `aps_schema_id`
- source package refs and hashes as reference-only evidence
- external export/download/connector dispatch disabled posture
- downstream unavailable entries
- next state

The UI must avoid:

- rendering `aps_bundle_ref` as a download URL unless a later freeze admits download behavior
- displaying raw APS bundle or package payload bodies
- implying connector-run ids, external destination refs, or generic downstream dispatch exist
- implying source package payloads were copied, edited, rebuilt, or superseded
- hiding downstream unavailable posture after dispatch

## Idempotency And Concurrency

The UI must:

- generate one `client_request_id` for each operator submit attempt
- prevent duplicate in-flight submissions from the same browser interaction
- render exact idempotent replay responses as server truth
- treat conflicting replay, duplicate dispatch, or stale authority as blocked/conflict state
- avoid offering amendment, supersession, rerun, retry, recover, or cancel controls after dispatch is recorded

Browser-side in-flight locking is only a usability guard. It is not the authority boundary.

## Failure Behavior

The UI must show blocked, conflict, unavailable, or error state when:

- session summary cannot be loaded
- approved plan or preview identity is missing
- selected terminal pass or result/status authority is missing
- approved result-review authority is missing
- package-review preview, package construction, or package-review submit state is missing
- package-review submit state is not `package_review_approved`
- handoff/export prepare state is missing or not `handoff_export_prepared`
- prepare ref or envelope ref is missing
- package ids, kinds, payload refs, payload hashes, result-review record ref, package-review preview hash, reconciliation id, submit ref, prepare ref, or envelope ref are missing from server state
- APS handoff dispatch summary is blocked or unavailable
- a dispatch decision is already recorded
- server returns duplicate/conflict/stale-authority errors
- request payload is rejected as non-admitted
- external export/download, connector dispatch, destination selection, package mutation, rerun, recovery, source, schema, runtime, artifact, or full mockup behavior is requested

For any server error, the UI must preserve the existing session and panel state unless the server returns newer authoritative state. It must not clear authority fields and replace them with guessed local values.

## Styling And Layout Boundary

The implementation should extend the existing Layer 3 workbench visual language instead of introducing a separate dashboard. The APS dispatch panel should sit downstream of handoff/export preparation, with stepper/chip state reflecting server summary only. Existing disabled downstream indicators may be updated only to communicate availability accurately; they must not become broad export, destination, download, or connector controls.

The panel must be usable on the same desktop and mobile breakpoints as the current workbench page. Text must not overflow buttons/cards, controls must not shift layout on state changes, and disabled downstream controls must remain visibly distinct from the active APS dispatch control.

## Tests Required Before Merge

Implementation tests must cover:

- no APS dispatch controls before a session exists
- no APS dispatch controls before `handoff_export_prepared`
- blocked/unavailable presentation for non-approved package-review submit and non-prepared handoff/export states
- controls enabled only after server-authoritative `aps_handoff_dispatch.available == true`
- request payload contains only admitted fields
- forbidden external export/download, connector, destination, package mutation, rerun, source, schema, runtime, artifact, and full mockup fields are absent from requests
- successful dispatch response renders server state and keeps downstream actions disabled
- reference-only APS output display contains no payload bodies, download URLs, connector-run ids, editable payloads, or rewritten content
- already-recorded dispatch state renders read-only
- duplicate/conflict response renders blocked/conflict state
- existing package-review UI, handoff/export prepare UI, and backend APS dispatch fail-closed tests still pass
- both headed and headless Chrome browser proof pass because rendered UI behavior changes

## Relationship To Backend Contracts

This contract depends on:

- `58_L3_WB_APS_HANDOFF_DISPATCH_FREEZE.md`
- `59_L3_WB_APS_HANDOFF_DISPATCH_API_AND_STATE_CONTRACT.md`
- `56_L3_WB_HANDOFF_EXPORT_UI_FREEZE.md`
- `57_L3_WB_HANDOFF_EXPORT_UI_STATE_CONTRACT.md`
- `54_L3_WB_HANDOFF_EXPORT_FREEZE.md`
- `55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md`

If backend state is insufficient for the UI contract, add or revise a backend API/state freeze before implementation. Do not expand backend behavior through the UI implementation PR.
