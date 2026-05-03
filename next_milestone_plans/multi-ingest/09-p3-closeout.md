# Phase P3 Closeout

Status: implementation closeout for CSV/delimited table typed diagnostics in this branch.

## Implemented Boundary

Phase P3 admits bounded CSV/delimited table parsing for diagnostics and parser-output contracts. It does not materialize datasets, change schema, alter Layer 3 source admission, or change UI behavior.

Implemented:

- `nrc_aps_csv_parser` defines `aps_csv_table_units_v1`.
- Media detection admits declared CSV and `.csv` filename artifacts when the body has a compatible text signature and no higher-priority refused or non-text signature.
- Parser registry admits `text/csv` and `application/csv` under the baseline engine as `csv_table`.
- Document processing emits `table_units`, optional `time_series_units`, and `table_diagnostics` for CSV.
- CSV output intentionally emits no `ordered_units` and no normalized document text.
- Connector diagnostics and extraction payloads preserve typed table diagnostics.
- ZIP `.csv` members are parsed for table diagnostics and are not flattened into archive normalized text.
- Focused tests prove positive CSV diagnostics and negative fail-closed behavior.

Not implemented:

- Dataset bridge.
- Dataset, dataset version, variable, or row materialization.
- Schema/model/migration changes.
- Layer 3 source preview/material preview/typing expansion.
- UI or browser behavior changes.
- Spreadsheet parser.
- JSON recordset parser.
- SEC/EDGAR filing parser.

## Files Changed

Runtime/source:

- `backend/app/services/nrc_aps_csv_parser.py`
- `backend/app/services/nrc_aps_media_detection.py`
- `backend/app/services/nrc_aps_parser_registry.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_content_index.py`

Tests:

- `tests/test_nrc_aps_csv_parser.py`
- `tests/test_nrc_aps_media_detection.py`
- `tests/test_nrc_aps_parser_registry.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/test_nrc_aps_artifact_ingestion.py`
- `tests/test_nrc_aps_expansion.py`

Planning docs:

- `next_milestone_plans/multi-ingest/README.md`
- `next_milestone_plans/multi-ingest/01-live-audit.md`
- `next_milestone_plans/multi-ingest/03-implementation.md`
- `next_milestone_plans/multi-ingest/04-validation.md`
- `next_milestone_plans/multi-ingest/05-decisions.md`
- `next_milestone_plans/multi-ingest/06-adequacy-audit.md`
- `next_milestone_plans/multi-ingest/08-p2-closeout.md`
- `next_milestone_plans/multi-ingest/09-p3-closeout.md`

## Validation

Passed:

- `python -m pytest .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_expansion.py -k "not candidate_b"`

Result:

- `76 passed, 9 deselected`.

Known validation caveat:

- Pytest emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`. The command exit code was still successful.
- Candidate B integration tests remain excluded from this focused command because the local `opendataloader-pdf` package version mismatch was already identified during P1 validation.

Not run:

- Browser tests, because no UI assets changed.
- Full backend suite, because P3 touched a bounded CSV/media/parser/document-processing diagnostics surface and the focused suite covers the affected paths.

## Scope Recheck

No-go boundaries preserved:

- Candidate B remains PDF-only.
- Existing PDF/text/image/generic-ZIP document behavior remains admitted.
- CSV is not materialized into datasets.
- CSV is not admitted as a Layer 3 typed source.
- Spreadsheet/JSON/XML/HTML/SEC parser behavior remains deferred or refused according to current media policy.
- The planning pack remains outside the settled progress-manifest spine until a separate governance sync admits it.

## Historical Next Action

At P3 closeout time, the next implementation tranche was Phase P4: dataset bridge for admitted table/time-series units. That tranche is now implemented and recorded in `10-p4-closeout.md`.

P4 should decide whether existing dataset provenance models are sufficient or whether a dedicated APS artifact-to-dataset bridge table is required. It should then materialize CSV table units idempotently into dataset authority without changing UI or adding spreadsheet/JSON/SEC parsing in the same tranche.
