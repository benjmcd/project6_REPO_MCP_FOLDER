# 00J - Candidate B OpenDataLoader File Touch Matrix and Escalation Rules

## Purpose

Translate the Candidate B boundary into explicit file-level rules.

## A. Allowed planning files now

- files under `next_milestone_plans/candidate_b_workbench/`

## B. Allowed future new files in a later implementation pass

### Tests/support
- `tests/support_nrc_aps_candidate_b_opendataloader.py`

### Tests
- `tests/test_nrc_aps_candidate_b_opendataloader.py`
- `tests/test_nrc_aps_candidate_b_opendataloader_compare.py`

### Corpus sidecars
- `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_labels.json`
- optional `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_manifest.json`

### Reports/raw outputs
- `tests/reports/nrc_aps_candidate_b_opendataloader_proof_report.json`
- `tests/reports/nrc_aps_candidate_b_opendataloader_compare_report.json`
- `tests/reports/nrc_aps_candidate_b_opendataloader_retention_manifest.json`
- `tests/reports/nrc_aps_candidate_b_opendataloader_raw/<run_id>/...`

### Dependency sidecar
- `tests/requirements_nrc_aps_candidate_b_opendataloader.txt`

## C. Read-only files in this objective

- `README.md`
- `REPO_INDEX.md`
- `project6.ps1`
- `backend/requirements.txt`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json`

## D. Escalate immediately if implementation would require

- touching any `backend/app/services/...` owner-path file
- adding any runtime selector or runtime-visible Candidate B path
- modifying `project6.ps1`
- modifying `backend/requirements.txt`
- creating API, review, report, export, schema, or persistence surfaces
- adding a generic candidate framework to make Candidate B work

Those are out of scope for this objective and require a new explicit freeze.
