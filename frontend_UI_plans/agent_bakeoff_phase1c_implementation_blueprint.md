# Agent Bake-Off Implementation Blueprint: APS Tier1 Retrieval Plane Phase1C

## 1. Purpose

This document freezes the repo-fit file and module ownership plan for the validate-only public cutover-proof slice.

## 2. Expected File Ownership

### 2.1 Operator Entrypoint

Expected modified file:

- `project6.ps1`

Responsibilities:

- add `validate-nrc-aps-retrieval-cutover` to the action set
- resolve and invoke one thin tool wrapper
- keep existing actions unchanged

### 2.2 Tool Layer

Expected new file:

- `tools\nrc_aps_retrieval_cutover_gate.py`

Responsibilities:

- remain a thin wrapper into backend service code
- not own business logic
- behave like the repo's existing `*_gate.py` entrypoints

### 2.3 Service Layer

Expected new file:

- `backend\app\services\aps_retrieval_plane_cutover_validation.py`

Responsibilities:

- compare canonical public read behavior to retrieval-plane behavior
- normalize the comparison into explicit result categories
- fail closed on empty runtime
- fail closed on missing or partial retrieval materialization

Allowed modified files if a small helper extraction is needed:

- `backend\app\services\aps_retrieval_plane_read.py`
- `backend\app\services\aps_retrieval_plane_validation.py`

### 2.4 API Layer

Expected touch:

- none

Do not modify `backend\app\api\router.py` in this round unless a repo-confirmed blocker proves the current public-route behavior cannot be validated without it.

### 2.5 Schema Layer

Expected touch:

- none

Reuse the current public request/response semantics by driving service-level comparison over the existing shapes.

### 2.6 Test Layer

Expected new files:

- `backend\tests\test_aps_retrieval_plane_cutover_validation.py`
- `backend\tests\test_aps_retrieval_plane_cutover_gate.py`

Responsibilities:

- validate-only pass case for run-scoped list and search
- mismatch reporting for fields/order
- empty-runtime fail-closed
- missing/partial retrieval fail-closed
- gate wrapper behavior

## 3. Explicitly Unwanted Touches

The following files should remain untouched unless a repo-confirmed blocker requires otherwise:

- `backend\app\api\router.py`
- `backend\app\schemas\api.py`
- `backend\main.py`
- `backend\app\review_ui\*`
- `backend\app\api\review_nrc_aps.py`
- `backend\app\services\review_nrc_aps_*`

## 4. Tech-Debt Guardrails

### 4.1 No Hidden Live Cutover

Do not add:

- a header switch on the existing public routes
- a query-string switch on the existing public routes
- a config flag that silently changes public route behavior in this slice

### 4.2 No Third Live Read Path

Do not add another HTTP route family for this round.

Phase1B already created the operator comparison route. Phase1C should add proof evidence, not another live branch.

### 4.3 No Report-Refresh Detour

Do not widen this slice into checked-in report refresh under `tests\reports\`.

Use temp or ephemeral output for proof execution if a report path is needed during validation.
