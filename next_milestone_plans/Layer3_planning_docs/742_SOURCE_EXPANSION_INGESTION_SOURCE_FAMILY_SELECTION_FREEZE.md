# 742 - Source Expansion Ingestion Source Family Selection Freeze

## Status

Status: branch-local source-family selection and behavior freeze for `server_configured_operator_directory_text_table_source_family`.

Doc: `742_SOURCE_EXPANSION_INGESTION_SOURCE_FAMILY_SELECTION_FREEZE.md`.

Predecessor current-main sync doc: `741_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_EXTERNAL_LOCAL_EXPORT_EVALUATION_CURRENT_MAIN_SYNC.md`.

Planning branch: `codex/l3-source-family-selection`.

Current-main checkpoint before selection: `a9d9215fbb17758dc7cec317b7c56ddcbaf413ae`.

Selected deferred lane: `source_expansion_ingestion`.

Selected source family: `server_configured_operator_directory_text_table_source_family`.

Selected source-family class: `server_configured_local_directory_text_table_ingestion`.

Selected implementation-entry mode: `server_configured_operator_directory_text_table_ingestion`.

Implementation entry allowed after current-main sync: `true`.

Runtime status: `not_started_freeze_only`.

Runtime behavior change in this pass: `false`.

## Selected Source Family

The selected source family is a server-configured operator-provided local directory containing only bounded text/table files:

- `.csv`;
- `.json`;
- `.txt`; and
- `.md`.

The source root must be configured by the server/operator, not supplied by a browser request. The future implementation may enumerate only direct child files under that configured root. Non-recursive direct-child enumeration is required; recursive traversal is not admitted.

The future implementation should record durable ingestion batch/file authority before any downstream material admission. The likely implementation surfaces are:

- owner service: `backend/app/services/layer3_source_directory_ingestion.py`;
- API owner: `backend/app/api/layer3.py`;
- candidate scan route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- candidate status route: `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`;
- config authority: `LAYER3_SOURCE_INGESTION_DIR`;
- durable batch authority: `L3SourceDirectoryIngestionBatch`; and
- durable file authority: `L3SourceDirectoryIngestionFile`.

## Required Future Behavior

The implementation slice after current-main sync must:

- fail closed when `LAYER3_SOURCE_INGESTION_DIR` is unset, relative, missing, not a directory, inside app-owned storage, or inside local-outbox/export staging;
- reject all caller-supplied paths, URLs, glob patterns, recursive flags, and file-content payloads;
- enumerate direct child files only;
- admit only `.csv`, `.json`, `.txt`, and `.md` files;
- reject PDFs, OCR/image files, Office documents, archives, arbitrary binaries, executable files, symlinks, device paths, and web connector inputs;
- compute server-side file identity from normalized relative name, size, mtime, and sha256 hash;
- persist a durable batch/file authority record with redacted refs only;
- expose no raw local path or configured root path in API responses, status, summaries, errors, logs intended for the client, or rendered state;
- prove idempotent same-request replay and same-basis new-request replay;
- fail closed on stale file hash/size/mtime, path escape, duplicate conflicting relative names, unsupported extensions, empty eligible directory, oversized file, oversized batch, and non-UTF/text decoding failure;
- create no `ConnectorRun` or `ConnectorRunTarget` rows;
- create no `L3OutputPackage`, package mutation, package activation, handoff/export, provider-private, provider-public, RAG/vector, or qualitative-hybrid runtime rows; and
- keep rendered controls out of scope unless separately selected and frozen.

## Still Blocked

This freeze admits no runtime behavior by itself. PDFs, OCR, Office documents, arbitrary binaries, web connectors, arbitrary recursive ingestion, caller-supplied paths/URLs/globs, browser-supplied file bytes, local upload expansion, package construction, package payload rewrite, source `L3OutputPackage` mutation, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, provider-public delivery/use, provider-private signed URL generation/use, RAG/vector indexing, qualitative-hybrid analysis runtime, auth/security broadening, rendered controls, full mockup activation, frontend-durable authority, and hidden LLM planning remain blocked.

## Next Posture

The next exact posture after merge is `current_main_sync_source_expansion_ingestion_source_family_selection_freeze`.

After current-main sync, the next exact posture is `implement_server_configured_operator_directory_text_table_ingestion_after_source_family_selection_sync`.
