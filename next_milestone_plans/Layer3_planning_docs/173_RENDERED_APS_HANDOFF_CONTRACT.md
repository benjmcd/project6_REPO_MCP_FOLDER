# Rendered APS Handoff Dispatch Contract

Status: planning/control UI and API contract for `172_RENDERED_APS_HANDOFF_FREEZE.md`.

This contract specifies the only future rendered control proof currently selected for moving the raw mixed `/review/layer3` UI past handoff/export prepared authority. It is not an implementation and admits no runtime behavior by itself.

## Contract Scope

Selected mode: `raw_mixed_rendered_aps_handoff_dispatch`.

The future implementation may only drive existing rendered operator controls for:

- `POST /api/v1/layer3/handoff/aps/dispatch`

It must reuse the existing backend contracts:

- request DTO `Layer3ApsHandoffDispatchRequest`
- response schema `Layer3ApsHandoffDispatchResponse`

It must not introduce a new route, DTO, service, model, migration, source adapter, ingestion path, package mutation path, connector dispatch path, provider URL path, RAG/vector path, hidden LLM path, full mockup path, external export/download runtime, or auth/security behavior.

## APS Handoff Dispatch Request

The rendered APS handoff dispatch request must be assembled from server-backed handoff/export prepare state:

- `client_request_id`: new browser-generated request id for this operator action;
- `session_id`: current server-created Layer 3 session id;
- `analysis_plan_id`: id returned by plan approval for the current session;
- `pass_run_id`: selected pass run returned by execution selection and started by execution start;
- `preview_id`: current approved plan preview id;
- `preview_hash`: current approved plan preview hash;
- `analysis_run_id`: id returned by execution start when the associated-cohort path admits it;
- `result_review_record_ref`: server-returned ref from an approved selected-pass result review;
- `package_review_preview_hash`: server-returned package review preview hash;
- `reconciliation_record_id`: server-returned package reconciliation id;
- `output_package_ids`: package ids returned by package construction/package submit;
- `package_kinds`: exactly `canonical_internal`, `user_facing`, and `review_facing`;
- `payload_refs`: payload refs returned by package construction/package submit;
- `payload_hashes`: payload hashes returned by package construction/package submit;
- `package_review_submit_record_ref`: server-returned package-review submit ref;
- `package_review_state`: `package_review_approved`;
- `prepare_record_ref`: server-returned handoff/export prepare ref;
- `handoff_export_state`: `handoff_export_prepared`;
- `handoff_export_envelope_ref`: server-returned handoff/export envelope ref;
- `handoff_target`: exactly `internal_export_envelope`;
- `export_mode`: exactly `prepare_only`;
- `aps_handoff_target`: exactly `aps_evidence_bundle`;
- `dispatch_mode`: exactly `server_side_aps_handoff`;
- `operator_decision`: exactly `dispatch_aps_handoff`;
- `decision_notes`: optional only.

The browser must not include or infer deferred fields: `external_export`, `external_target`, `download`, `download_url`, `destination`, `destination_selector`, `connector_run_id`, `connector_dispatch`, `dispatch`, `send`, `runtime_db_write`, `analysis_artifact`, `artifact_manifest`, `create_package`, `rebuild_package`, `package_payload`, `package_variant_content`, `rewrite_output`, `edited_findings`, `result_review_amendment`, `package_review_amendment`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, or `schema_migration`.

## APS Handoff Dispatch Response

Expected `Layer3ApsHandoffDispatchResponse` fields that the UI may consume:

- `schema_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_identity`
- `analysis_run_id`
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
- `decision_notes`
- `aps_handoff_state`
- `aps_handoff_record_ref`
- `aps_output_package_id`
- `aps_output_package_kind`
- `aps_bundle_ref`
- `aps_bundle_id`
- `aps_schema_id`
- `source_package_refs`
- `source_package_hashes`
- `external_export_enabled`
- `download_enabled`
- `connector_dispatch_enabled`
- `provider_public_url_enabled`
- `downstream_unavailable`
- `next_state`
- `authority_rail`

The response is authoritative for recorded APS handoff dispatch state. Browser state may display the response, but there must be no frontend-only durable authority.

## Rendered State Model

The future UI proof must use these phases:

- `not_ready`: no prepared handoff/export authority for the current session;
- `handoff_export_prepared_ready`: session summary exposes APS handoff readiness;
- `submitting`: request to `/handoff/aps/dispatch` is pending;
- `dispatched`: response supplies `aps_handoff_state: aps_handoff_dispatched`, `aps_handoff_record_ref`, and APS bundle refs;
- `next_ready`: the UI may surface external export/download readiness after dispatch, but the proof must not drive it;
- `blocked`: server error, stale preview, missing session, missing plan, missing selected pass run, missing result/status authority, missing approved result review, missing approved package review, missing reconciliation id, missing package ids/refs/hashes, missing handoff/export prepare ref, missing envelope ref, cancellation/recovery/rerun state, forbidden field, source expansion, package mutation, external export/download, or unsupported downstream scope.

The UI must preserve existing disabled state for external export/download delivery until external export/download prepare is separately proved. An error in APS dispatch must not unlock external export/download controls.

## Selector and Layout Contract

Future proof must use stable existing selectors:

- `[data-operation-target="aps-handoff-band"]`
- `#aps-handoff-dispatch-submit`
- `#aps-handoff-dispatch-panel`

The controls must remain keyboard focusable, visibly labeled, and readable in the existing APS handoff workband. They must not overlap result-review controls, package controls, handoff/export controls, external export/download controls, step chips, or mockup sections across desktop and mobile viewports.

## Browser Proof Contract

The future browser proof must:

- drive raw mixed source materialization through approved API setup before opening `/review/layer3`;
- use only returned source IDs after materialization setup;
- drive rendered preflight, source preview, material preview, Gate B, Gate C, plan preview, and plan approval;
- drive rendered execution selection and execution start through existing controls;
- inspect rendered result/status;
- submit rendered result review as `approved`;
- drive rendered package preview, package construction commit, and package-review submit;
- drive rendered handoff/export prepare;
- drive only rendered APS handoff dispatch;
- assert one `/handoff/aps/dispatch` request and no `/handoff/export/download`, provider URL, connector/destination, package mutation, package replacement, or package supersession route;
- preserve no frontend-only durable authority.
