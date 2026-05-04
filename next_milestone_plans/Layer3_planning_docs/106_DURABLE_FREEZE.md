# Layer 3 Durable Signed-Reference State Freeze

## Status

Current-main planning/control freeze for durable token, receipt, revocation, and audit state after PR `#499` backend/API same-origin signed-reference generation/use, PR `#514` rendered same-origin signed-reference UI, and PR `#516` durable-state planning/control merge.

This file does not implement durable behavior. It selects the durable-state question as the next workbench planning slice because provider/public URLs and connector/destination dispatch both need a settled replay, revocation, receipt, and audit model before they can be exposed safely.

Branch-local docs `108_DURABLE_ENTRY.md` and `109_DURABLE_STATE.md` refine this freeze into a future implementation-entry contract. They do not implement durable behavior or change current-main PR `#499`/PR `#514` behavior.

## Current Authority

Use this authority order:

1. current `project6-origin/main` source/tests at the branch base;
2. PR `#499` stateless HMAC signed-reference backend/API behavior;
3. PR `#514` rendered same-origin signed-reference UI behavior;
4. docs `102`/`103` signed-reference governance;
5. docs `104`/`105` signed-reference UI and deferred-gate governance;
6. this freeze and `107_DURABLE_CONTRACT.md` for the next durable-state planning boundary.

The current live signed-reference behavior is stateless, short-lived, server-owned, same-origin, and revalidated at generation/use. It creates no rows/files and does not provide revocation, receipt, audit, one-time-use, persistence, public/provider URL, connector, or destination semantics.

## Admitted Planning Scope

This freeze admits planning only for a future durable signed-reference state layer:

- token persistence and replay policy;
- receipt creation and receipt identity;
- revocation state and revocation authority;
- audit event schema and event retention;
- token/receipt binding to the existing associated-cohort delivery authority chain;
- idempotency and concurrency behavior;
- migration/model/table requirements, if any;
- compatibility rules for preserving or superseding PR `#499` stateless HMAC behavior.

## Non-Goals

This lane must not implement or imply:

- public/provider signed URLs or object-store ACL behavior;
- connector dispatch, destination selection, generic downstream dispatch, or connector-run lifecycle state;
- qualitative APS content document execution;
- package mutation, package reconstruction, or new package artifact families;
- source ingestion, non-PDF ingestion, runtime source widening, or schema/runtime widening beyond a separately admitted durable-state model/migration lane;
- rendered UI controls beyond already-live PR `#514` same-origin signed-reference controls;
- token copy/share/refresh/revoke UI behavior;
- runtime writes before an implementation contract explicitly admits them.

## Required Decisions Before Implementation

A later implementation lane cannot begin until `107_DURABLE_CONTRACT.md` or a successor freeze answers:

- whether durable signed references are persisted bearer tokens, persisted opaque token ids, one-time-use references, replayable references, or revocable handles over PR `#499` stateless references;
- whether PR `#499` stateless HMAC tokens remain supported as the default path, are wrapped by persisted state, or are intentionally superseded;
- exact database table/model/migration surfaces and whether they belong to existing control-plane models or a new bounded table family;
- token uniqueness, token hashing, secret rotation, and token lookup behavior;
- receipt identity, receipt payload, response contract, and whether receipts are created at generation, use, delivery, or all three;
- revocation authority, revocation timing, idempotent revoke behavior, and revoked-token response semantics;
- audit event taxonomy, event payload constraints, retention, cleanup, and operator-visible surfaces;
- concurrency and idempotency rules for generate, use, revoke, and receipt reads;
- failure modes for missing secret, stale authority, expired token, revoked token, replay conflict, receipt mismatch, and audit persistence failure;
- security review expectations for bearer token leakage, token hashing, log redaction, response headers, and cross-worker/process stability.

## Proof Requirements For A Later Implementation

The later implementation proof must include, at minimum:

- model/migration tests if a table or schema changes;
- backend/API tests for generation, use, replay, expiry, revocation, stale authority, missing secret, malformed token, and receipt/audit creation;
- tests proving PR `#499` stateless behavior is preserved or intentionally superseded with explicit migration/compatibility coverage;
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
