# Provider Private Signed URL Revoke-Only API Contract

Status: current-main planning/control API contract correction for `provider_private_signed_url_use_revoke_api_contract`.

The filename is retained for milestone continuity, but this document corrects the contract scope to revoke-only. It follows `234_PROVIDER_PRIVATE_SIGNED_URL_USE_REVOKE_FREEZE.md` and supersedes the earlier use-plus-revoke interpretation for the next runtime slice.

This pass is docs/proof/checker-only. It does not add routes, DTOs, services, models, migrations, executable backend tests, rendered UI controls, Playwright behavior, provider credentials, provider network calls, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector behavior, full mockup activation, auth/security behavior, same-origin delivery changes, same-origin signed-reference changes, provider/public URL runtime, or public proxy URL runtime.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_revoke_only_api_contract
entry_decision: revoke_api_contract_frozen_runtime_blocked
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
upstream_runtime_status: prepare_status_backend_api_only_implemented
second_runtime_slice: revoke_backend_api_only
provider_private_signed_url_use_route: deferred_blocked_by_redacted_token_boundary
runtime_implementation_allowed_next: true
rendered_ui_change: false
provider_network_or_object_store_write: false
same_origin_delivery_semantics_changed: false
same_origin_signed_reference_semantics_changed: false
```

## Allowed route contract

```yaml
routes:
  revoke:
    method: POST
    path: /api/v1/layer3/handoff/export/download/provider-private-signed-url/revoke
    owner_service: backend/app/services/layer3_provider_private_signed_url.py
    state_dependency: revoke_provider_private_signed_url_receipt
blocked_routes:
  use:
    method: POST
    path: /api/v1/layer3/handoff/export/download/provider-private-signed-url/use
    blocked_reason: redacted_token_boundary_requires_separate_delivery_authority_freeze
deferred_after_this_contract:
  use_route: true
  rendered_controls: true
  real_provider_network_or_object_store_behavior: true
  provider_public_url_runtime: true
  public_proxy_url_runtime: true
```

## Revoke request DTO

```yaml
required_fields:
  - client_request_id
  - provider_signed_url_receipt_id
  - idempotency_key
  - revoked_by
  - revocation_reason
  - operator_decision
required_values:
  operator_decision: revoke_provider_private_signed_url
optional_fields:
  - decision_notes
```

The revoke request must not accept provider credentials, provider bucket/container/key, raw provider object identifiers, raw provider-private tokens, public URLs, public proxy URLs, same-origin download URLs, same-origin signed-reference tokens, connector/destination payloads, source upload/local directory/web connector fields, package mutation payloads, RAG/vector settings, prompt/model/provider settings, auth/security overrides, or browser durable authority.

## Revoke response DTO

```yaml
required_fields:
  - schema_id
  - schema_version
  - request_id
  - status
  - provider_signed_url_receipt_id
  - provider_signed_url_state
  - delivery_mode
  - provider_url_redacted
  - provider_url_revoked
  - revocation_idempotency_key
  - source_artifact_hash
  - source_artifact_size_bytes
  - audit_receipt
  - authority_rail
  - next_allowed_actions
  - next_state
```

The revoke response must not return raw provider-private URL/token material, provider credentials, provider object identifiers, raw revocation reason text when durable state stores a reason hash, connector/destination details, public URLs, package/source payloads, or browser-local authority.

## Owner service contract

```yaml
owner_module: backend/app/services/layer3_provider_private_signed_url.py
new_owner_functions:
  - provider_private_signed_url_revoke
existing_state_functions:
  - revoke_provider_private_signed_url_receipt
existing_projection_function:
  - provider_private_signed_url_status
blocked_owner_functions_until_later_freeze:
  - provider_private_signed_url_use
```

The owner service must map `ProviderPrivateSignedUrlStateError` to bounded `Layer3WorkbenchError` responses without leaking raw tokens, provider URLs, provider object ids, raw artifact paths, provider credentials, or revocation reason text.

## Use route remains blocked

The use route remains deferred because the current prepare/status runtime deliberately returns only redacted URL/token material and durable state stores token hash/prefix metadata rather than raw usable token material. A client-callable use route cannot be specified coherently until the project decides a secure delivery/use model.

Required future planning before use:

- decide whether use is client-held-token, same-origin proxy, or server-owned internal validation;
- decide whether raw token material is ever exposed to the browser/client;
- decide whether raw token material is stored, encrypted, or never retained;
- decide the replay policy and proof surface for single-use consumption;
- add separate tests that prove token redaction, token mismatch behavior, stale authority rejection, and replay boundaries.

## Required tests

The implementation PR must add focused API tests proving:

1. OpenAPI revoke schema and forbidden fields;
2. successful revoke over a prepared receipt;
3. idempotent revoke retry;
4. idempotency conflict on changed revoked-by or reason;
5. missing receipt failure;
6. forbidden provider/destination/public URL/raw token fields fail closed;
7. status reflects revoked durable state;
8. use route remains absent;
9. no provider-private fields are added to same-origin delivery or same-origin signed-reference responses;
10. no rendered UI, provider network/object-store write, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector, hidden LLM, full mockup, auth/security, or frontend-only durable authority.

## Stop condition

Stop before implementation if revoke requires a use route, raw provider URLs in API responses, raw token persistence, rendered UI authority, public URL behavior, connector/destination dispatch, package/source mutation, same-origin delivery changes, same-origin signed-reference changes, auth/security changes, or frontend-only durable state.
