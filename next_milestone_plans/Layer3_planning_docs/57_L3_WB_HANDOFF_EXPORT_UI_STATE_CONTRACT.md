# Layer 3 Workbench Handoff Export UI State Contract

Status: planning-only UI/state companion for `56_L3_WB_HANDOFF_EXPORT_UI_FREEZE.md`.

This document defines the state, data, control, request, and proof contract for a future bounded `/review/layer3` handoff/export preparation presentation slice. It does not make UI behavior live by itself and does not admit new backend behavior, APS handoff, external export, downstream dispatch, physical export artifact creation, `AnalysisArtifact` creation, package payload mutation, package reconstruction, execution selection/start UI expansion, source expansion, schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Authority Order

The UI must use this authority order:

1. durable `L3Session` state returned by `GET /api/v1/layer3/session/{session_id}`
2. approved `L3AnalysisPlan` identity and approved preview id/hash from server state
3. selected `L3PassRun` identity, terminal status, and result/status authority from server state
4. approved selected-pass result-review state from server state
5. package-review preview basis from server state
6. package-construction commit state from server state
7. stored package ids, package kinds, payload refs, payload hashes, and reconciliation record id from server state
8. package-review submit state from server state
9. handoff/export preparation summary from server state
10. handoff/export preparation endpoint response from server state
11. browser state as display/cache and in-flight-submit guard only
12. operator input as preparation intent only

The UI must not treat local component state, disabled step chips, URL fragments, DOM attributes, typed ids, cached prior responses, or package-review approval labels as authority to prepare, export, hand off, dispatch, mutate, rebuild, rerun, recover, or rewrite output.

## UI State Model

A future bounded UI implementation may introduce only these UI-visible states:

| UI state | Authority source | Enabled controls | Disabled downstream controls |
| --- | --- | --- | --- |
| `handoff_export_ui_unavailable` | no session, no approved plan, no selected terminal pass, missing result-review/package authority, or missing package-review submit state | none | preparation, APS handoff, external export, dispatch |
| `handoff_export_ui_waiting_for_package_review` | package construction exists but package-review submit is absent or not `package_review_approved` | inspect package-review state only | preparation, APS handoff, external export, dispatch |
| `handoff_export_ui_ready` | server summary reports `handoff_export_prepare.available == true` over `package_review_approved` state | submit one preparation decision | APS handoff, external export, dispatch, package edit/rebuild |
| `handoff_export_ui_recording` | one preparation submission is in flight | none beyond browser-local in-flight guard | duplicate submit, APS handoff, external export, dispatch |
| `handoff_export_ui_prepared` | server recorded `handoff_export_prepared` | inspect reference-only envelope | conflicting decision, APS handoff, external export, dispatch, package edit/rebuild |
| `handoff_export_ui_held` | server recorded `handoff_export_held` | inspect decision | conflicting decision, APS handoff, external export, dispatch |
| `handoff_export_ui_declined` | server recorded `handoff_export_declined` | inspect decision | conflicting decision, APS handoff, external export, dispatch |
| `handoff_export_ui_blocked` | server recorded or returned blocked/unavailable handoff/export state | inspect block reason and upstream next action | preparation submit unless server later marks ready, APS handoff, external export, dispatch |

UI state names are presentation labels. The server's `handoff_export_*` states remain authoritative.

## Required Data Projection

The UI may display only data supplied by server summary or prepare endpoint responses:

| Field | Use | Requirement |
| --- | --- | --- |
| `session_id` | session identity | must come from current workbench session/server summary |
| `analysis_plan_id` | approved-plan identity | must match server-approved plan |
| `pass_run_id` | selected pass identity | must come from server-selected pass state |
| `preview_id` | preview identity | must match server-approved preview and endpoint payload |
| `preview_hash` | preview authority | must match server-approved preview and endpoint payload |
| `result_review_record_ref` | result-review authority | server summary or handoff/export prepare summary only |
| `package_review_preview_hash` | package-preview authority | server summary or handoff/export prepare summary only |
| `reconciliation_record_id` | package-set anchor | server summary or handoff/export prepare summary only |
| `output_package_ids` | package row identity | server summary or handoff/export prepare summary only |
| `package_kinds` | package type proof | must be server supplied and limited to `canonical_internal`, `user_facing`, and `review_facing` |
| `payload_refs` | package payload references | display only; no browser-side dereference or rewrite |
| `payload_hashes` | package immutability proof | display only; no browser-side hash rewrite |
| `package_review_submit_record_ref` | package-review approval authority | server summary or handoff/export prepare summary only |
| `package_review_state` | submit state | must equal `package_review_approved` before enabling preparation |
| `operator_decision` | intent/result | operator input before submit, server response after submit |
| `decision_notes` | operator rationale | required for `hold`, `decline`, and `blocked` |
| `handoff_export_state` | recorded preparation posture | server response/session summary only |
| `handoff_target` | target boundary | fixed display/request value `internal_export_envelope` |
| `export_mode` | mode boundary | fixed display/request value `prepare_only` |
| `external_handoff_enabled` | downstream flag | must render false/disabled |
| `external_export_enabled` | downstream flag | must render false/disabled |
| `dispatch_enabled` | downstream flag | must render false/disabled |
| `downstream_unavailable` | downstream boundary | must show `aps_handoff`, `external_export`, and `downstream_dispatch` when handoff/export prepare is active |
| `handoff_export_envelope` | reference-only summary | display only when returned by server; must not include payload bodies or external artifacts |

Any field missing from server state must be rendered as unavailable or unknown. The UI must not infer missing authority fields from labels, row order, local arrays, package cards, or previous sessions.

## Control Contract

A future bounded UI implementation may expose:

- a handoff/export preparation readiness panel driven by server summary
- a read-only package-review approval evidence summary
- a decision selector with `authorize_prepare`, `hold`, `decline`, and `blocked`
- a decision-notes input that is required for `hold`, `decline`, and `blocked`
- one submit preparation action gated by server authority
- a read-only recorded-decision display
- a reference-only envelope summary after `authorize_prepare`
- disabled APS handoff, external export, and downstream dispatch indicators

The UI must not expose:

- APS handoff buttons
- external export or download buttons
- downstream destination selectors
- connector-run selectors or dispatch controls
- package payload editors
- package rebuild or reconstruction controls
- editable package variant tabs
- package payload body viewers for preparation
- rerun, retry, recovery, cancel, or replay controls
- execution selection/start controls
- source-expansion pickers
- local upload or directory selectors
- raw output editing or rewrite controls
- schema/runtime write toggles
- qualitative/hybrid/RAG/vector controls

## Request Construction

When submitting handoff/export preparation, the UI may include only fields admitted by docs `54`/`55` and current backend behavior:

- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `result_review_record_ref`
- `package_review_preview_hash`
- `reconciliation_record_id`
- `output_package_ids`
- `payload_hashes`
- `package_review_submit_record_ref`
- `package_review_state`
- `handoff_target`
- `export_mode`
- `operator_decision`
- `client_request_id`
- `decision_notes` when supplied or required
- `analysis_run_id` only when server state exposes it
- `expected_package_kinds` only if the backend contract admits it and the value is exactly the expected package-kind set

The UI must never submit:

- `aps_handoff`
- `dispatch`
- `send`
- `external_export`
- `external_target`
- `download`
- `connector_run_id`
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

## Display Contract

The handoff/export preparation panel must display:

- current package-review submit state
- whether handoff/export preparation is unavailable, ready, prepared, held, declined, or blocked
- server-provided package-review submit record ref
- server-provided result-review record ref and package-review preview hash
- server-provided reconciliation record id
- package ids, kinds, payload refs, and payload hashes
- fixed `internal_export_envelope` target and `prepare_only` mode
- current operator decision when recorded
- reference-only envelope metadata when returned by the server
- external handoff/export/dispatch disabled posture
- backend block/error reason when the server fails closed

The panel must avoid:

- implying package-review approval automatically prepares, exports, or dispatches anything
- implying a prepared envelope is a downloadable artifact
- implying package payload bodies are copied or editable
- implying APS ids, connector-run ids, external artifact refs, or downstream destination refs exist
- hiding downstream unavailable posture after preparation, hold, decline, or block

## Idempotency And Concurrency

The UI must:

- generate one `client_request_id` for each operator submit attempt
- prevent duplicate in-flight submissions from the same browser interaction
- render exact idempotent replay responses as server truth
- treat conflicting replay or already-recorded responses as blocked or unavailable
- avoid offering amendment/supersession controls after a preparation decision is recorded

Browser-side in-flight locking is only a usability guard. It is not the authority boundary.

## Failure Behavior

The UI must show a blocked/unavailable state when:

- session summary cannot be loaded
- approved plan or preview identity is missing
- selected terminal pass or result/status authority is missing
- approved result-review authority is missing
- package-review preview or package-construction state is missing
- package-review submit state is missing or not `package_review_approved`
- package ids, kinds, payload refs, payload hashes, result-review record ref, package-review preview hash, reconciliation id, or submit ref are missing from server state
- a handoff/export preparation decision is already recorded
- server returns duplicate/conflict/stale-authority errors
- request payload is rejected as non-admitted
- package edit/rebuild, APS handoff, external export, dispatch, rerun, recovery, source, schema, runtime, artifact, or full mockup behavior is requested

For any server error, the UI must preserve the existing session and panel state unless the server returns newer authoritative state. It must not clear authority fields and replace them with guessed local values.

## Styling And Layout Boundary

The implementation should extend the existing Layer 3 workbench visual language instead of introducing a separate dashboard. The handoff/export preparation panel should sit downstream of the package-review panel, with stepper/chip state reflecting server summary only. Existing disabled handoff/export indicators may be updated only to communicate availability accurately; they must not become broad dispatch, destination, or download controls.

The panel must be usable on the same desktop and mobile breakpoints as the current workbench page. Text must not overflow buttons/cards, controls must not shift layout on state changes, and disabled downstream controls must remain visibly distinct from the active prepare-only control.

## Tests Required Before Merge

Implementation tests must cover:

- no handoff/export preparation controls before a session exists
- no handoff/export preparation controls before package-review submit approval
- blocked/unavailable presentation for non-approved package-review submit states
- controls enabled only after server-authoritative `handoff_export_prepare.available == true`
- decision notes required for `hold`, `decline`, and `blocked`
- request payload contains only admitted fields
- forbidden APS handoff, external export, dispatch, package mutation, rerun, source, schema, runtime, artifact, and full mockup fields are absent from requests
- successful `authorize_prepare`, `hold`, `decline`, and `blocked` responses render server state and keep downstream actions disabled
- reference-only envelope display contains no payload bodies, downloads, downstream APS ids, connector-run ids, editable payloads, or rewritten content
- already-recorded preparation state renders as read-only
- duplicate/conflict response renders blocked/unavailable state
- existing package-review UI and backend handoff/export prepare fail-closed tests still pass
- both headed and headless Chrome browser proof pass because rendered UI behavior changes

## Relationship To Backend Contracts

This contract depends on:

- `54_L3_WB_HANDOFF_EXPORT_FREEZE.md`
- `55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md`
- `52_L3_WB_PACKAGE_REVIEW_SUBMIT_FREEZE.md`
- `53_L3_WB_PACKAGE_REVIEW_SUBMIT_API_AND_STATE_CONTRACT.md`
- `50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE.md`
- `51_L3_WB_PACKAGE_CONSTRUCTION_API_AND_STATE_CONTRACT.md`

If backend state is insufficient for the UI contract, add or revise a backend API/state freeze before implementation. Do not expand backend behavior through the UI implementation PR.
