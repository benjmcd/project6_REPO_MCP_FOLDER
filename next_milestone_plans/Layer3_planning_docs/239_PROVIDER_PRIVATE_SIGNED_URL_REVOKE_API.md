# Provider Private Signed URL Revoke API

Status: current-main implementation/proof for `provider_private_signed_url_revoke_api`.

This document records the backend/API-only revoke runtime that follows `234_PROVIDER_PRIVATE_SIGNED_URL_USE_REVOKE_FREEZE.md` and `235_PROVIDER_PRIVATE_SIGNED_URL_USE_REVOKE_CONTRACT.md`.

## Runtime decision

```yaml
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
runtime_status: revoke_backend_api_only_implemented
implemented_route: POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/revoke
use_route_status: deferred_blocked_by_redacted_token_boundary
rendered_ui_change: false
provider_network_or_object_store_write: false
same_origin_delivery_semantics_changed: false
same_origin_signed_reference_semantics_changed: false
```

## Implemented scope

The runtime adds only the provider-private signed URL revoke route over existing durable receipt state.

Implemented files:

- `backend/app/api/layer3.py`
- `backend/app/services/layer3_provider_private_signed_url.py`
- `backend/tests/test_layer3_api.py`

The service delegates durable mutation to `revoke_provider_private_signed_url_receipt(...)`. It does not duplicate revocation ledger logic, expose raw provider-private URL/token material, add provider network behavior, write object-store data, dispatch connectors/destinations, mutate packages/sources, change same-origin delivery, change same-origin signed-reference behavior, or add rendered controls.

## Request boundary

The revoke route accepts only:

- `client_request_id`
- `provider_signed_url_receipt_id`
- `idempotency_key`
- `revoked_by`
- `revocation_reason`
- `operator_decision: revoke_provider_private_signed_url`
- optional `decision_notes`

The route rejects provider credentials, provider object fields, `provider_private_signed_url_token`, `raw_provider_private_signed_url_token`, public/proxy URLs, same-origin signed-reference tokens, connector/destination payloads, source expansion fields, package mutation fields, RAG/vector settings, prompt/model settings, auth/security overrides, and browser durable authority.

## Response boundary

The response is redacted and receipt-state oriented. It may report receipt id, provider-private receipt state, replay policy, use counts, revoked flag, source artifact hash/size, revocation idempotency key, authority rail, redacted audit receipt, next allowed actions, and next state.

The response must not report raw provider-private URL/token material, raw artifact refs, provider credentials, provider object identifiers, public URLs, connector/destination details, package/source payloads, or raw revocation reason text.

## Use route remains deferred

`POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use` remains absent. Use still requires a separate token/delivery authority freeze because current prepare/status/revoke responses expose only redacted provider-private URL/token material and durable state stores token hash/prefix metadata rather than raw usable token material.

## Proof obligations now covered

- OpenAPI exposes revoke while use remains absent.
- Revoke succeeds over a prepared receipt.
- Revoke idempotent retry returns revoked state.
- Revoke idempotency conflict fails closed.
- Missing receipt fails closed.
- Forbidden raw token/provider/destination/public URL fields fail closed.
- Status after revoke reflects durable revoked state.
- Same-origin delivery and signed-reference surfaces remain unchanged by this route.

## Remaining work

The next provider-private signed URL work is not more revoke behavior. It is a separate use-route token/delivery authority freeze, or a rendered UI freeze, or a real provider/public URL authority freeze, depending on the selected next use case.
