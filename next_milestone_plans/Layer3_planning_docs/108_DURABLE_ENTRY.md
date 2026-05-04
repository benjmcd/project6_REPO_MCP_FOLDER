# Layer 3 Durable Signed-Reference Implementation Entry Freeze

## Status

Branch-local planning/control freeze for the first possible durable signed-reference implementation lane after current-main PR `#516`.

This file does not implement durable behavior. It converts the open questions in docs `106`/`107` into an implementation-entry contract that a later code lane must satisfy before changing runtime behavior.

## Canonical Authority

Use this authority order:

1. current `project6-origin/main` at branch base `3e3141902b45ef1d27d2d768e0b52440fd468814`;
2. PR `#499` stateless same-origin signed-reference backend/API behavior in `backend/app/services/layer3_workbench.py` and `backend/app/api/layer3.py`;
3. PR `#514` rendered same-origin signed-reference UI behavior in `/review/layer3`;
4. current-main docs `106_DURABLE_FREEZE.md` and `107_DURABLE_CONTRACT.md`;
5. this entry freeze and `109_DURABLE_STATE.md`.

If `project6-origin/main` gains another Alembic migration, Layer 3 model change, or signed-reference API change before implementation begins, stop and refresh this entry freeze before coding.

## Entry Decision

The next implementation slice, if admitted later, should be durable same-origin signed-reference state only.

It should preserve the existing PR `#499` endpoints:

- `POST /api/v1/layer3/handoff/export/download/signed-reference/generate`
- `POST /api/v1/layer3/handoff/export/download/signed-reference/use`

It should add durable backing state behind those endpoints rather than introduce provider/public URLs or connector/destination behavior.

The live PR `#499` stateless HMAC token remains the compatibility baseline. A later implementation may wrap it with durable state, but must not silently remove the existing authority checks, fail-closed missing-secret behavior, 300-second default TTL posture, same-origin delivery basis, or forbidden downstream fields.

## Future Runtime Write Set

A later implementation may touch only these code surfaces unless a refreshed freeze admits more:

- `backend/app/models/models.py`
- `backend/alembic/versions/0016_layer3_signed_reference_state.py`
- `backend/app/services/layer3_signed_reference_state.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_signed_reference_state.py`
- `backend/tests/test_layer3_api.py`

`0016_layer3_signed_reference_state.py` is the selected migration filename for this branch base because current `backend/alembic/versions` ends at `0015_layer3_package_entry.py`. If that is no longer true at implementation start, the migration filename must be renumbered and this freeze must be updated before code changes.

## Future State Tables

The future implementation should use a bounded table family rather than hiding durable state inside `L3Session.summary_json` or `L3ReconciliationRecord.summary_json`.

Selected table names:

- `l3_signed_reference_token`
- `l3_signed_reference_receipt`
- `l3_signed_reference_revocation`
- `l3_signed_reference_audit_event`

The table family must remain control-plane state. It must not write to runtime snapshot DBs and must not mutate source, package, APS evidence-bundle, or delivery artifact bytes.

## Future Service Boundary

Durable token lifecycle logic should live in `backend/app/services/layer3_signed_reference_state.py`.

`backend/app/services/layer3_workbench.py` should remain the authority-chain integration point only:

- validate the existing PR `#499` delivery authority;
- call the durable service to create or read token state;
- call the durable service to record receipt, revocation, and audit events;
- continue streaming through the existing same-origin delivery path.

This split is required to avoid adding another large state machine directly into `layer3_workbench.py` and to keep the durable lifecycle independently testable.

## Required Implementation Semantics

The later implementation must:

- store only token hashes or opaque lookup handles, never raw bearer tokens;
- bind token state to the existing associated-cohort delivery authority hash;
- preserve current authority revalidation at generation and use;
- fail closed if durable state is missing, expired, revoked, malformed, stale, or inconsistent;
- define whether `used` is terminal before writing code;
- record receipt rows for admitted generation and use outcomes;
- record audit rows for generate, use, deny, expire, revoke, and replay-deny outcomes;
- make revocation server-authoritative and idempotent;
- keep provider/public URL fields, connector/destination fields, package mutation fields, source-widening fields, and qualitative execution fields unavailable.

## Required Tests

A later implementation must include focused tests for:

- Alembic upgrade and model metadata creation for the new table family;
- token generation creates one durable token record and does not persist the raw bearer token;
- repeated generation with the same idempotency basis either reuses the same durable token or returns the specified idempotent result;
- token use revalidates current PR `#499` delivery authority;
- expired, revoked, malformed, missing-state, stale-authority, and replay-denied tokens fail closed;
- receipt rows are immutable and response-safe;
- audit rows are append-only and contain no raw token;
- revocation is idempotent and takes precedence over replay;
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
