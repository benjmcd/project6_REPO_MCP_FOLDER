# Decisions And Open Questions

Status: decision log and self-audit for the multi-type ingestion planning lane.

## Settled Decisions

### D1: Current Support Must Be Described As Document-Chunk Support

Decision:

The current APS path is complete for the audited document-chunk ingestion path and audited downstream Layer 3 APS evidence consumers, not for heterogeneous typed data ingestion.

Reason:

Live source shows processing and indexing centered on normalized text, ordered units, `ApsContentDocument`, and `ApsContentChunk`. Layer 3 maps `aps_content_document` to `document_chunks`.

Risk avoided:

Avoids overclaiming CSV/text fallback or PDF processing as general corpus ingestion.

### D2: Candidate B Remains PDF-Only

Decision:

Candidate B should remain an OpenDataLoader PDF parser family. It should not be extended into general CSV/XLSX/JSON/SEC ingestion.

Reason:

Live source explicitly fails Candidate B on non-PDF. Its value is PDF-specific parser/runtime comparison, not heterogeneous file parsing.

Risk avoided:

Avoids coupling unrelated parser families to the Candidate B selector and preserving a clean baseline/Candidate A/Candidate B comparison boundary.

### D3: CSV-As-Text Is Not Tabular Support

Decision:

CSV currently flowing as `text/plain` or ZIP member text must not be treated as first-class tabular support.

Reason:

The current path loses schema, row, numeric, time-index, and variable semantics.

Risk avoided:

Avoids underbuilding the typed ingestion path while telling downstream workbench code that the pipeline already supports tables.

### D4: Classification Hardening Comes Before Parser Expansion

Decision:

The first implementation tranche should harden media classification and fail-closed diagnostics before adding new parser functionality.

Reason:

The highest immediate risk is not lack of parser volume; it is silent downgrade of structured files into text/archive success states.

Risk avoided:

Avoids accumulating parser-specific branches on top of ambiguous media detection.

### D5: Parser Registry Is The Modularity Boundary

Decision:

New parser families should be admitted through a parser registry or equivalent stable dispatcher, not by continuing to widen ad hoc branching inside the existing document processor.

Reason:

The target source set includes PDFs, text, images, archives, CSV, workbooks, JSON recordsets, and SEC filings. A registry makes parser admission, failure tokens, output contracts, and tests explicit.

Risk avoided:

Avoids fragile monolithic file-type handling and makes future parser addition reviewable.

### D6: Typed Data Should Reach Layer 3 Through Dataset Authority

Decision:

Tabular, numeric, financial, and time-series data should reach Layer 3 through `dataset_version` authority unless a later freeze explicitly creates a new typed source shape.

Reason:

The repo already has dataset, dataset version, variable, profile, row, provenance, and analysis method structures. The workbench already maps `dataset_version` to `tabular_numeric`.

Risk avoided:

Avoids duplicating quantitative analysis semantics inside `aps_content_document` chunks.

### D7: Mixed Filings Need Dual Representation

Decision:

SEC/EDGAR filings should be treated as mixed sources when tables are extracted: narrative sections map to document evidence, and extracted tables map to typed data.

Reason:

Financial filings combine qualitative context and structured tables. A single text-chunk representation is insufficient for numeric downstream work.

Risk avoided:

Avoids losing the relationship between filing narrative, table provenance, and quantitative data rows.

### D8: Architecture Quality Is An Acceptance Gate

Decision:

Flexibility, non-fragility, modularity, scalability, provenance stability, and bounded blast radius are acceptance requirements for this lane, not optional implementation preferences.

Reason:

The target corpus can include qualitatively different file families. If those families are admitted through ad hoc branches or lossy fallbacks, each new format will increase fragility and make Layer 3 source authority harder to audit.

Risk avoided:

Avoids accumulating tech debt where parser behavior, workbench source typing, and UI labels become coupled or inconsistent.

### D9: P2 Registry Is Metadata-Only

Decision:

The implemented Phase P2 parser registry is an admission and diagnostics contract, not a parser execution framework.

Reason:

The safe next move was to make current processor families explicit and testable before adding CSV parsing or dataset materialization. Rewriting dispatch at the same time would increase blast radius and make regressions harder to attribute.

Risk avoided:

Avoids coupling registry introduction to parser behavior changes, preserving existing PDF/text/image/archive outputs while making future parser admission mechanical.

### D10: P3 CSV Support Is Diagnostics-Only

Decision:

CSV is admitted only to bounded parser diagnostics in P3. It emits `table_units` and optional `time_series_units`; later phases are responsible for durable datasets, variables, rows, Layer 3 source admission, and UI affordances.

Reason:

The parser must prove table shape and source semantics before durable dataset materialization is introduced. Combining parser admission and dataset bridge in the same tranche would make failures harder to isolate.

Risk avoided:

Avoids claiming end-to-end typed ingestion before the dataset bridge, Layer 3 source authority, and UI/operator selection exist.

### D11: P4 Bridge Is Callable Before Runtime-Orchestrated

Decision:

P4 implemented an explicit callable CSV dataset bridge before connector finalization. P4.5 later added the legacy CSV-only runtime gate, and P7.5 later added the generic table runtime gate.

Reason:

The bridge needs its own idempotency, provenance, row, variable, profile, and storage guarantees before it becomes part of connector runtime orchestration.

Risk avoided:

Avoids making every CSV artifact alter durable dataset state before the admission and operator policy for automatic materialization is settled.

### D13: Generic Table Bridge Does Not Broaden The Legacy CSV Gate

Decision:

Phase P7.5 adds `table_dataset_bridge_enabled` and `aps.table_dataset_bridge_run.v1` instead of making `csv_dataset_bridge_enabled` accept XLSX.

Reason:

The legacy CSV gate and report names are already observable runtime contracts. Broadening them to include XLSX would make downstream consumers infer that generic table support is still CSV-specific, and would obscure whether a run used the compatibility bridge or the generic table-unit bridge.

Risk avoided:

Avoids CSV-named contract debt while preserving existing CSV consumers.

### D12: P5 Uses Existing DatasetVersion Source Shape

Decision:

APS-derived CSV table datasets should enter Layer 3 through the existing `dataset_version` source shape, with APS provenance carried in source identity/provenance fields instead of creating a new source class.

Reason:

The repo already maps `dataset_version` to `tabular_numeric` and pass-entry planning already admits dataset-version snapshots when `dataset_version_id`, variables, and storage are present. Adding a new source class would duplicate semantics and increase UI/API blast radius without a proven need.

Risk avoided:

Avoids source-shape proliferation and keeps typed quantitative data aligned with existing dataset authority while preserving APS source lineage.

## Open Questions

### Q1: What Is The First Typed Parser?

Current status:

CSV/delimited table diagnostics, the callable dataset bridge, opt-in legacy CSV connector/runtime orchestration, generic CSV/XLSX table connector/runtime orchestration, explicit Layer 3 APS-derived dataset admission, selected-pass execution/package proof, and bounded operator/UI selection are implemented. The next decision is broader parser-family sequencing.

Why:

CSV is simpler than spreadsheets and SEC filings, and it exercises the key downstream bridge into `DatasetVersion`.

Decision needed later:

Whether JSON recordset or SEC/EDGAR should be the next parser family, and when the legacy CSV bridge contract can be deprecated after generic table bridge adoption.

### Q2: Reuse Dataset Models Or Add A Bridge Table?

Current recommendation:

Prefer reusing existing dataset models, but audit whether `DatasetSourceProvenance` and `DatasetExternalIdentity` can carry APS artifact parser contract details without ambiguity.

Decision needed later:

Whether a dedicated APS artifact-to-dataset bridge table is required for source run/target/member/sheet/row provenance.

### Q3: How Should JSON Be Scoped?

Current recommendation:

Only admit JSON arrays of flat records or configured record paths. Keep arbitrary JSON refused.

Decision needed later:

Whether nested JSON flattening is allowed, and if so, what field-path and type semantics govern it.

### Q4: Which SEC/EDGAR Formats Are First?

Current recommendation:

Choose one narrow filing format first, likely a deterministic plain-text/SGML fixture before Inline XBRL/HTML/XML.

Decision needed later:

Which forms, encodings, metadata fields, and table extraction rules are in the first SEC/EDGAR tranche.

### Q5: Does Workbench Need A New Source Shape?

Current recommendation:

Use `dataset_version` for materialized typed APS data at first. APS provenance is now carried inside material-preview source identity/provenance and Gate B snapshots. Add a new source shape only if a later UI/operator clarity review proves the existing source shape is insufficient.

Decision needed later:

Whether `aps_dataset_version`, `aps_tabular_dataset`, or another source shape is needed for UI clarity. It is not required for the current backend authority path.

### Q6: How Far Should UI Go?

Current recommendation:

Backend authority now proves explicit typed source admission and selected-pass execution/package preservation for APS-derived CSV datasets. The next UI step should be minimal source-family selection/diagnostics before broader trace pages.

Decision needed later:

Whether document trace should remain document-only and whether a separate dataset/source trace is required.

## Grill-Me Self-Audit

Question: Are we overclaiming the current PDF path?

Answer: The docs say the PDF path is complete only for document/text/chunk semantics and downstream APS evidence consumers. They do not claim all Layer 3 semantics or all corpus types are solved.

Question: Are we underclaiming existing quantitative capability?

Answer: The docs preserve the fact that `dataset_version` time-series/tabular analysis exists downstream. They distinguish that from APS ingestion now creating datasets only for admitted CSV artifacts under an explicit runtime gate, not for arbitrary typed files.

Question: Is CSV support being represented accurately?

Answer: Yes. The docs state standalone CSV and ZIP CSV members now emit typed parser diagnostics, can be materialized through an explicit dataset bridge, can be invoked from connector finalization through the legacy CSV gate or generic table gate, and can enter Layer 3 when selected by explicit `dataset_version_id`. That is not broad heterogeneous support because JSON, SEC/EDGAR, and mixed parser families remain deferred.

Question: Is JSON/XML/HTML support being represented accurately?

Answer: Yes. The docs state these are explicitly refused today and should remain refused until specific parser families are admitted.

Question: Is XLSX risk explicitly handled?

Answer: Yes. The docs call out the ZIP-signature ambiguity, require XLSX to be classified as spreadsheet or refused, and now distinguish bounded standalone XLSX connector table-bridge orchestration from broad workbook/archive-member support.

Question: Does the plan preserve modularity and scalability?

Answer: Yes. It introduces classification hardening, parser registry, representation contracts, and dataset bridge boundaries before adding multiple parsers.

Question: Does the plan respect current Layer 3 source-shape authority?

Answer: Yes. It keeps `aps_content_document` as document chunks and `dataset_version` as typed quantitative material unless a later explicit freeze creates a new source shape.

Question: Does the plan account for tests and validation?

Answer: Yes. `04-validation.md` requires positive and negative fixture coverage by format, integration checks through APS ingestion and Layer 3, and browser checks only when UI assets change.

Question: What could still be missing?

Answer: Two items must be resolved during implementation planning: how UI should select/display APS-derived dataset versions, and which SEC/EDGAR filing format is admitted first. These are recorded as open questions rather than assumed.

## Immediate Next Action

Implement a UI/operator surfacing pass only after auditing the active workbench UI state:

- Expose APS-derived `DatasetVersion` candidates without treating UI state as source authority.
- Preserve backend-owned material-preview, Gate B, execution/result, and package contracts.
- Do not add new parser families, schema changes, or source shapes in the same PR.
- Keep document trace/document chunks separate from typed dataset selection unless a new mixed-source contract is explicitly defined.
