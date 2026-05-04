# Layer 3 Durable Signed-Reference Implementation Entry Freeze

## Status

Implementation-entry freeze for the first durable signed-reference runtime lane after current-main PR `#516`, PR `#518`, PR `#519`, and landed runtime PR `#520`.

This file constrained branch `codex/l3-durable-runtime-p23`, which landed as PR `#520`. The admitted runtime remains only same-origin durable token/receipt/revocation/audit backing state behind the existing signed-reference endpoints.

## Canonical Authority

Use this authority order:

1. current `project6-origin/main` at PR `#520` merge commit `721b892b88ef88bf1364e2c71f762fabccdeb171`;
2. PR `#499` stateless same-origin signed-reference backend/API behavior in `backend/app/services/layer3_workbench.py` and `backend/app/api/layer3.py`;
3. PR `#514` rendered same-origin signed-reference UI behavior in `/review/layer3`;
4. current-main docs `106_DURABLE_FREEZE.md` and `107_DURABLE_CONTRACT.md`;
5. this entry freeze and `109_DURABLE_STATE.md`.

After PR `#520`, if a later branch needs another Alembic migration, Layer 3 model change, or signed-reference API change, stop and create a fresh freeze before continuing.

## Entry Decision

The admitted implementation slice is durable same-origin signed-reference state only.

It preserves the existing PR `#499` endpoints:

- `POST /api/v1/layer3/handoff/export/download/signed-reference/generate`
- `POST /api/v1/layer3/handoff/export/download/signed-reference/use`

It adds durable backing state behind those endpoints rather than introduce provider/public URLs or connector/destination behavior.

The live PR `#499` stateless HMAC token remains the compatibility baseline. This lane wraps it with durable state and must not silently remove the existing authority checks, fail-closed missing-secret behavior, 300-second default TTL posture, same-origin delivery basis, or forbidden downstream fields. Replay behavior is intentionally tightened from stateless reuse to durable `single_use`.

## Runtime Write Set

This implementation may touch only these code surfaces unless a refreshed freeze admits more:

- `backend/app/models/models.py`
- `backend/alembic/versions/0016_layer3_signed_reference_state.py`
- `backend/app/services/layer3_signed_reference_state.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_api.py`

`0016_layer3_signed_reference_state.py` was the selected migration filename because branch base `5896b9b5910d61ff94b27ff0c142b35319dd5fa1` had `backend/alembic/versions` ending at `0015_layer3_package_entry.py`; PR `#520` landed that migration. A later migration must use the next available revision in a fresh freeze.

## State Tables

The implementation uses a bounded table family rather than hiding durable state inside `L3Session.summary_json` or `L3ReconciliationRecord.summary_json`.

Selected table names:

- `l3_signed_reference_token`
- `l3_signed_reference_receipt`
- `l3_signed_reference_revocation`
- `l3_signed_reference_audit_event`

The table family must remain control-plane state. It must not write to runtime snapshot DBs and must not mutate source, package, APS evidence-bundle, or delivery artifact bytes.

## Service Boundary

Durable token lifecycle logic should live in `backend/app/services/layer3_signed_reference_state.py`.

`backend/app/services/layer3_workbench.py` should remain the authority-chain integration point only:

- validate the existing PR `#499` delivery authority;
- call the durable service to create or read token state;
- call the durable service to record receipt, revocation, and audit events;
- continue streaming through the existing same-origin delivery path.

This split is required to avoid adding another large state machine directly into `layer3_workbench.py` and to keep the durable lifecycle independently testable.

## Required Implementation Semantics

The implementation must:

- store only token hashes or opaque lookup handles, never raw bearer tokens;
- bind token state to the existing associated-cohort delivery authority hash;
- preserve current authority revalidation at generation and use;
- fail closed if durable state is missing, expired, revoked, malformed, stale, or inconsistent;
- define `used` as terminal for this first runtime slice;
- record receipt rows for admitted generation and use outcomes;
- record audit rows for generate, use, deny, expire, revoke, and replay-deny outcomes;
- include revocation table/service awareness, but no public/API/UI revocation endpoint;
- keep provider/public URL fields, connector/destination fields, package mutation fields, source-widening fields, and qualitative execution fields unavailable.

## Required Tests

The implementation must include focused tests for:

- Alembic upgrade and model metadata creation for the new table family;
- token generation creates one durable token record and does not persist the raw bearer token;
- repeated generation in the same HMAC TTL bucket reuses the same raw token and durable token record while adding response-safe receipts/audits;
- token use revalidates current PR `#499` delivery authority;
- expired, revoked, malformed, missing-state, stale-authority, and replay-denied tokens fail closed;
- receipt rows are immutable and response-safe;
- audit rows are append-only and contain no raw token;
- revocation table semantics do not expose a public/API/UI revoke surface in this slice;
- provider/public URL, connector/destination, package mutation, source widening, and qualitative fields remain rejected or ignored fail-closed according to the API contract;
- validate-only actions remain validate-only and do not seed durable state.

Browser tests are not required for this entry contract. Headed and headless Chrome become required only if a later implementation changes rendered `/review/layer3`.

## Stop Conditions

Stop before implementation if the intended change needs:

- provider/public URL generation or object-store ACL behavior;
- connector/destination dispatch or connector-run lifecycle state;
- rendered copy/share/refresh/revoke UI behavior;
- source ingestion expansion, non-PDF execution expansion, or qualitative APS content document execution;
- package payload mutation, package reconstruction, or APS artifact byte mutation;
- runtime snapshot DB writes;
- a migration filename that conflicts with current `project6-origin/main`;
- changing PR `#499` stateless semantics without explicit compatibility and rollback coverage.
