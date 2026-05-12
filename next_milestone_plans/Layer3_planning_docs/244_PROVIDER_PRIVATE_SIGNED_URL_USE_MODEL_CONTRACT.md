# Provider Private Signed URL Use Model Contract

Status: planning/control contract for `no_use_api_external_provider_consumption`.

This contract makes the selected current-lane model explicit: Layer 3 does not provide a provider-private signed URL `use` API.

## Current route contract

```yaml
route: POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use
status: not_implemented
admission_result: closed_not_implemented
selected_use_model: no_use_api_external_provider_consumption
runtime_implementation_allowed_next: false
```

The absence of the route is intentional. It is not a missing endpoint.

## Prepare/status/revoke contract

The current admitted API contract remains:

- prepare may create durable provider-private signed URL receipt authority using fake-provider output and redacted response fields;
- status may inspect durable receipt state by receipt id;
- revoke may transition durable receipt state to revoked through receipt authority and idempotency controls;
- no API response may expose raw provider-private token or raw provider-private URL material;
- no live revoke request may accept `provider_private_signed_url_token` or `raw_provider_private_signed_url_token`.

## Future admission requirements

A future pass may reopen provider-private consumption only with a separate freeze that names exactly one target:

- real external recipient delivery;
- server-owned proxy use;
- encrypted server-retained token use;
- public/proxy URL exposure;
- rendered provider-private controls;
- connector/destination delivery.

That future freeze must define custody, storage, delivery, replay, expiry, revocation, stale-authority behavior, audit, leakage, auth/security posture, tests, and headed/headless rendered proof if UI changes are admitted.

## Required guard tests

Current and future checker/test coverage must preserve:

- OpenAPI absence for the provider-private signed URL `use` route;
- live revoke forbidden-field checks for raw token fields;
- prepare/status response redaction;
- durable state hash/prefix-only token authority;
- same-origin delivery and signed-reference non-regression;
- absence of rendered provider-private controls unless a later UI freeze admits them.

## Completion standard

The provider-private signed URL use-model gap is closed when docs, manifests, and checker agree that:

- `selected_use_model` is `no_use_api_external_provider_consumption`;
- the `use` route is closed and not implemented;
- prepare/status/revoke remain the only admitted backend/API surfaces in this lane;
- future provider-private consumption requires a separate implementation-entry freeze.

## Stop condition

Stop before implementation if any task tries to treat this contract as permission to add a use route, expose raw token material, retain raw usable token material, invoke a real provider, expose a public/proxy URL, add rendered provider-private controls, or route data through connector/destination delivery.
