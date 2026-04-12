
# 00L — Candidate B OpenDataLoader Invocation, Import, and Dependency Boundary

## Purpose

Freeze the exact import/invocation boundary for Candidate B v1.

---

## A. Approved imports in v1

### Candidate B workbench support/test modules may import:
- `opendataloader_pdf`
- standard Python library modules needed for file/path/hash/json/report handling
- current repo test/support utilities as needed
- `app.services.nrc_aps_document_processing` for baseline comparison only

### Candidate B workbench must not import as integration targets:
- connector API modules
- review/runtime modules
- persistence/model/schema modules
- evidence/report/export/context/deterministic services as extension points

---

## B. Invocation boundary

Approved:
- Python-launched module invocation: `sys.executable -m opendataloader_pdf ...`

Forbidden in v1:
- invoking `java -jar ...`
- using Node.js bindings
- using a hybrid backend
- writing wrapper code under `backend/app/services/...`

Current committed `main` note:
- the workbench support module currently launches the package module via Python rather than calling `opendataloader_pdf.convert(...)` directly
- direct wrapper invocation remains a possible future tightening step, not a fact about the committed `main` implementation

---

## C. Dependency boundary

Approved:
- install ODL in a workbench/test environment only
- optional tests-side sidecar dependency file

Forbidden:
- modifying backend runtime dependencies in v1
- assuming backend runtime must import ODL in v1

---

## D. Why this boundary exists

The boundary prevents:
- hidden runtime drift
- dependency leakage into the owner path
- ambiguous provenance about how Candidate B was run
- accidental early integration of a still-unproven comparator lane


---
