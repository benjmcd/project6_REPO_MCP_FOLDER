# 606 - Real Target Implementation Entry Freeze

## Status

Status: implementation-entry freeze for `named_real_connector_destination_target_after_local_receipt_lifecycle_sync`.

Doc: `606_REAL_TARGET_IMPLEMENTATION_ENTRY_FREEZE.md`.

Current-main checkpoint: `f62150ae0a7a9fb61bba27b37567d61d8f756078`.

Prior decision packet: `605_REAL_TARGET_DECISION_PACKET.md`.

Branch: `codex/l3-real-target-freeze`.

Runtime status before implementation: `not_implemented`.

Implementation-entry allowed next: true, but only for the fake-target contract/proof tranche defined here.

## Selected Target

Selected target identity: `server_owned_local_delivery_outbox_destination`.

Selected target class: `single_named_destination_dispatch`.

Selected downstream use case: `operator_requests_server_owned_local_outbox_handoff_after_layer3_external_export_download_and_local_receipt_lifecycle_proof`.

Selected artifact family: `aps_evidence_bundle_download_reference`.

Selected dispatch mode: `single_named_destination_dispatch_fake_target_first`.

The selected target is a destination target, not a connector invocation. It is selected because it is the smallest concrete target that builds outward from the landed fake/local receipt lifecycle without introducing credentials, provider-public exposure, connector-run lifecycle, generic downstream dispatch, source expansion, package mutation, RAG/vector behavior, or auth/security implementation.

## Current Authority Basis

The future implementation must derive authority only from current server-owned Layer 3 state:

- existing session authority;
- approved package/reconciliation authority;
- handoff/export prepare authority;
- APS handoff dispatch authority;
- external export/download prepare authority;
- internal connector dispatch record authority;
- local receipt lifecycle authority from `L3ConnectorLocalDestinationReceipt`;
- source artifact hash/size/ref already validated by the external export/download readiness path; and
- `client_request_id` supplied only as the idempotency key.

Browser state, copied local paths, operator-entered destination paths, destination URLs, connector keys, credentials, provider object keys, package payload bytes, source upload fields, RAG/vector fields, prompt/model fields, and auth/security overrides are not authority.

## Credential And Access Model

Credential/access model: `no_external_credentials_fake_target_first`.

The first admissible implementation must not accept or persist credentials. It must not call an external provider, connector, storage service, network endpoint, or operator-provided filesystem path.

If a later runtime pass wants a real local outbox write, it must define a server-owned storage root/config authority and pass a separate runtime admission gate. This freeze by itself does not admit production destination writes.

## Write Boundary

Admitted first implementation boundary: fake-target contract/proof only.

The future first implementation may define a deterministic fake-target owner service or contract double for `server_owned_local_delivery_outbox_destination`. It may project or record intent/status against already validated authority, but it must not perform a production destination write.

Any real destination write, even to a server-owned local outbox, requires a later runtime implementation pass after fake-target proof and current-main sync.

## Idempotency, Retry, And Failure Lifecycle

The future target contract must preserve the current local receipt lifecycle semantics:

- `client_request_id` is required and unique for the target operation;
- same `client_request_id` plus same authority basis returns the existing target receipt/status;
- same `client_request_id` plus different authority basis fails closed;
- same authority basis plus different `client_request_id` fails closed unless a later freeze admits multi-receipt behavior;
- retry is status-only until a real write boundary is separately admitted;
- stale authority fails before target-status recording;
- wrong session, artifact, external export/download ref, connector dispatch ref, local receipt id, or basis hash fails closed;
- cancel, queue, timeout, and async retry are not admitted; and
- partial completion is represented only as fake-target failure/status in the first tranche.

Required status vocabulary:

- `server_owned_local_outbox_target_not_ready`;
- `server_owned_local_outbox_fake_target_ready`;
- `server_owned_local_outbox_fake_target_recorded`;
- `server_owned_local_outbox_fake_target_replay`;
- `server_owned_local_outbox_fake_target_conflict`;
- `server_owned_local_outbox_fake_target_stale_authority`;
- `server_owned_local_outbox_fake_target_failed`.

## Receipt And Audit Contract

The first implementation may add only fake-target receipt/status authority. The receipt/audit contract must include:

- target receipt id;
- session id;
- pass run id;
- reconciliation record id;
- connector dispatch record ref;
- local destination receipt id;
- external export/download record ref;
- target identity `server_owned_local_delivery_outbox_destination`;
- dispatch mode `single_named_destination_dispatch_fake_target_first`;
- source artifact hash and size;
- redacted source artifact ref;
- authority basis hash;
- target state;
- idempotency key;
- created timestamp; and
- explicit booleans showing real connector invocation, destination write, connector-run creation, credentials, provider-public delivery/use, package mutation, source expansion, RAG/vector, auth/security implementation, full mockup activation, and frontend-durable authority remain disabled.

Response and audit surfaces must not expose raw local filesystem paths, credentials, bearer tokens, provider URLs, connector targets, destination URLs, package payload bytes, source contents, prompt/model data, RAG/vector internals, auth internals, or browser storage state.

## Fake-Target Proof Path

The next implementation-bearing pass must prove the target through isolated fake-target behavior:

1. API contract rejects credentials, destination paths/URLs, connector fields, provider/public fields, package mutation fields, source expansion fields, RAG/vector fields, auth/security override fields, and frontend-durable fields.
2. Fake-target happy path records status/receipt only after current server authority is present.
3. Same-key/same-basis replay is idempotent.
4. Same-key/different-basis conflict fails closed.
5. Same-basis/different-key conflict fails closed unless separately admitted.
6. Stale authority, wrong session, wrong artifact, wrong connector dispatch ref, wrong local receipt id, and wrong external export/download ref fail closed.
7. Database counts prove no `ConnectorRun` or `ConnectorRunTarget` creation.
8. Filesystem/runtime proof shows no production destination write.
9. Headed and headless rendered proof exercise read-only operator status if any UI surface is admitted.

## Operator Surface Obligations

No rendered write control is admitted by this freeze.

If a later implementation adds an operator-visible surface in the first tranche, it must be read-only status/history over server authority. It must not ask the operator for destination paths, connector keys, credentials, URLs, provider settings, package mutation instructions, source expansion inputs, RAG/vector settings, or auth/security overrides.

The read-only surface must show:

- selected target identity;
- target readiness;
- latest target receipt/status;
- failure-state projection;
- idempotency/retry policy;
- disabled downstream lanes; and
- redacted authority refs only.

## Security Posture

Security posture: `no_external_exposure_no_credentials_redacted_refs_only`.

The first tranche must remain local/test/fake-target only. It must not introduce public exposure, nonlocal destination access, credential storage, provider token custody, connector secret handling, auth policy changes, ACL changes, network writes, or browser-owned durable authority.

Any later external or production write pass must add a separate auth/security freeze tied to that exact surface.

## Non-Admission Boundary

This freeze admits no runtime behavior by itself, no real connector invocation, no production destination write, no connector-run creation, no credential handling, no provider-public delivery/use, no package mutation/reconstruction, no source expansion, no RAG/vector behavior, no auth/security implementation, no full mockup activation, no frontend-durable authority, no generic downstream dispatch, no real provider/object-store behavior, no browser-owned target authority, and no rendered write controls.

## Stop Conditions

Stop before implementation if the next pass:

- selects more than `server_owned_local_delivery_outbox_destination`;
- requires external credentials or provider/network access;
- accepts operator-provided local paths or destination URLs;
- creates `ConnectorRun` or `ConnectorRunTarget` rows;
- performs a production destination write;
- exposes unredacted artifact refs, local paths, credentials, provider URLs, connector targets, destination URLs, package payload bytes, source contents, prompt/model data, RAG/vector internals, auth internals, or browser storage state;
- widens package, source, RAG/vector, provider-public, mockup, or auth/security behavior as a side effect; or
- cannot prove fake-target behavior in isolated runtime state.

## Next Posture

The next whole-project posture is `await_server_owned_local_outbox_fake_target_contract_implementation_after_freeze_sync`.
