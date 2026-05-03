# Phase P7 Closeout: Bounded XLSX Parser

Status: implemented on 2026-05-03.

## Scope

Phase P7 admits a bounded `.xlsx` workbook parser after CSV parser diagnostics and dataset bridge materialization were already proven. The implementation is intentionally narrow: one simple or explicitly selected sheet table can be parsed into `table_units`, retain workbook/sheet/row provenance, and be materialized into existing `DatasetVersion` authority.

This phase does not admit `.xls`, `.xlsm`, encrypted workbooks, formula-bearing workbooks, arbitrary named ranges, multiple ambiguous non-empty sheets without selection, automatic connector bridge finalization for XLSX artifacts, schema/model/migration changes, or new Layer 3 source semantics.

## Implemented Boundary

- `backend/app/services/nrc_aps_media_detection.py` admits `.xlsx` as spreadsheet before generic ZIP handling while keeping `.xls` and `.xlsm` typed-unadmitted.
- `backend/app/services/nrc_aps_parser_registry.py` registers baseline `xlsx_workbook` with `table_units` output and `aps_xlsx_workbook_parser_v1`.
- `backend/app/services/nrc_aps_spreadsheet_parser.py` parses dependency-free OOXML `.xlsx` packages using stdlib ZIP/XML primitives.
- `backend/app/services/nrc_aps_document_processing.py` dispatches `.xlsx` to the new parser and emits `workbook_units`, `table_units`, `time_series_units`, and workbook-aware table diagnostics without producing document chunks.
- `backend/app/services/nrc_aps_dataset_bridge.py` adds `materialize_table_unit_dataset(...)` for explicit CSV/XLSX table-unit materialization while preserving the existing `materialize_csv_table_dataset(...)` compatibility entrypoint.

## Validation

Focused command run:

- `python -m pytest .\tests\test_nrc_aps_spreadsheet_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_dataset_bridge.py`: `73 passed`, `2 failed`.

Failure boundary:

- The two failures were pre-existing Candidate B PDF tests blocked by local `candidate_b_package_version_mismatch`, not XLSX behavior.
- The passing subset included the new XLSX parser, XLSX media detection, parser registry admission, document processing, artifact ingestion, and explicit dataset bridge materialization coverage.

Focused verification after excluding the known Candidate B local package mismatch:

- `python -m pytest .\tests\test_nrc_aps_spreadsheet_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_dataset_bridge.py -k "not candidate_b"`: `66 passed`, `9 deselected`.

## Caveats

- The dataset bridge still exposes the legacy `aps_csv_dataset_bridge_v1` contract id for backward compatibility. P7 adds a generic callable wrapper, but a future bridge-contract rename should be considered before automatic XLSX connector finalization.
- XLSX materialization is explicit. Connector finalization still auto-materializes only processed CSV table artifacts behind `csv_dataset_bridge_enabled=true`.
- Formula cells fail closed rather than being evaluated or preserved as formula diagnostics. This avoids hidden semantic drift from cached formula values.
- Date detection is limited to ISO-like cell values in this tranche. Excel serial-date style conversion remains deferred until style-aware date handling is specified and tested.

## Next

The immediate next decision is whether to generalize the connector bridge contract/name before enabling automatic XLSX bridge orchestration. If that is deferred, the next parser tranche should be JSON recordset or SEC/EDGAR with the same fail-closed parser/materialization discipline.
