# PageEvidence Internal Field Definition Register

## Purpose

Freeze the definition contract for any new or strengthened internal evidence fields introduced by the PageEvidence strengthening lane.

This register is decision-bound to a **small fixed set of pre-approved fields for Pass 3 only** within this separate pack. No other new internal fields are prepared for Pass 1-3 unless this register is explicitly updated first or in the same change set.

---

## Current-field note

The current PageEvidence service already emits fields such as:

- `word_count`
- `text_block_count`
- `image_count`
- `drawing_count`
- `text_coverage_ratio`
- `image_coverage_ratio`
- `drawing_coverage_ratio`
- `combined_visual_coverage_ratio`

Any new field must be defined with at least the same level of explicitness.

---

## Decision-bound authorization

### Pass 1
No new internal evidence fields.

### Pass 2
No new internal evidence fields by default; focus on separation and compatibility bridge only.

### Pass 3
Only the following fields are pre-approved for introduction, subject to the Lane Class A equivalence gate and the schema/artifact compatibility policy:

1. `largest_image_bbox_ratio`
2. `largest_drawing_bbox_ratio`
3. `dominant_visual_region_present`
4. `text_visual_overlap_ratio`
5. `meaningful_visual_region_count` (**optional**; may be deferred if derivation criteria are not yet stable enough)

No additional new field is in scope for Pass 3 by default.

---

## Definition template

For each new field, record:

- **field_name**
- **layer** (`shared evidence` or `candidate projection`)
- **meaning**
- **unit / allowed range**
- **derivation rule**
- **nullability / missing-data rule**
- **determinism expectation**
- **compatibility expectation**
- **used by current admitted Candidate A?** (`yes/no`)
- **behavior-drift relevance** (`none/possible/direct`)

---

## Pre-approved Pass 3 field definitions

### 1. `largest_image_bbox_ratio`
- layer: shared evidence
- meaning: area ratio of the largest image-region bounding box relative to total page area
- unit / allowed range: float in `[0.0, 1.0]`
- derivation rule: compute all image-region bounding-box areas using the same deterministic PyMuPDF-derived surface used by the strengthening lane; divide the largest image bbox area by page area
- nullability / missing-data rule: `0.0` if no image region exists or page area is zero
- determinism expectation: deterministic on the same PDF parsing surface
- compatibility expectation: additive internal field only by default
- used by current admitted Candidate A?: no, unless a later explicit behavior-changing lane says otherwise
- behavior-drift relevance: possible

### 2. `largest_drawing_bbox_ratio`
- layer: shared evidence
- meaning: area ratio of the largest drawing-region bounding box relative to total page area
- unit / allowed range: float in `[0.0, 1.0]`
- derivation rule: compute all drawing-region bounding-box areas using the same deterministic PyMuPDF-derived surface used by the strengthening lane; divide the largest drawing bbox area by page area
- nullability / missing-data rule: `0.0` if no drawing region exists or page area is zero
- determinism expectation: deterministic on the same PDF parsing surface
- compatibility expectation: additive internal field only by default
- used by current admitted Candidate A?: no, unless a later explicit behavior-changing lane says otherwise
- behavior-drift relevance: possible

### 3. `dominant_visual_region_present`
- layer: shared evidence
- meaning: boolean signal indicating whether the page contains at least one image or drawing region whose bbox ratio satisfies the lane's frozen dominant-region threshold
- unit / allowed range: boolean
- derivation rule: derived from `largest_image_bbox_ratio` and `largest_drawing_bbox_ratio` against a threshold frozen in the implementation change set; threshold must be explicitly recorded
- nullability / missing-data rule: `false` if page area is zero or no qualifying visual region exists
- determinism expectation: deterministic
- compatibility expectation: additive internal field only by default
- used by current admitted Candidate A?: no, unless a later explicit behavior-changing lane says otherwise
- behavior-drift relevance: possible

### 4. `text_visual_overlap_ratio`
- layer: shared evidence
- meaning: rough ratio describing overlap or close adjacency burden between text-bearing regions and visual regions on the page
- unit / allowed range: float in `[0.0, 1.0]`
- derivation rule: implementation must freeze one deterministic overlap/adjacency convention in the same change set; the convention must be documented explicitly in code/tests if the field is added
- nullability / missing-data rule: `0.0` if no text region or no visual region exists, unless a stronger explicit rule is frozen
- determinism expectation: deterministic under the same geometry interpretation
- compatibility expectation: additive internal field only by default
- used by current admitted Candidate A?: no, unless a later explicit behavior-changing lane says otherwise
- behavior-drift relevance: possible

### 5. `meaningful_visual_region_count` (optional)
- layer: shared evidence
- meaning: count of visual regions above the lane's minimum meaningful-region threshold
- unit / allowed range: non-negative integer
- derivation rule: count image/drawing regions whose bbox ratio is at or above a frozen minimum meaningful-region threshold recorded in the same change set
- nullability / missing-data rule: `0` if none
- determinism expectation: deterministic
- compatibility expectation: additive internal field only by default
- used by current admitted Candidate A?: no, unless a later explicit behavior-changing lane says otherwise
- behavior-drift relevance: possible
- decision note: this field may be deferred if the meaningful-region threshold cannot be frozen clearly enough for Pass 3 without creating ambiguity

---

## Rule

No new internal field should be added informally.
If a field changes behavior interpretation, projection logic, or artifact meaning, update this register first or in the same change set.
