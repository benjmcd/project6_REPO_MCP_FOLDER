# Rendered External Export Download Delivery Proof

Status: live test-only rendered browser proof for `raw_mixed_rendered_external_export_download_delivery`.

This document records the implementation proof selected by `178_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md` and `179_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONTRACT.md`. It proves that the existing rendered `/review/layer3` workbench can continue from raw mixed rendered external export/download prepared authority through same-origin browser-managed delivery by using existing rendered controls and the existing backend route.

This pass changes no production backend route, DTO, service, model, migration, rendered UI control, source handling, connector behavior, provider URL behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, signed-reference behavior, or Layer 3 runtime behavior.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- implementation branch: `codex/l3-rendered-download-delivery-proof`
- selected rendered external export/download mode: `raw_mixed_rendered_external_export_download_delivery`
- frozen governing docs: `178_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md` and `179_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONTRACT.md`
- existing external export/download route reused: `POST /api/v1/layer3/handoff/export/download/deliver`
- existing request DTO reused: `Layer3ExternalExportDownloadDeliveryRequest`
- existing delivery response schema/header reused: `layer3.external_export_download_delivery.v1`
- live UI shell: `backend/app/review_ui/static/layer3.html`
- live UI runtime: `backend/app/review_ui/static/layer3.js`
- browser proof: `e2e/layer3-workbench.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this note.

## Live Proof Boundary

The focused browser proof is:

`Layer 3 workbench drives raw mixed rendered external export download delivery`

The reusable proof helper is:

- `submitRenderedExternalExportDownloadDelivery`

The proof drives the already-live raw mixed rendered path through:

1. rendered raw mixed materialization;
2. rendered material preview;
3. rendered Gate B decision;
4. rendered Gate C preview and commit;
5. rendered plan preview and approval;
6. rendered execution selection and start;
7. rendered result/status inspection;
8. rendered approved result-review submit;
9. rendered package-review preview inspection;
10. rendered package construction commit;
11. rendered package-review submit;
12. rendered handoff/export prepare;
13. rendered APS handoff dispatch;
14. rendered external export/download prepare;
15. rendered external export/download delivery.

It stops after the same-origin delivery response records `external_export_download_delivered` in response headers and the rendered panel records browser-managed submitted/delivered state. Signed-reference generate/use, package mutation, package replacement, package supersession, provider URL generation, and connector/destination dispatch remain outside this proof.

## Request and Response Proof

The browser proof asserts that `/handoff/export/download/deliver` receives only admitted form request fields, including the server-backed APS bundle identity, `aps_bundle_hash`, `aps_bundle_size_bytes`, `export_download_target: aps_evidence_bundle_download_reference`, `download_mode: reference_only_prepare`, `operator_decision: deliver_external_export_download`, `external_export_download_record_ref`, `export_download_descriptor_ref`, `external_export_download_state: external_export_download_prepared`, and `delivery_mode: same_origin_artifact_stream`.

The proof rejects deferred request fields such as `download`, `download_url`, `delivery`, `destination`, `destination_selector`, `connector_run_id`, `connector_dispatch`, `dispatch`, `send`, `public_url`, `signed_url`, `signed_reference_token`, `provider_url`, `runtime_db_write`, `analysis_artifact`, `artifact_manifest`, `create_package`, `rebuild_package`, `package_payload`, `package_variant_content`, `rewrite_output`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, and `schema_migration`.

The response proof checks:

- successful same-origin delivery response;
- `x-layer3-schema-id` response schema header `layer3.external_export_download_delivery.v1`;
- `x-layer3-delivery-state` delivery state header `external_export_download_delivered`;
- response `content-disposition` contains `attachment`;
- `x-layer3-source-artifact-hash` source artifact hash header matches the prepared APS bundle/source artifact hash;
- external export/download record ref header matches the prepared readiness ref;
- no `download_url`, `public_url`, or `signed_url` response header is present.

The rendered UI proof checks that the delivery panel reaches browser-managed submitted/delivered state and displays the same server-returned external export/download record ref.

## Rendered State Proof

The proof uses existing selectors only:

- `[data-operation-target="external-export-download-band"]`
- `#external-export-download-delivery-submit`
- `#external-export-download-delivery-panel`

It verifies `external_export_download_delivery_ui_ready` before submit and `external_export_download_delivery_submitted` or `external_export_download_delivered` after submit. It does not click signed-reference controls, generate or use a signed reference, and it asserts no `/handoff/export/download/signed-reference`, `/package/mutation`, `/package/replacement`, `/package/supersession`, or `/handoff/connector` request is made.

The proof distinguishes rendered controls from frontend-only durable authority. The external export/download delivery action is driven only after server-authoritative result-review, package-preview, package-construction, package-review-submit, handoff/export prepare, APS handoff dispatch, and external export/download prepare responses. The operation dock and browser-managed attachment state are not treated as durable authority.

## Theme and Browser Proof

The proof preserves the existing theme posture by passing through the upstream path:

- `light` around result/status and package preview;
- `dark` around execution/package construction;
- `workbench` around package-review submit, handoff/export prepare, APS handoff dispatch, external export/download prepare, and external export/download delivery operation-dock navigation.

Because the Playwright harness uses fixed port `8031`, headed and headless proof runs must remain sequential unless a later freeze implements isolated ports/state.

## Negative Invariants

This proof admits no:

- production backend route, DTO, service, model, or migration change;
- rendered UI control change;
- source-family expansion beyond `dataset_version` and `aps_content_document`;
- source adapter registry behavior;
- local upload or local-directory ingestion;
- arbitrary local path input;
- web connector retrieval;
- RAG/vector retrieval or index creation;
- provider/public URL or signed public URL generation;
- real connector or destination dispatch;
- signed-reference generation or use;
- broad package mutation or reconstruction;
- package replacement or package supersession;
- package payload rewrite outside the already-admitted package-construction commit behavior;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

There is no frontend-only durable authority.

## Next Boundary

The next pass must not assume signed-reference generate/use, provider URL, connector/destination dispatch, package mutation, package replacement, or package supersession is proven for the raw mixed rendered path. Any deeper rendered downstream pass must first freeze the exact next rendered controls and then prove only that bounded slice.
