# Provider Private Signed URL Fake Provider Contract

Status: current-main implementation/test contract-double proof for `provider_private_signed_url_fake_provider_contract`.

This document follows `226_PROVIDER_PRIVATE_SIGNED_URL_CONTRACT_ONLY_FREEZE.md`. It records the narrow fake-provider contract double now present in `backend/app/services/layer3_provider_private_signed_url_fake_provider.py` and covered by `backend/tests/test_layer3_provider_private_signed_url_fake_provider.py`.

This pass does not add provider-private signed URL API routes, DTO route wiring, models, migrations, rendered UI controls, Playwright behavior, provider object writes, provider credentials, provider network calls, public URLs, connector/destination dispatch, package mutation, source expansion, RAG/vector behavior, hidden LLM behavior, full mockup activation, auth/security behavior, or changes to the existing same-origin delivery and same-origin signed-reference routes.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_fake_provider_contract
entry_decision: fake_provider_contract_implemented_runtime_blocked
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
runtime_status: not_implemented
provider_storage_authority_result: no_current_main_provider_storage_authority
fake_provider_contract_double_status: implemented_tested
provider_private_signed_url_runtime: false
route_dto_model_migration_ui_change: false
```

The fake provider is a deterministic in-memory contract double. It exists to make provider-private signed URL authority testable before any route or durable runtime is admitted. It is not a provider adapter, not a storage service, not a public URL generator, and not a downstream delivery implementation.

## Implemented Contract Surface

```yaml
fake_provider_module: backend/app/services/layer3_provider_private_signed_url_fake_provider.py
test_module: backend/tests/test_layer3_provider_private_signed_url_fake_provider.py
schema_id: layer3.provider_private_signed_url.fake_provider.v1
provider_authority: deterministic_in_memory_fake_provider
replay_policy: single_use
max_ttl_seconds: 900
states:
  prepared: provider_private_signed_url_prepared
  used: provider_private_signed_url_used
  revoked: provider_private_signed_url_revoked
  expired: provider_private_signed_url_expired
  blocked: provider_private_signed_url_blocked
  conflict: provider_private_signed_url_conflict
```

Implemented data contracts:

- `ProviderArtifactAuthority`;
- `ProviderPrivateSignedUrlPrepareRequest`;
- `ProviderPrivateSignedUrlReceipt`;
- `ProviderPrivateSignedUrlError`;
- `ProviderPrivateSignedUrlFakeProvider`.

Implemented fake-provider operations:

- `prepare`;
- `use`;
- `revoke`;
- `status`.

## Covered Proof

The focused test file proves:

1. deterministic provider object identity from artifact authority;
2. source artifact hash and size validation;
3. idempotent prepare for identical `client_request_id` plus authority;
4. idempotency conflict for reused `client_request_id` with different artifact authority;
5. stale hash/size authority rejection at use;
6. provider failure injection;
7. TTL expiry;
8. revocation and post-revocation use denial;
9. single-use replay denial;
10. redaction in prepare/status/error/audit responses;
11. no provider credentials, raw signatures, raw provider object keys, buckets, containers, public URLs, connector runs, destination writes, package payloads, source expansion, RAG/vector state, prompt/model payloads, or auth internals in fake-provider response surfaces.

## Runtime Still Blocked

The following remain unresolved before any provider-private signed URL route or durable runtime can be admitted:

- provider/storage authority;
- selected server-side artifact materialization owner;
- durable DB rows for receipts, revocations, audit events, expiry, idempotency, and replay;
- route/API DTO request and response schema;
- stale external export/download readiness reconciliation against live workbench state;
- response envelope policy for any usable bearer URL;
- log, trace, screenshot, manifest, and audit redaction policy beyond the fake provider response surface;
- auth/security posture for operator and external downstream recipient;
- headed/headless plus light/dark/workbench proof if rendered controls are admitted.

## Negative Invariants

- no provider/private signed URL runtime route;
- no provider/public URL runtime;
- no public proxy URL runtime;
- no provider storage authority;
- no provider object write, copy, ACL, bucket, container, key, credential, or network behavior;
- no provider URL fields on existing same-origin delivery or signed-reference routes;
- no same-origin delivery or same-origin signed-reference semantics change;
- no external connector invocation;
- no destination write;
- no source adapter registry;
- no source expansion;
- no local upload;
- no local-directory ingestion;
- no web connector retrieval;
- no package mutation or reconstruction;
- no broad qualitative/hybrid/RAG runtime;
- no vector index creation;
- no embedding generation;
- no hidden LLM planning;
- no prompt/model/provider runtime;
- no full mockup activation;
- no frontend-only durable authority;
- no auth/security behavior change;
- no route/API behavior change;
- no DTO behavior change;
- no model or migration change;
- no rendered UI control;
- no Playwright configuration change;
- no CI workflow change.

## Recommended Next Action

```yaml
recommended_next_action: freeze_provider_storage_and_durable_receipt_authority_before_routes
if_runtime_route_or_dto_is_requested_before_storage_authority: stop
if_public_exposure_is_requested: stop_and_create_separate_public_url_or_proxy_freeze
if_connector_or_destination_delivery_is_requested: stop_and_use_connector_destination_runtime_family
```

## Stop Condition

Stop before runtime route implementation if provider/storage authority, durable receipt/audit rows, selected artifact materialization authority, stale external export/download readiness checks, bearer URL response envelope policy, redaction/leakage policy, or auth/security posture remain unproven.
