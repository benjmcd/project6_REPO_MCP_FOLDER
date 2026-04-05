# 03S Review API Endpoint Exposure Matrix

## Purpose

Enumerate the verified baseline-facing review API surfaces that would expose experiment runs or experiment-derived artifacts/data if isolation is insufficient.

## Verified endpoints

### Run selector
- `get_runs()`
- Source: `discover_candidate_runs()`
- Exposure class: run visibility / discoverability

### Pipeline definition
- `get_pipeline_definition(run_id)`
- Exposure class: run-scoped pipeline projection visibility

### Overview
- `get_run_overview(run_id)`
- Exposure class: run-scoped summary / projection / tree visibility

### Tree
- `get_run_tree(run_id)`
- Exposure class: run-scoped filesystem layout visibility

### Node details
- `get_node_details_route(run_id, node_id)`
- Exposure class: run-scoped node metadata visibility

### File details
- `get_file_details_route(run_id, tree_id)`
- Exposure class: run-scoped file metadata visibility

### File preview
- `get_file_preview_route(run_id, tree_id)`
- Exposure class: run-scoped file-content preview visibility

### Document selector
- `get_run_documents(run_id)`
- Exposure class: run-scoped target visibility

### Document trace
- `get_document_trace(run_id, target_id)`
- Exposure class: run-scoped trace visibility

### Source blob
- `get_document_source(run_id, target_id)`
- Exposure class: run-scoped source artifact visibility

### Diagnostics
- `get_document_diagnostics(run_id, target_id)`
- Exposure class: structured diagnostics by run

### Normalized text
- `get_document_normalized_text(run_id, target_id)`
- Exposure class: normalized text by run

### Indexed chunks
- `get_document_indexed_chunks(run_id, target_id)`
- Exposure class: indexed chunk payloads by run

### Extracted units
- `get_document_extracted_units(run_id, target_id)`
- Exposure class: extraction-unit payloads by run

## Operational implication

Experiment isolation must be judged against all of the above, not only against:
- storage root separation
- artifact root separation
- absence of public variant tagging

If an experiment run is visible to these baseline-facing endpoints, then isolation is insufficient for the first integrated phase.
