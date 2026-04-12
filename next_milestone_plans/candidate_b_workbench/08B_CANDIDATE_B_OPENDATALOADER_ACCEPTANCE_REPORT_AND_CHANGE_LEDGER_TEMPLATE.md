
# 08B — Candidate B OpenDataLoader Acceptance Report and Change Ledger Template

## Purpose

Standardize the final implementation record so the outcome is auditable
and does not rely on memory or prose drift.

Use this document as the template for the Candidate B implementation record.

Recommended output:
- `tests/reports/mvvlc_candidate_b_opendataloader_implementation_record_v1.md`

---

## Template

### 1. Repo identity
- branch:
- commit SHA:
- working tree status:
- pack version:
- repo precheck artifact ref:

### 2. Candidate identity
- candidate id:
- candidate role:
- engine family:
- engine mode:
- exact package version:
- exact Java version:
- exact Python version:

### 3. Authority confirmation
- README/status rechecked: yes/no
- authority matrix rechecked: yes/no
- reader path rechecked: yes/no
- Candidate B still non-admitted: yes/no
- retained-`baseline` posture still valid: yes/no

### 4. Changed files
List every changed file by class:

#### 4a. New workbench owner files
- ...

#### 4b. New tests
- ...

#### 4c. New reports/artifacts
- ...

#### 4d. Conditionally modified files
- ...
- justification:
- authority precheck confirming this was allowed:

### 5. Explicitly untouched frozen surfaces
Confirm that none of the following changed:

- integrated owner-path/runtime files
- review/API/schema/model/migration files
- evidence/report/export/package files
- Docker/CI/frontend/e2e surfaces
- original authoritative lower-layer corpus/proof surfaces

### 6. Corpus used
- manifest ref:
- manifest SHA256:
- corpus bucket coverage:
- any explicit addendum used:
- any exclusions:

### 7. Commands executed
Record the exact commands used for:
- preflight
- workbench run
- comparison run
- tests

### 8. Artifacts produced
- workbench report ref + hash
- corpus comparison report ref + hash
- summary ref + hash
- config snapshot ref + hash
- raw-output manifest ref + hash
- warning log ref + hash

### 9. Outcome summary
For each intended win class, record:
- bucket:
- observed result:
- supporting artifact refs:
- divergence labels:

For each limitation class, record:
- limitation:
- observed result:
- supporting artifact refs:

For text-heavy equivalence controls:
- stable / drifted:
- evidence:

### 10. Failures and stops
List every failure/stop encountered, if any:
- failure code:
- affected document(s):
- disposition:

### 11. Final decision
Allowed values only:
- `reject`
- `iterate_as_workbench_only`
- `consider_later_target_definition`

### 12. Rationale for decision
Explain the decision in terms of:
- intended win classes
- stability on controls
- limitation honesty
- frozen-surface discipline
- operational reasonableness

### 13. Explicit non-claims
State explicitly that this run does **not** prove any of the following unless actually proven later:
- runtime admission readiness
- owner-path replacement
- vector-line-art success
- scanned-PDF/OCR success
- hybrid/docling value

### 14. Follow-on actions
List only narrow next actions allowed by the decision.

---

## Change-ledger addendum

The implementation record must include a compact change ledger with:

- file path
- change class (`new`, `modified`)
- component class
- why the change was necessary
- whether the change touched a frozen surface (must be `no`)
- reviewer note

This is what makes the final diff explainable in one pass.

---


---
