# Agent Bake-Off Rubric: APS Tier1 Retrieval Plane Phase1C

Score each submission against the same criteria.

## 1. Spec Fidelity

- did it stay within Phase1C validate-only cutover-proof scope
- did it avoid default cutover and hidden-route switching

## 2. Repo Fit

- does it follow the repo's existing `project6.ps1` plus `tools\*_gate.py` pattern
- does it keep public/API/schema surfaces narrow

## 3. Fail-Closed Correctness

- does it fail closed on empty runtime
- does it fail closed on missing or partial retrieval materialization

## 4. Parity Value

- does it compare the exact public-surface semantics that matter for a future cutover decision
- are mismatch categories explicit and actionable

## 5. Test Quality

- are isolated service/gate tests present
- do tests cover pass and fail paths

## 6. Tech-Debt Control

- did it avoid introducing a third live path
- did it avoid hidden flags on the public routes
- did it explicitly surface remaining cutover debt
