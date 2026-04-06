# 03Y Review/Report/Export Field Sensitivity Map

## Purpose

Provide the standalone field-level map that was still missing after merged M3/M4 closure.

This doc does not define the exact later-scope coexistence mechanism by itself.
It defines which live fields and write paths would expose experiment state if the next lane leaves them baseline-visible.

---

## Canonical live authority

This map is derived from the current merged-main authority chain:

- `backend/app/services/review_nrc_aps_runtime.py`
- `backend/app/services/review_nrc_aps_runtime_roots.py`
- `backend/app/services/review_nrc_aps_runtime_db.py`
- `backend/app/services/review_nrc_aps_catalog.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/app/services/review_nrc_aps_document_trace.py`
- `backend/app/schemas/review_nrc_aps.py`
- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/nrc_aps_evidence_report.py`
- `backend/app/services/nrc_aps_evidence_report_export.py`
- `backend/app/services/nrc_aps_evidence_report_export_package.py`

If any of those change materially, this map must be re-audited.

---

## Sensitivity rule

For the next later-scope lane, a field is sensitivity-relevant if populating it from experiment state would make the experiment:

1. discoverable through baseline-facing run selectors
2. queryable through baseline-facing review/document-trace APIs
3. persisted into shared `ConnectorRun.query_plan_json`
4. retrievable through shared diagnostics/content-index references

If a later-scope implementation touches one of the fields below, it must either:

- keep the field baseline-locked, or
- provide an explicit freeze rule for why that field remains safe.

---

## A. Run discovery and selector exposure

### Discovery inputs

The run selector is populated from `discover_runtime_bindings()` and `discover_candidate_runs()`.
Experiment state becomes baseline-visible if it reaches:

- summary-backed review roots under the allowlisted bases from `candidate_review_runtime_roots(...)`
- `ReviewRuntimeBinding.run_id`
- `ReviewRuntimeBinding.review_root`
- `ReviewRuntimeBinding.summary`
- `ConnectorRun.connector_run_id`

### Outward selector fields

The baseline-facing selector exposes:

- `run_id`
- `display_label`
- `status`
- `submitted_at`
- `completed_at`
- `reviewable`
- `disabled_reason_code`
- `summary_counters.selected_count`
- `summary_counters.downloaded_count`
- `summary_counters.failed_count`
- `default_run_id`

### Why these are sensitive

If an experiment reaches the allowlisted runtime-root discovery path and produces a summary-backed review root, it can become selectable through `get_runs()` even before any deeper API is queried.

`display_label` is also sensitive because it incorporates `binding.review_root.name`, which can expose naming/placement details of the underlying run root.

---

## B. Run-bound review projection and file surfaces

The following review endpoints expose run-bound state once `run_id` resolves a review root:

- pipeline definition
- overview
- tree
- node details
- file details
- file preview

### Outward fields

These surfaces expose or derive from:

- `run_id`
- `run_summary`
- projection `structured_summary`
- projection `artifact_refs`
- projection `mapped_file_refs`
- tree `path`
- file `path`
- file `name`
- file `content`
- file `preview_kind`
- file `mapped_node_ids`

### Why these are sensitive

Even if experiment document-trace data is hidden, a baseline-visible run root can still leak through projection/tree/file surfaces.

For the next lane, visibility control cannot stop at document selector or trace APIs.

---

## C. Document selector and trace surfaces

Once a run is discoverable and runtime DB access resolves, the review/document-trace plane exposes the following fields.

### Document selector fields

- `run_id`
- `default_target_id`
- `documents[].target_id`
- `documents[].accession_number`
- `documents[].document_title`
- `documents[].document_type`
- `documents[].media_type`
- `documents[].content_id`
- `documents[].trace_state.has_source_blob`
- `documents[].trace_state.has_diagnostics`
- `documents[].trace_state.has_normalized_text`
- `documents[].trace_state.has_indexed_chunks`
- `documents[].trace_state.has_downstream_usage`

### Trace manifest fields

- `run_id`
- `target_id`
- identity:
  - `accession_number`
  - `document_title`
  - `document_type`
  - `media_type`
  - `source_file_name`
  - `content_id`
  - `content_contract_id`
  - `chunking_contract_id`
  - `normalization_contract_id`
- source:
  - `blob_ref_present`
  - `source_endpoint`
  - `content_type`
  - `size_bytes`
  - `page_geometries`
- summary:
  - `document_class`
  - `quality_status`
  - `page_count`
  - `ordered_unit_count`
  - `indexed_chunk_count`
  - `visual_page_ref_count`
  - `visual_derivative_unit_count`
- completeness:
  - linkage/document/source/diagnostics/normalized-text/indexed-chunks/visual-derivatives/downstream flags
- tabs and warnings / limitations

### Diagnostics payload fields

- `run_id`
- `target_id`
- `quality_status`
- `document_class`
- `page_count`
- `ordered_unit_count`
- `visual_page_ref_count`
- `visual_derivative_unit_count`
- `unit_kind_counts`
- `warnings`
- `degradation_codes`
- `extractor_metadata`

### Normalized text fields

- `run_id`
- `target_id`
- `char_count`
- `mapping_precision`
- `text`

### Indexed chunk fields

- `run_id`
- `target_id`
- `chunk_count`
- per chunk:
  - `chunk_id`
  - `chunk_ordinal`
  - `page_start`
  - `page_end`
  - `start_char`
  - `end_char`
  - `unit_kind`
  - `quality_status`
  - `chunk_text`
  - `mapping_precision`

### Extracted unit and visual-artifact fields

- `run_id`
- `target_id`
- `reason_code`
- `source_precision`
- `source_layer`
- `page_number`
- `total_unit_count`
- `visual_artifacts[].artifact_id`
- `visual_artifacts[].page_number`
- `visual_artifacts[].status`
- `visual_artifacts[].visual_page_class`
- `visual_artifacts[].artifact_semantics`
- `visual_artifacts[].format`
- `visual_artifacts[].media_type`
- `visual_artifacts[].width`
- `visual_artifacts[].height`
- `visual_artifacts[].dpi`
- `visual_artifacts[].sha256`
- `visual_artifacts[].endpoint`
- `units[].unit_id`
- `units[].page_number`
- `units[].unit_kind`
- `units[].text`
- `units[].bbox`
- `units[].start_char`
- `units[].end_char`
- `units[].mapping_precision`

### Why these are sensitive

These fields are the actual baseline-facing manifestation of run-bound experiment state.
If experiment runs remain baseline-queryable by `run_id`, hiding only the filesystem root is insufficient.

---

## D. Content-index and diagnostics persistence fields

`nrc_aps_content_index.py` carries the run-bound linkage fields that later feed review/document-trace consumers.

### Run-bound linkage and payload fields

- `run_id`
- `target_id`
- `content_units_ref`
- `normalized_text_ref`
- `diagnostics_ref`
- `blob_ref`
- `blob_sha256`
- `download_exchange_ref`
- `discovery_ref`
- `selection_ref`
- `document_class`
- `quality_status`
- `page_count`
- `visual_page_refs`

### Why these are sensitive

These fields bridge processing output into persisted run-target state.
If experiment data writes to shared baseline-visible linkage rows or refs, later review APIs inherit the visibility automatically.

---

## E. Report/export/package persistence fields

The report/export services persist later-stage state back into shared `ConnectorRun.query_plan_json`.

### Evidence report persistence

Keys written under `run.query_plan_json`:

- `aps_evidence_report_report_refs.aps_evidence_reports[]`
- `aps_evidence_report_report_refs.aps_evidence_report_failures[]`
- `aps_evidence_report_summaries[]`

Summary fields include:

- `evidence_report_id`
- `source_citation_pack_id`
- `source_citation_pack_checksum`
- `total_sections`
- `total_citations`
- `total_groups`
- `ref`

### Evidence report export persistence

Keys written under `run.query_plan_json`:

- `aps_evidence_report_export_report_refs.aps_evidence_report_exports[]`
- `aps_evidence_report_export_report_refs.aps_evidence_report_export_failures[]`
- `aps_evidence_report_export_summaries[]`

Summary fields include:

- `evidence_report_export_id`
- `source_evidence_report_id`
- `source_evidence_report_checksum`
- `format_id`
- `total_sections`
- `total_citations`
- `total_groups`
- `ref`

### Evidence report export package persistence

Keys written under `run.query_plan_json`:

- `aps_evidence_report_export_package_report_refs.aps_evidence_report_export_packages[]`
- `aps_evidence_report_export_package_report_refs.aps_evidence_report_export_package_failures[]`
- `aps_evidence_report_export_package_summaries[]`

Summary fields include:

- `evidence_report_export_package_id`
- `evidence_report_export_package_checksum`
- `package_mode`
- `owner_run_id`
- `format_id`
- `source_export_count`
- `total_sections`
- `total_citations`
- `total_groups`
- `ordered_source_exports_sha256`
- `ref`

### Why these are sensitive

These write paths make experiment outputs visible through shared run-bound persistence even if runtime/artifact roots are separated.
`owner_run_id` is especially sensitive because it binds package state directly to a baseline-visible run identity.

---

## F. Approve-as-is implication for the next lane

For the next later-scope lane to be approve-as-is:

1. the exact coexistence mechanism must say which of the above fields stay baseline-locked
2. the exact visibility mechanism must say which fields are prevented from surfacing for experiment runs
3. validation must prove those fields remain absent or inaccessible through baseline-default discovery and baseline-facing APIs
4. any field that intentionally changes must be justified explicitly before implementation, not inferred during code review

Until that is frozen, later-scope implementation is not approve-as-is.
