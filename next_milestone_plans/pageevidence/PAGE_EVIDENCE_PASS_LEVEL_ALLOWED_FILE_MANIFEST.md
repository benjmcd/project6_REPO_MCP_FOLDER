# PageEvidence Pass-Level Allowed File Manifest

## Purpose

Freeze the default allowed-file boundary for each strengthening pass so implementation remains simple, low-fragility, and easy to review.

This manifest supplements the broader owner boundaries in the execution packet by making the per-pass allowed scope explicit.

---

## General rule for `nrc_aps_document_processing.py`

The current agreed posture is:

- do **not** touch `backend/app/services/nrc_aps_document_processing.py` in Pass 1
- do **not** assume it is editable in Pass 2–4 by default
- if analysis against a copy of that file is useful, that copy must be:
  - outside the production `backend` path
  - non-authoritative
  - non-imported by runtime/tests
  - clearly labeled as scratch/analysis only
- no committed duplicate production path is allowed by default

If a real repo edit to `nrc_aps_document_processing.py` becomes necessary, treat that as an escalation event and re-evaluate the lane class and blast radius explicitly.

---

## Pass 1 — cleanup and structural separation

### Goal

- explicit cleanup/resource-lifecycle hardening
- split shared evidence extraction from candidate-policy projection
- preserve current admitted Candidate A behavior materially

### Default allowed modified files

- `backend/app/services/nrc_aps_page_evidence.py`
- `backend/tests/test_nrc_aps_page_evidence.py`

### Default allowed new files

- one projection/helper file under `backend/app/services/` if required to keep the split clean

### Must remain untouched by default

- `backend/app/services/nrc_aps_document_processing.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- all hidden-consumer surfaces

### Optional analysis-only copy rule

If comparison against `nrc_aps_document_processing.py` is operationally useful during design or reasoning, an analysis-only copy may be created outside the production `backend` tree. That copy must not become a second runtime path or a committed production duplicate.

### Escalation trigger

If structural separation cannot be achieved without changing integrated seam behavior or runner semantics materially, stop and re-evaluate the lane class.

---

## Pass 2 — runner/report adaptation

### Goal

- adapt workbench/report generation to the separated evidence/projection structure
- preserve pinned artifact meaning or apply compatibility bridge explicitly

### Default allowed modified files

- `tools/run_nrc_aps_page_evidence_workbench.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`

### Default allowed new files

- one evaluation/disagreement helper under `tools/` if required by the frozen evaluation matrix

### Must remain untouched by default

- `backend/app/services/nrc_aps_document_processing.py`
- hidden-consumer surfaces

### Escalation trigger

If artifact compatibility cannot be preserved without touching a hidden-consumer surface or the integrated seam, stop and re-evaluate rather than widening casually.

---

## Pass 3 — fixed internal evidence-field enrichment

### Goal

- add only the pre-approved small fixed set of internal fields
- keep them additive by default
- keep admitted Candidate A behavior materially unchanged

### Default allowed modified files

- `backend/app/services/nrc_aps_page_evidence.py`
- `backend/tests/test_nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`

### Pre-approved fields only

The only new internal fields pre-approved for Pass 3 are:

- `largest_image_bbox_ratio`
- `largest_drawing_bbox_ratio`
- `dominant_visual_region_present`
- `text_visual_overlap_ratio`
- `meaningful_visual_region_count` (optional; may be deferred)

### Must remain untouched by default

- `backend/app/services/nrc_aps_document_processing.py`
- hidden-consumer surfaces
- outward schemas/review/report/export layers

### Escalation trigger

If the new fields change admitted projection outcomes on representative fixtures, stop and classify the work under the Lane Class A equivalence gate / Lane Class B decision path.

---

## Pass 4 — evaluation / disagreement expansion

### Goal

- stronger disagreement summaries
- borderline-page visibility
- representative-fixture comparability

### Default allowed modified files

- `tools/run_nrc_aps_page_evidence_workbench.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`
- one evaluation/disagreement helper if already allowed or newly justified under the execution packet

### Must remain untouched by default

- `backend/app/services/nrc_aps_document_processing.py`
- hidden-consumer surfaces
- outward consumer schemas

### Escalation trigger

If stronger evaluation requires touching integrated runtime behavior or hidden-consumer surfaces, stop and escalate rather than widening by convenience.

---

## Result

Each pass now has an explicit default file boundary, making implementation simpler and reducing accidental blast-radius expansion.
