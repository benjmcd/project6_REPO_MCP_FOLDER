# 13 Phase1A Surface Map

## Purpose

This document is a lane-local operational companion for the bounded Phase 1A Layer 3 slice on `codex/layer3-lane`.

It exists to make the concrete implementation surfaces explicit in one place:
- owner modules
- adjacent read-only modules
- live dependency and library touchpoints
- DB, storage, and migration connection points
- route and endpoint boundaries that remained intentionally untouched

If this document conflicts with the stronger Phase 1A control spine or the postcode acceptance audit, those stronger docs govern.

## Frozen tranche reminder

This map is still bounded to the same accepted Phase 1A tranche:
- `l3_session`
- `l3_selection_manifest`
- `l3_descriptor`
- `l3_retrieval_event`
- `l3_material_snapshot`

Still deferred:
- typing
- orchestration
- packaging
- APS handoff
- route-family widening
- UI widening
- consumer widening
- later Layer 3 objects beyond the first five

## Canonical authority surfaces for this lane

### Normative control spine

Use these first for tranche rules and no-go boundaries:
- `next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
- `next_milestone_plans/Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md`
- `next_milestone_plans/Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`
- `next_milestone_plans/Layer3_execution_handoff/04_PHASE1A_FILE_TOUCH_AND_OWNER_MATRIX.md`
- `next_milestone_plans/Layer3_execution_handoff/05_PHASE1A_PROOF_RUNBOOK_AND_STOP_CONDITIONS.md`
- `next_milestone_plans/Layer3_execution_handoff/06_PHASE1A_CODEWRITING_HANDOFF.md`
- `next_milestone_plans/Layer3_execution_freeze/07_PHASE1A_IMPLEMENTATION_LOCAL_DECISIONS_REV2.md`
- `next_milestone_plans/Layer3_execution_freeze/08_PHASE1A_PRECODE_ACCEPTANCE_CHECKLIST_REV2.md`
- `next_milestone_plans/Layer3_execution_freeze/09_PHASE1A_WRITE_ENABLED_CODEX_PROMPT_REV2.md`
- `next_milestone_plans/Layer3_execution_freeze/10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`

### Live repo-confirmed implementation surfaces

These are the actual Phase 1A code surfaces that landed:

| path | role | Phase 1A posture |
| --- | --- | --- |
| `backend/app/models/models.py` | append-only ORM block for the five new ledger objects | live owner surface |
| `backend/app/services/layer3_session_entry.py` | internal selection-to-descriptor-to-retrieval-to-snapshot service flow | live owner surface |
| `backend/alembic/versions/0012_layer3_session_entry.py` | manual migration for the five new tables | live owner surface |
| `backend/tests/test_layer3_session_entry.py` | direct internal-service proof module | live owner surface |

## Concrete owner-module map

### 1. ORM owner surface

`backend/app/models/models.py` now carries the bounded Layer 3 ORM block:
- `L3Session`
- `L3SelectionManifest`
- `L3Descriptor`
- `L3RetrievalEvent`
- `L3MaterialSnapshot`

What this module is responsible for:
- durable ledger identity
- session-scoped relationships
- JSON-backed manifest / selector / event / provenance payload fields
- additive only schema ownership for the first five objects

What it does not do:
- no Phase 2+ objects
- no route or API contracts
- no runtime DB helper behavior

### 2. Internal owner service

`backend/app/services/layer3_session_entry.py` is the narrow Phase 1A owner module.

What it owns:
- selection commit
- descriptor expansion
- retrieval-event recording
- material-snapshot persistence
- session finalization summary

What it explicitly depends on:
- `app.models.models` for the five Layer 3 models and `uuid_str`
- `app.core.config.settings` for artifact-storage-root resolution
- SQLAlchemy `Session`
- Python stdlib JSON / hashing / filesystem primitives

What it explicitly does not do:
- no FastAPI router registration
- no schema export
- no browser flow
- no APS downstream artifact assembly
- no runtime DB write reuse

### 3. Manual migration surface

`backend/alembic/versions/0012_layer3_session_entry.py` is the only migration surface for this tranche.

What it owns:
- creation of `l3_session`
- creation of `l3_selection_manifest`
- creation of `l3_descriptor`
- creation of `l3_retrieval_event`
- creation of `l3_material_snapshot`

What it does not do:
- no alteration of existing tables
- no Phase 2+ schema
- no migration-strategy redesign

### 4. Proof surface

`backend/tests/test_layer3_session_entry.py` is the only proof module for this slice.

What it proves:
- one happy path
- one partial-feed / explicit-failure path
- explicit plane lineage
- explicit loaded-versus-failed reporting

What it uses:
- in-memory SQLite for isolated ORM proof
- `tmp_path` for disposable payload persistence
- direct internal service imports only

## Component and contract posture

### UI / frontend components

For this tranche, there are no new Layer 3 UI components.

Explicitly not added:
- no review page
- no workbench page
- no static asset bundle
- no browser flow

Relevant untouched boundary surfaces:
- `backend/main.py`
- `backend/app/review_ui/static/**`
- `backend/app/api/review_nrc_aps.py`

### API / schema contracts

For this tranche, there are no new public API contracts.

Explicitly not added:
- no new router
- no new `APIRouter` include
- no new `backend/app/schemas/api.py` block
- no new review-facing or consumer-facing schema export

Relevant untouched boundary surfaces:
- `backend/app/api/router.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/app/schemas/api.py`
- `backend/app/schemas/review_nrc_aps.py`

## Libraries and dependencies actually in play

### Framework and persistence stack

- `FastAPI`
  - remains an adjacent boundary only for this tranche
  - no new route or page surface was added
- existing mounted review/component surfaces remain unchanged
- `SQLAlchemy`
  - ORM model definitions live in `backend/app/models/models.py`
  - `Session` enters through `backend/app/db/session.py`
  - JSON columns and ORM relationships are the main persistence primitives used
- `Alembic`
  - one manual migration file under `backend/alembic/versions`
  - URL resolution still flows through `backend/alembic/env.py`
- `pydantic-settings`
  - `backend/app/core/config.py` remains the config source for `settings.database_url` and `settings.artifact_storage_dir`
- `pytest`
  - single targeted proof module only

### Python stdlib surfaces actually used by the Phase 1A owner module

- `hashlib`
- `json`
- `pathlib.Path`
- `datetime`
- `collections.Counter`
- `dataclasses`

### Dependency posture

- no new third-party dependency was introduced for Phase 1A
- no package-management or environment-contract widening was required
- the slice reuses existing repo configuration, ORM, migration, and test infrastructure

## Connection and boundary map

### DB connection path

Runtime ORM path:
- `backend/app/core/config.py`
  - resolves `settings.database_url`
- `backend/app/db/session.py`
  - builds `engine`
  - exposes `SessionLocal`
- `backend/app/services/layer3_session_entry.py`
  - accepts a SQLAlchemy `Session`
  - performs write-side work only against the main repo DB target, not the runtime DB helper family

Migration path:
- `backend/alembic/env.py`
  - resolves DB target from:
    1. `DATABASE_URL`
    2. `settings.database_url`
    3. `alembic.ini`

### Storage connection path

Default Phase 1A payload persistence path:
- `backend/app/core/config.py`
  - `settings.artifact_storage_dir`
- `backend/app/services/layer3_session_entry.py`
  - `_default_storage_root() -> Path(settings.artifact_storage_dir) / "layer3"`

Proof-only override path:
- `backend/tests/test_layer3_session_entry.py`
  - passes `tmp_path` directly so the proof stays isolated and disposable

### Endpoint and route boundaries

Existing route boundary files:
- `backend/main.py`
- `backend/app/api/router.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/app/schemas/api.py`
- `backend/app/schemas/review_nrc_aps.py`

Phase 1A posture at those boundaries:
- no new `/api/v1/layer3` route family
- no new `/review/layer3` page family
- no router inclusion for Layer 3
- no new public schema contract block
- no change to existing review, market, or analyst-insight browser surfaces

### Adjacent read-only connection families

These families constrain semantics but remain intentionally untouched by Phase 1A:
- `backend/app/services/review_nrc_aps_*`
- `backend/app/services/analysis.py`
- `backend/app/api/market_data_*.py`
- `backend/app/services/market_data_*.py`
- `backend/app/services/market_insight_ai.py`
- `backend/app/services/nrc_aps_evidence_bundle*.py`
- `backend/app/services/nrc_aps_context_packet*.py`
- `backend/app/services/nrc_aps_context_dossier*.py`
- `backend/app/services/nrc_aps_deterministic_*`

## Practical implementation reading order

If a future reader needs the fastest concrete orientation for the accepted Phase 1A slice:

1. Read `10_PHASE1A_POSTCODE_ACCEPTANCE_AUDIT.md`
2. Read this surface map
3. Read `06_PHASE1A_CODEWRITING_HANDOFF.md`
4. Read the four actual Phase 1A code files
5. Only then decide whether a new pass is justified

## Why this doc exists

The control spine already froze the tranche correctly.
What it did not do in one place was spell out the live concrete surface map across:
- owner modules
- reused libraries
- config and migration resolution
- storage and DB connection points
- untouched endpoint and adjacent-service families

This companion doc closes that lane-local clarity gap without reopening scope.
