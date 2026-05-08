# Provider Private Signed URL Storage Receipt Durable State Contract

Status: current-main planning/control durable-state contract for `provider_private_signed_url_storage_receipt_durable_state_contract`.

This document follows `229_PROVIDER_PRIVATE_SIGNED_URL_DURABLE_STATE_FREEZE.md`. It defines the contract envelope to be passed to the next runtime PR for provider-private storage receipt state, before route/DTO/model/migration admission.

This contract does not add runtime routes, DTOs, models, migrations, services, executable backend tests, rendered controls, Playwright behavior, provider credentials, provider network calls, package mutation/reconstruction, source expansion, RAG/vector behavior, full mockup activation, auth/security behavior, or provider/public URL/public proxy URL runtime.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_storage_receipt_durable_state_contract
entry_decision: storage_receipt_durable_state_contract_runtime_blocked
selected_runtime_family: provider_public_url_runtime
selected_runtime_mode: provider_private_signed_url
named_use_case_selected: external_downstream_recipient_private_artifact_delivery
runtime_status: not_implemented
fake_provider_contract_double_status: implemented_tested
provider_storage_authority_result: absent_for_provider_private_signed_url
same_origin_signed_reference_state_precedent: available_not_provider_private_authority
provider_private_signed_url_runtime: false
route_dto_model_migration_ui_change: false
contract_family: storage_receipt
```

## Contract Scope

This contract freezes the exact state obligations for the next runtime PR and intentionally remains planning-only.

```yaml
candidate_state_module: backend/app/services/layer3_provider_private_signed_url_state.py
candidate_migration: backend/alembic/versions/0022_layer3_provider_private_signed_url_state.py
candidate_states:
  - L3ProviderPrivateSignedUrlReceipt
  - L3ProviderPrivateSignedUrlObjectAuthority
  - L3ProviderPrivateSignedUrlRevocation
  - L3ProviderPrivateSignedUrlAuditEvent
```

## Required State Semantics

1. `durable_receipt_identity`
   - Deterministically derived from `client_request_id`, artifact authority tuple, and artifact hash/size.
2. `artifact_authority_binding`
   - Receipt rows reference server authority of approved Layer 3 external export/download artifacts only.
3. `provider_object_identity_binding`
   - Receipt rows reference deterministic provider-object authority and do not accept client-generated object identifiers.
4. `client_request_id_idempotency`
   - Idempotent prepare for same `client_request_id` + authority tuple; conflict on mismatched repeat requests.
5. `expiry_enforcement`
   - Expired receipts are denied at issue/use and surfaced in status.
6. `revocation_enforcement`
   - Revocation is authoritative and fail-closed for all future use attempts.
7. `replay_policy_single_use`
   - Use/replay semantics are single-use unless contract explicitly expands later.
8. `durable_audit_events`
   - Redacted event records include provider-private receipt lifecycle and authorization failure class.
9. `stale_authority_fail_closed`
   - Stale external export/download readiness and stale hash/size authorities cannot reopen routes or status.
10. `fake_provider_failure_anchoring`
   - Deterministic failure-injection behavior from the fake-provider contract remains the pre-admission safety anchor for implementation.
11. `same_origin_compatibility_guard`
   - Existing same-origin signed-reference model/service behavior can remain, but no cross-mode aliasing or privilege carry is allowed.
12. `validation_requirements`
   - proof lock, checker lock, and manifest lock are required before route/model/migration admission.

## Runtime-Entry Contract Checklist

- provider/storage owner and storage-owner boundaries;
- provider object authority owner and lifecycle owner;
- durable receipt owner and durable revocation owner;
- durable audit event owner and redaction policy owner;
- replay conflict owner and idempotency conflict owner;
- stale external export/download readiness owner and fail-closed behavior owner;
- expiry owner and timebase owner.

## Negative Invariants for this Contract

- no provider/private signed URL runtime route;
- no provider/public URL runtime;
- no public proxy URL runtime;
- no provider object write/copy/ACL/network behavior;
- no provider URL fields on same-origin route surfaces;
- no same-origin delivery or same-origin signed-reference semantics change;
- no provider/private signed URL model or migration;
- no provider storage authority claim without contract lock;
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
- no auth/security behavior change;
- no route/API behavior change;
- no DTO behavior change;
- no rendered UI control;
- no Playwright configuration change;
- no CI workflow change;
- no frontend-only durable authority.

## Validation Requirements

Before any implementation PR that adds:

- routes,
- DTOs,
- models,
- migrations,
- owner services,

the following must be proven:

1. Checker lockstep for docs `229` and `230`.
2. Progress board update containing both freeze and contract keys.
3. Current `manifest`/`proof` entries for both keys and both lock objects.
4. Negative tests that prove:
   - idempotent `client_request_id` conflict policy,
   - stale authority fail-closed behavior,
   - single-use replay denial,
   - expiry and revocation enforcement,
   - provider-object binding enforcement,
   - redaction of secret-like fields.

## Recommended Next Action

```yaml
recommended_next_action: implement_storage_receipt_state_service_and_migration_with_contract
if_storage_receipt_durable_state_contract_not_locked: stop
if_route_or_dto_or_model_is_requested_before_contract_lock: stop
if_same_origin_signed_reference_semantics_are_mutated: stop
if_auth_or_leakage_posture_remains_unproven: stop
```

## Stop Condition

Stop before runtime entry unless all durable-state contract obligations are proven with redaction, idempotency, stale fail-closed, expiry, revocation, replay, audit, and provider object binding tests.
