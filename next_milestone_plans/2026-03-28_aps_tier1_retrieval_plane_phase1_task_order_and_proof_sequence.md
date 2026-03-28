# APS Tier1 Retrieval Plane Phase 1 Task Order And Proof Sequence

## Status

Planning only. This is the final ultra-narrow execution-order artifact for the bounded Phase 1 retrieval-plane slice.

This document does not widen scope beyond:

- `2026-03-27_aps_tier1_retrieval_plane_phase1_execution_spec.md`
- `2026-03-27_aps_tier1_retrieval_plane_phase1_migration_test_inventory_spec.md`

It exists to remove remaining ambiguity about:

- exact file-by-file implementation order
- exact proof order
- exact stop conditions between steps

## Governing Constraints

The implementation order below must remain aligned with these repo-confirmed facts:

1. Canonical evidence truth remains:
   - `backend/app/models/models.py` APS content tables
   - `backend/app/services/nrc_aps_content_index.py` canonical serializer/list/search semantics

2. Public default read behavior must remain unchanged in Phase 1.

3. Retrieval-plane build must remain separate from validate-only parity.

4. PostgreSQL lexical acceleration is allowed only as candidate pruning; current search ranking/pagination semantics remain authoritative.

5. SQLite head-upgrade and SQLite-shaped Tier2/Tier3 lanes must remain viable.

6. Upper analytical artifacts remain frozen and must not be widened.

7. New Python files must preserve canonical `app.*` imports and keep `tests/test_import_guardrail.py` green.

## Files In Scope

### New files

1. `backend/alembic/versions/0011_aps_retrieval_plane_v1.py`
2. `backend/app/services/nrc_aps_retrieval_plane.py`
3. `backend/app/services/nrc_aps_retrieval_plane_gate.py`
4. `tools/nrc_aps_retrieval_plane_shadow_build.py`
5. `tools/nrc_aps_retrieval_plane_gate.py`
6. `tests/test_nrc_aps_retrieval_plane.py`
7. `tests/test_nrc_aps_retrieval_plane_gate.py`

### Existing files to modify

1. `backend/app/models/models.py`
2. `backend/app/models/__init__.py`
3. `project6.ps1`
4. `README.md`

### Conditional touch files only if strictly needed

1. `backend/migration_compat.py`
2. `backend/alembic/env.py`
3. `backend/app/db/session.py`
4. `backend/app/services/nrc_aps_content_index.py`
5. `tests/test_api.py`

### No-touch files for this slice

- `backend/app/schemas/api.py`
- `backend/app/api/router.py`
- `backend/app/services/nrc_aps_evidence_bundle.py`
- `backend/app/services/nrc_aps_evidence_bundle_contract.py`
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/core/config.py`
- `backend/app/services/nrc_aps_sync_drift.py`
- `tools/run_nrc_aps_document_processing_proof.py`

## Ordered Task List

The implementation must proceed in the order below. Do not skip ahead.

### Step 0: Pre-edit audit checkpoint

Files read only:

- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `docs/postgres/postgres_status_handoff.md`
- `backend/app/models/models.py`
- `backend/app/models/__init__.py`
- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/nrc_aps_content_index_gate.py`
- `project6.ps1`
- `backend/migration_compat.py`
- `backend/alembic/env.py`

Required outcome:

- confirm the slice is still additive, lower-layer, shadow-first
- confirm no intervening repo change has already opened a broader lane
- confirm the no-touch set is still correct

Stop condition:

- if any live authority surface now says public reads, Evidence Bundle authority, or runtime-default behavior already changed, stop and re-plan before editing

### Step 1: Add the migration

Edit file:

- `backend/alembic/versions/0011_aps_retrieval_plane_v1.py`

Required content:

- create retrieval-plane table
- create cross-dialect-safe columns
- create uniqueness and btree indexes
- add PostgreSQL-only lexical acceleration
- keep dialect guards local unless impossible
- do not backfill data
- do not cut over reads

Must not:

- require literal `tsvector` support in SQLite
- alter canonical APS content tables
- alter upper-layer tables

Immediate proof after Step 1:

1. migration file imports cleanly
2. migration structure is coherent against `backend/migration_compat.py`
3. no other file has been edited yet

Stop condition:

- if migration requires widening `backend/migration_compat.py`, `backend/alembic/env.py`, or `backend/app/db/session.py`, document why and only then proceed to the narrowest necessary change

### Step 2: Add the ORM model

Edit file:

- `backend/app/models/models.py`

Required content:

- add retrieval-plane ORM model only
- use cross-dialect-safe field types
- keep SQLite `Base.metadata.create_all()` viable
- represent derived retrieval state only

Must not:

- introduce PostgreSQL-only ORM types that break SQLite import/create_all
- modify existing APS canonical model semantics

Immediate proof after Step 2:

1. `backend/app/models/models.py` imports successfully
2. ORM metadata can be created in SQLite without type failure

Stop condition:

- if ORM type choice forces `backend/app/db/session.py` or `backend/alembic/env.py` changes, stop and justify the exact reason before proceeding

### Step 3: Export the ORM model

Edit file:

- `backend/app/models/__init__.py`

Required content:

- export the new retrieval-plane ORM model if the new service/gate/test files will use package-level `app.models` imports

Immediate proof after Step 3:

1. canonical `app.models` import path resolves
2. `tests/test_import_guardrail.py` assumptions remain satisfiable

Stop condition:

- if export is not needed because every new file imports directly from `app.models.models`, leave this file untouched and document why in the implementation notes

### Step 4: Implement retrieval-plane service

Add file:

- `backend/app/services/nrc_aps_retrieval_plane.py`

Required content:

- canonical APS join query
- serializer reuse from current canonical semantics
- source signature build
- scoped rebuild/upsert logic
- stale-row reconciliation in-scope only
- retrieval-backed list/search helpers
- current lexical ranking preservation

Must not:

- repoint public routes
- change canonical content-index semantics
- alter Evidence Bundle source authority
- replace ranking with `ts_rank`
- auto-build retrieval rows during canonical writes

Immediate proof after Step 4:

1. file imports cleanly with canonical `app.*` imports only
2. serializer reuse preserves linkage-only diagnostics authority
3. no route or schema files have been touched

Stop condition:

- if exact serializer reuse is impossible without changing `backend/app/services/nrc_aps_content_index.py`, stop and perform the narrowest shared-helper extraction only

### Step 5: Add retrieval-plane service tests

Add file:

- `tests/test_nrc_aps_retrieval_plane.py`

Required coverage:

- signature stability
- no-op upsert on unchanged source
- update on changed source
- stale-row reconciliation
- run-scope and target-scope behavior
- explicit failure on unbounded build scope
- list ordering parity
- search token parity
- ranking parity
- pagination-after-ranking parity
- linkage-only diagnostics parity

Immediate proof after Step 5:

1. new retrieval-plane service tests pass
2. `tests/test_import_guardrail.py` still passes

Stop condition:

- if the new tests expose a mismatch between retrieval implementation and current canonical semantics, fix the service before adding any gate or operator surface

### Step 6: Add the shadow-build tool

Add file:

- `tools/nrc_aps_retrieval_plane_shadow_build.py`

Required content:

- explicit non-validate build wrapper
- bounded-scope requirement
- fail-closed when no bounded scope is supplied

Must not:

- validate parity
- write validation reports
- run implicitly from migration or canonical write paths

Immediate proof after Step 6:

1. tool imports cleanly
2. tool rejects unbounded invocation
3. tool can invoke bounded rebuild logic without changing public reads

Stop condition:

- if the tool needs `project6.ps1` wiring to be usable at all, note that as a narrow procedural change; otherwise keep shadow build as direct tool invocation in this slice

### Step 7: Implement retrieval-plane gate service

Add file:

- `backend/app/services/nrc_aps_retrieval_plane_gate.py`

Required content:

- validate-only parity logic
- fail-closed semantics on empty runtime by default
- deterministic JSON report generation
- exact mismatch classes
- candidate-run loading semantics compatible with current gate style

Must not:

- build retrieval rows
- seed runtime state
- refresh unrelated reports

Immediate proof after Step 7:

1. service imports cleanly
2. gate logic is strictly read/compare/report

Stop condition:

- if gate logic cannot stay validate-only without changing the retrieval service design, stop and correct the service boundary before proceeding

### Step 8: Add retrieval-plane gate tests

Add file:

- `tests/test_nrc_aps_retrieval_plane_gate.py`

Required coverage:

- fail closed on empty runtime
- fail on missing retrieval rows
- fail on orphan rows
- fail on field mismatch
- fail on diagnostics-authority mismatch
- pass on canonical/retrieval parity
- prove gate does not build retrieval rows as a side effect

Immediate proof after Step 8:

1. new gate tests pass
2. retrieval-plane service tests still pass

Stop condition:

- if gate tests require state-building inside the validator path, stop and correct the design; do not weaken validate-only semantics

### Step 9: Wire the validate-only operator action

Edit file:

- `project6.ps1`

Required changes only:

- add `validate-nrc-aps-retrieval-plane` to `ValidateSet`
- add one report path variable:
  - `tests/reports/nrc_aps_retrieval_plane_validation_report.json`
- add one tool-path variable
- add tool existence check
- invoke the gate under Tier2 isolated runtime semantics

Must not:

- add automatic shadow-build invocation
- repoint existing actions
- change existing validate/prove semantics

Immediate proof after Step 9:

1. `project6.ps1` parses successfully
2. new action is isolated and validate-only
3. existing actions remain textually untouched except for narrow insertion points

Stop condition:

- if wiring the action would require altering Tier2/Tier3 semantics or runtime-default logic, stop and re-plan

### Step 10: Run targeted existing non-regression tests

Execute targeted tests:

- `tests/test_import_guardrail.py`
- `tests/test_nrc_aps_content_index.py`
- `tests/test_nrc_aps_content_index_gate.py`
- `backend/tests/test_diagnostics_ref_persistence.py`
- `backend/tests/test_nrc_aps_evidence_bundle_integration.py`
- targeted APS retrieval/bundle assertions in `tests/test_api.py`

Required outcome:

- existing canonical lower-layer behavior remains intact
- no diagnostics-authority regression
- no evidence-bundle authority regression
- no import-path drift

Stop condition:

- if any existing canonical surface regresses, fix that before any migration proof or operator validation

### Step 11: Run migration proofs

Execute:

1. SQLite `alembic upgrade head`
2. PostgreSQL Tier1 `alembic upgrade head`

Required outcome:

- migration succeeds in both dialect lanes
- canonical APS content tables remain intact
- retrieval-plane migration remains bounded and additive

Stop condition:

- if SQLite head-upgrade fails, do not continue to parity validation
- if PostgreSQL head-upgrade succeeds but SQLite fails, the slice is not acceptable

### Step 12: Run SQLite metadata/create_all compatibility proof

Required proof:

- SQLite test/runtime lanes can still import models and create metadata

Reason:

- Tier2/Tier3 and many tests remain SQLite-shaped

Stop condition:

- if this fails, the ORM/migration design is still too PostgreSQL-specific and must be corrected before parity validation

### Step 13: Shadow-build bounded scope in PostgreSQL

Execute:

- explicit bounded-scope invocation of `tools/nrc_aps_retrieval_plane_shadow_build.py`

Required outcome:

- retrieval plane is built only for the requested bounded scope
- no public route cutover occurs

Stop condition:

- if shadow build requires unbounded scope or mutates canonical APS truth, stop and correct before validation

### Step 14: Run the new validate-only parity gate

Execute:

- `.\project6.ps1 -Action validate-nrc-aps-retrieval-plane`

Required outcome:

- validate-only parity report is generated
- gate passes on the intended isolated scope/runtime
- gate fails closed on empty runtime when appropriate
- gate does not build or seed retrieval rows

Stop condition:

- if parity validation depends on implicit build/seed behavior, stop and correct the operator boundary

### Step 15: Re-run existing validate-only lower-layer gates

Execute:

- `.\project6.ps1 -Action validate-nrc-aps-content-index`
- `.\project6.ps1 -Action validate-nrc-aps-evidence-bundle`

Required outcome:

- existing validate-only lower-layer gates still pass
- retrieval-plane slice has not disturbed canonical content-index or evidence-bundle validation

Stop condition:

- if either gate fails due to retrieval-plane changes, treat that as a regression in the bounded slice

### Step 16: Optional documentation update only after all proofs are green

Edit file only if implementation is accepted:

- `README.md`

Required content:

- add bounded documentation for the new validate-only retrieval-plane action

Must not:

- describe unimplemented cutover behavior
- imply public reads now use retrieval-plane data

Stop condition:

- if implementation is not yet accepted, leave `README.md` untouched

## Proof Sequence Summary

The proof sequence must occur in this exact order:

1. New retrieval-plane unit tests
2. New retrieval-plane gate tests
3. Existing canonical non-regression tests
4. SQLite head-upgrade proof
5. PostgreSQL head-upgrade proof
6. SQLite metadata/create_all proof
7. PostgreSQL bounded shadow-build proof
8. Validate-only retrieval-plane parity proof
9. Existing validate-only content-index proof
10. Existing validate-only evidence-bundle proof
11. Optional README update

Do not reorder this sequence.

## Minimum Acceptable Completion State

The slice is complete only if all of the following are true:

1. The retrieval-plane migration exists and is additive.
2. The ORM model exists and remains SQLite-compatible.
3. The retrieval service exists and preserves current canonical list/search semantics.
4. The shadow-build tool exists and is explicitly bounded and non-validate.
5. The validate-only parity gate exists and does not build/seed.
6. Existing canonical APS retrieval and Evidence Bundle behavior remains unchanged by default.
7. Existing lower-layer gates still pass.
8. No public route cutover occurred.
9. No upper analytical artifact surface was widened.

## Explicit Non-Goals During Implementation

The implementer must refuse any opportunistic additions in this slice, including:

- public route cutover
- route flags for retrieval-plane reads
- Evidence Bundle reads from retrieval plane
- semantic/vector retrieval
- runtime-default flip to PostgreSQL
- SQLite retirement
- automatic build during migration
- automatic build during canonical content-index upsert
- automatic build during validate-only gates
- full-scope rebuild as the default operator path

## Final Stop Rule

If any step requires touching a file outside the declared in-scope set, broadening a no-touch surface, or altering current canonical semantics rather than reproducing them, implementation must stop and return to planning mode before proceeding.
