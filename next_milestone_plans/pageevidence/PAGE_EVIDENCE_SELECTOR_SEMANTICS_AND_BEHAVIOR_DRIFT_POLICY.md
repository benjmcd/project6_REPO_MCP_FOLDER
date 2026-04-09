# PageEvidence Selector Semantics and Behavior-Drift Policy

## Purpose

Freeze the exact policy for deciding when a PageEvidence strengthening lane is:

- behavior-preserving enough to remain within the current admitted Candidate A selector semantics
- versus behavior-changing enough that explicit amendment, re-approval, or a new selector/version must be considered

This document exists because `candidate_a_page_evidence_v1` is already an admitted selector value.
A strengthening lane must therefore not silently change what that admitted selector means.

---

## Current live anchor

The repo currently preserves exactly:

- `baseline`
- `candidate_a_page_evidence_v1`

All other non-`baseline` values fail closed to `baseline`, and review/runtime visibility likewise treats only the admitted Candidate A value as baseline-visible operationally.

This means `candidate_a_page_evidence_v1` is not just an experiment label.
It is a currently admitted runtime selector with already-frozen approval and implementation history.

---

## Interpretation note

Within this policy, **lane classes** classify the overall strengthening lane. They are distinct from the **step classes** used in the blast-radius/topology document for per-step control and rollback analysis.

---

## Pack lane posture

This separate pack is written for:

- **Lane Class A only** within this pack's prepared strengthening scope
- **Lane Class B only as later scope by separate explicit freeze**

That means this policy still defines Lane Class B so the boundary is clear, but the prepared implementation path in this pack should remain Class A unless explicitly reclassified later.

---

## Exact problem this policy solves

A PageEvidence strengthening lane may improve the substrate without changing admitted Candidate A behavior materially.

But if the lane changes:

- how Candidate A decides visual significance
- which pages become preserve-eligible
- or the practical meaning of `candidate_a_page_evidence_v1`

then the lane is no longer a simple substrate refinement.
It becomes an admitted-behavior amendment problem.

This policy exists to prevent silent selector-semantic drift.

---

## Lane-class definitions

### Lane Class A — behavior-preserving substrate strengthening

A strengthening lane is Lane Class A if:

1. the core PageEvidence substrate changes
2. Candidate A projection remains behavior-equivalent or materially immaterial
3. any behavior differences are incidental, low-impact, and explicitly shown to be non-material under the evaluation/disagreement matrix

Examples:

- extracting the projection logic into a separate helper while preserving output behavior
- moving candidate identity out of the core evidence layer
- adding richer evidence fields not used by current admitted projection logic
- cleanup / lifecycle hardening that does not alter admitted decisions

### Lane Class B — behavior-changing Candidate A recalibration

A strengthening lane is Lane Class B if it materially changes:

- which pages Candidate A projects as visual
- which pages Candidate A makes preserve-eligible in the integrated owner path
- or the practical meaning of `candidate_a_page_evidence_v1`

Examples:

- tightening thresholds such that representative disagreement patterns change materially
- suppressing previously visual pages due to decorative-drawing logic
- introducing dominant-region rules that materially alter preserve decisions
- changing the candidate-policy rule in a way that affects accepted runtime outputs

---

## Selector rule

The current agreed selector rule is:

- the same admitted selector may remain in place **only if representative behavior stays materially equivalent**
- if representative behavior does **not** stay materially equivalent, explicit amendment or new-version handling is required

This is the governing rule for this pack.

---

## Materiality test

Under the current pack posture, treat the following as material by default:

1. any representative-fixture per-page projection change that alters preserve-eligibility or admitted visual-page decisions
2. any document-level collapse from mixed/text-heavy to all-visual or near-all-visual on representative fixtures
3. any change that alters the admitted Candidate A output on accepted behavior anchors without explicit approval

Regression-only fixtures may drift only with written justification.

A threshold/percentage-based materiality rule is a possible later evolution, but is not the current policy.

---

## Allowed actions for Class A

If the lane is Class A, the current admitted selector value may remain unchanged **only if**:

- the implementation record explicitly states that the lane was classified as Class A
- the Lane Class A equivalence gate is satisfied
- no new selector/version is needed for accurate interpretation
- no representative-fixture material drift is observed

---

## Required actions for Class B

If the lane is Class B, the lane must not proceed as a silent substrate-refinement lane.

At least one explicit handling path must be chosen:

### Path 1 — explicit amendment to current admitted-target meaning

This path is allowed only if the repo owner intends to treat the strengthened Candidate A behavior as the rightful continuation of the already-admitted selector.

Required evidence:

- explicit statement that admitted behavior is being amended
- explicit comparison between:
  - baseline
  - current admitted Candidate A
  - proposed strengthened Candidate A
- explicit decision that semantic drift of the existing selector is acceptable

### Path 2 — new selector/value/version

This path is required if the behavior drift is significant enough that reusing `candidate_a_page_evidence_v1` would be misleading.

Required outputs:

- new exact selector value/version proposal
- explicit approval path before integrated runtime admission
- existing admitted selector remains unchanged unless separately deprecated later

---

## Default recommendation

Under the current pack posture:

- remain Lane Class A
- do not silently reinterpret the existing selector
- prefer explicit amendment or a new selector/version over ambiguous semantic drift if Lane Class B is ever opened later

This is the safer default.

---

## Required evaluation posture when behavior may change

If materiality is uncertain or Lane Class B is being considered later, comparison must include:

1. baseline
2. current admitted Candidate A
3. proposed strengthened Candidate A

Comparison against baseline alone is insufficient once Candidate A is already admitted.

---

## Required implementation-record fields

Any strengthening implementation record must explicitly include:

- chosen lane class
- justification for that classification
- whether current selector semantics were preserved
- whether a new selector/version was required
- what evidence supported the determination

---

## Result

The repo now has an explicit policy preventing silent semantic drift of the admitted Candidate A selector during PageEvidence strengthening work.
