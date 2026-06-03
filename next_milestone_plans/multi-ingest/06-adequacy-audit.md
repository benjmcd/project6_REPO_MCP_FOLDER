# Adequacy Audit

Status: planning-pack self-audit for scope, justification, consistency, and implementation readiness. This audit now accounts for Phase P1 through Phase P10G implementation closeouts and the current-main SEC HTML/iXBRL reconciliation closeout; see `07-p1-closeout.md` through `25-p10g-gate-c-unsupported-trace-closeout.md`.

## Audit Question

Are the multi-type APS ingestion planning docs adequately laid out, constrained, scoped, justified, and aligned with live source and existing planning boundaries?

Answer: yes for the current bounded implementation lane. The pack is ready to govern the next implementation tranche, with explicit residual decisions preserved as open questions rather than assumptions. The SEC-specific HTML/iXBRL reconciliation checkpoint is now recorded as current-main authority rather than treated as an implicit exception to generic XML/HTML refusal.

Residual decisions:

- Whether existing dataset provenance models are sufficient or a dedicated APS artifact-to-dataset bridge table is required.
- How to connect the current-main SEC-specific HTML/iXBRL receipt chain to governed mixed-source package semantics without widening generic XML/HTML admission.

## Evidence Recheck

Confirmed from live source:

- Media detection supports PDF, text, ZIP, JPEG, PNG, TIFF, and JSON. XML and HTML are refusal content types.
- Candidate B raises `document_processing_engine_requires_pdf` for non-PDF input.
- Plain text emits `document_class="text_plain"` and ordered text units.
- ZIP processing records `.csv` members as typed table diagnostics instead of flattening them into text.
- Parser registry metadata is implemented for current PDF, Candidate B PDF, plain text, image OCR, and archive bundle processors.
- CSV parser diagnostics are implemented for bounded standalone CSV and ZIP CSV members.
- JSON parser diagnostics are implemented for bounded standalone JSON recordsets.
- SEC/EDGAR parser diagnostics are implemented for bounded complete submission text files with plain document text and simple delimited `<TABLE>` blocks.
- Current main separately admits `sec_edgar_html_inline_xbrl_source_family_parser_v1` as a governed SEC-specific HTML/iXBRL parser receipt chain; generic APS XML/HTML admission remains refused/deferred.
- A callable CSV dataset bridge is implemented using existing dataset, row, profile, identity, and provenance models.
- Content indexing is built around normalized text, ordered units, content documents, content chunks, and chunk unit kinds.
- Layer 3 workbench supports `dataset_version` and `aps_content_document`.
- Layer 3 typing maps `dataset_version` to `tabular_numeric` and `aps_content_document` to `document_chunks`.
- Layer 3 APS handoff reads APS content document/chunk/linkage rows, not typed dataset rows.
- Layer 3 material preview can now admit explicitly selected APS-derived `DatasetVersion` records while preserving APS source provenance.
- Layer 3 selected-pass execution/result/package commit now preserves single `dataset_version` source identity for APS-derived dataset packages.
- Layer 3 material preview now emits selected-material source trace detail for APS-derived `DatasetVersion` rows, and the Gate B material ledger renders that trace without requiring raw JSON inspection.
- Layer 3 workbench can now list/select indexed APS content documents, material preview can emit DB-backed `aps_content_document` candidates from `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage`, and the Gate B material ledger renders document/chunk/linkage trace detail without requiring raw JSON inspection.
- Layer 3 candidate and selected-material trace surfaces now label admitted server-owned raw mixed materialized `DatasetVersion` rows as `server_owned_raw_mixed` while preserving separate governance for mixed package semantics.
- Layer 3 workbench now renders source-family guardrail trace detail for refused/deferred families while preserving non-selectable status and no materialized `DatasetVersion` authority.
- Layer 3 Gate C unsupported material snapshots now carry trace detail from persisted `L3MaterialSnapshot` authority while preserving blocked typing and non-selectable status.

Confirmed from planning/status docs:

- Existing NRC APS status docs keep Candidate B PDF-only and preserve schema/model/migration/persistence widening as out of scope for that lane.
- Existing Layer 3 progress metadata repeatedly treats source/schema/runtime widening, qualitative/hybrid/RAG/vector behavior, local upload/directory ingestion, and full mockup activation as deferred unless a separate freeze admits them.
- The new multi-type lane therefore must not be represented as already admitted into the settled Layer 3 milestone-control spine.

## Scope Adequacy

Adequately scoped:

- The initial pack was docs-only. The current branch now also includes Phase P1 source/test changes recorded in `07-p1-closeout.md`, Phase P2 parser-registry source/test changes recorded in `08-p2-closeout.md`, Phase P3 CSV diagnostics source/test changes recorded in `09-p3-closeout.md`, Phase P4 dataset-bridge source/test changes recorded in `10-p4-closeout.md`, and subsequent closeout files through Phase P10G.
- The current verdict is limited to audited document-chunk paths, existing dataset paths, explicit APS-derived CSV/XLSX/JSON/SEC-EDGAR table dataset admission through `dataset_version`, selected-pass execution/package proof for that path, selected material trace detail, non-selectable guardrail trace detail, and Gate C unsupported material snapshot trace detail.
- The target design separates current implementation from future parser/bridge/workbench admission.
- Phase P1 is narrow: classification/refusal hardening and fixture coverage only.
- Broad generic XML/HTML parsing, broad source-shape expansion, archive-member XLSX/JSON/SEC-EDGAR orchestration, arbitrary JSON document semantics, nested JSON flattening, broad workbook semantics, and mixed-source package semantics are explicitly deferred. Bounded `.xlsx` parsing/materialization is implemented as Phase P7, bounded standalone XLSX connector table bridge orchestration is implemented as Phase P7.5, bounded standalone JSON recordset parser/materialization is implemented as Phase P8, bounded SEC/EDGAR complete-submission text parsing/materialization is implemented as Phase P9, and current main separately admits the governed SEC-specific HTML/iXBRL receipt chain.

Not over-scoped:

- The pack does not try to solve all heterogeneous ingestion at once.
- It does not claim arbitrary JSON, generic XML/HTML, broad SEC/EDGAR, financial filings, mixed-source packages, arbitrary workbooks, archive-member XLSX/JSON/SEC-EDGAR, or arbitrary time-series APS artifacts are already supported end to end. CSV is end-to-end through the explicit bridge/UI path; XLSX is bounded to standalone parser diagnostics plus explicit or opt-in connector table-unit materialization; JSON is bounded to standalone recordset parser diagnostics plus explicit or opt-in connector table-unit materialization; SEC/EDGAR is bounded to complete submission text files with plain document text and simple delimited table blocks plus the separate governed SEC-specific HTML/iXBRL receipt chain.
- It does not modify existing progress manifests because doing so would imply governance admission beyond this planning-entry pack.

Not under-scoped:

- It accounts for qualitative text, images, ZIP/archive behavior, CSV, spreadsheets, JSON recordsets, SEC/EDGAR filings, mixed qualitative/table sources, time-series data, financial/tabular data, dataset bridge requirements, Layer 3 source typing, workbench state, package/handoff provenance, and validation.
- It accounts for negative cases: empty, malformed, ambiguous, unsupported, oversized, encrypted, macro-enabled, heterogeneous, and unsafe files.
- It accounts for architecture quality: modularity, scalability, fail-closed behavior, parser isolation, provenance stability, idempotency, backwards compatibility, and bounded blast radius.

## Consistency Check

The docs are internally consistent on these boundaries:

- `aps_content_document` means document chunks and APS evidence consumers.
- `dataset_version` means typed quantitative/tabular/time-series analysis material.
- Candidate B means PDF-only OpenDataLoader PDF processing.
- CSV-as-text is not tabular support.
- JSON is admitted only for bounded recordsets; arbitrary JSON and generic XML/HTML remain refused until parser families are explicitly admitted. The current SEC-specific HTML/iXBRL receipt chain is already admitted, recorded in `22-sec-ixbrl-reconcile-closeout.md`, and remains separate from broad generic XML/HTML admission.
- XLSX must not be accepted as generic ZIP; `.xlsx` must route through `xlsx_workbook`, while `.xls`, `.xlsm`, encrypted, formula-bearing, empty, or ambiguous workbooks fail closed.
- UI projection must not become parser/source authority.
- Schema or migration work requires a separate freeze.

No contradiction found:

- `README.md` gives the operator-facing verdict and diagrams.
- `01-live-audit.md` records the source-backed evidence.
- `02-contract.md` defines target contracts and architecture quality properties.
- `03-implementation.md` converts the contract into bounded phases.
- `04-validation.md` defines the fixture and regression matrix.
- `05-decisions.md` records settled decisions and open questions.
- `07-p1-closeout.md` through `24-p10f-guardrail-trace-closeout.md` record implemented branch state, reconciliation state, and validation caveats.

## Grill-Me Self-Audit

Question: What would be the most likely overclaim?

Answer: Saying the pipeline supports all JSON, CSV, or non-PDF typed data merely because those artifacts may be downloaded or recognized. The pack avoids this by requiring typed parser output, dataset bridge authority, explicit Layer 3 source admission, and separate UI/operator surfacing before broader support is claimed.

Question: What would be the most likely omission?

Answer: Missing the XLSX-as-ZIP ambiguity. The pack explicitly marked XLSX detection/refusal as a P1 requirement and validation target; Phase P7 now admits bounded `.xlsx` parsing without weakening `.xls`/`.xlsm` refusal, and Phase P7.5 adds connector orchestration without widening workbook semantics.

Question: What would create avoidable tech debt?

Answer: Adding ad hoc file-type branches directly inside document processing or Layer 3 workbench logic. The pack requires a parser registry, representation contract, and dataset bridge boundary.

Question: What would make the plan fragile?

Answer: Letting UI labels, run display names, or fallback text normalization become source authority. The pack requires parser/source authority to be backend-owned and provenance-bearing.

Question: What must be true before implementation can claim heterogeneous ingestion is settled?

Answer: Targeted file families must have deterministic detection, parser fixtures, negative tests, representation contracts, dataset/content mapping, Layer 3 source admission or explicit refusal, package/handoff provenance, and existing PDF/document behavior must remain stable.

Question: Did P2 accidentally widen parser behavior?

Answer: No. P2 introduced metadata-only parser admission for already-existing processor families. CSV, XLSX, JSON recordset, bounded SEC/EDGAR complete-submission parser/materialization/orchestration work, and the separate SEC-specific HTML/iXBRL receipt chain were added later in bounded phases; arbitrary JSON, broad generic XML/HTML support, schema, new Layer 3 source-shape, and broad UI work remain deferred.

Question: Did P3 overclaim CSV support?

Answer: No. P3 admits CSV only as bounded parser diagnostics. It produces table units and time-series candidates, but no durable datasets, variables, rows, Layer 3 source admission, or UI projection.

Question: Did P4 overclaim end-to-end typed ingestion?

Answer: No. P4 adds explicit/callable dataset materialization for CSV parser output. P4.5 adds default-off CSV connector finalization orchestration behind `csv_dataset_bridge_enabled=true`. P7.5 adds default-off generic table connector orchestration behind `table_dataset_bridge_enabled=true`, and P8 reuses that generic path for bounded JSON recordsets. P5 adds explicit Layer 3 admission for APS-derived dataset versions, and P10A adds bounded operator selection.

Question: Did P5 create unnecessary source-shape or schema debt?

Answer: No. P5 reuses the existing `dataset_version` source shape and existing dataset provenance models. It adds DB-backed material-preview projection and Gate B persistence of source identity/provenance, not a new source class, schema, migration, or UI path.

Question: Did P6 overclaim mixed or APS handoff support?

Answer: No. P6 proves selected-pass quantitative execution/result/package construction for APS-derived `DatasetVersion` material. It does not claim APS document evidence-bundle handoff, mixed qualitative/table packages, or UI selection support.

Question: Did P8 overclaim JSON support?

Answer: No. P8 admits only standalone table-like JSON recordsets with flat records or configured record paths. It keeps arbitrary nested JSON, archive-member JSON orchestration, structured-document JSON, SEC/EDGAR JSON/XML/HTML filing semantics, schema changes, and new Layer 3 source semantics out of scope.

Question: Did P9 overclaim SEC/EDGAR support?

Answer: No. P9 admits only complete submission text files with SEC signature sniffing, admitted form types, plain document text, deterministic metadata/section extraction, and simple delimited `<TABLE>` materialization. Current main separately admits the SEC-specific HTML/iXBRL receipt chain. P9 still keeps unsupported forms, broad generic XML/HTML admission, ambiguous financial statements, archive-member filing orchestration, schema changes, new Layer 3 source semantics, and mixed-source package semantics out of scope.

## Validation Performed For The Initial Planning Pass

Required initial planning validation:

- Re-read created docs after edits.
- Rechecked source/status evidence with `Select-String`.
- Checked branch/worktree state.
- Ran trailing-whitespace scan.
- Ran ASCII scan.
- Ran `git diff --check`.

Tests intentionally not run:

- Pytest was not run for the initial planning pass because that pass changed only docs.
- Browser tests were not run because no UI assets changed.
- Runtime validation was not run because no executable pipeline behavior changed.

## Validation Performed For Phase P2

Passed:

- `python -m pytest .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_expansion.py -k "not candidate_b"`

Result:

- `55 passed, 9 deselected`.

Caveat:

- Pytest emitted a Windows temp cleanup `PermissionError` after the green result for `pytest-current`. This did not change the command exit code.

## Validation Performed For Phase P3

Passed:

- `python -m pytest .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_expansion.py -k "not candidate_b"`

Result:

- `76 passed, 9 deselected`.

Caveat:

- Pytest emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Validation Performed For Phase P4

Passed:

- `python -m pytest .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_expansion.py -k "not candidate_b"`

Result:

- `79 passed, 9 deselected`.

Caveat:

- Pytest emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Validation Performed For Phase P5

Passed:

- `python -m pytest .\backend\tests\test_layer3_workbench.py`
- `python -m pytest .\backend\tests\test_layer3_api.py -k "aps_derived_dataset_version or first_slice_preview_openapi_contracts or full_first_slice_flow"`

Result:

- Layer 3 workbench focused file: `10 passed`.
- Layer 3 API focused selection: `3 passed, 71 deselected`.

Caveat:

- Pytest emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Validation Performed For Phase P6

Passed:

- `python -m pytest .\backend\tests\test_layer3_api.py -k "aps_derived_dataset_version_reaches_package_commit"`
- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py`
- `python -m pytest .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_api.py .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_expansion.py .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py -k "not candidate_b"`

Result:

- `1 passed, 73 deselected`.
- Full Layer 3 workbench/API files: `84 passed`.
- Combined APS bridge/parser/media/document plus Layer 3 regression: `227 passed, 10 deselected`.

Caveat:

- Pytest emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Validation Performed For Phase P8

Passed:

- `python -m pytest .\tests\test_nrc_aps_json_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_nrc_aps_expansion.py .\tests\test_api.py -k "json or dataset_bridge or media_detection_expansion" -q`
- `python -m pytest .\tests\test_nrc_aps_json_parser.py .\tests\test_nrc_aps_spreadsheet_parser.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_expansion.py .\tests\test_api.py -k "not candidate_b" -q`
- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py -q`
- `npm run validate:structure`
- `git diff --check`

Result:

- `28 passed, 126 deselected`.
- `169 passed, 10 deselected`.
- `86 passed`.
- Structure validation: `errors: 0`, `warnings: 221` existing local-path/documentation warnings.
- Diff check: passed with line-ending conversion warnings only.

Caveat:

- Pytest emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Validation Performed For Phase P9

Passed:

- `python -m pytest .\tests\test_nrc_aps_sec_edgar_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_api.py -k "sec_edgar or parser_registry or media_detection or dataset_bridge" -q`
- `python -m pytest .\tests\test_nrc_aps_sec_edgar_parser.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_api.py -k "sec_edgar" -q`
- `python -m pytest .\tests\test_nrc_aps_sec_edgar_parser.py .\tests\test_nrc_aps_json_parser.py .\tests\test_nrc_aps_spreadsheet_parser.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_expansion.py .\tests\test_api.py -k "not candidate_b" -q`
- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py -q`
- `npm run validate:structure`
- `git diff --check`

Result:

- `43 passed, 112 deselected`.
- `11 passed, 126 deselected`.
- `181 passed, 10 deselected`.
- `86 passed`.
- Structure validation: `errors: 0`, `warnings: 221` existing local-path/documentation warnings.
- Diff check: passed with line-ending conversion warnings only.

Caveat:

- Pytest emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Final Planning Verdict

The pack is adequately scoped for the current bounded implementation lane and adequately specific for the next implementation step. It should not be treated as a completed heterogeneous-ingestion implementation. Phase P1 through Phase P10G are now implemented in this branch, and current main separately admits the governed SEC-specific HTML/iXBRL receipt chain with a recorded reconciliation checkpoint. The next correct action is a narrow parser-level refused artifact trace/detail surfacing pass backed by server authority, a separately scoped mixed-source package-semantics pass, or a legacy CSV bridge deprecation decision after generic table bridge adoption evidence is sufficient, while preserving all existing PDF/document, Candidate B PDF-only, generic XML/HTML refusal, and Layer 3 source-shape behavior.
