# PageEvidence Pass Sequencing and Commit Choreography

## Purpose

Freeze the recommended implementation order so the strengthening lane remains simple, revertible, and non-fragile.

This document exists because the lane becomes much harder to review and rollback if substrate refactor, artifact compatibility work, evaluation changes, and behavior recalibration are mixed together.

---

## Pack sequencing posture

Within this separate pack, the prepared sequencing posture is:

- **Lane Class A only**
- **Passes 1-4 only**
- **Pass 5 is out of current scope and would require a separate future freeze**
- **`nrc_aps_document_processing.py` remains no-touch in Pass 1 and should stay no-touch in later passes unless an explicit escalation is approved**
- **if analysis against a copy of `nrc_aps_document_processing.py` is useful, that copy must remain outside `backend`, non-authoritative, and non-runtime**

---

## Recommended pass order

### Pass 1 — lifecycle hardening and in-file extraction/projection separation

Goals:
- explicit `fitz` document close / cleanup semantics
- separate shared evidence extraction from candidate projection inside the existing service file when that can remain fully behavior-preserving
- no behavior drift
- no artifact meaning change
- no production touch to `nrc_aps_document_processing.py`

Preferred commit properties:
- isolated
- trivially revertible
- Step Class `R` only when the split can stay inside the existing owner files with no outward compatibility work

### Pass 2 — compatibility bridge / helper extraction if Pass 1 proves insufficient

Goals:
- complete evidence/projection separation only if Pass 1 cannot keep the split clean enough inside the existing service file
- preserve current admitted Candidate A behavior
- add temporary compatibility bridge only if required
- still no production touch to `nrc_aps_document_processing.py` unless escalation is explicitly approved

Skip this pass entirely if Pass 1 already achieved the split cleanly and the required Lane Class A validation remains green.
If later work is proposed after that hold state, it must begin from a new explicitly frozen objective rather than from this prepared sequencing note alone.

Preferred commit properties:
- isolated from behavior recalibration
- may span Step Classes `R` and `C`

### Pass 3 — additive internal evidence-field enrichment

Goals:
- add only the pre-approved fixed field set:
  - `largest_image_bbox_ratio`
  - `largest_drawing_bbox_ratio`
  - `dominant_visual_region_present`
  - `text_visual_overlap_ratio`
  - `meaningful_visual_region_count` (optional)
- do not consume them in admitted Candidate A logic

Preferred commit properties:
- additive and revertible
- Step Class `R` by default
- any drift pressure should stop the pass and trigger lane re-evaluation

### Pass 4 — evaluation / disagreement expansion

Goals:
- produce stronger summaries
- make borderline and disagreement cases explicit
- keep Lane Class A comparators centered on:
  - current admitted Candidate A
  - strengthened Candidate A
- baseline context may still be included, but Lane Class B-style tri-comparison is not part of the current pack-prepared lane

Preferred commit properties:
- evaluation-only where possible
- Step Classes `R` / `C`

### Pass 5 - behavior recalibration (not prepared in this pack)

Status:
- out of scope for the current pack posture
- requires a separate future freeze

---

## Commit choreography rules

1. Do not mix cleanup-only changes with behavior-changing changes in one commit.
2. Do not mix compatibility-bridge changes with broad evaluation rewrites in one commit unless the blast radius is explicitly re-proved.
3. Keep any `nrc_aps_document_processing.py` production edit in its own clearly labeled escalation commit set if it becomes necessary later.
4. Keep rollback targets aligned to passes, not only to the final merged state.
5. Keep the first pass as the smallest, safest, and most trivially revertible change set.

---

## Practical review rule

At review time, each pass should be answerable with one sentence:

- what changed
- what did not change
- what tests prove that claim

If a pass cannot be explained that simply, it is probably too broad.
