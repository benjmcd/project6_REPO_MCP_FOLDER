# 286 - Source Breadth Runtime Entry Freeze

Status: branch-local implementation entry

Date: 2026-05-13

Authoritative branch: `codex/l3-source-breadth-runtime`

## Approved runtime packet

```yaml
runtime_family: source_breadth_runtime
operator_product_use_case: server-owned operator upload of a single source document/corpus that current dataset_version and aps_content_document paths cannot represent
server_authority: Layer 3 source intake record owning source identity, bytes/metadata hash, provenance, freshness, storage pointer, and downstream eligibility
```

## Canonical source of truth

The runtime source of truth is the new persisted Layer 3 intake record, not the general CSV ingest route, not a UI-local file handle, and not a downstream material preview candidate.

Runtime authority surfaces:

- Model/table: `L3SourceIntakeRecord` / `l3_source_intake_record`
- Migration: `backend/alembic/versions/0024_layer3_source_intake_record.py`
- Service: `backend/app/services/layer3_source_intake.py`
- Route: `POST /api/v1/layer3/source/intake/upload`
- Boundary contract: `backend/app/services/layer3_source_boundary.py`

## Scope admitted in this freeze

This slice admits one narrow product use case:

- The operator uploads one source document or source-corpus file to the Layer 3 server.
- The server reads the bytes, computes a content hash, computes a metadata hash, stores a server-owned storage pointer, records provenance and freshness metadata, and returns downstream eligibility.
- The record is idempotent by `client_request_id` and `authority_basis_hash`.
- The storage pointer returned to the client is a relative server storage reference, not an absolute local filesystem path.

## Explicitly not admitted

This slice does not admit any of the following:

- Broad file upload source expansion.
- Local directory ingestion.
- Local path authority.
- Web connector fetch.
- RAG or vector-index source authority.
- Unbounded runtime database writes.
- Operator-uploaded material preview.
- Operator-uploaded package construction.
- UI source browsing.
- General `/sources/upload` widening.

The existing source-preview source classes remain exactly:

- `dataset_version`
- `aps_content_document`

The new route is a source-intake authority route. It is not a new `source_preview` candidate class and is not a material-preview path.

## Request contract

Route:

```text
POST /api/v1/layer3/source/intake/upload
Content-Type: multipart/form-data
```

Required fields:

- `file`
- `client_request_id`
- `operator_decision`
- `source_label`

Required operator decision:

```text
record_operator_uploaded_source
```

Optional fields:

- `source_description`
- `source_family`
- `freshness_timestamp`
- `declared_media_type`

If supplied, `source_family` must be:

```text
operator_uploaded_single_source
```

## Stored authority fields

Each accepted upload persists:

- `source_intake_record_id`
- `client_request_id`
- `operator_decision`
- `source_family`
- `source_label`
- `source_description`
- `original_filename`
- `media_type`
- `content_size_bytes`
- `content_sha256`
- `metadata_hash`
- `authority_basis_hash`
- `storage_ref`
- `freshness_timestamp`
- `provenance_json`
- `downstream_eligibility_json`
- `summary_json`
- `status`

## Downstream eligibility returned

The route returns:

```json
{
  "source_intake_recorded": true,
  "eligible_for_source_inventory": true,
  "eligible_for_material_preview": false,
  "material_preview_requires_later_freeze": true,
  "eligible_for_rag_vector_index": false,
  "eligible_for_web_connector": false,
  "eligible_for_unbounded_runtime_db": false
}
```

This is intentionally a recorded-authority step only. Later runtime work must define a separate freeze before operator-uploaded source intake can feed material preview, RAG, connector dispatch, package construction, or UI flows.

## Rejection contract

The route fails closed for deferred or forbidden source-mode fields, including:

- `source_upload`
- `local_upload`
- `local_directory`
- `local_path`
- `web_connector`
- `connector_key`
- `connector_run_id`
- `rag_vector_index`
- `rag_plan`
- `vector_plan`
- `runtime_db_query`
- `runtime_db_write`
- `provider_url`
- `public_url`
- `signed_url`
- `destination_url`
- `package_payload`
- `source_expansion`
- `schema_widening`
- `auth_context`
- `browser_durable_authority`

Unknown fields are rejected because the contract is intentionally scoped.

## Proof plan

Targeted proof is bounded to:

- Source boundary contract keeps `dataset_version` and `aps_content_document` as the only source-preview classes.
- Source boundary contract exposes the new operator upload intake mode while keeping broad upload, local directory, web connector, RAG/vector, and unbounded runtime DB disabled.
- OpenAPI exposes the new multipart route and required response shape.
- Uploading a valid source creates a server-owned intake authority record response with relative storage pointer and no material-preview eligibility.
- Replaying the same upload returns the existing authority record idempotently.
- Deferred source-mode fields fail closed.
- Wrong operator decision fails closed.

Implemented proof file:

```text
backend/tests/test_layer3_source_intake.py
```
