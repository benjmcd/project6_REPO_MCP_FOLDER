# Provider-Public URL Delivery/Use Rendered Control Extension

Proof doc: `914_PROVIDER_PUBLIC_URL_DELIVERY_USE_RENDERED_CONTROL_EXTENSION.md`.

Status: provider-public URL delivery/use rendered control extension implemented for `provider_public_url_delivery_use_rendered_control_extension`.

Predecessor freeze doc: `913_PROVIDER_PUBLIC_URL_DELIVERY_USE_RENDERED_CONTROL_EXTENSION_FREEZE.md`.

Current-main checkpoint before this implementation: `afe7bf8b513179736b7fe595002ecc710570403e`.

Implementation branch: `codex/l3-provider-public-use-rendered-control`.

Selected rendered target: `provider_public_url_delivery_use_rendered_control_extension`.

Selected rendered node: `/review/layer3 #provider-public-url-use`.

Selected static proof: `backend/tests/test_layer3_page.py::test_layer3_provider_public_url_use_rendered_control_is_bounded`.

Selected browser proof: `e2e/layer3-workbench.spec.js` test `Layer 3 workbench drives raw mixed rendered provider-private signed URL prepare status revoke and provider-public URL prepare status use revoke`.

## Implemented Scope

This pass implements the Doc 913 admitted rendered use-decision control on the existing provider-public URL workbench surface.

The implementation adds only:

- `data-rendered-extension="provider_public_url_delivery_use_rendered_control_extension"` on `/review/layer3 #provider-public-url-form`
- `/review/layer3 #provider-public-url-use`
- `State.providerPublicUrlUse`
- `canUseProviderPublicUrl`
- `providerPublicUrlUsePayload`
- `useProviderPublicUrlDecision`
- a rendered panel row for `/handoff/export/download/provider-public-url/use redacted_decision_only`

The rendered control posts only the existing bounded server contract:

- `client_request_id`
- `provider_public_url_receipt_id`
- `expected_authority_hash`
- `expected_source_artifact_hash`
- `expected_source_artifact_size_bytes`
- `delivery_use_mode`
- `operator_decision`

The control sources receipt and authority facts from server-returned provider-public prepare/status state, including `audit_receipt.authority_hash` for the optional expected authority hash. It is disabled until a provider-public receipt is prepared, disabled after the successful redacted use decision, and remains disabled after revocation.

## Canonical Authority

Canonical source of truth remains current repo route/state behavior, not the mockup asset and not browser-local state:

- `POST /api/v1/layer3/handoff/export/download/provider-public-url/prepare`
- `GET /api/v1/layer3/handoff/export/download/provider-public-url/status/{provider_public_url_receipt_id}`
- `POST /api/v1/layer3/handoff/export/download/provider-public-url/revoke`
- `POST /api/v1/layer3/handoff/export/download/provider-public-url/use`
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

## Proof Coverage

Static page proof verifies:

- the rendered extension marker exists
- `#provider-public-url-use` exists
- `#provider-public-url-deliver` remains absent
- the use payload sends only the admitted use-decision fields
- the use flow posts only `/handoff/export/download/provider-public-url/use`
- the use flow does not touch `localStorage` or `sessionStorage`

Browser proof verifies:

- the use control is present but disabled before provider-public prepare
- the use control is enabled after provider-public prepare/status returns server authority
- the use payload includes the fixed `fake_provider_redacted_use_decision` and `use_provider_public_url_redacted_fake_provider` values
- the use payload includes expected source hash, expected source size, and expected authority hash when available from `audit_receipt`
- the server response returns `layer3.provider_public_url.delivery_use.v1`
- the server response records `delivery_use_decision` as `allowed`
- raw public URL exposure remains false
- public URL, provider network, provider object write, public redirect, byte streaming, durable use row, audit row, provider credentials, connector dispatch, package mutation, source expansion, RAG/vector indexing, and frontend durable authority flags all remain false
- the use control is disabled again after the successful redacted use decision while revoke remains available
- the provider-public deliver route is not called
- provider-public browser storage keys remain absent

## Validation

- `node --check ./backend/app/review_ui/static/layer3.js` passed
- `python -m pytest ./backend/tests/test_layer3_page.py::test_layer3_page_route_serves_workbench_shell ./backend/tests/test_layer3_page.py::test_layer3_static_assets_are_mounted ./backend/tests/test_layer3_page.py::test_layer3_provider_public_url_use_rendered_control_is_bounded -q` passed with `3 passed, 3 warnings`
- `python -m pytest ./backend/tests/test_layer3_provider_public_url_delivery_use.py -q` passed with `9 passed, 3 warnings`
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "provider-public URL prepare status use revoke" --project=chromium` passed with `1 passed`
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "provider-public URL prepare status use revoke" --project=chromium --headed` passed with `1 passed`

Headless/headed comparison result: no behavioral divergence observed; both runs passed the same unavailable, prepared, allowed-use-decision, revoked, no-forbidden-route, and no-browser-storage proof path.

Focused headless Chromium proof and focused headed Chromium proof both passed against the same rendered use-decision control target.

## Explicit Behavior Classification

Runtime behavior introduced by this implementation: `false`.

Rendered behavior introduced by this implementation: `true`.

Backend behavior introduced by this implementation: `false`.

Route/API/DTO/model/migration/service behavior introduced by this implementation: `false`.

Executable test behavior introduced by this implementation: `true`.

Production UI behavior introduced by this implementation: `true`.

Server-authoritative full mockup activation introduced by this implementation: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed for full mockup activation by this implementation alone: `false`.

## Still Blocked

Still blocked after this implementation:

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

The next exact posture is `current_main_sync_provider_public_url_delivery_use_rendered_control_extension_then_select_next_blocker_retirement_lane`.
