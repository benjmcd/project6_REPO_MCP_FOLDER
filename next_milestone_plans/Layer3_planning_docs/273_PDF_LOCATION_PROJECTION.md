# Layer 3 PDF Location Projection Proof

Status: current-branch backend/API session-summary implementation proof for PDF-location projection.

```yaml
selected_runtime_mode: read_only_pdf_location_projection_from_existing_authority
entry_freeze: 272_PDF_LOCATION_FREEZE.md
implementation_branch: codex/l3-pdf-location-projection
live_behavior_change: true
route_api_behavior_change: true
model_migration_behavior_change: false
named_runtime_use_case: pdf_location_from_aps_content_document_citation
schema_id: layer3.pdf_location_projection.v1
```

## Implemented boundary

This pass implements the first server-authoritative PDF-location projection as read-only session-summary state. The projection is computed from existing `ApsContentDocument`, `ApsContentChunk.page_start`, `ApsContentChunk.page_end`, `visual_page_refs_json`, output payload chunk identity, and optional `sections[].citations[].highlight_spans` evidence.

Implemented surfaces:

- `backend/app/services/layer3_pdf_location.py`
- `backend/tests/test_layer3_pdf_location.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/api/layer3.py`
- `tools/l3-progress-check.py`

The route/API behavior change is limited to adding a `pdf_location_projection` object to the existing `/api/v1/layer3/session/{session_id}` response model and session summary payload. No new endpoint, model, migration, PDF streaming path, source adapter, connector, package mutation, auth/security behavior, or browser-owned durable authority is introduced.

## Fail-closed behavior

The projection is unavailable when the completed pass output is absent, unreadable, malformed, not `aps_content_document`, missing document identity, missing document authority, missing chunk authority, or missing page authority.

When available, the response returns bounded page/chunk/citation metadata only. It does not expose `blob_ref`, raw PDF paths, diagnostics paths, provider URLs, object-store URLs, tokens, prompts, connector secrets, or raw PDF bytes.

## Still blocked

- no raw PDF blob streaming
- no PDF byte download or provider/object-store URL exposure
- no browser-owned authoritative PDF location
- no browser correction of server page, chunk, or citation authority
- no new source family runtime
- no local upload
- no local-directory ingestion
- no arbitrary local path input
- no web connector retrieval
- no RAG/vector retrieval
- no connector/destination dispatch
- no package mutation
- no broad qualitative/hybrid/RAG runtime
- no auth/security behavior change
- no full durable mockup activation
- no frontend-only durable authority

## Validation

- `python -m py_compile .\backend\app\services\layer3_pdf_location.py .\backend\app\services\layer3_workbench.py .\backend\app\api\layer3.py .\tools\l3-progress-check.py`
- `python -m pytest .\backend\tests\test_layer3_pdf_location.py -q`
- `python .\tools\l3-progress-check.py`
