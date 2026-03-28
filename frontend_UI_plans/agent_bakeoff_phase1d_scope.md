# Agent Bake-Off Scope: APS Tier1 Retrieval Plane Phase1D

## 1. Purpose

This document freezes the next bounded public-cutover bake-off slice.

## 2. Slice Name

`Phase1D: Public Run-Scoped Retrieval Cutover`

## 3. In Scope

The implementation must include all of the following.

### 3.1 Public Run-Scoped Content-Units Cutover

Repoint the current public route:

- `GET /api/v1/connectors/runs/{connector_run_id}/content-units`

so that it now defaults to the retrieval read path for that run.

### 3.2 Public Run-Scoped Search Cutover

Repoint the current public route:

- `POST /api/v1/connectors/nrc-adams-aps/content-search`

so that it now defaults to the retrieval read path only when `payload.run_id` is explicitly non-empty.

If `payload.run_id` is omitted or blank:

- keep the current canonical path unchanged
- do not broaden this round into global search redesign

### 3.3 Fail-Closed Public Behavior

Public run-scoped cutover requests must:

- return the frozen retrieval-not-materialized `409` detail when retrieval rows are absent
- return the same `409` detail when retrieval rows are partially materialized
- never silently fall back to canonical reads for the cutover-eligible run-scoped surfaces

### 3.4 Focused Tests And Proof

Add or update focused tests that prove:

- public run-scoped `content-units` now uses retrieval semantics
- public run-scoped `content-search` now uses retrieval semantics when `run_id` is supplied
- omitted-`run_id` public search remains unchanged
- retrieval-not-materialized and partial materialization fail closed with `409`
- current public response schema and deterministic ordering remain intact
- the existing Phase1C cutover proof still passes on isolated runtime state

## 4. Explicitly Deferred

The following are out of scope for Phase1D:

- omitted-`run_id` search redesign
- operator route retirement
- hidden headers, query switches, or config flags
- new HTTP routes
- schema/model/Alembic widening
- review UI changes
- embeddings or vector work
- checked-in report refresh under `tests\reports\`

## 5. Allowed Repo Surface

This slice should normally touch only:

- `backend\app\api\router.py`
- `backend\app\services\aps_retrieval_plane_read.py`
- `backend\tests\`

Allowed only if a small validation adjustment is repo-confirmed necessary:

- `backend\app\services\aps_retrieval_plane_cutover_validation.py`

Do not touch:

- `project6.ps1`
- `tools\`
- `backend\app\schemas\api.py`
- `backend\alembic\versions\`
- `backend\app\models\`
- `backend\app\review_ui\*`

unless a repo-confirmed blocker makes that unavoidable. If that happens, stop and explain it instead of broadening scope silently.

## 6. Acceptance Criteria

This slice is adequate only if all of the following are true:

- the public run-scoped `content-units` route now defaults to the retrieval read path
- the public `content-search` route now defaults to the retrieval read path when `run_id` is explicitly supplied
- omitted-`run_id` search remains unchanged
- retrieval-not-materialized and partial materialization fail closed with explicit `409` detail
- public request and response schemas remain unchanged
- deterministic ordering is preserved for the proven run-scoped surfaces
- operator routes remain unchanged
- the focused review UI regression suite still passes
