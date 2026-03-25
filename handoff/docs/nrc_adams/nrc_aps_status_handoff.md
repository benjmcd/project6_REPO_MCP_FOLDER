# NRC ADAMS APS Status Handoff

Package-local note: this copy is a handoff control surface in the mixed package model. When both repo root and `handoff/` are available, live root authority remains `docs/nrc_adams/nrc_aps_status_handoff.md`.

## 1. Purpose and truth model
This document is the canonical package-local status surface for the portable NRC ADAMS APS handoff package as of March 13, 2026.

Repo truth precedence used here:
1. live code, tests, scripts, migrations, and repo-contained proof artifacts
2. live root docs, especially `docs/nrc_adams/nrc_aps_status_handoff.md`
3. package-local handoff controls
4. older planning/history only when not contradicted by the live repo

Status wording used below:
- `repo-confirmed in this workspace`
- `carried-forward but not revalidated here`
- `inferred from repo shape`

## 2. Current package-safe summary
### Repo-confirmed in this workspace
| Surface | Current state | Proof |
| --- | --- | --- |
| Upper analytical ceiling | Still closed/frozen through Deterministic Challenge Artifact v1 | current live contract/service/gate/tests/report surfaces for citation pack, evidence report/export/package, context packet, context dossier, deterministic insight, deterministic challenge |
| Lower document-processing layer | Reopened additively in the live repo | `backend/app/services/nrc_aps_media_detection.py`, `backend/app/services/nrc_aps_document_processing.py`, `backend/app/services/nrc_aps_ocr.py`, `backend/app/services/nrc_aps_artifact_ingestion.py`, `backend/app/services/nrc_aps_content_index.py`, `backend/alembic/versions/0009_aps_document_processing_metadata.py` |
| Focused lower-layer verification | Green in this workspace with OCR-enabled proof | fresh isolated proof rerun on March 13, 2026: `46 passed` across lower-layer media-detection/document-processing/corpus/content-index/OCR-adapter tests plus `3 passed` API proof tests for real extracted born-digital and OCR-backed content search/evidence-bundle persistence |
| Fresh lower-layer gate proof | Green in isolated temp runtime and checked in for the OCR-enabled lane | `tests/reports/nrc_aps_document_processing_proof_report.json`, `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`, and `tests/reports/nrc_aps_content_index_validation_report.json` |
| Upper-layer schema stability | Preserved | no upper `v1` schema ids were widened during this lower-layer work |

### Current proof freshness and remaining gaps
| Surface | Current state | Proof |
| --- | --- | --- |
| Fresh aggregate NRC gate PASS after lower-layer expansion | Available and fresh | rerun on March 13, 2026 via `./project6.ps1 -Action gate-nrc-aps`: aggregate pytest slice `143 passed, 29 deselected`, post-validator dossier ambiguity negative slice `1 passed, 55 deselected`, and aggregate validate-only reports refreshed to PASS through Deterministic Challenge Artifact |
| Existing APS validation reports | Partially fresh | current in this pass: the three lower-layer document-processing reports plus `nrc_aps_evidence_bundle_validation_report.json`, `nrc_aps_evidence_citation_pack_validation_report.json`, `nrc_aps_evidence_report_validation_report.json`, `nrc_aps_evidence_report_export_validation_report.json`, `nrc_aps_evidence_report_export_package_validation_report.json`, `nrc_aps_context_packet_validation_report.json`, `nrc_aps_context_dossier_validation_report.json`, `nrc_aps_deterministic_insight_artifact_validation_report.json`, and `nrc_aps_deterministic_challenge_artifact_validation_report.json`; other report artifacts under `tests/reports/` remain available but were not all rerun |

## 3. What is frozen and what is reopened
### Still closed/frozen
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

### Reopened additively
- artifact ingestion
- content indexing
- document/media detection
- document extraction and OCR handling

Important correction:
- older handoff prose that treated artifact ingestion and content indexing as closed is now stale
- upper analytical schemas remain frozen while the lower document-processing layer evolves additively

## 4. Current lower-layer live authority
The portable package records the reopened scope, but the authoritative implementation remains in the live repo:
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_media_detection.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_ocr.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_content_index.py`
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
- `tests/test_api.py`
- `tools/run_nrc_aps_document_processing_proof.py`

## 5. Lower-layer implementation snapshot
- `aps_media_detection_v1` now combines header normalization with deterministic byte sniffing.
- `aps_document_extraction_v1` now performs BOM-aware text decoding and PyMuPDF-based PDF extraction.
- OCR is wired through the Tesseract CLI adapter in `nrc_aps_ocr.py`.
- The OCR adapter now auto-detects the standard Windows install path `C:\Program Files\Tesseract-OCR\tesseract.exe` (and the x86 equivalent) in addition to `PATH` and `TESSERACT_CMD`.
- `content_parse_timeout_seconds` is now enforced cooperatively inside the live lower-layer processing path.
- Lower-layer normalization is now `aps_text_normalization_v2`.
- Content units are now `aps.content_units.v2` under `aps_content_units_v2`.
- Chunking is now `aps_chunking_v2` with page/unit metadata.
- `download_only` reprocessing now persists a diagnostics artifact as part of content-index derivation.
- `diagnostics_ref` is authoritative at the run-target/linkage and content-artifact level rather than on the deduplicated content-document row.
- Corpus proof is now manifest-driven through `tests/support_nrc_aps_doc_corpus.py` and `tests/test_nrc_aps_document_corpus.py`.
- The representative real NRC fixture `tests/fixtures/nrc_aps_docs/v1/ML17123A319.pdf` is now part of the lower-bound corpus.
- Real born-digital downstream usefulness is now proven through content search and evidence-bundle persistence in `tests/test_api.py`.
- OCR-backed downstream usefulness is also proven in this workspace through the scanned fixture path in `tests/test_api.py`.

## 6. Package-scope limitations
- This handoff package is intentionally scoped rather than exhaustive of the whole repo, but it now mirrors the current lower-layer corpus files needed for the reopened document-processing proof slice.
- OCR-success proof remains environment-dependent because Tesseract is not bundled in the repo, but it is now proven in the current workspace.
- Current fresh OCR-enabled lower-layer proof in the repo/package is:
  - `tests/reports/nrc_aps_document_processing_proof_report.json`
  - `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
  - `tests/reports/nrc_aps_content_index_validation_report.json`
- Current fresh aggregate gate proof in the repo/package is:
  - `tests/reports/nrc_aps_evidence_bundle_validation_report.json`
  - `tests/reports/nrc_aps_evidence_citation_pack_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_package_validation_report.json`
  - `tests/reports/nrc_aps_context_packet_validation_report.json`
  - `tests/reports/nrc_aps_context_dossier_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_insight_artifact_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_challenge_artifact_validation_report.json`
- Other checked-in `tests/reports/*.json` files should be treated as historical snapshots unless explicitly regenerated in the current pass.

## 7. Validator semantics
- Existing `validate-*` actions remain validate-only.
- They validate existing persisted artifacts only.
- They fail closed on empty runtime.
- They do not seed or generate artifacts.
- `project6.ps1 -Action prove-nrc-aps-document-processing` is the fresh isolated lower-layer proof runner. It is not validate-only: it builds isolated runtime state, runs lower-layer pytest proof, then invokes the existing validate-only artifact-ingestion and content-index gates against that isolated runtime.

## 8. Next safe continuation
The next safe continuation is not blocked by lower-layer OCR proof anymore. It is:
1. preserve the restored lower-layer baseline and current OCR-enabled proof basis
2. continue above the frozen analytical ceiling with a single bounded slice
3. rerun `.\project6.ps1 -Action prove-nrc-aps-document-processing -RequireOcr` when OCR/corpus behavior changes or when validating a new environment
