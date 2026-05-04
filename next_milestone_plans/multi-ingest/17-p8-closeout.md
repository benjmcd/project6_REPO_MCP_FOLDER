# Phase P8 Closeout: JSON Recordset Parser

Status: implemented in the `codex/l3-json-recordset` worktree.

## Scope

Phase P8 admits a bounded JSON recordset parser after the generic table bridge path was already proven for CSV/XLSX table units.

This phase admits only standalone JSON artifacts that are table-like:

- Root JSON array of flat objects.
- JSON object root with an explicitly configured record path to an array of flat objects.

This phase does not admit arbitrary nested JSON documents, nested flattening, heterogeneous record schemas, archive-member JSON orchestration, SEC/EDGAR filing parsing, XML/HTML parsing, schema/model/migration changes, new Layer 3 source semantics, or new UI assets.

## Implemented Boundary

- `backend/app/services/nrc_aps_media_detection.py` admits `application/json` as the `recordset` content family.
- `backend/app/services/nrc_aps_parser_registry.py` admits `application/json` under the baseline `json_recordset` parser family with `parser_output_family="table_units"`.
- `backend/app/services/nrc_aps_json_parser.py` parses bounded JSON recordsets into `table_units`, optional `time_series_units`, field-path diagnostics, and record-path provenance.
- `backend/app/services/nrc_aps_document_processing.py` dispatches standalone `application/json` to `_process_json(...)` and emits `typed_content_contract_id="aps_json_recordset_units_v1"`.
- `backend/app/services/nrc_aps_artifact_ingestion.py` forwards JSON parser bounds and configured record path from run config into document processing.
- `backend/app/services/nrc_aps_dataset_bridge.py` supports `json_recordset` under the generic `aps_table_dataset_bridge_v1` contract with `source_mode="artifact_json_recordset_parser"`.
- `backend/app/services/connectors_nrc_adams.py` normalizes JSON parser config and includes `json_recordset` in generic table bridge report support.

## Fail-Closed Rules

- JSON object roots without a configured record path fail closed.
- Nested object/list values fail closed until a flattening policy is specified.
- Heterogeneous keys fail closed; same key set with different object key order is accepted and normalized to first-record column order.
- Empty arrays, empty records, invalid JSON, unsupported record paths, oversized JSON, row-limit violations, and column-limit violations fail closed.
- XML/HTML remain refused, and JSON does not become SEC/EDGAR or structured-document support.

## Validation

Focused commands run:

- `python -m pytest .\tests\test_nrc_aps_json_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_nrc_aps_expansion.py .\tests\test_api.py -k "json or dataset_bridge or media_detection_expansion" -q`: `28 passed`, `126 deselected`.
- `python -m pytest .\tests\test_nrc_aps_json_parser.py .\tests\test_nrc_aps_spreadsheet_parser.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_expansion.py .\tests\test_api.py -k "not candidate_b" -q`: `169 passed`, `10 deselected`.
- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py -q`: `86 passed`.
- `npm run validate:structure`: `errors: 0`, `warnings: 221` existing local-path/documentation warnings.
- `git diff --check`: passed with line-ending conversion warnings only.

Validated assertions:

- Root-array JSON emits table units, numeric columns, time-column candidates, field paths, and row provenance.
- Object-root JSON works only with a configured record path.
- Non-recordset JSON fails closed before materialization.
- JSON artifact ingestion preserves parser diagnostics.
- Generic table bridge materializes JSON recordsets to `DatasetVersion` authority.
- Connector finalization can materialize JSON recordset artifacts only when `table_dataset_bridge_enabled=true`.
- Route-level APS run detail exposes the generic table bridge report ref for JSON recordset materialization.
- Existing CSV/XLSX table bridge behavior remains covered in the focused and broader regression selections.
- Existing Layer 3 `dataset_version` behavior remains green; no UI/browser validation was required because P8 changed no UI assets.

Caveat:

- Pytest exited successfully, but emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Residual Work

- SEC/EDGAR parser admission remains unimplemented.
- Arbitrary structured JSON remains unimplemented.
- Nested JSON flattening remains unimplemented until field-path/type/null semantics are specified.
- JSON inside archives remains unimplemented beyond visible archive-member accounting.
- Layer 3 still consumes materialized JSON records through the existing `dataset_version` source shape when explicitly selected.
- Broader typed/refused UI surfacing remains separate from parser admission.

## Next

The next implementation tranche should be either a narrow SEC/EDGAR parser slice or a bounded typed/refused UI surfacing pass. Do not combine SEC/EDGAR, arbitrary JSON flattening, schema changes, and UI expansion in one PR.
