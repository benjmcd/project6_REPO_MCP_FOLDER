# 00I Direct Backend Caller Closure Report

## Purpose

Record what is now directly verified about the backend caller path into the visual-lane owner system.

## Verified direct call chain

### Owner function
`backend/app/services/nrc_aps_document_processing.py`
- defines `process_document(...)`
- recursively calls itself for ZIP members

### Direct caller of `process_document(...)`
Verified by exact repo search:
- `backend/app/services/nrc_aps_artifact_ingestion.py`
  - `extract_and_normalize(...)` calls `nrc_aps_document_processing.process_document(...)`

No other direct backend callers were found in the searched `backend/**/*.py` surface.

### Direct callers of `extract_and_normalize(...)`
Verified by exact repo search:
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_content_index.py`

## Current verified backend chain

1. Connector orchestration path  
   `connectors_nrc_adams.py`  
   -> `nrc_aps_artifact_ingestion.extract_and_normalize(...)`  
   -> `nrc_aps_document_processing.process_document(...)`

2. Content-index path  
   `nrc_aps_content_index.py`  
   -> `nrc_aps_artifact_ingestion.extract_and_normalize(...)`  
   -> `nrc_aps_document_processing.process_document(...)`

3. ZIP recursion path  
   `process_document(...)`  
   -> recursive `process_document(...)` for ZIP members

## What this closes

This closes the **direct backend caller map** for the currently verified surfaces.

## What this does not close

It does not by itself close:
- broader indirect consumer effects,
- review/report/export visibility surfaces,
- non-backend surfaces not included in the current grep scope,
- any future dynamically introduced call paths outside the currently verified repo state.

## Updated interpretation

The remaining open item should now be phrased more precisely:

not “full caller map unknown,” but:

**indirect consumer closure beyond the verified direct backend caller chain remains open.**
