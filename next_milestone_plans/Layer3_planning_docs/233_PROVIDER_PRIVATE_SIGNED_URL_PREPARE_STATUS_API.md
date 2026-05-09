# Provider Private Signed URL Prepare Status API

Status: current-main implementation/proof for `provider_private_signed_url_prepare_status_api`.

This document records the first backend/API-only provider-private signed URL runtime slice after `231_PROVIDER_PRIVATE_SIGNED_URL_ROUTE_ENTRY_FREEZE.md` and `232_PROVIDER_PRIVATE_SIGNED_URL_ROUTE_API_CONTRACT.md`. The slice implements only prepare plus read-only status over existing external export/download readiness authority.

This pass adds no rendered UI controls, no provider network or object-store writes, no provider/public URL runtime, no public proxy URL runtime, no connector/destination dispatch, no package mutation/reconstruction, no source expansion, no RAG/vector behavior, no full mockup activation, no hidden LLM planning, no auth/security behavior change, no same-origin delivery behavior change, and no same-origin signed-reference behavior change.

## Decision

```yaml
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
first_runtime_slice: prepare_status_backend_api_only
runtime_status: prepare_status_backend_api_only_implemented
provider_private_signed_url_runtime: true
route_dto_change: true
rendered_ui_change: false
provider_network_or_object_store_write: false
provider_public_url_runtime: false
public_proxy_url_runtime: false
same_origin_delivery_semantics_changed: false
same_origin_signed_reference_semantics_changed: false
connector_destination_dispatch: false
package_mutation_reconstruction: false
source_expansion: false
rag_vector_hybrid_runtime: false
auth_security_behavior_change: false
```

## Implemented Routes

```yaml
allowed_routes:
  - POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/prepare
  - GET /api/v1/layer3/handoff/export/download/provider-private-signed-url/status/{provider_signed_url_receipt_id}
use_route_status: deferred_not_implemented
revoke_route_status: deferred_not_implemented
```

`use` and `revoke` remain deferred. A later second-slice freeze is required before either route can be implemented.

## Owner Surface

```yaml
owner_service: backend/app/services/layer3_provider_private_signed_url.py
owner_functions:
  - provider_private_signed_url_prepare
  - provider_private_signed_url_status
existing_authority_dependency:
  - backend/app/services/layer3_external_export_contract.py
durable_state_dependency:
  - backend/app/services/layer3_provider_private_signed_url_state.py
fake_provider_dependency:
  - backend/app/services/layer3_provider_private_signed_url_fake_provider.py
api_surface:
  - backend/app/api/layer3.py
focused_tests:
  - backend/tests/test_layer3_api.py
```

Prepare verifies existing external export/download readiness server-side, verifies source artifact hash and size against server-owned artifact bytes, calls the deterministic fake provider, and records durable provider-private signed URL receipt/object-authority/audit state. Status reads durable state and projects expired state without mutating rows or generating a new token.

## Request And Response Guardrails

Prepare admits only the route/API contract fields frozen by doc 232. It rejects provider credentials, provider bucket/container/key, raw provider signatures, raw local paths, local file paths, destination fields, connector payloads, source upload fields, local directory fields, web connector fields, package mutation payloads, RAG/vector settings, prompt/model/provider settings, auth/security overrides, browser durable authority, public URL fields, public proxy URL fields, same-origin download URL fields, and same-origin signed-reference token fields.

Responses expose only redacted provider-private URL state. They do not return raw bearer URLs, provider secrets, provider object keys, raw local artifact refs, same-origin delivery URLs, public URLs, public proxy URLs, connector destinations, or package payload rewrites.

## Validation Proof

The focused API tests in `backend/tests/test_layer3_api.py` prove:

1. `test_layer3_api_provider_private_signed_url_openapi_prepare_status_schema`;
2. `test_layer3_api_provider_private_signed_url_prepare_success_status_idempotent_and_negative_side_effect_absence`;
3. `test_layer3_api_provider_private_signed_url_fail_closed_stale_authority_forbidden_ttl_and_fake_provider_failure`.

The tests cover OpenAPI prepare/status schemas, forbidden sentinel fields, successful prepare/status over existing external export/download authority, idempotent retry, durable receipt/object-authority/audit state, stale authority rejection, TTL rejection, fake-provider failure redaction, missing receipt status rejection, same-origin route non-widening, unchanged external export/download readiness, and negative side-effect absence.

## Negative Invariants

- no provider-private signed URL `use` route;
- no provider-private signed URL `revoke` route;
- no rendered provider-private signed URL control;
- no provider network or object-store write/copy/ACL behavior;
- no provider public URL runtime;
- no public proxy URL runtime;
- no same-origin delivery semantics change;
- no same-origin signed-reference semantics change;
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
- no frontend-only durable authority.

## Stop Condition

Stop after this backend/API prepare/status slice. Do not implement provider-private signed URL use/revoke, rendered controls, real provider network/object-store behavior, provider/public URLs, public proxy URLs, connector/destination dispatch, package mutation/reconstruction, source expansion, qualitative/hybrid/RAG/vector behavior, full mockup activation, hidden LLM planning, auth/security behavior, same-origin delivery changes, or same-origin signed-reference changes without a separate freeze.
