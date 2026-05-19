# 852 - Internal Webhook Connector Freeze

## Status

Status: implementation-entry freeze for `server_configured_internal_webhook_destination`.

Doc: `852_INTERNAL_WEBHOOK_CONNECTOR_FREEZE.md`.

Current-main preflight checkpoint: `10ebfbbe9422ca92907f320a2b0efed75b0fc544`.

Predecessor decision packet: `609_REAL_CONNECTOR_DESTINATION_DECISION_PACKET_AFTER_LOCAL_OUTBOX_WRITE.md`.

Selected implementation action: `implement_server_configured_internal_webhook_destination_dispatch`.

Runtime status before implementation: `not_implemented`.

Runtime behavior introduced by this freeze: `false`.

Implementation-entry allowed next: true, after current-main sync, for only the exact internal webhook connector slice defined here.

## Selected Target

Target identity: `server_configured_internal_webhook_destination`.

Target class: `real_connector_invocation`.

Target owner: `Bennet / project operator`.

Operator purpose: after Layer 3 completes source-directory ingestion, retrieval/context, qualitative analysis, package review, handoff/export prepare, and export/download readiness, dispatch one redacted server-owned delivery envelope to one server-configured allowlisted internal webhook destination for downstream system handoff.

Selected dispatch mode: `server_configured_allowlisted_internal_webhook_post`.

Selected destination address model: `server_configured_allowlisted_url`.

Operator surface for the first slice: `read_only_status_only`.

No rendered write/submit control is admitted by this freeze.

## Authority Basis

The dispatch authority must derive only from:

- approved package-review submit authority;
- handoff/export prepare authority;
- external export/download prepare authority where applicable;
- server-owned package artifact refs, hash, and size;
- session id;
- pass run id;
- package ref and package kind;
- handoff/export prepare ref;
- export/download readiness ref where required;
- target identity;
- target class;
- selected dispatch mode;
- client request id; and
- a stable request basis hash over the selected authority and artifact basis.

The implementation must fail closed on stale package authority, wrong session, wrong pass, wrong package, missing package-review submit, missing handoff/export prepare, missing export/download readiness where required, artifact hash mismatch, artifact size mismatch, target mismatch, unsupported provider state, unsupported credential state, caller-supplied destination URL, timeout, partial response, ambiguous response, or any authority basis mismatch.

## Service, API, And Receiver Shape

The next implementation may add one backend owner service seam:

- `backend/app/services/layer3_internal_webhook_connector.py`.

The next implementation may add one API dispatch entrypoint and one read-only status entrypoint, or an explicitly equivalent internal-only harness if the implementation proves that no operator-triggered API surface is required:

- `POST /api/v1/layer3/handoff/export/internal-webhook/dispatch`;
- `GET /api/v1/layer3/handoff/export/internal-webhook/status/{internal_webhook_dispatch_receipt_id}`.

The POST entrypoint must accept only server-authority references and `client_request_id`. It must not accept destination URL, provider URL, raw local path, raw package payload, package bytes, credentials, token, header, body override, connector target, retry mode, rerun flag, source material, RAG/vector input, optional-tool input, or auth/security override fields.

The first proof path must use a server-configured fake/internal webhook receiver. Any allowlisted URL used by tests must be server configured and internal-only. External internet destinations are not admitted.

## Envelope Contract

The first slice may POST exactly one redacted Layer 3 handoff/export delivery envelope.

The envelope may include:

- schema id;
- session id;
- pass run id;
- package ref;
- package kind;
- package artifact ref;
- package artifact hash;
- package artifact size;
- handoff/export prepare ref;
- external export/download readiness ref where applicable;
- target identity;
- target class;
- idempotency key;
- request basis hash;
- dispatch timestamp; and
- redacted operator-facing status fields.

The envelope must not include raw package bytes, raw package payload, raw destination URL, raw token, raw secret header, raw local filesystem path, source document contents, provider object key, public URL, signed URL, prompt/model data, RAG/vector internals, optional-tool outputs, browser storage state, or auth internals.

Do not send raw package bytes in this first slice.

## Credential And Network Boundary

Credential model: `no_credentials`.

If the implementation requires receiver authentication for tests, it may use only a server-configured test secret header. It must not accept an operator-supplied token, browser-supplied credential, provider credential, OAuth token, stored provider credential, or arbitrary header.

Network posture: `private_internal_only_server_configured_allowlist`.

No public URL, provider-public delivery, provider-private signed URL, cloud object-store write, ACL change, external internet target, arbitrary operator-entered URL, destination self-selection, or provider/network widening is admitted.

## Idempotency Semantics

Required idempotency behavior:

- same `client_request_id` plus same authority/artifact basis returns the same durable receipt and status;
- same `client_request_id` plus different authority/artifact basis fails closed;
- same package/export basis plus a new `client_request_id` returns existing status unless a later freeze admits duplicate dispatch;
- identical replay returns existing receipt/status; and
- conflicting replay fails closed.

The request basis hash must bind the authority basis, artifact basis, target identity, target class, dispatch mode, and idempotency key.

## Receipt And Audit Contract

The next implementation may add durable receipt and audit state only for this selected dispatch mode.

The durable connector dispatch receipt must include:

- internal webhook dispatch receipt id;
- session id;
- pass run id;
- package ref;
- package kind;
- package artifact ref;
- package artifact hash;
- package artifact size;
- handoff/export prepare ref;
- external export/download readiness ref where applicable;
- target identity;
- target class;
- redacted destination display name;
- idempotency key;
- request basis hash;
- dispatch status;
- response status code if applicable;
- redacted response summary;
- created timestamp;
- updated timestamp;
- failure code; and
- audit event history.

Audit events must record request accepted, dispatch attempted, dispatch completed, dispatch failed, idempotent replay, conflict replay, stale authority, target mismatch, redaction failure, timeout, partial response, ambiguous response, and blocked forbidden-input attempts.

Receipts, audit events, API responses, logs, test output, screenshots, and proof manifests must not expose raw target URL, raw token/header, raw local path, raw package payload, raw package bytes, source content, provider object keys, public URLs, signed URLs, browser storage, or auth internals.

## Read-Only Operator Status

The implementation may project read-only status/history into the API response and session summary.

The projection may expose only:

- dispatch status;
- internal webhook dispatch receipt id;
- target identity;
- target class;
- redacted destination display name;
- package ref;
- package kind;
- artifact hash and size;
- idempotency policy;
- redacted response summary;
- failure code;
- timestamps; and
- audit history count.

Rendered write/submit controls remain blocked. Rendered read-only status may be admitted only if the implementation freeze or a later rendered freeze names the exact projection and proves headed/headless behavior.

## Required Proof

The implementation-bearing pass must prove:

1. Authority binding rejects stale package authority, wrong session, wrong pass, wrong package, missing package-review submit, missing handoff/export prepare, missing export/download readiness where required, artifact hash mismatch, artifact size mismatch, and target mismatch.
2. API contract rejects caller-supplied destination URL, provider URL, raw local path, raw package payload, credentials, token/header, connector target, retry/rerun flags, source expansion input, RAG/vector input, optional-tool input, and auth/security override fields.
3. Happy path POSTs exactly one redacted delivery envelope to the server-configured fake/internal webhook receiver and records one durable receipt.
4. Same-key/same-basis replay returns the existing receipt/status.
5. Same-key/different-basis replay fails closed.
6. Same package/export basis plus new client request id returns existing status unless duplicate dispatch is separately frozen.
7. Timeout, partial response, ambiguous response, unsupported credential state, unsupported provider state, and non-allowlisted destination fail closed.
8. Response, receipt, audit, logs, and proof output redact raw destination URL, raw token/header, raw local path, raw package payload, and raw package bytes.
9. Database counts prove no `ConnectorRun` or `ConnectorRunTarget` rows are created unless separately frozen.
10. No provider-public URL, provider-private signed URL, cloud object-store write, package mutation, source expansion, vector/RAG widening, optional-tool runtime, Gate C/pass-entry optional-tool admission, or broad auth/security behavior occurs.
11. Focused headed and headless E2E proof is required only if rendered status behavior is admitted.

## Non-Admission Boundary

This freeze admits no runtime behavior by itself, no arbitrary connector dispatch, no arbitrary destination URL, no operator-supplied URL, no provider-public URL, no provider-private signed URL, no cloud object-store write, no OAuth/provider credentials, no stored provider credentials, no `ConnectorRun`, no `ConnectorRunTarget`, no package mutation, no package payload rewrite, no raw package byte delivery, no source expansion, no vector/RAG widening, no TabPFN runtime, no NRC RAG runtime, no optional-tool Gate C/pass-entry admission, no broad auth/security behavior, no rendered write/submit control, no public exposure, and no frontend-only durable authority.

## Stop Conditions

Stop before implementation if the next pass:

- accepts more than `server_configured_internal_webhook_destination`;
- accepts caller-supplied destination URLs, provider URLs, raw local paths, raw package payloads, package bytes, credentials, tokens, arbitrary headers, connector targets, retry/rerun flags, source material, RAG/vector inputs, optional-tool inputs, or auth/security overrides;
- requires external internet delivery;
- creates `ConnectorRun` or `ConnectorRunTarget` rows;
- exposes raw destination URLs, raw tokens/headers, raw local paths, raw package payloads, raw package bytes, public URLs, signed URLs, provider object keys, browser storage, or auth internals;
- sends package bytes instead of the redacted envelope;
- widens provider/public URL, provider-private signed URL, package mutation, source expansion, RAG/vector, optional-tool, Gate C/pass-entry, rendered write-control, or auth/security behavior; or
- cannot prove the dispatch in isolated runtime state with a server-configured fake/internal webhook receiver.

## Next Posture

The next exact posture after this freeze is current-main sync for `server_configured_internal_webhook_destination`.

After current-main sync, the next exact implementation posture is `implement_server_configured_internal_webhook_destination_dispatch`.
