# Layer 3 Raw Ingestion Materialization Freeze

Status: bounded runtime contract for the first raw mixed-corpus source-authority materialization pass after `153_SOURCE_BREADTH_FREEZE.md`.

This artifact governs the exact first materialization boundary implemented by `codex/l3-raw-materialization-runtime` without widening source classes beyond current main.

## Decision

The selected raw-ingestion materialization mode is exactly:

- selected_raw_ingestion_mode: `raw_mixed_existing_source_materialization_entry`

The implementation may add only a server-owned manifest-to-source-authority materialization boundary for the current admitted source classes:

- `dataset_version`
- `aps_content_document`

It must not add a general source adapter registry, operator local upload, local-directory crawler, web connector retrieval, RAG/vector retrieval, provider/public URL, connector/destination dispatch, hidden LLM planning, full mockup activation, auth/security behavior, rendered UI control, or model/migration expansion.

## Runtime Surface

The selected runtime surface is:

- owner service: `backend/app/services/layer3_raw_mixed_materialization.py`
- route: `POST /api/v1/layer3/source/mixed-corpus/materialize`
- request DTO: `Layer3RawMixedCorpusMaterializeRequest`
- response DTO: `Layer3RawMixedCorpusMaterializeResponse`
- request schema id: `layer3.raw_mixed_corpus_materialize_request.v1`
- response schema id: `layer3.raw_mixed_corpus_materialize_result.v1`
- manifest schema id: `layer3.raw_mixed_corpus_materialization_manifest.v1`

The existing `POST /api/v1/layer3/source/mixed-corpus/seed` route remains seed-only and must continue to write no database rows or files.

## Authority And Inputs

The request may include only:

- `schema_id`
- `schema_version`
- `client_request_id`
- `materialization_mode`
- `corpus_batch_id`
- `artifact_manifest_ref`
- `artifact_manifest_hash`
- `requested_source_classes`
- `operator_confirmation`

The request must not include file bytes, local paths, directory paths, URLs to fetch, connector credentials, RAG/vector instructions, package instructions, destination instructions, provider URL instructions, UI state, hidden LLM instructions, mockup activation, auth overrides, schema migration instructions, or Layer 3 flow controls.

The manifest must be under the configured server-owned storage root, must be path-traversal safe, and must be SHA-256 checked before use. The manifest may point only to server-owned refs that already exist under the storage root.

## DB And File Behavior

The implementation may read:

- the server-owned materialization manifest;
- existing `Dataset`, `DatasetVersion`, `VariableDefinition`, `DatasetRow`, `VariableProfile`, and `DatasetSourceProvenance` rows for idempotent reuse/conflict checks;
- existing `ConnectorRun`, `ConnectorRunTarget`, `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage` rows for idempotent reuse/conflict checks;
- existing storage-root files referenced by the manifest for hash/size proof only.

The implementation may write only:

- deterministic `Dataset` rows required by materialized `DatasetVersion` authority;
- deterministic `DatasetVersion` rows;
- deterministic `VariableDefinition`, `DatasetRow`, and optional `VariableProfile` rows needed for the materialized dataset version to be consumable by existing Layer 3 source/material preview;
- deterministic `DatasetSourceProvenance` rows linking materialized dataset versions to server-owned source refs;
- deterministic `ConnectorRun` and `ConnectorRunTarget` rows only as manifest-declared source authority for APS content;
- deterministic `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage` rows needed for the materialized APS content document to be consumable by existing Layer 3 source/material preview.

The implementation must write no files. Source payload files must already exist under server-owned storage-root refs and must be hash checked before row materialization.

The implementation must create no `L3Session`, `L3Descriptor`, `L3SelectionManifest`, `L3MaterialSnapshot`, `L3TypingRecord`, `L3AnalysisPlan`, `L3PassRun`, execution/result/package/handoff/export state, connector dispatch/destination write, provider/public URL, signed URL, vector index, mockup state, or auth/security state.

No Layer 3 flow state during materialization is admitted.

## Idempotency And Concurrency

Idempotency must be deterministic by `client_request_id`, manifest hash, source class set, and manifest-declared deterministic IDs. Repeating the same request must return the same materialized source IDs without duplicate rows.

If an existing row has the same deterministic ID but mismatched manifest-declared hash, storage ref, source class, source provenance, chunk text hash, dataset row count, variable schema, or APS linkage authority, the implementation must fail closed before partial materialization.

The implementation must use a transaction around materialization. If row-level locking is available for the target rows, use it for existing-row checks; otherwise use deterministic IDs plus unique constraints and rollback-on-conflict behavior. Partial materialization on failure is not admitted.

## Required Tests

The implementation must include focused tests for:

- success materializing deterministic `dataset_version` and `aps_content_document` authority from a server-owned manifest;
- duplicate request/idempotent replay returning the same source IDs without duplicate rows;
- manifest missing, bad hash, malformed schema, unsupported source class, path traversal, missing storage-root file, and referenced-file hash mismatch fail closed;
- deterministic-ID conflict with mismatched row/source/hash/linkage authority fail closed;
- forbidden request fields fail before service mutation;
- failure cases write no DB rows and no files;
- success creates only admitted source-authority rows and no Layer 3 flow rows;
- the returned IDs can be consumed by the existing separate preflight/source-preview/material-preview/Gate B/Gate C path;
- negative invariants for local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, source adapter registry behavior, provider/public URL generation, connector/destination dispatch, package mutation/reconstruction, hidden LLM planning, full mockup activation, auth/security behavior, rendered UI controls, and frontend-only durable authority.

## Stop Conditions

Stop before runtime implementation if the intended change requires:

- accepting operator local file paths, file bytes, directories, or browser-uploaded files;
- fetching a web connector or external URL;
- creating a source adapter registry;
- adding or changing models/migrations;
- writing files;
- starting any Layer 3 flow phase inside materialization;
- creating package, handoff, export, connector dispatch, destination, provider/public URL, RAG/vector, mockup, or auth/security state;
- rendering new UI controls or theme behavior.

## Acceptance Criteria

This freeze is accepted only when:

- this file exists and names `selected_raw_ingestion_mode: raw_mixed_existing_source_materialization_entry`;
- `137_RAW_MIXED_BRIDGE_FREEZE.md` continues to identify the existing seed route as no-write seed-only behavior;
- `153_SOURCE_BREADTH_FREEZE.md` remains the source-breadth authority for current admitted source classes;
- progress/proof references identify this as a bounded runtime contract;
- `tools/l3-progress-check.py` requires this freeze and the no-write seed-route distinction;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` passes.
