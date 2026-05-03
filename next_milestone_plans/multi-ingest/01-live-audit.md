# Live Audit

Status: evidence record for current-main capability. This file separates confirmed source facts from inferred implications and target-state requirements.

## Source Authority

Confirmed authority:

- `backend/app/services/nrc_aps_media_detection.py`
- `backend/app/services/nrc_aps_csv_parser.py`
- `backend/app/services/nrc_aps_parser_registry.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/nrc_aps_dataset_bridge.py`
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/services/layer3_typing_entry.py`
- `backend/app/services/layer3_aps_handoff.py`
- `backend/app/models/models.py`
- `backend/app/services/analysis.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/test_nrc_aps_csv_parser.py`
- `tests/test_nrc_aps_parser_registry.py`
- `tests/test_nrc_aps_content_index.py`
- `tests/test_nrc_aps_dataset_bridge.py`
- `backend/tests/test_layer3_api.py`
- `docs/nrc_adams/nrc_aps_status_handoff.md`
- `next_milestone_plans/layer3_progress_manifest.json`

Authority gap:

- `.codesight/wiki/index.md` is absent in this worktree.
- `.codesight/CODESIGHT.md` is absent in this worktree.
- Therefore this audit uses tracked source and tracked planning/status docs, not `.codesight`.

## Media Detection Facts

Confirmed:

- `APS_SUPPORTED_CONTENT_TYPES` includes `application/pdf`, `text/plain`, `application/zip`, `image/jpeg`, `image/png`, and `image/tiff` at `backend/app/services/nrc_aps_media_detection.py:11`.
- `APS_REFUSAL_CONTENT_TYPES` includes `application/json`, `application/xml`, and `text/html` at `backend/app/services/nrc_aps_media_detection.py:19`.
- CSV media types are now admitted for bounded parser diagnostics, while spreadsheet media types remain typed but not parser-admitted.
- Optional filename/extension diagnostics now include `source_filename`, `file_extension`, `extension_content_type`, and `content_family`.
- The sniffing path maps supported/refused signatures and text heuristics in `sniff_content_type(...)` beginning at `backend/app/services/nrc_aps_media_detection.py:151`.
- OOXML spreadsheet packages are now sniffed as spreadsheet media rather than generic ZIP when the package contains workbook markers at `backend/app/services/nrc_aps_media_detection.py:176`.
- If the sniffed type is refused, resolution returns unsupported/refused before supported fallbacks at `backend/app/services/nrc_aps_media_detection.py:261`.
- If declared, sniffed, or extension context identifies JSON/XML/HTML, resolution refuses the artifact.
- If declared or extension context identifies CSV and the body has a compatible text signature, resolution admits `text/csv`.
- If declared, sniffed, or extension context identifies spreadsheet media, resolution returns `typed_content_type_not_admitted` with `supported_for_processing=False`.
- If the sniffed type is supported, resolution accepts it at `backend/app/services/nrc_aps_media_detection.py:315`.

Implications:

- JSON, XML, and HTML are not pending "maybe supported" file types. They are explicitly refused today.
- XLSX and other Office Open XML files are no longer accepted as generic ZIP when filename or OOXML package evidence identifies them as spreadsheets.
- CSV is now parser-admitted for typed diagnostics and can be materialized through the callable dataset bridge. Connector finalization can invoke that bridge only when `csv_dataset_bridge_enabled=true` and processed CSV table artifacts exist. Explicit Layer 3 material preview can now admit those APS-derived `DatasetVersion` records through the existing `dataset_version` source shape.

## Document Processing Facts

Confirmed:

- `backend/app/services/nrc_aps_parser_registry.py` now defines metadata-only parser admission for current baseline PDF, Candidate B PDF, plain text, image OCR, and archive bundle processors.
- `backend/app/services/nrc_aps_csv_parser.py` now parses bounded CSV/delimited tables into `table_units`, optional `time_series_units`, and table diagnostics.
- The parser registry returns stable `parser_registry_contract_id`, `parser_registry_version`, `parser_admission_status`, `parser_family`, `parser_output_family`, and `parser_contract_id` fields for admitted processors.
- Unsupported parser lookups and media-not-supported lookups fail closed with stable parser failure codes.
- Candidate B is named `candidate_b_opendataloader_pdf` at `backend/app/services/nrc_aps_document_processing.py:58`.
- Candidate B fails closed on non-PDF input with `document_processing_engine_requires_pdf`.
- The top-level processor dispatches `text/plain`, PDF, image types, and `application/zip`; unsupported types fail outside those branches.
- `_process_plain_text` emits `document_class="text_plain"` and `ordered_units` text blocks beginning at `backend/app/services/nrc_aps_document_processing.py:351`.
- `_process_image` emits `document_class="standalone_image"` and OCR-derived ordered units at `backend/app/services/nrc_aps_document_processing.py:403`, `backend/app/services/nrc_aps_document_processing.py:531`, and `backend/app/services/nrc_aps_document_processing.py:536`.
- `_process_zip` maps supported document/image members into the existing handlers, parses CSV members for table diagnostics, and keeps spreadsheet/JSON/XML/HTML members visible as unadmitted/refused outcomes instead of flattening them into text.
- PDF baseline processing emits a document class and ordered units at `backend/app/services/nrc_aps_document_processing.py:882`, `backend/app/services/nrc_aps_document_processing.py:891`, and `backend/app/services/nrc_aps_document_processing.py:896`.
- Candidate B emits ordered units and a document class through the same existing contract shape at `backend/app/services/nrc_aps_document_processing.py:1086` through `backend/app/services/nrc_aps_document_processing.py:1160`.

Implications:

- The current processor is normalized-text and ordered-unit oriented.
- The registry is an admission and diagnostics boundary, not a new parser execution framework.
- CSV-in-ZIP is now visible as typed table diagnostics. It still does not produce workbook metadata or dataset rows.
- Candidate B should not be widened to non-PDF input. It is a PDF engine and should remain a parser family inside the PDF lane.

## Content Index Facts

Confirmed:

- The APS content contract is `aps_content_units_v2` at `backend/app/services/nrc_aps_content_index.py:30`.
- `chunk_document_units` accepts `ordered_units` and filters units with non-empty `text` at `backend/app/services/nrc_aps_content_index.py:179` through `backend/app/services/nrc_aps_content_index.py:186`.
- The content index writes normalized text blobs at `backend/app/services/nrc_aps_content_index.py:215` through `backend/app/services/nrc_aps_content_index.py:237`.
- Processed document loading carries `ordered_units`, `document_class`, and `effective_content_type` at `backend/app/services/nrc_aps_content_index.py:265` through `backend/app/services/nrc_aps_content_index.py:314`.
- Chunk metadata derives `unit_kind` from text units at `backend/app/services/nrc_aps_content_index.py:326` and `backend/app/services/nrc_aps_content_index.py:335`.
- DB persistence writes `ApsContentDocument` and `ApsContentChunk` rows with media type, document class, chunk refs, and unit kind at `backend/app/services/nrc_aps_content_index.py:646` through `backend/app/services/nrc_aps_content_index.py:705`.
- Serialized content search rows expose content/chunk fields, normalized text references, media type, and document class at `backend/app/services/nrc_aps_content_index.py:776` through `backend/app/services/nrc_aps_content_index.py:806`.

Implications:

- The current content index can represent document-like text chunks.
- It does not represent typed tables, time-series observations, variable definitions, workbook sheets, SEC/EDGAR section/table provenance, or row-level numeric lineage.

## APS Connector Facts

Confirmed:

- Connector config admits artifact pipeline modes and content chunking settings at `backend/app/services/connectors_nrc_adams.py:90` through `backend/app/services/connectors_nrc_adams.py:97`.
- Artifact download records response `content_type` at `backend/app/services/connectors_nrc_adams.py:989` and `backend/app/services/connectors_nrc_adams.py:1050`.
- Runtime target processing records declared/sniffed/effective content type and fails unsupported media at `backend/app/services/connectors_nrc_adams.py:2492` through `backend/app/services/connectors_nrc_adams.py:2534`.
- The connector calls artifact extraction/normalization and writes processed target artifact payloads with media, parser-registry, typed-table, extraction, quality, and visual-page diagnostics.
- Run finalization records artifact pipeline mode, text normalization contract, content contract, chunking contract, and chunking policy in `query_plan_json` at `backend/app/services/connectors_nrc_adams.py:3439` through `backend/app/services/connectors_nrc_adams.py:3465`.
- Run finalization generates artifact-ingestion and content-index reports at `backend/app/services/connectors_nrc_adams.py:3477` through `backend/app/services/connectors_nrc_adams.py:3539`.

Implications:

- The APS connector is already wired for download, media detection, extraction, normalization, content indexing, and report references.
- The connector wiring is no longer the missing piece for CSV. Remaining connector/parser work is for non-CSV parser families and operator/UI selection surfaces.

## Layer 3 Facts

Confirmed:

- The workbench supports source classes `dataset_version` and `aps_content_document` at `backend/app/services/layer3_workbench.py:84`.
- Unsupported classes include non-admitted broader source families at `backend/app/services/layer3_workbench.py:85`.
- Material preview maps `dataset_version` to `tabular_numeric` and `aps_content_document` to `document_chunks`.
- Material preview can now accept explicit `dataset_version_ids` and serialize APS-derived dataset provenance from `DatasetSourceProvenance`.
- Gate B material snapshots record `source_shape=item["source_class"]` and can persist echoed real dataset source identity/provenance.
- Selected-pass execution/result/package commit can now preserve single `dataset_version` source shape and `source_dataset_version_ids` for APS-derived dataset packages.
- Typing rules map `dataset_version` to `tabular_numeric` and `aps_content_document` to `document_chunks` at `backend/app/services/layer3_typing_entry.py:81` through `backend/app/services/layer3_typing_entry.py:88`.
- Layer 3 APS handoff requires material snapshots with `source_shape="aps_content_document"` and source identity containing `content_id`, `run_id`, and `target_id` at `backend/app/services/layer3_aps_handoff.py:249` through `backend/app/services/layer3_aps_handoff.py:268`.
- Layer 3 APS handoff reads `ApsContentDocument`, `ApsContentChunk`, and linkage rows under the APS content/chunking contracts at `backend/app/services/layer3_aps_handoff.py:315` through `backend/app/services/layer3_aps_handoff.py:337`.

Implications:

- The Layer 3 workbench has a split between document chunks and tabular datasets.
- Typed quantitative capability exists behind `dataset_version`, not behind `aps_content_document`.
- APS-derived typed data now uses promotion into `DatasetVersion` for CSV bridge output. A new source shape remains unnecessary unless a later UI/operator clarity review proves the existing `dataset_version` source shape is insufficient.

## Dataset And Analysis Facts

Confirmed:

- The model layer has `Dataset`, `DatasetVersion`, `VariableDefinition`, and `DatasetRow` at `backend/app/models/models.py:36`, `backend/app/models/models.py:53`, `backend/app/models/models.py:77`, and `backend/app/models/models.py:729`.
- The model layer has source provenance models at `backend/app/models/models.py:681` and `backend/app/models/models.py:694`.
- The model layer has Layer 3 session/material/typing/pass/package rows at `backend/app/models/models.py:742`, `backend/app/models/models.py:814`, `backend/app/models/models.py:833`, `backend/app/models/models.py:910`, and `backend/app/models/models.py:943`.
- The analysis service registers cross-correlation, decomposition, structural-break, and descriptive-summary methods with time/numeric feature requirements at `backend/app/services/analysis.py:44` through `backend/app/services/analysis.py:118`.
- Method recommendation uses time-column and numeric-column conditions at `backend/app/services/analysis.py:202` through `backend/app/services/analysis.py:230`.
- `backend/app/services/nrc_aps_dataset_bridge.py` can explicitly materialize CSV parser output into `Dataset`, `DatasetVersion`, `VariableDefinition`, `VariableProfile`, `DatasetRow`, `DatasetExternalIdentity`, and `DatasetSourceProvenance` records.
- The bridge uses deterministic dataset and dataset-version ids for the same source artifact key, parser contract, table index, and table hash.

Implications:

- The project already has downstream structures for time-series/tabular analysis once a `DatasetVersion` exists.
- APS ingestion can now create that dataset/variable/row/provenance shape from CSV parser output when the bridge is explicitly invoked.
- Connector finalization can invoke the bridge behind the `csv_dataset_bridge_enabled` gate for processed CSV table artifacts, and records bridge report refs plus target dataset refs.
- Layer 3 does not auto-discover all APS-derived dataset versions and does not add a distinct typed APS source class. Explicit material preview can admit selected APS-derived dataset versions through `dataset_version`.

## Test Coverage Facts

Confirmed:

- Document processing tests assert text/plain behavior at `tests/test_nrc_aps_document_processing.py:42`.
- Document processing tests assert Candidate B requires PDF at `tests/test_nrc_aps_document_processing.py:211`.
- Document processing tests assert Candidate B processes PDF through the existing contract shape at `tests/test_nrc_aps_document_processing.py:247`.
- Media detection tests now cover declared JSON refusal, declared/extension CSV admission behavior, OOXML spreadsheet sniffing, and XLSX extension fail-closed behavior.
- Document processing tests now cover CSV filename fail-closed behavior before typed parser admission at `tests/test_nrc_aps_document_processing.py:53`.
- Parser registry tests cover baseline PDF, Candidate B PDF, Candidate B non-PDF refusal, text, images, archives, and media-not-supported failure behavior.
- CSV parser tests cover positive table/time-series diagnostics, quoted delimiters, null markers, empty/header-only/ragged/invalid-encoding/formula-risk failures, and size bounds.
- Dataset bridge tests cover CSV parser output materialization, deterministic idempotency, dataset rows/profiles/provenance, and fail-closed rejection of non-CSV parser output.
- Archive tests now cover ZIP CSV member table diagnostics without text flattening.
- Content index tests cover chunking over ordered text units at `tests/test_nrc_aps_content_index.py:39` through `tests/test_nrc_aps_content_index.py:87`.
- Content index tests cover `text_plain` and PDF-like content rows at `tests/test_nrc_aps_content_index.py:210`, `tests/test_nrc_aps_content_index.py:233`, `tests/test_nrc_aps_content_index.py:267`, and `tests/test_nrc_aps_content_index.py:308`.
- Layer 3 tests seed `dataset_version` and `aps_content_document` separately in `backend/tests/test_layer3_api.py` and browser support fixtures.
- New Layer 3 workbench/API tests prove an APS-derived `DatasetVersion` with `DatasetSourceProvenance.source_system="nrc_adams_aps"` reaches material preview, Gate B, Gate C, and plan preview with `dataset_version_id` preserved.
- New Layer 3 API tests prove the same APS-derived `DatasetVersion` reaches execution start, result status, result review, package preview, and package commit with `dataset_version_id` and package source shape preserved.

Implications:

- Existing tests prove the current document/text and pre-seeded dataset paths.
- They do not prove APS CSV/XLSX/JSON/SEC/time-series ingestion into a typed dataset path.

## Completion Boundary

Complete today:

- APS artifact download and report wiring.
- Media detection for the currently admitted document families.
- PDF/text/image/ZIP document processing into normalized text and ordered units.
- Parser-registry metadata for the currently admitted document processors.
- CSV typed diagnostics for standalone CSV and ZIP CSV members.
- Callable CSV dataset bridge into `DatasetVersion` authority.
- Explicit Layer 3 material-preview/Gate B/Gate C/plan-preview admission for APS-derived `DatasetVersion` records.
- Selected-pass execution/result/package proof for APS-derived `DatasetVersion` records.
- APS content index persistence/search over document chunks.
- Candidate B PDF-only runtime processing through the existing document contract.
- Layer 3 workbench handling for `aps_content_document` as qualitative document chunks.
- Layer 3 handling for `dataset_version` when dataset rows/variables already exist.

Partial today:

- Plain qualitative text as document chunks.
- Image OCR as document chunks.
- ZIP bundles with supported member extraction into flattened document chunks.
- CSV as typed parser diagnostics, explicit/callable durable dataset materialization, default-off connector bridge orchestration, explicit Layer 3 admission, and selected-pass execution/package proof. UI/operator selection is still not implemented.

Not implemented today:

- Spreadsheet parser.
- JSON recordset parser.
- SEC/EDGAR filing parser.
- Parser families beyond CSV.
- UI/operator source selection for APS-derived dataset versions.
- End-to-end UI tests proving heterogeneous corpus artifacts reach Layer 3 with preserved source semantics.
