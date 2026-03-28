# Agent Bake-Off Scope: APS Tier1 Retrieval Plane Phase1C

## 1. Purpose

This document freezes the next bounded retrieval-plane bake-off slice.

## 2. Slice Name

`Phase1C: Validate-Only Public Cutover Proof Gate`

## 3. In Scope

The implementation must include all of the following.

### 3.1 Validate-Only Proof Service

Add one validate-only proof service that:

- compares canonical public `content-units` behavior to retrieval-plane `content-units` behavior for one run
- compares canonical public `content-search` behavior to retrieval-plane `content-search` behavior for one run-scoped query
- emits explicit result categories for match, mismatch, empty runtime, and retrieval-not-materialized conditions
- preserves current public request semantics while remaining validate-only

### 3.2 Validate Action And Tool Wrapper

Add:

- one thin tool wrapper under `tools\`
- one `project6.ps1` action named `validate-nrc-aps-retrieval-cutover`

The validate action must:

- remain validate-only
- fail closed on empty runtime
- not seed or generate business artifacts
- not flip any public route behavior

### 3.3 Focused Tests

Add focused tests that prove:

- canonical vs retrieval parity passes for run-scoped list
- canonical vs retrieval parity passes for run-scoped search
- field/order mismatches are reported explicitly
- empty runtime fails closed
- partial or absent retrieval materialization fails closed

## 4. Explicitly Deferred

The following are out of scope for Phase1C:

- default public cutover of `content-units` or `content-search`
- hidden flags, headers, or query switches on the existing public routes
- new HTTP routes
- operator route changes
- schema/model/Alembic widening
- review UI changes
- embeddings or vector work
- checked-in report refresh under `tests\reports\`

## 5. Allowed Repo Surface

This slice should normally touch only:

- `project6.ps1`
- `tools\`
- `backend\app\services\aps_retrieval_plane_read.py`
- `backend\app\services\aps_retrieval_plane_validation.py`
- `backend\app\services\aps_retrieval_plane_cutover_validation.py`
- `backend\tests\`

Do not touch:

- `backend\app\api\router.py`
- `backend\app\schemas\api.py`
- `backend\alembic\versions\`
- `backend\app\models\`
- `backend\app\review_ui\*`

unless a repo-confirmed blocker makes that unavoidable. If that happens, stop and explain it instead of broadening scope silently.

## 6. Acceptance Criteria

This slice is adequate only if all of the following are true:

- `project6.ps1` exposes one validate-only `validate-nrc-aps-retrieval-cutover` action
- the validate-only gate proves or rejects readiness for run-scoped `content-units` and `content-search`
- empty runtime fails closed
- absent or partial retrieval materialization fails closed
- mismatch reporting is explicit enough to support a later cutover decision
- current public routes remain unchanged
- no review UI regression is introduced
