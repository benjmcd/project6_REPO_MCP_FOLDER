# Provider Private Signed URL Implementation Entry Freeze

Status: current-main planning/control implementation-entry freeze for `provider_private_signed_url_implementation_entry_freeze`.

This document follows `223_PROVIDER_PRIVATE_SIGNED_URL_USE_CASE_SELECTION.md`. It freezes the minimum implementation-entry authority that must exist before any future `provider_private_signed_url` runtime work, but it does not implement runtime behavior, change routes, DTOs, models, migrations, services, executable tests, rendered UI controls, Playwright configuration, CI workflow, source handling, package behavior, connector behavior, provider object behavior, RAG/vector behavior, mockup behavior, auth/security behavior, hidden LLM behavior, or frontend-only durable authority.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_implementation_entry_freeze
entry_decision: implementation_entry_frozen_runtime_blocked
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
runtime_status: not_implemented
provider_storage_authority_status: unverified
selected_artifact_family_status: external_export_download_artifact_candidate_only
candidate_route_namespace: /api/v1/layer3/handoff/export/download/provider-private-signed-url
fake_provider_contract_double_required: true
runtime_implementation_allowed: false
```

The selected use case remains the one chosen in doc `223`: an operator needs to share one already-approved Layer 3 external export/download artifact with an external downstream recipient who cannot use the same-origin review UI session.

This freeze does not make runtime implementation eligible. It records the future entry contract and keeps runtime blocked because provider/storage authority remains unverified.

## Canonical Authority Order

1. live `project6-origin/main` source code, tests, models, migrations, API routes, service implementations, and checker behavior;
2. current same-origin external export/download delivery and same-origin signed-reference implementation;
3. docs `187`, `188`, and `213` for provider/public URL non-admission and authority-discovery closeout;
4. docs `221`, `222`, and `223` for current-main runtime readiness, named use-case selection, and selected provider-private signed URL use case;
5. this freeze document;
6. future provider, storage, auth/security, and rendered UI evidence only after it is proven in source/tests.

Planning prose, mockups, session logs, and external handoff notes are not runtime authority unless later reconciled against source and tests.

## Entry Contract To Prove Before Runtime

A later implementation PR must prove all of the following before adding runtime code:

1. provider/storage owner and backing implementation;
2. exact server-side artifact family, row authority, artifact hash authority, and artifact size authority;
3. exact route, request DTO, response DTO, and OpenAPI contract;
4. owner service/function and state-transition contract;
5. DB rows read, DB rows written, and idempotency keys or durable request identifiers;
6. files/artifacts read, files/artifacts written, and whether provider object materialization is write-through or reference-only;
7. idempotency, replay, concurrency, stale-state, expiry, revocation, cancellation, and recovery semantics;
8. fake-provider or provider-contract-double architecture for deterministic tests;
9. leak-control and redaction rules for logs, error bodies, traces, screenshots, manifests, audit rows, and response fields;
10. cache-control, referrer-policy, content-disposition, CORS, and CSP posture;
11. audit/receipt contract for issuance, use, expiry, revocation, failure, and replay denial;
12. auth/security posture for operator authority and external recipient access;
13. negative cross-mode tests proving same-origin signed references cannot be upgraded into provider URLs;
14. headed/headless and light/dark/workbench proof plan if rendered controls are admitted;
15. explicit stop condition for any unresolved provider, storage, access, leakage, revocation, stale-authority, or auth/security question.

## Candidate Route Boundary

The candidate route namespace is:

```yaml
candidate_route_namespace: /api/v1/layer3/handoff/export/download/provider-private-signed-url
candidate_operation_family:
  prepare_or_create: true
  use_or_redeem: explicit_future_decision_required
  revoke: explicit_future_decision_required
  status_or_audit: explicit_future_decision_required
```

This is a planning namespace only. No endpoint is live. A future runtime PR must still freeze the exact method/path names, request DTOs, response DTOs, status codes, error codes, OpenAPI examples, and owner service before implementation.

The future request contract must not accept provider credentials, provider bucket/container names, provider object keys, raw local filesystem paths, connector targets, destination identifiers, browser-generated artifact bytes, package mutation payloads, source adapter configuration, RAG/vector settings, prompt/model/provider settings, or auth/security overrides.

The future response contract must not expose provider credentials, unredacted signatures outside the intended private URL, raw provider object keys, raw local filesystem paths, connector/destination state, package payload bytes, source expansion state, RAG/vector state, hidden planning prompts, auth internals, or provider URL fields on existing same-origin routes.

## Required State Model

```yaml
future_state_model_required:
  source_rows_read: existing_layer3_session_package_handoff_export_and_artifact_authority_only
  source_rows_written: explicit_future_decision_required
  files_read: already_approved_external_export_download_artifact_only
  files_written: explicit_future_decision_required_for_provider_object_materialization
  provider_rows_written: explicit_future_decision_required
  connector_rows_written: false
  destination_rows_written: false
  source_expansion_rows_written: false
  rag_vector_rows_written: false
  package_payload_mutation: false
```

Current same-origin delivery and same-origin signed references remain separate delivery modes. They must not be renamed, represented, or upgraded as provider-private signed URLs.

## Runtime Blockers

Runtime remains blocked until all blockers are resolved in source/tests:

- provider/storage authority is unverified;
- selected artifact family is only a candidate;
- provider object materialization policy is not frozen;
- TTL, expiry, revocation, and replay semantics are not implemented;
- fake-provider contract double is not designed or tested;
- audit/receipt schema and redaction contract are not frozen;
- auth/security posture for external recipient access is not proven;
- cache-control, referrer-policy, content-disposition, CORS, and CSP behavior is not proven;
- rendered controls, themes, and headed/headless proof are not admitted.

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
  same_origin_signed_reference:
    current_behavior_preserved: true
    renamed_or_represented_as_provider_private_url: false
  same_origin_external_export_download:
    current_behavior_preserved: true
    provider_url_fields_added: false
  connector_destination_dispatch:
    selected: false
    runtime_allowed_in_this_pass: false
```

## Negative Invariants

- no provider/private signed URL runtime;
- no provider/public URL runtime;
- no public proxy URL runtime;
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
recommended_next_action: prove_provider_storage_authority_and_fake_provider_contract_before_runtime
if_provider_storage_authority_remains_unverified: keep_runtime_blocked
if_exact_route_or_dto_is_requested_without_storage_authority: stop_and_write_contract_only_no_runtime
if_public_exposure_is_requested: stop_and_create_separate_public_url_or_proxy_freeze
if_connector_or_destination_delivery_is_requested: stop_and_use_connector_destination_runtime_family
```

## Stop Condition

Stop before runtime implementation if provider/storage authority, selected artifact-family authority, provider object materialization policy, TTL/revocation/audit behavior, access authority, fake-provider test architecture, leak controls, stale-authority tests, route/API contract, owner service, DB/artifact semantics, or auth/security posture remain unproven.
