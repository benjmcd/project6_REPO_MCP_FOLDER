# PageEvidence Operator Execution Sheet

## Purpose

Compress the strengthening pack into one short operator-facing execution sheet so the implementation lane can be run with minimal interpretation burden.

Use this sheet together with the full pack, not instead of it.

---

## Pack-prepared lane

- **Lane Class A only**
- Lane Class B remains future scope only by separate freeze

---

## Pack-prepared passes

- Pass 1: cleanup + explicit close/cleanup semantics + evidence/projection separation setup
- Pass 2: runner/report adaptation + compatibility bridge
- Pass 3: fixed internal evidence-field additions only
- Pass 4: disagreement/evaluation expansion

Do **not** start Lane Class B work under this sheet.

---

## Pass 1 default editable files

- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `backend/tests/test_nrc_aps_page_evidence.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`

### Pass 1 production no-touch rule

- Do **not** edit `backend/app/services/nrc_aps_document_processing.py` in Pass 1 unless a narrowly justified compatibility bridge is proven necessary.
- If analysis requires a scratch copy of `nrc_aps_document_processing.py`, it must live outside `backend/`, remain clearly marked non-production, and must not become a committed duplicate production path.

---

## Representative fixture rule

- Representative fixtures are binding for Lane Class A equivalence/no-drift.
- Regression-only fixtures may drift only with written justification.

See the representative fixture lock note for the canonical subset.

---

## Selector rule

- Keep the same selector only if representative behavior remains materially equivalent.
- If material behavior drift appears, stop and escalate into amendment/new-version handling rather than widening by inference.

---

## Fixed pass-3 field set

Allowed first-pass internal evidence additions:

- `largest_image_bbox_ratio`
- `largest_drawing_bbox_ratio`
- `dominant_visual_region_present`
- `text_visual_overlap_ratio`

Optional/deferable only with explicit justification:

- `meaningful_visual_region_count`

Do not add other internal fields in Lane Class A without a documented expansion decision.

---

## Artifact rule

- Strengthened artifacts coexist with the current pinned Candidate A artifact.
- The current pinned Candidate A artifact remains historically authoritative unless later explicitly superseded.

---

## Stop immediately if any of these occurs

- representative fixture Candidate A projection drift
- need for a new runtime-visible selector value
- outward schema / review / report / export widening
- generic candidate-registry/framework pressure
- broad OCR/hybrid/media-scope reopening
- hidden-consumer incompatibility without a bounded compatibility bridge
- inability to preserve Lane Class A no-drift conditions

---

## Required validation posture

At minimum after edits:

- substrate / projection tests
- workbench runner tests
- baseline-compatibility bundle
- Lane Class A equivalence/no-drift checks
- disagreement/evaluation outputs
- hidden-consumer compatibility review

---

## Execution principle

Prefer the smallest change that:
- improves structure
- preserves admitted Candidate A behavior
- preserves outward contract behavior
- and remains reversible
