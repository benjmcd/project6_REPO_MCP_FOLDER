# PageEvidence Rollback and Change-Control Guardrails

## Purpose

Freeze the rollback and change-control rules for a PageEvidence strengthening lane so implementation remains reversible, comprehensible, and non-fragile.

This document exists because strengthening work may touch:

- core evidence artifact shape
- candidate projection placement
- admitted Candidate A behavior
- pinned workbench artifacts
- hidden-consumer compatibility assumptions

Without explicit rollback rules, the lane risks becoming harder to reason about than the problem it is trying to solve.

---

## Core rollback principle

The strengthening lane must be implementable in a way that allows the repo to retreat cleanly to the current admitted/stateful baseline if the lane fails validation or produces unacceptable disagreement patterns.

Interpretation rule:

- separation/refactor work should be reversible
- behavior-changing recalibration should be explicitly isolatable
- artifact/version changes should not destroy historical evidence meaning

---

## Required rollback-friendly implementation properties

1. projection separation should be introducible without forcing broad downstream rewrites
2. historical workbench artifacts must remain interpretable
3. admitted Candidate A behavior changes, if any, must be isolatable from substrate-only refactor changes
4. additive evidence fields should be removable without corrupting historical artifacts
5. new helper modules should remain narrow and easily removable if the lane is abandoned

---

## Change-control rules

### Rule 1 — separate refactor commits from behavior commits

If the lane includes both:
- substrate refactor
- and behavior-changing Candidate A recalibration

then those changes should not be conceptually or evidentially collapsed into one undifferentiated implementation step.

### Rule 2 — preserve historical artifact meaning

No historical pinned artifact should become misleading because a strengthened implementation silently changes how readers are expected to interpret old fields.

### Rule 3 — preserve current-state explainability

At any point during implementation, it should remain explainable:
- what the current admitted Candidate A behavior is
- what the strengthened proposed behavior is
- and whether they differ materially

### Rule 4 — prefer additive transitions over destructive rewrites

When practical:
- add richer fields before deleting old ones
- add compatibility handling before removing legacy assumptions
- version artifacts rather than overwriting semantic meaning

---

## Minimum rollback checkpoints

The implementation record should be able to answer these checkpoints explicitly:

1. Can the repo keep the strengthened substrate while abandoning the strengthened projection?
2. Can the repo keep the historical workbench artifacts untouched if a new schema/version is introduced?
3. Can the repo abandon a Lane Class B recalibration while keeping Lane Class A substrate improvements?
4. Can the repo explain which changes affected runtime behavior and which did not?

If any answer is effectively “no,” the lane is too entangled and should be simplified.

---

## Default recommendation

Prefer the following order for implementation and commit structure:

1. cleanup/resource-hygiene changes
2. extraction/projection separation
3. additive internal evidence-field changes
4. evaluation/reporting improvements
5. only then, if justified, Candidate A projection recalibration

This order minimizes fragility and maximizes reversibility.

---

## Result

The strengthening lane now has explicit rollback and change-control guardrails, helping ensure that implementation stays modular, auditable, and reversible rather than entangled and fragile.


## Relation to pass sequencing

Rollback and change-control assumptions depend on strict pass sequencing.
Refactor-only passes should remain independently revertible from behavior-changing passes, and artifact/schema compatibility work should remain independently revertible from both where possible.
