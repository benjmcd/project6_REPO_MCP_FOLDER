# PageEvidence Operator Execution Sheet

## Purpose

Compress the strengthening pack into one short operator-facing execution sheet so the implementation lane can be run with minimal interpretation burden.

This document is operational and non-normative.
It summarizes rules that are governed by the active control docs listed in the README doc classification table.
Use that table as the complete normative source map for this pack.

Use this sheet together with the full pack, not instead of it.
If conflict appears, the README classification table and the active control docs it lists outrank this sheet.

---

## Pack-prepared lane

- **Lane Class A only**
- Lane Class B remains future scope only by separate freeze

---

## Pack-prepared passes

- Pass 1: cleanup + explicit close/cleanup semantics + in-file extraction/projection separation if it stays inside the existing owner set
- Pass 2: compatibility bridge / helper extraction + runner/report adaptation only if Pass 1 proved insufficient
- Pass 3: fixed internal evidence-field additions only
- Pass 4: disagreement/evaluation expansion

If Pass 1 closure is already green and fresh truth re-establishment finds no residual insufficiency, do **not** open Pass 2; stop and hold instead.
Any future implementation work must begin from a new explicitly frozen objective rather than continuing from this sheet by momentum.

Do **not** start Lane Class B work under this sheet.

---

## Pass 1 default editable files

- `backend/app/services/nrc_aps_page_evidence.py`
- `backend/tests/test_nrc_aps_page_evidence.py`

### Pass 1 production no-touch rule

- Do **not** edit `backend/app/services/nrc_aps_document_processing.py` in Pass 1.
- If a later pass proves a compatibility bridge or other production touch is necessary, treat that as an explicit escalation rather than a Pass 1 convenience.
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
- Lane Class A may improve structure, separability, observability, and compatibility, but it may not silently change admitted Candidate A behavior on representative fixtures.

---

## Fixed Pass 3 field set

Allowed Pass 3 internal evidence additions:

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
- The current pinned Candidate A artifact remains historically authoritative for workbench/report compatibility and before-state reference unless later explicitly superseded; it is not the controlling definition of current admitted integrated Candidate A behavior.

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
- run review/runtime trace/API validation in an isolated invocation when shared process-level runtime-root state (for example `STORAGE_DIR`) could make mixed bundles misleading

---

## Execution principle

Prefer the smallest change that:
- improves structure
- preserves admitted Candidate A behavior
- preserves outward contract behavior
- and remains reversible

This sheet creates no new rules beyond the normative docs it summarizes.
