# Validation Plan

Status: required checks for the planning pack and later implementation phases.

## Current Branch Validation

This branch now contains Phase P1, Phase P2, Phase P3, Phase P4, Phase P4.5, Phase P5, Phase P6, and bounded Phase P10A source/test/UI changes plus the planning pack. Required validation for this pass:

- `git diff --check`
- `git status --short --branch`
- Re-read created docs for internal consistency.
- Confirm no schema, migration, or model changed.
- Confirm UI asset changes are limited to bounded APS-derived `DatasetVersion` operator selection in the Layer 3 workbench.
- Confirm API route-definition changes are limited to material-preview accepting DB-backed explicit `dataset_version_ids` and read-only APS-derived dataset-version candidate listing.
- Run focused dataset-bridge, CSV parser, parser-registry, media/artifact/document-processing tests.
- Run the route-level CSV dataset bridge test proving connector finalization can invoke the bridge under `csv_dataset_bridge_enabled=true`.
- Run Layer 3 workbench/API tests proving APS-derived dataset material reaches Gate B, Gate C, and plan preview.
- Run Layer 3 API tests proving APS-derived dataset material reaches execution, result review, package preview, and package commit.

Browser tests are required for Phase P10A because UI assets changed.

## General Test Doctrine

All parser and validation work must be isolated, deterministic, and fail-closed.

Rules:

- Use isolated temporary runtime state for parser and integration tests.
- Do not rely on shared seeded state.
- Do not let validate-only commands seed, download, parse, generate, or persist artifacts.
- Use content-addressed refs and deterministic diagnostics where possible.
- Tests must assert refused/unsupported behavior, not only successful parsing.
- Do not upgrade fallback behavior into support claims.

Architecture regression checks:

- Adding a parser family does not modify Candidate B PDF behavior unless it is a PDF parser.
- Adding a parser family does not require workbench UI changes before backend source authority exists.
- Adding typed data support does not route typed rows through `aps_content_document` chunks.
- Parser registry tests prove parser-family isolation.
- Dataset bridge tests prove idempotent materialization for repeated content/parser contracts.
- Provenance tests prove source run, target, raw blob, parser family, parser version, and contract identity survive through the downstream boundary being tested.
- Negative fixtures prove unsupported inputs fail closed without creating content chunks, dataset rows, packages, or handoff records.

## Format Matrix

| Format/source | Current behavior to preserve or fix | Required future behavior |
| --- | --- | --- |
| PDF baseline | Supported document processing | Preserve |
| PDF Candidate B | PDF-only OpenDataLoader path, fail-closed on non-PDF | Preserve PDF-only boundary |
| Plain text | Qualitative text chunks | Preserve; optionally add qualitative source diagnostics |
| Image JPEG/PNG/TIFF | OCR into text chunks | Preserve; add source-family diagnostics |
| Generic ZIP | Archive bundle for selected members | Preserve only with visible member outcome accounting |
| ZIP with CSV | CSV member is parsed into table diagnostics and is not flattened into text | Future dataset bridge should materialize table units only when explicitly admitted |
| XLSX | Risk of ZIP-signature ambiguity | Detect as spreadsheet or refuse until parser is admitted |
| CSV standalone | Not first-class | Detect as table candidate; refuse or parse explicitly |
| JSON | Explicitly refused | Keep refused until `json_recordset` parser exists |
| XML | Explicitly refused | Keep refused until selected structured parser exists |
| HTML | Explicitly refused | Keep refused until selected filing/document parser exists |
| SEC/EDGAR text filing | May flow as plain text | Preserve as text only when no structured parser is admitted; do not claim filing support |
| SEC/EDGAR HTML/XML/Inline XBRL | Refused or unsupported | Admit only under specific filing parser contracts |
| Malformed/empty files | Must fail closed | Preserve and expand diagnostics |

## Phase P1 Validation

Unit tests:

- Supported PDF still resolves to PDF.
- Supported text still resolves to text.
- Supported images still resolve to image types.
- Generic ZIP still resolves to archive only when it is truly generic archive content.
- XLSX fixture is not classified as generic ZIP.
- CSV fixture is not silently claimed as qualitative document support when typed parser is disabled.
- JSON/XML/HTML fixtures are refused with stable tokens.
- Declared/sniffed conflicts fail closed or resolve according to explicit precedence.
- Empty bytes fail closed.

Integration tests:

- Connector target artifact handling records declared/sniffed/effective media diagnostics.
- Unsupported/refused artifacts produce artifact failure payloads with stable error classes.
- Existing PDF/text/image tests remain green.

Regression risks:

- Accidental breakage of current APS PDF ingestion.
- Accidental widening of JSON/XML/HTML behavior.
- Candidate B accepting non-PDF input.
- XLSX being accepted as archive.

## Phase P2 Validation

Unit tests:

- Registry has stable entries for baseline PDF, Candidate B PDF, plain text, image OCR, archive bundle, and unsupported refusal.
- Unsupported parser lookup fails closed.
- Registry output shape is stable for current document processors.
- Existing document processor outputs remain byte/field compatible where tests expect them.
- Candidate B non-PDF lookup is not admitted.
- CSV remains unadmitted; P2 must not add CSV parser behavior.

Integration tests:

- Artifact processing payloads can preserve registry metadata without changing content index behavior for existing fixture types.
- Candidate B still requires artifact storage dir and PDF input.

Validation performed in this branch:

- `python -m pytest .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_expansion.py -k "not candidate_b"`

Result:

- `55 passed, 9 deselected`.

Caveat:

- The command exited successfully, but pytest emitted a Windows temp cleanup `PermissionError` after the green result for `pytest-current`. Treat that as a local temp-directory cleanup caveat, not as a failed validation result.

## Phase P3 CSV Parser Validation

Status: implemented for typed parser diagnostics only.

Positive fixtures:

- Simple comma-delimited table with headers.
- Numeric columns and one date/time column.
- Qualitative categorical column plus numeric measures.
- Missing values and blank cells.
- Quoted delimiters and escaped quotes.

Negative fixtures:

- Empty file.
- Header-only file.
- Ragged rows beyond policy.
- Invalid encoding.
- Oversized row count.
- Oversized column count.
- Formula-injection style leading characters where export risk matters.
- CSV-like prose that should remain qualitative text or unsupported.

Assertions:

- Parser reports delimiter, encoding, row count, column count, header decision, column types, numeric columns, and time-column candidates.
- Parser emits `table_units`.
- Parser does not create dataset rows unless dataset bridge is explicitly active.
- Refusals include stable failure tokens.
- ZIP CSV members are not flattened into normalized document text.

Validation performed in this branch:

- `python -m pytest .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_expansion.py -k "not candidate_b"`

Result:

- `76 passed, 9 deselected`.

Caveat:

- The command exited successfully, but pytest emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Phase P4 Dataset Bridge Validation

Status: implemented for explicit/callable CSV table materialization only.

Unit tests:

- Table unit materializes one `Dataset`, one `DatasetVersion`, variable definitions, profiles, and rows.
- Time-column candidate becomes `Dataset.time_column` only when confidence and policy allow it.
- Numeric columns set `is_numeric`.
- Source provenance includes run id, target id, raw blob hash, parser family, parser version, and contract id.
- Re-running the same content/parser contract is idempotent.
- Missing required provenance fails closed.
- No schema or migration is required for the current bridge slice.

Integration tests:

- Fixture CSV to parser to dataset bridge.
- Dataset version loads through existing analysis utilities.
- Dataset source provenance can answer original APS/corpus identity.

Validation performed in this branch:

- `python -m pytest .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_expansion.py -k "not candidate_b"`

Result:

- `79 passed, 9 deselected`.

Caveat:

- The command exited successfully, but pytest emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Phase P4.5 Connector Bridge Orchestration Validation

Status: implemented for opt-in CSV bridge invocation from APS connector finalization.

Unit/focused tests:

- Connector helper materializes a processed CSV target artifact into dataset authority.
- Connector helper skips non-CSV parser artifacts without materializing datasets.
- Connector helper writes a run report and target dataset refs.
- Reused bridge service keeps idempotent dataset/version identity.

Route-level integration test:

- APS run submission with `artifact_pipeline_mode="hydrate_process"` and `csv_dataset_bridge_enabled=true` downloads CSV fixture content, emits CSV parser diagnostics, invokes the dataset bridge, exposes `aps_csv_dataset_bridge` in `report_refs`, and links the connector target to `dataset_id` and `dataset_version_id`.

Validation performed in this branch:

- `python -m pytest .\tests\test_nrc_aps_dataset_bridge.py`
- `python -m pytest .\tests\test_api.py -k "csv_dataset_bridge"`
- `python -m pytest .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_api.py .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_expansion.py -k "not candidate_b"`

Result:

- Bridge focused file after P4.5: `5 passed`.
- Route-level bridge integration: `1 passed, 62 deselected`.
- Focused regression after P4.5: `143 passed, 10 deselected`.

Caveat:

- The bridge focused command exited successfully but emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Phase P5 Layer 3 Typed Admission Validation

Status: implemented for explicit APS-derived `DatasetVersion` admission through the existing `dataset_version` source shape.

Unit/focused tests:

- Layer 3 material preview accepts explicit `dataset_version_ids` and projects dataset/version/variable metadata.
- APS `DatasetSourceProvenance` is surfaced as `aps_source_provenance` without creating a new source shape.
- Gate B persists real source identity and source provenance into `L3MaterialSnapshot`.
- Gate C commit keeps `planning_shape_family="tabular_numeric"` and quantitative analysis units.
- Plan preview admits the resulting dataset-shaped material and preserves `dataset_version_id` in planned passes.

API tests:

- `/api/v1/layer3/material-preview` accepts explicit `dataset_version_ids` using the existing route.
- An APS-derived dataset fixture reaches `/gate-b/decision`, `/gate-c/preview`, and `/plan/preview`.
- Existing first-slice synthetic preview flow remains green.

Validation performed in this branch:

- `python -m pytest .\backend\tests\test_layer3_workbench.py`
- `python -m pytest .\backend\tests\test_layer3_api.py -k "aps_derived_dataset_version or first_slice_preview_openapi_contracts or full_first_slice_flow"`

Result:

- Layer 3 workbench focused file: `10 passed`.
- Layer 3 API focused selection: `3 passed, 71 deselected`.

Caveat:

- Both commands exited successfully but emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Phase P10A UI/State Validation

Status: implemented for bounded Layer 3 APS-derived CSV `DatasetVersion` selection surfacing.

- Source preview shows existing `aps_content_document` unchanged.
- Source preview shows pre-existing `dataset_version` unchanged.
- UI selection shows APS-derived datasets with parser/source provenance without treating UI state as source authority.
- Material preview maps APS-derived dataset to `tabular_numeric`, not `document_chunks`.
- Gate B records source identity and provenance.
- Gate C typing uses quantitative dataset rules.
- Unsupported source shape fails closed.

Additional P10A validation:

- Read-only Layer 3 candidate endpoint returns APS-derived dataset versions from existing `DatasetSourceProvenance` rows.
- Workbench static UI includes APS-derived `DatasetVersion` candidate display, explicit ID input, and material-preview `dataset_version_ids` wiring.
- Headless and headed Chromium both pass the Layer 3 workbench browser spec after the UI asset change.

Commands:

- `python -m pytest .\backend\tests\test_layer3_page.py .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py -k "aps_dataset_version_candidates or dataset_version_candidates or first_slice_preview_openapi_contracts or layer3_page_route_serves_workbench_shell or layer3_static_assets_are_mounted"`
- `python -m pytest .\backend\tests\test_layer3_page.py .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py`
- `npm run test:e2e:chromium -- e2e/layer3-workbench.spec.js`
- `npm run test:e2e:headed -- e2e/layer3-workbench.spec.js`

Result:

- Focused page/workbench/API selection: `5 passed, 84 deselected`.
- Full Layer 3 page/workbench/API files: `89 passed`.
- Headless Chromium Layer 3 workbench spec: `8 passed`.
- Headed Chromium Layer 3 workbench spec: `8 passed`.

Caveat:

- Pytest exited successfully but emitted the known Windows temp cleanup `PermissionError` after green results for `pytest-current`.
- The first Playwright attempt used a Windows backslash file argument and found no tests; cleanup verification showed no live listener on port `8031`, and the rerun with a forward-slash path passed.

Future state consistency tests:

- Session summary, material snapshot, typing record, plan preview, execution selection, result status, package preview, and package construction all agree on source identity.
- A document-chunk source cannot be accidentally executed through dataset-only analysis methods.
- A typed dataset source cannot be accidentally dispatched through APS document-chunk handoff without explicit mixed-source governance.

## Phase P6 Execution And Package Validation

Status: implemented for selected-pass execution/result/package proof of an explicitly admitted APS-derived `DatasetVersion`.

Tests:

- Descriptive summary runs on APS-derived general table fixture.
- Time-series methods are recommended only when time-column and numeric-variable requirements are met.
- Cross-correlation requires at least two numeric variables.
- Decomposition and structural-break require time-indexed numeric data.
- Result/status includes dataset and source provenance.
- Package preview and package construction preserve source provenance.

Negative tests:

- Dataset without time column does not run time-series-only methods.
- Dataset with only qualitative columns falls back or fails according to method policy.
- Source provenance mismatch blocks package/handoff paths.

Validation performed in this branch:

- `python -m pytest .\backend\tests\test_layer3_api.py -k "aps_derived_dataset_version_reaches_package_commit"`
- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py`
- `python -m pytest .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_api.py .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_expansion.py .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py -k "not candidate_b"`

Result:

- `1 passed, 73 deselected`.
- Full Layer 3 workbench/API files: `84 passed`.
- Combined APS bridge/parser/media/document plus Layer 3 regression: `227 passed, 10 deselected`.

Caveat:

- The command exited successfully but emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Phase P7 Spreadsheet Validation

Positive fixtures:

- Single-sheet workbook with one clear table.
- Multi-sheet workbook with one selected table.
- Workbook with date/time and numeric columns.

Negative fixtures:

- Encrypted workbook.
- Macro-enabled workbook if macros are not admitted.
- Empty workbook.
- Workbook with only formatting/no data.
- Workbook with multiple ambiguous tables and no selection policy.
- Corrupt ZIP/workbook.

Assertions:

- XLSX is not processed as generic ZIP.
- Sheet/table provenance is retained.
- Formula/value policy is explicit.
- Dataset bridge sees sheet/table origin.

## Phase P8 JSON Recordset Validation

Positive fixtures:

- Array of flat objects.
- Object containing a configured records array.
- Numeric and date/time fields.

Negative fixtures:

- Arbitrary nested document JSON.
- Heterogeneous arrays without flattening policy.
- Empty object.
- Empty array.
- Invalid JSON.
- Oversized JSON.

Assertions:

- Record path, field paths, types, null/missing behavior, and row counts are recorded.
- Non-recordset JSON remains refused.

## Phase P9 SEC/EDGAR Validation

Positive fixtures:

- Narrow first admitted plain-text filing.
- Filing with deterministic metadata fields.
- Filing with extractable table under selected parser policy.

Negative fixtures:

- Unsupported form type.
- Unsupported encoding.
- Malformed filing.
- Filing with ambiguous tables.
- Inline XBRL/XML/HTML before parser admission.

Assertions:

- Narrative sections map to document units.
- Extracted tables map to table units.
- Mixed source envelope links both branches.
- Downstream package can prove source identity without conflating text sections and tables.

## Browser Validation

Browser tests are required only when UI assets or rendered workbench behavior changes.

When required:

- Run headless browser coverage.
- Run headed Chrome coverage.
- Compare headed/headless findings rather than treating one as sufficient if they disagree.
- Verify source cards, material preview, Gate B/Gate C state, package/source summaries, and unsupported/refusal messaging.

## Completion Definition

The overall heterogeneous ingestion lane is complete only when all of the following are true:

- Detection refuses or classifies every targeted file family deterministically.
- Each admitted parser has positive and negative fixtures.
- Typed parsers preserve source-family semantics in diagnostics.
- Dataset bridge or governed source-shape path exists for typed data.
- Layer 3 source preview, material preview, typing, plan, execution, result, package, and handoff/export paths are consistent with source identity.
- Existing PDF/Candidate B/document-chunk behavior is unchanged except for additive diagnostics.
- Docs and tests do not claim broader support than the implementation proves.
