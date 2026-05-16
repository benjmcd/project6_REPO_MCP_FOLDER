# 610 - Real Target Freeze After Local Outbox Write

## Status

Status: implemented and merged on current main for `server_owned_local_outbox_provider_private_handoff_target_after_local_outbox_write`.

Doc: `610_REAL_TARGET_FREEZE.md`.

Pre-implementation current-main checkpoint: `e813759ee4c9346d5bb7fefe737c7c046fc55644`.

Implemented feature commit: `d44cd7dc2a5d5f848b2d794f8cdac697e8c94dde`.

Merged current-main checkpoint: `3eb68cdd4c6e6b2582515ef9f76b62b22d3deb5e`.

Merged PR: `#1207`.

Prior decision packet: `609_REAL_CONNECTOR_DESTINATION_DECISION_PACKET_AFTER_LOCAL_OUTBOX_WRITE.md`.

Runtime status before implementation: `server_owned_local_outbox_write_implemented_and_reaudited_on_current_main`.

Implementation-entry result: fake-provider prepare/status slice implemented and merged; further real-provider, destination-write, provider-public, raw-token, package, source-expansion, RAG/vector, auth/security, rendered-write-control, full-mockup, and frontend-durable authority remains blocked unless separately frozen and admitted.

## Selected Target

Selected target identity: `server_owned_local_outbox_provider_private_handoff_destination`.

Selected target class: `provider_private_handoff_destination`.

Selected downstream use case: `operator_requests_private_downstream_access_to_server_owned_local_outbox_artifact_after_receipt_lifecycle_proof`.

Selected artifact family: `aps_evidence_bundle_from_server_owned_local_outbox_write`.

Selected dispatch mode: `provider_private_fake_provider_prepare_status_from_local_outbox_receipt`.

Selected operator decision: `prepare_provider_private_handoff_from_local_outbox`.

This target is a destination handoff target, not a generic connector invocation. It is selected because current main now proves the server-owned local receipt to outbox write lifecycle, and the repo already contains provider-private fake-provider and durable-state substrate. The first implementation slice must bind that substrate to the local outbox receipt chain without admitting provider-public delivery/use, raw token use, provider network writes, credentials, `ConnectorRun` creation, package mutation, source expansion, RAG/vector behavior, broad auth/security behavior, full mockup activation, or frontend-durable authority.

## Current Evidence Basis

Repo-confirmed authority used for this freeze:

- `backend/app/services/layer3_server_owned_local_outbox_write.py` owns the completed server-owned local outbox write target, including `SERVER_OWNED_LOCAL_OUTBOX_WRITE_IDENTITY`, derived `layer3-outbox` storage, redacted storage refs, and forbidden downstream fields.
- `backend/app/services/layer3_connector_local_destination_receipt.py` owns the local fake/destination receipt authority that precedes the local outbox target and write.
- `backend/app/services/layer3_connector_dispatch_entry.py` owns the internal dispatch record authority and keeps connector invocation, destination writes, and connector-run creation disabled.
- `backend/app/services/layer3_provider_private_signed_url.py`, `backend/app/services/layer3_provider_private_signed_url_fake_provider.py`, and `backend/app/services/layer3_provider_private_signed_url_state.py` prove the repo already has provider-private fake-provider and durable-state substrate that can be reused or wrapped for a local-outbox-bound handoff target.
- `backend/app/api/layer3.py` exposes existing connector-local, local outbox, and provider-private route families and already models broad forbidden fields for connector, destination, provider-public, token, source, package, RAG/vector, auth/security, and browser-durable inputs.
- `e2e/layer3-handoff.spec.js` proves the current local receipt to server-owned local outbox lifecycle reaches a read-only rendered state before any future provider-private target is admitted.

This evidence does not prove a live provider-private local-outbox handoff yet. It proves only that the next implementation-entry target can be frozen without selecting a generic connector, provider-public surface, raw token use, or broader runtime expansion.

## Decision Resolution Against 609

The open decisions from `609_REAL_CONNECTOR_DESTINATION_DECISION_PACKET_AFTER_LOCAL_OUTBOX_WRITE.md` are resolved for this target as follows:

| 609 decision | Resolution |
| --- | --- |
| Target identity | `server_owned_local_outbox_provider_private_handoff_destination`, owned by the Layer 3 handoff/export runtime, for private downstream access to the server-owned local outbox artifact. |
| Target class | `provider_private_handoff_destination`; destination handoff target, not generic connector invocation and not provider-public delivery/use. |
| Authority basis | Existing server-owned local outbox write receipt plus the connector dispatch, connector-local receipt, fake-target receipt, external export/download readiness, session, pass, reconciliation, and artifact hash/size chain. |
| Artifact family | `aps_evidence_bundle_from_server_owned_local_outbox_write`; source is the server-owned local outbox artifact and manifest produced from already validated external export/download authority. |
| Credential model | `no_operator_credentials_fake_provider_first`; no accepted credential fields, no stored secrets, no delegated token, no provider token, and no raw token exposure in the first slice. |
| Destination address model | Server-derived fake-provider object identity from local outbox write receipt id and authority basis hash; no caller address, path, URL, bucket, object key, connector target, or provider target. |
| Side-effect boundary | Fake-provider prepare/status receipt only; no provider network write, object-store write, external destination write, connector invocation, public URL, raw token use, or local outbox artifact mutation. |
| Idempotency semantics | `client_request_id` plus authority basis controls replay and conflict; same-basis/new-key remains fail-closed unless a later freeze admits multi-recipient behavior. |
| Failure lifecycle | Stale authority, wrong session, wrong artifact hash/size, wrong connector dispatch/local receipt/fake-target/outbox write refs, wrong destination identity, TTL expiry, fake-provider failure, timeout, and partial completion fail closed. |
| Receipt/audit contract | Durable provider-private handoff receipt with redacted provider marker, authority snapshot, source/outbox hashes, TTL, fake-provider status, and explicit disabled-surface booleans. |
| Security posture | `no_external_exposure_no_credentials_no_raw_token_fake_provider_first`; later real provider, token, credential, public, proxy, or network behavior needs its own freeze. |
| Test architecture | Fake-provider prepare/status backend/API tests, OpenAPI schema proof, isolated runtime state, negative forbidden-field/authority/idempotency tests, DB count checks, filesystem non-mutation proof, and headed/headless E2E only if rendered status changes. |

## Authority Basis

The future implementation must derive authority only from server-owned Layer 3 state:

- session id;
- analysis plan id;
- pass run id;
- reconciliation record id;
- connector dispatch record ref;
- connector-local destination receipt id;
- server-owned local outbox fake-target receipt id;
- server-owned local outbox write receipt id;
- external export/download record ref;
- target identity;
- selected dispatch mode;
- server-owned local outbox write authority basis hash;
- server-owned outbox artifact hash and size;
- accepted source artifact hash and size; and
- `client_request_id` supplied only as the idempotency key.

Browser state, copied local paths, operator-entered destination paths, provider URLs, public URLs, connector keys, credentials, provider object keys, raw token material, package payload bytes, source upload fields, RAG/vector fields, prompt/model fields, and auth/security overrides are not authority.

## Credential And Destination Model

Credential model: `no_operator_credentials_fake_provider_first`.

Destination address model: `server_derived_fake_provider_object_from_local_outbox_write_receipt`.

The first implementation slice must not accept or persist credentials. It must not call an external provider, connector, storage service, network endpoint, public URL service, or operator-provided filesystem path. The fake provider object identity must be derived by the server from the local outbox write receipt id and authority basis hash.

Any later real provider, real object-store, public URL, proxy, raw token use, or credential custody pass requires a separate freeze tied to that exact surface.

## Admitted First Slice

The next implementation-bearing pass may add only:

- one owner service seam, preferably `backend/app/services/layer3_local_outbox_provider_private_handoff.py`;
- one prepare API entrypoint;
- one read-only status API entrypoint;
- one durable receipt/audit contract for the local-outbox provider-private handoff target;
- fake-provider prepare/status behavior over existing server authority;
- OpenAPI request/response examples for prepare/status; and
- targeted backend tests proving authority, idempotency, redaction, and negative guardrails.

Candidate route namespace:

```yaml
prepare: POST /api/v1/layer3/handoff/connector/local-outbox/provider-private/prepare
status: GET /api/v1/layer3/handoff/connector/local-outbox/provider-private/status/{provider_private_handoff_receipt_id}
```

The first slice is backend/API-only unless implementation discovers that existing read-only session summary projection must include this status for operator review. If rendered status is changed, focused headed and headless Playwright proof is required. No rendered write controls are admitted.

## Request Contract

The prepare request may accept only:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `connector_dispatch_record_ref`;
- `connector_local_destination_receipt_id`;
- `server_owned_local_outbox_target_receipt_id`;
- `server_owned_local_outbox_write_receipt_id`;
- `external_export_download_record_ref`;
- `target_identity`;
- `dispatch_mode`;
- `operator_decision`;
- `recipient_scope`;
- `requested_ttl_seconds`; and
- optional `decision_notes`.

The route must derive or validate artifact authority from the durable local outbox write receipt and current reconciliation summary. It must not accept raw local paths, destination paths, provider object identifiers, provider credentials, buckets, containers, object keys, connector payloads, connector secrets, public URLs, provider URLs, raw token material, package mutation payloads, source expansion inputs, RAG/vector settings, prompt/model fields, auth/security overrides, browser durable authority, retry, rerun, cancel, or use/revoke fields.

## Response And Status Contract

Prepare and status responses may expose only redacted server-owned fields:

- schema id/version and request id;
- status;
- session, pass, reconciliation, connector dispatch, local receipt, fake-target receipt, outbox write receipt, and external export/download refs;
- `provider_private_handoff_receipt_id`;
- target identity;
- dispatch mode;
- recipient scope;
- TTL/expiry projection;
- redacted provider-private marker, not a usable URL or bearer token;
- idempotency/replay policy;
- source artifact hash/size;
- outbox artifact hash/size;
- authority basis hash;
- audit receipt summary; and
- disabled downstream lanes.

Responses and errors must not expose raw provider URLs, raw signed URLs, raw token material, credentials, provider object keys, connector targets, destination URLs, absolute local filesystem paths, source artifact refs, package payload bytes, source contents, prompt/model data, RAG/vector internals, auth internals, or browser storage state.

## Lifecycle, Idempotency, And Failure Semantics

Required status vocabulary:

- `local_outbox_provider_private_handoff_not_ready`;
- `local_outbox_provider_private_handoff_ready`;
- `local_outbox_provider_private_handoff_prepared`;
- `local_outbox_provider_private_handoff_replay`;
- `local_outbox_provider_private_handoff_conflict`;
- `local_outbox_provider_private_handoff_stale_authority`;
- `local_outbox_provider_private_handoff_expired`;
- `local_outbox_provider_private_handoff_failed`.

Required idempotency semantics:

- `client_request_id` is required and unique for the prepare operation;
- same `client_request_id` plus same authority basis returns the existing receipt/status;
- same `client_request_id` plus different authority basis fails closed;
- same authority basis plus different `client_request_id` fails closed unless a later freeze admits multi-recipient behavior;
- duplicate fake-provider object identity with same basis is replay/status-only;
- duplicate fake-provider object identity with different basis fails closed;
- stale session, stale reconciliation summary, wrong local receipt, wrong fake-target receipt, wrong outbox write receipt, wrong external export/download ref, wrong artifact hash, wrong artifact size, expired TTL, fake-provider failure, timeout, partial completion, and wrong destination identity fail closed; and
- retry/rerun/cancel/use/revoke are not admitted in the first slice.

## Receipt And Audit Contract

The durable receipt/audit contract must include:

- provider-private handoff receipt id;
- client request id;
- session id;
- analysis plan id;
- pass run id;
- reconciliation record id;
- connector dispatch record ref;
- connector-local destination receipt id;
- server-owned local outbox fake-target receipt id;
- server-owned local outbox write receipt id;
- external export/download record ref;
- target identity `server_owned_local_outbox_provider_private_handoff_destination`;
- dispatch mode `provider_private_fake_provider_prepare_status_from_local_outbox_receipt`;
- recipient scope;
- requested TTL and expiry projection;
- redacted provider-private marker;
- source artifact hash and size;
- outbox artifact hash and size;
- authority basis hash;
- authority snapshot;
- status;
- fake-provider status/error projection;
- created timestamp; and
- updated timestamp.

The audit record must include explicit booleans showing that real connector invocation, external destination write, `ConnectorRun` creation, `ConnectorRunTarget` creation, credential handling, provider-public delivery/use, raw token use, package mutation/reconstruction, source expansion, RAG/vector behavior, broad auth/security behavior, full mockup activation, frontend-durable authority, and generic downstream dispatch remain disabled.

## Required Proof

The implementation-bearing pass must prove:

1. Prepare success from an existing server-owned local outbox write receipt.
2. Status success from the durable provider-private handoff receipt.
3. OpenAPI prepare/status request and response schema.
4. Forbidden request fields fail closed.
5. Same-key/same-basis replay is idempotent.
6. Same-key/different-basis conflict fails closed.
7. Same-basis/different-key conflict fails closed.
8. Stale authority, wrong session, wrong artifact hash/size, wrong connector dispatch ref, wrong local receipt id, wrong fake-target receipt id, wrong outbox write receipt id, and wrong external export/download ref fail closed.
9. TTL validation and expiry projection are deterministic.
10. Fake-provider failure maps to a controlled API error without leaking raw token/provider internals.
11. Database counts prove no `ConnectorRun` or `ConnectorRunTarget` creation.
12. Filesystem proof shows no mutation of the existing local outbox artifact.
13. Responses and errors expose only redacted provider-private and storage refs.
14. Existing same-origin delivery, signed-reference, connector-local receipt, local outbox write, provider-public, package, source, RAG/vector, auth/security, and rendered UI behavior remain unchanged unless separately frozen.
15. Headed/headless E2E proof runs only if a rendered operator status projection is changed.

## Non-Admission Boundary

This freeze admits no real connector invocation, no generic connector framework, no unfrozen destination write, no external object-store/network write, no `ConnectorRun` creation, no `ConnectorRunTarget` creation, no operator-provided destination path, no destination URL, no connector target, no credential handling, no provider-public delivery/use, no public proxy URL, no raw provider-private token use route, no raw token durable persistence, no package mutation/reconstruction, no source expansion, no RAG/vector behavior, no broad auth/security implementation, no full mockup activation, no frontend-durable authority, no generic downstream dispatch, no rendered write controls, and no browser-owned target authority.

## Stop Conditions

Stop before implementation if the next pass:

- selects more than `server_owned_local_outbox_provider_private_handoff_destination`;
- requires external credentials, connector secrets, provider tokens, raw token exposure, public URL exposure, or network access;
- accepts operator-provided local paths, destination paths, destination URLs, provider URLs, buckets, containers, object keys, or connector targets;
- creates `ConnectorRun` or `ConnectorRunTarget` rows;
- mutates the existing server-owned local outbox artifact;
- exposes raw local filesystem paths, source artifact refs, provider URLs, signed URLs, raw token material, credentials, connector targets, destination URLs, package payload bytes, source contents, prompt/model data, RAG/vector internals, auth internals, or browser storage state;
- widens package, source, RAG/vector, provider-public, mockup, rendered UI, or auth/security behavior as a side effect; or
- cannot prove fake-provider prepare/status behavior in isolated runtime state.

## Next Posture

The next whole-project posture is `implement_local_outbox_provider_private_handoff_prepare_status_after_freeze`.

## Current-Main Implementation Status

Current main status: `local_outbox_provider_private_handoff_prepare_status_implemented_merged`.

Implemented first-slice surfaces:

- durable receipt table `l3_local_outbox_provider_private_handoff_receipt`;
- durable audit table `l3_local_outbox_provider_private_handoff_audit_event`;
- owner service `backend/app/services/layer3_local_outbox_provider_private_handoff.py`;
- prepare API `POST /api/v1/layer3/handoff/connector/local-outbox/provider-private/prepare`;
- read-only status API `GET /api/v1/layer3/handoff/connector/local-outbox/provider-private/status/{provider_private_handoff_receipt_id}`; and
- OpenAPI and targeted backend proof in `backend/tests/test_layer3_api.py`.

Merged proof already exercised:

- prepare success from an existing server-owned local outbox write receipt;
- read-only status success from durable handoff state;
- same-key/same-payload replay;
- same-key/different-payload conflict;
- same-authority/different-client-request conflict;
- forbidden field, TTL, wrong dispatch mode, wrong operator decision, wrong connector dispatch ref, wrong write receipt, missing receipt, fake-provider failure, expired status, and stale authority fail-closed cases;
- no `ConnectorRun` or `ConnectorRunTarget` creation;
- no provider-private signed URL durable-state row creation;
- no package mutation;
- no raw token, signed URL, provider URL, source artifact ref, credential, destination path, or absolute filesystem path exposure in responses; and
- migration upgrade to head against isolated in-memory SQLite.

Still not admitted by this implementation:

- real connector invocation;
- external provider network writes;
- external object-store writes;
- destination writes;
- `ConnectorRun` or `ConnectorRunTarget` creation;
- credentials or raw provider token use;
- provider-public delivery/use;
- package mutation/reconstruction;
- source expansion;
- RAG/vector behavior;
- broad auth/security behavior;
- rendered write controls;
- full mockup activation; and
- frontend-durable authority.

Next whole-project pass after this merge: choose between adding a read-only session-summary/history projection for this handoff receipt or freezing a named real provider/destination target. The default next pass should be the read-only projection unless current-main authority proves it already exists or a named external target freeze has been separately admitted.
