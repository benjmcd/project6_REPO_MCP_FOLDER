# Agent Bake-Off Validation Plan: APS Tier1 Retrieval Plane Phase1C

## 1. Purpose

This document defines the minimum validation bar for the validate-only public cutover-proof slice.

## 2. Validation Principles

- validate-only actions remain validate-only
- validation must fail closed on empty runtime
- validation must fail closed when retrieval rows are absent or partial for a required run scope
- validation must not seed or generate business artifacts
- canonical APS truth remains the authority for parity comparison
- current public endpoint behavior must remain unchanged
- use isolated runtime state for tests and proof whenever possible
- do not rely on shared checked-in SQLite runtime state such as `backend\method_aware.db`

## 3. Required Validation Areas

### 3.1 Run-Scoped Content-Units Proof

Must prove:

- canonical public `content-units` and retrieval-plane `content-units` match in shape, values, and order for the same run after retrieval rebuild

### 3.2 Run-Scoped Content-Search Proof

Must prove:

- canonical public `content-search` and retrieval-plane `content-search` match in shape, values, and order for the same run-scoped query after retrieval rebuild

### 3.3 Fail-Closed Proof

Must prove:

- empty runtime fails closed
- absent retrieval rows for a non-empty run fail closed
- partial retrieval materialization for a non-empty run fails closed

### 3.4 Public Path Non-Regression

Must prove:

- Phase1C does not alter the current public route behavior by default

### 3.5 Review UI Guardrail

If the submission touches shared code with plausible review UI impact, rerun the focused review UI regression suite.

## 4. Required Commands

At minimum, the submission should run:

```powershell
python -m pytest tests\test_aps_retrieval_plane_cutover_validation.py tests\test_aps_retrieval_plane_cutover_gate.py
```

The focused Phase1C tests should use isolated in-memory or temp-database state and explicitly rebuild retrieval rows inside test setup.

The submission must also run one direct gate invocation against isolated state. If the implementation adds `project6.ps1` support as required, the submission should also state whether it executed the PowerShell action itself or only the thin Python gate wrapper.

If `project6.ps1` is touched, the submission must explicitly state:

- whether the new action was executed
- against what isolated runtime shape
- whether any temp output path was used

## 5. Failure Conditions

This slice is inadequately validated if:

- parity is asserted without direct gate or service tests
- the gate silently falls back when retrieval rows are absent or partial
- the slice alters the current public routes
- the slice introduces a hidden cutover switch
- proof depends on shared checked-in runtime state
