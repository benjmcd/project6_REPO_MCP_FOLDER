# 09A — Candidate B OpenDataLoader Output Isolation, Retention, and Event Registry

## Purpose

Ensure Candidate B outputs remain isolated from live runtime artifact namespaces,
and resolve the retention policy instead of leaving it implicit.

---

## A. Approved output roots

### Raw OpenDataLoader outputs
- historical committed raw-output root:
  - `tests/reports/nrc_aps_candidate_b_opendataloader_raw/<run_id>/...`
- compare-surface run-scoped raw-output root:
  - `tests/reports/cb-compare-<run_id>/raw/...`

### Durable Candidate B reports
- historical committed artifacts:
  - `tests/reports/nrc_aps_candidate_b_opendataloader_proof_report.json`
  - `tests/reports/nrc_aps_candidate_b_opendataloader_compare_report.json`
  - `tests/reports/nrc_aps_candidate_b_opendataloader_retention_manifest.json`
- compare-surface run-scoped artifacts:
  - `tests/reports/cb-compare-<run_id>/baseline-summary.json`
  - `tests/reports/cb-compare-<run_id>/proof.json`
  - `tests/reports/cb-compare-<run_id>/compare.json`
  - `tests/reports/cb-compare-<run_id>/retain.json`

### Existing labels sidecar
- `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_labels.json`
- no new Candidate B sidecar manifest in the first compare-surface pass

---

## B. Forbidden output locations

Candidate B v1 must not write into:
- runtime artifact-storage roots used by current NRC APS runs
- current content-blob namespaces
- current visual-page artifact namespaces
- evidence/report/export/context/deterministic runtime roots
- any API-facing persisted output location
- any source-fixture directory by relying on ODL default output behavior

---

## C. Required provenance for each run

Each proof/compare report must record at minimum:
- run id
- execution timestamp
- repo root used
- git revision if available locally
- Python version
- Java version
- ODL package version
- ODL expected package hash
- ODL verified package hash posture
- ODL config snapshot
- corpus manifest ref
- labels/sidecar ref if used
- raw output root
- hashes for durable reports

---

## D. Retention rule

### Default rule
Raw ODL outputs are **not** committed by default.

### Required review posture
Raw outputs must be retained under the approved run-scoped raw root long enough to support review and triage.
A retention manifest must record the inventory and hashes.

### After review posture
After the review window closes, choose one of these:
- keep local raw outputs outside version control
- archive externally by hash/reference
- move local raw outputs into the repo archive area after confirming the retention manifest is complete

### Separate approval required
Any decision to commit raw ODL JSON/Markdown/image outputs into the repo requires a separate explicit decision.
That is not part of Candidate B v1 by default.

---

## E. Redaction / sensitivity rule

Because raw ODL outputs reproduce source-document content,
any share/commit/archive decision must treat them as document-derived content,
not as innocuous logs.
If a reviewer-facing sample is ever needed,
prefer a tiny explicitly approved sample or a redacted derivative,
not the full raw run.

---

## F. Follow-on Candidate B Trace note

Current compare-surface truth remains:

- the approved durable top-level outputs are still `baseline-summary.json`, `proof.json`, `compare.json`, and `retain.json`
- current compare bundles may carry `annotated_pdf_ref`, `annotated_pdf_sha256`, and `annotated_pdf_status` inside `documents[*].candidate_b` while the annotated PDFs themselves remain under the approved run-scoped raw root

The landed Candidate B Trace surface continues to follow the contract frozen in:

- `04D_CANDIDATE_B_OPENDATALOADER_ANNOTATED_PDF_AND_INSPECTION_ARTIFACT_CONTRACT.md`

That means:

- annotated PDFs stay under the run-scoped raw root
- they are not committed by default
- they are hashed and inventoried
- they are surfaced only through validated bundle-scoped refs, not arbitrary browser path entry
