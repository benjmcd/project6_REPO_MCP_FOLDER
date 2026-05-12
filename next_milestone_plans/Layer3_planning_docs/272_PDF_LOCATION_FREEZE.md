# Layer 3 PDF Location Use Case Freeze

Status: current-branch named runtime-use-case freeze for mockup PDF-location projection.

```yaml
selected_planning_mode: pdf_location_use_case_freeze
entry_decision: named_server_authoritative_runtime_use_case_selected_planning_only
base_branch: main
implementation_branch: codex/l3-pdf-location-use-case-freeze
live_behavior_change: false
upstream_gate_doc: 271_MOCKUP_RUNTIME_GATE.md
named_runtime_use_case: pdf_location_from_aps_content_document_citation
selected_activation_mode: single_mockup_screen_read_only_projection
selected_source_family: aps_content_document
server_authority_contract: aps_content_document_chunk_page_refs_and_citation_highlight_spans
runtime_implementation_allowed_next: true
next_allowed_action: implement_read_only_pdf_location_projection_from_existing_authority
```

## Decision

The first named runtime use case after the post-mockup runtime gate is the mockup PDF-location projection: given an existing server-authoritative APS content document, chunk/page identity, and citation/highlight provenance, the workbench may later render a read-only "where in the PDF did this come from" projection.

This freeze does not implement runtime behavior. It selects only the next allowed implementation boundary.

The use case is intentionally not source-breadth expansion. It must use existing `aps_content_document` authority and must not create a new source family, upload surface, local-directory ingestion path, arbitrary local path input, web retrieval path, vector/RAG retrieval layer, connector dispatch path, or browser-owned PDF-location authority.

## Canonical authority

The selected server authority is the existing APS document/citation chain:

- `ApsContentDocument` for document identity, media type, page count, and server-owned blob reference metadata.
- `ApsContentChunk.page_start` and `ApsContentChunk.page_end` for chunk-to-page location.
- `visual_page_refs_json` for canonical visual page references already preserved by the retrieval-plane contract.
- `nrc_aps_evidence_citation_pack` for persisted citation-pack provenance.
- `sections[].citations[].highlight_spans` for citation-to-text-span evidence where a citation pack is present.
- `source_bundle.run_id`, bundle id, bundle checksum, citation id, content id, and chunk id for stale-authority checks.

The browser may display these values, but it may not invent, persist, or correct them as authority.

## Future implementation contract

A later implementation may proceed only as a read-only projection from existing authority:

- Resolve the selected session/run/result/citation to one existing `aps_content_document` identity.
- Resolve one or more chunk/page references from `ApsContentChunk.page_start`, `ApsContentChunk.page_end`, `visual_page_refs_json`, or citation-pack `sections[].citations[].highlight_spans`.
- Fail closed when document identity, chunk identity, page references, citation pack, source bundle, run id, or checksum authority is missing or stale.
- Return only bounded location metadata and display labels needed for the workbench projection.
- Add headed and headless proof if rendered `/review/layer3` behavior changes.

## Forbidden in this slice and the next implementation

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
- no vector index creation
- no connector/destination dispatch
- no package mutation
- no broad qualitative/hybrid/RAG runtime
- no auth/security behavior change
- no full durable mockup activation
- no frontend-only durable authority

## Required tests for the next implementation

The implementation-entry pass that follows this freeze must include targeted tests for:

- successful projection from existing `aps_content_document` chunk/page/citation authority;
- fail-closed missing document identity;
- fail-closed stale run id, bundle id, bundle checksum, or citation id;
- fail-closed missing page/chunk/highlight authority;
- no raw path, blob ref, provider URL, token, prompt, or connector secret leakage in responses or UI;
- no backend source, package, connector, auth/security, RAG/vector, or full-mockup side effects;
- headed and headless rendered proof if the PDF-location projection is surfaced in the mockup workbench theme.

## Stop condition

Stop before code if the selected implementation cannot be expressed as a read-only projection from existing `ApsContentDocument`, chunk/page, visual-page-ref, and citation/highlight authority. In that case, the work must return to source-breadth or auth/security planning rather than widening this slice.
