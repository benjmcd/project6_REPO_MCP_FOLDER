# 623 - Next External Surface Decision Intake

## Status

Status: filled planning/control intake for `server_configured_external_local_export_directory_after_selected_server_owned_local_outbox_target_satisfied_sync`.

Doc: `623_NEXT_EXTERNAL_SURFACE_DECISION_INTAKE.md`.

Current-main checkpoint at intake creation: `2e30146544409eea5bd194485510ad9f5d17bb1b`.

Current-main checkpoint at operator fill: `173cb84553eb1841c7b317879adcd151afafee2b`.

Prior current-main sync: `622_TARGET_SELECTION_SELECTED_OUTBOX_CURRENT_MAIN_SYNC.md`.

Satisfied selected target: `server_owned_local_delivery_outbox_destination`.

Satisfied selected target freeze: `608_SERVER_OWNED_LOCAL_OUTBOX_REAL_WRITE_ADMISSION_FREEZE.md`.

Runtime status: `selected_next_external_surface_frozen_runtime_not_implemented`.

Implementation-entry freeze written for next external surface: true.

Selected next external surface: `server_configured_external_local_export_directory`.

Selected implementation action: `write_server_configured_external_local_export_directory_implementation_entry_freeze`.

Live behavior change in this pass: false.

## Current Authority

Current main already satisfies the operator-selected server-owned local outbox destination through the existing `608` freeze and current-main runtime. The satisfied behavior is bounded to one server-owned local outbox artifact/manifest write under backend-controlled storage.

This intake existed because the active Layer 3 objective was still not complete, but implementation could not continue into any new external/provider/destination/package/source/RAG/auth/frontend surface until exactly one next surface or action was named and separately frozen. The operator has now selected exactly one next external destination-write surface.

This is not a broad no-runtime audit. It is the concrete handoff record for the next operator decision after the selected local/server-owned outbox target was satisfied and synced.

External reference context is advisory only: the Project 2a diagram maps Layer 3 to the Data Structuring & Processing block. This selected surface is therefore an export/write boundary for finalized Layer 3 structured outputs, not an admission of downstream qualitative analysis, package mutation/reconstruction, source expansion, RAG/vector, provider-public delivery/use, connector invocation, credentials, or auth/security broadening.

## Decision To Fill

The operator-filled record is:

```yaml
next_surface_identity: server_configured_external_local_export_directory
next_surface_owner: Bennet / project operator
next_surface_class: server_configured_external_destination_write
operator_purpose: after Layer 3 completes source intake, Data Structuring & Processing, package/review, handoff/export, local outbox write, and provider-private preparation where applicable, write the finalized outbox artifact and manifest to a controlled local filesystem export directory outside app-owned staging for manual review, preservation, or downstream consumption
authority_source: external export/download readiness + connector-local durable receipt + server-owned local outbox write receipt + provider-private local-outbox handoff receipt where applicable
artifact_family: finalized outbox artifact + outbox manifest derived from server-owned package/export/handoff authority
credential_model: no_credentials
destination_address_model: server_configured_target_only
side_effect_boundary: write exactly one finalized Layer 3 outbox artifact and one outbox manifest to one server-configured local filesystem export directory outside app-owned staging; no caller-supplied path, network egress, connector invocation, connector-run creation, provider-public delivery, package mutation, source expansion, RAG/vector, auth/security broadening, full mockup activation, or frontend-durable authority
idempotency_contract: same client_request_id plus same authority/export/outbox/provider-private basis returns same receipt/status; same client_request_id plus different basis fails closed; same authority basis plus different client_request_id returns existing status rather than duplicate external export output; same export-directory deterministic target plus same bytes returns existing receipt/status; same target plus different bytes fails closed
failure_lifecycle: fail closed on stale authority, wrong session/pass/artifact/basis, missing export/download readiness, missing connector-local receipt, missing server-owned local outbox write receipt, missing required provider-private handoff receipt where applicable, tampered hash/size, target mismatch, export directory unavailable, path escape, timeout, partial write, conflicting existing output, unsupported credential/provider state, caller-supplied path/URL, or any forbidden adjacent surface
receipt_audit_contract: durable receipt id, session/pass/package/export refs, connector-local receipt ref, local outbox write receipt ref, provider-private handoff receipt ref where applicable, artifact/manifest refs with hash/size, target identity/class, redacted server-configured destination label, status/history, created/updated timestamps, idempotency key, redacted failure code, and audit history; never expose raw local paths
exposure_security_posture: private/internal only; no public URL; no provider-public delivery/use; no raw token; no credential storage; no external network egress; no public/indexable artifact exposure; no user-provided arbitrary path or URL
operator_surface: write_submit_control_plus_read_only_status_history_no_path_editing
proof_architecture: API proof over isolated runtime state plus headed/headless E2E proof if rendered write/status behavior changes; negative tests for stale authority, wrong artifact, duplicate-key conflict, same-key different-basis conflict, no ConnectorRun or ConnectorRunTarget creation, no real external connector invocation, no credential use, no provider-public delivery/use, no package mutation, no source expansion, no RAG/vector behavior, no broad auth/security change, and no arbitrary destination path
selection_complete: true
implementation_entry_freeze_written: true
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

The separate implementation-entry freeze is `626_SERVER_CONFIGURED_EXTERNAL_LOCAL_EXPORT_DIRECTORY_FREEZE.md`; it must:

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

- sync the filled decision record and freeze, then implement only after the freeze is merged and current-main synced; or
- keep runtime blocked and report the exact contradiction that prevents this selected surface from proceeding.

## Non-Admission Boundary

This intake admits no runtime behavior, backend route behavior, service behavior, response-model shape change, schema/model/migration change, rendered UI behavior, real connector invocation, destination write implementation before the separate freeze is current-main authority, connector-run creation, connector-run-target creation, credential use, network write, provider-public delivery/use, raw public URL exposure, raw token exposure, caller-supplied destination path/URL, package mutation/reconstruction, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, or generic downstream dispatch.

## Next Posture

The next whole-project posture is `await_current_main_sync_for_server_configured_external_local_export_directory_freeze`.

After that sync, the next admissible posture is `implement_server_configured_external_local_export_directory_after_freeze_sync` if and only if the merged current-main freeze still explicitly admits that exact runtime slice.
