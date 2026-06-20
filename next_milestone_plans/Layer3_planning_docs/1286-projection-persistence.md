# 1286 - SEC XBRL Projection Persistence

Milestone:

`sec_xbrl_projection_persistence_design_v1`

## Status

Planning-only Tier-2 risk-assessed design entry.

This document admits no runtime write path by itself. It does not add `models.py` rows,
Alembic migrations, persistence services, API/UI, operator workflow, value reveal,
default-on behavior, source acquisition, Arelle invocation, raw runtime artifacts, or
production-readiness claims.

## Authority

Canonical governance is `SEC-XBRL-MERGE-GATE-VERIFIER-POLICY.md`. This is a Tier-2
lane because durable schema and persistence are the next selected surface. Tier-2 is
risk-assessed under the softened policy: exact touched surfaces, narrow tests, and
rollback or containment notes are required; independent pre-merge review is sought when
practical or when a concrete risk trigger is present.

Current repo authority before this design:

- `1284-statement-packet.md` defines the redacted reviewable statement packet over
  canonical projection and statement organization authority.
- `1285-multi-period.md` defines validate-only multi-period projection and names this
  persistence lane as the next posture.
- `layer3_progress_manifest.json` marks real-filer sector-family validation satisfied
  by `sec_xbrl_sector_family_real_filer_validation_v1`.
- `layer3_sec_xbrl_canonical_concepts.py` emits canonical projection rows with
  provenance fields and private raw-value fields.
- `layer3_sec_xbrl_statement_assembly.py` consumes only public projection row shape and
  keeps values redacted in review packets.

## Selected First Persistence Slice

The first implementation slice should persist redacted canonical projection authority,
not raw fact values and not a review UI.

Admitted first-slice surfaces:

- `backend/app/models/models.py`: SEC XBRL projection persistence ORM models only.
- `backend/alembic/versions/<next>_layer3_sec_xbrl_projection_persistence.py`:
  additive tables and indexes only.
- A small service module for deterministic materialization from already-built canonical
  projection results.
- Focused tests for schema, idempotency, rollback/containment, redaction, empty-runtime
  fail-closed behavior, and no default-on behavior.

Not admitted in the first implementation slice:

- value reveal or persisted raw values;
- raw issuer identity, raw accession, raw resolved fact authorities, local paths, SEC
  URLs, or operator contact fields;
- source acquisition, live SEC network, Arelle subprocess invocation, or taxonomy cache
  mutation;
- API/UI/operator workflow;
- persisted statement packet tables;
- default-on behavior;
- production-readiness or final financial-statement semantics claims.

## Proposed Durable Shape

Use two additive tables for the first implementation:

1. `l3_sec_xbrl_projection_set`

   One row per deterministic projection materialization request. The row is the
   idempotency and provenance envelope.

   Required fields:

   - `sec_xbrl_projection_set_id`: UUID primary key.
   - `client_request_id`: idempotency key, unique.
   - `projection_basis_hash`: stable hash over the redacted projection input envelope,
     unique.
   - `projection_schema_id`: expected `layer3.sec_xbrl_projection_set.v1`.
   - `source_report_schema_id`: diagnostic/report schema that admitted the projection
     evidence.
   - `source_report_hash`: hash of the redacted report or local runtime evidence packet
     used for admission.
   - `dataset_version_id`: existing governed dataset-version reference when available.
   - `sidecar_receipt_hash`: governed sidecar receipt hash.
   - `value_store_hash`: governed value-store hash.
   - `sector_family_presence_json`: redacted public sector-family presence summary.
   - `period_refs_json`: redacted period refs only, not raw period dates.
   - `projection_summary_json`: counts and status summary only.
   - `redaction_policy`: must equal `redacted_no_values`.
   - `status`: initially only `materialized`.
   - `created_at` and `updated_at`.

2. `l3_sec_xbrl_projection_fact`

   One row per redacted canonical projection fact within a projection set. The row
   preserves reviewable semantics and provenance presence without storing values.

   Required fields:

   - `sec_xbrl_projection_fact_id`: UUID primary key.
   - `sec_xbrl_projection_set_id`: foreign key to the projection set.
   - `period_ref`: redacted period reference.
   - `period_index`: integer ordering from the multi-period wrapper.
   - `statement`: `income`, `balance`, or `cashflow`.
   - `statement_row_index`: deterministic ordering within statement and period.
   - `canonical_id`, `basis`, `requested_basis`, `family`, `source_qname`.
   - `status`, `oracle_confirmed`, `mapping_method`, `mapping_confidence`,
     `unit_class`.
   - `provenance_complete`: boolean copied from projection public row semantics.
   - `value_redacted`: must be true for all rows.
   - `resolved_fact_provenance_present`: boolean, not raw resolved fact id.
   - `sidecar_receipt_hash` and `value_store_hash`: repeated only when needed for row
     containment checks.
   - `derived_from_concepts_json`: public concept ids only.

Do not store `_value`, `effective_value`, `amount`, raw `resolved_fact_id`, raw CIK,
raw accession, raw period dates, SEC URLs, local paths, or raw sidecar/value-store
payloads in either table.

## Write Contract

The materializer must:

1. accept only already-built canonical projection output;
2. reject empty projection sets;
3. reject any row carrying raw value fields;
4. reject raw identity, accession, local path, or SEC URL strings in the persisted
   envelope;
5. require sidecar receipt hash, value-store hash, dataset-version reference when the
   projection claims those fields are present;
6. require every persisted fact row to have `value_redacted=true`;
7. compute `projection_basis_hash` from the redacted envelope before writing;
8. replay only when the same `client_request_id` resolves to the same
   `projection_basis_hash`; the same `projection_basis_hash` under a different
   `client_request_id` fails closed until a separate alias policy is frozen;
9. write projection set and fact rows in one transaction;
10. roll back the whole transaction on any row-level validation failure.

The materializer must not call SEC network paths, invoke Arelle, acquire sources,
mutate taxonomy/cache state, or reveal values.

## Rollback And Containment

The schema migration must be additive. Downgrade drops only the new SEC XBRL projection
persistence tables and indexes in reverse dependency order.

Containment requirements for the implementation PR:

- Runtime default remains off.
- No route or UI reaches these tables in the first slice.
- Tests run in isolated temporary DB state.
- Failed materialization leaves no partial projection set or fact rows.
- Replaying the same request returns the existing materialization instead of duplicating
  rows; same-basis/new-request replay fails closed rather than silently aliasing
  authority.
- If downgrade is exercised after test data exists, only the new projection persistence
  tables are removed.

If a later PR admits operator-visible writes or production retention, rollback must be
revisited before that PR lands. This design does not claim production data-retention
rollback.

## Verification Required For First Implementation

Minimum local verification:

- focused persistence model/service tests;
- migration upgrade/downgrade or project-standard equivalent migration proof;
- empty projection fail-closed test;
- raw value/raw identity/raw accession/local path/SEC URL rejection tests;
- exact-request replay and same-basis/new-request mismatch tests for
  `client_request_id` and `projection_basis_hash`;
- partial-write rollback test;
- `python ./tools/l3-target-selection-validate.py --expect frozen`;
- `python ./tools/l3-progress-check.py`;
- py_compile on touched Python files;
- JSON parse for changed manifests/reports;
- redaction scan across changed SEC XBRL committed reports or proof artifacts;
- `git diff --check`.

CI must be green before merge. Independent review is recommended because this is Tier-2
persistence work. Under the softened policy, merge is blocked by failing CI checks
(author-enforced; `main` has no branch-protection required-status-check gate),
unresolved critical/blocking findings, missing rollback or containment notes, unclear
authority, or an explicit operator instruction requiring review.

## Follow-On After Projection Persistence

Only after redacted projection persistence lands and is verified should the project
select `sec_xbrl_persisted_statement_packet_design_v1`.

That later packet lane should persist the already-redacted statement packet shape from
`layer3_sec_xbrl_statement_assembly.py`, not recompute values and not expose operator UI
until a separate route/UI freeze names exact controls and browser proof.
