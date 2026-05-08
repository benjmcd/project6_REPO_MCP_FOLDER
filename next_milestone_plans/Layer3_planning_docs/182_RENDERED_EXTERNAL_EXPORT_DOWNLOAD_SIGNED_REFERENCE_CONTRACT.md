# Rendered External Export Download Signed Reference Contract

Status: planning/control UI and API contract for `181_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_FREEZE.md`.

This contract specifies the only rendered control proof currently selected for moving the raw mixed `/review/layer3` UI through same-origin signed-reference generation and use. It is not an implementation and admits no runtime behavior by itself.

## Contract Scope

Selected mode: `raw_mixed_rendered_external_export_download_signed_reference`.

The future implementation may only drive existing rendered operator controls for:

- `POST /api/v1/layer3/handoff/export/download/signed-reference/generate`
- `POST /api/v1/layer3/handoff/export/download/signed-reference/use`

It must reuse the existing backend contracts:

- generate request DTO `Layer3ExternalExportDownloadDeliveryRequest`
- generate response schema `layer3.external_export_download_signed_reference.v1`
- use request body with only `signed_reference_token`
- use response schema/header `layer3.external_export_download_signed_reference_use.v1`

It must not introduce a new route, DTO, service, model, migration, source adapter, ingestion path, package mutation path, connector dispatch path, provider URL path, RAG/vector path, hidden LLM path, full mockup path, public URL runtime, or auth/security behavior.

## Signed Reference Generate Request

The rendered signed-reference generate request must reuse the same server-backed delivery basis fields as same-origin delivery, including:

- `external_export_download_record_ref`;
- `export_download_descriptor_ref`;
- `external_export_download_state: external_export_download_prepared`;
- `delivery_mode: same_origin_artifact_stream`;
- `operator_decision: deliver_external_export_download`;
- APS bundle ref/id/schema/hash/size;
- package ids/kinds/refs/hashes;
- result-review, package-review, handoff/export, and APS handoff authority refs.

The browser must not include or infer deferred fields: `download_url`, `destination`, `destination_selector`, `connector_run_id`, `connector_dispatch`, `public_url`, `signed_url`, `signed_reference_token`, `provider_url`, `runtime_db_write`, `analysis_artifact`, `artifact_manifest`, `create_package`, `rebuild_package`, `package_payload`, `package_variant_content`, `rewrite_output`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, or `schema_migration`.

## Signed Reference Generate Response

Expected `layer3.external_export_download_signed_reference.v1` response evidence:

- `signed_reference_state: external_export_download_signed_reference_ready`;
- server-generated `signed_reference_token`, `signed_reference_token_id`, and `signed_reference_receipt_id`;
- `signed_reference_replay_policy: single_use`;
- `signed_reference_use_count: 0`;
- `signed_reference_max_use_count: 1`;
- `signed_reference_revoked: false`;
- `signed_reference_use_endpoint: /api/v1/layer3/handoff/export/download/signed-reference/use`;
- `delivery_mode: same_origin_signed_delivery_reference`;
- `server_authority: associated_cohort_external_export_download_signed_reference_gate`;
- `source_artifact_hash` and `source_artifact_size_bytes` match prepared APS bundle authority;
- `public_url_enabled`, `external_object_store_url_enabled`, `connector_dispatch_enabled`, `destination_selection_enabled`, `generic_downstream_dispatch_enabled`, `package_mutation_enabled`, and `schema_runtime_source_widening_enabled` are false;
- `authority_rail.token_authority: server_hmac_with_durable_state`;
- `authority_rail.durable_state_required: true`;
- `authority_rail.configured_secret_present: true`;
- no `download_url`, `download_token`, `public_url`, `signed_url`, or `connector_run_id`.

## Signed Reference Use Response

Expected use response evidence:

- request body contains only `signed_reference_token`;
- `x-layer3-schema-id` is `layer3.external_export_download_signed_reference_use.v1`;
- `x-layer3-delivery-state` is `external_export_download_delivered`;
- `x-layer3-signed-reference-state` is `external_export_download_signed_reference_delivered`;
- `x-layer3-signed-reference-token-id` matches the generated token id;
- `x-layer3-signed-reference-receipt-id` is present;
- `x-layer3-signed-reference-replay-policy` is `single_use`;
- `x-layer3-signed-reference-use-count` is `1`;
- `x-layer3-source-artifact-hash` matches prepared APS bundle authority;
- no `download_url`, `public_url`, or `signed_url` response header is present.

The rendered use control must disable after use because the token is single-use. Browser state may display the response, but there must be no frontend-only durable authority.

## Browser Proof Contract

The future browser proof must:

- drive raw mixed source materialization through approved API setup before opening `/review/layer3`;
- use only returned source IDs after materialization setup;
- drive rendered preflight, source preview, material preview, Gate B, Gate C, plan preview, approval, execution, result review, package review, handoff/export prepare, APS handoff dispatch, and external export/download prepare;
- drive only rendered signed-reference generation and use;
- assert one signed-reference generate request and one signed-reference use request;
- assert no direct `/handoff/export/download/deliver`, provider URL, connector/destination, package mutation, package replacement, or package supersession route;
- preserve no frontend-only durable authority.
