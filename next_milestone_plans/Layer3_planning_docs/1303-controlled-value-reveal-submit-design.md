# 1303 - SEC XBRL Controlled Value-Reveal Submit Design

Milestone: `sec_xbrl_controlled_value_reveal_submit_v1`

Base authority: `project6-origin/main` at `0ce24f713fd3453e97810d56cfdad4d0176abbed`

Merged authority: `project6-origin/main` at `ddcab8771ebecfdd33b78a077bc461a37edc7d90`

Prior milestone: `next_milestone_plans/Layer3_planning_docs/1302-value-reveal-authority-receipt.md`

## Status

Merged current-main Tier-2 design/pre-review entry. This pass changes no runtime,
schema, persistence, API contract, rendered UI, default-on behavior, source
acquisition, Arelle invocation, delivery/export, raw artifact, or production
readiness surface.

## Design Decision

The next implementation should add a controlled SEC XBRL reveal-submit surface
that consumes the `sec_xbrl_value_reveal_authority_receipt_v1` receipt from
1302. The browser must not provide raw sidecar receipt IDs, sidecar hashes,
dataset hashes, value-store hashes, local paths, accessions, CIKs, or source
artifact authority.

The existing legacy service
`backend/app/services/layer3_sec_edgar_arelle_value_reveal.py` proves there is a
working value-store reveal primitive, but its public request admits
client-supplied `sidecar_receipt_id`, `sidecar_receipt_hash`,
`dataset_version_id`, and `dataset_version_hash`. The SEC XBRL submit path must
not expose that authority shape. It should either factor an internal helper from
the legacy service or implement a SEC XBRL owner service that reconstructs all
value-store authority from the approved authority receipt.

## Future API Boundary

Future route:

`POST /api/v1/layer3/sec-xbrl/value-reveal/submit`

Admitted request fields:

- `client_request_id`;
- `submit_mode=sec_xbrl_controlled_value_reveal_submit_v1`;
- `operator_decision=submit_explicit_sec_xbrl_value_reveal_from_authority_receipt`;
- `sec_xbrl_value_reveal_authority_receipt_id`;
- `authority_basis_hash`;
- `operator_reveal_confirmation=true`;
- optional `max_records`, with a server-owned hard cap;
- optional `page_cursor`, if pagination is implemented in the first runtime
  slice.

The request must reject raw sidecar, dataset, path, URL, accession, CIK, ticker,
contact, local storage, source acquisition, Arelle, delivery/export, UI, or
default-on fields.

## Server-Side Authority Resolution

The future owner service must:

1. Load the authority receipt by id and authority basis hash.
2. Revalidate authority state, policy id, redaction policy, and immutable
   decision/workflow/packet/projection/dataset/sidecar/value-store lineage.
3. Re-run the existing operator-review decision status projection and require
   the decision to remain approved with `ready_for_next_freeze`.
4. Require zero workflow, packet, and packet-row review exceptions.
5. Require all persisted projection facts and packet rows to remain
   value-redacted before reveal.
6. Resolve the sidecar receipt and internal value store from server-owned
   projection/authority hashes; never from browser-supplied sidecar inputs.
7. Produce transient reveal records only after response redaction and identity
   checks pass.

## Persistence And Containment

The implementation should add, or explicitly justify not adding, a durable SEC
XBRL reveal-submit audit receipt. If added, the receipt must persist only hashes,
counts, receipt ids, policy/state, pagination facts, and inventory hashes. It
must not persist raw values, raw identity values, raw sidecar receipt IDs, local
paths, accessions, CIKs, operator contacts, SEC URLs, or delivery locations.

Returned values are allowed only in the transient submit response and only for
facts that pass identity-value redaction. The status endpoint for any reveal
receipt must remain hash/count-only and must not replay raw values.

Rollback/containment requirements for the implementation:

- additive migration only if a new table is introduced;
- downgrade drops only the new reveal-submit receipt table/indexes;
- failed lineage, redaction, value-store, or receipt-write checks create no
  partial reveal-submit receipt;
- idempotent replay by the same basis returns the same receipt metadata;
- conflicting client request or authority basis fails closed;
- feature flag remains default-off and default-on admission stays a separate
  milestone.

## Tier Mapping

Future Tier-2 implementation surfaces:

- value-reveal handling;
- backend API route;
- owner service;
- optional additive audit-receipt model/migration;
- focused tests proving authority, redaction, idempotency, and fail-closed
  behavior.

Surfaces that remain out of scope:

- rendered value UI;
- default-on behavior;
- source acquisition;
- live SEC network;
- Arelle subprocess invocation;
- delivery/export;
- provider/public URL or connector dispatch;
- raw runtime artifact commits;
- production-readiness or financial-statement semantics claims.

## Validation Plan

Required implementation tests:

- authority receipt required and client-supplied sidecar/dataset authority
  rejected;
- non-approved, stale, mismatched, missing, or tampered authority receipt fails
  closed;
- missing sidecar or internal value store fails closed with no partial receipt;
- identity-like values remain redacted in transient response;
- status endpoint is hash/count-only;
- feature flag default-off blocks submit and status;
- default-on, source acquisition, Arelle, rendered UI, and delivery/export flags
  remain false;
- idempotent replay and conflicting request behavior are covered.

Required verification commands:

- `python -m py_compile` on touched Python files;
- focused SEC XBRL value-reveal/operator-review tests;
- full `backend/tests/test_sec_xbrl*.py` suite;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- JSON/proof-manifest validation with `utf-8-sig`;
- committed SEC XBRL report redaction scan;
- residual-magnitude scan;
- `git diff --check`.

## Independent Review Checklist

Ask an independent reviewer to focus on:

- whether reveal-submit is fully authority-receipt bound;
- whether raw sidecar receipt IDs are only transient and server-derived;
- whether any value, identity, accession, path, or contact can persist outside
  the transient response;
- whether status surfaces are hash/count-only;
- whether pagination/capping is deterministic and non-lossy;
- whether default-off and no-delivery/export boundaries are preserved;
- whether rollback/containment is sufficient for any schema change.

## Next Posture

After this design is reviewed and current-main verification remains clean, the
next bounded runtime slice is
`sec_xbrl_controlled_value_reveal_submit_v1_tier2_risk_assessed_implementation`.
That implementation must not add rendered value UI or default-on admission.
