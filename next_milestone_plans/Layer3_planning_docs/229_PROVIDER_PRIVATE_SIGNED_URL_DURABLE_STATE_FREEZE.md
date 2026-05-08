# Provider Private Signed URL Storage Receipt Durable State Freeze

Status: current-main planning/control storage and durable-receipt state authority freeze for `provider_private_signed_url_storage_receipt_durable_state_freeze`.

This document follows `228_PROVIDER_PRIVATE_SIGNED_URL_STORAGE_RECEIPT_AUTHORITY_FREEZE.md`. It records the minimum durable-state authority and compatibility posture that must be proved before any `provider-private-signed-url` route/model/migration/service/runtime work can be admitted.

This pass does not add routes, DTOs, models, migrations, services, executable backend tests, rendered UI controls, Playwright runtime behavior, auth/security behavior, or same-origin signed-reference semantics changes. It does not introduce provider credentials, provider network calls, package mutation/reconstruction, source expansion, RAG/vector runtime, full mockup activation, or provider/public URL/public proxy URL runtime.

## Decision

```yaml
selected_planning_mode: provider_private_signed_url_storage_receipt_durable_state_freeze
entry_decision: storage_receipt_durable_state_freeze_runtime_blocked
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

Current main still has same-origin signed-reference durable state, but no provider-private durable state. This freeze is the authority bridge for the storage/receipt layer before any implementation route or schema is admitted.

## Current Authority Findings

```yaml
provider_private_signed_url_authority_precedent:
  same_origin_signed_reference_state:
    models_present: true
    reuse_eligible_without_bridge: false
    note: "same-origin signed-reference behavior is not a valid substitute for provider-private authority"
provider_private_signed_url_storage_receipt_authority:
  route: absent
  dto: absent
  model: absent
  migration: absent
  service: absent
  status: not_implemented
```

## Frozen Durable-State Requirements

Before any provider-private durable implementation, future implementation work must prove the following:

1. `durable_receipt_identity` is deterministic and globally unique per `client_request_id`, artifact authority tuple, and actor.
2. `artifact_authority_binding` requires server-side proof that the artifact is approved, in-bounds, and hash/size validated.
3. `provider_object_identity_binding` binds every receipt to exactly one provider object authority identity and prohibits browser-supplied object identity.
4. `client_request_id_idempotency` is enforced with conflict handling and deterministic duplicate behavior.
5. `receipt_expiry_enforcement` is strict at issue and use time and is observable in status/audit.
6. `revocation_owner` and `revocation_fail_closed` semantics are defined and deny all later use.
7. `replay_single_use_policy` is explicit and rejects duplicate usable receipt attempts unless a later plan changes it.
8. `durable_audit_events` record only response-safe authority hashes and IDs with redaction posture.
9. `failure_and_recovery` behavior is explicit for fake-provider failure modes, stale authority failures, and replay/revocation races.
10. `fake_provider_failure_handling` from the current contract double remains the mandatory precondition test anchor.
11. `same_origin_signed_reference_compatibility` requires no semantic drift: same-origin signed-reference rows and behavior stay unchanged unless separately admitted.
12. `stale_authority_fail_closed` rejects reused rows, stale readiness links, stale artifact hash/size authority, and stale `provider_request_id` combinations.
13. `validation_requirements` include checker, board, manifest/proof lockstep for this and downstream docs.

## Candidate Durable-State Shape

The next implementation branch is expected to materialize one of:

- a dedicated provider-private state service in `backend/app/services/layer3_provider_private_signed_url_state.py`;
- a dedicated migration that adds provider-private durable receipt/revocation/audit rows (for example `backend/alembic/versions/0022_layer3_provider_private_signed_url_state.py`);
- explicit owner service contracts for storage, object identity, idempotency, expiry, revocation, and audit logging.

Candidate model family (admitted naming for the next runtime pass):

- `L3ProviderPrivateSignedUrlReceipt`
- `L3ProviderPrivateSignedUrlObjectAuthority`
- `L3ProviderPrivateSignedUrlRevocation`
- `L3ProviderPrivateSignedUrlAuditEvent`

No file changes are made in this freeze doc.

## Validation Requirements Before Any Runtime Entry

Validation is completed by:

- branch-local checker lockstep after this freeze doc;
- board traceability entry in `next_milestone_plans/layer3_progress_board.md`;
- manifest and workbench proof manifest entries for this freeze key;
- proof list showing the compatibility lock with same-origin signed-reference state and stale/fail-closed behavior;
- explicit negative test list in the contract doc preventing route/DLL/model/migration admission without lockstep authority.

## Recommended Next Action

```yaml
recommended_next_action: write_provider_private_signed_url_storage_receipt_durable_state_contract
if_provider_private_signed_url_authority_remains_absent: keep_runtime_blocked
if_durable_receipt_binding_or_replay_semantics_change: write_contract_before_route_or_dto
if_public_exposure_or_provider_object_network_behavior_requested: stop_for_separate_public_url_or_proxy_freeze
if_route_or_dto_is_requested_before_contract: stop
```

## Stop Condition

Stop before any route/model/migration admission if durable receipt identity, artifact/provider-object binding, `client_request_id` conflict policy, expiry, revocation, replay/fail-closed behavior, audit redaction, or stale-authority rejection remain unproven.
