# Agent Bake-Off Scope: APS Tier1 Retrieval Plane Phase1B

## 1. Purpose

This document freezes the second bounded retrieval-plane bake-off slice.

This slice is intentionally narrow. It must not become an implicit cutover, ranking rewrite, or public API redesign.

## 2. Slice Name

`Phase1B: Operator Retrieval Read Path`

## 3. In Scope

The implementation must include all of the following.

### 3.1 Retrieval Read Service

Add one retrieval-plane read service that can:

- list retrieval rows for one run in the same logical shape as `list_content_units_for_run`
- search retrieval rows in the same logical shape as `search_content_units`
- preserve deterministic ordering compatible with current APS behavior

### 3.2 Operator-Only Endpoints

Add exactly these operator-only endpoints:

- external HTTP route: `GET /api/v1/connectors/runs/{connector_run_id}/_operator/retrieval-content-units`
- external HTTP route: `POST /api/v1/connectors/nrc-adams-aps/_operator/retrieval-content-search`

These endpoints must:

- read from the retrieval plane, not from canonical APS joins
- reuse the current public request/response schemas
- leave the current public endpoints unchanged

### 3.3 Empty-Scope Fail-Closed Behavior

If the requested run has no retrieval-plane rows where rows are required, the operator-only retrieval path must fail closed rather than silently falling back to canonical APS reads.

### 3.4 Focused Parity Tests

Add focused tests that prove:

- operator-only retrieval list matches canonical list shape and order after rebuild
- operator-only retrieval search matches canonical search shape and order after rebuild
- operator-only retrieval path fails closed when retrieval rows are absent for a non-empty canonical run

## 4. Exact Ordering Rules

### 4.1 Run-Scoped List Order

The retrieval-plane list path must preserve the current list order:

- `content_id ASC`
- `chunk_ordinal ASC`
- `target_id ASC`

### 4.2 Search Order

The retrieval-plane search path must preserve the current search order:

- `matched_unique_query_terms DESC`
- `summed_term_frequency DESC`
- `chunk_length ASC`
- `content_id ASC`
- `chunk_ordinal ASC`
- `run_id ASC`
- `target_id ASC`

### 4.3 Search Matching Rule

The retrieval-plane search path must preserve the current token semantics:

- normalize query tokens using the existing APS token normalization logic
- require all unique query tokens to appear in `search_text`
- compute `summed_term_frequency` from `search_text`

## 5. Explicitly Deferred

The following are out of scope for Phase1B:

- default read-path cutover of existing public endpoints
- feature-flagging the existing public endpoints
- response-schema widening
- review UI changes
- embeddings or vector indexes
- Postgres-specific ranking or index tuning beyond what is strictly required for this slice
- operator orchestration surfaces, background jobs, or CLI entrypoints
- upper-layer artifact consumption of the retrieval plane

## 6. Allowed Repo Surface

This slice should normally touch only:

- `backend\app\api\router.py`
- `backend\app\services\aps_retrieval_plane_contract.py`
- `backend\app\services\aps_retrieval_plane.py`
- `backend\app\services\aps_retrieval_plane_read.py`
- `backend\tests\`

Touch `backend\app\schemas\api.py` only if a repo-confirmed blocker makes schema reuse impossible.

Do not touch:

- `backend\app\review_ui\*`
- `backend\main.py`
- `backend\app\api\review_nrc_aps.py`
- `backend\app\services\review_nrc_aps_*`

unless a repo-confirmed blocker makes that unavoidable. If that happens, stop and explain it instead of broadening scope silently.

## 7. Acceptance Criteria

This slice is adequate only if all of the following are true:

- operator-only retrieval endpoints exist at the exact frozen routes
- current public content-search and content-units routes remain unchanged by default
- retrieval endpoints reuse existing request/response contracts
- retrieval list/search results preserve current deterministic ordering semantics
- retrieval reads do not silently fall back to canonical joins when retrieval rows are missing
- linkage-authoritative `diagnostics_ref` semantics remain intact
- focused parity tests pass
- no review UI regression is introduced
