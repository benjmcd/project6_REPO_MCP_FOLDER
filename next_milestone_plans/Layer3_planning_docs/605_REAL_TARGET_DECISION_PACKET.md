# 605 - Real Target Decision Packet

## Status

Status: missing-decision packet for `await_real_connector_destination_named_target_decision_after_local_receipt_lifecycle_runtime_sync`.

Doc: `605_REAL_TARGET_DECISION_PACKET.md`.

Current-main checkpoint: `5d71f153f0e19a02075d8ccc6a08143b5bbb4049`.

Prior runtime sync doc: `604_LOCAL_RECEIPT_LIFECYCLE_RUNTIME_SYNC.md`.

Implementation-entry freeze written: false.

Runtime status: `not_implemented`.

Selected implementation action: `none`.

## Current Authority

Current main now has a durable local receipt lifecycle foundation for the fake/local connector destination. It proves the operator can see status/history/failure/idempotency/retry information for local receipt authority without admitting a real connector or destination.

The only admitted destination-like behavior remains internal and fake/local:

- server-side receipt projection is read-only for the operator surface;
- the local receipt write route records only fake/local receipt authority;
- no real connector is invoked;
- no destination write occurs;
- no `ConnectorRun` creation is admitted by this lifecycle tranche; and
- provider-public delivery/use, credentials, package mutation, source expansion, RAG/vector, auth/security, full mockup activation, and frontend-durable authority remain blocked.

## Missing Target Decisions

A real connector/destination implementation-entry freeze must not be written until one concrete target is named and all of the following are decided:

1. Target identity: exact connector or destination name, owner, and operator purpose.
2. Authority source: which existing Layer 3 state, artifact, package, receipt, or handoff record authorizes the target.
3. Dispatch mode: internal dispatch record only, real connector invocation, destination write, provider-private handoff, provider-public delivery, or another named mode.
4. Credential model: no credentials, operator-provided credential, stored secret, delegated token, or external provider token.
5. Write boundary: exact external side effect, if any, including path/object/API target and whether dry-run/fake-provider mode remains mandatory first.
6. Idempotency key: required key fields, replay behavior, same-key/same-payload result, same-key/different-payload conflict, and same-basis/new-key conflict.
7. Lifecycle semantics: status vocabulary, retry, timeout, cancel, failure, stale authority, wrong artifact/session/basis, and partial completion behavior.
8. Receipt/audit contract: durable receipt fields, redaction rules, operator-visible status/history fields, and audit-event minimums.
9. Test architecture: fake target, fake provider, isolated runtime state, headed/headless E2E, and negative guardrails.
10. Security posture: auth boundary, leak controls, public/private exposure, credential redaction, and review/approval requirements.

## Candidate Next Freeze

If a target is named, the next admissible planning artifact is a separate implementation-entry freeze with:

- one named target;
- one owner-service seam;
- one route/API surface or an explicit no-route internal harness;
- one durable receipt/audit contract;
- one fake-provider/fake-target proof path;
- one headed/headless rendered proof path if an operator surface is admitted; and
- a full non-admission list for all remaining deferred surfaces.

## Decision Result

Decision result: `no_runtime_now_real_connector_destination_target_absent_after_local_receipt_lifecycle_sync`.

Required next action: name exactly one real connector or destination target, or explicitly select another local receipt lifecycle hardening pass.

## Non-Admission Boundary

This packet admits no runtime behavior, backend route behavior, service behavior, response-model shape change, schema/model/migration change, rendered UI implementation, executable test behavior, real connector invocation, destination write, connector-run creation, credential handling, provider-public delivery/use, package mutation/reconstruction, source expansion, RAG/vector behavior, auth/security behavior change, full mockup activation, frontend-durable authority, generic downstream dispatch, or external provider use.
