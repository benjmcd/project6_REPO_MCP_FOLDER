# Phase P7.5 Closeout: Generic Table Bridge Orchestration

Status: implemented on 2026-05-03 in the `codex/l3-table-bridge` worktree.

## Scope

Phase P7.5 resolves the immediate post-P7 bridge-contract decision. XLSX connector orchestration is now supported only through a new generic table bridge path, not by broadening the existing CSV-named gate.

This phase does not admit `.xls`, `.xlsm`, encrypted workbooks, formula-bearing workbooks, arbitrary named ranges, ambiguous multi-sheet workbooks without explicit selection, XLSX files nested inside archives, JSON recordsets, SEC/EDGAR filings, schema/model/migration changes, or new Layer 3 source semantics.

## Implemented Boundary

- `backend/app/services/nrc_aps_dataset_bridge.py` defines `aps_table_dataset_bridge_v1` for generic table-unit materialization while preserving `aps_csv_dataset_bridge_v1` for the CSV compatibility wrapper.
- `materialize_table_unit_dataset(...)` supports admitted `csv_table` and `xlsx_workbook` table-unit parser contracts under the generic bridge contract.
- `materialize_csv_table_dataset(...)` remains CSV-only and rejects XLSX parser output.
- `backend/app/services/connectors_nrc_adams.py` normalizes `table_dataset_bridge_enabled` with default `false`.
- Connector finalization invokes the generic table bridge only when the run is terminal-success-like, `table_dataset_bridge_enabled=true`, and the target artifact is processed table-unit output.
- Generic bridge run reports use `aps.table_dataset_bridge_run.v1` and write `aps_table_dataset_bridge_*` refs.
- Legacy CSV bridge run reports and target refs remain `aps.csv_dataset_bridge_run.v1` and `aps_csv_dataset_bridge_*`.
- `backend/app/services/connectors_sciencebase.py` exposes generic table bridge report refs through connector run detail responses.

## Validation

Focused commands run:

- `python -m pytest .\tests\test_nrc_aps_dataset_bridge.py -q`: `8 passed`.
- `python -m pytest .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_api.py -k "dataset_bridge" -q`: `10 passed`, `62 deselected`.
- `python -m pytest .\tests\test_nrc_aps_spreadsheet_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_api.py -k "not candidate_b" -q`: `131 passed`, `10 deselected`.
- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py -q`: `86 passed`.
- `npm run validate:structure`: `errors: 0`, `warnings: 221` existing local-path/documentation warnings.

Validated assertions:

- Legacy CSV materialization keeps `aps_csv_dataset_bridge_v1`.
- Generic XLSX materialization uses `aps_table_dataset_bridge_v1`.
- Generic connector XLSX materialization writes `aps_table_dataset_bridge_ref`, target `dataset_id`, target `dataset_version_id`, and XLSX parser provenance.
- Runtime APS run detail exposes `report_refs["aps_table_dataset_bridge"]`.
- Generic table bridge refs do not masquerade as legacy CSV bridge refs.

## Caveats

- The legacy CSV bridge path remains intentionally supported for existing consumers.
- Generic table bridge orchestration is opt-in and requires the existing hydrate/process artifact pipeline.
- Layer 3 still consumes the resulting records through the existing `dataset_version` source shape.
- Broader workbook semantics, JSON recordsets, SEC/EDGAR filings, and mixed qualitative-plus-table package semantics remain separate phases.

## Next

The next implementation tranche should be either JSON recordset parsing or SEC/EDGAR filing parsing, with the same fail-closed parser admission, explicit materialization, provenance, and downstream Layer 3 validation discipline.
