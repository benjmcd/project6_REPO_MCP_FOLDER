# Agent Bake-Off Validation Plan: APS Tier1 Retrieval Plane Phase1D

## 1. Purpose

This document defines the minimum validation bar for the public run-scoped cutover slice.

## 2. Validation Principles

- public cutover must preserve current request and response schemas
- deterministic ordering must remain intact for the proven run-scoped surfaces
- run-scoped public cutover must fail closed on absent or partial retrieval materialization
- omitted-`run_id` search must remain unchanged
- canonical APS truth remains the authority for parity comparison
- validate-only actions remain validate-only and must not seed or generate artifacts
- use isolated runtime state for tests and proof whenever possible
- do not rely on shared checked-in SQLite runtime state such as `backend\method_aware.db`

## 3. Required Validation Areas

### 3.1 Public Run-Scoped Content-Units Cutover

Must prove:

- the public route now serves retrieval-backed results for run-scoped content-units
- output shape and ordering remain identical for the proven run scope

### 3.2 Public Run-Scoped Content-Search Cutover

Must prove:

- the public route now serves retrieval-backed results when `run_id` is supplied
- output shape and ordering remain identical for the proven run scope

### 3.3 Unchanged Omitted-Run Search

Must prove:

- omitted-`run_id` public search behavior remains on the canonical path
- this slice did not silently widen cutover semantics

### 3.4 Fail-Closed Public Behavior

Must prove:

- absent retrieval rows for a non-empty cutover-eligible run fail closed with `409`
- partial retrieval materialization for a non-empty cutover-eligible run fails closed with `409`

### 3.5 Cutover Proof Recheck

Must prove:

- the existing Phase1C cutover proof still passes on isolated runtime state after the cutover

### 3.6 Review UI Guardrail

Because `router.py` changes in this slice, rerun the focused review UI regression suite.

## 4. Required Commands

At minimum, the submission should run:

```powershell
python -m pytest tests\test_aps_retrieval_plane_read.py tests\test_aps_retrieval_plane_operator_api.py tests\test_aps_retrieval_plane_cutover_validation.py tests\test_aps_retrieval_plane_public_api.py
python -m pytest tests\test_review_nrc_aps_api.py tests\test_review_nrc_aps_catalog.py tests\test_review_nrc_aps_details.py tests\test_review_nrc_aps_graph.py tests\test_review_nrc_aps_page.py tests\test_review_nrc_aps_tree.py
```

The focused Phase1D tests should use isolated in-memory or temp-database state and explicitly rebuild retrieval rows inside test setup.

The submission must also run one direct isolated invocation of the existing Phase1C proof surface after the cutover, using either:

- `tools\nrc_aps_retrieval_cutover_gate.py`
- or the equivalent service entrypoint

The submission must explicitly state:

- whether the direct proof invocation passed
- whether `project6.ps1` was rerun in this slice
- what isolated runtime shape was used

## 5. Failure Conditions

This slice is inadequately validated if:

- public run-scoped cutover is asserted without direct route tests
- omitted-`run_id` search behavior changes without being called out
- the public cutover silently falls back when retrieval rows are absent or partial
- public response shape changes
- router changes are made without rerunning the focused review UI regression suite
