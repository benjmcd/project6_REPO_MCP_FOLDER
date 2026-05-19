# 854 - Recursive Source Ingestion Family Selection Freeze

## Status

Status: no-runtime source-family selection freeze for `recursive_server_configured_operator_directory_text_table_source_family`.

Doc: `854_RECURSIVE_SOURCE_INGESTION_FAMILY_SELECTION_FREEZE.md`.

Current-main preflight checkpoint: `19a1482dc2a8bc18b8e34f015922f8f50c8a5c66`.

Predecessor current-main sync doc: `853_INTERNAL_WEBHOOK_CONNECTOR_RUNTIME_CURRENT_MAIN_SYNC.md`.

Selected deferred lane: `broader_source_ingestion_family_selection`.

Selected source family: `recursive_server_configured_operator_directory_text_table_source_family`.

Selected source-family class: `recursive_server_configured_local_directory_text_table_ingestion`.

Runtime behavior introduced by this freeze: `false`.

Implementation-entry allowed next: false until a later runtime-entry freeze selects exact traversal limits, exclusion policy, stale-authority behavior, and proof scope.

## Current-Main Baseline

Current main already includes bounded direct-child server-configured operator directory ingestion for `.csv`, `.json`, `.txt`, and `.md` files under `LAYER3_SOURCE_INGESTION_DIR`.

The current implementation owner remains:

- `backend/app/services/layer3_source_directory_ingestion.py`.

The current API surfaces remain:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`.

Current main intentionally reports `direct_child_only: True` and `recursive_traversal_admitted: False`. That behavior remains unchanged by this freeze.

## Selected Family

The selected future family is server-configured recursive local directory text/table ingestion over the same file family already admitted for direct-child source-directory ingestion:

- `.csv`;
- `.json`;
- `.txt`; and
- `.md`.

The source root must remain server/operator configured. The future implementation must not accept caller-supplied paths, URLs, glob patterns, recursive flags, browser file bytes, connector selectors, credentials, source package refs, provider URLs, or arbitrary destination references.

The future family may enumerate eligible files below the configured root only after a later runtime-entry freeze selects exact traversal limits and fail-closed policy.

## Runtime Policy Still Required

A later implementation-entry freeze is required before runtime. That freeze must select:

- maximum recursion depth;
- relative path normalization and redaction contract;
- hidden file and hidden directory policy;
- symlink, junction, device path, and path escape rejection policy;
- duplicate relative name and case-fold conflict handling;
- maximum file count, per-file bytes, and aggregate bytes;
- stale file identity behavior across nested files;
- directory fingerprint basis for nested relative paths;
- empty root and empty eligible subtree behavior;
- archive, generated-output, and app-owned storage exclusion policy;
- status/readiness projection shape;
- downstream material authority compatibility;
- proof plan for idempotency, stale authority, wrong root, nested path redaction, and no forbidden adjacent behavior.

## Non-Admission Boundary

This freeze admits no runtime behavior, no recursive traversal in the live API, no request-schema change, no rendered control change, no source authority promotion, no package/handoff/export/download integration, no connector dispatch, no provider-private or provider-public URL behavior, no credential or network behavior, no semantic/vector RAG widening, no prompt/model/provider qualitative generation, no TabPFN runtime, no NRC RAG runtime, no optional-tool Gate C/pass-entry admission, and no broad auth/security behavior.

PDFs, OCR, Office documents, images, archives, arbitrary binaries, browser upload expansion, web connectors, database connectors, arbitrary caller-provided paths, and local upload behavior remain blocked unless a later current-main freeze selects that exact source family.

## Stop Conditions

Stop before implementation if the next pass:

- changes `backend/app/services/layer3_source_directory_ingestion.py` to traverse recursively without a separate runtime-entry freeze;
- adds a `recursive` request field or any caller-selected traversal flag;
- accepts caller-supplied paths, URLs, globs, file bytes, connector selectors, or credentials;
- admits PDFs, OCR, Office documents, images, archives, arbitrary binaries, web connectors, database connectors, or browser uploads;
- exposes raw configured root paths or raw local nested paths;
- mutates package, handoff, export, connector, provider URL, vector/RAG, optional-tool, or auth/security behavior; or
- cannot prove fail-closed traversal, redaction, idempotency, and stale-authority behavior in isolated runtime state.

## Next Posture

The next exact posture after this freeze is current-main sync for `recursive_server_configured_operator_directory_text_table_source_family`.

After current-main sync, the next exact posture is `select_recursive_source_ingestion_runtime_policy_before_implementation`.
