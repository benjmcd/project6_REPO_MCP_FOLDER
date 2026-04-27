# 69 L3 Workbench External Export Download Delivery UI State Contract

## Status

Planning-only UI state contract paired with doc 68. This document defines the state, request, response, and proof contract for a future rendered `/review/layer3` external export/download delivery control over the already-live backend/API delivery endpoint from PR #278.

This contract does not implement UI or runtime behavior. It does not admit public URLs, signed URLs, connector dispatch, destination selection, generic downstream dispatch, package mutation, schema/runtime/source widening, or full mockup activation.

## Authority Order

The future UI must use this authority order:

1. Server session summary and server response envelopes.
2. Stored package-review submit state.
3. Stored handoff/export prepare state.
4. Stored APS handoff dispatch state.
5. Stored external export/download readiness state.
6. Live PR #278 delivery endpoint response.
7. Browser display, in-flight, and last-attempt state.

Browser state is never authority for availability, identity, hash basis, stream authorization, conflict state, or downstream enablement.

## Active Server Gate

The delivery UI may render an enabled action only when the server summary proves:

- the Layer 3 session identity is current;
- selected/pass/result-review authority remains current;
- package construction authority remains current;
- package-review submit state is approved;
- handoff/export prepare state is prepared;
- APS handoff dispatch state is dispatched;
- external export/download readiness state is prepared;
- source package ids, package kinds, payload refs, and payload hashes still match the approved, dispatched, and readiness basis;
- `external_export_download_delivery.available == true` or the current backend/session-summary equivalent proves delivery availability;
- no server blocker requires public/signed URL, connector, destination, generic dispatch, package mutation, schema widening, or source expansion.

If any required server field is missing, stale, or unavailable, the UI must render the control disabled or unavailable and may not fabricate the missing basis.

## UI State Names

These are presentation states only. Server state names remain authoritative.

- `external_export_download_delivery_ui_unavailable`: upstream gate incomplete or server summary lacks required delivery basis.
- `external_export_download_delivery_ui_ready`: server reports delivery availability for the recorded descriptor.
- `external_export_download_delivery_ui_downloading`: one browser-local delivery request is in flight.
- `external_export_download_delivery_ui_completed`: same-origin response completed without client-side error.
- `external_export_download_delivery_ui_blocked`: backend returns a blocked or unavailable fail-closed response.
- `external_export_download_delivery_ui_conflict`: backend rejects the request as stale, duplicate-conflicting, or authority-mismatched.
- `external_export_download_delivery_ui_error`: backend returns a non-conflict error or the request cannot be completed.

The UI must not introduce state names that imply public URL generation, signed URL generation, connector dispatch, destination selection, or generic downstream dispatch.

## Rendered Data Contract

The future UI should render only reference-oriented state from the server, including:

- session identity;
- analysis plan identity;
- pass run identity;
- package-review submit record reference and approved state;
- handoff/export prepare record reference and prepared state;
- APS handoff dispatch record reference and dispatched state;
- external export/download readiness record reference and prepared state;
- source APS handoff package id and kind;
- source artifact reference, schema id, hash, and safe filename if returned by the server;
- delivery mode;
- downstream disabled flags and unavailable reasons;
- next-state guidance returned by the backend.

The UI must not render package payload bodies, editable package content, public URLs, signed URLs, local filesystem paths, destination ids, or connector-run identities.

## Action Contract

The UI may render exactly one active external export/download delivery action:

- `deliver_external_export_download`.

The action may be enabled only when the active server gate is satisfied. It must post to:

- `POST /api/v1/layer3/handoff/export/download/deliver`.

No other external export/download action is admitted by this UI contract.

## Request Construction Contract

The UI must construct the request from server-confirmed state plus a fresh browser-generated `client_request_id` for the delivery attempt.

The request must preserve the docs 66/67 backend contract and may include only backend-admitted fields such as:

- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `preview_id`;
- `preview_hash`;
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
- handoff export envelope reference;
- `handoff_target == internal_export_envelope`;
- `export_mode == prepare_only`;
- APS handoff dispatch record reference;
- `aps_handoff_state == aps_handoff_dispatched`;
- `aps_handoff_target == aps_evidence_bundle`;
- `dispatch_mode == server_side_aps_handoff`;
- APS output package id and kind;
- APS bundle reference, id, schema id, and hash if admitted;
- external export/download record reference;
- export download descriptor reference;
- `external_export_download_state == external_export_download_prepared`;
- `export_download_target == aps_evidence_bundle_download_reference`;
- `download_mode == reference_only_prepare`;
- `delivery_mode == same_origin_artifact_stream`;
- `operator_decision == deliver_external_export_download`;
- optional decision notes if admitted by the backend contract;
- `client_request_id`.

If current backend field names differ while remaining semantically equivalent, the future implementation must use the live backend names and document that mapping in the implementation PR.

## Forbidden Request Fields

The future UI must not send:

- `download_url`;
- `download_token`;
- `public_url`;
- `signed_url`;
- `local_file_path`;
- `external_target`;
- `destination`;
- `destination_selector`;
- `destination_id`;
- `connector_run_id`;
- `connector_dispatch`;
- `generic_dispatch`;
- `dispatch`;
- `send`;
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

If an attempted implementation needs any of those fields, stop and freeze a separate prerequisite instead.

## Response Handling Contract

The delivery endpoint is expected to return a same-origin attachment response on success. The UI may:

- initiate the request from an operator action;
- handle the binary response as a browser download;
- show non-authoritative completed/failed attempt status;
- refresh server summary after completion.

The UI must not:

- store the response body in workbench state;
- rewrite or inspect package payloads;
- create new artifacts;
- construct public or signed URLs from response headers;
- persist local filesystem paths;
- retry automatically without a fresh operator action and fresh `client_request_id`.

## Proof Requirements

A future implementation PR must prove:

- the active control appears only after server-authoritative delivery availability;
- unavailable and stale authority states render disabled and fail closed;
- the request contains only docs 66/67 admitted fields;
- forbidden fields are absent from the UI request;
- the browser receives the same-origin attachment response without any public or signed URL;
- connector dispatch, destination selection, generic downstream dispatch, package mutation, row creation, schema/runtime/source widening, and full mockup activation remain absent;
- existing delivery backend/API tests still pass;
- relevant page/static tests pass;
- Playwright proves both headed and headless Chromium behavior for ready, unavailable, and successful-download states.
