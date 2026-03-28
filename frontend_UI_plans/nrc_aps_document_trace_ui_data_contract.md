# NRC APS Document Trace UI Data Contract

## 1. Purpose

This document defines the additive read-only route and response-model plan for the NRC APS document-trace UI.

The contract is intentionally separated from the visual spec so that:

- the trace model is the authority
- the renderer can evolve without changing provenance semantics
- large document tabs can be loaded independently

## 2. Route Family

Recommended route families:

- UI route:
  - `/review/nrc-aps/document-trace`
- review API routes:
  - `/api/v1/review/nrc-aps/...`

All document-trace API routes in v1 should be:

- GET-only
- read-only
- bounded to review-safe runtime roots

## 3. Identity Model

The canonical document-trace identity is:

- `run_id + target_id`

Important secondary identifiers:

- `accession_number`
- `content_id`
- `chunk_id`

The contract must not use `content_id` alone as the page key because the audited runtime contains multiple targets that collapse to one persisted content identity.

## 4. Proposed Read-Only Endpoints

### 4.1 Document Selector

`GET /api/v1/review/nrc-aps/runs/{run_id}/documents`

Purpose:

- populate the document selector for one run
- provide run-scoped target rows that can launch the page

Response model:

```json
{
  "run_id": "string",
  "default_target_id": "string|null",
  "documents": [
    {
      "target_id": "string",
      "accession_number": "string|null",
      "document_title": "string|null",
      "document_type": "string|null",
      "media_type": "string|null",
      "content_id": "string|null",
      "trace_state": {
        "has_source_blob": true,
        "has_diagnostics": true,
        "has_normalized_text": true,
        "has_indexed_chunks": true,
        "has_downstream_usage": false
      }
    }
  ]
}
```

Sorting requirement:

- stable sort by accession number when present, then title, then `target_id`

### 4.2 Trace Manifest

`GET /api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/trace`

Purpose:

- return the authoritative document-trace assembly for the selected target
- drive page bootstrapping, tab availability, and identity rendering

Response model:

```json
{
  "run_id": "string",
  "target_id": "string",
  "identity": {
    "accession_number": "string|null",
    "document_title": "string|null",
    "document_type": "string|null",
    "media_type": "string|null",
    "source_file_name": "string|null",
    "content_id": "string|null",
    "content_contract_id": "string|null",
    "chunking_contract_id": "string|null",
    "normalization_contract_id": "string|null"
  },
  "source": {
    "viewer_kind": "pdf|text|json|csv|unsupported",
    "blob_ref_present": true,
    "source_endpoint": "/api/v1/review/nrc-aps/runs/.../documents/.../source",
    "content_type": "application/pdf",
    "size_bytes": 0
  },
  "summary": {
    "document_class": "layout_complex_pdf|null",
    "quality_status": "strong|null",
    "page_count": 13,
    "ordered_unit_count": 0,
    "indexed_chunk_count": 0
  },
  "trace_completeness": {
    "has_linkage_row": true,
    "has_document_row": true,
    "has_source_blob": true,
    "has_diagnostics": true,
    "has_normalized_text": true,
    "has_indexed_chunks": true,
    "has_visual_derivatives": false,
    "has_downstream_usage": false,
    "retrieval_available": false
  },
  "sync_capabilities": {
    "source_to_units": "unit",
    "units_to_source": "unit",
    "normalized_text_to_source": "best_effort",
    "chunk_to_source": "page"
  },
  "tabs": [
    {
      "tab_id": "summary",
      "label": "Summary",
      "available": true
    },
    {
      "tab_id": "extracted_units",
      "label": "Extracted Units",
      "available": true,
      "endpoint": "/api/v1/review/nrc-aps/runs/.../documents/.../extracted-units"
    }
  ],
  "warnings": [],
  "limitations": []
}
```

### 4.3 Source Document Stream

`GET /api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/source`

Purpose:

- stream the durable run-scoped source object referenced by `blob_ref`

Requirements:

- the route must resolve the source from the assembled trace model, not directly from user path input
- the route must verify the resolved path is within the allowed review runtime root
- the route must set content type from durable metadata when available and fall back conservatively
- the route must not expose arbitrary runtime paths

### 4.4 Extracted Units

`GET /api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/extracted-units`

Optional query parameters:

- `page_number`

Purpose:

- provide the fine-grained diagnostics-backed extracted-unit view

Response model:

```json
{
  "run_id": "string",
  "target_id": "string",
  "source_precision": "unit",
  "page_number": 1,
  "units": [
    {
      "unit_id": "string",
      "page_number": 1,
      "unit_kind": "paragraph",
      "text": "string",
      "bbox": [0, 0, 0, 0],
      "start_char": 0,
      "end_char": 100,
      "mapping_precision": "unit"
    }
  ]
}
```

Authoritative source for this endpoint in v1:

- diagnostics `ordered_units`

### 4.5 Normalized Text

`GET /api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/normalized-text`

Purpose:

- provide normalized text plus lightweight metadata

Response model:

```json
{
  "run_id": "string",
  "target_id": "string",
  "available": true,
  "char_count": 0,
  "mapping_precision": "best_effort",
  "text": "string"
}
```

### 4.6 Indexed Chunks

`GET /api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/indexed-chunks`

Optional query parameters:

- `page_number`

Purpose:

- return the chunk/index layer for the selected document

Response model:

```json
{
  "run_id": "string",
  "target_id": "string",
  "chunk_count": 0,
  "chunks": [
    {
      "chunk_id": "string",
      "chunk_ordinal": 0,
      "page_start": 1,
      "page_end": 1,
      "start_char": 0,
      "end_char": 250,
      "unit_kind": "paragraph",
      "quality_status": "strong|null",
      "chunk_text": "string",
      "mapping_precision": "page"
    }
  ]
}
```

Primary source for this endpoint in v1:

- `aps_content_chunk`

### 4.7 Diagnostics

`GET /api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/diagnostics`

Purpose:

- expose document-processing diagnostics and trace quality metadata

Response model:

```json
{
  "run_id": "string",
  "target_id": "string",
  "available": true,
  "quality_status": "strong|null",
  "document_class": "layout_complex_pdf|null",
  "page_count": 13,
  "ordered_unit_count": 0,
  "warnings": [],
  "degradation_codes": [],
  "extractor_metadata": {}
}
```

### 4.8 Downstream Usage

`GET /api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/downstream-usage`

Purpose:

- expose attributable downstream usage when it exists

Response model:

```json
{
  "run_id": "string",
  "target_id": "string",
  "available": true,
  "usage": [
    {
      "consumer_stage": "branch_a",
      "artifact_class": "evidence_bundle",
      "display_ref": "string",
      "attribution_precision": "document|branch|unknown"
    }
  ],
  "limitations": []
}
```

## 5. Required Contract Semantics

### 5.1 Missingness

Missingness must be explicit.

If a layer is absent, the response must:

- keep the endpoint stable
- return `available: false` or equivalent completeness flags
- include a short reason code when the absence is known

### 5.2 Sync Precision

Each tab payload that supports synchronization must report a precision tier:

- `page`
- `unit`
- `best_effort`
- `none`

### 5.3 Dedupe

The contract must surface both:

- `target_id`
- `content_id`

It must not collapse them into one identifier.

### 5.4 Retrieval

Retrieval data must be treated as optional or absent in v1.

There should be no required retrieval tab in the contract because the audited runtime has zero retrieval rows.

## 6. Non-Goals For The Contract

- no mutation routes
- no POST, PUT, PATCH, or DELETE routes
- no dependency on local corpus file paths
- no guarantee that downstream usage exists for every document
- no guarantee of exact region-level synchronization

