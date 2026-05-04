# Target Contract

Status: target-state contract with current implementation notes. Phase P8 now admits a bounded `json_recordset` parser; broader structured JSON remains target-state only until a later implementation PR changes source and tests.

## Requirement

The pipeline must preserve the source artifact's actual content family from acquisition through downstream Layer 3 admission. A file that begins as a table, workbook, JSON recordset, SEC filing, time-series dataset, or qualitative text source must not be silently flattened into generic text when that flattening destroys semantics needed by Layer 3.

The target contract must answer five questions for every artifact:

- What was acquired?
- What type was declared, sniffed, and finally admitted?
- Which parser family handled it?
- Which representations were produced?
- Which downstream Layer 3 source path is authoritative?

## Content Source Envelope

Every processed artifact should produce a source envelope before downstream indexing or dataset materialization.

Required fields:

- `source_system`: for this lane, initially `nrc_aps`.
- `source_run_id`: connector or corpus run authority.
- `source_target_id`: target/document/file identity within the run.
- `original_filename`: if available from APS metadata, URL, headers, archive member path, or corpus manifest.
- `declared_content_type`: response/header/media declaration.
- `sniffed_content_type`: deterministic sniff result.
- `effective_content_type`: admitted runtime type after refusal and conflict resolution.
- `content_family`: one of `document`, `qualitative_text`, `image_ocr`, `archive`, `table`, `time_series`, `spreadsheet`, `recordset`, `filing`, `mixed`, or `unsupported`.
- `parser_family`: admitted parser name.
- `parser_version`: deterministic parser contract version.
- `contract_id`: representation contract, not just text normalization contract.
- `raw_blob_ref`: content-addressed raw blob reference.
- `diagnostics_ref`: content-addressed diagnostics reference.
- `failure_status`: absent for success; otherwise fail-closed reason.

Representation slots:

- `document_units`: page/section/block units with text and optional visual refs.
- `text_units`: normalized qualitative text blocks.
- `image_units`: OCR text plus image/page/region provenance.
- `table_units`: table schemas, rows, column types, labels, and source ranges.
- `time_series_units`: observation rows with time index, frequency hints, numeric variables, and missingness profile.
- `workbook_units`: sheets, named ranges, tables, formulas/values policy, and sheet-level provenance.
- `filing_units`: filing metadata, sections, exhibits, tables, accession/company/form metadata when available.
- `archive_units`: manifest of members, member classifications, member outcomes, and recursive parser refs.
- `dataset_bridge`: durable target dataset/dataset-version/variable/row ids when materialized.

## Parser Families

Initial parser registry:

| Parser family | Input examples | Output representation | Downstream default |
| --- | --- | --- | --- |
| `pdf_document` | `application/pdf` | `document_units`, `text_units`, visual refs | `aps_content_document` |
| `pdf_candidate_b_opendataloader` | PDF only, opt-in | `document_units`, OpenDataLoader diagnostics | `aps_content_document` |
| `plain_text` | `.txt`, textual responses, selected SEC text filings | `text_units` | `aps_content_document` |
| `ocr_image` | JPEG, PNG, TIFF | `image_units`, `text_units` | `aps_content_document` |
| `archive_bundle` | ZIP archives | `archive_units`, child parser refs | child-dependent |
| `csv_table` | `.csv`, `text/csv`, delimited table text | `table_units`, optional `time_series_units` | `dataset_version` if admitted |
| `xlsx_workbook` | `.xlsx` workbooks admitted by the bounded parser | `workbook_units`, `table_units`, optional `time_series_units` | `dataset_version` if explicitly materialized |
| `json_recordset` | table-like JSON arrays/objects with flat records or configured record paths | `table_units`, optional `time_series_units` | `dataset_version` if admitted |
| `edgar_filing` | SEC/EDGAR text, SGML, HTML, XML, Inline XBRL where admitted | `filing_units`, `text_units`, `table_units` | mixed |
| `unsupported_refusal` | unknown, unsafe, ambiguous, or unadmitted files | diagnostics only | none |

## Non-Negotiable Invariants

Fail closed:

- Empty runtime input must not seed or generate artifacts.
- Unsupported, ambiguous, or unsafe media must produce a precise failure record, not a downgraded success.
- Arbitrary structured JSON, XML, and HTML remain refused until a specific parser family is admitted with tests. The current JSON admission is limited to bounded `json_recordset` input and must fail closed for non-recordset JSON.
- XLSX must not be accepted as generic ZIP. It must be detected as spreadsheet and admitted only through the bounded `xlsx_workbook` parser, while `.xls`, `.xlsm`, encrypted, formula-bearing, empty, or ambiguous workbooks fail closed until explicitly admitted.
- CSV must not be described as tabular support if it is only processed as text.
- Archive extraction must record every member as processed, refused, skipped, or failed; skipped members must be intentional and visible.

Contract separation:

- `aps_content_document` remains the document-chunk evidence path.
- `dataset_version` remains the quantitative/tabular/time-series analysis path unless a new source shape is explicitly governed.
- Candidate B remains a PDF parser family and is not the general multi-type parser.
- Parser selection must be independent of UI labels and review display names.

Provenance:

- Every downstream row or chunk must carry source run, target, raw blob, parser family, parser version, and content contract identity.
- Dataset bridge materialization must retain original file/member/sheet/row provenance sufficient to answer "which corpus item produced this observation?"
- Mixed documents must not lose the connection between qualitative sections and extracted tables.

Validation:

- Validate-only paths must remain validate-only and must not seed, download, parse, or write runtime artifacts.
- Parser diagnostics must be deterministic enough for fixture comparison.
- Source typing must be explicit; implicit "looks numeric" heuristics cannot become authority without recorded confidence and operator-visible diagnostics.

## Architecture Quality Properties

The target contract is acceptable only if it supports extension without destabilizing existing lanes.

Modularity requirements:

- Media detection owns declared/sniffed/effective type resolution and refusal tokens.
- Parser registry owns parser-family admission, preconditions, parser versions, and output representation families.
- Parser implementations own only their source-family transformation and diagnostics.
- Content indexing owns document/text chunk persistence.
- Dataset bridge owns typed table/time-series materialization.
- Layer 3 workbench owns source preview, material preview, Gate B, Gate C, plan/execution/package state, and must consume typed source authority rather than infer it.
- UI surfaces own projection only and must not become parser or source-truth authority.

Scalability requirements:

- A new source family must be addable by introducing a parser-family entry, fixtures, output contract mapping, and downstream admission rule.
- A new parser must not require changing Candidate B PDF logic unless the parser is itself a PDF engine.
- A new typed source must not require duplicating analysis-method logic already attached to `dataset_version`.
- Mixed-source files must link representations instead of forcing every representation through one table or one chunk model.

Non-fragility requirements:

- Format-specific parser failures must not poison unrelated parser families.
- Parser outputs must be versioned so later parser improvements do not invalidate old packages without explicit migration or reprocessing.
- Source identity must be content-addressed where possible so reruns can be idempotent and comparable.
- Runtime/operator display labels must not be used as control-flow authority.
- Archive processing must isolate member failures and record member outcomes.

## Downstream Mapping

Qualitative/document path:

- `document_units` and `text_units` flow into `ApsContentDocument` and `ApsContentChunk`.
- Layer 3 material preview uses `source_shape="aps_content_document"`.
- Typing rule defaults to `planning_shape_family="document_chunks"`.
- APS handoff consumers use content/chunk/linkage rows.

Typed tabular/time-series path:

- `table_units` and `time_series_units` flow into `Dataset`, `DatasetVersion`, `VariableDefinition`, `VariableProfile`, and `DatasetRow`, or into a new explicitly governed source shape if chosen later.
- Layer 3 material preview uses `source_shape="dataset_version"` or a new source shape that maps into the same quantitative analysis constraints.
- Typing rule defaults to `planning_shape_family="tabular_numeric"` when the data passes numeric/time/index profiling.
- Analysis methods use existing time/numeric feature gates.

Mixed filing path:

- `filing_units` produce document sections for qualitative evidence.
- Extracted filing tables produce `table_units`.
- A single source envelope links both document chunks and dataset rows so package/handoff artifacts can prove common source identity.

## Required Diagnostics

Every parser must emit diagnostics with:

- parser family and version.
- source identity and raw blob hash.
- declared/sniffed/effective media fields.
- row, page, section, member, sheet, or table counts as applicable.
- detected encodings and delimiter decisions where applicable.
- column type profile and time-column candidates for tables.
- refusal reason for unsupported or unsafe artifacts.
- downstream materialization ids when created.

## Schema And Migration Boundary

The current live models already contain dataset and APS content rows, but this lane likely needs schema work once implementation reaches durable typed materialization.

No schema widening is allowed implicitly. A later implementation pass must decide whether to:

- reuse existing `DatasetSourceProvenance` and `DatasetExternalIdentity`;
- add a dedicated APS artifact-to-dataset bridge table;
- add representation-contract refs to existing APS content rows;
- add parser diagnostics refs to dataset/version rows;
- add a mixed-source linking table for filing sections plus extracted tables.

Until that decision is made and frozen, typed parser work should start with deterministic diagnostics and fixture-level proof before durable DB widening.

## Workbench Contract

Layer 3 workbench admission must not treat all APS artifacts as `aps_content_document`.

Required workbench behavior:

- Show admitted source class and source family separately.
- Show whether a source is document-chunk, tabular numeric, time-series, filing, mixed, or unsupported.
- Preserve current `aps_content_document` behavior for existing document evidence flows.
- Admit typed APS-derived datasets only after dataset bridge or new source-shape authority exists.
- Keep source preview, material preview, Gate B, Gate C, plan preview, execution, result, package, and handoff state aligned on the same source identity.

## Out Of Scope For First Parser Slice

The first implementation slice should not add broad UI redesign, public upload ingestion, connector dispatch, signed URLs, package mutation, or full mockup activation.

The first implementation slice should not attempt every format. It should harden classification and then admit one narrow typed parser with fixtures and a fail-closed unsupported matrix.
