# 623 - Next External Surface Decision Intake

## Status

Status: planning/control intake for `await_operator_decision_for_next_external_surface_after_selected_server_owned_local_outbox_target_satisfied_sync`.

Doc: `623_NEXT_EXTERNAL_SURFACE_DECISION_INTAKE.md`.

Current-main checkpoint at intake creation: `2e30146544409eea5bd194485510ad9f5d17bb1b`.

Prior current-main sync: `622_TARGET_SELECTION_SELECTED_OUTBOX_CURRENT_MAIN_SYNC.md`.

Satisfied selected target: `server_owned_local_delivery_outbox_destination`.

Satisfied selected target freeze: `608_SERVER_OWNED_LOCAL_OUTBOX_REAL_WRITE_ADMISSION_FREEZE.md`.

Runtime status: `no_new_runtime_next_external_surface_decision_required`.

Implementation-entry freeze written for next external surface: false.

Selected next external surface: `null`.

Selected implementation action: `none`.

Live behavior change in this pass: false.

## Current Authority

Current main already satisfies the operator-selected server-owned local outbox destination through the existing `608` freeze and current-main runtime. The satisfied behavior is bounded to one server-owned local outbox artifact/manifest write under backend-controlled storage.

This intake exists because the active Layer 3 objective is still not complete, but implementation cannot continue into any new external/provider/destination/package/source/RAG/auth/frontend surface until exactly one next surface or action is named and separately frozen.

This is not a broad no-runtime audit. It is the concrete handoff record for the next operator decision after the selected local/server-owned outbox target was satisfied and synced.

## Decision To Fill

The next implementation-entry freeze may be written only after the operator fills exactly one record:

```yaml
next_surface_identity: null
next_surface_owner: null
next_surface_class: null
operator_purpose: null
authority_source: null
artifact_family: null
credential_model: null
destination_address_model: null
side_effect_boundary: null
idempotency_contract: null
failure_lifecycle: null
receipt_audit_contract: null
exposure_security_posture: null
operator_surface: null
proof_architecture: null
selection_complete: false
implementation_entry_freeze_written: false
```

Acceptable `next_surface_class` values must be one exact class, such as:

- `real_provider_private_delivery`;
- `server_configured_external_destination_write`;
- `named_connector_invocation`;
- `provider_public_delivery_use`;
- `named_package_action`;
- `named_source_family_expansion`;
- `named_rag_vector_index`;
- `named_auth_security_surface`;
- `named_frontend_durable_authority`; or
- another single operator-named class with the same authority and proof fields filled.

## Required Freeze Shape After Selection

The next implementation-entry freeze must:

1. Copy the filled decision record verbatim.
2. Name one allowed owner service seam.
3. Name one route/API entrypoint or one explicit internal-only harness.
4. Name one durable receipt/audit contract where the selected surface has side effects or lifecycle state.
5. Name exact allowed files, routes, services, tables, and tests for the first tranche.
6. Define stop conditions before code edits.
7. Define focused API proof for authority, stale state, wrong session/artifact/basis, idempotency replay, same-key conflict, same-basis different-key conflict, redaction, and disabled side effects.
8. Require headed and headless E2E proof if rendered status/history behavior changes.
9. Preserve every unselected blocked surface.

## Anti-Cycle Rule

Do one live authority check before writing the next freeze. If `project6-origin/main`, open PR state, or `tools/l3-progress-check.py` contradicts this intake, stop and reconcile the contradiction.

If live authority still matches this intake, do not run another broad no-runtime audit. Either:

- fill exactly one next-surface decision record and write the separate freeze; or
- keep runtime blocked and report that no next external surface is selected.

## Non-Admission Boundary

This intake admits no runtime behavior, backend route behavior, service behavior, response-model shape change, schema/model/migration change, rendered UI behavior, real connector invocation, destination write beyond the already-satisfied server-owned local outbox target, connector-run creation, connector-run-target creation, credential use, network write, provider-public delivery/use, raw public URL exposure, raw token exposure, caller-supplied destination path/URL, package mutation/reconstruction, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, or generic downstream dispatch.

## Next Posture

The next whole-project posture is `await_filled_next_external_surface_decision_record_after_selected_server_owned_local_outbox_target_sync`.

Implementation-entry remains blocked until the decision record above has exactly one named `next_surface_identity`, one named `next_surface_class`, explicit authority and proof fields, and a separate implementation-entry freeze.
