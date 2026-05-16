# 608 - Server-Owned Local Outbox Real Write Admission Freeze

## Status

Status: implementation-entry freeze for `await_server_owned_local_outbox_real_write_admission_after_fake_target_current_main_sync`.

Doc: `608_SERVER_OWNED_LOCAL_OUTBOX_REAL_WRITE_ADMISSION_FREEZE.md`.

Current-main checkpoint: `4993a750bdb9e49d315925e9acc68ac9a0fb73f0`.

Prior sync doc: `607_SERVER_OWNED_LOCAL_OUTBOX_FAKE_TARGET_CURRENT_MAIN_SYNC.md`.

Runtime status before implementation: `fake_target_implemented_real_write_not_implemented`.

Implementation-entry allowed next: true, but only for the server-owned local outbox write tranche defined here.

## Selected Target

Selected target identity: `server_owned_local_delivery_outbox_destination`.

Selected target class: `server_owned_local_destination_write`.

Selected downstream use case: `operator_requests_server_owned_local_outbox_handoff_after_fake_target_receipt`.

Selected artifact family: `aps_evidence_bundle_download_reference`.

Selected dispatch mode: `server_owned_local_outbox_write_via_storage_dir`.

Selected operator decision: `write_server_owned_local_outbox`.

This target is still not a connector invocation. It is a single server-owned local filesystem write under the backend's configured storage root, performed only after the fake-target receipt exists.

## Storage And Config Authority

The storage root authority is the normalized backend `STORAGE_DIR` setting from `backend/app/core/config.py`.

The admitted outbox root is derived by the server only:

`Path(settings.storage_dir) / "layer3-outbox"`.

The implementation must not accept any caller-supplied path, directory, URL, object key, bucket, provider target, connector target, or external destination. The implementation must resolve every persisted outbox file under the derived server-owned outbox root and fail closed if any computed path escapes that root.

No new credential, provider, network, browser, or operator-local configuration is admitted.

## Write Artifact Shape

The first real-write artifact is a copy of the already validated APS evidence bundle artifact referenced by the current external export/download readiness state.

The implementation may write only:

- one artifact file under the derived server-owned outbox root;
- one JSON receipt/manifest file under the same receipt directory; and
- one durable database receipt for the write.

The path shape is server-derived and deterministic from the write receipt id:

- artifact relative ref: `layer3-outbox/<write_receipt_id>/artifact.json`;
- manifest relative ref: `layer3-outbox/<write_receipt_id>/receipt.json`.

The operator/API response may expose only redacted server-owned storage refs such as `storage://server-owned-local-outbox/<write_receipt_id>/artifact.json`. It must not expose absolute local filesystem paths, source artifact refs, package payload bytes, provider URLs, destination URLs, credentials, bearer tokens, connector targets, prompt/model data, RAG/vector internals, auth internals, or browser storage state.

## Authority Basis

The write authority must derive only from:

- session id;
- approved analysis plan id;
- pass run id;
- reconciliation record id;
- connector dispatch record ref;
- connector-local destination receipt id;
- server-owned local outbox fake-target receipt id;
- external export/download record ref;
- target identity;
- selected write dispatch mode;
- fake-target receipt authority basis hash;
- accepted artifact hash and size; and
- source artifact hash/size validated through existing external export/download delivery authority.

The write must fail closed when the reconciliation summary, fake-target receipt row, connector-local destination receipt row, connector dispatch record, or external export/download readiness state no longer agrees with that basis.

## Lifecycle, Idempotency, And Failure Semantics

Required write status vocabulary:

- `server_owned_local_outbox_write_not_ready`;
- `server_owned_local_outbox_write_ready`;
- `server_owned_local_outbox_write_recorded`;
- `server_owned_local_outbox_write_replay`;
- `server_owned_local_outbox_write_conflict`;
- `server_owned_local_outbox_write_stale_authority`;
- `server_owned_local_outbox_write_failed`.

Required idempotency semantics:

- `client_request_id` is required and unique for the write operation;
- same `client_request_id` plus same authority basis returns the existing write receipt/status;
- same `client_request_id` plus different authority basis fails closed;
- same authority basis plus different `client_request_id` fails closed;
- same deterministic outbox artifact path plus same bytes is not a new write;
- same deterministic outbox artifact path plus different bytes fails closed; and
- retry/rerun/cancel request fields are not admitted.

Partial completion must fail closed. If the artifact copy or manifest write cannot be verified against the expected hash/size, the service must not claim `server_owned_local_outbox_write_recorded`.

## Receipt And Audit Contract

The durable write receipt must include:

- write receipt id;
- fake-target receipt id;
- session id;
- pass run id;
- reconciliation record id;
- connector-local destination receipt id;
- connector dispatch record ref;
- external export/download record ref;
- target identity;
- dispatch mode;
- write state;
- outbox artifact relative ref;
- outbox manifest relative ref;
- outbox artifact hash and size;
- accepted source artifact hash and size;
- authority basis hash;
- authority snapshot;
- idempotency key;
- created timestamp; and
- updated timestamp.

The session summary may add a read-only `server_owned_local_outbox_write` projection with latest write receipt, history count, idempotency policy, failure-state projection, redacted outbox refs, and disabled downstream lanes.

## Security Boundary

Security posture: `server_owned_local_storage_only_no_external_exposure_no_credentials`.

The implementation must not add public exposure, nonlocal destination access, credential storage, provider token custody, connector secret handling, auth policy changes, ACL changes, network writes, or browser-owned durable authority.

The implementation may perform local filesystem writes only under the derived server-owned outbox root.

## Required Proof

The implementation-bearing pass must prove:

1. API contract rejects credentials, destination paths/URLs, connector fields, provider/public fields, package mutation fields, source expansion fields, RAG/vector fields, auth/security override fields, frontend-durable fields, and retry/rerun/cancel fields.
2. Write happy path copies the existing validated source artifact under the derived server-owned outbox root and records a durable write receipt.
3. Response and session summary expose only redacted storage refs, not raw paths.
4. Same-key/same-basis replay is idempotent.
5. Same-key/different-basis conflict fails closed.
6. Same-basis/different-key conflict fails closed.
7. Stale authority, wrong session, wrong artifact hash/size, wrong fake-target receipt id, wrong connector-local receipt id, wrong connector dispatch ref, and wrong external export/download ref fail closed.
8. Database counts prove no `ConnectorRun` or `ConnectorRunTarget` creation.
9. Filesystem proof shows all outbox writes stay under `Path(settings.storage_dir) / "layer3-outbox"`.
10. Focused headed and headless E2E proof is required only if a rendered UI status change is made in this tranche.

## Non-Admission Boundary

This freeze admits no real connector invocation, no external destination write, no operator-provided destination path, no destination URL, no connector-run creation, no `ConnectorRunTarget` creation, no credential handling, no provider-public delivery/use, no external provider/object-store behavior, no package mutation/reconstruction, no source expansion, no RAG/vector behavior, no broad auth/security implementation, no full mockup activation, no frontend-durable authority, no generic downstream dispatch, no rendered write controls, and no browser-owned target authority.

## Stop Conditions

Stop before implementation if the next pass:

- selects more than `server_owned_local_delivery_outbox_destination`;
- requires external credentials, connector secrets, provider tokens, or network access;
- accepts operator-provided local paths, destination paths, destination URLs, provider URLs, buckets, object keys, or connector targets;
- creates `ConnectorRun` or `ConnectorRunTarget` rows;
- writes outside `Path(settings.storage_dir) / "layer3-outbox"`;
- exposes raw local filesystem paths, source artifact refs, credentials, provider URLs, destination URLs, connector targets, package payload bytes, source contents, prompt/model data, RAG/vector internals, auth internals, or browser storage state;
- widens package, source, RAG/vector, provider-public, mockup, or auth/security behavior as a side effect; or
- cannot prove the write in isolated runtime state.

## Next Posture

The next whole-project posture is `implement_server_owned_local_outbox_real_write_after_admission_freeze`.
