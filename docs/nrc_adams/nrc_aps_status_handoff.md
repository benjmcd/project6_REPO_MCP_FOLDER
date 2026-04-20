# NRC ADAMS APS Status Handoff

## 1. Purpose and truth model
This document is the canonical live-repo status surface for the NRC ADAMS APS stack. Last updated April 20, 2026 to reflect the bounded Layer 3 APS evidence-report-export handoff slice now landed on current `main`, on top of the bounded evidence-report slice now landed on current `main`, the earlier bounded evidence-bundle and citation-pack handoff slices also landed on current `main`, the Deterministic Challenge Review Packet v1 closeout, and the narrow Tier2 diagnostics-write closeout.

Repo truth precedence used here:
1. live code, tests, scripts, migrations, and repo-contained proof artifacts
2. this live status doc and other current root docs
3. handoff package control surfaces
4. older planning/history only when not contradicted by the live repo

Status wording used below:
- `repo-confirmed in this workspace`
- `carried-forward but not revalidated here`
- `inferred from repo shape`

## 2. Current status summary
### Repo-confirmed in this workspace
| Surface | Current state | Proof |
| --- | --- | --- |
| Upper analytical ceiling | Still closed/frozen through Deterministic Challenge Review Packet v1 | current live contract/service/gate/tests/report surfaces for citation pack, evidence report/export/package, context packet, context dossier, deterministic insight, deterministic challenge, deterministic challenge review packet |
| Lower document-processing layer | Reopened additively for deterministic media detection, real PDF extraction, OCR fallback hooks, quality gating, and content-units v2 | `backend/app/services/nrc_aps_media_detection.py`, `backend/app/services/nrc_aps_document_processing.py`, `backend/app/services/nrc_aps_ocr.py`, `backend/app/services/nrc_aps_artifact_ingestion.py`, `backend/app/services/nrc_aps_content_index.py`, `backend/alembic/versions/0009_aps_document_processing_metadata.py` |
| Phase 8 APS bridge | **Closed** - All required APS-table materialization invariants satisfied (41 targets, 41 linkages, 40 distinct content IDs, 40 documents) using run `closure-run-005`. | `backend/app/services/nrc_adams_index_builder.py` run with `closure-run-005` on `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136` |
| Bounded Layer 3 APS evidence-bundle handoff consumer | Present as one additive Layer 3 consumer of the live APS evidence-bundle family; emits `aps_evidence_bundle_handoff` from already-packaged terminal Layer 3 sessions without widening APS contract/gate files. | `backend/app/services/layer3_aps_handoff.py`, `backend/tests/test_layer3_aps_handoff.py`, `next_milestone_plans/Layer3_planning_docs/09_GATED_APS_HANDOFF_FREEZE.md` |
| Bounded Layer 3 APS citation-pack handoff consumer | Present as one additive Layer 3 consumer of the live APS citation-pack family; emits `aps_evidence_citation_pack_handoff` from already-packaged terminal Layer 3 sessions without route/UI widening, runtime DB writes, or APS contract/gate widening. | `backend/app/services/layer3_aps_citation_handoff.py`, `backend/tests/test_layer3_aps_citation_handoff.py`, `next_milestone_plans/Layer3_planning_docs/10_GATED_APS_CITATION_FREEZE.md` |
| Bounded Layer 3 APS evidence-report handoff consumer | Present as one additive Layer 3 consumer of the live APS evidence-report family; emits `aps_evidence_report_handoff` from already-packaged terminal Layer 3 sessions without route/UI widening, runtime DB writes, or APS contract/gate widening. | `backend/app/services/layer3_aps_report_handoff.py`, `backend/tests/test_layer3_aps_report_handoff.py`, `next_milestone_plans/Layer3_planning_docs/11_GATED_APS_REPORT_FREEZE.md` |
| Bounded Layer 3 APS evidence-report-export handoff consumer | Present as one additive Layer 3 consumer of the live APS evidence-report-export family; emits `aps_evidence_report_export_handoff` from already-packaged terminal Layer 3 sessions without route/UI widening, runtime DB writes, or APS contract/gate widening. | `backend/app/services/layer3_aps_report_export_handoff.py`, `backend/tests/test_layer3_aps_report_export_handoff.py`, `next_milestone_plans/Layer3_planning_docs/12_GATED_APS_REPORT_EXPORT_FREEZE.md` |
| API/schema wiring for lower-layer controls | Present | `backend/app/schemas/api.py`, `backend/app/api/router.py` |
| Lower-layer fixture corpus | Present and manifest-driven | `tests/fixtures/nrc_aps_docs/v1/manifest.json`, `tests/support_nrc_aps_doc_corpus.py`, `tests/test_nrc_aps_document_corpus.py`, plus live text/PDF/corrupt/truncated fixtures including `tests/fixtures/nrc_aps_docs/v1/ML17123A319.pdf` |
| Fresh lower-layer proof runner | Present and current | `tools/run_nrc_aps_document_processing_proof.py`, `project6.ps1 -Action prove-nrc-aps-document-processing`, and `tests/reports/nrc_aps_document_processing_proof_report.json` |
| Focused lower-layer verification | Green (March 13 baseline; March 25 adds new coverage) | fresh isolated proof rerun on March 13, 2026: `46 passed` across lower-layer media-detection/document-processing/corpus/content-index/OCR-adapter tests plus `3 passed` API proof tests. March 25 hardening (`2f597f9`) added `backend/tests/test_diagnostics_ref_persistence.py` and expanded `backend/tests/test_nrc_aps_evidence_bundle_integration.py`; these test files are on disk but not yet reflected in a refreshed checked-in report. |
| Fresh lower-layer gate proof | Green in isolated temp runtime | `validate-nrc-aps-artifact-ingestion` and `validate-nrc-aps-content-index` both reran PASS on March 13, 2026 against a fresh isolated SQLite/runtime proof set built from repaired hydrate-process, download-only, and OCR-backed lower-layer paths |
| Upper-layer schema stability during lower-layer changes | Preserved | broader APS pytest rerun on March 13, 2026: `208 passed`; no upper `v1` schema ids were widened |
| Phase 7A Advanced Validation | `accepted-state` | Rerun on March 14, 2026: 43/43 files processed with real advanced OCR (19) and advanced table (28) evidence |

### Current proof freshness and remaining gaps
| Surface | Current state | Proof |
| --- | --- | --- |
| Fresh full aggregate NRC gate PASS after lower-layer expansion | Available; covers pre-March-25 state | rerun on March 13, 2026 via `./project6.ps1 -Action gate-nrc-aps`: aggregate pytest slice `143 passed, 29 deselected`, post-validator dossier ambiguity negative slice `1 passed, 55 deselected`, and aggregate validate-only reports refreshed to PASS through Deterministic Challenge Artifact. Note: March 25, 2026 hardening commits (`2f597f9`, `90c0c58`) changed diagnostics_ref resolution and visual artifact materialization behavior after this gate run. |
| Fresh bounded Layer 3 APS handoff proof | Available in this workspace for the merged bounded APS consumer slice | focused rerun on April 19, 2026: `51 passed, 2 warnings` across `backend/tests/test_layer3_aps_handoff.py`, `backend/tests/test_layer3_package_entry.py`, and `backend/tests/test_nrc_aps_evidence_bundle_integration.py` |
| Existing APS validation reports under `tests/reports/` | Partially fresh | refreshed in this workspace for the March 26 closeouts: `nrc_aps_content_index_validation_report.json`, `nrc_aps_evidence_bundle_validation_report.json`, and `nrc_aps_deterministic_challenge_review_packet_validation_report.json`; other checked-in APS reports remain prior generated artifacts unless explicitly rerun |
| Fresh live batch and promotion validation | Not rerun in this pass | existing manifests/reports remain available under `backend/app/storage/connectors/reports/` and `tests/reports/` |

## 3. Active lower-layer implementation state
### Media detection
- Header normalization is still used, but it is no longer the only decision surface.
- `aps_media_detection_v1` now performs deterministic byte sniffing for PDF, text, HTML, JSON, XML, PNG, JPEG, TIFF, ZIP, and unknown binary.
- Supported processing classes remain `application/pdf` and `text/plain`.
- HTML, JSON, XML, ZIP, and image signatures are refused explicitly as artifact bodies in the APS document-processing path.
- Generic or missing headers can now be overridden by a supported sniffed type; supported mismatches are processed with recorded degradation.

### Document extraction
- `aps_document_extraction_v1` now routes through `nrc_aps_document_processing.py`.
- Plain text decoding is BOM-aware and attempts UTF-8/UTF-16 before CP1252 fallback.
- PDF extraction now uses PyMuPDF block extraction instead of raw `latin-1` byte decoding.
- OCR support is wired through `nrc_aps_ocr.py` using the Tesseract CLI, with fixed language/DPI/timeout config surfaces.
- The OCR adapter now auto-detects the standard Windows install path `C:\Program Files\Tesseract-OCR\tesseract.exe` (and the x86 equivalent) in addition to `PATH` and `TESSERACT_CMD`.
- `content_parse_timeout_seconds` is now enforced cooperatively inside the lower-layer processing path.
- When OCR is required but unavailable, scanned PDFs fail closed and mixed PDFs degrade explicitly if native text still exists.

### Normalization and quality
- Lower-layer normalization contract is now `aps_text_normalization_v2`.
- Quality states are `strong`, `limited`, `weak`, and `unusable`.
- Weak and unusable extraction outcomes are preserved with provenance and diagnostics, but are excluded from downstream chunk indexing.

### Content indexing
- Content-unit schema is now `aps.content_units.v2`.
- Content contract is now `aps_content_units_v2`.
- Chunking contract is now `aps_chunking_v2`.
- Chunks are now built from ordered document units with page/unit metadata rather than pure raw-character slicing.
- DB metadata now includes media type, document class, quality status, page count, diagnostics refs, and chunk page spans/unit kinds.
- `download_only` reprocessing now persists a diagnostics artifact as part of content-index derivation.
- `diagnostics_ref` is authoritative at the run-target/linkage and content-artifact level; the deduplicated content-document row must not be treated as the authoritative diagnostics pointer across runs. Hardened March 25, 2026 (`2f597f9`): the upsert path now correctly persists `diagnostics_ref` from payload (prior code hardcoded `None`), and the serializer uses linkage-only authority via `_resolve_diagnostics_ref` with no document-level fallback.
- Visual artifact materialization in the production hydrate pipeline was corrected March 25, 2026 (`90c0c58`): `connectors_nrc_adams.py` now passes `artifact_storage_dir` from settings into the extraction config, enabling visual page refs to be written to storage during the hydrate-process path.

### Corpus and proof
- `tests/fixtures/nrc_aps_docs/v1/manifest.json` is now the executable corpus oracle rather than a descriptive inventory only.
- `tests/support_nrc_aps_doc_corpus.py` and `tests/test_nrc_aps_document_corpus.py` now drive lower-layer fixture expectations from that manifest.
- Representative fixtures now exist for UTF-8 text, UTF-16 text, born-digital PDF, layout/font-oriented PDFs, scanned/mixed PDFs, mismatch cases, and corrupt/truncated PDFs.
- The corpus now includes a representative real NRC PDF fixture at `tests/fixtures/nrc_aps_docs/v1/ML17123A319.pdf`, copied from the local example dropped under `data_demo/`.
- Real born-digital downstream usefulness is now proven in `tests/test_api.py` through content search and evidence-bundle persistence using extracted text rather than seeded synthetic chunks.
- OCR-backed downstream usefulness is now also proven in `tests/test_api.py` through the scanned fixture path when Tesseract is available.
- Current fresh OCR-enabled proof is recorded in:
  - `tests/reports/nrc_aps_document_processing_proof_report.json`
  - `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
  - `tests/reports/nrc_aps_content_index_validation_report.json`
- Fresh aggregate gate proof is now also recorded in:
  - `tests/reports/nrc_aps_evidence_bundle_validation_report.json`
  - `tests/reports/nrc_aps_evidence_citation_pack_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_package_validation_report.json`
  - `tests/reports/nrc_aps_context_packet_validation_report.json`
  - `tests/reports/nrc_aps_context_dossier_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_insight_artifact_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_challenge_artifact_validation_report.json`
- OCR-success is now proven in this workspace. Tesseract remains an external prerequisite for reproducing that proof elsewhere.

### Phase 7 / 7A: Advanced capabilities
- `nrc_aps_advanced_table_parser.py` implements borderless table extraction using Camelot and Ghostscript.
- `nrc_aps_advanced_ocr.py` implements high-accuracy OCR using local PaddleOCR models.
- Advanced routing is triggered by category-based rules (`Technical Specification Amendment`, etc.) OR health-based triggers (low-quality native text detection).
- Phase 7A validation proved these capabilities on 43 real NRC ADAMS documents.
- Verified counts: 19 files utilized Advanced OCR, 28 files utilized Advanced Tables.
- Advanced environment provenance: Requires Python 3.11, `paddleocr` (v2.10.0), `camelot-py` (v1.0.9), and Ghostscript.

## 4. Closed layers
These layers remain closed/frozen except for defect-driven work:
- replay regression control
- 2A sync delta / drift correctness
- operational safeguards
- 2B promotion governance
- evidence retrieval / assembly
- citation-pack v1
- evidence-report v1
- evidence-report export v1
- evidence-report export package v1
- Context Packet v1
- Context Dossier v1
- Deterministic Insight Artifact v1
- Deterministic Challenge Artifact v1
- Deterministic Challenge Review Packet v1

Important correction:
- artifact ingestion and content indexing are no longer treated as closed/frozen in this document-processing workstream
- upper analytical schemas remain frozen while lower-layer document/media handling evolves additively

## 5. Lower-layer contract and schema inventory
### New or updated lower-layer contracts
- `aps_media_detection_v1`
- `aps_document_extraction_v1`
- `aps_text_normalization_v2`
- `aps_content_units_v2`
- `aps_chunking_v2`

### Persisted lower-layer metadata surfaces
- declared/sniffed/effective content type
- media detection contract/status/reason
- document class
- extractor family/id/version
- quality status and degradation codes
- page count
- diagnostics refs
- chunk page spans and unit kind

### Schema/migration authority
- DB/model changes live in `backend/app/models/models.py`
- schema migration lives in `backend/alembic/versions/0009_aps_document_processing_metadata.py`
- API request/response wiring lives in `backend/app/schemas/api.py`

## 6. Operator and validation notes
- Existing `validate-*` actions remain validate-only, fail closed on empty runtime, and must not seed artifacts.
- `project6.ps1` remains the operator entrypoint for migrations and APS validators.
- `project6.ps1 -Action prove-nrc-aps-document-processing` is now the fresh isolated lower-layer proof runner for this reopened workstream. It is not a validate-only action: it builds isolated runtime state, runs lower-layer pytest proof, then invokes the existing validate-only artifact-ingestion and content-index gates against that isolated runtime.
- OCR success paths remain environment-dependent because Tesseract is not bundled in the repo, but the current workspace now has a passing OCR-enabled proof run.
- For the shipped review/document-trace/workbench/Candidate B Trace operator flow on current `main`, use:
  - `frontend_UI_plans/README.md` as the front-door index
  - `frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md` for explicit backend binding and route bring-up
  - `frontend_UI_plans/wb-compare-validation.md` for same-checkout prep and the `tools/validate_wb_prep.py` readiness gate
  - `frontend_UI_plans/nrc_aps_frontend_ui_operator_validation_guide.md` for the broader manual validation pass after startup and prep succeed

## 7. Current explicit limits
- Tesseract CLI availability is an external prerequisite for scanned/mixed PDF OCR success.
- In a no-Tesseract environment, scanned PDFs fail closed with `ocr_required_but_unavailable`, and mixed PDFs may degrade to weak/native-only output.
- The current merged `main` state now includes bounded Layer 3 APS evidence-bundle, citation-pack, evidence-report, and evidence-report-export handoff tranches: `aps_evidence_bundle_handoff`, `aps_evidence_citation_pack_handoff`, `aps_evidence_report_handoff`, and `aps_evidence_report_export_handoff` emitted from already-packaged terminal Layer 3 sessions without route/UI widening, runtime DB writes, or APS contract/gate widening. Later APS families remain deferred.
- The checked-in fixture corpus now proves manifest-driven parser routing, degradation semantics, downstream usefulness for representative born-digital content, and OCR-success usefulness for the scanned/mixed corpus fixtures in this workspace.
- The current checked-in lower-layer proof basis in this workspace (covers behavior through March 13, 2026) is:
  - `tests/reports/nrc_aps_document_processing_proof_report.json`
  - `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
  - `tests/reports/nrc_aps_content_index_validation_report.json`
- The current checked-in fresh aggregate gate proof basis in this workspace (covers behavior through March 13, 2026) is:
  - `tests/reports/nrc_aps_evidence_bundle_validation_report.json`
  - `tests/reports/nrc_aps_evidence_citation_pack_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_package_validation_report.json`
  - `tests/reports/nrc_aps_context_packet_validation_report.json`
  - `tests/reports/nrc_aps_context_dossier_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_insight_artifact_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_challenge_artifact_validation_report.json`
- The current checked-in dedicated post-challenge validate-only proof basis in this workspace is:
  - `tests/reports/nrc_aps_deterministic_challenge_review_packet_validation_report.json`
- March 25, 2026 hardening commits (`2f597f9`, `90c0c58`) changed diagnostics_ref resolution semantics and visual artifact materialization behavior. Proof of those changes still lives in `backend/tests/test_diagnostics_ref_persistence.py` and the expanded `backend/tests/test_nrc_aps_evidence_bundle_integration.py`. The narrow March 26, 2026 Tier2 closeout resolved the local diagnostics-write blocker and refreshed `tests/reports/nrc_aps_content_index_validation_report.json` plus `tests/reports/nrc_aps_evidence_bundle_validation_report.json` in this workspace. The post-commit March 26, 2026 review-packet closeout refreshed `tests/reports/nrc_aps_deterministic_challenge_review_packet_validation_report.json` via the dedicated validate-only action from current `HEAD`; other checked-in `tests/reports/*.json` artifacts remain historical unless regenerated separately.
- Other checked-in `tests/reports/*.json` artifacts should still be treated as historical snapshots unless explicitly regenerated in the current verification pass.
- **Phase 7A Validation Package**: `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136`
- **Phase 7A Artifact Audit**: `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136/artifact_audit`

## 8. Recommended next continuation
The next safe continuation is:
1. preserve the restored lower-layer baseline and current OCR-enabled proof basis
2. treat the bounded Layer 3 APS export-derived context-packet handoff slice as the current additive ceiling extension on current `main`, not as permission to widen into export-package implementation, package-derived context, dossier, deterministic, or later APS families
3. treat `next_milestone_plans/Layer3_planning_docs/13_GATED_APS_CONTEXT_FREEZE.md` as the governing carried-forward contract for that bounded direct export-derived context-packet slice only, not as permission to widen directly into later shared APS families
4. treat the bounded Layer 3 APS multisource admission slice as the current additive ceiling extension in the current branch state beyond current `main`, not as permission to widen into export-package implementation, package-derived context, dossier, deterministic, or later APS families
5. treat `next_milestone_plans/Layer3_planning_docs/14_GATED_APS_MULTISOURCE_FREEZE.md` as the governing carried-forward contract for that bounded shared same-run source-admission slice only, not as permission to widen directly into export-package implementation, package-derived context, dossier, deterministic, or later APS families
6. rerun `.\project6.ps1 -Action prove-nrc-aps-document-processing -RequireOcr` when OCR/corpus behavior changes, and treat `.\project6.ps1 -Action validate-nrc-aps-content-index` plus `.\project6.ps1 -Action validate-nrc-aps-evidence-bundle` as the validate-only refresh path for those checked-in reports

## 9. Primary live authority surfaces for this workstream
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `backend/app/models/models.py`
- `backend/app/services/layer3_session_entry.py`
- `backend/app/services/layer3_typing_entry.py`
- `backend/app/services/layer3_package_entry.py`
- `backend/app/services/layer3_aps_handoff.py`
- `backend/app/services/layer3_aps_citation_handoff.py`
- `backend/app/services/layer3_aps_report_handoff.py`
- `backend/app/services/layer3_aps_report_export_handoff.py`
- `backend/app/services/layer3_aps_context_packet_handoff.py`
- `backend/app/services/layer3_aps_multisource.py`
- `backend/tests/test_layer3_session_entry.py`
- `backend/tests/test_layer3_typing_entry.py`
- `backend/tests/test_layer3_package_entry.py`
- `backend/tests/test_layer3_aps_handoff.py`
- `backend/tests/test_layer3_aps_citation_handoff.py`
- `backend/tests/test_layer3_aps_report_handoff.py`
- `backend/tests/test_layer3_aps_report_export_handoff.py`
- `backend/tests/test_layer3_aps_context_packet_handoff.py`
- `backend/tests/test_layer3_aps_multisource.py`
- `next_milestone_plans/Layer3_planning_docs/10_GATED_APS_CITATION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/11_GATED_APS_REPORT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/12_GATED_APS_REPORT_EXPORT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/13_GATED_APS_CONTEXT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/14_GATED_APS_MULTISOURCE_FREEZE.md`
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_media_detection.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_ocr.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/nrc_aps_evidence_bundle_contract.py`
- `backend/app/services/nrc_aps_evidence_bundle.py`
- `backend/app/services/nrc_aps_evidence_citation_pack_contract.py`
- `backend/app/services/nrc_aps_evidence_citation_pack.py`
- `backend/app/services/nrc_aps_evidence_citation_pack_gate.py`
- `backend/app/services/nrc_aps_evidence_report_contract.py`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_evidence_report_gate.py`
- `backend/app/services/nrc_aps_evidence_report_export_contract.py`
- `backend/app/services/nrc_aps_evidence_report_export.py`
- `backend/app/services/nrc_aps_evidence_report_export_gate.py`
- `backend/app/services/nrc_aps_context_packet_contract.py`
- `backend/app/services/nrc_aps_context_packet.py`
- `backend/app/services/nrc_aps_context_packet_gate.py`
- `backend/app/models/models.py`
- `backend/app/schemas/api.py`
- `backend/alembic/versions/0009_aps_document_processing_metadata.py`
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/support_nrc_aps_doc_corpus.py`
- `tests/test_nrc_aps_media_detection.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/test_nrc_aps_document_corpus.py`
- `tests/test_nrc_aps_artifact_ingestion.py`
- `tests/test_nrc_aps_content_index.py`
- `tests/test_nrc_aps_content_index_gate.py`
- `tests/test_nrc_aps_evidence_citation_pack.py`
- `tests/test_nrc_aps_evidence_citation_pack_gate.py`
- `tests/test_nrc_aps_evidence_report.py`
- `tests/test_nrc_aps_evidence_report_gate.py`
- `tests/test_nrc_aps_context_packet.py`
- `tests/test_nrc_aps_context_packet_gate.py`
- `tests/test_api.py`
- `backend/tests/test_layer3_aps_handoff.py`
- `backend/tests/test_diagnostics_ref_persistence.py`
- `backend/tests/test_nrc_aps_evidence_bundle_integration.py`
- `tools/run_nrc_aps_document_processing_proof.py`
- `tests/reports/nrc_aps_document_processing_proof_report.json`

## 10. Closed Phase 8 Boundary
- **Closed milestone**: Downstream bridge reconciliation and validation from accepted Phase 7A outputs into the APS content tables.
- **Closure criterion satisfied**: Successful population of the APS content tables (`ApsContentDocument`, `ApsContentChunk`, `ApsContentLinkage`); Evidence Bundle execution remained a downstream consumer and was **not** required for closure.
- **Authoritative inputs used for closure**:
  - Content Schema: `aps_content_units_v2` (extracted text units, table markdown units, quality metadata)
  - Validation Basis: `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136`
  - Audit Basis: `backend/app/storage_test_runtime/advanced_validation_runs/run_20260314_010136/artifact_audit`
- **Immutable Facts**: OCR (19) and Table (28) counts are frozen as verified in the Artifact Audit.
- **Do Not Reopen**: Ingestion routing logic and advanced capability adapters are considered stable/frozen for this closed bridge milestone.

## 11. Phase 7A Closeout Archive
- **Closeout Package**: [handoff/phase_7a_closeout/](../../handoff/phase_7a_closeout/)
- **Audit Findings**: Corroborated internal consistency and evidence provenance.
