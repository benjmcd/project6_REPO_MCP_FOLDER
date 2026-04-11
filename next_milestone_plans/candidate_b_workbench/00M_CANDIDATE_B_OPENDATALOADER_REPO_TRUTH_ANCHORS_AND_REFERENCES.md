# 00M - Candidate B OpenDataLoader Repo-Truth Anchors and References

## Purpose

Provide one place that states exactly what was verified from current `main`,
what Candidate B planning is allowed to treat as repo truth,
and what remains unproven because Candidate B has not yet been executed.

---

## Verified live repo anchors

### A. Current merged-main control spine
Current `main` includes the active MVVLC front door and merged closure spine:
- `next_milestone_plans/multi_variant_visual_lane_control/README_INDEX.md`
- `next_milestone_plans/multi_variant_visual_lane_control/05N_M6B_MERGED_MAIN_CLOSURE_AND_POST_ADMISSION_HANDOFF.md`
- `next_milestone_plans/multi_variant_visual_lane_control/05P_POST_ADMISSION_RETAIN_BASELINE_DEFAULT_DECISION_RECORD.md`
- `next_milestone_plans/multi_variant_visual_lane_control/05Q_POST_ADMISSION_RETAIN_BASELINE_MERGED_MAIN_CLOSURE_AND_HANDOFF.md`

These are higher authority than any branch-local Candidate B planning note.

### B. Current merged-main MVVLC/PageEvidence posture
Verified from current merged-main control docs:
- `baseline` remains the default runtime mode
- `candidate_a_page_evidence_v1` remains the only admitted non-`baseline` value
- Candidate B and Candidate C remain non-admitted
- the adopted PageEvidence pack under `next_milestone_plans/pageevidence/` is subordinate lane-local hold-state only
- PageEvidence Pass 1 is complete, Pass 2 is not needed on current merged `main`, and any future PageEvidence work requires a new explicit freeze

Candidate B must not reopen or imply more than that.

### C. Root authority references explicitly named by the live root README
The live root `README.md` names these as the authoritative NRC APS status/navigation surfaces:
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `docs/nrc_adams/nrc_aps_authority_matrix.md`
- `docs/nrc_adams/nrc_aps_reader_path.md`
- `docs/postgres_status_handoff.md` or adjacent PostgreSQL status handoff surface as linked by the README

Candidate B planning must treat those paths as higher authority than any free-form inference from old notes.

### D. Root README warning that still matters
The live root README warns that unverified `tests/...` and `tools/...` references should not be trusted blindly unless their on-disk presence is directly confirmed.

Interpretation:
- a path named in planning docs is not enough on its own
- implementation preflight must confirm file presence in the actual working tree

### E. Live connector/API surface explicitly named by the root README
The root README currently names these NRC APS surfaces among the active connector endpoints:
- `POST /api/v1/connectors/nrc-adams-aps/runs`
- `POST /api/v1/connectors/nrc-adams-aps/content-search`
- evidence bundle / citation pack / evidence report / export / export package endpoints
- context packet / context dossier endpoints
- deterministic insight / deterministic challenge artifact endpoints
- additive run-detail refs for those artifact families

Candidate B v1 is not allowed to alter any of those outward surfaces.

### F. Live lower-layer reopening explicitly named by the root README
The root README states that the NRC APS upper analytical layers remain frozen,
and that the lower document-processing layers are reopened additively around:
- deterministic media detection (`aps_media_detection_v1`)
- PyMuPDF-based PDF extraction (`aps_document_extraction_v1`)
- BOM-aware plain-text decoding
- OCR adapter wiring via the Tesseract CLI
- timeout enforcement
- content-units v2 / chunking v2 with page and unit metadata

Candidate B v1 must therefore be planned as a comparator over this reopened lower layer,
not as an immediate replacement of it.

### G. Live lower-layer proof harness named by the root README
The root README explicitly names the active lower-layer proof harness:
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/support_nrc_aps_doc_corpus.py`
- `tests/test_nrc_aps_document_corpus.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/reports/nrc_aps_document_processing_proof_report.json`
- `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
- `tests/reports/nrc_aps_content_index_validation_report.json`
- `project6.ps1 -Action prove-nrc-aps-document-processing`

This is the correct Candidate B v1 anchor.

### H. Live runtime requirements named by the root README
The root README currently states the repo runtime expectation as:
- Windows PowerShell
- Python 3.12 via `py -3.12`

Candidate B planning must align with repo runtime first, not library minimum first.

### I. Visible live backend/service surface
The visible `backend/app/services` tree includes, among many others:
- `connectors_nrc_adams.py`
- `nrc_aps_artifact_ingestion.py`
- `nrc_aps_document_processing.py`
- `nrc_aps_media_detection.py`
- `nrc_aps_ocr.py`
- `nrc_aps_settings.py`
- evidence / report / export / context / deterministic artifact services
- review/runtime/document-trace services

Interpretation:
Candidate B v1 should not open service-layer work unless separately authorized later.

### J. Live lower-layer implementation invariants visible in `nrc_aps_document_processing.py`
Verified from the live file page:
- admitted visual lane modes are exactly `baseline` and `candidate_a_page_evidence_v1`
- visual classes are `diagram_or_visual` and `text_heavy_or_empty`
- visually significant content includes large embedded images or at least 20 drawing commands
- preserve eligibility requires visually significant content plus weak/unusable native text
- `page_summaries` include `visual_page_class`
- final results include `document_processing_contract_id`, `extractor_family`, `page_summaries`, `degradation_codes`, `visual_page_refs`, `normalized_text`, `normalized_text_sha256`
- `ocr_required_but_unavailable` still raises when final quality remains unusable and OCR is required but unavailable

### K. Live PageEvidence/runner anchors that remain reference-only for Candidate B
Verified on current `main`:
- `backend/app/services/nrc_aps_page_evidence.py` remains the live PageEvidence owner file for the closed Candidate A lane
- `tools/run_nrc_aps_page_evidence_workbench.py` remains the isolated Candidate A workbench runner
- `tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json` remains the historically authoritative pinned Candidate A workbench artifact

Candidate B may cite those only as historical/reference anchors.
It may not reopen that lane or treat those surfaces as active implementation scope.

### L. Live coupling visible in `nrc_aps_artifact_ingestion.py`
Verified from the live file page:
- run config is converted to processing config via `processing_config_from_run_config(...)`
- `extract_and_normalize(...)` calls `nrc_aps_document_processing.process_document(...)`
- the returned artifact-ingestion structure forwards `content_type` plus `**processed`

Interpretation:
mutating lower-layer extraction semantics too early will couple into artifact ingestion and then outward surfaces.

### M. Live lower-layer tests visible in `tests/test_nrc_aps_document_processing.py`
Verified from the live file page:
- preserve-eligible pages must produce `visual_page_refs` with status `preserved` and class `diagram_or_visual`
- non-eligible pages keep `visual_page_refs == []` and summary class `text_heavy_or_empty`
- visual-capture failure is non-fatal but must record `visual_capture_failed`
- OCR strictness must remain fail-closed: scanned PDFs without OCR must still raise `ocr_required_but_unavailable`

Candidate B must preserve those invariants.

### N. Candidate B pack location truth
`git ls-tree -r --name-only main -- next_milestone_plans/candidate_b_workbench` returned no files in this pass.

So the current Candidate B pack is branch-local only.
It is not already on `main`.

---

## What remains unverified in this session

This pass does **not** claim:
- that Candidate B code/tests/report artifacts already exist on `main`
- that the current machine already satisfies Java 11+ resolution on `PATH`
- that `opendataloader-pdf` is already installed locally
- that any Candidate B comparator result has been produced yet

Therefore the pack may rely on:
- verified current-`main` docs, tree inventory, and opened file contents
- verified root README statements
- verified current lower-layer proof/fixture anchors
- verified current merged-main closure posture

but it must not invent stronger repo knowledge than that.

---

## Planning implication

The correct Candidate B planning posture is now:
- repo-truth grounded
- merged-main closure aware
- PageEvidence-lane non-reopening
- service-layer frozen
- proof-harness anchored
- outward-surface non-interference enforced
- live lower-layer invariant preserving

That is the minimum standard for opening Candidate B work.

---
