# 00G - Candidate B OpenDataLoader Repo Verification and Authority Precheck

## Purpose

Prevent Candidate B work from drifting away from current merged-main truth.

This precheck is mandatory before any Candidate B implementation work.

## A. Required on-disk confirmations

The implementer must directly confirm the on-disk presence of all of the following.

### Merged-main control spine
- `next_milestone_plans/multi_variant_visual_lane_control/README_INDEX.md`
- `next_milestone_plans/multi_variant_visual_lane_control/05P_POST_ADMISSION_RETAIN_BASELINE_DEFAULT_DECISION_RECORD.md`
- `next_milestone_plans/multi_variant_visual_lane_control/05Q_POST_ADMISSION_RETAIN_BASELINE_MERGED_MAIN_CLOSURE_AND_HANDOFF.md`

### Adopted PageEvidence hold-state pack
- `next_milestone_plans/pageevidence/README_PAGEEVIDENCE_STRENGTHENING_PACK.md`
- `next_milestone_plans/pageevidence/PAGE_EVIDENCE_STRENGTHENING_ROADMAP_AND_DECISION_NOTES.md`

### Root and status anchors
- `README.md`
- `REPO_INDEX.md`
- `project6.ps1`
- `backend/requirements.txt`
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `docs/nrc_adams/nrc_aps_authority_matrix.md`
- `docs/nrc_adams/nrc_aps_reader_path.md`

### Current baseline proof harness
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/support_nrc_aps_doc_corpus.py`
- `tests/test_nrc_aps_document_corpus.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/reports/nrc_aps_document_processing_proof_report.json`

### Current admitted Candidate A anchors
- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json`
- `next_milestone_plans/multi_variant_visual_lane_control/05L_M6B_CANDIDATE_A_APPROVED_TARGET_RECORD.md`

### Protected owner-path files
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_media_detection.py`
- `backend/app/services/nrc_aps_ocr.py`
- `backend/app/services/nrc_aps_settings.py`

If any of those are missing, moved, or materially changed, Candidate B planning must be amended before code begins.

## B. Required truth confirmations

Confirm all of the following are still true before implementation:
- `baseline` remains default
- `candidate_a_page_evidence_v1` remains the only admitted non-`baseline` value
- the PageEvidence lane remains closed and Pass 2 remains not needed
- Candidate B remains non-admitted and non-runtime-visible
- no new repo-native authority doc has opened Candidate B work implicitly

## C. Required dependency prechecks

Before any Candidate B code:
- confirm the current Python interpreter is `py -3.12`
- confirm Java availability if the implementation still depends on it
- confirm the OpenDataLoader package pin, hash, license posture, and wrapper API/signature still match this pack

If any dependency precheck fails, stop and amend the pack before code begins.
