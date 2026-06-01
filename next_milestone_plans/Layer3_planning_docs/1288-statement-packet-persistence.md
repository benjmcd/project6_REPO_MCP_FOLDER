# 1288 - SEC XBRL Statement Packet Persistence

Milestone:

`sec_xbrl_persisted_statement_packet_design_v1`

## Status

Planning-only Tier-2 risk-assessed design entry.

This document admits no runtime write path by itself. It does not add `models.py` rows,
Alembic migrations, persistence services, API/UI, operator workflow, value reveal,
default-on behavior, source acquisition, Arelle invocation, raw runtime artifacts, or
production-readiness claims.

## Authority

Canonical governance is `SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md`. This is a Tier-2
lane because the follow-on implementation would add durable statement-packet schema and
persistence. Tier-2 remains risk-assessed: exact touched surfaces, narrow tests, and
rollback or containment notes are required; independent review is sought when practical
or when a concrete risk trigger is present.

Current repo authority before this design:

- `1284-statement-packet.md` defines the redacted validate-only reviewable statement
  packet shape.
- `1286-projection-persistence.md` selected durable redacted projection authority as
  the required predecessor to persisted statement packets.
- `1287-projection-persist-impl.md` documents the landed projection persistence
  implementation and its rollback/containment proof.
- `backend/app/services/layer3_sec_xbrl_statement_assembly.py` emits
  `layer3.sec_xbrl_reviewable_statement_packet.v1`.
- `backend/app/services/layer3_sec_xbrl_projection_persistence.py` materializes
  redacted projection sets and facts that the packet implementation must consume.

## Selected First Persistence Slice

The first statement-packet implementation slice should persist an already-built
redacted statement packet derived from a persisted projection set. It should not
recompute projection facts, reveal values, or expose an operator workflow.

Admitted first-slice surfaces:

- `backend/app/models/models.py`: SEC XBRL statement-packet persistence ORM models only.
- `backend/alembic/versions/<next>_layer3_sec_xbrl_statement_packet_persistence.py`:
  additive tables and indexes only.
- A small service module that materializes statement-packet rows from an existing
  `L3SecXbrlProjectionSet` and the public statement-packet payload.
- Focused tests for schema, idempotency, rollback/containment, redaction, empty packet
  fail-closed behavior, projection-set binding, and no default-on behavior.

Not admitted in the first implementation slice:

- value reveal or persisted raw values;
- raw issuer identity, raw accessions, raw resolved fact authorities, raw period dates,
  local paths, SEC URLs, or operator contact fields;
- source acquisition, live SEC network, Arelle subprocess invocation, or taxonomy cache
  mutation;
- API/UI/operator workflow;
- persisted statement packet delivery/export;
- default-on behavior;
- production-readiness or final financial-statement semantics claims;
- linkbase emission, dimensional roll-forward handling, or filing-wide canonicalization.

## Proposed Durable Shape

Use three additive tables for the first implementation:

1. `l3_sec_xbrl_statement_packet_set`

   One row per deterministic statement-packet materialization request. The row is the
   idempotency, provenance, and review-readiness envelope.

   Required fields:

   - `sec_xbrl_statement_packet_set_id`: UUID primary key.
   - `sec_xbrl_projection_set_id`: foreign key to `l3_sec_xbrl_projection_set`.
   - `client_request_id`: idempotency key, unique.
   - `packet_basis_hash`: stable hash over the redacted packet input envelope, unique.
   - `packet_schema_id`: expected `layer3.sec_xbrl_reviewable_statement_packet.v1`.
   - `source_projection_basis_hash`: copied from the persisted projection set.
   - `source_projection_schema_id`: copied from the persisted projection set.
   - `statement_organization_authority`: public authority label from the packet.
   - `value_policy`: must equal `redacted_no_values`.
   - `statement_count`, `total_review_rows`, `provenance_complete_count`,
     `review_exception_count`.
   - `review_ready`: boolean copied from the redacted packet.
   - `identity_rollup_json`: counts/status only; no residual magnitudes in the first
     persistence slice.
   - `organization_contract_json`: public contract summary only.
   - `packet_summary_json`: counts and status summary only.
   - `status`: initially only `materialized`.
   - `created_at` and `updated_at`.

2. `l3_sec_xbrl_statement_packet_statement`

   One row per statement section in the packet.

   Required fields:

   - `sec_xbrl_statement_packet_statement_id`: UUID primary key.
   - `sec_xbrl_statement_packet_set_id`: foreign key to the packet set.
   - `statement`: `income`, `balance`, or `cashflow`.
   - `statement_index`: deterministic order.
   - `line_count`, `projected_count`, `derived_count`,
     `provenance_complete_count`, `review_exception_count`.
   - `status_counts_json` and `family_counts_json`: public count maps only.

3. `l3_sec_xbrl_statement_packet_row`

   One row per public packet row. The row must bind back to the persisted projection
   fact when possible and otherwise fail closed unless the implementation explicitly
   documents why a public row cannot be bound.

   Required fields:

   - `sec_xbrl_statement_packet_row_id`: UUID primary key.
   - `sec_xbrl_statement_packet_statement_id`: foreign key to the statement row.
   - `sec_xbrl_projection_fact_id`: foreign key to `l3_sec_xbrl_projection_fact`.
   - `statement`, `statement_row_index`, `source_index`.
   - `period_ref`, `period_index`.
   - `canonical_id`, `basis`, `requested_basis`, `family`, `source_qname`.
   - `status`, `oracle_confirmed`, `mapping_method`, `mapping_confidence`,
     `unit_class`.
   - `provenance_complete`: boolean copied from public row semantics.
   - `value_redacted`: must be true for all rows.
   - `review_exception`: derived boolean; true when provenance is incomplete or oracle
     state requires review.
   - `derived_from_concepts_json`: public concept ids only.

Do not store `_value`, `effective_value`, `amount`, raw `resolved_fact_id`, raw CIK,
raw accession, raw period dates, SEC URLs, local paths, raw sidecar/value-store payloads,
or identity residual magnitudes in these tables.

## Write Contract

The materializer must:

1. accept only a persisted `L3SecXbrlProjectionSet` plus an already-built redacted
   statement packet;
2. reject packets whose `schema_id` is not `layer3.sec_xbrl_reviewable_statement_packet.v1`;
3. reject empty packets or packets with zero review rows;
4. require `value_policy=redacted_no_values`;
5. require packet rows to match persisted projection facts by period, statement,
   statement row index, canonical id, basis, family, and source qname where present;
6. reject raw value fields, raw issuer identity keys, raw accessions, raw period dates,
   SEC URLs, local paths, raw resolved fact authorities, and residual magnitude fields;
7. compute `packet_basis_hash` from the redacted packet envelope and the persisted
   projection basis hash before writing;
8. be idempotent on `client_request_id` and `packet_basis_hash`;
9. write packet set, statement, and row records in one transaction;
10. roll back the whole transaction on any row-level validation failure.

The materializer must not call SEC network paths, invoke Arelle, acquire sources,
mutate taxonomy/cache state, reveal values, or emit route/UI/operator workflow state.

## Rollback And Containment

The schema migration must be additive. Downgrade drops only the new SEC XBRL statement
packet persistence tables and indexes in reverse dependency order.

Containment requirements for the implementation PR:

- Runtime default remains off.
- No route or UI reaches these tables in the first slice.
- Tests run in isolated temporary DB state.
- Failed materialization leaves no partial packet set, statement, or row records.
- Replaying the same request returns the existing packet materialization instead of
  duplicating rows.
- Projection persistence rows are read as authority inputs, not mutated.
- If downgrade is exercised after test data exists, only the new statement-packet
  persistence tables are removed.

If a later PR admits operator-visible writes, exports, delivery, or production retention,
rollback and retention controls must be revisited before that PR lands.

## Verification Required For First Implementation

Minimum local verification:

- focused statement-packet persistence model/service tests;
- migration upgrade/downgrade or project-standard equivalent migration proof;
- empty packet fail-closed test;
- raw value/raw identity/raw accession/raw period date/local path/SEC URL/residual
  magnitude rejection tests;
- projection-set and projection-fact binding tests;
- idempotent replay test for `client_request_id` and `packet_basis_hash`;
- partial-write rollback test;
- `python -m pytest ./backend/tests/test_sec_xbrl_statement_assembly.py -q`;
- `python -m pytest ./backend/tests/test_sec_xbrl_projection_persistence.py -q`;
- full `backend/tests/test_sec_xbrl*.py` suite;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- py_compile on touched Python files;
- JSON parse for changed manifests/reports;
- redaction scan across changed SEC XBRL committed reports or proof artifacts;
- `git diff --check`.

CI must be green before merge. Independent review is recommended because this is Tier-2
persistence work. Under the softened policy, merge is blocked by failed required checks,
unresolved critical/blocking findings, missing rollback or containment notes, unclear
authority, or an explicit operator instruction requiring review.

## Follow-On After Statement Packet Persistence

Only after persisted statement packets land and are verified should the project select a
governed operator-review workflow design lane.

That later workflow must name the exact route/UI/operator controls, redaction posture,
browser proof, authorization assumptions, and stop conditions. It must not reveal values,
change defaults, or claim production readiness without a separate freeze and proof.
