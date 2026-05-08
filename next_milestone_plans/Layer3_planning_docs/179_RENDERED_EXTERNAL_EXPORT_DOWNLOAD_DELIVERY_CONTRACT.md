# Rendered External Export Download Delivery Contract

Status: planning/control UI and API contract for `178_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md`.

This contract specifies the only future rendered control proof currently selected for moving the raw mixed `/review/layer3` UI past external export/download prepared authority. It is not an implementation and admits no runtime behavior by itself.

## Contract Scope

Selected mode: `raw_mixed_rendered_external_export_download_delivery`.

The future implementation may only drive existing rendered operator controls for:

- `POST /api/v1/layer3/handoff/export/download/deliver`

It must reuse the existing backend contract:

- request DTO `Layer3ExternalExportDownloadDeliveryRequest`
- delivery response schema/header `layer3.external_export_download_delivery.v1`

It must not introduce a new route, DTO, service, model, migration, source adapter, ingestion path, package mutation path, connector dispatch path, provider URL path, RAG/vector path, hidden LLM path, full mockup path, signed-reference runtime, or auth/security behavior.

## External Export Download Delivery Request

The rendered external export/download delivery request must be submitted as the existing browser-managed same-origin attachment form and assembled from server-backed external export/download prepare state:

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
- `aps_handoff_record_ref`: server-returned APS handoff dispatch ref;
- `aps_handoff_state`: `aps_handoff_dispatched`;
- `aps_handoff_target`: exactly `aps_evidence_bundle`;
- `dispatch_mode`: exactly `server_side_aps_handoff`;
- `aps_output_package_id`: server-returned APS output package id;
- `aps_output_package_kind`: exactly `aps_evidence_bundle_handoff`;
- `aps_bundle_ref`: server-returned APS bundle artifact ref;
- `aps_bundle_id`: server-returned APS bundle id;
- `aps_schema_id`: server-returned APS schema id;
- `aps_bundle_hash`: server-returned or server-derived APS bundle hash;
- `aps_bundle_size_bytes`: server-returned or server-derived APS bundle size;
- `export_download_target`: exactly `aps_evidence_bundle_download_reference`;
- `download_mode`: exactly `reference_only_prepare`;
- `operator_decision`: exactly `deliver_external_export_download`;
- `external_export_download_record_ref`: server-returned external export/download readiness ref;
- `export_download_descriptor_ref`: server-returned export/download descriptor ref;
- `external_export_download_state`: `external_export_download_prepared`;
- `delivery_mode`: exactly `same_origin_artifact_stream`.

The browser must not include or infer deferred fields: `download`, `download_url`, `delivery`, `destination`, `destination_selector`, `connector_run_id`, `connector_dispatch`, `dispatch`, `send`, `public_url`, `signed_url`, `signed_reference_token`, `provider_url`, `runtime_db_write`, `analysis_artifact`, `artifact_manifest`, `create_package`, `rebuild_package`, `package_payload`, `package_variant_content`, `rewrite_output`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, or `schema_migration`.

## External Export Download Delivery Response

Expected delivery response evidence:

- HTTP success from `POST /api/v1/layer3/handoff/export/download/deliver`;
- `content-disposition` contains `attachment`;
- `x-layer3-schema-id` is `layer3.external_export_download_delivery.v1`;
- `x-layer3-delivery-state` is `external_export_download_delivered`;
- `x-layer3-source-artifact-hash` matches the prepared APS bundle/source artifact hash;
- `x-layer3-external-export-download-record-ref` matches the server-returned external export/download readiness ref;
- no `download_url`, `public_url`, or `signed_url` response header is present.

The response is browser-managed same-origin attachment delivery. Browser state may record submitted/delivered UI state, but there must be no frontend-only durable authority.

## Browser Proof Contract

The future browser proof must:

- drive raw mixed source materialization through approved API setup before opening `/review/layer3`;
- use only returned source IDs after materialization setup;
- drive rendered preflight, source preview, material preview, Gate B, Gate C, plan preview, and plan approval;
- drive rendered execution selection and execution start through existing controls;
- inspect rendered result/status;
- submit rendered result review as `approved`;
- drive rendered package preview, package construction commit, package-review submit, handoff/export prepare, APS handoff dispatch, and external export/download prepare;
- drive only rendered external export/download delivery;
- assert one `/handoff/export/download/deliver` request and no signed-reference, provider URL, connector/destination, package mutation, package replacement, or package supersession route;
- preserve no frontend-only durable authority.
