# Phase P1 Closeout

Status: implementation closeout for media classification/refusal hardening in this branch. This file records the P1 boundary; `08-p2-closeout.md` records the later P2 parser-registry boundary.

## Implemented Boundary

Phase P1 now hardens classification for typed or structured artifacts without admitting parsers, dataset materialization, schema changes, Layer 3 source-shape changes, or UI behavior.

Implemented:

- `nrc_aps_media_detection` now accepts optional `source_filename` context.
- Detection now emits `source_filename`, `file_extension`, `extension_content_type`, and `content_family` diagnostics.
- Declared, sniffed, or extension JSON/XML/HTML evidence is refused.
- Declared, sniffed, or extension CSV/spreadsheet evidence returns `typed_content_type_not_admitted`.
- XLS/XLSX/XLSM are classified as unadmitted spreadsheet candidates by extension.
- OOXML spreadsheet ZIP containers are sniffed as spreadsheet media instead of generic ZIP when workbook markers are present.
- Artifact ingestion forwards APS target filenames into media detection.
- Unsupported-media failure evidence includes media reason, source filename, extension, extension content type, and content family.
- Document-processing diagnostics and extraction payloads include the new media diagnostics.
- ZIP archive processing records typed/refused members as member-level unadmitted/refused outcomes instead of flattening CSV/structured members into text.

Not implemented:

- CSV parser.
- Spreadsheet parser.
- JSON recordset parser.
- SEC/EDGAR filing parser.
- Dataset bridge.
- Schema/model/migration changes.
- Layer 3 source preview/material preview/typing expansion.
- UI or browser behavior changes.

## Files Changed

Runtime/source:

- `backend/app/services/nrc_aps_media_detection.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/connectors_nrc_adams.py`

Tests:

- `tests/test_nrc_aps_media_detection.py`
- `tests/test_nrc_aps_artifact_ingestion.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/test_nrc_aps_expansion.py`

Planning docs:

- `next_milestone_plans/multi-ingest/README.md`
- `next_milestone_plans/multi-ingest/01-live-audit.md`
- `next_milestone_plans/multi-ingest/03-implementation.md`
- `next_milestone_plans/multi-ingest/04-validation.md`
- `next_milestone_plans/multi-ingest/06-adequacy-audit.md`
- `next_milestone_plans/multi-ingest/07-p1-closeout.md`

## Validation

Passed:

- `python -m pytest tests/test_nrc_aps_media_detection.py tests/test_nrc_aps_artifact_ingestion.py tests/test_nrc_aps_document_processing.py tests/test_nrc_aps_expansion.py -k "not candidate_b"`

Result:

- `51 passed, 7 deselected`.

Known validation caveat:

- Running the same focused suite without the `not candidate_b` filter produced two failures in pre-existing Candidate B integration tests because the local `opendataloader-pdf` package version does not match `APS_ODL_PDF_EXPECTED_VERSION`.
- The failures occur in `test_extract_and_normalize_forwards_candidate_b_engine` and `TestCandidateBProcessingIntegration.test_candidate_b_processes_pdf_with_existing_contract_shape`.
- This is an environment/dependency mismatch on Candidate B integration coverage, not a regression in P1 media classification behavior.

Not run:

- Browser tests, because no UI assets changed.
- Full backend suite, because P1 touched a narrow media/document-processing surface and the focused suite already exposed the local Candidate B environment blocker.

## Scope Recheck

No-go boundaries preserved:

- Candidate B remains PDF-only.
- Existing PDF/text/image/generic-ZIP processing remains admitted.
- CSV/spreadsheet/JSON/XML/HTML are not parsed.
- Typed data is not materialized into datasets.
- Layer 3 still admits only the existing `dataset_version` and `aps_content_document` source classes.
- The planning pack remains outside the settled progress-manifest spine until a separate governance sync admits it.

## Historical Next Action

At P1 closeout time, the next implementation tranche was Phase P2: parser registry skeleton. That tranche is now implemented and recorded in `08-p2-closeout.md`.

P2 should make parser-family addition mechanical before any CSV parser or dataset bridge work starts. That preserves the non-fragility requirement: new source families should be added through registry entries, output contracts, and fixtures rather than ad hoc branches in document processing or workbench code.
