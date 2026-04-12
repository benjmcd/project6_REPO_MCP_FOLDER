
# 00H — Candidate B OpenDataLoader Module, Component, and Connection Manifest

## Purpose

State exactly which modules/components/connections matter for Candidate B v1,
and whether they are reference-only, frozen, or allowed new workbench surfaces.

---

## A. Authority / navigation components (reference-only)

- root `README.md`
- `REPO_INDEX.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `docs/nrc_adams/nrc_aps_authority_matrix.md`
- `docs/nrc_adams/nrc_aps_reader_path.md`

Role in Candidate B:
- planning alignment
- authority cross-check
- no direct implementation edits in v1

---

## B. Existing lower-layer proof harness components (reference-only baseline)

- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/support_nrc_aps_doc_corpus.py`
- `tests/test_nrc_aps_document_corpus.py`
- `tests/test_nrc_aps_document_processing.py`
- current lower-layer proof reports under `tests/reports/`
- `project6.ps1 -Action prove-nrc-aps-document-processing`

Role in Candidate B:
- corpus source
- baseline truth source
- pre-existing proof/reference harness

---

## C. Frozen lower-layer owner-path components (read-only)

### Direct owner path
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_media_detection.py`
- `backend/app/services/nrc_aps_ocr.py`
- `backend/app/services/nrc_aps_settings.py`
- `backend/app/services/connectors_nrc_adams.py`

### Why frozen
These files collectively determine:
- parsing config flow
- owner-path extraction semantics
- OCR/media behavior
- connector/runtime integration

Candidate B v1 is not allowed to alter any of those.

---

## D. Frozen outward service families (read-only)

Because these families already own outward connector/report/review behavior,
Candidate B v1 must not modify them:
- retrieval plane family
- content-index family
- evidence bundle family
- evidence citation pack family
- evidence report/export/package family
- context packet/dossier family
- deterministic insight/challenge family
- review/runtime/document-trace family

---

## E. Allowed new Candidate B v1 components

### 1. Workbench support module
- `tests/support_nrc_aps_candidate_b_opendataloader.py`

Responsibilities:
- resolve corpus from the existing manifest-driven harness
- invoke OpenDataLoader with the frozen v1 config
- parse raw outputs
- derive Candidate B summaries
- run comparison against current lower-layer outputs

### 2. Workbench tests
- `tests/test_nrc_aps_candidate_b_opendataloader.py`

Responsibilities:
- current committed `main` unit test coverage is helper-focused only
- it proves footer-page tracking, image-source collision detection, and multi-column signal detection
- a separate compare-report pytest surface is not present in the current committed tree

### 3. Optional corpus sidecar labels
- `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_labels.json`
- optional sidecar manifest if truly required

Responsibilities:
- record page/document buckets for Candidate B value/control analysis
- do not mutate the base manifest in v1

### 4. Candidate B reports/raw outputs
- `tests/reports/nrc_aps_candidate_b_opendataloader_proof_report.json`
- `tests/reports/nrc_aps_candidate_b_opendataloader_compare_report.json`
- `tests/reports/nrc_aps_candidate_b_opendataloader_raw/<run_id>/...`

---

## F. Connection model

### Existing baseline connection model
`project6.ps1` / pytest / support files -> lower-layer proof corpus -> `nrc_aps_document_processing.process_document()` -> lower-layer proof reports

### Candidate B v1 connection model
same corpus -> Candidate B support module -> `sys.executable -m opendataloader_pdf` -> raw ODL outputs -> derived Candidate B summaries -> compare against current lower-layer outputs -> Candidate B proof/compare reports

### Explicitly forbidden connection model in v1
OpenDataLoader -> backend service runtime -> connector endpoints -> persisted outward artifact families

That connection is out of scope for v1.


---
