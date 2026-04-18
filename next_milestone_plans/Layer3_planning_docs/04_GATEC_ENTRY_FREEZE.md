# GateC Entry Freeze

## Purpose

This document is the narrow post-Phase 1A planning bridge for the next Layer 3 lane.

It exists to answer one question only:
- what must be explicitly frozen before any Gate C typing-orchestration implementation work starts

It is not a write-enabled prompt.
It is not a Phase 2 implementation plan.
It is not permission to widen route, UI, packaging, APS handoff, or consumer scope.

## Authority and scope

Authority order for this document:
1. live repo code and live status handoffs
2. the active Phase 1A REV2 control spine
3. this Gate C entry-freeze bridge
4. historical Phase 1A REV1 artifacts as context only

This document keeps the already-accepted boundaries:
- Phase 1A remains closed as Gate-B-only feeder and ledger entry
- Gate C is still blocked until typing heuristics and analysis-unit boundaries are explicitly frozen
- package-family work, APS handoff, route-family widening, and consumer widening remain out

## Current starting point

The repo already has three relevant live surface families:

1. `Layer 3 Phase 1A ledger surfaces`
- `backend/app/models/models.py`
- `backend/app/services/layer3_session_entry.py`
- `backend/alembic/versions/0012_layer3_session_entry.py`
- `backend/tests/test_layer3_session_entry.py`

2. `Existing deterministic analysis surfaces`
- `backend/app/services/analysis.py`
- `backend/app/models/models.py` for `AnalysisRun`, `AssumptionCheck`, `CaveatNote`, and `AnalysisArtifact`
- `backend/app/api/router.py`
- `backend/app/schemas/api.py`

3. `Existing analyst-insight and review/runtime surfaces`
- `backend/main.py`
- `backend/app/api/market_data_integration.py`
- `backend/app/api/market_data_validation.py`
- `backend/app/api/market_insight_ai.py`
- `backend/app/review_ui/static/analyst_insight.html`
- `backend/app/review_ui/static/analyst_insight.js`
- `backend/app/services/review_nrc_aps_runtime_db.py`

The current repo therefore already has:
- a bounded Layer 3 write-side ledger slice
- a separate dataset-centric deterministic analysis stack
- a live analyst-insight alias route family and review page
- a separate read-only review/runtime DB helper

Gate C must freeze how those families relate before any new typing-orchestration implementation begins.

## Core dependency stack already in play

Gate C does not start from an empty repo. The live stack already includes:
- `FastAPI` for page and API wiring through `backend/main.py` and `backend/app/api/router.py`
- `pydantic` schema contracts through `backend/app/schemas/api.py`
- `SQLAlchemy` model and session ownership through `backend/app/models/models.py` and the repo DB session layer
- `Alembic` for main-DB migration ownership
- `pandas`, `numpy`, `matplotlib`, `ruptures`, and `statsmodels` inside the existing deterministic analysis stack

Gate C planning must therefore say explicitly:
- which of these are merely reused context
- which are actual owner surfaces
- and which existing dependency-heavy paths stay out of the first Gate C slice

## Connection chains already present

### 1. Public API chain

The current public API wiring already runs:
- `backend/main.py`
- `backend/app/api/router.py`
- `backend/app/api/market_data_integration.py`
- `backend/app/api/market_data_validation.py`
- `backend/app/api/market_insight_ai.py`

That means Gate C must explicitly decide whether it:
- stays internal and avoids public route work
- reuses an existing route family
- or proposes a new route family after a separate freeze

### 2. Dataset-analysis chain

The current dataset-analysis chain already runs:
- `backend/app/api/router.py`
- `backend/app/schemas/api.py`
- `backend/app/services/analysis.py`
- `backend/app/models/models.py`

That means Gate C must explicitly decide whether typing-orchestration:
- reads this chain only as adjacent context
- writes parallel Layer 3 records while leaving this chain unchanged
- or reuses pieces of this chain under an explicit freeze decision

### 3. Analyst-insight UI chain

The current analyst-insight UI chain already runs:
- `backend/main.py`
- `backend/app/review_ui/static/analyst_insight.html`
- `backend/app/review_ui/static/analyst_insight.js`
- the `/api/v1/analyst-insight/...` alias routes

That means Gate C must not silently widen browser or workbench scope just because this chain already exists.

### 4. Review/runtime chain

The current review/runtime chain already runs separately through:
- `backend/app/services/review_nrc_aps_runtime_db.py`
- the NRC APS review and document-trace surfaces

That chain is explicitly read-only and remains a separate consumption plane.

## Live surfaces that Gate C must treat carefully

### 1. Existing analysis stack is real, but not automatic Layer 3 truth

`backend/app/services/analysis.py` already implements deterministic analysis execution and persists:
- `AnalysisRun`
- `AssumptionCheck`
- `CaveatNote`
- `AnalysisArtifact`

It also depends on:
- `pandas`
- `numpy`
- `matplotlib`
- `ruptures`
- `statsmodels`
- the dataset / dataset-version / variable-profile model family

Gate C must not silently assume:
- that `AnalysisRun` is already the Layer 3 typing record
- that existing dataset-version analysis is already the Layer 3 unit/group/set model
- that Layer 3 should reuse these tables without an explicit freeze decision

### 2. Existing analyst-insight API and page surfaces are live, but not a frozen Gate C contract

Current live routes already include:
- `/review/analyst-insight`
- `/api/v1/analyst-insight/integration/cross-reference`
- `/api/v1/analyst-insight/validation/run`
- `/api/v1/analyst-insight/insights/process`

Current legacy-compatible routes also remain live:
- `/api/v1/market-pipeline/integration/cross-reference`
- `/api/v1/market-pipeline/validation/run`
- `/api/v1/market-pipeline/insights/process`

Current dataset-centric analysis routes also exist:
- `/api/v1/datasets/{dataset_id}/versions/{dataset_version_id}/analysis/recommend`
- `/api/v1/analysis-runs`
- `/api/v1/analysis-runs/{analysis_run_id}`

Gate C must not silently assume:
- that the future Layer 3 route family is the current analyst-insight alias family
- that UI or route widening is automatically in scope because those routes already exist
- that Gate C must expose a new public route at all

### 3. Review/runtime DB remains a separate read-only plane

`backend/app/services/review_nrc_aps_runtime_db.py` is the live authority for per-run review/document-trace runtime DB access.

Its contract is explicitly:
- read-only
- schema-validated
- no migrations
- no write-side reuse

Gate C must not cross that boundary by convenience.
Any Gate C implementation lane that needs runtime DB writes, runtime DB migrations, or reuse of review/document-trace helper posture is mis-scoped and should stop.

## Live proof surfaces already present

Current tests already prove parts of the adjacent live surface area:
- `backend/tests/test_layer3_session_entry.py`
- `backend/tests/test_analyst_insight_page.py`
- `backend/tests/test_analyst_insight_alias_parity.py`
- `backend/tests/test_market_data_integration.py`
- `backend/tests/test_market_data_validation.py`
- `backend/tests/test_market_insight_ai.py`
- `backend/tests/test_review_nrc_aps_runtime_db.py`

Gate C planning should name its proof posture relative to these existing tests instead of assuming a blank-slate proof harness.

## Exact blockers that still need explicit freeze

### 1. Typing heuristics

Still not frozen:
- what counts as the first Layer 3 typed record
- whether typing is descriptor-derived, retrieval-derived, material-derived, or hybrid
- what deterministic fields must exist before a record is considered typed
- whether typing is per descriptor, per material snapshot, per retrieval event, or per analysis unit

Required outcome before Gate C write work:
- one explicit first-v1 typing heuristic contract
- one explicit decision about write order relative to the existing Phase 1A ledger tables

### 2. Analysis-unit boundary

Still not frozen:
- what an analysis unit is
- whether unit/group/set boundaries map to dataset-version rows, retrieval chunks, descriptor groups, or another bounded shape
- how those boundaries differ from the already-live dataset-centric `AnalysisRun` family

Required outcome before Gate C write work:
- one explicit unit boundary
- one explicit grouping boundary
- one explicit non-goal list for anything beyond the first frozen boundary

### 3. Persistence posture relative to existing analysis tables

Still not frozen:
- whether Gate C reuses `AnalysisRun` and its companion tables
- whether Gate C writes parallel Layer 3 tables
- whether Gate C reads existing analysis outputs without treating them as Layer 3 truth

Required outcome before Gate C write work:
- one explicit reuse-or-parallel decision
- one explicit statement of which existing model family remains read-only context only

### 4. Invocation and proof posture

Still not frozen:
- whether Gate C entry proof is internal-service only
- whether it may use existing dataset analysis routes
- whether any analyst-insight alias route or page surface is in scope

Required outcome before Gate C write work:
- one explicit proof posture
- one explicit owner-module / touch-set proposal
- one explicit statement about whether public routes stay out

### 5. Qualitative-engine ceiling

Still not frozen:
- how far Gate C goes beyond bounded deterministic typing/orchestration
- whether any broader qualitative-engine ambition enters the tranche

Required outcome before Gate C write work:
- one explicit ceiling
- one explicit no-go line that keeps packaging, handoff, and consumer admission out

## Files to read before opening a Gate C implementation lane

### Planning and control

- `next_milestone_plans/Layer3_planning_docs/01_IMPLEMENTATION_ENTRY_BASELINE_REV2.md`
- `next_milestone_plans/Layer3_planning_docs/02_PHASE1A_IMPLEMENTATION_PREP_SPEC_REV2.md`
- `next_milestone_plans/Layer3_planning_docs/03_PHASE1A_VALIDATION_AND_EXECUTION_PLAN_REV2.md`
- `next_milestone_plans/Layer3_execution_freeze/13-phase1a-surface-map.md`

### Live status docs

- `docs/analyst_insight/analyst_insight_status_handoff.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

### Live code surfaces

- `backend/app/services/analysis.py`
- `backend/app/models/models.py`
- `backend/app/api/router.py`
- `backend/app/api/market_data_integration.py`
- `backend/app/api/market_data_validation.py`
- `backend/app/api/market_insight_ai.py`
- `backend/app/schemas/api.py`
- `backend/main.py`
- `backend/app/services/review_nrc_aps_runtime_db.py`

## Recommended next-lane output

The smallest justified next planning deliverable is not a broad architecture rewrite.

It is one Gate C freeze packet that settles:
- first-v1 typing heuristic
- first-v1 analysis-unit and grouping boundary
- reuse-vs-parallel persistence posture against `AnalysisRun`
- owner module and bounded touched-file set
- proof posture
- explicit non-goals

That next packet should remain read-only until those freezes are accepted.

## Stop conditions for the next lane

Stop instead of widening scope if a proposed Gate C lane requires:
- a public `/api/v1/layer3` route family before the route-family freeze exists
- new page or browser workbench exposure before the workbench freeze exists
- runtime DB writes or runtime DB migrations
- packaging, APS handoff, or consumer admission work
- implicit promotion of existing `AnalysisRun` or analyst-insight routes into Layer 3 truth without an explicit freeze decision

## Bottom line

Phase 1A is no longer the blocker.

The blocker is now a missing explicit Gate C freeze across:
- typing heuristics
- analysis-unit boundaries
- persistence posture
- invocation and proof posture
- qualitative-engine ceiling

Until those are frozen, the correct next step is planning, not implementation.
