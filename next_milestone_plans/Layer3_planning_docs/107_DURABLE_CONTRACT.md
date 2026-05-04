# Layer 3 Durable Signed-Reference Contract

## Purpose

This contract defines the minimum shape the durable signed-reference implementation must satisfy. It exists to prevent durable token, receipt, revocation, and audit work from being hidden inside provider/public URL, connector/destination, qualitative execution, or UI-only patches.

Docs `108_DURABLE_ENTRY.md` and `109_DURABLE_STATE.md` provide the implementation-entry refinement of this contract. PR `#520` landed the bounded runtime implementation on `project6-origin/main` at merge commit `721b892b88ef88bf1364e2c71f762fabccdeb171`.

## Contract Boundary

The durable-state layer sits between the already-live same-origin signed-reference endpoints and any future provider/public URL or connector/destination behavior.

Current live endpoints remain:

- `POST /api/v1/layer3/handoff/export/download/signed-reference/generate`
- `POST /api/v1/layer3/handoff/export/download/signed-reference/use`

This implementation preserves those endpoints and adds durable backing state behind the same admitted same-origin contract. Future successor endpoints remain out of scope unless a later freeze admits them.

The compatibility rule is: preserve the PR `#499` HMAC envelope, missing-secret failure, 300-second TTL posture, token-only use request, and generation/use authority revalidation, while intentionally adding durable missing-state, revocation, and single-use replay failure modes.

## State Requirements

The durable implementation defines:

- `token_record`: persisted token identity, token hash or opaque lookup key, authority snapshot, expiry, state, and creation metadata;
- `receipt_record`: immutable proof of generation/use/delivery outcome, artifact basis, authority basis, and response-safe receipt id;
- `revocation_record`: revocation actor, time, reason, idempotency key, and final token state;
- `audit_event`: append-only event family for generate, use, deliver, revoke, expire, replay-deny, stale-authority-deny, and malformed-token-deny;
- `authority_binding`: explicit binding to associated-cohort delivery readiness, PR `#487` delivery UI authority, and PR `#499` same-origin signed-reference authority.

The implementation must not persist raw bearer tokens. If a bearer token is used, only a hash or opaque lookup handle may be stored unless a later security review explicitly admits otherwise.

## State Machine

The durable token state machine must be explicit:

- `created`: durable token record exists and is not yet usable until all authority checks pass;
- `ready`: token may be used through the admitted same-origin API;
- `used`: token was accepted at least once, with replay policy determining whether further use is allowed;
- `revoked`: token was explicitly revoked and must fail closed;
- `expired`: token lifetime elapsed and must fail closed;
- `denied`: malformed, stale-authority, missing-secret, or policy-denied use attempt was recorded without granting access.

For this first runtime slice, `used` is terminal. Replay is denied after one accepted use with `single_use` and `max_use_count=1`. A replay attempt records an audit denial and does not create a delivery receipt.

## API Requirements

The implementation defines response fields for:

- token readiness and expiry;
- durable token id or token prefix only, never raw token echo beyond the existing generated token response if that response remains admitted;
- receipt id and receipt status;
- revoked/expired/stale/malformed failure codes;
- audit-safe reason codes;
- disabled downstream flags for provider/public URL and connector/destination behavior until those separate gates are admitted.

Request payloads must remain admitted-field-only. Provider URL fields, destination ids, connector ids, package mutation fields, source-widening fields, and qualitative execution fields must be rejected or ignored fail-closed according to the implementation contract.

## Security And Operational Requirements

The durable implementation specifies:

- token TTL and maximum retention;
- token hashing and log-redaction rules;
- secret/key rotation behavior;
- whether tokens survive process restart and multi-worker deployment;
- cleanup job or retention process ownership remains deferred, but the table family is indexed by state/expiry for a later cleanup lane;
- audit log retention and operator inspection limits;
- idempotency key requirements for generate, use, revoke, and receipt reads;
- concurrency rules for simultaneous use/revoke/expiry transitions;
- failure behavior if receipt or audit persistence fails after authority passes.

## Testing Requirements

Required tests for this implementation:

- migration/model tests for every new or changed table/model/index;
- focused API tests for every state transition and failure code;
- authority-chain tests proving stale or mismatched associated-cohort delivery state fails closed;
- security tests proving raw tokens are not persisted or logged by normal response paths;
- idempotency and concurrency tests for generate/use/revoke;
- compatibility tests for PR `#499` HMAC behavior, with replay deliberately superseded by durable single-use state;
- negative tests proving provider/public URL, connector/destination, package mutation, source widening, and qualitative execution remain unavailable.

Browser tests are required only when a later lane changes rendered UI. If UI changes are admitted, both headed and headless Chrome proof are required.

## Implementation Entry Conditions

Implementation entry has been admitted for only these surfaces:

- `backend/app/models/models.py`
- `backend/alembic/versions/0016_layer3_signed_reference_state.py`
- `backend/app/services/layer3_signed_reference_state.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_api.py`

Do not broaden beyond those surfaces without a refreshed freeze. Provider/public URL, connector/destination, qualitative execution, package mutation, source widening, and rendered revoke/copy/share UI remain deferred.
