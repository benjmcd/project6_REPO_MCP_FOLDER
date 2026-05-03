# Layer 3 Selected-Pass Cohort External Export Download Delivery UI Contract

## Status

Current-main planning/control contract paired with `100_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_FREEZE.md`.

This contract defines how PR `#487` intentionally settles associated-cohort delivery UI activation over the PR `#483` backend/API proof. It does not admit public URLs, signed URLs, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, schema/runtime/source widening, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

## Authority Order

The implemented UI uses this authority order:

1. server-stored Layer 3 session, approved plan, selected associated-cohort pass, result/status, result-review, package construction, package-review submit, handoff/export prepare, APS dispatch, and external export/download readiness state;
2. server summary or response field that explicitly admits associated-cohort rendered delivery activation;
3. existing PR `#483` backend/API delivery endpoint response;
4. existing generic `/review/layer3` delivery form and attachment-submission helper;
5. browser display, in-flight, and last-attempt state.

Browser state is never authority for delivery availability, identity, stream authorization, stale/conflict state, package mutation, downstream enablement, or URL generation.

## Active UI Gate

The rendered delivery control may be enabled only when all of these are true:

- server summary identifies the current session, approved plan, selected terminal pass, and result-review authority;
- `pass_type`, `pass_scope`, `method`, `source_gate`, `source_shape`, and `source_dataset_version_ids` match the associated-cohort contract;
- package-review submit state is `package_review_approved`;
- handoff/export state is `handoff_export_prepared`;
- APS handoff state is `aps_handoff_dispatched`;
- external export/download state is `external_export_download_prepared`;
- external export/download record ref and descriptor ref are present;
- APS output package kind is `aps_evidence_bundle_handoff`;
- APS bundle ref/id/schema/hash/size are present and server-derived;
- the server explicitly marks associated-cohort rendered delivery as available through `delivery_ui.available == true`, `delivery_ui.state == associated_cohort_external_export_download_delivery_ui_ready`, and `delivery_ui.server_authority == associated_cohort_external_export_download_delivery_ui_gate`;
- no downstream flag requires public/signed URL generation, connector dispatch, destination selection, generic dispatch, package mutation, schema/runtime/source widening, or broader UI activation.

If any field is missing, stale, ambiguous, or not explicitly server-admitted, the UI must render delivery unavailable. PR `#487` preserves `browser_download_enabled: false` and uses `delivery_ui` as the explicit replacement gate; if that object is absent or unavailable, the control stays disabled.

## State Vocabulary

UI states are presentation-only. PR `#487` makes the server `delivery_ui.state` associated-cohort-specific while preserving existing generic rendered delivery labels for shared ready/in-flight attempt presentation:

- `associated_cohort_external_export_download_delivery_ui_unavailable`;
- `associated_cohort_external_export_download_delivery_ui_ready`;
- `external_export_download_delivery_ui_ready`;
- `external_export_download_delivery_ui_downloading`;
- `associated_cohort_external_export_download_delivery_ui_downloading`;
- `associated_cohort_external_export_download_delivery_ui_submitted`;
- `associated_cohort_external_export_download_delivery_ui_completed`;
- `associated_cohort_external_export_download_delivery_ui_blocked`;
- `associated_cohort_external_export_download_delivery_ui_conflict`;
- `associated_cohort_external_export_download_delivery_ui_error`.

No UI state may imply public URL generation, signed URL generation, connector dispatch, destination selection, generic downstream dispatch, package mutation, durable delivery receipt creation, schema/runtime/source widening, or full mockup activation.

## Request Construction Contract

The UI may call only:

`POST /api/v1/layer3/handoff/export/download/deliver`

The request must be built from server-confirmed state plus a fresh browser-generated `client_request_id`. It may include only backend-admitted fields from docs `99` and current OpenAPI schema, including:

- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `preview_id`;
- `preview_hash`;
- result-review record ref;
- package-review preview hash;
- reconciliation record id;
- output package ids;
- package kinds;
- payload refs;
- payload hashes;
- package-review submit record ref and approved state;
- handoff/export prepare record ref and prepared state;
- handoff export envelope ref;
- APS handoff record ref and dispatched state;
- APS output package id and kind;
- APS bundle ref/id/schema/hash/size;
- external export/download record ref and descriptor ref;
- `external_export_download_state == external_export_download_prepared`;
- `export_download_target == aps_evidence_bundle_download_reference`;
- `download_mode == reference_only_prepare`;
- `delivery_mode == same_origin_artifact_stream`;
- `operator_decision == deliver_external_export_download`;
- optional `analysis_run_id` and decision notes only if server-admitted.

The UI must not send:

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
- amendments to result review, package review, handoff/export, APS handoff, or readiness;
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
- `schema_migration`;
- browser-inferred authority fields.

## Response Handling Contract

The UI may:

- submit one operator-initiated same-origin attachment request;
- let the browser handle the attachment response;
- display non-authoritative in-flight, submitted, completed, blocked, conflict, or error attempt status;
- refresh server summary after a completed or blocked attempt.

The UI must not:

- inspect, rewrite, store, or persist the downloaded body as workbench state;
- construct public or signed URLs from headers;
- persist local filesystem paths;
- create new artifacts or package payloads;
- retry automatically without a fresh operator action and fresh `client_request_id`;
- treat a browser-local completed state as durable server delivery state.

## Proof Requirements

PR `#487` proves:

- unavailable state when server delivery UI authority is absent, including the current `browser_download_enabled: false` case if no replacement gate is added;
- ready state only after exact associated-cohort server authority;
- request payload contains only admitted fields and includes a fresh `client_request_id`;
- forbidden fields are absent from the UI request;
- stale/mismatched readiness, APS dispatch, handoff/export prepare, package-review submit, package refs/hashes, APS package row, or APS bundle state renders unavailable and fails closed if submitted;
- successful response remains same-origin attachment delivery with no public/signed URL;
- no connector/destination/generic dispatch, package mutation, row creation, schema/runtime/source widening, or full mockup activation occurs;
- existing PR `#483` backend/API tests still pass;
- page/static tests cover the explicit server gate;
- headed and headless Chromium tests cover unavailable, ready, and same-origin attachment response behavior.
