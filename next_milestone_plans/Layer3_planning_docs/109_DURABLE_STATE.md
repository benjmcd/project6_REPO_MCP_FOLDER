# Layer 3 Durable Signed-Reference State Contract

## Purpose

This contract specifies the durable token, receipt, revocation, and audit state shape landed by PR `#520` from branch `codex/l3-durable-runtime-p23`. It is the implementation contract for the bounded same-origin durable signed-reference state slice.

## State Model

### `l3_signed_reference_token`

Required fields:

- `signed_reference_token_id`: primary key UUID string.
- `session_id`: foreign key to `l3_session.session_id`.
- `reconciliation_record_id`: foreign key to `l3_reconciliation_record.reconciliation_record_id`.
- `token_hash`: unique hash of the bearer token or opaque handle.
- `token_prefix`: short response-safe diagnostic prefix.
- `state`: one of `ready`, `used`, `revoked`, `expired`; `created` and `denied` remain reserved for later endpoint/read-model expansion.
- `replay_policy`: one of `single_use`, `bounded_replay`, `replay_allowed`.
- `max_use_count`: integer, fixed at `1` for this first `single_use` implementation.
- `use_count`: integer.
- `expires_at`: timezone-aware datetime.
- `authority_hash`: hash of the PR `#499` delivery authority basis.
- `authority_snapshot_json`: response-safe authority basis with no raw token.
- `request_basis_hash`: idempotency basis for generation.
- `created_by_request_id`: generation `client_request_id`.
- `created_at`, `updated_at`, `last_used_at`.

Required constraints:

- unique `token_hash`;
- index `session_id`;
- index `reconciliation_record_id`;
- index `(state, expires_at)`;
- unique idempotency key over the selected generation basis.

### `l3_signed_reference_receipt`

Required fields:

- `signed_reference_receipt_id`: primary key UUID string.
- `signed_reference_token_id`: foreign key to `l3_signed_reference_token`.
- `receipt_type`: one of `generated`, `used`; `delivered`, `denied`, and `revoked` remain reserved for later endpoint/read-model expansion.
- `receipt_status`: response-safe status.
- `request_id`: client request id when present.
- `authority_hash`: authority basis hash observed for the receipt.
- `artifact_ref`, `artifact_hash`, `artifact_size_bytes`: populated only when delivery reaches an artifact basis.
- `receipt_payload_json`: response-safe receipt details.
- `created_at`.

Receipts must be immutable after creation. A receipt must not contain raw bearer tokens, provider URLs, connector ids, destination ids, local file paths, or package payload bytes.

### `l3_signed_reference_revocation`

Required fields:

- `signed_reference_revocation_id`: primary key UUID string.
- `signed_reference_token_id`: foreign key to `l3_signed_reference_token`.
- `idempotency_key`: unique revocation request key for the token.
- `revoked_by`: server/operator actor string.
- `revocation_reason`: constrained reason code.
- `revocation_payload_json`: response-safe details.
- `created_at`.

Revocation must be idempotent. A second revoke with the same key must return the same final token state. A second revoke with a different key must not resurrect or mutate a revoked token except to append an audit event.

### `l3_signed_reference_audit_event`

Required fields:

- `signed_reference_audit_event_id`: primary key UUID string.
- `signed_reference_token_id`: nullable foreign key to `l3_signed_reference_token`.
- `event_type`: one of `generate`, `use`; deny, expiry, revoke, replay, stale-authority, and malformed-token distinctions are encoded in `event_status` and `reason_code` for this first implementation.
- `event_status`: response-safe status.
- `request_id`: client request id when present.
- `authority_hash`: authority hash when available.
- `reason_code`: constrained reason code.
- `event_payload_json`: response-safe payload with no raw token.
- `created_at`.

Audit events must be append-only. Audit write failure must fail closed unless a later security review explicitly permits delivery without audit persistence.

## API Contract

The existing generate endpoint may add response-safe durable fields:

- `signed_reference_token_id`
- `signed_reference_token_prefix`
- `signed_reference_receipt_id`
- `signed_reference_replay_policy`
- `signed_reference_use_count`
- `signed_reference_max_use_count`
- `signed_reference_revoked`
- `signed_reference_audit_event_id`

The existing use endpoint may add response headers:

- `X-Layer3-Signed-Reference-Token-Id`
- `X-Layer3-Signed-Reference-Receipt-Id`
- `X-Layer3-Signed-Reference-Replay-Policy`
- `X-Layer3-Signed-Reference-Use-Count`

The use request body remains token-only unless a later freeze admits a revoke or receipt-read endpoint. Provider URL fields, connector fields, destination fields, package mutation fields, source-widening fields, and qualitative execution fields remain outside the request schema.

## Revocation Endpoint Decision

Do not add a revocation endpoint in the first durable implementation unless the implementation freeze explicitly admits it.

The first implementation includes revocation table awareness but no public/API/UI revocation route. Rendered UI and public API revocation must remain out until a separate endpoint/UI freeze names:

- route path;
- request schema;
- actor authority;
- idempotency key;
- response fields;
- browser proof requirements.

## Compatibility Rule

PR `#499` stateless HMAC behavior is preserved as the authority validator and token envelope baseline. The durable layer adds lookup state and fail-closed revocation/replay checks, but it must still:

- require `LAYER3_SIGNED_REFERENCE_SECRET`;
- reject malformed tokens;
- reject signature mismatch;
- reject expired tokens through the HMAC expiry guard and durable expiry state when reached through a recorded token row;
- reject extra use-request fields;
- revalidate current associated-cohort delivery authority;
- keep public/provider URLs, connector/destination dispatch, package mutation, schema/runtime/source widening, qualitative execution, and broader UI out.

## Concurrency Rule

The implementation must use database transactions around state transitions. Simultaneous use/revoke/expire attempts must resolve deterministically:

- `revoked` beats `ready` and `used`;
- `expired` beats `ready` and `used` when current time is at or after expiry;
- replay is denied after one accepted use because this implementation selects `single_use` and `max_use_count=1`;
- receipt creation and audit creation must be in the same committed unit as the token transition unless the implementation documents a stricter fail-closed order.

## Retention Rule

Cleanup remains a later lane, but the schema includes indexed state for cleanup by `expires_at`, terminal state, and creation time.

## Security Rules

The implementation must:

- never persist raw bearer tokens;
- never log raw bearer tokens in normal response or audit paths;
- treat token hashes as sensitive operational data;
- avoid echoing raw tokens except in the existing generate response body if that response remains admitted;
- keep token prefixes short and non-secret;
- make secret rotation behavior explicit before deployment;
- fail closed on missing secret, missing durable state, and audit persistence failure.

## No-Go Boundaries

This contract does not admit:

- provider/public signed URLs;
- external object-store ACL behavior;
- connector dispatch, destination selection, or connector-run state;
- copy/share/refresh/revoke rendered UI controls;
- qualitative APS content document execution;
- non-PDF source execution expansion;
- package mutation or reconstruction;
- runtime snapshot DB writes;
- source/schema/runtime widening beyond the named durable control-plane table family.
