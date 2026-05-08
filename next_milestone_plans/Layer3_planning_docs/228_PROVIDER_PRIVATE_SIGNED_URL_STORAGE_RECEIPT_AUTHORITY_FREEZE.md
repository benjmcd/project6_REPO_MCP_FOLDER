# Provider Private Signed URL Storage Receipt Authority Freeze

Status: current-main planning/control storage and durable-receipt authority freeze for `provider_private_signed_url_storage_receipt_authority_freeze`.

This document follows `227_PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_CONTRACT.md`. It freezes the minimum provider/storage and durable receipt authority required before any provider-private signed URL route, DTO, model, migration, service runtime, or rendered control can be admitted.

This pass does not implement provider-private signed URL runtime behavior, add routes, add DTOs, add models, add migrations, change rendered UI controls, change Playwright configuration, create provider objects, introduce provider credentials, invoke provider networks, create public URLs, dispatch connectors or destinations, mutate packages, expand sources, add RAG/vector behavior, activate full mockups, add hidden LLM behavior, alter auth/security behavior, or change the existing same-origin delivery and same-origin signed-reference behavior.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_storage_receipt_authority_freeze
entry_decision: storage_receipt_authority_frozen_runtime_blocked
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
runtime_status: not_implemented
fake_provider_contract_double_status: implemented_tested
provider_storage_authority_result: absent_for_provider_private_signed_url
same_origin_signed_reference_state_precedent: available_not_provider_private_authority
provider_private_signed_url_runtime: false
route_dto_model_migration_ui_change: false
```

Current main contains durable same-origin signed-reference state tables and service logic for `external_export_download_signed_reference`. Those tables are intentionally scoped to the same-origin signed-reference runtime and must not be treated as provider-private signed URL authority by inference. Provider-private signed URL runtime needs its own explicit durable authority before routes are implemented.

## Current Authority Findings

```yaml
existing_same_origin_signed_reference_authority:
  models:
    - L3SignedReferenceToken
    - L3SignedReferenceReceipt
    - L3SignedReferenceRevocation
    - L3SignedReferenceAuditEvent
  service: backend/app/services/layer3_signed_reference_state.py
  migration: backend/alembic/versions/0016_layer3_signed_reference_state.py
  route_family: /api/v1/layer3/handoff/export/download/signed-reference
  authority_status: live_for_same_origin_signed_reference_only
provider_private_signed_url_authority:
  provider_storage_service: absent
  provider_private_receipt_table: absent
  provider_private_revocation_table: absent
  provider_private_audit_table: absent
  provider_private_runtime_route: absent
  authority_status: not_implemented
```

The live same-origin signed-reference state is a precedent for durable idempotency, replay, expiry, revocation, and audit semantics, but it is not a reusable provider-private authority until a later implementation pass explicitly designs compatibility, table ownership, and migration semantics.

## Frozen Future Storage Authority

A future provider-private signed URL runtime must define all of the following before route implementation:

1. provider storage owner and backing mode;
2. server-side artifact materialization owner or reference-only authority;
3. provider object identity contract;
4. provider object lifecycle and cleanup policy;
5. durable receipt storage owner;
6. durable revocation storage owner;
7. durable audit event owner;
8. expiry and replay enforcement owner;
9. idempotency key and conflict policy;
10. stale external export/download readiness reconciliation owner;
11. leak/redaction policy for responses, errors, logs, traces, screenshots, manifests, and audit rows;
12. auth/security policy for operator and external recipient access.

## Candidate Durable State Families

The later runtime pass may choose either a new provider-private state family or a rigorously proven extension of the signed-reference durable state family. Until that choice is made, the only admitted candidate names are planning labels:

```yaml
candidate_new_state_module: backend/app/services/layer3_provider_private_signed_url_state.py
candidate_new_migration: backend/alembic/versions/0022_layer3_provider_private_signed_url_state.py
candidate_rows:
  - L3ProviderPrivateSignedUrlReceipt
  - L3ProviderPrivateSignedUrlRevocation
  - L3ProviderPrivateSignedUrlAuditEvent
  - L3ProviderPrivateSignedUrlObjectAuthority
candidate_row_status: not_implemented
```

If the future implementation chooses to reuse or extend `L3SignedReferenceToken`, `L3SignedReferenceReceipt`, `L3SignedReferenceRevocation`, or `L3SignedReferenceAuditEvent`, that PR must prove that same-origin signed-reference semantics remain unchanged and that provider-private signed URL rows cannot be mistaken for same-origin signed-reference rows.

## Required Runtime-Entry Proof Before Routes

Before adding any provider-private route or DTO, the implementation-entry PR must prove:

- provider storage authority is selected and fail-closed;
- object identity is deterministic from artifact authority and not browser supplied;
- artifact hash and size are revalidated before durable receipt creation;
- stale external export/download readiness fails closed;
- `client_request_id` idempotency is durable and conflict-detecting;
- use/replay is durable and single-use unless a separate replay policy is frozen;
- revocation fail-closes all later use;
- expiry is enforced at use and reflected in status;
- audit rows contain only response-safe authority and hashes;
- raw bearer tokens, provider credentials, raw object keys, buckets, containers, raw local paths, public URLs, and connector/destination payloads are never stored or returned where forbidden;
- same-origin delivery and same-origin signed-reference routes continue to expose no provider-private URL fields.

## Negative Invariants

- no provider/private signed URL runtime route;
- no provider/public URL runtime;
- no public proxy URL runtime;
- no provider storage service;
- no provider-private signed URL model or migration;
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
- no rendered UI control;
- no Playwright configuration change;
- no CI workflow change.

## Recommended Next Action

```yaml
recommended_next_action: freeze_provider_private_route_dto_runtime_entry_after_storage_receipt_authority
if_provider_storage_authority_remains_absent: keep_runtime_blocked
if_runtime_route_or_dto_is_requested_before_storage_authority: stop
if_public_exposure_is_requested: stop_and_create_separate_public_url_or_proxy_freeze
if_connector_or_destination_delivery_is_requested: stop_and_use_connector_destination_runtime_family
```

## Stop Condition

Stop before route or DTO implementation if provider storage authority, durable receipt/revocation/audit rows, selected artifact materialization authority, stale external export/download readiness checks, bearer URL response envelope policy, redaction/leakage policy, or auth/security posture remain unproven.
