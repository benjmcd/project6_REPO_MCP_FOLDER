# Rendered External Export Download Signed Reference Proof

Status: live rendered browser proof for `raw_mixed_rendered_external_export_download_signed_reference`.

This document records the implementation proof selected by `181_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_FREEZE.md` and `182_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_CONTRACT.md`. It proves that the existing rendered `/review/layer3` workbench can continue from raw mixed rendered external export/download prepared authority through same-origin signed-reference generation and single-use delivery by using existing rendered controls and existing backend routes.

This pass changes no production backend route, DTO, service, model, migration, source handling, connector behavior, provider URL behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, or Layer 3 backend runtime behavior. It includes one narrow rendered UI hardening: after signed-reference use succeeds, `#external-export-download-signed-reference-use` stays disabled so the UI does not invite a backend replay-denied action for a single-use token.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- implementation branch: `codex/l3-rendered-signed-reference-proof`
- selected rendered external export/download mode: `raw_mixed_rendered_external_export_download_signed_reference`
- frozen governing docs: `181_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_FREEZE.md` and `182_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_CONTRACT.md`
- existing signed-reference generate route reused: `POST /api/v1/layer3/handoff/export/download/signed-reference/generate`
- existing signed-reference use route reused: `POST /api/v1/layer3/handoff/export/download/signed-reference/use`
- existing generate request DTO reused: `Layer3ExternalExportDownloadDeliveryRequest`
- existing generate response schema reused: `layer3.external_export_download_signed_reference.v1`
- existing use response schema/header reused: `layer3.external_export_download_signed_reference_use.v1`
- live UI shell: `backend/app/review_ui/static/layer3.html`
- live UI runtime: `backend/app/review_ui/static/layer3.js`
- browser proof: `e2e/layer3-workbench.spec.js`
- test-server secret source: `playwright.config.js` sets `LAYER3_SIGNED_REFERENCE_SECRET` for the review-browser server harness only

Live source, tests, routes, models, migrations, and checker behavior outrank this note.

## Live Proof Boundary

The focused browser proof is:

`Layer 3 workbench drives raw mixed rendered external export download signed reference`

The reusable proof helper is:

- `submitRenderedExternalExportDownloadSignedReference`

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
15. rendered external export/download signed-reference generation;
16. rendered external export/download signed-reference use.

It stops after the signed-reference use response records `external_export_download_signed_reference_delivered` in response headers and the rendered panel records delivered state. Direct same-origin attachment delivery, provider URL generation, connector/destination dispatch, package mutation, package replacement, and package supersession remain outside this proof.

## Request and Response Proof

The browser proof asserts that `/handoff/export/download/signed-reference/generate` receives only admitted JSON request fields, including the server-backed APS bundle identity, `aps_bundle_hash`, `aps_bundle_size_bytes`, `export_download_target: aps_evidence_bundle_download_reference`, `download_mode: reference_only_prepare`, `operator_decision: deliver_external_export_download`, `external_export_download_record_ref`, `export_download_descriptor_ref`, `external_export_download_state: external_export_download_prepared`, and `delivery_mode: same_origin_artifact_stream`.

The proof rejects deferred request fields such as `download_url`, `destination`, `destination_selector`, `connector_run_id`, `connector_dispatch`, `public_url`, `signed_url`, `signed_reference_token`, `provider_url`, `runtime_db_write`, `analysis_artifact`, `artifact_manifest`, `create_package`, `rebuild_package`, `package_payload`, `package_variant_content`, `rewrite_output`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, and `schema_migration`.

The signed-reference generation proof checks:

- `layer3.external_export_download_signed_reference.v1`;
- `external_export_download_signed_reference_ready`;
- server-generated `signed_reference_token`, `signed_reference_token_id`, and `signed_reference_receipt_id`;
- `single_use` replay policy;
- `signed_reference_use_count: 0`;
- `signed_reference_max_use_count: 1`;
- `signed_reference_revoked: false`;
- `same_origin_signed_delivery_reference`;
- `associated_cohort_external_export_download_signed_reference_gate`;
- source artifact hash and size matching prepared APS bundle authority;
- `server_hmac_with_durable_state`;
- durable state required;
- configured secret present;
- no `download_url`, `download_token`, `public_url`, `signed_url`, or `connector_run_id`.

The signed-reference use proof checks:

- request body is only `signed_reference_token`;
- `x-layer3-schema-id` response schema header `layer3.external_export_download_signed_reference_use.v1`;
- `x-layer3-delivery-state` response header `external_export_download_delivered`;
- `x-layer3-signed-reference-state` response header `external_export_download_signed_reference_delivered`;
- token id header matches the generated token id;
- receipt id header is present;
- replay policy header is `single_use`;
- use count header is `1`;
- source artifact hash header matches prepared APS bundle authority;
- no `download_url`, `public_url`, or `signed_url` response header is present.

## Rendered State Proof

The proof uses existing selectors only:

- `[data-operation-target="external-export-download-band"]`
- `#external-export-download-signed-reference-generate`
- `#external-export-download-signed-reference-use`
- `#external-export-download-signed-reference-panel`

It verifies `external_export_download_signed_reference_ui_ready` before generation, `external_export_download_signed_reference_ready` after generation, and `external_export_download_signed_reference_delivered` after use. It also verifies the use button is disabled before generation, enabled after generation, and disabled again after use.

The UI hardening is intentionally narrow: `canUseExternalExportDownloadSignedReference()` now requires that `State.externalExportDownloadSignedReferenceUse` is absent before enabling `#external-export-download-signed-reference-use`. This preserves the backend single-use replay policy in rendered affordances and does not create frontend-only durable authority.

The proof asserts no direct `/handoff/export/download/deliver`, `/package/mutation`, `/package/replacement`, `/package/supersession`, or `/handoff/connector` request is made.

## Theme and Browser Proof

The proof preserves the existing theme posture by passing through the upstream path:

- `light` around result/status and package preview;
- `dark` around execution/package construction;
- `workbench` around package-review submit, handoff/export prepare, APS handoff dispatch, external export/download prepare, signed-reference generation, and signed-reference use.

Because the Playwright harness uses fixed port `8031`, headed and headless proof runs must remain sequential unless a later freeze implements isolated ports/state.

## Negative Invariants

This proof admits no:

- production backend route, DTO, service, model, or migration change;
- new rendered UI control;
- source-family expansion beyond `dataset_version` and `aps_content_document`;
- source adapter registry behavior;
- local upload or local-directory ingestion;
- arbitrary local path input;
- web connector retrieval;
- RAG/vector retrieval or index creation;
- provider/public URL or signed public URL generation;
- real connector or destination dispatch;
- direct same-origin attachment delivery in this proof;
- broad package mutation or reconstruction;
- package replacement or package supersession;
- package payload rewrite outside the already-admitted package-construction commit behavior;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

There is no frontend-only durable authority.

## Next Boundary

The next pass must not assume provider URL, connector/destination dispatch, package mutation, package replacement, package supersession, broader source handling, RAG/vector retrieval, hidden LLM planning, full mockup activation, or auth/security behavior is proven for the raw mixed rendered path. Any deeper rendered downstream pass must first freeze the exact next rendered controls and then prove only that bounded slice.
