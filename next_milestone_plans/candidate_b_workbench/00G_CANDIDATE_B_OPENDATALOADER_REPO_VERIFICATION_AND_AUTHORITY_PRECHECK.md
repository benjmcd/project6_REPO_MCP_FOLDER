
# 00G — Candidate B OpenDataLoader Repo Verification and Authority Precheck

## Purpose

Prevent implementation from drifting away from the current repo truth.

This precheck is mandatory before any Candidate B v1 code/doc adoption work.

Status note:
- this precheck froze the original Candidate B v1 bundle/comparator boundary before Candidate B runtime admission was explicitly reopened
- current `main` now includes a bounded later runtime-admission program for `document_processing_engine="candidate_b_opendataloader_pdf"`, `/runs` metadata, rendered review/document-trace selector labels, Workbench Compare runtime-source selection, and fixed-fixture runtime-source prep/validation
- therefore stop condition 5 below remains a stop condition for treating this original v1 pack as live implementation authority; it is not a veto over the separately reopened runtime-source tranches documented in the current front-door/status docs

---

## A. Required on-disk confirmations

The implementer must directly confirm the on-disk presence of all of the following:

### Root / authority anchors
- `README.md`
- `REPO_INDEX.md`
- `project6.ps1`
- `backend/requirements.txt`
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `docs/nrc_adams/nrc_aps_authority_matrix.md`
- `docs/nrc_adams/nrc_aps_reader_path.md`

### Lower-layer proof harness
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/support_nrc_aps_doc_corpus.py`
- `tests/test_nrc_aps_document_corpus.py`
- `tests/test_nrc_aps_document_processing.py`

### Frozen owner-path files
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_media_detection.py`
- `backend/app/services/nrc_aps_ocr.py`
- `backend/app/services/nrc_aps_settings.py`

If any of those are missing or moved, Candidate B planning must be amended before code begins.

---

## B. Required semantic confirmations

The implementer must confirm all of the following directly from the live files:

1. the root README still states that the upper NRC APS layers are frozen and the lower document-processing layer is reopened additively
2. the root README still names the manifest-driven lower-layer proof harness
3. `nrc_aps_document_processing.py` still exposes the current visual-lane/output semantics Candidate B is supposed to compare against
4. `nrc_aps_artifact_ingestion.py` still couples lower-layer processed outputs into artifact ingestion
5. `tests/test_nrc_aps_document_processing.py` still enforces the current OCR/visual-lane invariants

---

## C. Stop conditions

Stop Candidate B v1 planning or implementation immediately if any of the following are true:

1. the lower-layer proof harness has materially changed and this pack no longer matches it
2. the owner-path lower-layer files have already been replaced by a different architecture
3. the repo now authorizes a different higher-authority Candidate B plan
4. the current lower-layer tests no longer enforce the invariants this pack depends on
5. the repo owner has already moved Candidate B into a runtime lane separately

---

## D. Repo-native confirmation note

Session tooling availability can vary.
This pack must therefore stay grounded in repo-native confirmation methods that are actually available in the implementation session, such as:
- local git history and tree inspection
- opened on-disk source files
- repo connector results when available
- root README statements plus the cited authority docs

Before implementation, do one final repo-native confirmation pass against current `main`.
That pass is a confirmation step, not a license to redesign the pack ad hoc.


---
