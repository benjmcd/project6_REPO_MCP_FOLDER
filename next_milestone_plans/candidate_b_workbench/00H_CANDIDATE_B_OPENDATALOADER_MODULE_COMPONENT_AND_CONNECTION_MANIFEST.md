# 00H - Candidate B OpenDataLoader Module, Component, and Connection Manifest

## Purpose

State exactly which modules, components, and connections matter for Candidate B, and whether they are authority anchors, protected baseline surfaces, or future workbench-only surfaces.

## A. Authority and navigation components (reference-only)

- `next_milestone_plans/multi_variant_visual_lane_control/README_INDEX.md`
- `05P_POST_ADMISSION_RETAIN_BASELINE_DEFAULT_DECISION_RECORD.md`
- `05Q_POST_ADMISSION_RETAIN_BASELINE_MERGED_MAIN_CLOSURE_AND_HANDOFF.md`
- `next_milestone_plans/pageevidence/README_PAGEEVIDENCE_STRENGTHENING_PACK.md`
- `next_milestone_plans/pageevidence/PAGE_EVIDENCE_STRENGTHENING_ROADMAP_AND_DECISION_NOTES.md`
- `README.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `docs/nrc_adams/nrc_aps_authority_matrix.md`
- `docs/nrc_adams/nrc_aps_reader_path.md`

Role in Candidate B:
- establish current merged baseline truth
- freeze what Candidate B must not override

## B. Existing baseline proof harness components (reference-only)

- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/support_nrc_aps_doc_corpus.py`
- `tests/test_nrc_aps_document_corpus.py`
- `tests/test_nrc_aps_document_processing.py`
- current lower-layer proof reports under `tests/reports/`
- `project6.ps1 -Action prove-nrc-aps-document-processing`

Role in Candidate B:
- baseline comparison source
- non-interference proof source

## C. Current admitted Candidate A baseline surfaces (reference-only)

- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json`
- `05L_M6B_CANDIDATE_A_APPROVED_TARGET_RECORD.md`

Role in Candidate B:
- optional secondary comparison anchor
- current admitted-candidate behavior reference

## D. Protected owner-path components

- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_media_detection.py`
- `backend/app/services/nrc_aps_ocr.py`
- `backend/app/services/nrc_aps_settings.py`

Role in Candidate B:
- protected integrated baseline
- not editable in this objective

## E. Hidden-consumer and outward surfaces (reference-only, protected)

- retrieval plane
- content index
- evidence bundle
- review/document trace
- route/API surfaces
- report/export/package surfaces

Role in Candidate B:
- must remain untouched and unaffected
- later implementation validation must prove non-interference without widening them

## F. Future workbench-only implementation surfaces

If a later implementation pass is explicitly opened, only the following surface classes may be added by default:
- tests-side dependency sidecar
- tests-side Candidate B support and compare modules
- labels or optional sidecar manifest under the existing fixture folder
- workbench proof, compare, and retention artifacts under `tests/reports/`

No service-layer, selector, API, or persistence component is part of the default Candidate B objective.
