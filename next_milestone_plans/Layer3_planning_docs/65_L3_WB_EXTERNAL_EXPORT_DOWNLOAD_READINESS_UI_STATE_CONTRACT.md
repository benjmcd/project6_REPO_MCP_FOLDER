# 65 L3 Workbench External Export Download Readiness UI State Contract

## Status

Planning-only UI state contract paired with doc 64. This document defines the state, request, response, and proof contract for a future rendered `/review/layer3` external export/download readiness UI over the already-live backend/API readiness endpoint from PR #269.

This contract does not implement UI or runtime behavior. It does not admit browser download delivery, public URLs, signed URLs, file streaming, connector dispatch, destination selection, generic downstream dispatch, package mutation, schema/runtime/source widening, or full mockup activation.

## Authority Order

The future UI must use this authority order:

1. Server session summary and server response envelopes.
2. Stored package-review submit state.
3. Stored handoff/export prepare state.
4. Stored APS handoff dispatch state.
5. Stored external export/download readiness state.
6. Browser display state and in-flight state.

Browser state is never authority for availability, identity, hash basis, recorded readiness, conflict state, or downstream enablement.

## Active Server Gate

The external export/download readiness UI may render an enabled action only when the server summary proves:

- the Layer 3 session identity is current;
- selected/pass/result-review authority remains current;
- package construction authority remains current;
- package-review submit state is approved;
- handoff/export prepare state is prepared;
- APS handoff dispatch state is dispatched;
- source package ids, package kinds, payload refs, and payload hashes still match the approved and dispatched basis;
- `external_export_download.available == true`;
- no existing external export/download readiness state already records a terminal or conflicting decision.

If any required server field is missing, stale, or unavailable, the UI must render the control disabled or unavailable and may not fabricate the missing basis.

## UI State Names

These are presentation states only. Server state names remain authoritative.

- `external_export_download_ui_unavailable`: upstream gate incomplete or server summary lacks required readiness basis.
- `external_export_download_ui_ready`: server reports `external_export_download.available == true` and no recorded readiness decision blocks submission.
- `external_export_download_ui_preparing`: one browser-local submit is in flight.
- `external_export_download_ui_prepared`: server response or refreshed summary records external export/download readiness.
- `external_export_download_ui_recorded`: existing recorded readiness is shown read-only.
- `external_export_download_ui_conflict`: backend rejects the request as stale, duplicate-conflicting, or authority-mismatched.
- `external_export_download_ui_error`: backend returns a non-conflict error or the request cannot be completed.

The UI must not introduce state names that imply a delivered browser download, generated URL, connector dispatch, destination selection, or generic downstream dispatch.

## Rendered Data Contract

The future UI should render only reference-oriented state from the server, including:

- session identity;
- analysis plan identity;
- pass run identity;
- package-review submit record reference and approved state;
- handoff/export prepare record reference and prepared state;
- APS handoff dispatch record reference and dispatched state;
- source APS handoff package id and kind;
- source artifact reference and hash;
- source payload refs and payload hashes;
- external export/download target and mode;
- external export/download readiness state;
- readiness record reference or descriptor reference, if recorded;
- downstream disabled flags and unavailable reasons;
- next-state guidance returned by the backend.

The UI must not render package payload bodies, editable package content, generated external file content, public URLs, signed URLs, or connector-run identities.

## Action Contract

The UI may render exactly one active external export/download readiness action:

- `prepare_external_export_download`.

The action may be enabled only when the active server gate is satisfied. It must post to:

- `POST /api/v1/layer3/handoff/export/download/prepare`.

No other external export/download action is admitted by this UI contract.

## Request Construction Contract

The UI must construct the request from server-confirmed state plus a fresh browser-generated `client_request_id` for the submit attempt.

The request must preserve the docs 62/63 backend contract and may include only backend-admitted fields such as:

- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- result-review record reference;
- package-review preview hash;
- reconciliation record id;
- output package ids;
- package kinds;
- payload refs;
- payload hashes;
- package-review submit record reference;
- `package_review_state == package_review_approved`;
- handoff/export prepare record reference;
- `handoff_export_state == handoff_export_prepared`;
- APS handoff dispatch record reference;
- `aps_handoff_state == aps_handoff_dispatched`;
- source APS handoff package id;
- source APS handoff package kind;
- source artifact reference;
- source artifact hash;
- `export_download_target`;
- `download_mode`;
- `operator_decision == prepare_external_export_download`;
- optional decision notes if admitted by the backend contract;
- `client_request_id`.

If current backend field names differ while remaining semantically equivalent, the future implementation must use the live backend names and document that mapping in the implementation PR.

## Forbidden Request Fields

The UI must not submit fields that imply behavior outside the readiness boundary, including:

- `download_url`;
- `public_url`;
- `signed_url`;
- `stream_file`;
- `browser_download`;
- `external_export`;
- `send`;
- `dispatch`;
- `generic_dispatch`;
- `connector_run_id`;
- `connector_dispatch`;
- `destination`;
- `destination_id`;
- `external_target`;
- `runtime_db_write`;
- `analysis_artifact`;
- `artifact_manifest`;
- `create_package`;
- `rebuild_package`;
- `package_payload`;
- `package_variant_content`;
- `rewrite_output`;
- `edited_findings`;
- `result_review_amendment`;
- `package_review_amendment`;
- `handoff_export_amendment`;
- `aps_handoff_amendment`;
- `rerun`;
- `retry`;
- `recover`;
- `cancel`;
- `selected_pass_ids`;
- `pass_run_ids`;
- `new_analysis_plan`;
- `plan_revision`;
- `source_expansion`;
- `local_upload`;
- `local_directory`;
- `schema_migration`.

The future UI may maintain local form state for display and in-flight prevention, but that local state must not become a request field unless it is admitted above or by the live backend contract.

## Response Display Contract

On success, conflict, or failure, the UI must render the server response as authority. The minimum displayed response set should include:

- status;
- session identity;
- pass and plan identity;
- source package identity;
- source artifact reference and hash;
- external export/download readiness state;
- readiness record reference;
- target and mode;
- downstream unavailable flags;
- next state;
- server error or conflict reason, if present.

The UI must preserve a read-only recorded state after success. A refreshed session summary that reports recorded readiness must disable the submit action.

## Idempotency And Concurrency Contract

The UI must generate one `client_request_id` per submit attempt and keep at most one in-flight request for this action.

The backend remains authoritative for idempotent replay and conflict handling. The UI must:

- allow an exact server-accepted response to render read-only after refresh;
- render duplicate or stale authority failures as conflicts or blocked states using backend response text;
- not attempt a browser-local retry with a mutated authority basis;
- not silently reissue the same `client_request_id` for a new decision.

## Downstream Disabled Contract

The UI must render these capabilities as disabled or unavailable:

- browser download;
- download URL;
- public URL;
- signed URL;
- file streaming;
- connector dispatch;
- connector-run handling;
- destination selection;
- generic downstream dispatch;
- external export delivery.

Disabled downstream items may be shown as a state explanation. They must not appear as active controls, hidden submit fields, menu choices, or route invocations.

## Layout And Interaction Boundaries

The external export/download readiness panel must be presented as a downstream continuation after APS handoff dispatch. It should reuse existing `/review/layer3` disabled-state, state-badge, response-envelope, and refresh patterns.

The future UI must avoid a parallel authority model. It may cache only:

- the current operator note field, if shown;
- the current in-flight state;
- the generated `client_request_id` for the active submit attempt;
- the latest displayed server response.

## Failure Rendering

The UI must render backend failures without widening behavior:

- missing upstream authority: disabled/unavailable state;
- stale package basis: conflict or blocked state;
- stale APS handoff dispatch basis: conflict or blocked state;
- existing recorded readiness: read-only recorded state;
- forbidden-field rejection: error state with server reason;
- network or unexpected server error: error state with retry left to a fresh operator action.

The UI must not respond to failures by trying alternate endpoints, reconstructing packages, changing source artifacts, changing dispatch state, or expanding source/runtime scope.

## Future Implementation Proof

A future implementation PR must include focused proof that:

- package-review submit, handoff/export prepare, and APS handoff dispatch UI behavior remains intact;
- the external export/download readiness panel is disabled before `external_export_download.available == true`;
- the readiness action is enabled only from server state;
- the request contains no forbidden fields;
- success records and renders read-only reference state;
- conflicting replay or stale authority renders a server-authoritative blocked/conflict state;
- disabled downstream capabilities remain disabled and do not submit requests.

Expected proof includes page/static tests, JavaScript syntax validation, focused Layer 3 API regression tests, and headed plus headless Chromium verification for `/review/layer3` when UI code is touched.
