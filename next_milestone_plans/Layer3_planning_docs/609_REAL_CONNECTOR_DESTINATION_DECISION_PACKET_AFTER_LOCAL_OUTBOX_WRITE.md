# 609 - Real Connector Destination Decision Packet After Local Outbox Write

## Status

Status: missing-decision packet for `await_first_real_connector_destination_target_freeze_after_server_owned_local_outbox_write`.

Doc: `609_REAL_CONNECTOR_DESTINATION_DECISION_PACKET_AFTER_LOCAL_OUTBOX_WRITE.md`.

Current branch base checkpoint: `4993a750bdb9e49d315925e9acc68ac9a0fb73f0`.

Prior admission freeze: `608_SERVER_OWNED_LOCAL_OUTBOX_REAL_WRITE_ADMISSION_FREEZE.md`.

Runtime status before this packet: `server_owned_local_outbox_write_implemented_in_branch_not_yet_main_authority`.

Implementation-entry freeze written for real connector/destination: false.

Selected implementation action: `none`.

## Current Local Handoff Authority

The current Layer 3 local handoff foundation is now expected to contain, after landing, this server-owned sequence:

- external export/download readiness for an APS evidence bundle;
- internal connector dispatch record authority;
- connector-local fake/local destination receipt authority;
- server-owned local outbox fake-target receipt authority; and
- server-owned local outbox write receipt authority under `Path(settings.storage_dir) / "layer3-outbox"`.

This local handoff path is not a real connector invocation. It proves that a validated artifact can be advanced through server-owned receipt, target, and local outbox write states without accepting caller paths, credentials, provider URLs, public URLs, connector targets, package mutation inputs, source expansion inputs, RAG/vector inputs, auth/security overrides, or browser durable authority.

## Decision Required Before Real Connector Freeze

A real connector/destination implementation-entry freeze must not be written until the operator names exactly one target and records these decisions:

1. Target identity: exact connector or destination name, owner, and operator purpose.
2. Target class: real connector invocation, external destination write, provider-private handoff, provider-public delivery/use, or another named class.
3. Authority basis: which existing Layer 3 receipt, outbox manifest, artifact hash, package record, or handoff record authorizes the real side effect.
4. Artifact family: exact artifact family and whether the source is the local outbox artifact, its manifest, the export/download readiness artifact, or another named server-owned artifact.
5. Credential model: no credentials, operator-supplied one-time credential, stored secret, delegated token, provider token, or proxy-owned identity.
6. Destination address model: no caller address, server-configured destination, allowlisted object target, provider account target, or operator-selected target.
7. Side-effect boundary: exact external write/call, whether a fake-provider pass remains mandatory first, and what proves no other side effect occurred.
8. Idempotency semantics: required key fields, same-key/same-basis replay, same-key/different-basis conflict, same-basis/new-key behavior, duplicate destination conflict, and retry status.
9. Failure lifecycle: stale authority, wrong session, wrong artifact hash/size, wrong local outbox receipt, wrong destination, credential failure, provider failure, timeout, partial completion, and audit-only recovery.
10. Receipt/audit contract: durable receipt fields, audit event fields, redaction rules, operator-visible status/history fields, and retention/cleanup policy.
11. Security posture: auth owner, access control, credential custody, leak controls, provider/public exposure, network egress boundary, and required review/approval.
12. Test architecture: fake target/provider, isolated runtime state, headed/headless UI proof if rendered status changes, and negative guardrail coverage.

## Recommended First Freeze Shape

The next implementation-entry freeze should be accepted only if it has:

- one named target;
- one service seam;
- one route/API entrypoint or an explicit internal-only harness;
- one durable receipt/audit table contract;
- one fake-provider or dry-run proof path before any live side effect;
- one read-only operator status/history projection;
- one isolated E2E proof path; and
- one explicit non-admission list preserving all still-blocked surfaces.

## Anti-Cycle Rule

Do not run another broad no-runtime audit before the next implementation-bearing step unless current-main authority contradicts the local outbox write proof.

The next planning action should be either:

- `name_one_real_connector_destination_target_and_write_freeze`; or
- `defer_real_target_and_land_operator_ready_local_handoff`, if no target owner/destination/credential decision exists.

## Non-Admission Boundary

This packet admits no runtime behavior, backend route behavior, service behavior, response-model shape change, schema/model/migration change, rendered UI implementation, executable test behavior, real connector invocation, external destination write, connector-run creation, credential handling, provider-public delivery/use, package mutation/reconstruction, source expansion, RAG/vector behavior, auth/security behavior change, full mockup activation, frontend-durable authority, generic downstream dispatch, or external provider use.

## Decision Result

Decision result: `real_connector_destination_target_not_yet_named_after_local_outbox_write`.

Required next action: land and re-audit the operator-ready local handoff runtime, then name exactly one real connector/destination target before writing a real connector implementation-entry freeze.
