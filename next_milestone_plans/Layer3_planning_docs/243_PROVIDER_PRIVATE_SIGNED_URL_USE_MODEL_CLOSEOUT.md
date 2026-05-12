# Provider Private Signed URL Use Model Closeout

Status: planning/control closeout for `provider_private_signed_url_use_model_closeout`.

This document follows `240_PROVIDER_PRIVATE_SIGNED_URL_USE_AUTHORITY_FREEZE.md` and `241_PROVIDER_PRIVATE_SIGNED_URL_USE_AUTHORITY_CONTRACT.md`. It resolves the current use-route model gap without admitting a `use` route.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_use_model_closeout
entry_decision: use_route_closed_current_lane
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
selected_use_model: no_use_api_external_provider_consumption
provider_private_signed_url_use_route: closed_not_implemented
prepare_status_runtime: prepare_status_backend_api_only_implemented
revoke_runtime: revoke_backend_api_only_implemented
runtime_implementation_allowed_next: false
rendered_ui_change: false
provider_network_or_object_store_write: false
same_origin_delivery_semantics_changed: false
same_origin_signed_reference_semantics_changed: false
```

The selected model is `no_use_api_external_provider_consumption` for the current provider-private signed URL lane.

## Authority finding

Live backend authority supports prepare/status/revoke only:

- `provider_private_signed_url_prepare` receives raw provider-private token material only from the deterministic fake provider and records durable state through `record_prepared_provider_private_signed_url_receipt`.
- Durable state stores `provider_private_signed_url_token_hash` and `provider_private_signed_url_token_prefix`, not raw usable token material.
- prepare/status responses expose `provider_url_redacted` and receipt/audit metadata, not a usable provider-private URL.
- revoke delegates to `revoke_provider_private_signed_url_receipt` and forbids `provider_private_signed_url_token` and `raw_provider_private_signed_url_token`.
- `POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use` remains absent.

Therefore a Layer 3 API `use` route would require a new custody model that is not currently selected.

## Model adjudication

```yaml
client_held_token:
  decision: rejected_for_current_lane
  reason: would require accepting raw provider-private token material from a client even though current prepare/status never exposes it
server_owned_proxy_use:
  decision: rejected_for_current_lane
  reason: requires proxy semantics plus raw token retention or equivalent usable-secret access
encrypted_server_retained_token:
  decision: rejected_for_current_lane
  reason: requires secret storage, encryption, rotation, recovery, leakage, and auth/security authority beyond this lane
no_use_api_external_provider_consumption:
  decision: selected_for_current_lane
  reason: preserves redaction and durable receipt authority while keeping provider-private consumption outside the Layer 3 API
```

## Consequence

The current lane is complete for backend/API prepare, status, and revoke. It does not implement provider-private signed URL use. A future real provider, external recipient delivery, public/proxy URL, or rendered provider-private control pass must get its own freeze before implementation.

## Negative invariants

This closeout admits no:

- `POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use` route;
- raw provider-private token in API responses, logs, audit receipts, tests, screenshots, or manifests;
- raw token durable persistence;
- provider network/object-store behavior;
- public/proxy URL behavior;
- rendered provider-private controls;
- connector/destination dispatch;
- package/source mutation;
- same-origin delivery or signed-reference semantic change;
- auth/security behavior change;
- frontend-only durable authority.

## Recommended next actions

```yaml
recommended_next_actions:
  - keep_provider_private_signed_url_use_route_absent
  - write_rendered_provider_private_signed_url_ui_freeze_before_controls
  - write_real_provider_delivery_freeze_before_external_recipient_delivery
  - write_public_or_proxy_url_freeze_before_public_exposure
```

## Stop condition

Stop before implementation if the work requires a `use` route, raw token exposure, raw token durable persistence, provider network access, public/proxy URL behavior, rendered controls, connector/destination delivery, package/source mutation, same-origin delivery changes, same-origin signed-reference changes, auth/security changes, or browser-owned durable authority without a separate freeze admitting that exact behavior.
