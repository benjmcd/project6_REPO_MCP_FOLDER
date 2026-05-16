# 612 - Target Selection Intake

## Status

Status: operator-fillable intake for `select_one_real_connector_or_destination_target_after_local_outbox_provider_private_lifecycle_proof`.

Doc: `612_TARGET_SELECTION_INTAKE.md`.

Current-main checkpoint at intake creation: `07b8cd1a22f2793602c6357d1964be224d07eb92`.

Prior decision packet: `611_TARGET_DECISION_PACKET.md`.

Runtime status: `not_implemented`.

Implementation-entry freeze written: false.

Selected target identity: `null`.

Selected target class: `null`.

Selected implementation action: `none`.

## Purpose

This intake is the narrow operator action required before any real connector or destination implementation-entry freeze.

It converts the missing decisions in `611_TARGET_DECISION_PACKET.md` into a single fillable target-selection record. It does not select a target by itself, admit runtime behavior, or allow a generic connector/destination implementation.

## Fillable Selection Record

The operator must fill every field before a real-target implementation-entry freeze can be written:

| Field | Required value |
| --- | --- |
| `target_identity` | Exact connector, destination, provider, object-store, or delivery target name. |
| `target_owner` | Person, team, service owner, or operator accountable for approving the first real side effect. |
| `target_class` | Exactly one of `real_connector_invocation`, `external_destination_write`, `real_provider_private_delivery`, `provider_public_delivery_use`, or another single named class. |
| `operator_purpose` | Concrete operator workflow that needs this real target. |
| `authority_source` | Exact Layer 3 receipt or record authorizing the side effect. |
| `artifact_family` | Exact artifact and whether the side effect uses the outbox artifact, outbox manifest, provider-private handoff receipt, package record, or another named server-owned artifact. |
| `credential_model` | One of `no_credentials`, `operator_one_time_credential`, `stored_secret`, `delegated_token`, `provider_token`, `proxy_owned_identity`, or another named custody model. |
| `destination_address_model` | One of `server_configured_target`, `allowlisted_object_target`, `provider_account_target`, `operator_selected_target`, or `no_destination_address`. |
| `side_effect_boundary` | The one external write, call, delivery, or use that will be admitted if frozen. |
| `idempotency_contract` | Required key fields, replay behavior, same-key conflict behavior, same-basis/new-key behavior, duplicate target behavior, and retry status. |
| `failure_lifecycle` | Stale authority, wrong session/basis/artifact, credential failure, provider failure, timeout, partial completion, and recovery behavior. |
| `receipt_audit_contract` | Durable receipt fields, audit-event fields, redaction rules, status/history fields, and retention expectations. |
| `exposure_security_posture` | Provider-private, provider-public, public URL, network egress, auth/security, and operator-access posture. |
| `operator_surface` | `read_only_status_only`, `write_submit_control`, or `no_rendered_surface`. |
| `proof_architecture` | Fake/dry-run proof path, isolated runtime state, API proof, headed/headless E2E if rendered behavior changes, and negative guardrails. |

## Structured Selection Record

The operator may complete the intake by replacing every `null` value below. Leave `selection_complete: false` until every required value is filled and a separate implementation-entry freeze is ready to copy the completed record.

```yaml
target_identity: null
target_owner: null
target_class: null
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

## Acceptance Gate

A completed intake is acceptable only when:

1. Exactly one `target_identity` is named.
2. Exactly one `target_class` is named.
3. The `authority_source` is a server-owned Layer 3 receipt or record already present on current main.
4. The `side_effect_boundary` names one and only one real external side effect.
5. Credential custody is explicit, even if the answer is `no_credentials`.
6. Public/private exposure is explicit, even if no public exposure is admitted.
7. The receipt/audit contract is durable and operator-visible.
8. The proof path includes a fake-provider, dry-run, fake-target, or equivalent fail-closed pre-live proof.
9. The non-admission list below remains intact for all unselected surfaces.

If any gate fails, the next action remains target selection, not implementation.

## Freeze Output Required After Selection

Once this intake is complete, the next artifact must be a separate implementation-entry freeze. That freeze must:

- copy the selected intake fields verbatim;
- identify the exact files/routes/services/tables allowed for the first implementation tranche;
- define stop conditions before code edits;
- define the focused API/E2E proof path;
- keep unselected candidates out of scope; and
- preserve all blocked surfaces not named in the intake.

## Non-Admission Boundary

This intake admits no runtime behavior, backend route behavior, service behavior, response-model shape change, schema/model/migration change, rendered UI implementation, executable test behavior, real connector invocation, destination write, connector-run creation, credential handling, provider-public delivery/use, raw token use, package mutation/reconstruction, source expansion, RAG/vector behavior, auth/security behavior change, full mockup activation, frontend-durable authority, generic downstream dispatch, or external provider use.

## Decision State

Decision state: `target_selection_required`.

Selection complete: false.

Required next action: fill this intake with one named real connector or destination target. If no target can be named, keep runtime blocked and do not start another broad no-runtime audit unless current-main authority contradicts the local-outbox provider-private lifecycle proof.
