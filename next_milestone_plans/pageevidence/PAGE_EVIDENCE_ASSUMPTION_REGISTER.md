# PageEvidence Assumption Register

## Purpose

Make implementation-relevant assumptions explicit so the strengthening lane does not silently depend on untested beliefs.

This register is optional but recommended for high-rigor review.

---

## Assumptions

### A1 — PyMuPDF-derived geometry/count signals are stable enough for current strengthening work
- why it matters: the lane is intentionally avoiding new dependencies and broader visual models
- risk if false: the strengthened substrate may still be too noisy for reliable calibration
- implication if false: broader dependency or analyzer reconsideration may be required in a later explicit lane

### A2 — Hidden-consumer compatibility can be preserved without outward contract widening
- why it matters: the lane is explicitly trying to stay internal-first and non-disruptive
- risk if false: downstream retrieval/review/report surfaces may require explicit compatibility bridges or widening
- implication if false: the lane escalates into stronger schema/reader-change territory

### A3 — Current admitted Candidate A behavior is sufficiently understood to distinguish refactor from behavior drift
- why it matters: selector-semantics control depends on knowing when admitted behavior has changed materially
- risk if false: implementation may under-classify behavior-changing work as harmless refactor
- implication if false: stricter comparison evidence and possibly broader amendment handling are required

### A4 — The canonical fixture corpus is representative enough for gate decisions at this stage
- why it matters: quantitative materiality judgments and disagreement analysis depend on the corpus
- risk if false: false-positive or false-negative patterns may be missed
- implication if false: corpus policy must expand before stronger claims are made

### A5 — Strengthening PageEvidence does not itself authorize broader runtime/program re-expansion
- why it matters: repo governance currently holds a retained-default stable-hold posture
- risk if false: implementers may infer Candidate B or broader subsystem work is implicitly opened
- implication if false: program-level control drift occurs
