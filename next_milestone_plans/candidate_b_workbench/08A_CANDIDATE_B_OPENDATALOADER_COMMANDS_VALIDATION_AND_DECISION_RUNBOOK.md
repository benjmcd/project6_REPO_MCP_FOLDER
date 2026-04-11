# 08A - Candidate B OpenDataLoader Commands, Validation, and Decision Runbook

## Purpose

Provide the exact validation and command order for a future Candidate B workbench implementation pass.

This runbook is grounded in the current merged baseline and is intentionally stricter than the older lower-layer-only framing.

## Phase 0 - repo and authority preflight

### Confirm current merged baseline posture
```powershell
git status --short --branch
git log --oneline --decorate -n 5
```

Reconfirm on disk:
- `05P` and `05Q`
- adopted PageEvidence README and roadmap
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json`

### Confirm repo runtime
```powershell
py -3.12 --version
java -version
```

### Confirm the existing lower-layer proof lane still passes
```powershell
.\project6.ps1 -Action prove-nrc-aps-document-processing -RequireOcr
```

Execution finding from the first actual Candidate B run:
- the default non-`RequireOcr` lower-layer proof posture now fails in a Tesseract-capable workspace because the proof runner forces `NRC_APS_CORPUS_OCR_MODE=disabled`
- the OCR-required proof lane is the live baseline-truth anchor for this workbench lane

If this OCR-required baseline proof fails, stop.
Do not open Candidate B work.

## Phase 1 - Candidate B dependency preflight

### Preferred reproducible install
```powershell
py -3.12 -m pip install --require-hashes -r tests/requirements_nrc_aps_candidate_b_opendataloader.txt
py -3.12 -m pip show opendataloader-pdf
```

### Required API and signature capture
```powershell
py -3.12 -c "import inspect, opendataloader_pdf; print(getattr(opendataloader_pdf, '__version__', 'unknown')); print(inspect.signature(opendataloader_pdf.convert))"
```

If the package version, license posture, hash, or wrapper signature does not match the pack, stop and amend the docs before implementation continues.

## Phase 2 - labels and baseline anchors

Before the first Candidate B run:
- freeze any labels sidecar contents
- record the manifest hash
- if optional Candidate A comparison will be used, record the exact frozen refs from `04B`

## Phase 3 - Candidate B proof run

Run Candidate B only through the approved tests/report-side surfaces.
Generate at minimum:
- proof report
- compare report
- retention manifest
- raw outputs under the approved Candidate B raw root

## Phase 4 - non-interference proof

After the Candidate B run:
- confirm touched files stayed inside the approved allowlist
- confirm outputs stayed inside the approved output roots
- rerun the baseline proof unchanged
- compare before and after baseline posture

## Phase 5 - decision

The only allowed decision outcomes are:
- proceed as documented workbench-only
- iterate the pack and retry later
- reject or defer Candidate B
- escalate to a new explicit objective

A Candidate B run is not allowed to self-promote into runtime integration, selector admission, or broader framework work.
