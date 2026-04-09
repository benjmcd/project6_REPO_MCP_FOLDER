# PageEvidence Strengthening Roadmap and Decision Notes

## Purpose

Provide one consolidated roadmap for the PageEvidence strengthening effort so the next moves, pass order, decision gates, escalation triggers, and post-pass branching do not need to be reconstructed across multiple docs.

This roadmap is subordinate to the execution packet and selector-semantics policy.
It does not widen scope beyond what those docs allow.

---

## Pack-prepared roadmap posture

This roadmap is frozen to the following pack-local decisions:

1. **Lane Class A only within this pack's prepared strengthening scope**
2. **Lane Class B is later scope only by separate explicit freeze**
3. **Representative fixtures are binding for Lane Class A equivalence**
4. **Regression-only drift may occur only with written justification**
5. **A threshold/percentage-based materiality rule is possible later, but not part of the current lane**
6. **Passes 1-4 are the only prepared passes in this pack**
7. **The first lane should avoid touching `nrc_aps_document_processing.py`; analysis against a non-authoritative scratch copy is acceptable if useful, but production-file edits remain escalation-only**
8. **Strengthened artifacts coexist with the current pinned Candidate A artifact; the old artifact remains historically authoritative unless later explicitly superseded**

---

## Decision gate 0 — Choose the lane class before code starts

Exactly one of the following lane classes must be chosen before implementation:

### Lane Class A — substrate strengthening / no material Candidate A behavior drift

Meaning:

- improve PageEvidence as shared deterministic evidence infrastructure
- preserve current admitted Candidate A behavior materially
- do not change selector meaning in practice

Current pack recommendation:

- **Lane Class A is the only prepared lane in this pack**

### Lane Class B — Candidate A recalibration / material admitted behavior drift allowed

Meaning:

- alter what the admitted Candidate A path actually does materially
- potentially require selector-semantics amendment or new-version handling

Current pack recommendation:

- **Not prepared in this pack**
- only later scope by separate explicit freeze

If uncertainty exists, default to **Lane Class A**.

---

## Decision gate 1 — Truth re-establishment first

Re-establish live repo truth directly before code work starts.

Required actions:

1. re-read the live source files
2. re-check representative fixtures and pinned artifacts
3. confirm authority ordering remains explicit

If truth re-establishment is unclear, implementation should stop.

---

## Roadmap phases

### Phase 1 — truth re-establishment and authority alignment

Goals:
- re-read the actual live source files before editing
- confirm the current PageEvidence service / runner / Candidate A seam-local consumer shape
- confirm hidden-consumer surfaces have not drifted materially since the planning pack was drafted
- confirm the pinned workbench artifact is still the canonical before-state reference

Exit condition:
- source-of-truth assumptions still hold, or new drift is explicitly recorded before implementation begins

### Phase 2 — Lane Class A substrate strengthening

Default subpasses:

#### Pass 1
- cleanup and lifecycle hardening
- explicit `fitz` close / cleanup semantics
- no artifact meaning change
- no admitted behavior drift
- no production touch to `nrc_aps_document_processing.py`

#### Pass 2
- shared evidence / candidate projection separation
- compatibility bridge if required
- preserve current admitted Candidate A behavior
- no production touch to `nrc_aps_document_processing.py` unless a separate escalation is approved

#### Pass 3
- additive internal evidence-field enrichment
- only fields frozen in the field-definition register:
  - `largest_image_bbox_ratio`
  - `largest_drawing_bbox_ratio`
  - `dominant_visual_region_present`
  - `text_visual_overlap_ratio`
  - `meaningful_visual_region_count` (optional)
- no consumption by admitted Candidate A path unless separately justified

#### Pass 4
- evaluation / disagreement expansion
- stronger summaries
- borderline-page visibility
- baseline vs current admitted Candidate A checks

Exit condition:
- shared deterministic evidence extractor exists
- projection is separable
- retained-default posture unchanged
- no hidden-consumer drift
- no representative-fixture material drift
- any regression-only drift is explicitly justified

### Phase 3 — optional Lane Class B recalibration

Not prepared under the current pack posture.

This phase may be opened only by a separate future freeze.

---

## Decision gates between phases/passes

### Gate A — after truth re-establishment
Question:
- Are live truth surfaces, pack boundaries, and authority ordering clear enough to begin implementation planning?

If no:
- stop before implementation

### Gate B — before Pass 1
Question:
- Do the prepared Lane Class A pass boundaries still fit the re-established live repo truth?

If no:
- update the pack or stop

### Gate C — before Pass 2
Question:
- Can evidence/projection separation be done without touching the admitted Candidate A behavior?

If yes:
- remain Lane Class A
If no:
- stop and prepare a future separate freeze rather than silently drifting toward Lane Class B

### Gate D — before Pass 3
Question:
- Are the new internal evidence fields fully defined and compatibility-safe?

If no:
- stop until the field-definition register is tightened

### Gate E — before Pass 4
Question:
- Is the disagreement/evaluation output sufficient to detect borderline and representative-fixture drift?

If no:
- strengthen evaluation before proceeding

---

## Post-pass branching options

After a successful Lane Class A pass, only the following next moves are justified:

1. **Stop and hold**
   - strengthened substrate in place
   - no further PageEvidence action for current horizon

2. **Open a bounded future Lane Class B recalibration**
   - only by separate explicit freeze

3. **Open a later candidate-neutral comparison planning lane**
   - only if separately frozen
   - not implied by substrate strengthening alone

4. **Open a broader program-amendment lane**
   - only if the project truly intends to move beyond the current baseline-default runtime posture

---

## Escalation triggers

The following automatically require escalation review:

1. touching `backend/app/services/nrc_aps_document_processing.py` in a production-relevant way
2. changing the meaning of the currently admitted selector value
3. changing workbench artifact meaning without explicit schema/artifact compatibility handling
4. requiring hidden-consumer file changes outside the default owner set
5. introducing new dependencies beyond the frozen dependency posture for this lane
6. changing representative-fixture outcomes in a way that is not explicitly classified as acceptable drift

---

## Validation order

### Lane Class A minimum order
1. service/projection tests
2. runner/report tests
3. baseline-compatibility bundle
4. hidden-consumer compatibility checklist
5. artifact compatibility checks
6. disagreement/evaluation outputs

Lane Class B validation is out of current scope.

---

## Rollback checkpoints

Recommended rollback anchors:

1. post-truth-re-establishment, pre-code
2. post-cleanup, pre-separation
3. post-separation, pre-field-enrichment
4. post-field-enrichment, pre-evaluation expansion

---

## Result

This roadmap now gives the lane a single explicit execution narrative: re-establish live truth first, remain Lane Class A only, prepare Passes 1-4 only, keep representative-fixture equivalence binding, allow regression-only drift only by written justification, and defer Lane Class B until separately frozen.
