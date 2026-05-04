# Layer 3 Durable Signed-Reference State Freeze

## Status

Current-main freeze for durable token, receipt, revocation, and audit state after PR `#499` backend/API same-origin signed-reference generation/use, PR `#514` rendered same-origin signed-reference UI, PR `#516` durable-state planning/control merge, PR `#518`/PR `#519` implementation-entry planning/docs sync, and PR `#520` durable runtime implementation.

This file remains the durable-state freeze. PR `#520` implements only the bounded same-origin durable backing state selected by docs `108`/`109`: token hash state, generation/use receipts, revocation table support without a public endpoint, and audit rows.

Docs `108_DURABLE_ENTRY.md` and `109_DURABLE_STATE.md` are now the current implementation-entry contract for this runtime lane. They do not admit provider/public URLs, connector/destination dispatch, qualitative execution, package mutation, source widening, or rendered revoke/copy/share UI behavior.

## Current Authority

Use this authority order:

1. current `project6-origin/main` source/tests at PR `#520` merge commit `721b892b88ef88bf1364e2c71f762fabccdeb171`;
2. PR `#499` stateless HMAC signed-reference backend/API behavior;
3. PR `#514` rendered same-origin signed-reference UI behavior;
4. docs `102`/`103` signed-reference governance;
5. docs `104`/`105` signed-reference UI and deferred-gate governance;
6. this freeze, `107_DURABLE_CONTRACT.md`, `108_DURABLE_ENTRY.md`, and `109_DURABLE_STATE.md` for the durable-state implementation boundary.

Current main after PR `#520` remains short-lived, server-owned, same-origin, and revalidated at generation/use, but now has durable single-use state behind the same endpoints. PR `#520` intentionally supersedes only the stateless replay posture. Provider/public URL, connector, destination, package mutation, source-widening, and qualitative execution semantics remain unavailable.

## Admitted Planning Scope

This freeze admits only the bounded durable signed-reference state layer:

- token persistence and replay policy;
- receipt creation and receipt identity;
- revocation state and revocation authority;
- audit event schema and event retention;
- token/receipt binding to the existing associated-cohort delivery authority chain;
- idempotency and concurrency behavior;
- migration/model/table requirements, if any;
- compatibility rules for wrapping PR `#499` HMAC tokens with durable single-use state while preserving the HMAC envelope, missing-secret failure, TTL, and authority revalidation.

## Non-Goals

This lane must not implement or imply:

- public/provider signed URLs or object-store ACL behavior;
- connector dispatch, destination selection, generic downstream dispatch, or connector-run lifecycle state;
- qualitative APS content document execution;
- package mutation, package reconstruction, or new package artifact families;
- source ingestion, non-PDF ingestion, runtime source widening, or schema/runtime widening beyond a separately admitted durable-state model/migration lane;
- rendered UI controls beyond already-live PR `#514` same-origin signed-reference controls;
- token copy/share/refresh/revoke UI behavior;
- runtime writes outside the named durable control-plane table family.

## Required Decisions For This Implementation

The implementation lane must continue to honor these answered decisions:

- signed references remain HMAC bearer tokens, but raw tokens are never persisted;
- token lookup uses the token hash and response-safe token prefix;
- `used` is terminal for this first runtime slice with `single_use`, `max_use_count=1`;
- generation and accepted use create receipts and audit events;
- revocation has table/service awareness but no public/API/UI endpoint in this slice;
- audit persistence failure fails closed for durable generation/use;
- missing secret, malformed token, expired token, stale authority, missing durable state, revoked token, and replay conflict fail closed;
- public/provider URLs, connector/destination dispatch, package mutation, source widening, and qualitative execution remain unavailable.

## Proof Requirements For This Implementation

The implementation proof must include, at minimum:

- model/migration tests if a table or schema changes;
- backend/API tests for generation, use, replay, expiry, revocation, stale authority, missing secret, malformed token, and receipt/audit creation;
- tests proving PR `#499` HMAC validation is preserved while replay behavior is intentionally superseded by durable single-use state;
- tests proving no provider/public URL or connector/destination dispatch appears as a side effect;
- tests proving empty or isolated runtime state fails closed and validate-only actions do not seed or generate artifacts;
- `npm run validate:structure` and `git diff --check`;
- headed and headless browser proof only if UI surfaces change.

## Stop Conditions

Stop and return to planning if implementation would require:

- provider credentials, external object-store ACL changes, or public URL generation;
- connector credentials, destination registry, connector-run state, or downstream dispatch;
- qualitative execution engine ownership or qualitative result schema decisions;
- schema/model/migration changes not explicitly named in the durable-state contract;
- changing PR `#499` signed-reference API behavior without a compatibility and security decision;
- changing PR `#514` rendered UI behavior without a separate rendered durable-state UI freeze.
