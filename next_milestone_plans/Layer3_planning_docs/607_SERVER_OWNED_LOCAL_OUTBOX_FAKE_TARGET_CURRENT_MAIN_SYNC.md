# 607 - Server-Owned Local Outbox Fake Target Current-Main Sync

## Status

Status: current-main sync for `await_server_owned_local_outbox_fake_target_contract_implementation_after_freeze_sync`.

Doc: `607_SERVER_OWNED_LOCAL_OUTBOX_FAKE_TARGET_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint: `4993a750bdb9e49d315925e9acc68ac9a0fb73f0`.

Prior implementation-entry freeze: `606_REAL_TARGET_IMPLEMENTATION_ENTRY_FREEZE.md`.

Merged runtime target: `server_owned_local_delivery_outbox_destination`.

Runtime status: `fake_target_implemented`.

Real write status: `not_implemented`.

## Current-Main Result

Current main now includes the fake-target proof tranche admitted by doc `606`.

The implemented runtime adds the server-owned local outbox target as a fake target only:

- route: `POST /api/v1/layer3/handoff/connector/local-outbox/fake-target`;
- service: `backend/app/services/layer3_server_owned_local_outbox_target.py`;
- model: `L3ServerOwnedLocalOutboxTargetReceipt`;
- table: `l3_server_owned_local_outbox_target_receipt`;
- migration: `0027_layer3_local_outbox_target_receipt`;
- session summary field: `server_owned_local_outbox_target`; and
- read-only status/history projection over durable target receipts.

## Current Authority Basis

The fake-target receipt derives authority from current server-owned Layer 3 state only:

- existing session authority;
- approved analysis plan and pass run authority;
- reconciliation record authority;
- connector dispatch record authority;
- external export/download prepared authority;
- connector-local destination receipt authority; and
- the accepted artifact hash and size already validated by the external export/download delivery path.

The fake target does not accept browser state, operator-entered paths, destination URLs, connector keys, credentials, provider object keys, package payload bytes, source upload fields, RAG/vector fields, prompt/model fields, or auth/security overrides as authority.

## Implemented Lifecycle

Current main now projects:

- `server_owned_local_outbox_target_not_ready`;
- `server_owned_local_outbox_fake_target_ready`;
- `server_owned_local_outbox_fake_target_recorded`;
- `server_owned_local_outbox_fake_target_replay`;
- `server_owned_local_outbox_fake_target_conflict`;
- `server_owned_local_outbox_fake_target_stale_authority`; and
- `server_owned_local_outbox_fake_target_failed`.

The durable fake-target receipt records:

- target receipt id;
- session id;
- pass run id;
- reconciliation record id;
- connector-local destination receipt id;
- connector dispatch record ref;
- external export/download record ref;
- target identity;
- dispatch mode;
- accepted artifact hash and size;
- authority basis hash;
- authority snapshot; and
- idempotency key.

## Current Proof Boundary

The implemented fake target proves:

- credentials, destination paths, destination URLs, connector fields, provider fields, package mutation fields, source expansion fields, RAG/vector fields, auth/security override fields, and frontend-durable fields are rejected fail-closed;
- same `client_request_id` plus the same authority basis replays the existing target receipt;
- same `client_request_id` plus a different basis conflicts;
- same authority basis plus a different `client_request_id` conflicts;
- stale connector/local-receipt/readiness authority conflicts before target recording;
- no `ConnectorRun` row is created;
- no `ConnectorRunTarget` row is created; and
- no destination write is performed.

## Non-Admission Boundary

This sync admits no real connector invocation, no external connector run, no `ConnectorRun` creation, no `ConnectorRunTarget` creation, no external credentials, no provider-public delivery/use, no package mutation/reconstruction, no source expansion, no RAG/vector behavior, no auth/security implementation, no full mockup activation, no frontend-durable authority, no generic downstream dispatch, no operator-provided destination path, no destination URL, and no external provider/object-store behavior.

The only now-ready follow-up is the first server-owned local outbox write, and only after a separate runtime admission freeze names the storage/config authority, write artifact shape, lifecycle/idempotency semantics, cleanup/audit policy, and security boundary.

## Next Posture

The next whole-project posture is `await_server_owned_local_outbox_real_write_admission_after_fake_target_current_main_sync`.
