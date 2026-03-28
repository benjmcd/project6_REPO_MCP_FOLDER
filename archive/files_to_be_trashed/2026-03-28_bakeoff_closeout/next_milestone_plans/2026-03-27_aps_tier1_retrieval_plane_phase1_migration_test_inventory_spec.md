# APS Tier1 Retrieval Plane Phase 1 Migration And Test Inventory Spec

## Status

Planning only. This document is a companion to `2026-03-27_aps_tier1_retrieval_plane_phase1_execution_spec.md`.

It exists to answer the remaining execution-grade questions that the Phase 1 execution spec intentionally left open:

- exactly which repo files belong to the slice
- which files must remain untouched
- which proof obligations are mandatory versus optional
- where tech debt can accumulate during implementation
- how the split PostgreSQL/SQLite repo model constrains the migration shape

This document is not authorization to modify live implementation files outside `next_milestone_plans`.

## Canonical Basis

This inventory is grounded in the live authority surfaces below. If this inventory conflicts with any of them, the live authority surfaces win.

- `docs/nrc_adams/nrc_aps_authority_matrix.md`
- `docs/nrc_adams/nrc_aps_reader_path.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `docs/postgres/postgres_status_handoff.md`
- `project6.ps1`
- `backend/migration_compat.py`
- `backend/alembic/env.py`
- `backend/app/db/session.py`
- `backend/app/models/__init__.py`
- `backend/app/models/models.py`
- `backend/app/schemas/api.py`
- `backend/app/api/router.py`
- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/nrc_aps_content_index_gate.py`
- `backend/app/services/nrc_aps_evidence_bundle.py`
- `backend/app/services/nrc_aps_sync_drift.py`
- `backend/alembic/versions/0008_aps_content_index_tables.py`
- `backend/alembic/versions/0009_aps_document_processing_metadata.py`
- `backend/alembic/versions/0010_visual_page_refs_json.py`
- `tests/test_import_guardrail.py`
- `tests/test_nrc_aps_content_index.py`
- `tests/test_nrc_aps_content_index_gate.py`
- `tests/test_api.py`
- `backend/tests/test_diagnostics_ref_persistence.py`
- `backend/tests/test_nrc_aps_evidence_bundle_integration.py`
- `README.md`

## Slice Identity

This is a bounded Phase 1 slice for a derived Tier1 PostgreSQL retrieval plane.

It is:

- additive
- shadow-first
- parity-validated
- default-cutover-deferred
- lower-layer only

It is not:

- a reopening of closed Phase 8 APS table materialization
- a widening of frozen upper analytical schemas
- a public API expansion slice
- a vector search slice
- a semantic extraction slice
- a runtime-default flip in `config.py`
- a SQLite retirement slice

## Current Live Facts This Slice Must Respect

1. Canonical evidence truth remains the APS content tables:
   - `aps_content_document`
   - `aps_content_chunk`
   - `aps_content_linkage`

2. Current public retrieval surfaces are still list/search through:
   - `GET /api/v1/connectors/runs/{connector_run_id}/content-units`
   - `POST /api/v1/connectors/nrc-adams-aps/content-search`

3. Current retrieval-visible row semantics are controlled by `_serialize_index_row()` and linkage-authoritative `_resolve_diagnostics_ref()` in `backend/app/services/nrc_aps_content_index.py`.

4. Tier1 operator default is PostgreSQL, but:
   - bare runtime default remains SQLite in `backend/app/core/config.py`
   - Tier2 and Tier3 remain intentionally SQLite-shaped
   - many validate/proof lanes still run against isolated SQLite runtime state through `project6.ps1`

5. Existing validate actions must remain:
   - validate-only
   - fail-closed on empty runtime
   - non-seeding

6. The frozen upper analytical ceiling remains closed through Deterministic Challenge Review Packet v1.

7. New Python files must preserve the canonical import discipline enforced by `tests/test_import_guardrail.py`.
   - use `app.*` imports
   - do not import `backend.app.*`

8. Current search semantics are an explicit contract, not an implementation detail.
   - query tokenization is controlled by `normalize_query_tokens()`
   - all-token containment is required
   - current result ordering and post-ranking pagination must be preserved unless a later slice explicitly changes them

## Implementation Strategy Summary

The implementation packet for this slice should create one derived retrieval plane and one validate-only parity lane without changing public default reads.

The minimum viable implementation should do all of the following and nothing broader:

1. Add the retrieval table migration for Phase 1.
2. Add the ORM model for the retrieval table.
3. Export the retrieval ORM model through `backend/app/models/__init__.py` if the implementation uses package-level `app.models` imports.
4. Add an internal retrieval-plane service for:
   - rebuild/upsert
   - scope reconciliation
   - retrieval-backed list
   - retrieval-backed search
   - parity validation
5. Add a separate explicit shadow-build tool surface that is not validate-only.
6. Add a validate-only retrieval-plane gate service and tool wrapper.
7. Add a `project6.ps1` action for the new validate-only retrieval-plane gate.
8. Add targeted tests for:
   - migration-safe table presence assumptions
   - rebuild logic
   - list/search parity semantics
   - gate fail-closed behavior
   - no-regression on existing content index and evidence bundle behavior

The minimum viable implementation should not:

- cut over existing public list/search routes by default
- replace APS canonical storage
- change Evidence Bundle source authority
- add semantic/vector fields
- add retrieval history/version tables
- add public operator/debug endpoints

## File Inventory

### A. New files expected in the slice

These are the narrowest expected new live files.

1. Alembic migration
   - expected isolated-lane filename pattern: `backend/alembic/versions/<next_free_revision>_aps_retrieval_plane_v1.py`
   - determine the next free Alembic revision at implementation time; do not hardcode `0011_...` if the chain moved

2. Retrieval-plane service
   - `backend/app/services/nrc_aps_retrieval_plane.py`

3. Retrieval-plane gate service
   - `backend/app/services/nrc_aps_retrieval_plane_gate.py`

4. Shadow-build tool wrapper
   - `tools/nrc_aps_retrieval_plane_shadow_build.py`

5. Tool wrapper
   - `tools/nrc_aps_retrieval_plane_gate.py`

6. Retrieval-plane service tests
   - `tests/test_nrc_aps_retrieval_plane.py`

7. Retrieval-plane gate tests
   - `tests/test_nrc_aps_retrieval_plane_gate.py`

### B. Existing files expected to be modified

These modifications are part of the slice and should be treated as required, not incidental.

1. `backend/app/models/models.py`
   - add the ORM model for the retrieval plane
   - do not modify the existing APS content-table contracts beyond what is necessary for coexistence

2. `backend/app/models/__init__.py`
   - export the retrieval-plane ORM model if package-level `app.models` imports are used anywhere in the slice

3. `project6.ps1`
   - add a new validate-only action for retrieval-plane parity
   - add explicit bounded-scope argument pass-through for that action
   - add narrow scope parameters `NrcApsRunId` and `NrcApsTargetId`
   - add the exact report-path variable
   - add report-path wiring
   - keep existing Tier2/Tier3 validate/proof semantics unchanged for existing actions
   - run the new retrieval-plane parity action against Tier1 PostgreSQL because the validated shadow plane lives there
   - do not repoint existing actions to the retrieval plane

4. `README.md`
   - update operator command documentation only if and when the new validate-only action is added
   - do not use README edits as substitute proof of implementation correctness

### C. Existing files that may be modified only if strictly needed

These files are conditional. Treat them as no-touch unless the narrow implementation requires them.

1. `backend/migration_compat.py`
   - default plan: no change
   - only widen if the migration cannot stay dialect-local without duplicative or unsafe logic
   - if widened, add the narrowest possible helper and no generalized abstraction layer

2. `backend/app/services/nrc_aps_content_index.py`
   - allowed for narrow shared-helper reuse only
   - do not convert existing public list/search functions to retrieval-plane reads in this slice
   - do not fork `_serialize_index_row()` semantics

3. `tests/test_api.py`
   - modify only if a strictly internal implementation detail requires refreshed route-level non-regression coverage
   - do not add new public API behavior assertions in this slice

4. `backend/alembic/env.py`
   - default plan: no change
   - only touch if the new migration cannot remain compatible with current Alembic environment behavior

5. `backend/app/db/session.py`
   - default plan: no change
   - only touch if ORM type selection would otherwise break the current cross-dialect engine/session setup

### D. Existing files that should remain untouched in this slice

These are explicit no-touch surfaces unless a defect is discovered that directly blocks the bounded slice.

- `backend/app/schemas/api.py`
- `backend/app/api/router.py`
- `backend/app/services/nrc_aps_evidence_bundle.py`
- `backend/app/services/nrc_aps_evidence_bundle_contract.py`
- all upper analytical artifact services, schemas, and gates
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/core/config.py`
- `backend/app/services/nrc_aps_sync_drift.py`
- `tools/run_nrc_aps_document_processing_proof.py`

Rationale:

- public API shape must stay unchanged by default
- Evidence Bundle must continue reading canonical APS content tables in Phase 1
- document-processing and hydrate behavior are below the retrieval-plane slice
- runtime-default semantics are explicitly deferred tech debt, not a Phase 1 retrieval task

## Migration Design Inventory

### Mandatory migration responsibilities

The migration must:

1. create the retrieval table described in the execution spec
2. create the uniqueness and lookup indexes required by the execution spec
3. remain safe inside the shared Alembic chain
4. not break SQLite `alembic upgrade head`
5. not assume PostgreSQL is the active dialect at migration runtime

### Dialect rules

The migration must separate cross-dialect structure from PostgreSQL-only search acceleration.

Required split:

- cross-dialect:
  - base table
  - base uniqueness/indexes that SQLite can tolerate
  - textual `search_text`
  - all provenance/ordering columns

- PostgreSQL-only:
  - lexical acceleration over `search_text`
  - GIN expression index over `to_tsvector('simple', search_text)` or a strictly equivalent strategy, but only if bounded PostgreSQL query-parity proof shows the prefilter is no-false-negative relative to current token semantics
  - any dialect-specific SQL needed to populate or maintain PostgreSQL lexical acceleration if expression indexing alone is insufficient

Implementation implication:

- do not assume the current helper set in `backend/migration_compat.py` is enough for PostgreSQL-only search-vector wiring
- prefer keeping dialect guards local to the new migration file
- only widen `backend/migration_compat.py` if the local migration would otherwise become incoherent
- do not force SQLite-shaped lanes to emulate a literal `tsvector` column or PostgreSQL-only type

### Naming and revision constraints

The new migration must:

- revise `0010_visual_page_refs_json.py`
- use a short revision/file name to avoid path-length debt
- keep table/index names short and deterministic

### Downgrade expectation

The migration should include a coherent downgrade for the retrieval-plane objects it creates, but downgrade completeness is secondary to:

- forward upgrade safety
- idempotent behavior inside the repo's mixed `create_all`/Alembic realities
- not damaging canonical APS tables

## ORM / Service Design Inventory

### Retrieval ORM model responsibilities

The retrieval ORM model should:

- live in `backend/app/models/models.py`
- represent only derived retrieval state
- include explicit `retrieval_contract_id`
- include `source_signature_sha256`
- include rebuild timestamps
- include the retrieval-visible payload fields required by the execution spec
- stay compatible with SQLite `Base.metadata.create_all()` in test/runtime lanes

The model should not:

- replace APS canonical identifiers
- introduce semantic/vector fields beyond Phase 1 lexical needs
- encode historical retrieval versions
- introduce PostgreSQL-only ORM types that break SQLite import/create_all lanes

### Retrieval service responsibilities

`backend/app/services/nrc_aps_retrieval_plane.py` should contain the following bounded concerns:

1. canonical-source query
   - join `ApsContentLinkage`
   - join `ApsContentDocument`
   - join `ApsContentChunk`
   - preserve the existing join keys

2. canonical serialization reuse
   - reuse `_serialize_index_row()` semantics
   - reuse linkage-only diagnostics authority
   - avoid copying field-mapping logic into a second incompatible serializer

3. retrieval-row build
   - compute `source_signature_sha256`
   - build `search_text`
   - use PostgreSQL lexical acceleration only when dialect supports it

4. lexical search contract preservation
   - reuse `normalize_query_tokens()`
   - preserve all-token containment semantics
   - preserve current exact ranking/tie-break behavior
   - apply pagination only after final ranking
   - treat PostgreSQL FTS as candidate pruning only, not ranking replacement
   - if candidate pruning cannot be proven semantics-safe in PostgreSQL, leave retrieval-backed search on Python-side filtering over retrieval rows for Phase 1

5. scoped rebuild
   - run scope
   - target scope
   - full scope only if intentionally opened

6. stale-row reconciliation
   - current-state-only semantics
   - delete only rows inside the declared rebuild scope that were not observed

7. retrieval-backed list/search helpers
   - internal only in Phase 1
   - same public payload shape as current list/search helpers
   - deterministic ordering parity with current behavior

8. parity validator
   - compare canonical APS list/search outputs against retrieval-plane outputs
   - report exact mismatch classes
   - require explicit bounded scope that matches the shadow-build surface
   - do not substitute latest-run discovery for explicit scope

9. explicit build separation
   - rebuild must remain separate from validate-only parity actions
   - rebuild must not be wired into canonical content-index writes in Phase 1
   - rebuild must not run implicitly during migration

### Existing content-index service constraints

If `backend/app/services/nrc_aps_content_index.py` is touched at all, the change must be limited to one of the following:

- extracting a shared serializer/helper so retrieval build logic does not fork field semantics
- exposing a narrow internal canonical-row iterator used by both current list/search and retrieval build

It must not:

- repoint public default list/search behavior
- repurpose APS canonical tables as retrieval tables
- change Evidence Bundle read authority
- broaden query semantics beyond current lexical behavior

## Gate / Tooling Inventory

### New gate behavior

The retrieval-plane gate must be validate-only and fail-closed.

It should:

- read existing APS canonical data
- compare canonical versus retrieval-plane rows
- require explicit bounded run/target scope matching the shadow-build surface
- write a deterministic JSON report using the same deterministic-writer pattern already used by current APS gates
- fail when:
  - explicit bounded scope is omitted
  - the scoped runtime is empty and empties are not allowed
  - retrieval rows are missing
  - orphan retrieval rows exist
  - field parity mismatches exist
  - list ordering mismatches exist
  - search parity mismatches exist
  - diagnostics authority mismatches exist

### Expected new tooling surfaces

1. `tools/nrc_aps_retrieval_plane_shadow_build.py`
   - explicit non-validate shadow-build wrapper
   - must require a bounded scope
   - must fail closed if invoked without a bounded scope

2. `backend/app/services/nrc_aps_retrieval_plane_gate.py`
   - core validate-only gate implementation

3. `tools/nrc_aps_retrieval_plane_gate.py`
   - thin wrapper following the existing gate pattern
   - should stay thin for import/bootstrap only
   - should accept `--run-id` and `--target-id`
   - must require explicit bounded scope arguments compatible with the gate service
   - must not substitute latest-run discovery for explicit bounded scope

4. `project6.ps1`
    - add:
      - action name: `validate-nrc-aps-retrieval-plane`
      - scope params: `-NrcApsRunId`, `-NrcApsTargetId`
      - report path: `tests/reports/nrc_aps_retrieval_plane_validation_report.json`
      - report path variable
      - tool existence check
      - explicit bounded-scope argument pass-through
      - Tier1 PostgreSQL validate-only invocation path for the new action

### Tooling non-goals

Do not add in this slice:

- a new proof runner that seeds its own runtime
- a public comparison endpoint
- a route flag that lets public API callers opt into retrieval-plane reads
- automatic execution of retrieval validation from unrelated validate actions
- automatic invocation of shadow build from validate actions, migrations, or canonical content-index writes

Keep the new gate isolated and explicit.

## Test Inventory

### Required new tests

#### 1. `tests/test_nrc_aps_retrieval_plane.py`

This file should cover at least:

- canonical-source serialization reuse
- build of `source_signature_sha256`
- unchanged-source no-op upsert
- changed-source row update
- stale-row reconciliation inside a declared scope
- retrieval-backed list ordering parity
- retrieval-backed search query-token parity
- search ranking parity with current lexical semantics
- pagination-after-ranking parity
- linkage-only diagnostics parity
- current-state-only deletion semantics
- explicit failure on unbounded build scope
- PostgreSQL candidate-pruning parity on a bounded representative query suite, or explicit proof that candidate pruning stays disabled for Phase 1

#### 2. `tests/test_nrc_aps_retrieval_plane_gate.py`

This file should cover at least:

- fail-closed behavior on empty runtime
- fail when retrieval rows are missing
- fail on orphan rows
- fail on field mismatch
- fail on search parity mismatch
- fail on diagnostics authority mismatch
- pass on clean canonical/retrieval parity
- fail when explicit bounded scope is omitted

### Required updates to existing tests

#### 1. `tests/test_nrc_aps_content_index.py`

Add or adjust only where needed to prove that:

- current canonical list/search behavior remains authoritative
- retrieval-plane helper reuse does not change existing canonical payload semantics

Do not turn this file into the retrieval-plane test suite.

#### 2. `tests/test_nrc_aps_content_index_gate.py`

Update only if shared utilities or report-shape helpers are touched.

#### 3. `tests/test_api.py`

Keep route-level expectations unchanged unless a narrow non-regression assertion is needed to prove:

- `/content-units` still works
- `/content-search` still works
- Evidence Bundle behavior is unchanged

No route cutover assertions belong here in Phase 1.

#### 4. `backend/tests/test_diagnostics_ref_persistence.py`

Do not weaken or bypass these protections. They remain part of the proof basis because retrieval-plane parity depends on linkage-authoritative diagnostics semantics.

#### 5. `backend/tests/test_nrc_aps_evidence_bundle_integration.py`

Do not repoint bundle assembly to the retrieval plane. This test file remains a frozen-consumer protection surface.

### Test surfaces that must remain green

At minimum, the implementation should preserve green status for:

- `tests/test_import_guardrail.py`
- `tests/test_nrc_aps_content_index.py`
- `tests/test_nrc_aps_content_index_gate.py`
- `tests/test_api.py` targeted APS retrieval/bundle assertions
- `backend/tests/test_diagnostics_ref_persistence.py`
- `backend/tests/test_nrc_aps_evidence_bundle_integration.py`
- the two new retrieval-plane test files

## Verification Matrix

### Mandatory pre-merge verification

The implementation packet should require all of the following.

#### A. Migration verification

1. SQLite head-upgrade proof
   - `alembic upgrade head` succeeds in SQLite mode

2. PostgreSQL head-upgrade proof
   - `alembic upgrade head` succeeds in PostgreSQL Tier1 mode

3. No canonical APS-table regression
   - existing APS content tables still exist and remain readable after migration

4. SQLite metadata/create_all compatibility
   - SQLite-backed test/runtime lanes can still import models and create metadata without PostgreSQL-type breakage

#### B. Targeted pytest verification

Run the new and existing targeted tests for:

- retrieval plane
- retrieval-plane gate
- content index
- content-index gate
- diagnostics persistence
- evidence-bundle integration
- route-level APS retrieval/bundle assertions

#### C. Validate-only gate verification

1. Existing canonical lower-layer gates still pass:
   - `validate-nrc-aps-content-index`
   - `validate-nrc-aps-evidence-bundle`

2. New retrieval-plane gate passes on explicit bounded Tier1 PostgreSQL scope:
   - `validate-nrc-aps-retrieval-plane`

3. Retrieval-plane gate fails closed on missing scope or empty runtime

4. Retrieval-plane gate does not build or seed retrieval rows as part of validation

#### D. PostgreSQL shadow validation

In Tier1 PostgreSQL runtime:

- shadow-build retrieval plane for a bounded scope through the explicit non-validate build surface
- validate parity for that same scope
- prove bounded query-parity for representative search cases before enabling PostgreSQL candidate pruning
- prove no public-route cutover occurred by default

### Optional verification

These are optional for the bounded slice unless a blocker or unexpected regression appears:

- full `gate-nrc-aps`
- checked-in report refresh outside the retrieval-plane report
- public read-path cutover experiments

## Documentation / Closeout Inventory

### Required only if implementation lands

If the implementation is completed and accepted, closeout should update:

1. `README.md`
   - new validate-only action
   - bounded description of what it validates

2. `docs/nrc_adams/nrc_aps_status_handoff.md`
   - retrieval-plane slice status
   - proof freshness
   - explicit note that default public reads remain canonical until a later cutover decision

3. `docs/postgres/postgres_status_handoff.md`
   - only if PostgreSQL Tier1 retrieval-plane support materially changes operator guidance

### Not required for code correctness

These doc updates are closeout tasks, not substitutes for proof:

- narrative planning refresh
- historical session exports
- handoff mirror updates

## Tech-Debt Register

The implementation must actively control the following debt risks.

### 1. Split-default dialect debt

Risk:

- PostgreSQL-oriented retrieval work breaks SQLite migration or isolated validation lanes

Control:

- keep PostgreSQL-only search-vector/index logic behind dialect guards
- preserve SQLite head-upgrade success
- preserve Tier2/Tier3 validate-only operation
- preserve SQLite metadata/create_all compatibility in tests and isolated runtimes

### 2. Dual-read drift debt

Risk:

- canonical list/search and retrieval-backed list/search diverge silently

Control:

- do not fork serializer semantics
- add a dedicated parity gate
- keep public default reads unchanged until parity is proven
- keep search ranking and pagination semantics explicitly pinned to the current Python contract

### 3. Lexical-pruning semantic drift debt

Risk:

- PostgreSQL candidate pruning excludes true matches or changes effective ranking because its tokenization diverges from `normalize_query_tokens()`

Control:

- require bounded PostgreSQL query-parity proof before enabling candidate pruning
- keep candidate pruning as prefilter only, never ranking authority
- disable PostgreSQL candidate pruning in Phase 1 if no-false-negative proof is not established

### 4. Dual-state storage debt

Risk:

- retrieval plane becomes stale or orphaned relative to canonical APS tables

Control:

- current-state-only scoped reconciliation
- source-signature upsert rules
- explicit stale-row deletion inside scope
- validate-only orphan detection

### 5. Scope-creep debt

Risk:

- implementation broadens into Evidence Bundle, semantic retrieval, or API redesign

Control:

- explicit no-touch list
- no new public endpoint
- no default route cutover
- no vector/semantic features

### 6. Migration-helper debt

Risk:

- generalized helper widening in `backend/migration_compat.py` for one narrow slice creates long-lived abstraction debt

Control:

- prefer local migration guards first
- widen helper surface only if clearly necessary
- if widened, add the smallest helper that is demonstrably reusable

### 7. Import-path drift debt

Risk:

- new files use `backend.app.*` imports or bypass `app.models` export discipline, creating duplicate package state or fragile model registration

Control:

- keep canonical `app.*` imports only
- keep `tests/test_import_guardrail.py` green
- export new ORM model through `backend/app/models/__init__.py` if package-level imports are used

### 8. Report proliferation debt

Risk:

- new reports become indistinguishable from historical checked-in proof artifacts

Control:

- keep the retrieval-plane report narrowly named and validate-only
- do not refresh unrelated checked-in reports in this slice without explicit reason

## Prohibited Assumptions

Implementation must not assume any of the following:

1. PostgreSQL is the only active dialect in the repo.
2. A Postgres-specific retrieval plane can ignore SQLite migration/test lanes.
3. Evidence Bundle may safely read from the retrieval plane in Phase 1.
4. Public list/search routes may be repointed once the retrieval plane exists.
5. Validate-only parity actions may build retrieval rows as part of validation.
6. PostgreSQL lexical acceleration is allowed to replace current ranking semantics.
7. New service/tool files may ignore the import-path guardrail.
8. Document-level `diagnostics_ref` can be used as a fallback for retrieval parity.
9. Existing validate-only gates cover retrieval-plane parity without a dedicated new gate.
10. The new retrieval-plane gate can safely reuse latest-run discovery instead of explicit bounded scope.
11. A Tier2 SQLite validate path is an adequate proxy for Tier1 PostgreSQL retrieval-plane parity.
12. The new migration file can safely hardcode `0011_...` if another revision lands first.

## Exit Criteria For This Planning Packet

This inventory is adequate only if implementation can follow it and answer all of the following without improvising scope:

1. Which files are definitely new?
2. Which existing files are definitely modified?
3. Which existing files are explicitly no-touch?
4. How does the migration stay safe under PostgreSQL and SQLite?
5. Which tests must be added?
6. Which existing tests must remain green?
7. Which validator actions are mandatory?
8. Which actions are optional and should not be auto-opened?
9. Where can tech debt accumulate, and what are the controls?

If any of those answers are still unclear during implementation, work should return to audit mode before code changes broaden.
