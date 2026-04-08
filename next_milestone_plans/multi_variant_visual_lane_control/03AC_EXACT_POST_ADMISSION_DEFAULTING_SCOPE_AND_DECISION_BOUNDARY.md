# 03AC Exact Post-Admission Defaulting Scope and Decision Boundary

## Purpose

Freeze the exact scope and decision boundary for the separate post-admission/defaulting planning phase that follows merged M6B Candidate A closure.

This is a planning-boundary document, not an implementation packet and not a default-promotion approval.

---

## Status note

Merged `main` now admits exactly one approved non-`baseline` selector value:

- `candidate_a_page_evidence_v1`

That merged-main closure is already recorded in:

- `05M_M6B_CANDIDATE_A_ADMISSION_IMPLEMENTATION_RECORD.md`
- `05N_M6B_MERGED_MAIN_CLOSURE_AND_POST_ADMISSION_HANDOFF.md`

What remains later-scope is broader post-admission/defaulting work.
This document freezes how that later-scope planning must be bounded before any new default-promotion or additional-candidate code is considered.
It also preserves the fact that `00D` still treats `baseline` as the default program rule unless that rule is explicitly revisited in a later record.

---

## Governing basis

- `00D_MULTI_VARIANT_PROGRAM_DECISION.md`
- `00F_LIVE_REPO_VERIFIED_FACTS_AND_OPEN_ITEMS.md`
- `03AA_EXACT_M6_CONTROLLED_ADMISSION_AND_PROMOTION_MECHANISM.md`
- `05L_M6B_CANDIDATE_A_APPROVED_TARGET_RECORD.md`
- `05M_M6B_CANDIDATE_A_ADMISSION_IMPLEMENTATION_RECORD.md`
- `05N_M6B_MERGED_MAIN_CLOSURE_AND_POST_ADMISSION_HANDOFF.md`
- `06E_BLOCKER_DECISION_TABLE.md`

---

## Verified live anchors this boundary is built on

1. `backend/app/services/connectors_nrc_adams.py` now preserves exactly `baseline` and `candidate_a_page_evidence_v1`, while fail-closing every other `visual_lane_mode` value to `baseline`.
2. `backend/app/services/nrc_aps_artifact_ingestion.py` still forwards `visual_lane_mode` and required no widening for the merged M6B lane.
3. `backend/app/services/nrc_aps_document_processing.py` now preserves exactly `baseline` and `candidate_a_page_evidence_v1`, and contains the admitted Candidate A seam-local path.
4. `backend/app/services/review_nrc_aps_runtime.py` now treats exactly `baseline` and `candidate_a_page_evidence_v1` as baseline-visible.
5. Review/catalog/API/report/export/package surfaces remain governed by the already-frozen M5 and M6 no-drift rules; the merged M6B lane did not widen those outward surfaces.
6. The active run-submission and run-review entry surfaces remain the same:
   - `POST /connectors/nrc-adams-aps/runs`
   - `GET /review/nrc-aps`
   - `GET /runs`
   - existing run-bound `/runs/{run_id}/...` review endpoints
   - existing NRC APS evidence-report/export/package endpoints
7. The admitted Candidate A mechanism already reuses the existing deterministic PageEvidence service and workbench evidence:
   - `backend/app/services/nrc_aps_page_evidence.py`
   - `tools/run_nrc_aps_page_evidence_workbench.py`
   - `tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json`
8. The merged M6B lane introduced no new libraries, no new schema/model surfaces, and no new migration surfaces.

---

## Exact questions this planning phase is allowed to answer

1. Whether the current `00D` program rule that `baseline` remains the default should be reaffirmed for the current horizon.
2. If that rule is ever reconsidered explicitly, whether `candidate_a_page_evidence_v1` is the only selector value eligible for any future default-promotion discussion.
3. What additional evidence and validation would be required before any explicit program-decision amendment or default-promotion target-definition could be frozen.
4. Whether Candidate B and Candidate C should remain non-admitted.
5. Whether any later selector widening is justified at all.

---

## Exact questions this planning phase is not allowed to answer by implication

This planning phase does **not** itself authorize:

1. Candidate A default-promotion code.
2. Candidate B or Candidate C admission.
3. OCR-routing changes.
4. OCR / hybrid OCR reopening.
5. media-scope widening.
6. policy tuning or threshold retuning.
7. new outward variant-identity fields.
8. report/export/schema/model/migration widening.
9. new library or dependency introduction.

If any later proposal depends on one of those items, that becomes a separate explicit freeze rather than an implied consequence of this document.

---

## Modules and components any later defaulting lane would have to re-audit

### Default owner set

- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/review_nrc_aps_runtime.py`

### Conditional owner set

Only if a repo-confirmed blocker proves the default owner set is insufficient:

- `backend/app/services/review_nrc_aps_catalog.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_evidence_report_export.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`

### Inspect-only protection set

Remain out of scope unless a later explicit freeze proves otherwise:

- `backend/app/services/nrc_aps_promotion_gate.py`
- `backend/app/services/nrc_aps_promotion_tuning.py`
- `backend/app/services/review_nrc_aps_runtime_roots.py`
- `backend/app/services/review_nrc_aps_runtime_db.py`
- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/schemas/review_nrc_aps.py`
- `backend/app/schemas/api.py`
- `backend/app/models/models.py`
- `backend/alembic/*`
- `backend/migration_compat.py`

---

## Dependencies and library posture

This planning phase reuses the already-admitted dependency posture.

That means:

- keep the current deterministic PageEvidence / PyMuPDF-based mechanism as the only admitted non-baseline mechanism in scope
- do not reopen library-selection work
- do not treat OpenCV, Shapely, Docling, layout-model stacks, OCR engines, or any new package as part of the current defaulting question

If a future defaulting proposal requires a new dependency or library class, that is outside this boundary and requires a separate freeze.

---

## Endpoint and outward-surface posture

This planning phase must treat the following as frozen outward-surface classes:

- run submission through `POST /connectors/nrc-adams-aps/runs`
- review run selection and run-bound review endpoints
- evidence-report/export/package endpoints and persistence paths
- existing retrieval/evidence/document-trace surfaces

The allowed question is whether the admitted non-`baseline` value ever becomes the default selector behavior.
The disallowed move is changing endpoint shapes, adding outward variant identity, or redefining surface contracts by inference.

---

## Stop conditions

Stop and open a different explicit freeze if any proposal requires:

1. a new selector value
2. Candidate B or Candidate C admission
3. OCR-routing or media-scope widening
4. policy tuning or threshold retuning
5. new dependencies or packages
6. schema/model/migration changes
7. new outward API/report/export identity fields

---

## Boundary output

After this planning freeze, the next justified move is one of only three things:

1. freeze an explicit retain-`baseline`-as-default decision
2. freeze an explicit program-decision-amendment plus exact Candidate A default-promotion target-definition lane
3. explicitly defer broader post-admission/defaulting work while preserving current merged-main behavior

No implementation lane should start by inference from this boundary document alone.
