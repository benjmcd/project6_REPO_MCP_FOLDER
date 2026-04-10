# PageEvidence Pass-Level Allowed File Manifest

## Purpose

Freeze the default allowed-file boundary for each strengthening pass so implementation remains simple, low-fragility, and easy to review.

This manifest supplements the broader owner boundaries in the execution packet by making the per-pass allowed scope explicit.

Current branch interpretation note:

- this manifest remains a prepared pass-boundary reference
- it does **not** by itself authorize opening Pass 2-4 on the current branch
- the current branch is in Stop-and-hold posture after Pass 1 closure
- any future implementation work must begin from a new explicitly frozen objective before later pass boundaries are activated again

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

## Pass 1 — lifecycle hardening and in-file extraction/projection separation

### Goal

- explicit cleanup/resource-lifecycle hardening
- separate shared evidence extraction from candidate projection inside the existing PageEvidence service if that can be done without widening file ownership
- no artifact meaning change
- no admitted behavior drift

### Default allowed modified files

- `backend/app/services/nrc_aps_page_evidence.py`
- `backend/tests/test_nrc_aps_page_evidence.py`


### Must remain untouched by default

- `backend/app/services/nrc_aps_document_processing.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- all hidden-consumer surfaces

### Optional analysis-only copy rule

If comparison against `nrc_aps_document_processing.py` is operationally useful during design or reasoning, an analysis-only copy may be created outside the production `backend` tree. That copy must not become a second runtime path or a committed production duplicate.

### Escalation trigger

If cleanup/lifecycle hardening plus in-file extraction/projection separation cannot remain behavior-preserving, artifact-preserving, and confined to the current Pass 1 owner set, stop and re-evaluate rather than widening casually.

---

## Pass 2 — compatibility bridge / helper extraction if Pass 1 proves insufficient

### Goal

- complete evidence/projection separation only if Pass 1 cannot keep the split clean enough inside the existing service file
- preserve current admitted Candidate A behavior
- add compatibility bridge only if required
- adapt runner/report handling only as required by the separation

### Default allowed modified files

- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `backend/tests/test_nrc_aps_page_evidence.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`

### Default allowed new files

- one projection/helper file under `backend/app/services/` if required to keep the split clean
- no evaluation/disagreement helper is default-authorized in Pass 2; that belongs to Pass 4 unless a written pass-boundary justification proves it is needed only for frozen runner/report compatibility

### Must remain untouched by default

- `backend/app/services/nrc_aps_document_processing.py`
- hidden-consumer surfaces

### Escalation trigger

If evidence/projection separation or any required compatibility bridge cannot be preserved without touching the integrated seam or hidden-consumer surfaces materially, stop and re-evaluate rather than widening casually.

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

### Default allowed new files

- one evaluation/disagreement helper under `tools/` if required by the frozen evaluation matrix

### Must remain untouched by default

- `backend/app/services/nrc_aps_document_processing.py`
- hidden-consumer surfaces
- outward consumer schemas

### Escalation trigger

If stronger evaluation requires touching integrated runtime behavior or hidden-consumer surfaces, stop and escalate rather than widening by convenience.

---

## Result

Each pass now has an explicit default file boundary, making implementation simpler and reducing accidental blast-radius expansion.
