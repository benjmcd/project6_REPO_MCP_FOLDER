# Provider Private Signed URL Route Entry Freeze

Status: current-main planning/control route-entry freeze for `provider_private_signed_url_route_entry_freeze`.

This document follows the durable-state substrate implemented through PR #786 and review-debt hardening through PR #787. It records the minimum route/API implementation-entry posture now that the fake-provider contract double and durable receipt/revocation/audit substrate exist.

This pass is docs/proof/checker-only. It does not add routes, DTOs, services, models, migrations, executable backend tests, rendered UI controls, Playwright behavior, provider credentials, provider network calls, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector behavior, full mockup activation, auth/security behavior, same-origin delivery changes, same-origin signed-reference changes, provider/public URL runtime, or public proxy URL runtime.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_route_entry_freeze
entry_decision: route_entry_frozen_runtime_blocked
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
runtime_status: not_implemented
fake_provider_contract_double_status: implemented_tested
durable_state_substrate_status: implemented_tested
provider_private_signed_url_runtime: false
route_dto_change: false
rendered_ui_change: false
first_runtime_slice_candidate: prepare_status_backend_api_only
implementation_entry_allowed_next: true
```

The next implementation pass may add only the smallest backend/API provider-private signed URL route slice if it preserves this freeze. The preferred first slice is `prepare` plus read-only `status` because it proves request/response shape, authority binding, durable receipt creation, fake-provider integration, redaction, idempotency, and OpenAPI guardrails without making rendered UI controls or external connector/provider network behavior live.

## Current Authority

```yaml
live_prerequisites:
  fake_provider_contract_double: implemented_tested
  durable_state_substrate: implemented_tested
  recipient_scope_request_basis_binding: implemented_tested
  revocation_idempotency_conflict_guard: implemented_tested
  same_origin_delivery: existing_separate_authority
  same_origin_signed_reference: existing_separate_authority
not_live:
  provider_private_signed_url_route: true
  provider_private_signed_url_dto: true
  provider_private_signed_url_rendered_control: true
  provider_network_or_object_store_write: true
  provider_public_url_or_public_proxy: true
```

Existing planning docs `223` through `230` remain historical authority for selection, fake-provider proof, and durable-state proof. This document supersedes their pre-substrate stop condition only for the narrow question of route/API implementation entry. It does not rewrite the negative invariants that remain true for public/provider URL exposure, rendered UI controls, provider object-store/network behavior, connector/destination dispatch, and package/source/runtime widening.

## Frozen First Runtime Slice

```yaml
first_slice:
  allowed_routes:
    - POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/prepare
    - GET /api/v1/layer3/handoff/export/download/provider-private-signed-url/status/{provider_signed_url_receipt_id}
  explicitly_deferred_routes:
    - POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use
    - POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/revoke
  allowed_owner_service:
    - backend/app/services/layer3_provider_private_signed_url.py
  allowed_existing_dependencies:
    - backend/app/services/layer3_provider_private_signed_url_state.py
    - backend/app/services/layer3_provider_private_signed_url_fake_provider.py
    - backend/app/services/layer3_external_export_contract.py
  allowed_tests:
    - backend/tests/test_layer3_provider_private_signed_url_api.py
    - narrow additions to backend/tests/test_layer3_api.py only if OpenAPI aggregation requires them
```

The first slice must be backend/API-only. It must not add rendered controls, route discovery UI, browser automation, provider object-store/network calls, public URL delivery, connector/destination dispatch, or package/source/runtime expansion.

## Request Authority

The prepare request must be server-verifiable from already-live external export/download readiness authority. It may accept only:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `external_export_download_record_ref`;
- `export_download_descriptor_ref`;
- `external_export_download_state`;
- `export_download_target`;
- `download_mode`;
- `delivery_mode`;
- `operator_decision`;
- `source_artifact_hash`;
- `source_artifact_size_bytes`;
- `recipient_scope`;
- `requested_ttl_seconds`;
- optional `decision_notes`.

The route must derive or validate artifact authority from server-owned external export/download state. It must not accept raw local paths, provider object identifiers, provider credentials, bucket/container/key fields, destination fields, connector payloads, public URLs, same-origin signed-reference tokens, RAG/vector fields, source-upload fields, auth/security overrides, prompt/model fields, or package mutation payloads.

## Response Authority

The prepare response must be redacted and durable-state-backed. It may include:

- schema id/version and request id;
- `status`;
- session, plan, pass, reconciliation, external export/download, and descriptor refs;
- `provider_signed_url_receipt_id`;
- provider-private state;
- delivery mode;
- redacted provider URL marker, not a usable bearer URL;
- expiry time/TTL;
- replay policy;
- revocation-supported flag;
- source artifact hash/size;
- authority rail;
- audit receipt;
- next allowed actions and next state.

The status response must be read-only and redacted. It must not include a raw provider signed URL, provider secret, provider object key, provider credentials, connector/destination result, raw local path, public URL, public proxy URL, package payload, source expansion state, RAG/vector state, auth internals, prompt/model payload, or frontend-only durable authority.

## Required Implementation Tests

The next implementation pass must include focused tests for:

1. prepare route success over existing external export/download authority;
2. status route success over the durable receipt row;
3. OpenAPI request/response schema for prepare/status;
4. forbidden request fields fail closed;
5. stale session, package, descriptor, artifact hash, and artifact size fail closed;
6. client request id idempotent retry and conflict behavior;
7. recipient scope included in durable request basis;
8. TTL validation and status expiry projection;
9. fake-provider failure injection mapped to controlled API errors;
10. redaction across success and error bodies;
11. no provider URL fields on same-origin delivery or same-origin signed-reference routes;
12. no rendered UI controls, connector dispatch, destination write, source expansion, package mutation, RAG/vector behavior, hidden LLM behavior, full mockup activation, or auth/security behavior change.

## Negative Invariants

- no rendered provider-private signed URL UI control;
- no provider network call or object-store write/copy/ACL behavior;
- no provider credentials, bucket, container, object key, raw signature, or raw bearer URL in request/response/log/test surfaces;
- no provider public URL runtime;
- no public proxy URL runtime;
- no same-origin delivery behavior change;
- no same-origin signed-reference behavior change;
- no connector invocation;
- no destination selection or destination write;
- no generic downstream dispatch;
- no package mutation or reconstruction;
- no source adapter registry, source expansion, local upload, local-directory ingestion, or web connector retrieval;
- no broad qualitative/hybrid/RAG/vector runtime;
- no hidden LLM planning;
- no prompt/model/provider runtime expansion;
- no full mockup activation;
- no auth/security behavior change;
- no frontend-only durable authority;
- no Playwright or rendered theme proof requirement in this backend/API-only first slice.

## Recommended Next Action

```yaml
recommended_next_action: write_provider_private_signed_url_route_api_contract
then_implement: prepare_status_backend_api_only
if_rendered_ui_requested: stop_for_rendered_provider_private_signed_url_ui_freeze
if_use_or_revoke_requested_in_first_slice: stop_or_write_separate_use_revoke_freeze
if_provider_network_or_public_url_requested: stop_for_provider_public_url_or_public_proxy_freeze
if_connector_destination_requested: stop_for_connector_destination_runtime_family
```

## Stop Condition

Stop before implementation if prepare/status cannot be driven from existing external export/download authority without accepting client-supplied provider identifiers, raw local paths, provider credentials, public URLs, connector destinations, package mutation payloads, or frontend-only durable state.
