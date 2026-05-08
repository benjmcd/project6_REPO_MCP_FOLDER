# Provider Private Signed URL Contract Only Freeze

Status: current-main planning/control contract-only freeze for `provider_private_signed_url_contract_only_freeze`.

Supersession note: `227_PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_CONTRACT.md` implements and tests the deterministic fake-provider contract double that this document listed as a required future step. The provider-private signed URL runtime routes, durable provider/storage authority, models, migrations, rendered UI controls, and route DTO wiring remain blocked.

This document follows `225_PROVIDER_PRIVATE_SIGNED_URL_STORAGE_AUTHORITY_FAKE_PROVIDER_FREEZE.md`. It freezes the exact candidate route, DTO, owner-service, state, and negative-invariant contract shape for a future provider-private signed URL runtime, but it does not implement runtime behavior, change routes, DTOs, models, migrations, services, executable tests, rendered UI controls, Playwright configuration, CI workflow, source handling, package behavior, connector behavior, provider object behavior, RAG/vector behavior, mockup behavior, auth/security behavior, hidden LLM behavior, or frontend-only durable authority.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_contract_only_freeze
entry_decision: contract_frozen_runtime_blocked
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
runtime_status: not_implemented
provider_storage_authority_result: no_current_main_provider_storage_authority
fake_provider_contract_double_status: required_not_implemented
candidate_route_namespace: /api/v1/layer3/handoff/export/download/provider-private-signed-url
contract_only: true
runtime_implementation_allowed: false
```

Current main still has only same-origin external export/download delivery and same-origin signed-reference delivery. The provider-private signed URL route family described here is a future contract boundary only. No endpoint, DTO, owner service, provider adapter, fake provider, storage table, provider object, provider credential, signed URL generator, revocation handler, or rendered control is live.

## Current Live Baseline

```yaml
live_same_origin_routes:
  prepare: /api/v1/layer3/handoff/export/download/prepare
  deliver: /api/v1/layer3/handoff/export/download/deliver
  signed_reference_generate: /api/v1/layer3/handoff/export/download/signed-reference/generate
  signed_reference_use: /api/v1/layer3/handoff/export/download/signed-reference/use
live_owner_service:
  module: backend/app/services/layer3_workbench.py
  same_origin_delivery_function: external_export_download_deliver
  same_origin_signed_reference_generate_function: external_export_download_generate_signed_reference
  same_origin_signed_reference_use_function: external_export_download_use_signed_reference
provider_private_signed_url_live: false
```

The future provider-private signed URL path must remain parallel to the live same-origin delivery and same-origin signed-reference paths. It must not rename, extend, bypass, or silently upgrade those live paths.

## Candidate Route Contract

```yaml
candidate_routes:
  prepare:
    method: POST
    path: /api/v1/layer3/handoff/export/download/provider-private-signed-url/prepare
    purpose: create_or_preview_provider_private_signed_url_authority
    live_now: false
  use:
    method: POST
    path: /api/v1/layer3/handoff/export/download/provider-private-signed-url/use
    purpose: redeem_or_validate_provider_private_signed_url_receipt
    live_now: false
  revoke:
    method: POST
    path: /api/v1/layer3/handoff/export/download/provider-private-signed-url/revoke
    purpose: revoke_provider_private_signed_url
    live_now: false
  status:
    method: GET
    path: /api/v1/layer3/handoff/export/download/provider-private-signed-url/status/{provider_signed_url_receipt_id}
    purpose: inspect_redacted_provider_private_signed_url_state
    live_now: false
```

The `prepare` route is the first candidate runtime entry point if implementation later becomes eligible. The `use`, `revoke`, and `status` routes are frozen as required contract companions, not as automatic first-slice implementation scope.

## Candidate Request DTOs

```yaml
prepare_request_required_fields:
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
  - source_artifact_ref
  - source_artifact_hash
  - source_artifact_size_bytes
prepare_request_enums:
  external_export_download_state:
    - external_export_download_prepared
  export_download_target:
    - aps_evidence_bundle_download_reference
  download_mode:
    - reference_only_prepare
  delivery_mode:
    - provider_private_signed_url
  operator_decision:
    - prepare_provider_private_signed_url
prepare_request_optional_fields:
  - decision_notes
  - recipient_scope
  - requested_ttl_seconds
  - provider_policy_ref
use_request_required_fields:
  - provider_signed_url_receipt_id
  - provider_private_signed_url_token
revoke_request_required_fields:
  - provider_signed_url_receipt_id
  - operator_decision
  - revocation_reason
status_request_required_fields:
  - provider_signed_url_receipt_id
```

Forbidden request fields include provider credentials, provider bucket/container/key, raw local filesystem path, destination id, destination URL, connector payload, connector secret, source upload, local directory, web connector, package mutation payload, RAG/vector settings, prompt/model/provider settings, auth/security overrides, browser durable authority, public URL, public proxy URL, same-origin download URL, and same-origin signed-reference token.

## Candidate Response DTOs

```yaml
prepare_response_required_fields:
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
  - source_artifact_ref
  - source_artifact_hash
  - source_artifact_size_bytes
  - authority_rail
  - audit_receipt
  - next_allowed_actions
  - next_state
response_forbidden_fields:
  - provider_credentials
  - provider_secret
  - raw_provider_signature
  - raw_provider_object_key
  - raw_local_path
  - provider_bucket
  - provider_container
  - public_url
  - public_proxy_url
  - connector_run_id
  - destination_write_id
  - package_payload
  - source_expansion_state
  - rag_vector_state
  - prompt_or_model_payload
  - auth_internal_state
```

If a future response must return a usable provider URL to an external recipient, the runtime PR must define a separate safe delivery envelope and redaction policy before implementation. This contract-only freeze does not admit returning a bearer URL in existing same-origin workbench responses.

## Candidate Owner Service Contract

```yaml
candidate_owner_module: backend/app/services/layer3_provider_private_signed_url.py
candidate_owner_functions:
  - provider_private_signed_url_prepare
  - provider_private_signed_url_use
  - provider_private_signed_url_revoke
  - provider_private_signed_url_status
candidate_fake_provider_module: backend/app/services/layer3_provider_private_signed_url_fake_provider.py
live_now: false
```

The future owner service must not be added until provider/storage authority and fake-provider architecture are implemented and tested in a separate runtime pass. The live `backend/app/services/layer3_workbench.py` same-origin delivery logic must remain the authority for existing same-origin delivery and signed-reference behavior.

## Candidate State Contract

```yaml
candidate_states:
  prepared: provider_private_signed_url_prepared
  delivered: provider_private_signed_url_delivered
  used: provider_private_signed_url_used
  revoked: provider_private_signed_url_revoked
  expired: provider_private_signed_url_expired
  blocked: provider_private_signed_url_blocked
  conflict: provider_private_signed_url_conflict
candidate_idempotency:
  prepare: client_request_id plus artifact authority plus recipient scope
  revoke: provider_signed_url_receipt_id plus revocation reason
candidate_replay_policy:
  use: explicit_future_decision_required
candidate_revocation_policy:
  revoke_fail_closes_future_use: true
candidate_stale_authority_policy:
  hash_size_package_handoff_export_aps_dispatch_readiness_mismatch_fails_closed: true
```

Candidate DB state, file/artifact writes, provider object materialization, cleanup lifecycle, and audit receipt storage are still explicit future decisions. No model or migration is admitted by this pass.

## Required Tests Before Runtime

A future runtime PR must include focused tests for:

1. OpenAPI request/response schema and forbidden request fields;
2. fake-provider deterministic object identity and hash/size validation;
3. idempotent prepare;
4. stale external export/download readiness rejection;
5. stale artifact hash and size rejection;
6. provider failure injection;
7. TTL expiry;
8. revocation and post-revocation use denial;
9. replay policy;
10. redaction in response bodies, errors, logs, traces, screenshots, manifests, and audit receipts;
11. no provider URL fields on existing same-origin delivery or signed-reference routes;
12. no connector/destination/source/package/RAG/mockup/hidden-LLM/auth-security side effects;
13. headed/headless and light/dark/workbench proof if rendered controls are admitted.

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
recommended_next_action: implement_fake_provider_contract_tests_before_runtime_routes
if_provider_storage_authority_remains_absent: keep_runtime_blocked
if_runtime_route_or_dto_is_requested_before_fake_provider_tests: stop
if_public_exposure_is_requested: stop_and_create_separate_public_url_or_proxy_freeze
if_connector_or_destination_delivery_is_requested: stop_and_use_connector_destination_runtime_family
```

## Stop Condition

Stop before runtime implementation if fake-provider tests, provider/storage authority, selected artifact-family authority, provider object materialization policy, TTL/revocation/audit behavior, access authority, leak controls, stale-authority tests, owner service, DB/artifact semantics, or auth/security posture remain unproven.
