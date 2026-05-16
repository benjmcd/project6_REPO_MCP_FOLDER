# 611 - Target Decision Packet

## Status

Status: missing-decision packet for `await_named_real_connector_or_destination_target_after_local_outbox_provider_private_lifecycle_proof`.

Doc: `611_TARGET_DECISION_PACKET.md`.

Current-main checkpoint at packet creation: `2a576047e7d3d70810beb107e89d766becb0578c`.

Prior runtime/freeze doc: `610_REAL_TARGET_FREEZE.md`.

Prior lifecycle hardening proof: PR `#1213`, commit `2787b937`, merged into current main by `2a576047e7d3d70810beb107e89d766becb0578c`.

Implementation-entry freeze written for real connector/destination: false.

Runtime status: `not_implemented`.

Selected implementation action: `none`.

## Current Authority

Current main now proves the local authority chain through a read-only provider-private local-outbox handoff lifecycle:

- external export/download readiness for the APS evidence bundle;
- internal connector dispatch record authority;
- connector-local fake/local destination receipt authority;
- server-owned local outbox fake-target receipt authority;
- server-owned local outbox write receipt authority;
- local-outbox-bound provider-private fake-provider prepare/status receipt authority;
- read-only session-summary status/history projection; and
- rendered read-only operator review of provider-private handoff status/history.

This chain is still local/fake-provider bounded. It does not admit a real connector invocation, external destination write, `ConnectorRun` or `ConnectorRunTarget` creation, credentials, provider-public delivery/use, raw token use, package mutation/reconstruction, source expansion, RAG/vector behavior, auth/security implementation, rendered write controls, full mockup activation, frontend-durable authority, generic downstream dispatch, or external provider use.

## Missing Decisions

A real connector or destination implementation-entry freeze must not be written until exactly one target is named and these decisions are filled:

| Decision | Required answer before freeze |
| --- | --- |
| Target identity | Exact connector, destination, provider, object-store, or delivery target name. |
| Target owner | Operator or system owner responsible for approving the first real side effect. |
| Target class | One of `real_connector_invocation`, `external_destination_write`, `real_provider_private_delivery`, `provider_public_delivery_use`, or another single named class. |
| Authority source | Exact Layer 3 receipt or record authorizing the side effect: provider-private handoff receipt, server-owned local outbox write receipt, outbox manifest, package record, or another named server-owned record. |
| Artifact family | Exact artifact to deliver or invoke against, including hash/size basis and whether the outbox artifact or manifest is the delivery subject. |
| Credential model | `no_credentials`, operator one-time credential, stored secret, delegated token, provider token, proxy-owned identity, or another named custody model. |
| Destination address model | Server-configured target, allowlisted object target, provider account target, operator-selected target, or no destination address. |
| Side-effect boundary | The one external write/call/use allowed, plus an explicit proof that no other side effect occurs. |
| Idempotency semantics | Required key fields, replay behavior, same-key conflict behavior, same-basis/new-key behavior, duplicate target behavior, and retry status. |
| Failure lifecycle | Stale authority, wrong session/basis/artifact, credential failure, provider failure, timeout, partial completion, and audit-only recovery behavior. |
| Receipt/audit contract | Durable receipt fields, audit-event fields, redaction rules, status/history fields, and retention expectations. |
| Exposure/security posture | Whether provider-private, provider-public, public URL, network egress, auth/security, or operator access surfaces become real. |
| Operator surface | Read-only status only, write/submit control, or no rendered surface. |
| Test architecture | Fake target/provider proof, isolated runtime state, API proof, headed/headless E2E if rendered behavior changes, and negative guardrail coverage. |

## Freeze Preconditions

The next implementation-entry freeze may proceed only if it has all of the following:

1. One named target and one target class.
2. One owner-service seam.
3. One route/API entrypoint or an explicit internal-only harness.
4. One durable receipt/audit contract.
5. One fake-provider, dry-run, or fake-target proof path before any live side effect.
6. One operator-visible status/history projection if any operator surface is admitted.
7. One isolated API or E2E proof path.
8. One explicit non-admission list preserving every deferred surface not selected by the freeze.

If any precondition is missing, the correct next action is to keep runtime blocked and fill this packet, not to implement a generic connector or destination layer.

## Candidate Freeze Shapes

The next freeze should choose exactly one of these shapes:

| Candidate | What it would admit | What remains blocked |
| --- | --- | --- |
| `real_provider_private_delivery_from_local_outbox_handoff` | A real provider-private delivery target from the existing local-outbox provider-private handoff receipt. | Provider-public use, public URLs, generic connector runs, package mutation, source expansion, RAG/vector, broad auth/security, and frontend-durable authority. |
| `server_configured_destination_write_from_local_outbox` | One server-configured destination write from the server-owned local outbox write receipt and manifest. | Operator paths, arbitrary destinations, credentials unless separately named, connector runs, provider-public delivery, package mutation, source expansion, RAG/vector, and auth/security expansion. |
| `named_connector_invocation_from_dispatch_record` | One named connector invocation from existing internal dispatch and receipt authority. | Generic connector registry expansion, connector-run creation unless explicitly included, provider-public delivery, package mutation, source expansion, RAG/vector, and auth/security expansion. |

No candidate is selected by this packet. Selection requires an operator-named target.

## Non-Admission Boundary

This packet admits no runtime behavior, backend route behavior, service behavior, response-model shape change, schema/model/migration change, rendered UI implementation, executable test behavior, real connector invocation, destination write, connector-run creation, credential handling, provider-public delivery/use, raw token use, package mutation/reconstruction, source expansion, RAG/vector behavior, auth/security behavior change, full mockup activation, frontend-durable authority, generic downstream dispatch, or external provider use.

## Decision Result

Decision result: `real_connector_destination_target_not_yet_named_after_local_outbox_provider_private_lifecycle_proof`.

Required next action: name exactly one real connector or destination target, then write a separate implementation-entry freeze for that target. If no target can be named, keep runtime blocked and do not run another broad no-runtime audit unless current-main authority contradicts the local-outbox provider-private lifecycle proof.
