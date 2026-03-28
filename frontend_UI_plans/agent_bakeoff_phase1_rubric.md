# Agent Bake-Off Rubric: APS Tier1 Retrieval Plane Phase1A

## 1. Purpose

This rubric scores Jules and Antigravity against the same bounded retrieval-plane slice.

The goal is to compare correctness, scope discipline, and repo-fit execution quality.

## 2. Scoring Model

Recommended scale per category:

- `0` = failed or materially incorrect
- `1` = weak
- `2` = adequate
- `3` = strong
- `4` = excellent

Recommended weighting:

| Category | Weight |
| --- | --- |
| Authority/spec fidelity | 20 |
| Scope discipline | 15 |
| Canonical-truth preservation | 15 |
| Derivation and source-signature correctness | 15 |
| Validate-only parity handling | 10 |
| Test quality | 10 |
| Repo-fit simplicity and tech-debt control | 10 |
| Regression discipline | 5 |

## 3. Category Definitions

### 3.1 Authority/Spec Fidelity

Score how closely the output follows:

- the Phase1 plan
- the bounded Phase1A scope
- the implementation blueprint
- the validation plan

### 3.2 Scope Discipline

Score whether the output stayed within Phase1A.

Low score triggers:

- public read-path work
- API/UI expansion
- embeddings/vector work
- unrelated refactors

### 3.3 Canonical-Truth Preservation

Score whether the implementation keeps APS evidence truth canonical and the retrieval plane clearly derived.

### 3.4 Derivation And Source-Signature Correctness

Score whether:

- derived row identity is coherent
- source-signature logic is explicit
- linkage-authoritative diagnostics semantics are preserved

### 3.5 Validate-Only Parity Handling

Score whether parity comparison:

- is validate-only
- fails closed on empty scope
- surfaces mismatches clearly

### 3.6 Test Quality

Score whether tests are:

- present
- focused
- meaningful
- aligned to the validation plan

### 3.7 Repo-Fit Simplicity And Tech-Debt Control

Score whether the implementation fits the repo without unnecessary platform expansion.

High score requires:

- minimal touched-file surface consistent with the blueprint
- no unnecessary API/UI/framework work
- explicit avoidance of avoidable tech debt in derivation, validation, and future cutover paths

### 3.8 Regression Discipline

Score whether the submission avoids regressing the current verified review UI baseline when shared code is touched.

## 4. Disqualifying Mistakes

Any of these should heavily penalize or disqualify an entry:

- treating retrieval rows as canonical evidence truth
- changing default public read paths
- widening upper APS artifact contracts
- adding UI/API surfaces without a repo-confirmed need
- passing validation on empty runtime/scope
- silently reintroducing document-row diagnostics fallback semantics

## 5. Recommended Review Output

For each agent, produce:

- per-category score
- weighted total
- short strengths summary
- short weaknesses summary
- merge recommendation:
  - accept
  - reject
  - accept only as partial basis
