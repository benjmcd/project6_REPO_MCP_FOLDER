# Phase P4.5 Closeout

Status: implementation closeout for opt-in CSV dataset bridge orchestration in this branch.

## Implemented Boundary

Phase P4.5 connects the existing APS connector finalization path to the Phase P4 dataset bridge. It is default-off and applies only to processed CSV table artifacts.

Implemented:

- `csv_dataset_bridge_enabled` is normalized into APS run config with default `false`.
- Connector finalization invokes the bridge only when the run is terminal-success-like and `csv_dataset_bridge_enabled=true`.
- Bridge invocation requires target artifact `outcome_status="processed"`, `parser_family="csv_table"`, and `typed_content_contract_id="aps_csv_table_units_v1"`.
- Successful materialization writes `dataset_id`, `dataset_version_id`, bridge contract id, source artifact key, and bridge report ref onto the connector target.
- Connector-orchestrated materialization sets `DatasetSourceProvenance.connector_run_id` to the live APS run id.
- A run-level `aps.csv_dataset_bridge_run.v1` report is written and exposed as `report_refs["aps_csv_dataset_bridge"]`.
- Materialization failures append `aps_csv_dataset_bridge_failed` and move the run to `completed_with_errors` unless the run is already failed or cancelled.
- Existing document content indexing, PDF/Candidate B behavior, and APS document evidence paths remain separate from typed dataset materialization.

Not implemented:

- Layer 3 source preview, material preview, Gate B, Gate C, execution, result, package, or handoff admission for APS-derived datasets.
- Schema/model/migration changes.
- UI or browser-visible behavior changes.
- Automatic bridge invocation for non-CSV parser families.
- Spreadsheet, JSON recordset, SEC/EDGAR, XML, or HTML parser support.

## Files Changed

Runtime/source:

- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/connectors_sciencebase.py`

Tests:

- `tests/test_nrc_aps_dataset_bridge.py`
- `tests/test_api.py`

Planning docs:

- `next_milestone_plans/multi-ingest/README.md`
- `next_milestone_plans/multi-ingest/01-live-audit.md`
- `next_milestone_plans/multi-ingest/03-implementation.md`
- `next_milestone_plans/multi-ingest/04-validation.md`
- `next_milestone_plans/multi-ingest/05-decisions.md`
- `next_milestone_plans/multi-ingest/06-adequacy-audit.md`
- `next_milestone_plans/multi-ingest/10-p4-closeout.md`
- `next_milestone_plans/multi-ingest/11-p4-5-closeout.md`

## Validation

Passed:

- `python -m pytest .\tests\test_nrc_aps_dataset_bridge.py`
- `python -m pytest .\tests\test_api.py -k "csv_dataset_bridge"`
- `python -m pytest .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_api.py .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_expansion.py -k "not candidate_b"`

Result:

- Bridge focused file: `5 passed`.
- Route-level runtime orchestration: `1 passed, 62 deselected`.
- Focused regression after P4.5: `143 passed, 10 deselected`.

Known validation caveat:

- The bridge focused command exited successfully, but pytest emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

Not run:

- Browser tests, because no UI assets changed.
- Full backend suite beyond the focused regression matrix.
- Candidate B integration tests, because the local `opendataloader-pdf` package version mismatch remains outside this CSV bridge slice.

## Scope Recheck

No-go boundaries preserved:

- Candidate B remains PDF-only.
- Existing PDF/text/image/generic-ZIP document behavior remains admitted.
- CSV bridge materialization is opt-in, not default connector behavior.
- Layer 3 still lacks APS-derived typed dataset source admission.
- Spreadsheet/JSON/XML/HTML/SEC parser behavior remains deferred or refused according to current media policy.
- No schema/model/migration/API route definition/UI changes were added.

## Next Action

The next implementation tranche should be Layer 3 typed dataset admission for APS-derived `DatasetVersion` records.

The first safe slice should prove source preview, material preview, Gate B, and Gate C for one APS-derived CSV dataset while preserving existing `aps_content_document` and plain `dataset_version` behavior.
