# Provider Private Signed URL Route API Contract

Status: current-main planning/control route/API contract for `provider_private_signed_url_route_api_contract`.

This document follows `231_PROVIDER_PRIVATE_SIGNED_URL_ROUTE_ENTRY_FREEZE.md`. It freezes the precise backend/API first-slice contract for provider-private signed URL runtime entry after fake-provider and durable-state substrates are implemented and tested.

This pass is docs/proof/checker-only. It does not add routes, DTOs, services, models, migrations, executable backend tests, rendered UI controls, Playwright behavior, provider credentials, provider network calls, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector behavior, full mockup activation, auth/security behavior, same-origin delivery changes, same-origin signed-reference changes, provider/public URL runtime, or public proxy URL runtime.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_route_api_contract
entry_decision: route_api_contract_frozen_runtime_blocked
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
runtime_status: not_implemented
fake_provider_contract_double_status: implemented_tested
durable_state_substrate_status: implemented_tested
provider_private_signed_url_runtime: false
route_dto_change: false
rendered_ui_change: false
first_runtime_slice: prepare_status_backend_api_only
runtime_implementation_allowed_next: true
```

## Allowed First-Slice Route Contract

```yaml
routes:
  prepare:
    method: POST
    path: /api/v1/layer3/handoff/export/download/provider-private-signed-url/prepare
    owner_service: backend/app/services/layer3_provider_private_signed_url.py
    purpose: create a redacted provider-private signed URL durable receipt over existing external export/download authority
  status:
    method: GET
    path: /api/v1/layer3/handoff/export/download/provider-private-signed-url/status/{provider_signed_url_receipt_id}
    owner_service: backend/app/services/layer3_provider_private_signed_url.py
    purpose: read redacted durable provider-private signed URL receipt state
deferred_routes:
  use: /api/v1/layer3/handoff/export/download/provider-private-signed-url/use
  revoke: /api/v1/layer3/handoff/export/download/provider-private-signed-url/revoke
```

The first implementation must not include `use` or `revoke` unless a later freeze explicitly admits that second slice. The first implementation may expose `revocation_supported: true` only as state capability metadata, not as a live revoke route.

## Prepare Request DTO

```yaml
required_fields:
  - client_request_id
  - session_id
  - analysis_plan_id
  - pass_run_id
  - reconciliation_record_id
  - external_export_download_record_ref
  - export_download_descriptor_ref
  - external_export_download_state
  - export_download_target
  - download_mode
  - delivery_mode
  - operator_decision
  - source_artifact_hash
  - source_artifact_size_bytes
  - recipient_scope
optional_fields:
  - requested_ttl_seconds
  - decision_notes
required_values:
  external_export_download_state: external_export_download_prepared
  export_download_target: aps_evidence_bundle_download_reference
  download_mode: reference_only_prepare
  delivery_mode: provider_private_signed_url
  operator_decision: prepare_provider_private_signed_url
ttl:
  default_seconds: 300
  max_seconds: 900
idempotency:
  client_request_id: required
  conflict_basis:
    - external export/download artifact authority
    - source artifact hash
    - source artifact size
    - recipient_scope
    - requested_ttl_seconds
```

Forbidden fields must be typed as impossible or rejected fail-closed: provider credentials, provider secret, provider bucket/container/key, provider object identity, raw provider signature, raw local path, local file path, destination id, destination URL, connector payload, connector secret, source upload, local directory, web connector, package mutation payload, RAG/vector settings, prompt/model/provider settings, auth/security overrides, browser durable authority, public URL, public proxy URL, same-origin download URL, and same-origin signed-reference token.

## Prepare Response DTO

```yaml
required_fields:
  - schema_id
  - schema_version
  - request_id
  - status
  - session_id
  - analysis_plan_id
  - pass_run_id
  - reconciliation_record_id
  - external_export_download_record_ref
  - export_download_descriptor_ref
  - provider_signed_url_receipt_id
  - provider_signed_url_state
  - delivery_mode
  - provider_url_redacted
  - provider_url_expires_at
  - provider_url_expires_in_seconds
  - provider_url_replay_policy
  - provider_url_revocation_supported
  - source_artifact_hash
  - source_artifact_size_bytes
  - authority_rail
  - audit_receipt
  - next_allowed_actions
  - next_state
status_values:
  success: prepared
  idempotent_success: prepared
  blocked: blocked
  conflict: conflict
```

`provider_url_redacted` must be an explicit redacted marker or non-usable fake-provider preview. It must not be a bearer URL, public URL, public proxy URL, same-origin download URL, or connector destination URL.

## Status Response DTO

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
  - provider_url_expires_at
  - provider_url_replay_policy
  - provider_url_revocation_supported
  - provider_url_use_count
  - provider_url_max_use_count
  - provider_url_revoked
  - source_artifact_hash
  - source_artifact_size_bytes
  - audit_receipt
  - next_allowed_actions
```

Status must be read-only. It must not generate a new provider token, mutate provider-private state, mutate same-origin signed-reference state, write files, write package rows, dispatch connectors, or infer browser/UI authority.

## Owner Service Contract

```yaml
owner_module: backend/app/services/layer3_provider_private_signed_url.py
owner_functions:
  - provider_private_signed_url_prepare
  - provider_private_signed_url_status
allowed_dependencies:
  - backend/app/services/layer3_provider_private_signed_url_state.py
  - backend/app/services/layer3_provider_private_signed_url_fake_provider.py
  - backend/app/services/layer3_external_export_contract.py
  - existing Layer 3 models needed to verify session/plan/pass/package/export authority
deferred_owner_functions:
  - provider_private_signed_url_use
  - provider_private_signed_url_revoke
```

The owner service must verify existing external export/download authority server-side. It must not trust client-provided artifact refs, provider object ids, provider storage locations, local paths, destination ids, connector payloads, or browser state as durable authority.

## Required Tests

The first runtime PR must add focused API tests proving:

1. prepare success creates one durable provider-private receipt over admitted external export/download authority;
2. prepare idempotent retry returns the same durable receipt and does not create duplicate rows;
3. prepare conflicting recipient scope, artifact hash, artifact size, TTL, or authority fails closed;
4. status returns redacted durable receipt state without mutation;
5. missing or stale session/plan/pass/reconciliation/export/download authority fails closed;
6. fake-provider prepare failure maps to a controlled response without leaked token/provider details;
7. requested TTL is bounded and reflected in response/status;
8. OpenAPI exposes the admitted prepare/status schemas and preserves forbidden sentinel fields as impossible or fail-closed;
9. existing same-origin external export/download deliver and same-origin signed-reference generate/use responses do not gain provider-private URL fields;
10. no rendered UI controls, Playwright behavior, provider network/object-store writes, connector/destination dispatch, source expansion, package mutation/reconstruction, RAG/vector behavior, hidden LLM planning, full mockup activation, auth/security behavior change, or frontend-only durable authority.

## Negative Invariants

- no `use` route in the first slice;
- no `revoke` route in the first slice;
- no `provider_private_signed_url_use_route_first_slice`;
- no `provider_private_signed_url_revoke_route_first_slice`;
- no rendered provider-private signed URL controls;
- no provider object-store/network write/copy/ACL behavior;
- no provider credentials, bucket, container, object key, raw signature, or raw bearer URL in request/response/error/log/test surfaces;
- no provider public URL runtime;
- no public proxy URL runtime;
- no same-origin delivery behavior change;
- no same-origin signed-reference behavior change;
- no connector invocation, destination selection, destination write, or generic downstream dispatch;
- no package mutation or reconstruction;
- no source adapter registry, source expansion, local upload, local-directory ingestion, or web connector retrieval;
- no broad qualitative/hybrid/RAG/vector runtime;
- no prompt/model/provider runtime expansion;
- no hidden LLM planning;
- no full mockup activation;
- no auth/security behavior change;
- no frontend-only durable authority.

## Recommended Next Action

```yaml
recommended_next_action: implement_provider_private_signed_url_prepare_status_backend_api
if_prepare_status_authority_requires_client_provider_identifier: stop
if_use_or_revoke_is_needed: write_second_slice_freeze_first
if_rendered_controls_are_requested: write_rendered_ui_freeze_first
if_real_provider_network_or_public_url_is_requested: stop_for_provider_public_url_or_public_proxy_freeze
if_connector_destination_dispatch_is_requested: stop_for_connector_destination_runtime_family
```

## Stop Condition

Stop before runtime implementation if prepare/status cannot be verified against existing server-owned external export/download authority, or if implementation would require client-supplied provider identifiers, raw paths, provider credentials, public URLs, connector/destination behavior, rendered UI controls, package mutation, source expansion, RAG/vector behavior, hidden LLM planning, full mockup activation, auth/security changes, or frontend-only durable authority.
