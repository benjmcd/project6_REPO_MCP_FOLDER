# Agent Bake-Off Rubric: APS Tier1 Retrieval Plane Phase1D

Score each submission against the same criteria.

## 1. Spec Fidelity

- did it stay within Phase1D public run-scoped cutover scope
- did it avoid broadening into omitted-`run_id` redesign or hidden switches

## 2. Repo Fit

- does it keep the cutover centered in the existing router plus retrieval-read path
- does it avoid unnecessary tool, schema, or model churn

## 3. Public Contract Preservation

- did it preserve the current public request and response schemas
- did it preserve deterministic ordering for the proven run-scoped surfaces

## 4. Fail-Closed Correctness

- does it fail closed on absent retrieval rows
- does it fail closed on partial retrieval materialization
- does it avoid silent fallback for cutover-eligible run-scoped requests

## 5. Cutover Discipline

- did it cut over only the proven run-scoped public surfaces
- did it leave omitted-`run_id` search unchanged
- did it leave operator routes unchanged

## 6. Test Quality

- are isolated public-route tests present
- was the existing cutover proof rerun
- was the review UI regression suite rerun because `router.py` changed

## 7. Tech-Debt Control

- did it reduce dual-read debt without creating hidden compatibility debt
- did it explicitly surface remaining deferred debt
