# 748 - Source Directory Ingestion Gate B Material Admission Runtime Proof

## Status

Status: branch-local runtime proof for `source_directory_ingestion_gate_b_material_admission`.

Doc: `748_SOURCE_DIRECTORY_INGESTION_GATE_B_MATERIAL_ADMISSION_RUNTIME_PROOF.md`.

Implementation branch: `codex/l3-source-directory-material-admission`.

Predecessor current-main sync doc: `747_SOURCE_DIRECTORY_INGESTION_DOWNSTREAM_MATERIAL_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before implementation: `0de713bb3a6ef465658c81c9cc829583afab726a`.

Runtime behavior change: `true`.

## Admitted Runtime

This slice implements only the selected downstream material authority over persisted source-directory ingestion rows.

Canonical upstream authorities:

- `L3SourceDirectoryIngestionBatch`
- `L3SourceDirectoryIngestionFile`

Runtime owner service: `backend/app/services/layer3_source_directory_material_admission.py`.

API owner: `backend/app/api/layer3.py`.

Material-preview route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/material-preview`.

Gate B route reuse: `POST /api/v1/layer3/gate-b/decision`.

Source-boundary owner: `backend/app/services/layer3_source_boundary.py`.

Admitted material candidate source class: `server_configured_directory_file`.

Admitted material candidate prefix: `mat-server_configured_directory_file-`.

The material-preview route requires the caller to name a persisted batch/file authority row and echo the persisted `file_identity_hash` and `authority_basis_hash`. The service re-reads only the configured direct-child file represented by that row, verifies the live file still matches persisted authority, returns a bounded UTF-8 text preview, and emits a Gate B decision basis.

The existing Gate B decision route now validates `server_configured_directory_file` decision basis before committing the selected candidate into the existing Layer 3 session/descriptor/material-snapshot path.

The existing Gate C typing entry now includes a bounded `server_configured_directory_file` text/table rule with `document_chunks` planning shape and `qualitative` modality, so a candidate admitted by this slice is not stranded immediately after Gate B.

## Proof

Focused validation passed:

```powershell
python -m py_compile .\backend\app\services\layer3_source_directory_material_admission.py .\backend\app\services\layer3_source_boundary.py .\backend\app\services\layer3_workbench.py .\backend\app\api\layer3.py
python -m pytest .\backend\tests\test_layer3_source_directory_ingestion.py .\backend\tests\test_layer3_source_boundary.py .\backend\tests\test_layer3_source_intake.py .\backend\tests\test_layer3_model_exports.py .\backend\tests\test_layer3_api.py::test_layer3_forbidden_sentinel_openapi_fields_are_impossible -q
```

Observed result: compile pass; `32 passed`.

Proof coverage:

- OpenAPI request schema for material preview is intentionally scoped and excludes caller path/recursive fields.
- Material preview reaches Gate B using persisted `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile` authority.
- Gate B persists a `server_configured_directory_file` `L3MaterialSnapshot`.
- Gate C preview types that material as `document_chunks` / `qualitative`.
- Source-directory configuration drift during preview or Gate B revalidation returns a blocked response instead of an unhandled server error.
- Live file inspection/read failures are converted to source-directory material-admission errors.
- Stale supplied file identity hash fails closed.
- Live file drift after ingestion fails closed.
- Raw configured root and absolute file paths are not exposed in responses.
- No `ConnectorRun`, `ConnectorRunTarget`, or `L3OutputPackage` rows are created.

## Still Blocked

This slice admits no RAG/vector indexing, qualitative-hybrid runtime, package construction, package mutation/reconstruction, source package row mutation, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, rendered controls, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, caller-supplied paths/URLs/globs, browser-supplied file bytes, browser/operator path editing, auth/security broadening, or source `L3OutputPackage` mutation.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_source_directory_ingestion_gate_b_material_admission_runtime_proof`.

After current-main sync, pivot under the standing rule: do not continue same-family source-directory package/export/active-authority loops unless current-main evidence names a concrete unresolved defect or downstream reader. The likely next major deferred lane is `select_rag_vector_or_qualitative_hybrid_authority_after_source_directory_material_admission_sync`, but only after current-main sync confirms the source/index authority question is named and frozen.
