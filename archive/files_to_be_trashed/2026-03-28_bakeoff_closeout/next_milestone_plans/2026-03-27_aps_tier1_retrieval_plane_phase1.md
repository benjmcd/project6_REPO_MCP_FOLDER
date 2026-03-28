# APS Tier1 Retrieval Plane Phase 1 Design Spec

## Status

Planning only. This document is a strict bounded-slice planning surface. It does not authorize code edits, schema edits, API edits, validator edits, artifact regeneration, or milestone reclassification by itself.

## Scope

This document defines a recommended Phase 1 plan for a Tier1 PostgreSQL retrieval plane that improves APS investigation retrieval without changing canonical APS evidence truth and without reopening closed APS milestones.

This phase is intentionally limited to:

- additive Tier1 PostgreSQL retrieval infrastructure
- lexical retrieval and filterable browse/query behavior
- parity validation against canonical APS truth
- planning for a later optional read-path cutover decision

This phase explicitly excludes:

- embeddings
- vector indexes
- semantic extraction
- concept graphs
- machine-generated insight persistence
- upper-layer schema widening
- closed-layer default behavior changes without a separate cutover decision

## Canonical Authority And Truth Model

Primary live authority for this plan:

- `docs/nrc_adams/nrc_aps_authority_matrix.md`
- `docs/nrc_adams/nrc_aps_reader_path.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `docs/postgres/postgres_status_handoff.md`
- `project6.ps1`
- `backend/app/core/config.py`
- `backend/app/models/models.py`
- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/nrc_aps_evidence_bundle_contract.py`
- `backend/app/services/nrc_aps_evidence_bundle.py`
- `backend/app/services/analysis.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_evidence_report_gate.py`
- `backend/alembic/versions/0008_aps_content_index_tables.py`
- `backend/alembic/versions/0009_aps_document_processing_metadata.py`
- `backend/alembic/versions/0010_visual_page_refs_json.py`

Repo-confirmed facts that constrain this plan:

- Tier1 operator default is PostgreSQL; no-env runtime remains SQLite; Tier2/Tier3 remain intentionally SQLite-shaped.
- APS canonical content truth currently lives in `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage`.
- The current APS search path performs token-based matching in application code after fetching joined APS rows.
- The upper analytical ceiling remains frozen through Deterministic Challenge Review Packet v1.
- Artifact ingestion and content indexing remain reopened additively for lower-layer work, but Phase 8 APS table materialization is already closed.
- Existing APS artifact layers already use schema IDs, contract IDs, stable checksums, and validate/gate patterns.
- `diagnostics_ref` is authoritative at the linkage/run-target level; document-row fallback is not authoritative across runs.
- Existing `validate-*` actions remain validate-only, fail closed on empty runtime, and must not seed artifacts.

Non-authoritative or lower-authority surfaces for this plan:

- `handoff/backend/*`
- stale/historical planning prose
- broad repo prose unless directly corroborated by current root docs and live root code

## Workstream Classification

This work must be treated as:

- a bounded additive slice above the closed Phase 8 bridge milestone
- a Tier1 PostgreSQL operator/performance/retrieval slice
- not a reopening of settled lower-layer proof facts
- not an automatic widening of the frozen upper analytical chain

This work must not silently reclassify itself into:

- a lower-layer document-processing milestone
- a new evidence-bundle milestone
- a schema-widening upper-layer milestone
- a general semantic platform buildout

## Problem Statement

The current APS canonical tables are adequate for deterministic evidence storage, but they are not an optimized retrieval surface.

Current repo-confirmed shape:

- APS content tables are indexed mainly for identity and run/content lookup.
- Search behavior is implemented in Python over rows loaded from the database.
- Retrieval-relevant filters and display metadata are spread across document, chunk, and linkage tables.
- There is no single flattened Tier1 PostgreSQL surface dedicated to investigation-oriented retrieval.

That means the system has canonical truth, but not a dedicated Tier1 retrieval plane.

## Critical Invariants

The following invariants are mandatory for this plan:

1. `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage` remain canonical evidence truth.
2. Any retrieval-plane row is fully derived, never canonical.
3. Phase 1 must be additive first. No default read-path replacement is part of the initial build.
4. No frozen upper-layer schema ID, contract ID, checksum algorithm, or artifact shape may be widened by this work.
5. `diagnostics_ref` authority must continue to follow linkage-level semantics, not document-level fallback semantics.
6. Validate-only actions must remain validate-only, fail closed on empty runtime, and must not seed or generate artifacts.
7. Any proof-style action must use isolated runtime state and must not rely on shared seeded state.
8. Tier2/Tier3 SQLite-shaped behavior is not a design ceiling for Tier1 PostgreSQL, but this phase must not force lower-tier redesign.

## Phase 1 Objective

Phase 1 should deliver a shadow retrieval plane, not an immediate consumer cutover.

The objective is to add one derived Tier1 PostgreSQL retrieval surface that:

- is rebuilt from canonical APS content/linkage truth
- supports DB-native lexical search
- supports run-scoped and filter-scoped browse/list behavior
- preserves deterministic ordering and provenance visibility
- can be validated against canonical APS truth
- is designed so later embedding support can be added without redesigning the retrieval surface

The objective is not to switch all closed read surfaces to that plane in the same slice.

## Non-Goals

This phase must not:

- change APS canonical evidence semantics
- add embeddings or vector indexes
- introduce semantic extraction or concept persistence
- require external search engines
- become a prerequisite for current deterministic APS artifact generation
- force Tier2 or Tier3 off their current SQLite-shaped design
- change Evidence Bundle, Citation Pack, Evidence Report, Context Packet, Context Dossier, Deterministic Insight, Deterministic Challenge, or Review Packet schemas
- change default public APS API behavior before parity is proven and a separate cutover decision is accepted

## Recommended Execution Sequence

Phase 1 should be executed in four strict stages:

### Stage 1: Shadow Retrieval Plane Build

Build the retrieval plane as an additive derived Tier1 PostgreSQL surface.

At this stage:

- canonical APS writes remain unchanged
- existing public read paths remain unchanged
- the retrieval plane is populated and queryable internally

### Stage 2: Validate-Only Parity

Add a retrieval-plane validator that compares shadow retrieval rows to canonical APS truth.

At this stage:

- the validator must be validate-only
- the validator must fail closed on empty runtime
- the validator must not seed or generate business artifacts
- no public cutover occurs

### Stage 3: Optional Operator Read Path

If Stage 2 parity is stable, add an explicit operator-only or feature-flagged read path that can query the retrieval plane.

At this stage:

- default public behavior still remains unchanged
- the retrieval plane is an opt-in read surface for controlled comparison

### Stage 4: Separate Cutover Decision

Only after stable parity and controlled read-path evidence should the repo decide whether a closed public surface such as `content-search` should change its default read path.

That cutover is outside base Phase 1 build scope and must be treated as a separate decision gate.

## Recommended Shape

### Recommendation

Use a derived retrieval table, not a materialized view, as the Phase 1 retrieval plane.

### Why a derived table is preferred

- It matches the repo's existing explicit persistence and validation style better than opaque database refresh behavior.
- It allows row-level rebuilds and run-scoped rebuilds instead of only blunt full refresh patterns.
- It gives a cleaner path for later hybrid retrieval, where lexical and semantic state may coexist without changing canonical APS tables.
- It makes source hashing and contract-version invalidation explicit.
- It can be validated against canonical APS rows using the repo's existing gate/report idioms.

### Alternatives considered

- Materialized view:
  - Simpler as a read projection.
  - Less attractive because rebuild control, row-level invalidation, and later semantic expansion are weaker.
- Directly widening APS canonical tables:
  - Rejected.
  - Would blur canonical evidence truth with derived retrieval state.
- External search engine:
  - Rejected for Phase 1.
  - Too broad for the current repo and unnecessary before Tier1 PostgreSQL is fully exploited.

## Proposed Retrieval Surface

### Recommended logical name

`aps_retrieval_chunk_v1`

This is a proposed planning name only. It is not yet authoritative.

### Row identity

Each retrieval row should represent one APS chunk in one run/target context.

Recommended stable identity input:

- `retrieval_contract_id`
- `run_id`
- `target_id`
- `content_id`
- `chunk_id`

### Proposed columns

Core identity and source keys:

- `aps_retrieval_chunk_id`
- `retrieval_contract_id`
- `run_id`
- `target_id`
- `content_id`
- `chunk_id`
- `content_contract_id`
- `chunking_contract_id`
- `normalization_contract_id`
- `accession_number`

Chunk shape and order:

- `chunk_ordinal`
- `start_char`
- `end_char`
- `page_start`
- `page_end`
- `chunk_text`
- `chunk_text_sha256`

Document and retrieval filters:

- `content_status`
- `quality_status`
- `document_class`
- `media_type`
- `page_count`

Provenance and evidence references:

- `content_units_ref`
- `normalized_text_ref`
- `normalized_text_sha256`
- `blob_ref`
- `blob_sha256`
- `download_exchange_ref`
- `discovery_ref`
- `selection_ref`
- `diagnostics_ref`
- `visual_page_refs_json`

Derived retrieval fields:

- `search_text`
- `search_vector`
- `matched_language_config`
- `source_signature_sha256`
- `source_updated_at`
- `rebuilt_at`
- `created_at`

### Notes on proposed fields

- `search_text` should normally mirror `chunk_text` in Phase 1, but the separate field leaves room for future normalization choices without touching canonical APS chunk text.
- `search_vector` is the DB-native lexical-search representation for `search_text`.
- `source_signature_sha256` is a stable hash of the canonical APS fields that feed this retrieval row.
- `source_updated_at` tracks the latest canonical source timestamp consumed by the retrieval row.
- `diagnostics_ref` in the retrieval plane must be sourced from linkage-authoritative semantics, not document-row fallback semantics.
- `visual_page_refs_json` is copied retrieval metadata only; document-level visual references remain canonical in APS truth.

## Recommended Indexing Strategy

Phase 1 should add indexes for retrieval behavior, not only identity lookup.

Recommended index groups:

- unique lookup on retrieval identity
- btree on `(run_id, quality_status, document_class)`
- btree on `(run_id, content_id, chunk_ordinal)`
- btree on `(content_id, chunk_id)`
- lexical-search index on `search_vector`

The retrieval plane should preserve deterministic tie-break order compatible with current APS behavior:

- stronger lexical match first
- then stable chunk/document order
- then stable identity order

## Rebuild And Invalidation Rules

### Canonical source rule

The retrieval plane is always derived from:

- one `ApsContentLinkage` row
- one `ApsContentDocument` row
- one `ApsContentChunk` row

No retrieval row is canonical. Every retrieval row must be reconstructable from APS truth.

### Rebuild triggers

Rebuild the affected retrieval rows when any of the following change:

- `chunk_text_sha256`
- `chunk_text`
- `chunk_ordinal`
- `start_char` or `end_char`
- `page_start` or `page_end`
- `content_status`
- `quality_status`
- `document_class`
- `media_type`
- `page_count`
- provenance refs
- `content_contract_id`
- `chunking_contract_id`
- `normalization_contract_id`
- linkage-authoritative `diagnostics_ref`
- retrieval contract version

### Rebuild scope

Preferred rebuild scopes:

- single content/chunk rebuild
- single target rebuild
- single run rebuild
- full retrieval-plane rebuild on contract bump

### Invalidation rule

If the canonical APS source triplet no longer exists, the derived retrieval row must no longer be treated as current. The exact implementation choice can be:

- delete derived row
- mark derived row inactive
- move derived row to an archived retrieval history table

That decision can be deferred, but the retrieval plane must never silently outlive missing APS source truth.

### Hash rule

If `source_signature_sha256` matches the new canonical source projection, the retrieval row should not be rewritten.

## API Behavior

### Principle

Phase 1 is additive first. Default public APS API behavior must remain unchanged until parity is proven and a separate cutover decision is accepted.

### Existing surfaces to target first

- `/connectors/nrc-adams-aps/content-search`
- `/connectors/runs/{connector_run_id}/content-units`

### Phase 1 public-surface rule

Stage 1 and Stage 2 must not replace the default read path for these surfaces.

Only Stage 3 may introduce:

- operator-only retrieval-plane reads
- feature-flagged internal comparisons
- explicit parity/debug endpoints if needed

### Future cutover rule

If a later slice proposes default read-path cutover for `content-search` or any other closed public surface, that cutover must:

- be treated as a separate decision
- prove parity against canonical APS truth
- preserve existing request semantics
- preserve returned provenance fields and APS identities
- preserve deterministic tie-break ordering
- not widen public schema contracts

## Validation Strategy

### General rule

Validation and proof obligations must track the repo's existing operator semantics:

- `validate-*` actions remain validate-only
- validate actions fail closed on empty runtime
- validate actions do not seed or generate artifacts
- proof actions use isolated runtime state

### Phase 1 validation obligations

Phase 1 should include a dedicated validate-only comparison between canonical APS truth and the retrieval plane.

Validation must confirm:

- row-count agreement at the intended scope
- source-signature agreement
- field-level agreement for retrieval-visible metadata
- deterministic ordering agreement
- resolvable provenance refs
- linkage-authoritative diagnostics semantics
- zero orphan retrieval rows at the validated scope

### Recommended proof layering

- Stage 1:
  - schema/migration verification for the retrieval plane itself
  - no public cutover assertions
- Stage 2:
  - validate-only parity report for retrieval plane vs APS truth
- Stage 3:
  - controlled operator read-path comparison
- Stage 4:
  - only if approved, consumer-facing parity proof for the specific surface being cut over

### Lower-layer proof boundary

`prove-nrc-aps-document-processing` is a lower-layer proof runner, not a generic validator for this work. It should only be rerun if this slice actually changes lower-layer document/media behavior or canonical content-index derivation behavior.

The report format should reuse the repo's existing schema/checksum/report style instead of introducing ad hoc diagnostics.

## Recommended Reuse

Reuse from the existing repo:

- APS schema/contract/checksum idioms for retrieval-plane validation artifacts
- existing gate philosophy for parity reporting
- `AnalysisRun` / `AnalysisArtifact` persistence patterns only if a durable execution log is needed for retrieval rebuild or comparison jobs
- existing APS gate philosophy for any validation output

Do not reuse by force:

- dataset-analysis domain tables as the canonical store for APS retrieval state
- any lower-tier SQLite assumptions that would weaken Tier1 PostgreSQL design choices
- document-row diagnostics semantics where linkage-authoritative semantics are already established

## Tech Debt Register

Phase 1 must explicitly account for these debt risks:

### 1. Split-default backend debt

- Tier1 is PostgreSQL-first while no-env runtime remains SQLite.
- Risk:
  - implementation or tests accidentally assume one backend model is universal.
- Control:
  - make the retrieval plane explicitly Tier1 PostgreSQL-scoped.

### 2. Dual-state debt

- Canonical APS truth and derived retrieval state will coexist.
- Risk:
  - silent drift, stale rows, or untracked rebuild lag.
- Control:
  - source signatures, explicit rebuild rules, validate-only parity reports.

### 3. Cutover debt

- Shadow and default read paths may diverge if both live too long.
- Risk:
  - prolonged dual-read complexity.
- Control:
  - require explicit Stage 4 decision rather than indefinite partial adoption.

### 4. Diagnostics authority debt

- The repo already hardened linkage-only `diagnostics_ref` authority.
- Risk:
  - a retrieval plane accidentally reintroduces document-level fallback semantics.
- Control:
  - make linkage-authoritative diagnostics a hard invariant and parity check.

### 5. Contract-drift debt

- Retrieval-plane logic may drift from APS contracts.
- Risk:
  - hidden mismatch between APS truth and retrieval output.
- Control:
  - retrieval contract ID plus parity validator plus explicit invalidation on contract change.

### 6. Validation freshness debt

- Checked-in reports may become historical quickly.
- Risk:
  - false confidence from stale validation artifacts.
- Control:
  - treat new retrieval-plane parity reports as scope-specific and date-scoped proof only.

### 7. PostgreSQL-extension debt

- A future vector path may require optional extensions.
- Risk:
  - premature coupling of Phase 1 lexical retrieval to future vector assumptions.
- Control:
  - keep Phase 1 lexical-only and semantic-ready, not semantic-dependent.

### 8. Path-length / identifier debt

- Windows path-length and filename constraints are real in this repo.
- Risk:
  - verbose retrieval artifact names or report identifiers cause avoidable friction.
- Control:
  - keep retrieval-plane IDs, report names, and artifact paths short.

## Unsafe Assumptions To Avoid

Do not assume:

- that a retrieval plane automatically justifies altering frozen upper analytical behavior
- that `content-search` default cutover is part of base Phase 1
- that Evidence Bundle or any upper-layer artifact should consume the retrieval plane in Phase 1
- that document-row `diagnostics_ref` is safe authority across runs
- that Tier2/Tier3 must mirror Tier1 retrieval-plane design immediately
- that lexical retrieval work should pull in embeddings or external search in the same slice
- that broad repo prose surfaces outrank the APS authority docs and live root code

## Acceptance Criteria

Phase 1 is adequate only if all of the following are true:

- the retrieval plane is strictly derived from canonical APS truth
- canonical APS evidence tables remain the source of truth
- no closed upper-layer schema or artifact contract is widened
- no default closed public read surface is repointed during base build stages
- Tier1 PostgreSQL can satisfy lexical retrieval from the shadow retrieval plane
- retrieval-visible metadata preserves provenance visibility, deterministic ordering, and linkage-authoritative diagnostics semantics
- rebuild and invalidation rules are explicit
- a validate-only parity comparison can prove retrieval-plane agreement with APS truth
- all verification semantics remain aligned with existing validate-only and isolated-runtime rules

## Deferred To Later Phases

Deferred deliberately:

- default public read-path cutover
- embeddings
- hybrid lexical + vector ranking
- semantic extraction
- claim/entity/relation persistence
- insight-run persistence
- promotion gates for semantic artifacts

## Open Decisions

Still worth settling before implementation:

- whether inactive-row history is needed or whether current-state-only retrieval rows are sufficient
- whether retrieval rebuild execution should be tracked with a dedicated APS run model or a reused `AnalysisRun`-like pattern
- whether `search_text` should remain equal to `chunk_text` in Phase 1 or apply a retrieval-specific normalization step
- whether operator-only comparison should use a feature flag, a separate endpoint, or a separate CLI/read path
- what exact proof threshold is required before any closed public surface can be proposed for default cutover

## Recommended Next Planning Step

If this design direction is accepted, the next planning pass should define:

- exact retrieval table DDL
- exact index set
- exact source-signature payload
- exact lexical ranking rules
- exact parity-validator report schema
- exact stage-by-stage verification matrix
- exact operator-only read-path strategy
- exact criteria for any future default cutover proposal
