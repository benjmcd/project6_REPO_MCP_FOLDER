# 00B - Candidate B OpenDataLoader Repo Surface Map and Touch Policy

## Purpose

Freeze exactly which repo surfaces Candidate B may read, reference, add new workbench files under, or must not touch.

This frozen objective is grounded in the current merged baseline, not in older pre-merge repo assumptions.

## A. Highest-authority reference surfaces (read-only)

Candidate B planning is subordinate to these merged-main authority surfaces:
- `next_milestone_plans/multi_variant_visual_lane_control/README_INDEX.md`
- `next_milestone_plans/multi_variant_visual_lane_control/05P_POST_ADMISSION_RETAIN_BASELINE_DEFAULT_DECISION_RECORD.md`
- `next_milestone_plans/multi_variant_visual_lane_control/05Q_POST_ADMISSION_RETAIN_BASELINE_MERGED_MAIN_CLOSURE_AND_HANDOFF.md`
- `next_milestone_plans/pageevidence/README_PAGEEVIDENCE_STRENGTHENING_PACK.md`
- `next_milestone_plans/pageevidence/PAGE_EVIDENCE_STRENGTHENING_ROADMAP_AND_DECISION_NOTES.md`
- `README.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `docs/nrc_adams/nrc_aps_authority_matrix.md`
- `docs/nrc_adams/nrc_aps_reader_path.md`

## B. Repo-root proof and execution anchor surfaces (read-only)

These are repo-truth anchors for Candidate B planning and verification:
- `README.md`
- `REPO_INDEX.md`
- `project6.ps1`
- `backend/requirements.txt`

Candidate B may reference those surfaces but must not modify them.

## C. Existing baseline proof harness and comparison anchors (read-only)

Mandatory baseline comparison anchors:
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/support_nrc_aps_doc_corpus.py`
- `tests/test_nrc_aps_document_corpus.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/reports/nrc_aps_document_processing_proof_report.json`
- `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
- `tests/reports/nrc_aps_content_index_validation_report.json`

Current admitted Candidate A reference anchors:
- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `tests/reports/mvvlc_candidate_a_page_evidence_workbench_report_v1.json`
- `next_milestone_plans/multi_variant_visual_lane_control/05L_M6B_CANDIDATE_A_APPROVED_TARGET_RECORD.md`
- `next_milestone_plans/multi_variant_visual_lane_control/05Q_POST_ADMISSION_RETAIN_BASELINE_MERGED_MAIN_CLOSURE_AND_HANDOFF.md`

These are comparison anchors, not edit targets.

## D. Frozen owner-path service surfaces (read-only)

These surfaces are protected in Candidate B:
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_media_detection.py`
- `backend/app/services/nrc_aps_ocr.py`
- `backend/app/services/nrc_aps_settings.py`
- `backend/app/services/nrc_aps_page_evidence.py`

Candidate B must not modify the current owner path, OCR routing, media detection, run-config processing, or admitted Candidate A evidence path.

## E. Frozen outward-service families (read-only)

Candidate B must not touch the following outward families:

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

## F. Allowed new workbench-only surfaces in this objective

Planning and control docs in this folder are allowed.
A later implementation pass may add only the following new workbench surfaces or direct analogues under the same folders:

### Tests/support
- `tests/support_nrc_aps_candidate_b_opendataloader.py`
- `tests/test_nrc_aps_candidate_b_opendataloader.py`
- `tests/test_nrc_aps_candidate_b_opendataloader_compare.py`

### Corpus sidecars
- `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_labels.json`
- optional `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_manifest.json`

### Workbench reports and raw outputs
- `tests/reports/nrc_aps_candidate_b_opendataloader_proof_report.json`
- `tests/reports/nrc_aps_candidate_b_opendataloader_compare_report.json`
- `tests/reports/nrc_aps_candidate_b_opendataloader_retention_manifest.json`
- `tests/reports/nrc_aps_candidate_b_opendataloader_raw/<run_id>/...`

### Dependency sidecar
- `tests/requirements_nrc_aps_candidate_b_opendataloader.txt`

## G. Explicitly forbidden new surfaces

Candidate B must not add:
- any new `backend/app/services/...` module
- any new API route
- any new connector selector or runtime mode
- any new review/runtime page
- any new DB model, schema, or migration
- any new persisted run-detail ref family
- any new `project6.ps1` action
- any new runtime-visible `tools/` runner by default
- any generic candidate registry or framework surface

## H. Touch policy summary

Read-only reference surfaces:
- merged-main authority docs
- root README and status docs
- current lower-layer proof harness
- current admitted Candidate A baseline surfaces

Allowed future new surfaces:
- this planning pack
- tests/support
- tests/test...
- tests/reports...
- optional corpus sidecars
- tests-side dependency sidecar

Forbidden surfaces:
- service layer
- selector and owner-path semantics
- endpoint/API layer
- review/runtime surfaces
- DB/persistence/schema/migration surfaces
- operator-script surfaces
- generic framework surfaces
