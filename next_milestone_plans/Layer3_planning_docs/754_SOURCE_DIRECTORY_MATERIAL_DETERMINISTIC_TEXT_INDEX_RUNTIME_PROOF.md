# 754 - Source Directory Material Deterministic Text Index Runtime Proof

## Status

Status: branch-local runtime proof for `source_directory_material_deterministic_text_index_authority`.

Doc: `754_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_TEXT_INDEX_RUNTIME_PROOF.md`.

Runtime branch: `codex/l3-source-index-text-impl`.

Current-main checkpoint before implementation: `fb107c909a69a43a1f9ceb5eb1acc2e1685e2361`.

Predecessor current-main sync doc: `753_SOURCE_DIRECTORY_MATERIAL_SOURCE_INDEX_AUTHORITY_CONTRACT_CURRENT_MAIN_SYNC.md`.

Predecessor result: `current_main_synced_source_directory_material_source_index_authority_contract`.

Selected implementation posture: `implement_source_directory_material_deterministic_text_index_authority_after_contract_sync`.

Runtime behavior introduced by this pass: `true`.

## Runtime Owner

Owner service: `backend/app/services/layer3_source_directory_text_index.py`.

Proof tests: `backend/tests/test_layer3_source_directory_ingestion.py`.

No backend route, API DTO, model, migration, rendered UI control, frontend durable state, source-index durable table, vector table, embedding table, retrieval route, qualitative-hybrid route, package route, connector route, provider route, or auth/security behavior is introduced by this pass.

## Admitted Behavior

The runtime service admits only `source_directory_material_deterministic_text_index_authority` over already admitted `server_configured_directory_file` `L3MaterialSnapshot` rows.

The service reads and verifies existing authority from:

- `L3SourceDirectoryIngestionBatch`;
- `L3SourceDirectoryIngestionFile`; and
- `L3MaterialSnapshot`.

The request boundary accepts only `client_request_id`, `material_snapshot_id`, and optional stale-authority identity fields for `source_ingestion_batch_id`, `source_ingestion_file_id`, `content_sha256`, `file_identity_hash`, `authority_basis_hash`, and `payload_hash`.

The service fails closed on missing snapshot authority, non-`server_configured_directory_file` material, missing batch or file authority, unrecorded batch or file status, unsupported extension, stale request identity, mismatched material identity, unreadable or hash-drifted material payload, unavailable configured source root, non-direct-child relative name, path escape, source file read drift, UTF-8 decode failure, live file identity drift, empty text, unknown request fields, and forbidden deferred-scope fields.

The output is deterministic `deterministic_text_segments` with `SEGMENTATION_VERSION = "line-window-v1"`, stable `segment_id`, `segment_sequence`, line and character offsets, `segment_hash`, segment text, and a replay-stable `index_authority_hash`.

The service returns `source_index_rows_written: False` and negative invariants proving route admission, vector index, embedding generation, retrieval query, qualitative-hybrid runtime, connector dispatch, provider-public delivery, provider-private signed URL use, package construction, package mutation, frontend-durable authority, and network egress all remain disabled.

## Validation

Observed branch validation passed:

- `python -m py_compile .\backend\app\services\layer3_source_directory_text_index.py .\backend\tests\test_layer3_source_directory_ingestion.py`;
- `python -m pytest .\backend\tests\test_layer3_source_directory_ingestion.py -q` -> `13 passed`; and
- `python -m pytest .\backend\tests\test_layer3_source_boundary.py .\backend\tests\test_layer3_source_intake.py .\backend\tests\test_layer3_model_exports.py .\backend\tests\test_layer3_api.py::test_layer3_forbidden_sentinel_openapi_fields_are_impossible -q` -> `24 passed`.

The proof covers CSV, JSON, TXT, and MD source-directory files after material preview and Gate B admission; deterministic replay identity; fail-closed live file drift; fail-closed payload hash mismatch; forbidden retrieval/vector request fields; and absence of `ConnectorRun`, `ConnectorRunTarget`, and `L3OutputPackage` side effects.

## Still Blocked

This pass does not admit backend routes, API DTOs, model changes, migrations, source-index durable row writes, vector indexing, embedding generation, retrieval query runtime, qualitative-hybrid analysis runtime, package construction, package mutation/reconstruction, package payload rewrite, source `L3OutputPackage` mutation, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, or raw local path exposure.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_source_directory_material_deterministic_text_index_runtime_proof`.

After current-main sync, pivot to `select_next_retrieval_or_qualitative_hybrid_authority_after_text_index_runtime_sync` only if current-main evidence confirms the deterministic text index runtime is cleanly synced and no concrete unresolved defect or named same-family downstream reader remains.
