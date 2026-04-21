# NRC ADAMS APS Status Handoff

## 1. Purpose and truth model
This document is the canonical live-repo status surface for the NRC ADAMS APS stack. Last updated April 21, 2026 to reflect the bounded Layer 3 APS export-derived context-packet, multisource, evidence-report-export-package, package-derived-context, context-dossier, deterministic-insight, deterministic-challenge, deterministic challenge review-packet, and dedicated validate-only runtime/report-ref handoff slices now landed on current `main`, the landed export-package first shared-consumer freeze, package-derived-context freeze, context-dossier freeze, deterministic-insight continuation freeze, deterministic-challenge continuation freeze, deterministic challenge review-packet continuation freeze, validate-only-gates continuation freeze, and dedicated validate-only runtime/report-ref continuation freeze now all landed on current `main`, the post-PR136 docs/progress sync now also landed on current `main`, the bounded validate-only gate-report refresh slice now also landed on current `main` from PR `#138`, the post-PR138 docs/progress sync now also landed on current `main` from PR `#139`, the merged malformed-scoped candidate-discovery closeout now also landed on current `main`, the merged deterministic-gate exact-run hardening now also landed on current `main`, the post-PR140 docs/progress sync from PR `#141`, the post-PR141 docs/progress sync from PR `#142`, and the bounded dedicated validate-only runtime/report-ref implementation slice now also landed on current `main` from PR `#143`, on top of the earlier bounded evidence-bundle, citation-pack, evidence-report, and evidence-report-export handoff slices landed on current `main`, the Deterministic Challenge Review Packet v1 closeout, and the narrow Tier2 diagnostics-write closeout.

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
| Bounded Layer 3 APS export-derived context-packet handoff consumer | Present as one additive Layer 3 consumer of the live APS context-packet family; emits `aps_context_packet_handoff` from already-packaged terminal Layer 3 sessions using direct export-derived sources without route/UI widening, runtime DB writes, or APS contract/gate widening. | `backend/app/services/layer3_aps_context_packet_handoff.py`, `backend/tests/test_layer3_aps_context_packet_handoff.py`, `next_milestone_plans/Layer3_planning_docs/13_GATED_APS_CONTEXT_FREEZE.md` |
| Bounded Layer 3 APS same-run multisource admission consumer | Present as one additive Layer 3 consumer of the live shared-source admission boundary; emits `aps_multisource_admission` from already-packaged terminal Layer 3 sessions using existing durable same-run grouping seams without route/UI widening, runtime DB writes, or schema widening. | `backend/app/services/layer3_aps_multisource.py`, `backend/tests/test_layer3_aps_multisource.py`, `next_milestone_plans/Layer3_planning_docs/14_GATED_APS_MULTISOURCE_FREEZE.md` |
| Bounded Layer 3 APS evidence-report-export-package handoff consumer | Present as one additive Layer 3 consumer of the live APS evidence-report-export-package family; emits `aps_evidence_report_export_package_handoff` from `aps_multisource_admission` plus matched persisted same-run exports while keeping route/UI, runtime DB, and schema widening out. Current `main` also now includes the narrow export/export-package gate hardening that filters exact embedded run identity under sanitized filename-scope collisions. | `backend/app/services/layer3_aps_report_export_package_handoff.py`, `backend/app/services/nrc_aps_evidence_report_export_gate.py`, `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`, `backend/tests/test_layer3_aps_report_export_handoff.py`, `backend/tests/test_layer3_aps_report_export_package_handoff.py`, `next_milestone_plans/Layer3_planning_docs/15_GATED_APS_EXPORT_PACKAGE_FREEZE.md` |
| Bounded Layer 3 APS package-derived context handoff consumer | Present as one additive Layer 3 consumer of the live APS context-packet package family; emits `aps_context_packet_package_handoff` from `aps_evidence_report_export_package_handoff` while keeping route/UI, runtime DB, and schema widening out. Current `main` now also includes the adjacent export, export-package, and context-packet gate hardening that preserves exact owner-run filtering and closes malformed-scoped candidate discovery when `run_ids` are omitted. | `backend/app/services/layer3_aps_context_packet_package_handoff.py`, `backend/app/services/nrc_aps_evidence_report_export_gate.py`, `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`, `backend/app/services/nrc_aps_context_packet_gate.py`, `backend/tests/test_layer3_aps_report_export_handoff.py`, `backend/tests/test_layer3_aps_report_export_package_handoff.py`, `backend/tests/test_layer3_aps_context_packet_handoff.py`, `backend/tests/test_layer3_aps_context_packet_package_handoff.py`, `next_milestone_plans/Layer3_planning_docs/16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md` |
| Bounded Layer 3 APS context-dossier handoff consumer | Present as one additive Layer 3 consumer of the live APS context-dossier family; emits `aps_context_dossier_handoff` from the landed package-derived context handoff only as gating provenance, then resolves the actual dossier inputs from the paired persisted export-derived context packets required by the live dossier contract. Current `main` also now includes the narrow dossier-gate scope hardening that preserves exact owner-run filtering under sanitized filename-scope collisions. | `backend/app/services/layer3_aps_context_dossier_handoff.py`, `backend/app/services/nrc_aps_context_dossier_gate.py`, `backend/tests/test_layer3_aps_context_dossier_handoff.py`, `next_milestone_plans/Layer3_planning_docs/17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md` |
| Bounded Layer 3 APS deterministic-insight handoff consumer | Present as one additive Layer 3 consumer of the live APS deterministic-insight family; emits `aps_deterministic_insight_artifact_handoff` from one persisted `aps_context_dossier_handoff` package while leaving `ConnectorRun.query_plan_json` runtime refs and summaries untouched. Current `main` now also includes narrow deterministic-gate hardening that restores exact owner-run filtering under sanitized filename-scope collisions and keeps malformed-scoped candidate discovery fail-closed. | `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py`, `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`, `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`, `next_milestone_plans/Layer3_planning_docs/18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md` |
| Read-only Gate D APS deterministic-challenge continuation freeze | Landed on current `main`; selects `deterministic_challenge_artifact` as the next deterministic continuation beyond the landed deterministic-insight boundary without admitting challenge implementation, challenge-review-packet fan-out, validate-only expansion, route/UI, runtime DB, or schema widening. | `next_milestone_plans/Layer3_planning_docs/19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`, `backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`, `backend/app/services/review_nrc_aps_graph.py` |
| Bounded Layer 3 APS deterministic-challenge handoff consumer | Present as one additive Layer 3 consumer of the live APS deterministic-challenge family; emits `aps_deterministic_challenge_artifact_handoff` from one persisted `aps_deterministic_insight_artifact_handoff` package while leaving `ConnectorRun.query_plan_json` runtime refs and summaries untouched. Current `main` now also includes narrow deterministic challenge gate hardening that restores exact owner-run filtering under sanitized filename-scope collisions and keeps malformed-scoped candidate discovery fail-closed. | `backend/app/services/layer3_aps_deterministic_challenge_artifact_handoff.py`, `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`, `backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py`, `next_milestone_plans/Layer3_planning_docs/19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md` |
| Read-only Gate D APS deterministic challenge review-packet continuation freeze | Landed on current `main`; selects `deterministic_challenge_review_packet` as the next deterministic continuation beyond the landed deterministic challenge handoff while keeping validate-only gates later and still excluding route/UI, runtime DB, and schema widening. | `next_milestone_plans/Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md`, `backend/app/services/nrc_aps_deterministic_challenge_review_packet_contract.py`, `backend/app/services/nrc_aps_deterministic_challenge_review_packet.py`, `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`, `backend/app/services/review_nrc_aps_graph.py` |
| Bounded Layer 3 APS deterministic challenge review-packet handoff consumer | Present as one additive Layer 3 consumer of the live APS deterministic challenge review-packet family; emits `aps_deterministic_challenge_review_packet_handoff` from one persisted `aps_deterministic_challenge_artifact_handoff` package while leaving `ConnectorRun.query_plan_json` runtime refs and summaries untouched. Current `main` now also includes narrow review-packet gate hardening that restores exact owner-run filtering under sanitized filename-scope collisions and keeps malformed-scoped candidate discovery fail-closed. | `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py`, `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`, `backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py`, `next_milestone_plans/Layer3_planning_docs/20_GATED_APS_REVIEW_PACKET_FREEZE.md` |
| Read-only Gate D APS validate-only-gates continuation freeze | Landed on current `main` from PR `#136`; selects `validate_only_gates` as the exact next verification continuation beyond the landed deterministic challenge review-packet handoff while making explicit that current `main` still relies on generic `gate_reports` plus `gate_results` surfaces rather than a dedicated validate-only runtime family. | `next_milestone_plans/Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md`, `backend/app/services/review_nrc_aps_graph.py`, `backend/app/services/review_nrc_aps_tree.py`, `backend/tests/test_review_nrc_aps_graph.py`, `project6.ps1`, `backend/app/services/connectors_sciencebase.py` |
| Bounded Layer 3 APS validate-only gate-report refresh slice | Landed on current `main` from PR `#138`; refreshes one adopted review runtime's `gate_reports/*.json` plus `summary.gate_results` from the existing generic validate-only gates without seeding artifacts or widening promotion, retrieval cutover, route/UI, runtime DB, schema, or a dedicated validate-only runtime family. | `backend/app/services/review_nrc_aps_gate_reports.py`, `tools/nrc_aps_refresh_review_gate_reports.py`, `tools/run_nrc_aps_local_corpus_e2e.py`, `backend/tests/test_review_nrc_aps_gate_reports.py`, `project6.ps1`, `next_milestone_plans/Layer3_planning_docs/21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md` |
| Read-only Gate D APS dedicated validate-only runtime/report-ref continuation freeze | Landed on current `main` from PR `#140`; selects the dedicated `validate_only_gates` family-specific runtime/report-ref decision as the next bounded continuation beyond the landed generic gate-report refresh lane while still excluding implementation, promotion, retrieval cutover, route/UI, runtime DB, and schema widening. | `next_milestone_plans/Layer3_planning_docs/22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`, `backend/app/services/connectors_sciencebase.py`, `backend/app/services/review_nrc_aps_graph.py`, `backend/app/services/review_nrc_aps_tree.py`, `backend/app/services/review_nrc_aps_gate_reports.py`, `project6.ps1` |
| Bounded Layer 3 APS dedicated validate-only runtime/report-ref implementation slice | Landed on current `main` from PR `#143`; adds the dedicated validate-only contract/runtime/gate trio plus run-level report-ref registry, review graph/tree, shared runtime-binding, operator entrypoint integration, and narrow validate-only boundary hardening while preserving the landed generic gate-report refresh lane as the immediate upstream truth and still excluding later validate-only top-chain expansion, promotion, retrieval cutover, route/UI, runtime DB, and schema widening. | `backend/app/services/nrc_aps_validate_only_gates_contract.py`, `backend/app/services/nrc_aps_validate_only_gates.py`, `backend/app/services/nrc_aps_validate_only_gates_gate.py`, `backend/app/services/review_nrc_aps_runtime.py`, `backend/app/services/review_nrc_aps_gate_reports.py`, `backend/app/services/review_nrc_aps_graph.py`, `backend/app/services/review_nrc_aps_tree.py`, `backend/app/services/connectors_sciencebase.py`, `backend/tests/test_nrc_aps_validate_only_gates.py`, `tools/nrc_aps_refresh_validate_only_gates.py`, `tools/nrc_aps_validate_only_gates_gate.py`, `project6.ps1` |
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
| Fresh bounded Layer 3 APS continuation proof | Available in this workspace for the current merged export-package, package-derived-context, context-dossier, deterministic-insight, deterministic-challenge, and deterministic challenge review-packet handoff slices, plus the merged export/export-package/context-packet/dossier/deterministic/review-packet gate hardening follow-ups | focused rerun on April 21, 2026: `90 passed, 2 warnings` across `backend/tests/test_layer3_session_entry.py`, `backend/tests/test_layer3_typing_entry.py`, `backend/tests/test_layer3_pass_entry.py`, `backend/tests/test_layer3_package_entry.py`, `backend/tests/test_layer3_aps_handoff.py`, `backend/tests/test_layer3_aps_citation_handoff.py`, `backend/tests/test_layer3_aps_report_handoff.py`, `backend/tests/test_layer3_aps_report_export_handoff.py`, `backend/tests/test_layer3_aps_report_export_package_handoff.py`, `backend/tests/test_layer3_aps_context_packet_handoff.py`, `backend/tests/test_layer3_aps_context_packet_package_handoff.py`, `backend/tests/test_layer3_aps_context_dossier_handoff.py`, `backend/tests/test_layer3_aps_multisource.py`, `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`, `backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py`, and `backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py` |
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
- The current merged `main` state now includes bounded Layer 3 APS evidence-bundle, citation-pack, evidence-report, evidence-report-export, export-derived context-packet, multisource-admission, export-package first shared-consumer freeze, export-package handoff, and narrow export/export-package gate-hardening tranches: `aps_evidence_bundle_handoff`, `aps_evidence_citation_pack_handoff`, `aps_evidence_report_handoff`, `aps_evidence_report_export_handoff`, `aps_context_packet_handoff`, `aps_multisource_admission`, the landed `15_GATED_APS_EXPORT_PACKAGE_FREEZE.md` selection freeze, `aps_evidence_report_export_package_handoff`, plus the exact-run gate hardening in `nrc_aps_evidence_report_export_gate.py` and `nrc_aps_evidence_report_export_package_gate.py`. Later APS families remain deferred.
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
2. treat the bounded Layer 3 APS export-derived context-packet, multisource, and export-package handoff slices plus the landed `15_GATED_APS_EXPORT_PACKAGE_FREEZE.md` selection freeze and the merged narrow export/export-package gate hardening as the current additive ceiling extensions on current `main`, not as permission to widen directly into later APS families
3. current `main` now includes the read-only `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md` package-derived-context freeze from the landed export-package boundary; it settles the next later shared-family choice without admitting implementation by itself
4. treat the landed `aps_evidence_report_export_package_handoff` slice, the merged exact-run gate hardening, and the now-landed `16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md` freeze as proof that the bounded export-package boundary and the next later shared-family choice are now on current `main`, but not as permission to skip straight into `context_dossier`, deterministic, or route/UI widening
5. current `main` now also includes the bounded package-derived context handoff implementation slice rooted in `backend/app/services/layer3_aps_context_packet_package_handoff.py` and `backend/tests/test_layer3_aps_context_packet_package_handoff.py`, plus the narrow APS gate hardening that keeps exact owner-run filtering and malformed scoped artifacts fail-closed in `backend/app/services/nrc_aps_evidence_report_export_gate.py`, `backend/app/services/nrc_aps_evidence_report_export_package_gate.py`, and `backend/app/services/nrc_aps_context_packet_gate.py`
6. current `main` now also includes the read-only `17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md` freeze selecting `context_dossier` as the next later shared APS family after the landed package-context milestone while preserving paired export-derived context packets as the live dossier input branch
7. current `main` now also includes the bounded `context_dossier` handoff implementation lane rooted in `backend/app/services/layer3_aps_context_dossier_handoff.py` and `backend/tests/test_layer3_aps_context_dossier_handoff.py`, plus the narrow dossier-gate scope hardening in `backend/app/services/nrc_aps_context_dossier_gate.py`; it preserves paired export-derived context packets as dossier inputs and does not widen route/UI, runtime DB, schema, or later deterministic families by itself
8. current `main` now also includes the read-only `18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md` freeze selecting `deterministic_insight_artifact` as the next deterministic continuation beyond the landed dossier boundary; that landed freeze settles deterministic insight as the first deterministic continuation without admitting challenge/review-packet, route/UI, runtime DB, or schema widening by itself
9. current `main` now also includes the bounded deterministic-insight handoff lane rooted in `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py` and `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`, plus the narrow deterministic-gate hardening in `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`; that landed lane preserves one persisted dossier as the deterministic source boundary, leaves `ConnectorRun.query_plan_json` untouched, and does not widen challenge/review-packet, validate-only, route/UI, runtime DB, or schema surfaces
10. current `main` now also includes the read-only `19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md` freeze selecting `deterministic_challenge_artifact` as the next deterministic continuation beyond the landed deterministic-insight handoff; that landed freeze still does not admit implementation, challenge-review-packet fan-out, validate-only expansion, route/UI, runtime DB, or schema widening by itself
11. current `main` now also includes the bounded deterministic-challenge handoff lane rooted in `backend/app/services/layer3_aps_deterministic_challenge_artifact_handoff.py` and `backend/tests/test_layer3_aps_deterministic_challenge_artifact_handoff.py`, plus the narrow deterministic challenge gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`; that landed lane preserves one persisted deterministic insight artifact as the immediate source boundary, leaves `ConnectorRun.query_plan_json` untouched, and still does not admit challenge-review-packet fan-out, validate-only expansion, route/UI, runtime DB, or schema widening by itself
12. current `main` now also includes the landed read-only `20_GATED_APS_REVIEW_PACKET_FREEZE.md` freeze from PR `#132`, selecting `deterministic_challenge_review_packet` as the next deterministic continuation beyond the now-landed deterministic challenge handoff while keeping validate-only gates later
13. current `main` now also includes the bounded deterministic challenge review-packet handoff lane rooted in `backend/app/services/layer3_aps_deterministic_challenge_review_packet_handoff.py`, the focused proof in `backend/tests/test_layer3_aps_deterministic_challenge_review_packet_handoff.py`, the narrow review-packet gate hardening in `backend/app/services/nrc_aps_deterministic_challenge_review_packet_gate.py`, and the post-PR134 docs/progress sync from PR `#135`
14. current `main` now also includes the read-only `21_GATED_APS_VALIDATE_ONLY_GATES_FREEZE.md` freeze from PR `#136`, selecting `validate_only_gates` as the exact next verification continuation beyond that landed review-packet handoff while keeping validate-only execution/report refresh, promotion, retrieval cutover, route/UI, runtime DB, and schema widening later
15. current `main` now also includes the bounded validate-only gate-report refresh lane from PR `#138`, rooted in `backend/app/services/review_nrc_aps_gate_reports.py`, `tools/nrc_aps_refresh_review_gate_reports.py`, `tools/run_nrc_aps_local_corpus_e2e.py`, `backend/tests/test_review_nrc_aps_gate_reports.py`, and `project6.ps1`; it refreshes one adopted review runtime's `gate_reports/*.json` plus `summary.gate_results`, stays validate-only and fail-closed on missing runtime, and does not widen promotion, retrieval cutover, route/UI, runtime DB, schema, or a dedicated validate-only runtime family-specific stack
16. current `main` now also includes the read-only `22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md` freeze from PR `#140`; it settles the next continuation as a dedicated validate-only family-specific runtime/report-ref decision beyond the landed generic gate-report boundary, while still not admitting direct implementation, promotion, retrieval cutover, route/UI, runtime DB, or schema widening
17. current `main` now also includes the bounded dedicated validate-only runtime/report-ref implementation slice from PR `#143`, rooted in `backend/app/services/nrc_aps_validate_only_gates_contract.py`, `backend/app/services/nrc_aps_validate_only_gates.py`, `backend/app/services/nrc_aps_validate_only_gates_gate.py`, and `backend/tests/test_nrc_aps_validate_only_gates.py`, plus the bounded downstream integrations in `backend/app/services/review_nrc_aps_runtime.py`, `backend/app/services/review_nrc_aps_gate_reports.py`, `backend/app/services/review_nrc_aps_graph.py`, `backend/app/services/review_nrc_aps_tree.py`, `backend/app/services/connectors_sciencebase.py`, `tools/nrc_aps_refresh_validate_only_gates.py`, `tools/nrc_aps_validate_only_gates_gate.py`, and `project6.ps1`; that landed lane keeps the landed generic gate-report refresh boundary as upstream truth and still does not admit later validate-only top-chain expansion, promotion, retrieval cutover, route/UI, runtime DB, or schema widening
18. rerun `.\project6.ps1 -Action prove-nrc-aps-document-processing -RequireOcr` when OCR/corpus behavior changes, treat `.\project6.ps1 -Action validate-nrc-aps-content-index` plus `.\project6.ps1 -Action validate-nrc-aps-evidence-bundle` as the validate-only refresh path for checked-in reports, use `.\project6.ps1 -Action refresh-nrc-aps-review-gate-reports -NrcApsRunId <run_id>` for adopted review-runtime `gate_reports` plus `summary.gate_results`, and use the now-landed bounded dedicated validate-only entrypoints `.\project6.ps1 -Action refresh-nrc-aps-validate-only-gates -NrcApsRunId <run_id>` plus `.\project6.ps1 -Action validate-nrc-aps-validate-only-gates [-NrcApsRunId <run_id>]` for the dedicated validate-only runtime/report-ref lane on current `main`
19. current `main` now also includes the landed read-only `23_GATED_APS_PROMOTION_FREEZE.md` freeze from PR `#145`; it selects promotion as the first later APS family beyond the landed dedicated validate-only runtime/report-ref boundary while keeping retrieval cutover later

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
- `backend/app/services/layer3_aps_report_export_package_handoff.py`
- `backend/app/services/layer3_aps_context_packet_package_handoff.py`
- `backend/app/services/layer3_aps_context_dossier_handoff.py`
- `backend/app/services/nrc_aps_context_packet_gate.py`
- `backend/app/services/nrc_aps_context_dossier_gate.py`
- `backend/app/services/layer3_aps_deterministic_insight_artifact_handoff.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact_contract.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact.py`
- `backend/app/services/nrc_aps_deterministic_insight_artifact_gate.py`
- `backend/app/services/nrc_aps_deterministic_challenge_artifact_contract.py`
- `backend/app/services/nrc_aps_deterministic_challenge_artifact.py`
- `backend/app/services/nrc_aps_deterministic_challenge_artifact_gate.py`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/review_nrc_aps_tree.py`
- `backend/app/services/review_nrc_aps_gate_reports.py`
- `backend/app/services/review_nrc_aps_details.py`
- `backend/tests/test_layer3_session_entry.py`
- `backend/tests/test_layer3_typing_entry.py`
- `backend/tests/test_layer3_package_entry.py`
- `backend/tests/test_layer3_aps_handoff.py`
- `backend/tests/test_layer3_aps_citation_handoff.py`
- `backend/tests/test_layer3_aps_report_handoff.py`
- `backend/tests/test_layer3_aps_report_export_handoff.py`
- `backend/tests/test_layer3_aps_context_packet_handoff.py`
- `backend/tests/test_layer3_aps_multisource.py`
- `backend/tests/test_layer3_aps_report_export_package_handoff.py`
- `backend/tests/test_layer3_aps_context_packet_package_handoff.py`
- `backend/tests/test_layer3_aps_context_dossier_handoff.py`
- `backend/tests/test_layer3_aps_deterministic_insight_artifact_handoff.py`
- `backend/tests/test_review_nrc_aps_gate_reports.py`
- `next_milestone_plans/Layer3_planning_docs/22_GATED_APS_VALIDATE_ONLY_RUNTIME_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/10_GATED_APS_CITATION_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/11_GATED_APS_REPORT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/12_GATED_APS_REPORT_EXPORT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/13_GATED_APS_CONTEXT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/14_GATED_APS_MULTISOURCE_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/15_GATED_APS_EXPORT_PACKAGE_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/16_GATED_APS_PACKAGE_CONTEXT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/17_GATED_APS_CONTEXT_DOSSIER_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/18_GATED_APS_DETERMINISTIC_INSIGHT_FREEZE.md`
- `next_milestone_plans/Layer3_planning_docs/19_GATED_APS_DETERMINISTIC_CHALLENGE_FREEZE.md`
- `backend/app/services/nrc_aps_evidence_report_export_package_contract.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`
- `backend/app/services/nrc_aps_context_packet_contract.py`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/connectors_nrc_adams.py`
- `tools/nrc_aps_refresh_review_gate_reports.py`
- `tools/run_nrc_aps_local_corpus_e2e.py`
- `project6.ps1`
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
