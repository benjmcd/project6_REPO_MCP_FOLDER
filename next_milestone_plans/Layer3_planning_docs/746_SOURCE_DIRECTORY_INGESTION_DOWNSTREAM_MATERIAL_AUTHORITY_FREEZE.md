# 746 - Source Directory Ingestion Downstream Material Authority Freeze

## Status

Status: branch-local downstream authority selection freeze for `source_directory_ingestion_gate_b_material_admission`.

Doc: `746_SOURCE_DIRECTORY_INGESTION_DOWNSTREAM_MATERIAL_AUTHORITY_FREEZE.md`.

Branch: `codex/l3-source-directory-downstream-selection`.

Current-main predecessor: `745_SERVER_CONFIGURED_OPERATOR_DIRECTORY_TEXT_TABLE_INGESTION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before selection: `4f909e63721bd1fd050fd9b4ae776b2898524c5b`.

Selected upstream runtime: `server_configured_operator_directory_text_table_ingestion`.

Selected source family: `server_configured_operator_directory_text_table_source_family`.

Selected downstream family: `source_directory_ingestion_material_authority`.

Selected downstream mode: `source_directory_ingestion_gate_b_material_admission`.

Selected downstream authority: `gate_b_material_candidate_from_source_directory_ingestion_file`.

Selected canonical upstream authorities: `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile`.

Selected future owner service: `backend/app/services/layer3_source_directory_material_admission.py`.

Selected future API owner: `backend/app/api/layer3.py`.

Selected future material-preview route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/material-preview`.

Selected future Gate B route reuse: `POST /api/v1/layer3/gate-b/decision`.

Runtime behavior introduced by this freeze: `false`.

Next posture after merge: `current_main_sync_source_directory_ingestion_downstream_material_authority_freeze`.

Next posture after sync: `implement_source_directory_ingestion_gate_b_material_admission_after_downstream_selection_sync`.

## Selection Rationale

Current main now has durable source-directory ingestion authority but deliberately leaves downstream material/index authority separate.

The selected downstream path is material admission before indexing. This follows the existing Layer 3 source-intake precedent: bounded source authority first, then material-preview/Gate B admission, then later typing/plan/execution/package flow. RAG/vector indexing and qualitative-hybrid retrieval remain blocked until material authority and separate source/index authority are selected and proven.

The next code-bearing pass may bridge one already-recorded source-directory ingestion file into Gate B material review. It must not rescan a directory, accept caller-supplied paths, read arbitrary files, create connector rows, create `L3OutputPackage` rows, or build an index.

## Future Runtime Contract

The later implementation may introduce only `source_directory_ingestion_gate_b_material_admission`.

Request authority must identify exactly one existing `L3SourceDirectoryIngestionBatch` and one existing `L3SourceDirectoryIngestionFile` by durable server-owned identifiers, plus the expected file identity hash or authority basis hash. It must not accept raw local paths, directory paths, glob patterns, browser file bytes, URLs, provider references, connector targets, package payloads, vector index identifiers, or hidden execution instructions.

Response authority may expose only Gate B material-candidate state, source-directory batch/file identifiers, redacted `server-configured://LAYER3_SOURCE_INGESTION_DIR` source refs, relative file names, media type, size, content hash, file identity hash, authority basis hash, material preview id/hash, status, blocked reason, and next allowed actions.

The selected material source class for the future implementation is `server_configured_directory_file`. CSV, JSON, TXT, and MD files must remain direct-child files from the previously recorded batch/file authority. PDFs, OCR, Office documents, arbitrary binaries, archives, executable files, recursive children, symlinks, and non-file children remain out of scope.

The future implementation must prove stale-authority rejection for missing batch/file rows, mismatched batch/file ownership, stale file identity hash, stale authority basis hash, unsupported extension, mismatched content hash, and any attempt to derive authority from a fresh directory scan instead of the persisted batch/file rows.

The future implementation must prove idempotency for repeated material-preview/admission requests over the same batch id, file id, file identity hash, authority basis hash, session, and client request key. Conflicting replay or changed authority basis must fail closed without creating duplicate material candidates.

## Required Future Tests

The implementation PR must include focused tests for:

- successful material preview from one persisted `L3SourceDirectoryIngestionFile`;
- successful Gate B candidate admission using only the server-returned material preview identity/hash;
- unknown batch id and unknown file id;
- file not belonging to the requested batch;
- stale file identity hash and stale authority basis hash;
- forbidden request fields, including nested `path`, `local_path`, `directory`, `glob`, `recursive`, `file`, `file_bytes`, `url`, `provider_url`, `connector_target`, `rag_index`, `vector_index`, `package_payload`, `execution_mode`, and `auth_policy`;
- no `ConnectorRun`, `ConnectorRunTarget`, `L3OutputPackage`, package mutation, connector dispatch, provider URL, RAG/vector index, qualitative-hybrid runtime, rendered controls, frontend durable authority, or auth/security behavior; and
- no raw configured root path or absolute local file path in responses or errors.

## Explicit Non-Admission

This freeze admits no runtime behavior, backend route behavior, service behavior, model change, migration, rendered UI control, source package row mutation, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, RAG/vector indexing, qualitative-hybrid analysis runtime, auth/security broadening, full mockup activation, frontend-durable authority, hidden LLM planning, arbitrary source ingestion, arbitrary recursive ingestion, broad local upload, PDFs, OCR, Office documents, arbitrary binaries, web connectors, or browser/operator path editing.

## Stop Condition

After this freeze is current-main synced, the next allowed code-bearing action is `implement_source_directory_ingestion_gate_b_material_admission_after_downstream_selection_sync` only.

If implementation discovers that source-directory material admission requires new package construction, RAG/vector indexing, raw path access, recursive traversal, source package row mutation, connector dispatch, provider URL behavior, frontend durable authority, auth/security broadening, or any source family beyond the persisted `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile` authorities, it must stop and return to planning instead of widening the runtime PR.
