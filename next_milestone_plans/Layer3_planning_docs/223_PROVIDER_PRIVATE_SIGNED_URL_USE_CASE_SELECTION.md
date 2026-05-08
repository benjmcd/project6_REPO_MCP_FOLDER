# Provider Private Signed URL Use Case Selection

Status: current-main planning/control use-case selection for `provider_private_signed_url_use_case_selection`.

This document follows `222_NAMED_RUNTIME_USE_CASE_SELECTION_GATE.md`. It selects one concrete operator/product use case for future implementation-entry planning, but it does not implement runtime behavior, change routes, DTOs, models, migrations, services, executable tests, rendered UI controls, Playwright configuration, CI workflow, source handling, package behavior, connector behavior, provider object behavior, RAG/vector behavior, mockup behavior, auth/security behavior, hidden LLM behavior, or frontend-only durable authority.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_use_case_selection
entry_decision: use_case_selected_implementation_blocked
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
runtime_status: not_implemented
implementation_entry_freeze_required: true
provider_storage_authority_status: unverified
runtime_implementation_allowed: false
```

The selected use case is:

> An operator needs to share one already-approved Layer 3 external export/download artifact with an external downstream recipient who cannot use the same-origin review UI session, while preserving server-side artifact authority, short-lived private access, revocation/audit requirements, and no public indexing or connector/destination dispatch.

This selection is not a runtime admission. It only establishes the next implementation-entry freeze target. Runtime remains blocked until provider/storage authority, artifact-family authority, exposure model, access authority, TTL/revocation/audit behavior, fake-provider test architecture, leak controls, and auth/security posture are proven.

## Why This Use Case Comes First

This is the least speculative named runtime use case after the current-main gate because:

- current main already has same-origin artifact delivery and same-origin signed-reference behavior;
- docs `187`, `188`, and `213` already identify `provider_private_signed_url` as a candidate mode while keeping it blocked;
- the gap is concrete: same-origin delivery requires the app/session boundary, but the selected recipient is outside that boundary;
- `provider_private_signed_url` is narrower than `provider_public_url` and `public_proxy_url` because it avoids public ACLs, proxy semantics, and public indexing by default;
- it does not require connector/destination dispatch, package mutation, source expansion, broad qualitative/RAG behavior, full mockup activation, or auth/security runtime changes in this selection pass.

## Current Authority

```yaml
current_authority:
  same_origin_delivery_and_signed_reference:
    status: live_bounded
    evidence:
      - backend/app/services/layer3_workbench.py
      - backend/tests/test_layer3_api.py
      - backend/tests/test_layer3_bounded_e2e.py
      - next_milestone_plans/Layer3_planning_docs/187_PROVIDER_PUBLIC_URL_ENTRY_FREEZE.md
      - next_milestone_plans/Layer3_planning_docs/188_PROVIDER_PUBLIC_URL_ENTRY_CONTRACT.md
      - next_milestone_plans/Layer3_planning_docs/213_PROVIDER_PUBLIC_URL_AUTHORITY_DISCOVERY_CLOSEOUT.md
  provider_storage_authority:
    status: unverified
    consequence: runtime_blocked
  selected_artifact_family:
    status: not_frozen_for_provider_runtime
    consequence: implementation_entry_freeze_required
  exposure_classification:
    status: private_only_candidate
    consequence: public_provider_url_and_public_proxy_url_remain_deferred
```

## Future Implementation-Entry Freeze Requirements

A later implementation-entry freeze for this use case must include:

1. provider/storage owner and allowed backing implementation;
2. selected artifact family and exact server-side artifact authority;
3. route/API request and response schema;
4. owner service/function and state-transition contract;
5. DB rows read and written;
6. files/artifacts read and written;
7. idempotency, replay, concurrency, stale-state, expiry, revocation, and recovery semantics;
8. fake-provider or provider-contract-double test architecture;
9. leak-control and redaction contract for logs, error bodies, screenshots, traces, manifests, and response fields;
10. cache-control, referrer-policy, content-disposition, CORS, and CSP posture;
11. audit/receipt contract;
12. auth/security posture for recipient access and operator authority;
13. negative tests proving no cross-mode upgrade from same-origin signed references;
14. headed/headless and light/dark/workbench proof plan if rendered controls are admitted;
15. explicit stop condition for any unresolved provider, storage, access, leakage, or security authority.

## Mode Isolation

```yaml
mode_isolation:
  provider_private_signed_url:
    selected_for_future_entry_freeze: true
    runtime_allowed_in_this_pass: false
  provider_public_url:
    selected_for_future_entry_freeze: false
    runtime_allowed_in_this_pass: false
  public_proxy_url:
    selected_for_future_entry_freeze: false
    runtime_allowed_in_this_pass: false
  same_origin_signed_reference:
    current_behavior_preserved: true
    renamed_or_represented_as_provider_url: false
  connector_destination_dispatch:
    selected: false
    runtime_allowed_in_this_pass: false
```

## Negative Invariants

- no provider/private signed URL runtime;
- no provider/public URL runtime;
- no public proxy URL runtime;
- no provider object write, copy, ACL, bucket, container, key, or credential behavior;
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
recommended_next_action: write_provider_private_signed_url_implementation_entry_freeze
if_provider_storage_authority_remains_unverified: keep_runtime_blocked
if_public_exposure_is_requested: stop_and_create_separate_public_url_or_proxy_freeze
if_connector_or_destination_delivery_is_requested: stop_and_use_connector_destination_runtime_family
```

## Stop Condition

Stop before runtime implementation if the next task does not prove provider/storage authority, selected artifact-family authority, private exposure classification, access authority, TTL/revocation/audit behavior, fake-provider test architecture, leak controls, stale-authority tests, route/API contract, owner service, DB/artifact semantics, and auth/security posture for `provider_private_signed_url`.
