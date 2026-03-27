# Agent Bake-Off Validation Plan: APS Tier1 Retrieval Plane Phase1B

## 1. Purpose

This document defines the minimum validation bar for the operator-only retrieval read-path slice.

## 2. Validation Principles

- validate-only actions remain validate-only
- validation must fail closed on empty runtime or empty retrieval scope where rows are required
- validation must not seed or generate business artifacts
- canonical APS truth remains the authority for parity comparison
- current public endpoint behavior must remain unchanged

## 3. Required Validation Areas

### 3.1 Retrieval List Parity

Must prove:

- after retrieval rebuild, operator-only retrieval list returns the same item fields and order as the current canonical run-scoped content-units path for the same run

### 3.2 Retrieval Search Parity

Must prove:

- after retrieval rebuild, operator-only retrieval search returns the same item fields and order as the current canonical content-search path for the same query and run scope

### 3.3 Fail-Closed Retrieval Empty Scope

Must prove:

- if canonical APS rows exist for a run but retrieval rows are absent, the operator-only retrieval path fails closed instead of falling back silently

### 3.4 Public Path Non-Regression

Must prove:

- existing public content-search route still uses the canonical path
- existing public run content-units route still uses the canonical path

### 3.5 Review UI Guardrail

If the submission touches shared code with plausible review UI impact, rerun the focused review UI regression suite.

## 4. Required Commands

At minimum, the submission should run the focused Phase1B tests.

If `router.py` is touched, the submission must also state whether it reran:

```powershell
python -m pytest tests\test_review_nrc_aps_api.py tests\test_review_nrc_aps_catalog.py tests\test_review_nrc_aps_details.py tests\test_review_nrc_aps_graph.py tests\test_review_nrc_aps_page.py tests\test_review_nrc_aps_tree.py
```

If that review-UI suite is not run, the submission must explicitly justify why the touch was isolated enough not to affect it.

## 5. Failure Conditions

This slice is inadequately validated if:

- retrieval parity is asserted without actual operator-route or read-service tests
- retrieval empty-scope behavior silently falls back to canonical APS reads
- public content-search or content-units behavior changes without explicit disclosure
- response ordering semantics drift from the frozen rules
