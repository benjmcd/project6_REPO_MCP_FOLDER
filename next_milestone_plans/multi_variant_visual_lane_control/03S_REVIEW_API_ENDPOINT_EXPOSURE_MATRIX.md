# 03S Review API Endpoint Exposure Matrix

## Purpose

Enumerate the verified baseline-facing review API surfaces that would expose experiment runs or experiment-derived artifacts/data if isolation is insufficient.

## Verified endpoints

### Run selector
- `get_runs()`
- Source: `discover_candidate_runs()`
- Exposure class: run visibility / discoverability

### Visual artifact
- `get_document_visual_artifact(run_id, target_id, artifact_id)`
- Exposure class: preserved visual artifacts by run

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
