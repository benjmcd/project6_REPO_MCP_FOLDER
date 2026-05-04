# Phase P10D Closeout

Status: implemented in the current branch as bounded APS content-document selection and selected-material trace/detail surfacing.

## Scope

Phase P10D adds operator-facing selection and trace visibility for indexed APS content documents in the Layer 3 workbench.

Implemented:

- Read-only `GET /api/v1/layer3/aps-content-document-candidates` backed by `ApsContentDocument` plus first available `ApsContentLinkage`.
- `POST /api/v1/layer3/material-preview` accepts explicit `aps_content_document_ids` at the top level or under `query_basis.filters`.
- Selected APS content documents become DB-backed material candidates with `owner_service_source_shape="aps_content_document"` and `planning_shape_family="document_chunks"`.
- Material candidates include `layer3.aps_content_document_source_trace.v1` built from `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage`.
- The Gate B material ledger renders document identity, content contract, chunking contract, target, accession, chunks, pages, media type, document class, content-units refs, blob refs, and diagnostics refs without requiring raw JSON inspection.
- Gate B persistence preserves the selected document trace inside material snapshot source provenance.

Out of scope:

- No parser changes.
- No Candidate B changes.
- No schema, model, migration, or Layer 3 typing-rule changes.
- No document-trace-page redesign.
- No mixed-source package semantics.
- No HTML/XML/inline-XBRL parser admission.

## Justification

The source authority already exists in live models and services: indexed APS documents are represented as content documents, chunks, and linkage refs. The missing operator surface was selection and trace visibility in the workbench path that feeds Gate B. P10D therefore reuses existing authority rather than inventing a new source shape or parser path.

## Validation Targets

Required checks for this tranche:

- `python -m compileall .\backend\app\services\layer3_workbench.py .\backend\app\api\layer3.py .\backend\tests\review_browser_server.py`
- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py .\backend\tests\test_layer3_page.py -q`
- `npm run validate:structure`
- `git diff --check`
- Headless Playwright for `e2e/layer3-workbench.spec.js`.
- Headed Playwright for `e2e/layer3-workbench.spec.js`.

## Residual Boundary

P10D settles selected indexed APS content-document trace surfacing in the Layer 3 workbench. It does not settle refused-artifact trace surfacing, mixed qualitative-plus-table package semantics, SEC/EDGAR HTML/XML/inline-XBRL parsing, or a richer standalone document trace page.
