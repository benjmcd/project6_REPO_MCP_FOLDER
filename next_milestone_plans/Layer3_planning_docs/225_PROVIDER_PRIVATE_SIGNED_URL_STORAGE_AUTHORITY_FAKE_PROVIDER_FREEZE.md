# Provider Private Signed URL Storage Authority Fake Provider Freeze

Status: current-main planning/control storage-authority and fake-provider freeze for `provider_private_signed_url_storage_authority_fake_provider_freeze`.

This document follows `224_PROVIDER_PRIVATE_SIGNED_URL_IMPLEMENTATION_ENTRY_FREEZE.md`. It records the current-main provider/storage authority audit and freezes the fake-provider contract requirements that must exist before any provider-private signed URL runtime implementation. It does not implement runtime behavior, change routes, DTOs, models, migrations, services, executable tests, rendered UI controls, Playwright configuration, CI workflow, source handling, package behavior, connector behavior, provider object behavior, RAG/vector behavior, mockup behavior, auth/security behavior, hidden LLM behavior, or frontend-only durable authority.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_storage_authority_fake_provider_freeze
entry_decision: authority_freeze_runtime_blocked
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
runtime_status: not_implemented
provider_storage_authority_result: no_current_main_provider_storage_authority
provider_service_surface_status: absent
fake_provider_contract_double_status: required_not_implemented
runtime_implementation_allowed: false
```

Current-main inspection found no provider/storage service implementation surface for Layer 3 provider-private signed URLs. The live delivery authority remains same-origin external export/download delivery plus same-origin signed-reference delivery. Provider URL fields remain blocked or non-admitted on the relevant request/response surfaces.

This freeze therefore cannot admit runtime implementation. It only records the authority gap and the minimum fake-provider contract shape required before a later runtime contract or implementation PR.

## Current-Main Evidence

```yaml
current_main_evidence:
  provider_service_modules:
    status: absent
    inspected_globs:
      - backend/app/services/*provider*
      - backend/app/services/*storage*
  same_origin_delivery:
    status: live_bounded
    evidence:
      - backend/app/api/layer3.py
      - backend/app/services/layer3_workbench.py
      - backend/tests/test_layer3_api.py
      - backend/tests/test_layer3_external_export_response.py
      - backend/tests/test_layer3_bounded_e2e.py
  same_origin_signed_reference:
    status: live_bounded
    evidence:
      - backend/app/api/layer3.py
      - backend/app/services/layer3_workbench.py
      - backend/app/services/layer3_signed_reference_state.py
      - backend/tests/test_layer3_api.py
  provider_private_signed_url:
    status: not_implemented
  provider_public_url:
    status: not_implemented
  public_proxy_url:
    status: not_implemented
```

The evidence proves non-admission and blocked authority. It does not prove provider storage readiness, provider credential handling, object-store semantics, network behavior, provider ACL behavior, URL generation correctness, revocation behavior, CORS/CSP behavior, cache behavior, or recipient access security.

## Fake Provider Contract Requirements

A future implementation-entry contract must specify a deterministic fake-provider or provider-contract-double before runtime code. The fake provider must be used by tests instead of any real provider network, credential, bucket, container, or account.

Required fake-provider capabilities:

1. deterministic provider object identity from artifact authority, not from wall-clock time or random provider state;
2. artifact reference or materialization operation with explicit hash and size verification;
3. private signed URL creation with explicit TTL, expiry timestamp, recipient/access scope, and redacted receipt id;
4. revocation operation that fail-closes subsequent use;
5. replay/use counter or replay-denial receipt behavior matching the selected policy;
6. stale-authority rejection when current artifact hash, size, package, handoff/export, APS dispatch, or external export/download authority no longer matches;
7. deterministic provider failure injection for unavailable provider, denied credentials, expired URL, revoked URL, malformed authority, and stale object state;
8. redacted audit receipt for create, use, revoke, expiry, replay denial, and provider failure;
9. no raw provider credentials, raw signatures, raw object keys, local paths, buckets, containers, tokens, or full bearer URLs in logs, errors, traces, screenshots, manifests, or existing same-origin responses;
10. no connector run creation, destination write, source expansion, package mutation, RAG/vector state, full mockup activation, hidden LLM planning, or auth/security behavior change.

## Future Provider Storage Authority To Prove

A later runtime contract must prove:

- provider/storage owner and backing implementation;
- whether provider objects are copied, referenced, or materialized by server-owned write-through;
- provider object namespace ownership and collision policy;
- credentials and secret-loading owner;
- TTL and expiry authority;
- revocation owner and failure semantics;
- audit/receipt storage owner;
- cache-control, referrer-policy, content-disposition, CORS, and CSP owner;
- recipient access model and auth/security boundary;
- cleanup/expiry lifecycle;
- local development and CI fake-provider mode;
- production/nonlocal provider mode, if any, with explicit stop-before-merge security review.

## Candidate Boundary

```yaml
candidate_route_namespace: /api/v1/layer3/handoff/export/download/provider-private-signed-url
candidate_owner_service: explicit_future_decision_required
candidate_provider_contract_double: explicit_future_decision_required
candidate_db_state: explicit_future_decision_required
candidate_artifact_state: explicit_future_decision_required
candidate_audit_receipt_state: explicit_future_decision_required
```

This is still a planning namespace only. No endpoint, service, provider adapter, storage table, provider object, provider credential, URL generator, revocation handler, or fake-provider implementation is live.

## Mode Isolation

```yaml
mode_isolation:
  provider_private_signed_url:
    selected_for_future_runtime_entry: true
    runtime_allowed_in_this_pass: false
  provider_public_url:
    selected_for_future_runtime_entry: false
    runtime_allowed_in_this_pass: false
  public_proxy_url:
    selected_for_future_runtime_entry: false
    runtime_allowed_in_this_pass: false
  same_origin_external_export_download:
    current_behavior_preserved: true
  same_origin_signed_reference:
    current_behavior_preserved: true
  connector_destination_dispatch:
    selected: false
    runtime_allowed_in_this_pass: false
```

## Negative Invariants

- no provider/private signed URL runtime;
- no provider/public URL runtime;
- no public proxy URL runtime;
- no provider adapter or fake-provider implementation;
- no provider object write, copy, ACL, bucket, container, key, credential, or network behavior;
- no provider URL fields on existing same-origin delivery or signed-reference routes;
- no same-origin delivery or same-origin signed-reference semantics change;
- no external connector invocation;
- no destination write;
- no generic downstream dispatch;
- no source adapter registry;
- no local upload;
- no local-directory ingestion;
- no web connector retrieval;
- no broad source expansion;
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
- no production service behavior change;
- no executable test behavior change;
- no rendered UI control;
- no Playwright configuration change;
- no CI workflow change.

## Recommended Next Action

```yaml
recommended_next_action: write_provider_private_signed_url_contract_only_after_storage_authority_and_fake_provider_are_specified
if_provider_storage_authority_remains_absent: keep_runtime_blocked
if_fake_provider_contract_is_not_testable_without_real_network: stop_and_redesign_contract
if_public_exposure_is_requested: stop_and_create_separate_public_url_or_proxy_freeze
if_connector_or_destination_delivery_is_requested: stop_and_use_connector_destination_runtime_family
```

## Stop Condition

Stop before runtime implementation if provider/storage authority, fake-provider contract architecture, selected artifact-family authority, provider object materialization policy, TTL/revocation/audit behavior, access authority, leak controls, stale-authority tests, route/API contract, owner service, DB/artifact semantics, or auth/security posture remain unproven.
