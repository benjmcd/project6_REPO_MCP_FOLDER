# 858 - Recursive Source Ingestion Runtime Proof

## Status

Status: runtime implementation proof for `recursive_server_configured_directory_text_table_policy_v1`.

Doc: `858_RECURSIVE_SOURCE_INGESTION_RUNTIME_PROOF.md`.

Implementation branch: `codex/l3-recursive-source-ingestion-runtime`.

Current-main entry authority: `857_RECURSIVE_SOURCE_INGESTION_RUNTIME_POLICY_SELECTION_CURRENT_MAIN_SYNC.md`.

Implemented action: `implement_recursive_server_configured_operator_directory_text_table_ingestion`.

Runtime behavior introduced by this pass: `true`, limited to recursive enumeration under server-configured `LAYER3_SOURCE_INGESTION_DIR`.

## Implemented Runtime Boundary

The existing server-configured source-directory scan route now uses `recursive_server_configured_directory_text_table_policy_v1`:

- route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- status route: `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`;
- source root authority: `LAYER3_SOURCE_INGESTION_DIR`;
- allowed extensions: `.csv`, `.json`, `.txt`, and `.md`;
- maximum recursion depth: `2`;
- maximum normalized relative path segments: `3`, including filename;
- maximum file count: `100`;
- maximum per-file bytes: `MAX_UPLOAD_MB * 1024 * 1024`;
- maximum aggregate bytes: `MAX_UPLOAD_MB * 1024 * 1024 * 100`;
- ordering: deterministic lexical normalized relative path order;
- caller-selected recursive flag allowed: `false`; and
- path exposure: normalized relative paths only.

The implementation reuses `L3SourceDirectoryIngestionBatch`, `L3SourceDirectoryIngestionFile`, and schema family `layer3.source_directory_ingestion_batch.v1`.

## Proof Summary

Focused runtime proof passes for:

- recursive happy path recording normalized relative paths for direct, one-level, and two-level `.csv`, `.json`, `.txt`, and `.md` files;
- same request id and same authority basis replaying to the same batch/status;
- same authority basis with a new request id returning existing batch/status;
- same request id with changed basis failing closed through existing idempotency conflict behavior;
- traversal beyond selected depth failing closed;
- hidden path segment failing closed;
- nested unsupported extension failing closed;
- nested symlink/reparse entry failing closed when the environment can create a symlink;
- caller-supplied local path and recursive flag rejected by the request schema;
- configured root and raw local nested paths redacted from scan, status, material-preview, and text-index responses;
- nested source-directory material preview reaching Gate B through existing source-directory material authority;
- nested source-directory deterministic text indexing;
- live-file drift and stale material/text-index authority still failing closed; and
- no `ConnectorRun`, `ConnectorRunTarget`, or `L3OutputPackage` rows from recursive scan/material/text-index proof.

Observed command:

```powershell
python -m pytest .\backend\tests\test_layer3_source_directory_ingestion.py -q
```

Observed result: `15 passed, 1 skipped`. The skipped case is the symlink creation branch when the local environment does not permit creating a symlink; the code path remains covered when symlink creation is available.

## Non-Admission Boundary

This runtime pass admits recursive source-directory scan/status and existing downstream source-directory material preview/text indexing over recorded recursive file authority only.

Still not admitted:

- caller-provided paths, URLs, globs, file bytes, or recursive flags;
- rendered control changes;
- source authority promotion;
- package/handoff/export/download behavior changes;
- connector dispatch;
- provider-private or provider-public URL behavior;
- credentials or network behavior;
- semantic/vector RAG widening beyond current deterministic local source-directory surfaces;
- prompt/model/provider qualitative generation;
- TabPFN runtime;
- NRC RAG runtime;
- optional-tool Gate C/pass-entry admission;
- broad auth/security behavior;
- PDFs, OCR, Office documents, images, archives, or arbitrary binaries;
- browser uploads;
- web connectors; and
- database connectors.

## Next Posture

The next exact posture after this implementation proof is current-main sync for `recursive_server_configured_directory_text_table_policy_v1`.

After sync, select the next highest-value deferred platform lane from current-main evidence rather than continuing recursive source-ingestion polish unless a concrete defect, failed check, stale sync, review item, or operator-flow blocker is named.
