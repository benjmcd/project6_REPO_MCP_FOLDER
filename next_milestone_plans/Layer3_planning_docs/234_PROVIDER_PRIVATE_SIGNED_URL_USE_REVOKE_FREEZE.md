# Provider Private Signed URL Revoke-Only Freeze

Status: current-main planning/control correction for `provider_private_signed_url_use_revoke_route_freeze`.

The filename is retained for milestone continuity, but this document corrects the admitted scope: the next provider-private signed URL runtime slice is revoke-only. The use route remains deferred because current prepare/status behavior returns only redacted provider-private URL/token material and durable receipt state stores token hash/prefix metadata rather than raw usable token material.

This pass is docs/proof/checker-only. It does not add routes, DTOs, services, models, migrations, executable backend tests, rendered UI controls, browser automation, provider credentials, provider network calls, provider object-store writes, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector behavior, full mockup activation, auth/security behavior, same-origin delivery changes, same-origin signed-reference changes, provider/public URL runtime, or public proxy URL runtime.

Implementation note: `239_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_API.md` records the backend/API-only revoke runtime that implements this corrected revoke-only boundary while keeping `use` deferred.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_revoke_only_freeze
entry_decision: revoke_route_frozen_runtime_blocked
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
upstream_runtime_status: prepare_status_backend_api_only_implemented
second_runtime_slice_candidate: revoke_backend_api_only
provider_private_signed_url_use_route: deferred_blocked_by_redacted_token_boundary
provider_private_signed_url_revoke_route: frozen_not_implemented
rendered_ui_change: false
provider_network_or_object_store_write: false
same_origin_delivery_semantics_changed: false
same_origin_signed_reference_semantics_changed: false
implementation_entry_allowed_next: true
```

## Current authority

Current main already has:

- durable provider-private receipt/object-authority/audit/revocation rows;
- `record_used_provider_private_signed_url_receipt(...)` in the state substrate;
- `revoke_provider_private_signed_url_receipt(...)` in the state substrate;
- backend/API prepare and read-only status routes;
- OpenAPI proof that provider-private use/revoke routes are not yet exposed;
- redacted prepare/status responses that do not expose raw provider-private URL/token material.

The critical correction is that state-substrate existence is not enough to admit the use route. `record_used_provider_private_signed_url_receipt(...)` requires a raw provider-private signed URL token for hash validation, while the live API intentionally redacts that token and does not retain raw usable token material durably. A client-callable use route therefore needs a separate token-delivery/use-authority freeze before implementation.

## Frozen second runtime slice

```yaml
allowed_routes:
  - POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/revoke
blocked_routes:
  - POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use
allowed_owner_service:
  - backend/app/services/layer3_provider_private_signed_url.py
allowed_existing_dependencies:
  - backend/app/services/layer3_provider_private_signed_url_state.py
allowed_api_surface:
  - backend/app/api/layer3.py
allowed_tests:
  - backend/tests/test_layer3_api.py
```

The revoke slice is backend/API-only. It may add request/response DTOs and OpenAPI schema for revoke. It must not add rendered controls, Playwright proof, provider object-store/network writes, provider/public URL runtime, public-proxy runtime, connector/destination dispatch, package mutation/reconstruction, source expansion, or same-origin behavior changes.

## Use route status

The use route remains blocked until a later freeze decides:

- whether use is client-held-token, same-origin proxy, or server-owned internal validation;
- whether a raw provider-private token is ever exposed to a browser/client;
- whether raw token material is stored, encrypted, or never retained;
- how single-use replay policy is enforced without token leakage;
- which proof surface demonstrates redaction, replay denial, and stale-authority rejection.

No implementation pass may add `POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use` under this freeze.

## Revoke route authority

The revoke route must require:

- `client_request_id`;
- `provider_signed_url_receipt_id`;
- `idempotency_key`;
- `revoked_by`;
- `revocation_reason`;
- `operator_decision: revoke_provider_private_signed_url`.

The route must be idempotent for the same receipt/idempotency/revoked_by/reason basis and conflict on mismatched reuse. It must fail closed for missing receipt, already revoked with a different idempotency basis, stale/mismatched authority, forbidden provider/destination fields, or attempts to revoke via browser-only state.

The response may confirm revoked state, revocation idempotency outcome, redacted audit receipt, source artifact hash/size, authority rail, and next state. It must not expose raw provider-private URL/token material, provider credentials, provider object identifiers, connector/destination details, public URLs, package/source payloads, or raw revocation reason text if durable state stores only a reason hash.

## Required implementation tests

The next implementation PR must prove:

1. OpenAPI exposes revoke and keeps prepare/status schemas stable;
2. use remains absent until its own token/delivery freeze exists;
3. revoke succeeds and records durable revocation/audit state;
4. revoke idempotent retry returns the same revocation state;
5. revoke idempotency conflict fails closed;
6. missing receipt fails closed;
7. forbidden provider/destination/public URL/raw token fields are rejected;
8. status after revoke reflects durable revoked state without generating a new token;
9. existing same-origin delivery and same-origin signed-reference routes do not gain provider-private fields;
10. no rendered controls, provider network/object-store writes, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector behavior, hidden LLM behavior, full mockup activation, auth/security behavior change, or frontend-only durable authority.

## Recommended next action

```yaml
recommended_next_action: implement_provider_private_signed_url_revoke_backend_api_only
if_use_route_is_requested: stop_for_token_delivery_use_authority_freeze
if_rendered_controls_are_requested: write_rendered_provider_private_signed_url_ui_freeze_first
if_real_provider_network_or_public_url_is_requested: stop_for_provider_public_url_or_public_proxy_freeze
if_connector_destination_dispatch_is_requested: stop_for_connector_destination_runtime_family
```

## Stop condition

Stop before implementation if revoke cannot be driven from existing prepared receipt, durable provider-private state, and server-owned external export/download authority without adding the use route, rendered UI authority, raw token exposure, raw token durable persistence, provider network/object-store behavior, public URLs, connector/destination behavior, package/source mutation, same-origin delivery changes, same-origin signed-reference changes, auth/security changes, or frontend-only durable state.
