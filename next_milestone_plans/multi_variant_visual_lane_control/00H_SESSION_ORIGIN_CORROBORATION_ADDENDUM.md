# 00H Session-Origin Corroboration Addendum

## Purpose

Capture the strongest **session-origin** findings that materially tighten the control model even where the current pass did not re-run every live check directly.

These are not unconditional live facts.
They are:
- repo-grounded findings from the attached session,
- useful for blocker tightening,
- and must remain explicitly labeled as session-origin unless re-verified again in the current pass.

## 1. Direct caller corroboration

### Session-origin finding
The attached session reports an exact direct caller map for `process_document(...)`:

#### Direct callers
1. `backend/app/services/nrc_aps_document_processing.py`
   - internal recursive ZIP-member call
2. `backend/app/services/nrc_aps_artifact_ingestion.py`
   - primary external direct caller via `extract_and_normalize(...)`

#### Near-direct / adapter consumers
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/nrc_aps_content_index.py`

### Status in current model
**Already broadly aligned, but now more explicit**

### Control implication
The current pack should continue treating:
- artifact ingestion,
- connector orchestration,
- content indexing/diagnostics,
as the minimum non-owner live impact surface.

## 2. Processing-config passthrough corroboration

### Session-origin finding
The attached session reports that `processing_config_from_run_config(...)` passes through:
- content parsing controls
- OCR controls
- `artifact_storage_dir`
- `visual_render_dpi`

before calling `default_processing_config(...)`.

### Status in current model
**Already aligned, but stronger now**

### Control implication
A future selector control is not entering a blank config path.
It is entering an existing processing-override lane that already carries artifact- and rendering-relevant controls.

## 3. `document_type` threading candidate

### Session-origin finding
The attached session reports that:
- a meaningful `document_type` signal already exists upstream,
- `_process_pdf(...)` consults `config.get("document_type")` for advanced-doc routing,
- but that signal may not yet be fully threaded into processing config.

### Status in current model
**Material tightening, still provisional**

### Control implication
`document_type` is now a credible candidate activation/control surface.
But it must still be treated as:
- candidate,
- not frozen selector key,
- not guaranteed fully threaded in the live path until re-verified again.

## 4. Review API exposure corroboration

### Session-origin finding
The attached session reports that review API endpoints expose at least:
- visual artifact
- diagnostics
- normalized text
- indexed chunks
- extracted units
- document trace

### Status in current model
**Material tightening**

### Control implication
The API-facing blast radius is broader than “review runtime” in the abstract.
A selector mistake could surface through any of these endpoint classes even if the underlying processing change looks local.

## 5. Isolation tightening

### Session-origin finding
The attached session argues that separate runtime/artifact roots alone do not guarantee out-of-band isolation because:
- review/catalog discovery can still aggregate across roots,
- and shared run visibility can still expose experiments.

### Status in current model
**Already adopted in v10, now reaffirmed**

### Control implication
No future plan should claim “isolated” on the basis of `storage_dir` or `artifact_storage_dir` separation alone.
