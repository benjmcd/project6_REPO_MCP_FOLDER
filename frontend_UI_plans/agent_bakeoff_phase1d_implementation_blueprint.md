# Agent Bake-Off Implementation Blueprint: APS Tier1 Retrieval Plane Phase1D

## 1. Purpose

This document freezes the repo-fit file and module ownership plan for the public run-scoped cutover slice.

## 2. Expected File Ownership

### 2.1 API Layer

Expected modified file:

- `backend\app\api\router.py`

Responsibilities:

- repoint the public run-scoped `content-units` route to the retrieval read service
- repoint the public `content-search` route to the retrieval read service when `payload.run_id` is explicitly present
- leave omitted-`run_id` search on the canonical path
- preserve the existing public response models
- translate retrieval-not-materialized conditions into the same public `409` detail

### 2.2 Retrieval Read Service

Expected modified file only if a narrow helper adjustment is needed:

- `backend\app\services\aps_retrieval_plane_read.py`

Responsibilities:

- remain the single retrieval read authority for the cutover-eligible run-scoped surfaces
- preserve current ordering and field shape
- preserve fail-closed materialization checks

Do not duplicate retrieval ranking or serialization logic in the router.

### 2.3 Cutover Proof Service

Expected touch:

- none by default

Allowed modified file only if a repo-confirmed proof-alignment fix is necessary:

- `backend\app\services\aps_retrieval_plane_cutover_validation.py`

### 2.4 Tool Layer

Expected touch:

- none

Do not modify:

- `project6.ps1`
- `tools\nrc_aps_retrieval_cutover_gate.py`

unless a repo-confirmed blocker proves the existing Phase1C proof surface cannot validate the cutover.

### 2.5 Schema Layer

Expected touch:

- none

Reuse the current public request and response models unchanged.

### 2.6 Test Layer

Expected new or modified files under:

- `backend\tests\`

Responsibilities:

- prove public run-scoped `content-units` cutover
- prove public run-scoped `content-search` cutover
- prove omitted-`run_id` search remains unchanged
- prove fail-closed `409` behavior for absent and partial retrieval materialization
- rerun or preserve the Phase1C proof surface against isolated state
- rerun the focused review UI regression suite because `router.py` changes

## 3. Explicitly Unwanted Touches

The following files should remain untouched unless a repo-confirmed blocker requires otherwise:

- `project6.ps1`
- `tools\nrc_aps_retrieval_cutover_gate.py`
- `backend\app\schemas\api.py`
- `backend\main.py`
- `backend\app\review_ui\*`
- `backend\app\api\review_nrc_aps.py`
- `backend\app\services\review_nrc_aps_*`

## 4. Tech-Debt Guardrails

### 4.1 No Silent Fallback

Do not add:

- canonical fallback inside the public cutover-eligible run-scoped surfaces
- silent downgrade to canonical reads on retrieval absence or partial materialization

### 4.2 No Hidden Dual Semantics

Do not add:

- route headers that switch public behavior
- query-string flags that switch public behavior
- config flags that silently restore canonical routing in this slice

### 4.3 No Omitted-Run Redesign

Do not widen this slice into:

- global search parity redesign
- cross-run retrieval completeness work
- a new mixed routing matrix for every search shape

Leave omitted-`run_id` search explicitly unchanged.
