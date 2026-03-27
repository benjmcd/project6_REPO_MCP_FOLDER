# Agent Bake-Off Implementation Blueprint: APS Tier1 Retrieval Plane Phase1B

## 1. Purpose

This document freezes the repo-fit file and module ownership plan for the operator-only retrieval read-path slice.

## 2. Expected File Ownership

### 2.1 API Layer

Expected modified file:

- `backend\app\api\router.py`

Responsibilities:

- add exactly two operator-only retrieval endpoints
- keep existing public APS endpoints unchanged
- reuse current schema contracts
- fail closed when retrieval rows are absent for a non-empty required scope

Do not add a new standalone router file for this round.

### 2.2 Schema Layer

Expected behavior:

- reuse `NrcApsContentSearchIn`
- reuse `NrcApsContentSearchOut`
- reuse `ConnectorRunContentUnitsPageOut`

Expected file:

- `backend\app\schemas\api.py`

Expected touch:

- none

Only modify this file if a repo-confirmed blocker proves schema reuse impossible.

### 2.3 Retrieval Read Service

Expected new file:

- `backend\app\services\aps_retrieval_plane_read.py`

Responsibilities:

- list retrieval rows in the public content-units shape
- search retrieval rows in the public content-search shape
- preserve current ordering and token semantics
- expose explicit fail-closed behavior for missing retrieval scope

### 2.4 Existing Retrieval Services

Allowed modified files if useful:

- `backend\app\services\aps_retrieval_plane_contract.py`
- `backend\app\services\aps_retrieval_plane.py`
- `backend\app\services\aps_retrieval_plane_validation.py`

Responsibilities:

- only additive helpers needed to support the new read service
- no rebuild-orchestration expansion
- no contract broadening beyond this slice

### 2.5 Test Layer

Expected new files:

- `backend\tests\test_aps_retrieval_plane_read.py`
- `backend\tests\test_aps_retrieval_plane_operator_api.py`

Responsibilities:

- retrieval read list parity
- retrieval search parity
- empty retrieval fail-closed behavior
- route behavior for the operator-only endpoints

## 3. Explicitly Unwanted Touches

The following files should remain untouched unless a repo-confirmed blocker requires otherwise:

- `backend\main.py`
- `backend\app\review_ui\*`
- `backend\app\api\review_nrc_aps.py`
- `backend\app\services\review_nrc_aps_*`

If touching any of those becomes necessary, stop and explain the blocker first.

## 4. Tech-Debt Guardrails

### 4.1 No Dual-Behavior Hidden Behind Public Routes

Do not add a flag, header, or hidden switch to the current public content-search or content-units endpoints.

Reason:

- that creates hidden cutover debt on the same route
- it weakens comparability between current and retrieval paths

### 4.2 No Silent Canonical Fallback

If retrieval rows are missing for the requested run, the operator-only retrieval path must fail closed.

Do not silently execute the canonical join path and pretend the retrieval plane is ready.

### 4.3 No Public Contract Widening

This slice is about read-path comparison, not contract redesign.

Reuse the current request/response shapes and keep any operator distinction in the route path only.
