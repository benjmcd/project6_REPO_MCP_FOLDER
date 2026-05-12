# Provider Private Signed URL Rendered UI Contract

Status: planning/control contract for `provider_private_signed_url_rendered_ui_entry`.

This contract defines the allowed rendered `/review/layer3` behavior for provider-private prepare/status/revoke controls. It does not implement the controls.

## Route contract

The rendered UI may call only these existing endpoints:

```yaml
allowed_routes:
  - POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/prepare
  - GET /api/v1/layer3/handoff/export/download/provider-private-signed-url/status/{provider_signed_url_receipt_id}
  - POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/revoke
blocked_route:
  - POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use
```

No backend/API route is admitted by this contract.

## Request contract

Prepare request fields must come from existing server-authoritative rendered state and must match the already-live backend/API DTO. Revoke request fields must be limited to receipt id, request/idempotency fields, and `operator_decision: revoke_provider_private_signed_url`.

The UI must never send:

- `provider_private_signed_url_token`;
- `raw_provider_private_signed_url_token`;
- provider credentials;
- provider URL;
- public URL;
- connector or destination targets;
- source expansion fields;
- package mutation fields.

## Response/display contract

The UI may display:

- receipt id;
- redacted provider URL marker;
- provider-private state;
- expiry timestamp;
- source artifact hash and size;
- audit receipt id and reason code;
- next allowed action labels.

The UI must not display raw provider-private token or raw provider-private URL material.

## Theme/accessibility contract

The implementation proof must run in both headed and headless Chromium and must prove the controls remain coherent across `system`, `light`, `dark`, and `workbench`. The implementation must use stable selectors and restore or preserve theme state when parity checkpoints are run.

## Negative invariants

The implementation must prove:

- no provider-private `use` route request;
- no raw token field in prepare/revoke/status payloads or displays;
- no provider/public URL or public proxy exposure;
- no connector/destination dispatch;
- no package mutation/reconstruction;
- no source expansion;
- no same-origin delivery or signed-reference semantic change;
- no frontend-only durable authority.

## Completion standard

The future implementation is complete only when the rendered controls can prepare, inspect, and revoke provider-private signed URL receipt state over existing APIs, with headed/headless and live-theme proof, while keeping `use` closed and every deferred category absent.

## Stop condition

Stop before implementation if any control requires backend/API changes, raw token custody, real provider credentials, public/proxy URL exposure, connector/destination delivery, source expansion, package mutation, auth/security behavior changes, or Claude runtime admission.
