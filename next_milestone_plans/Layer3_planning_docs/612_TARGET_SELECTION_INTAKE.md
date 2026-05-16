# 612 - Target Selection Intake

## Status

Status: operator-filled target-selection intake for `server_owned_local_delivery_outbox_destination`.

Doc: `612_TARGET_SELECTION_INTAKE.md`.

Current-main checkpoint at intake creation: `07b8cd1a22f2793602c6357d1964be224d07eb92`.

Current-main checkpoint at operator fill: `8b3e845b77f1b09864e1fdd17a9997866a32975a`.

Prior decision packet: `611_TARGET_DECISION_PACKET.md`.

Runtime status: `implemented_on_current_main_by_existing_server_owned_local_outbox_write_runtime`.

Implementation-entry freeze written: true.

Selected target identity: `server_owned_local_delivery_outbox_destination`.

Selected target class: `external_destination_write`.

Selected implementation action: `current_main_satisfied_by_608_server_owned_local_outbox_real_write_admission_freeze`.

## Purpose

This intake records the narrow operator action required before any real connector or destination implementation-entry freeze.

It converts the missing decisions in `611_TARGET_DECISION_PACKET.md` into a single target-selection record. This selected target is already covered by `608_SERVER_OWNED_LOCAL_OUTBOX_REAL_WRITE_ADMISSION_FREEZE.md` and the current-main server-owned local outbox write runtime, so this intake does not admit any new runtime behavior, real connector invocation, provider network write, public delivery/use, or generic connector/destination implementation.

## Fillable Selection Record

The operator-filled values are:

| Field | Selected value |
| --- | --- |
| `target_identity` | `server_owned_local_delivery_outbox_destination` |
| `target_owner` | Bennet / project operator |
| `target_class` | `external_destination_write` |
| `operator_purpose` | Write a finalized Layer 3 export/outbox artifact and manifest to a controlled server-owned local delivery outbox so it can be manually reviewed or consumed downstream. |
| `authority_source` | external export/download readiness + connector-local durable receipt + server-owned local outbox write receipt + provider-private local-outbox handoff receipt where applicable |
| `artifact_family` | outbox artifact + outbox manifest |
| `credential_model` | `no_credentials` |
| `destination_address_model` | `server_configured_target` |
| `side_effect_boundary` | Write exactly one approved Layer 3 outbox artifact/manifest to one server-configured local delivery outbox destination. |
| `idempotency_contract` | same `client_request_id` + same authority/artifact basis returns the same receipt; same `client_request_id` + different basis fails closed; same basis + new `client_request_id` returns existing status rather than creating duplicate output; duplicate target write returns existing receipt/status if identical and fails closed if conflicting. |
| `failure_lifecycle` | fail closed on stale authority, wrong session/pass/artifact, missing readiness, missing receipt, tampered hash, target mismatch, timeout, partial write, unsupported credential/provider state, or any caller-supplied path/URL. |
| `receipt_audit_contract` | durable receipt id, session/pass/package/export refs, artifact ref/hash/size, target identity/class, status/history, created/updated timestamps, idempotency key, redacted failure code, and audit history; do not expose raw local paths. |
| `exposure_security_posture` | private/internal only; no public URL; no provider-public delivery/use; no raw token; no credential storage; no external network egress; no user-provided arbitrary path. |
| `operator_surface` | `read_only_status_only` |
| `proof_architecture` | fake/local/server-owned target proof first; API proof; headed/headless E2E proof if rendered status changes; negative tests for stale authority, wrong artifact, duplicate-key conflict, no connector-run creation, no real external connector invocation, no credential use, and no arbitrary destination write. |

## Structured Selection Record

The operator completed the intake below. `implementation_entry_freeze_written: true` is satisfied by the already-merged `608_SERVER_OWNED_LOCAL_OUTBOX_REAL_WRITE_ADMISSION_FREEZE.md`, which admits only the server-owned local outbox write tranche for this target identity.

```yaml
target_identity: server_owned_local_delivery_outbox_destination
target_owner: Bennet / project operator
target_class: external_destination_write
operator_purpose: Write a finalized Layer 3 export/outbox artifact and manifest to a controlled server-owned local delivery outbox so it can be manually reviewed or consumed downstream.
authority_source: external export/download readiness + connector-local durable receipt + server-owned local outbox write receipt + provider-private local-outbox handoff receipt where applicable
artifact_family: outbox artifact + outbox manifest
credential_model: no_credentials
destination_address_model: server_configured_target
side_effect_boundary: Write exactly one approved Layer 3 outbox artifact/manifest to one server-configured local delivery outbox destination.
idempotency_contract: same client_request_id + same authority/artifact basis returns the same receipt; same client_request_id + different basis fails closed; same basis + new client_request_id returns existing status rather than creating duplicate output; duplicate target write returns existing receipt/status if identical and fails closed if conflicting.
failure_lifecycle: fail closed on stale authority, wrong session/pass/artifact, missing readiness, missing receipt, tampered hash, target mismatch, timeout, partial write, unsupported credential/provider state, or any caller-supplied path/URL.
receipt_audit_contract: durable receipt id, session/pass/package/export refs, artifact ref/hash/size, target identity/class, status/history, created/updated timestamps, idempotency key, redacted failure code, and audit history; do not expose raw local paths.
exposure_security_posture: private/internal only; no public URL; no provider-public delivery/use; no raw token; no credential storage; no external network egress; no user-provided arbitrary path.
operator_surface: read_only_status_only
proof_architecture: fake/local/server-owned target proof first; API proof; headed/headless E2E proof if rendered status changes; negative tests for stale authority, wrong artifact, duplicate-key conflict, no connector-run creation, no real external connector invocation, no credential use, and no arbitrary destination write.
selection_complete: true
implementation_entry_freeze_written: true
```

## Acceptance Gate

A completed intake is acceptable only when:

1. Exactly one `target_identity` is named.
2. Exactly one `target_class` is named.
3. The `authority_source` is a server-owned Layer 3 receipt or record already present on current main.
4. The `side_effect_boundary` names one and only one side effect; for this selected target, that side effect is the already-admitted server-owned local outbox write under backend-controlled storage.
5. Credential custody is explicit, even if the answer is `no_credentials`.
6. Public/private exposure is explicit, even if no public exposure is admitted.
7. The receipt/audit contract is durable and operator-visible.
8. The proof path includes a fake-provider, dry-run, fake-target, or equivalent fail-closed pre-live proof.
9. The non-admission list below remains intact for all unselected surfaces.

This completed intake passes the selection gate by current-main reconciliation because the selected target identity, dispatch mode, credential model, destination-address model, idempotency, redaction, and proof architecture map to the already-merged `608` freeze and its current-main runtime.

## Freeze Output Required After Selection

When a selected target is not already covered by a current-main implementation-entry freeze, the next artifact must be a separate implementation-entry freeze. That freeze must:

- copy the selected intake fields verbatim;
- identify the exact files/routes/services/tables allowed for the first implementation tranche;
- define stop conditions before code edits;
- define the focused API/E2E proof path;
- keep unselected candidates out of scope; and
- preserve all blocked surfaces not named in the intake.

For this selected target, no new implementation-entry freeze is required in this pass because `608_SERVER_OWNED_LOCAL_OUTBOX_REAL_WRITE_ADMISSION_FREEZE.md` already copies/adjudicates the selected target identity and admits only the server-owned local outbox write tranche.

## Non-Admission Boundary

This intake admits no new runtime behavior, backend route behavior, service behavior, response-model shape change, schema/model/migration change, rendered UI implementation, executable test behavior, real connector invocation, new destination-write class beyond the already-admitted server-owned local outbox write, connector-run creation, credential handling, provider-public delivery/use, raw token use, package mutation/reconstruction, source expansion, RAG/vector behavior, auth/security behavior change, full mockup activation, frontend-durable authority, generic downstream dispatch, or external provider use.

## Decision State

Decision state: `selected_target_current_main_satisfied_by_existing_608_server_owned_local_outbox_write_freeze`.

Selection complete: true.

Required next action: record the current-main satisfied selected-target posture and do not implement runtime in this pass. If the operator needs behavior beyond the selected server-owned local outbox destination, the next exact posture is a new named-target decision and a separate implementation-entry freeze for that different surface.
