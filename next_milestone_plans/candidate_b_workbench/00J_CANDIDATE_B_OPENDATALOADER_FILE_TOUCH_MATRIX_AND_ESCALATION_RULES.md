# 00J - Candidate B OpenDataLoader File Touch Matrix and Escalation Rules

## Purpose

Translate the v5 boundary into explicit file-level rules.

---

## A. Allowed new files in v1

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
- `tests/reports/nrc_aps_candidate_b_opendataloader_raw/<run_id>/...`

### Dependency sidecar (if adopted)
- `tests/requirements_nrc_aps_candidate_b_opendataloader.txt`

### Branch-local planning pack only
- `next_milestone_plans/candidate_b_workbench/...`

---

## B. Read-only files in v1

- `README.md`
- `REPO_INDEX.md`
- `project6.ps1`
- `backend/requirements.txt`
- current authority docs under `docs/nrc_adams/...`
- existing proof harness files under `tests/fixtures/...`, `tests/support...`, `tests/test...`
- existing `tests/reports/...` baseline reports
- all current service-layer owner-path/outward-surface files

---

## C. Forbidden-touch files/directories in v1

- anything under `backend/app/api/`
- anything under `backend/app/db/`
- anything under `backend/app/models/`
- anything under `backend/app/schemas/`
- any current file under `backend/app/services/`
- any migrations
- any frontend/e2e/Docker/CI files
- any current review/runtime service file
- `project6.ps1`

---

## D. Escalation rules

Escalate and stop if Candidate B v1 appears to require:
1. editing a current service file
2. adding a new service module
3. modifying a runtime dependency surface
4. adding a new endpoint or run-detail ref
5. changing corpus/base manifest semantics rather than adding a sidecar
6. enabling hybrid/docling or other backend-assisted widening
7. creating parallel handoff copies outside `next_milestone_plans/candidate_b_workbench/...`

Those are not v1 decisions.

---
