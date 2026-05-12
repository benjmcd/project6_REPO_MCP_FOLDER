# Provider Private Signed URL Use Authority Contract

Status: planning/control contract for the blocked provider-private signed URL use route.

This document defines the minimum contract that must exist before `POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use` can be implemented. It does not admit the route.

## Current route status

```yaml
route: POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use
status: not_implemented
admission_result: blocked_no_token_delivery_model
prepare_status_runtime: implemented
revoke_runtime: implemented
runtime_implementation_allowed_next: false
```

## Required selected model

A future implementation-entry freeze must choose exactly one:

- `client_held_token`
- `server_owned_proxy_use`
- `encrypted_server_retained_token`
- `no_use_api_external_provider_consumption`

The selected model must define token custody, delivery, storage, replay, expiry, revocation, stale-authority behavior, audit, leakage, auth/security posture, and tests. A use route without a selected model is under-specified.

## Minimal future request contract

No request contract is admitted yet. A later freeze must decide whether the request contains:

- a raw provider-private token supplied by a client;
- only a receipt id for server-owned proxy/use;
- an encrypted token reference;
- no use API at all.

Until then, `provider_private_signed_url_token` and `raw_provider_private_signed_url_token` remain forbidden request fields on the live revoke route.

## Minimal future response contract

No use response contract is admitted yet. A later freeze must decide whether use returns:

- proof-of-use only;
- a same-origin stream/proxy response;
- a provider-side redirect/reference;
- no API response because there is no use API.

Any future response must remain redacted unless a separate security freeze admits otherwise.

## Required future tests

A use implementation PR must not exist until a freeze names tests for:

- OpenAPI route contract;
- token custody and redaction;
- token mismatch;
- single-use replay denial;
- expired receipt denial;
- revoked receipt denial;
- stale artifact/session/receipt authority denial;
- forbidden raw-token leakage in responses/errors/logs/audits/tests/screenshots/manifests;
- same-origin route non-regression;
- rendered UI headed/headless proof if UI controls are admitted;
- auth/security and secret-handling posture if raw token material is exposed or retained.

## Stop condition

Stop before implementation if the work requires raw token exposure, raw token durable persistence, provider network access, public/proxy URL behavior, rendered controls, connector/destination dispatch, package/source mutation, same-origin delivery changes, same-origin signed-reference changes, auth/security changes, or browser-owned durable authority without a separate freeze admitting that exact behavior.
