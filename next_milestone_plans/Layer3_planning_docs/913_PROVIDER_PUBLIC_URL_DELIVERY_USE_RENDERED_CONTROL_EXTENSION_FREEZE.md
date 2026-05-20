# Provider-Public URL Delivery/Use Rendered Control Extension Freeze

Freeze doc: `913_PROVIDER_PUBLIC_URL_DELIVERY_USE_RENDERED_CONTROL_EXTENSION_FREEZE.md`.

Status: provider-public URL delivery/use rendered control extension frozen for `provider_public_url_delivery_use_rendered_control_extension_freeze`.

Predecessor proof doc: `912_SOURCE_DIRECTORY_HYBRID_CONTEXT_PACKET_TO_OUTPUT_HANDOFF_RENDERED_STATUS_EXTENSION.md`.

Current-main checkpoint before this freeze: `6db5e44cbcc1c3e9a5c3b6c5a6ebf701de373efc`.

Freeze branch: `codex/l3-provider-public-use-rendered-freeze`.

Selected freeze mode: `single_existing_provider_public_use_rendered_control_extension_freeze`.

Selected target: `provider_public_url_delivery_use_rendered_control_extension`.

Selected implementation action after freeze sync: `implement_provider_public_url_delivery_use_rendered_control_extension_after_freeze_sync`.

## Why This Target

Doc 912 current-main synced the first post-readiness rendered extension over the source-directory hybrid context-packet-to-output-handoff lane. The next blocker-retirement pass should not jump to full mockup program activation because every critical mockup journey still lacks complete per-control route, state, durable authority, headed browser proof, headless browser proof, and security proof.

Repo inspection points to one narrow provider blocker target. Current main already exposes the bounded redacted provider-public URL delivery/use decision route, but the rendered workbench still blocks the corresponding operator control. The correct next pass is therefore to freeze a single rendered control extension over the existing use-decision route/state authority.

Grill-me challenge outcome: the first question was whether this should be full-program activation, provider-public raw URL delivery, public proxy behavior, or one rendered use-decision control. Source inspection answers it without user input: the backend route already exists and is covered by redaction/fail-closed tests, while `layer3.html`, `layer3.js`, `test_layer3_page.py`, and `e2e/layer3-workbench.spec.js` explicitly keep `#provider-public-url-use` and `#provider-public-url-deliver` absent. The adequate target is this single rendered use-decision control extension, not raw public URL delivery.

## Canonical Authority

Canonical source of truth remains current repo route/state behavior, not the mockup asset and not browser-local state:

- `POST /api/v1/layer3/handoff/export/download/provider-public-url/prepare`
- `GET /api/v1/layer3/handoff/export/download/provider-public-url/status/{provider_public_url_receipt_id}`
- `POST /api/v1/layer3/handoff/export/download/provider-public-url/revoke`
- `POST /api/v1/layer3/handoff/export/download/provider-public-url/use`
- `Layer3ProviderPublicUrlPrepareRequest`
- `Layer3ProviderPublicUrlPrepareResponse`
- `Layer3ProviderPublicUrlStatusResponse`
- `Layer3ProviderPublicUrlRevokeRequest`
- `Layer3ProviderPublicUrlRevokeResponse`
- `Layer3ProviderPublicUrlDeliveryUseRequest`
- `Layer3ProviderPublicUrlDeliveryUseResponse`
- `PROVIDER_PUBLIC_URL_DELIVERY_USE_SCHEMA_ID`
- `PROVIDER_PUBLIC_URL_DELIVERY_USE_MODE`
- `PROVIDER_PUBLIC_URL_DELIVERY_USE_OPERATOR_DECISION`
- `provider_public_url_delivery_use`
- `PROVIDER_PUBLIC_URL_REDACTED_MARKER`
- `L3ProviderPublicUrlReceipt`
- `L3ProviderPublicUrlObjectAuthority`
- `L3ProviderPublicUrlRevocation`

## Rendered Surface Contract

The follow-up implementation may add only a bounded use-decision control to the existing provider-public URL workbench surface:

- `/review/layer3 #provider-public-url-form`
- `/review/layer3 #provider-public-url-panel`
- existing `/review/layer3 #provider-public-url-prepare`
- existing `/review/layer3 #provider-public-url-status`
- existing `/review/layer3 #provider-public-url-revoke`
- future `/review/layer3 #provider-public-url-use`, only if it posts the bounded use-decision request to the existing server route

Permitted future request fields are limited to the existing API contract:

- `client_request_id`
- `provider_public_url_receipt_id`
- `expected_authority_hash`
- `expected_source_artifact_hash`
- `expected_source_artifact_size_bytes`
- `delivery_use_mode`
- `operator_decision`

The future rendered control must source its receipt and authority facts from server-returned provider-public prepare/status/revoke state already projected into the workbench. It must fail closed when no provider-public receipt is present, when the receipt is revoked, when expected hashes/sizes do not match, or when the server returns a denied decision.

## Future Implementation Proof Contract

The follow-up implementation must prove all of these before it can be considered complete:

1. Page-level static proof preserves the existing provider-public prepare/status/revoke bounded-control proof.
2. A focused page test proves the new rendered use control names only the existing provider-public use route and exact request/response fields.
3. Focused headless Chromium proof covers unavailable, available, allowed-use-decision, and revoked-or-denied states.
4. Focused headed Chromium proof covers the same states and reports no divergence from headless behavior.
5. Browser proof reports no console errors, no page errors, and no mobile overflow for the provider-public panel.
6. The rendered control never exposes raw provider/public URLs, provider credentials, object-store bucket/key/path, signed tokens, connector destinations, package payload bytes, browser supplied bytes, or browser-storage authority.
7. The implementation does not add `#provider-public-url-deliver`, public proxy access, byte streaming, public redirects, raw URL copy/display, provider network writes, or provider object writes.
8. The implementation does not create a new backend route, DTO, model, migration, or service behavior.
9. The implementation does not create durable use/audit rows beyond the existing receipt/authority/revocation state contract.
10. The implementation does not enable connector dispatch, destination write, package mutation, source expansion, RAG/vector/model/provider runtime, auth/security behavior expansion, frontend-only durable authority, or full mockup activation.

## Deferred Scope

Still blocked after this freeze:

- full mockup program activation
- mockup-frame write controls without complete route/state/proof contracts
- raw provider-public URL display or copy behavior
- provider-public deliver route or public proxy runtime
- byte streaming, public redirects, provider network writes, and provider object writes
- real connector/destination dispatch
- package mutation/reconstruction expansion
- broad source picker and caller path/directory/file-byte/URL/glob/recursive controls
- broad RAG/vector/hidden LLM/model/provider runtime
- optional-tool runtime
- auth/security behavior
- browser-storage authority and frontend-only durable authority

## Whole-Program Road Map

Immediate next pass after this freeze is synced to current main: implement `provider_public_url_delivery_use_rendered_control_extension` as one bounded rendered use-decision control over the existing provider-public prepare/status/revoke/use route chain.

Next proof pass: run page tests plus focused headless and headed Chromium proof for unavailable, available, allowed, denied, and revoked states, including no console/page errors, no mobile overflow, no forbidden route calls, and no sensitive authority leakage.

Next sync pass: merge the rendered extension only if checks and review surfaces are clean, then re-run post-merge JSON, checker, page, browser, and diff validation from current main.

Mid-term blocker retirement lanes: freeze and retire remaining source expansion, package mutation/reconstruction, connector/destination dispatch, public proxy/provider delivery, RAG/vector/model/provider runtime, browser-storage authority, optional-tool runtime, and auth/security as separate lanes with exact contracts.

Program readiness pass: rerun full mockup-to-live coverage/readiness after the rendered extension and blocker lanes are current-main synced; every critical mockup journey must be classified as live, read-only, excluded, or explicitly blocked.

Full activation freeze: only after the readiness pass is clean, create a dedicated full mockup program activation freeze naming every admitted route, state object, durable authority, DOM control, headed/headless browser proof, security proof, and no-go boundary.

Full activation implementation: implement only the controls admitted by the freeze, with server authority for every write/control and no frontend-only durable state.

Post-activation audit: prove all critical journeys from source intake through output review, package, handoff, export/download, provider/connector surfaces, and rendered mockup projection; then mark full mockup activation ready only if the entire route/state/browser/security contract passes.

## Explicit Non-Changes

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Backend behavior introduced by this freeze: `false`.

Route/API/DTO/model/migration/service behavior introduced by this freeze: `false`.

Executable test behavior introduced by this freeze: `false`.

Production UI behavior introduced by this freeze: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed by this freeze: `false`.

The next exact posture is `current_main_sync_provider_public_url_delivery_use_rendered_control_extension_freeze_then_implement_rendered_extension`.
