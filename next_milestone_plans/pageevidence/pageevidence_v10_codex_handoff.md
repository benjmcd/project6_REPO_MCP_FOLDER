# PageEvidence v10 Codex Handoff

## Purpose

This document hands off continued work on the standalone PageEvidence planning/control pack.

It summarizes:

- the live repo facts that matter
- what this pack is for
- what decisions are already frozen inside the pack
- where the pack is strong
- where it still needs caution
- what it should not cover
- what to do next

This is not a claim that implementation is complete.

---

## 1. Current live repo facts that matter

The current live runtime facts relevant to this pack are:

- `baseline` remains the current default runtime mode
- `candidate_a_page_evidence_v1` remains the current admitted non-`baseline` value
- `backend/app/services/nrc_aps_page_evidence.py` still fuses shared evidence extraction, candidate identity, and projected-class logic
- the workbench runner and pinned Candidate A workbench artifact still exist and remain the main before-state references
- hidden-consumer downstream surfaces are real and must be treated as compatibility surfaces

Practical consequence:

PageEvidence work must be treated as a bounded strengthening lane, not as permission to widen runtime scope casually.

---

## 2. What this pack is actually for

This pack is the current planning/control layer for strengthening PageEvidence under a narrow, disciplined posture.

Its core idea is:

> PageEvidence should be treated as a shared deterministic evidence extractor, not as the conceptual owner of candidate-policy classification.

The pack is meant to separate those concerns without broadening scope.

---

## 3. Frozen decisions already made in the pack

Unless explicitly reopened later, treat the following as binding pack decisions:

### Lane posture

- **Lane Class A only** is prepared in this pack.
- **Lane Class B** remains future scope only by separate freeze.

Interpretation:
- Lane A = strengthen PageEvidence without materially changing admitted Candidate A behavior.
- Lane B = Candidate A recalibration / behavior change.

### Selector semantics

- Keep the same selector only if representative behavior remains materially equivalent.
- If behavior changes materially, that must escalate into amendment/new-version handling.

### Materiality rule for now

- representative fixtures are binding
- regression-only fixtures may drift only with written justification
- threshold/percentage-based materiality remains deferred

### First-pass field authorization

Allowed fixed first-pass field set:

- `largest_image_bbox_ratio`
- `largest_drawing_bbox_ratio`
- `dominant_visual_region_present`
- `text_visual_overlap_ratio`
- `meaningful_visual_region_count` only as optional/deferable

### `nrc_aps_document_processing.py` posture

- do not touch the production file in Pass 1 unless forced by a narrowly justified compatibility bridge
- analysis-only scratch copies may exist only outside `backend/`
- no committed duplicate production path

### Artifact posture

- strengthened artifacts coexist with the current pinned Candidate A artifact
- the current pinned artifact remains historically authoritative unless later explicitly superseded

### Roadmap posture

- Passes 1-4 are the only prepared passes in this pack
- Lane Class B remains later scope only by separate freeze

---

## 4. What the pack contains

The pack includes:

1. boundary/separation control
2. execution packet
3. selector semantics / behavior-drift policy
4. schema / artifact compatibility policy
5. evaluation and disagreement matrix
6. hidden-consumer compatibility checklist
7. module/component/dependency/touchpoint inventory
8. rollback/change-control guardrails
9. blast-radius / before-after topology
10. file-to-test-to-bundle traceability matrix
11. internal field definition register
12. payload examples
13. pass sequencing / commit choreography
14. roadmap and decision notes
15. assumption register
16. pack activation / working-use plan
17. Lane A equivalence / no-drift gate
18. pass-level allowed file manifest
19. implementation-record template
20. verification report
21. activation / verification checklist
22. operator execution sheet
23. representative fixture lock / canonical subset note

In category terms, the pack is broadly complete.

---

## 5. Strengths of the pack

### A. Correct center of gravity

The pack is aimed at the right problem:

- separate shared evidence extraction from candidate-policy projection
- improve structure without broadening scope
- preserve current admitted Candidate A behavior materially in Lane Class A

### B. Strong governance/control structure

The pack includes the main control surfaces that matter:

- boundary docs
- execution packet
- blast radius
- hidden-consumer checklist
- schema/artifact compatibility
- selector semantics
- rollback guardrails
- traceability matrix
- operator execution sheet
- activation checklist

### C. Good distinction between lane scope and step scope

The pack distinguishes:

- Lane Class A / Lane Class B
- Step Class R / P / C / H

### D. Strong implementation usability

The pack includes:

- operator sheet
- activation plan/checklist
- representative fixture lock
- pass sequencing
- file/test/bundle traceability

That substantially reduces synthesis burden during implementation.

---

## 6. Weaknesses / cautions

The pack is strong, but it is still not implementation proof.

It does not prove:

- code has been changed
- tests passed after changes
- hidden-consumer surfaces remain green after implementation
- Lane A equivalence/no-drift is satisfied in code

It also still depends on a fresh live repo reconnaissance pass before implementation.

---

## 7. What the pack should NOT cover

Do not bloat this pack into:

- a broad visual-understanding subsystem charter
- a general multi-candidate framework design
- a broad external API/endpoints spec
- a long-range product strategy doc
- a new OCR/hybrid/media redesign pack
- a broad schema widening plan for user-facing surfaces

The pack should remain narrowly about:

- shared evidence extraction
- projection separation
- Lane A equivalence / no-drift
- disciplined implementation planning and execution

---

## 8. What still matters before implementation

1. re-read the live repo truth surfaces directly
2. confirm the representative fixture subset explicitly in the implementation loop
3. confirm hidden-consumer compatibility surfaces are still real and unchanged enough for the pack assumptions to hold
4. confirm the current pinned artifact is still the right historical before-state reference

---

## 9. What Codex should do next

### Phase 0 - pack hygiene re-audit

Before using the pack for implementation planning:

1. verify the README inventory still matches the folder
2. verify the verification report still matches the latest pack state
3. make sure the pack still reads as one coherent separate control pack

### Phase 1 - live repo reconnaissance

Reconfirm the source of truth directly from code, fixtures, artifacts, and downstream-consumer surfaces.

### Phase 2 - Lane A implementation planning only

Prepared passes under current pack decisions:

#### Pass 1
- cleanup / explicit close semantics
- evidence/projection separation setup
- no production touch to `nrc_aps_document_processing.py` unless forced

#### Pass 2
- runner/report adaptation
- compatibility bridge work

#### Pass 3
- only the fixed pre-approved field set

#### Pass 4
- disagreement/evaluation expansion

Do not start Lane B under the current pack posture.

### Phase 3 - validation

At minimum:

- PageEvidence service tests
- workbench runner tests
- baseline-compatibility bundle
- representative-subset equivalence checks
- hidden-consumer compatibility review
- artifact compatibility checks

### Phase 4 - stop and reassess

After Passes 1-4, decide whether:

- stable hold is sufficient
- more Lane A refinement is needed
- Lane Class B needs a separate future freeze

---

## 10. Best concise statement for Codex

> Treat the v10 pack as the active standalone PageEvidence planning/control layer. Re-verify the live source-of-truth files before implementation planning, then execute Passes 1-4 only under Lane A while preserving representative-fixture equivalence and avoiding any material Candidate A behavior drift or broader runtime/program widening.

---

## 11. Final determination

### What the pack is good enough for

- constraining a disciplined Lane A implementation lane
- reducing interpretive ambiguity during execution
- serving as the active planning/control pack for this current repo lane

### What it is not yet good enough for by itself

- claiming implementation correctness
- authorizing Lane Class B work
- proving no-drift after code changes

### Bottom line

The planning work is strong enough to proceed.

The next meaningful work is:

1. re-verify live code/artifact/downstream truth surfaces
2. use this pack as the control surface for Lane A
3. validate hard
4. stop before any Lane B drift unless separately frozen
