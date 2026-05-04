# Phase P9 Closeout: SEC/EDGAR Complete Submission Text Parser

Status: implemented in the `codex/l3-sec-edgar-p9` worktree.

## Scope

Phase P9 admits a bounded SEC/EDGAR complete submission text parser after the generic table bridge path was already proven for CSV, XLSX, and JSON recordset table units.

This phase admits only complete submission text files identified by SEC submission signatures such as `<SEC-DOCUMENT>` or `<SEC-HEADER>`. It supports:

- Plain document text inside `<DOCUMENT>` / `<TEXT>` blocks.
- Deterministic filing metadata from the SEC header.
- Filing section ordered units from item-style headings.
- Simple delimited `<TABLE>` blocks that can be parsed as table units.
- Default admitted form types `10-K`, `10-Q`, and `8-K`, with config override support.

This phase does not admit HTML filing documents, XML, inline XBRL, unsupported form types by default, ambiguous financial-statement semantics, archive-member SEC/EDGAR orchestration, schema/model/migration changes, new Layer 3 source semantics, broad mixed-source package semantics, or UI asset changes.

## Implemented Boundary

- `backend/app/services/nrc_aps_media_detection.py` sniffs SEC/EDGAR complete submission text before generic plain-text fallback and emits `application/x-sec-edgar-submission` with `content_family="structured_filing"`.
- `backend/app/services/nrc_aps_parser_registry.py` admits `application/x-sec-edgar-submission` under the baseline `sec_edgar_filing` parser family with `parser_output_family="mixed_document_table_units"`.
- `backend/app/services/nrc_aps_sec_edgar_parser.py` parses filing metadata, document metadata, filing sections, simple delimited `<TABLE>` blocks, table units, time-series candidates, and fail-closed diagnostics.
- `backend/app/services/nrc_aps_document_processing.py` dispatches the SEC/EDGAR content type to `_process_sec_edgar(...)` and emits `typed_content_contract_id="aps_sec_edgar_filing_units_v1"`.
- `backend/app/services/nrc_aps_artifact_ingestion.py` forwards SEC/EDGAR parser bounds and admitted form config.
- `backend/app/services/nrc_aps_dataset_bridge.py` supports `sec_edgar_filing` under the generic `aps_table_dataset_bridge_v1` contract with `source_mode="artifact_sec_edgar_filing_parser"`.
- `backend/app/services/connectors_nrc_adams.py` normalizes SEC/EDGAR parser config and includes `sec_edgar_filing` in generic table bridge report support.

## Fail-Closed Rules

- Missing SEC submission signature fails closed.
- Missing form type fails closed.
- Unsupported form types fail closed unless explicitly admitted by config.
- HTML document text fails closed.
- XML and inline-XBRL document text fail closed.
- Missing document blocks or missing document text fail closed.
- Empty or malformed table blocks fail closed with SEC-specific table parse diagnostics.
- Ordinary `text/plain` documents without SEC signatures remain the existing plain-text path.

## Validation

Focused commands run:

- `python -m compileall .\backend\app\services\nrc_aps_sec_edgar_parser.py .\backend\app\services\nrc_aps_media_detection.py .\backend\app\services\nrc_aps_parser_registry.py .\backend\app\services\nrc_aps_document_processing.py .\backend\app\services\nrc_aps_artifact_ingestion.py .\backend\app\services\nrc_aps_dataset_bridge.py .\backend\app\services\connectors_nrc_adams.py`: passed.
- `python -m pytest .\tests\test_nrc_aps_sec_edgar_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_api.py -k "sec_edgar or parser_registry or media_detection or dataset_bridge" -q`: `43 passed`, `112 deselected`.
- `python -m pytest .\tests\test_nrc_aps_sec_edgar_parser.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_api.py -k "sec_edgar" -q`: `11 passed`, `126 deselected`.
- `python -m pytest .\tests\test_nrc_aps_sec_edgar_parser.py .\tests\test_nrc_aps_json_parser.py .\tests\test_nrc_aps_spreadsheet_parser.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_expansion.py .\tests\test_api.py -k "not candidate_b" -q`: `181 passed`, `10 deselected`.
- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py -q`: `86 passed`.
- `npm run validate:structure`: `errors: 0`, `warnings: 221` existing local-path/documentation warnings.
- `git diff --check`: passed with line-ending conversion warnings only.

Validated assertions:

- SEC/EDGAR complete submission text is sniffed before generic plain text.
- Parser registry admission is explicit and separate from plain text.
- Filing metadata and section units are emitted.
- Simple delimited `<TABLE>` blocks emit table units and time-series candidates.
- HTML SEC/EDGAR document text fails closed.
- Unsupported forms fail closed by default.
- Malformed table blocks fail closed with SEC-specific diagnostics.
- Generic table bridge materializes SEC/EDGAR table units to `DatasetVersion` authority.
- Runtime APS run detail exposes the generic table bridge report ref for SEC/EDGAR table materialization.
- Existing CSV/XLSX/JSON generic table bridge report families remain supported.

Caveat:

- Pytest exited successfully, but emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Residual Work

- HTML filing parsing remains unimplemented.
- XML and inline XBRL parsing remain unimplemented.
- Rich financial-statement semantics remain unimplemented.
- Unsupported form families require explicit future admission.
- SEC/EDGAR files inside archives remain unimplemented beyond visible archive-member accounting.
- Layer 3 still consumes materialized SEC/EDGAR table records through the existing `dataset_version` source shape when explicitly selected.
- Mixed qualitative-plus-table package semantics remain separate from parser admission.
- Broader typed/refused UI surfacing remains separate because this phase changed no UI assets.

## Next

The next implementation tranche should be a bounded typed/refused UI surfacing pass for server-backed source families, unless a separate SEC/EDGAR HTML/XML/inline-XBRL contract is intentionally prioritized first. Do not combine UI expansion, HTML/XML parser admission, mixed-source package semantics, schema changes, and legacy bridge deprecation in one PR.
