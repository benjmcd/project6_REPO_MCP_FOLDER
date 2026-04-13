# 00B - Candidate B OpenDataLoader Repo Surface Map and Touch Policy

## Purpose

Freeze exactly which repo surfaces Candidate B v1 may:
- read,
- reference,
- add new workbench files under,
- or must not touch.

This v5 version is grounded in the live repo root README, the visible repo tree,
the visible `backend/app/services` tree, and opened lower-layer files/tests.

Scope note:
- this document freezes the original Candidate B v1 lower-layer/workbench comparator boundary
- it does not override a later separately reopened additive lane that is explicitly frozen elsewhere in this pack
- the Candidate B Trace follow-on is that kind of separately reopened lane and is governed by:
  - `04D_CANDIDATE_B_OPENDATALOADER_ANNOTATED_PDF_AND_INSPECTION_ARTIFACT_CONTRACT.md`
  - `05U_CANDIDATE_B_OPENDATALOADER_CANDIDATE_B_TRACE_IMPLEMENTATION_PLAN.md`
  - `08F_CANDIDATE_B_OPENDATALOADER_CANDIDATE_B_TRACE_VALIDATION_PLAN.md`
- unless a later lane is explicitly reopened that way, this document remains the controlling touch boundary

---

## A. Highest-authority reference surfaces (read-only)

These are named by the live root README as authoritative status/navigation surfaces.
They are read-only in Candidate B v1:
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `docs/nrc_adams/nrc_aps_authority_matrix.md`
- `docs/nrc_adams/nrc_aps_reader_path.md`
- the linked PostgreSQL status handoff surface named by the root README

Candidate B planning docs must align to these if and when they are opened directly in a later pass.

---

## B. Repo-root proof and execution anchor surfaces (read-only)

These are repo-truth anchors for Candidate B planning and verification:
- `README.md`
- `REPO_INDEX.md`
- `project6.ps1`
- `backend/requirements.txt` (reference-only in v1)

Candidate B v1 may reference these surfaces but must not modify them.

Bounded compare-surface note:
- the compare-surface lane now adds one new `project6.ps1` action named `compare-nrc-aps-candidate-b` and repo-native helper tools under `tools/`
- that remains workbench-only and does not widen Candidate B into runtime/service/API posture
- do not treat this note as permission to widen into runtime/service/API work

---

## C. Existing lower-layer proof harness (read-only inputs)

Candidate B v1 must treat these as the primary comparison harness:
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/support_nrc_aps_doc_corpus.py`
- `tests/test_nrc_aps_document_corpus.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/reports/nrc_aps_document_processing_proof_report.json`
- `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
- `tests/reports/nrc_aps_content_index_validation_report.json`

These are input/baseline truth surfaces, not edit targets in Candidate B v1.

---

## D. Frozen owner-path service surfaces (read-only)

These are specifically frozen in Candidate B v1:
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_media_detection.py`
- `backend/app/services/nrc_aps_ocr.py`
- `backend/app/services/nrc_aps_settings.py`

Interpretation:
Candidate B v1 must not modify the current owner path, OCR routing, media detection, or run-config processing.

---

## E. Frozen outward-service families (read-only)

Because the visible service tree shows these outward families already exist,
Candidate B v1 must not touch them:

### Retrieval / connector / indexing
- `aps_retrieval_plane*.py`
- `nrc_aps_content_index*.py`
- `nrc_aps_live_batch.py`
- `nrc_aps_replay_*.py`
- `nrc_aps_sync_drift*.py`
- `nrc_aps_safeguards*.py`
- `nrc_aps_promotion*.py`

### Evidence / citation / report / export
- `nrc_aps_evidence_bundle*.py`
- `nrc_aps_evidence_citation_pack*.py`
- `nrc_aps_evidence_report*.py`
- `nrc_aps_evidence_report_export*.py`
- `nrc_aps_evidence_report_export_package*.py`

### Context / deterministic artifact families
- `nrc_aps_context_packet*.py`
- `nrc_aps_context_dossier*.py`
- `nrc_aps_deterministic_insight_artifact*.py`
- `nrc_aps_deterministic_challenge_artifact*.py`
- `nrc_aps_deterministic_challenge_review_packet*.py`

### Review/runtime/document-trace
- `review_nrc_aps_catalog.py`
- `review_nrc_aps_details.py`
- `review_nrc_aps_document_trace.py`
- `review_nrc_aps_graph.py`
- `review_nrc_aps_overview.py`
- `review_nrc_aps_runtime.py`
- `review_nrc_aps_runtime_db.py`
- `review_nrc_aps_runtime_roots.py`
- `review_nrc_aps_tree.py`

Candidate B v1 must not alter any of those surfaces.

---

## F. Allowed new workbench-only surfaces in v1

Candidate B v1 may add only the following new files or direct analogues under the same folders:

### Tests/support
- `tests/support_nrc_aps_candidate_b_opendataloader.py`
- `tests/test_nrc_aps_candidate_b_opendataloader.py`
- `tests/test_nrc_aps_candidate_b_opendataloader_compare.py`

### Repo-native compare-surface helpers
- `tools/run_nrc_aps_candidate_b_compare.py`
- `tools/run_nrc_aps_candidate_b_baseline.py`

### Corpus sidecar labels / manifests
- `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_labels.json`
- do not add a new `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_manifest.json` in the first compare-surface pass; use the existing base manifest plus the frozen labels sidecar only

### Workbench reports and raw outputs
- historical committed artifacts:
  - `tests/reports/nrc_aps_candidate_b_opendataloader_proof_report.json`
  - `tests/reports/nrc_aps_candidate_b_opendataloader_compare_report.json`
  - `tests/reports/nrc_aps_candidate_b_opendataloader_retention_manifest.json`
- compare-surface run-scoped outputs:
  - `tests/reports/cb-compare-<run_id>/baseline-summary.json`
  - `tests/reports/cb-compare-<run_id>/proof.json`
  - `tests/reports/cb-compare-<run_id>/compare.json`
  - `tests/reports/cb-compare-<run_id>/retain.json`
  - `tests/reports/cb-compare-<run_id>/raw/...`

### Candidate B planning/workbench pack
- `next_milestone_plans/candidate_b_workbench/...`

Do not fan out parallel handoff copies in v1.

---

## G. Explicitly forbidden new surfaces in v1

Candidate B v1 must not add:
- any new `backend/app/services/...` module
- any new API route
- any new connector selector or runtime mode
- any new review/runtime page
- any new DB model / schema / migration
- any new persisted run-detail ref family
- any Docker / CI / frontend / deployment changes

Bounded follow-on compare-surface exception:
- one repo-native `project6.ps1` compare action is allowed only in the separate compare-surface lane
- that exception does not permit changes to any API, review UI, runtime selector, or backend service surface

Separate Candidate B Trace note:
- the prohibition list above remains correct for Candidate B v1
- it must not be read as invalidating the separately reopened Candidate B Trace lane frozen in `05U`
- if implementation pressure goes beyond the exact Candidate B Trace scope frozen there, stop and reopen the pack again

---

## H. Touch policy summary

### Read-only reference surfaces
- authority docs
- root README / REPO_INDEX / project6.ps1
- backend owner path
- current lower-layer proof harness
- current proof reports

### Allowed new surfaces
- tests/support
- tests/test...
- tests/reports...
- the existing corpus labels sidecar only; no new sidecar manifest in the first compare-surface pass
- the existing Candidate B planning/workbench pack only

### Forbidden surfaces
- service layer
- endpoint/API layer
- review/runtime surfaces
- DB/persistence/schema/migration surfaces
- operator script surfaces except for the one bounded compare-surface action described above

This is the exact v1 control boundary.

---
