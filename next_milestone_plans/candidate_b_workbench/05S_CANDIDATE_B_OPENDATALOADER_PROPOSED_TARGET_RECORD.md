
# 05S — Candidate B OpenDataLoader Proposed Target Record

## Purpose

Record the exact v1 identity of Candidate B without implying runtime admission.

Scope note:
- this target record freezes Candidate B identity for the original workbench comparator posture
- it does not prevent a later bundle-scoped inspection surface from being added
- it still forbids treating Candidate B as a normal admitted runtime in the first inspection pass

---

## Candidate B v1 record

### Identifier
`candidate_b_opendataloader_workbench_v1`

### Status
- workbench-only
- non-admitted
- non-default
- tests/report comparator only

### Runtime/invocation posture
- Python wrapper invocation only
- local Java runtime required
- no hybrid
- no service-layer integration

### Package pin
- `opendataloader-pdf==2.0.0`

### Corpus anchor
- current lower-layer manifest-driven NRC APS corpus

### Primary comparison target
- current live lower-layer baseline outputs/invariants

### Secondary comparison target
- Candidate A artifacts only if explicitly frozen and supplied

### Explicit non-goals
- no selector admission
- no endpoint changes
- no review/runtime changes
- no owner-path replacement
- no hybrid/docling widening

---

## Interpretation

This target record exists to freeze meaning.
It does not authorize runtime integration.
It also does not block the separately reopened bundle-scoped `Candidate B Trace` follow-on.


---
