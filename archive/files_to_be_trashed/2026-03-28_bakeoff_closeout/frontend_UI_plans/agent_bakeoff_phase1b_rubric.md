# Agent Bake-Off Rubric: APS Tier1 Retrieval Plane Phase1B

## Scoring Categories

### 1. Scope Fidelity

High score only if the submission:

- implements the exact operator-only retrieval read slice
- avoids default cutover
- avoids review UI work
- avoids contract widening

### 2. Repo Fit

High score only if the submission:

- touches the narrow expected files
- reuses current API schemas
- does not invent a separate framework or orchestration layer

### 3. Retrieval Correctness

High score only if the submission:

- reads from the retrieval plane, not canonical joins
- preserves current list and search ordering semantics
- preserves linkage-authoritative diagnostics behavior

### 4. Fail-Closed Safety

High score only if the submission:

- fails closed when retrieval rows are absent for a required scope
- does not silently fall back to canonical APS reads on the operator retrieval path

### 5. Parity Evidence

High score only if the submission:

- proves parity between retrieval and canonical list or search behavior after rebuild
- reports concrete commands and results

### 6. Tech-Debt Discipline

High score only if the submission:

- avoids hidden dual-route flag debt
- calls out any new debt explicitly
- keeps the operator-only distinction obvious
