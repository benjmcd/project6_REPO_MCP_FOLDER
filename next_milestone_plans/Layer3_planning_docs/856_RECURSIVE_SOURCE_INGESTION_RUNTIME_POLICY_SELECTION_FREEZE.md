# 856 - Recursive Source Ingestion Runtime Policy Selection Freeze

## Status

Status: no-runtime runtime-policy selection freeze for `recursive_server_configured_operator_directory_text_table_ingestion`.

Doc: `856_RECURSIVE_SOURCE_INGESTION_RUNTIME_POLICY_SELECTION_FREEZE.md`.

Current-main preflight checkpoint: `8c943a273ac96dcec3b11bbb0f5277147a71ff8e`.

Predecessor current-main sync doc: `855_RECURSIVE_SOURCE_INGESTION_FAMILY_SELECTION_FREEZE_CURRENT_MAIN_SYNC.md`.

Selected implementation action: `implement_recursive_server_configured_operator_directory_text_table_ingestion`.

Runtime behavior introduced by this freeze: `false`.

Implementation-entry allowed next: true, after current-main sync, for only the exact recursive source-ingestion runtime policy selected here.

## Selected Runtime Policy

Runtime policy id: `recursive_server_configured_directory_text_table_policy_v1`.

Selected source family: `recursive_server_configured_operator_directory_text_table_source_family`.

Selected source-family class: `recursive_server_configured_local_directory_text_table_ingestion`.

Selected source root authority: `LAYER3_SOURCE_INGESTION_DIR`.

Allowed file extensions remain:

- `.csv`;
- `.json`;
- `.txt`; and
- `.md`.

No new source families are selected. PDFs, OCR, Office documents, images, archives, arbitrary binaries, browser uploads, web connectors, database connectors, and caller-provided paths remain blocked.

## Traversal Limits

The implementation may enumerate eligible files below the server-configured root with these exact limits:

- maximum recursion depth: `2` directory levels below the configured root;
- maximum normalized relative path segments: `3`, including the filename;
- maximum file count: `100`;
- maximum per-file bytes: `MAX_UPLOAD_MB * 1024 * 1024`;
- maximum aggregate bytes: `MAX_UPLOAD_MB * 1024 * 1024 * 100`;
- traversal order: deterministic lexical order over normalized relative paths;
- directory traversal mode: depth-first or breadth-first is allowed only if the persisted and response ordering is normalized lexical order; and
- recursive traversal must be server-owned and must not be caller selected.

The implementation must not add a `recursive` request field or any caller-controlled traversal flag.

## Path And Redaction Contract

The implementation must normalize each admitted file to a server-relative path below `LAYER3_SOURCE_INGESTION_DIR`.

Normalized relative paths must:

- use `/` separators in API responses, stored identity, fingerprint basis, and proof output;
- contain no drive letter, root prefix, device prefix, `..` segment, empty segment, or raw configured root path;
- be case-folded only for conflict detection, not for display;
- be included in file identity and directory fingerprint hashing; and
- be exposed only as relative names, never as raw local absolute paths.

The API may expose `source_root_ref: server-configured://LAYER3_SOURCE_INGESTION_DIR`, normalized relative names, file hashes, file sizes, media types, mtime values, and durable authority ids. It must not expose the configured root path, raw local nested paths, file bytes, source content, provider URLs, connector targets, credentials, tokens, browser storage, prompts, or auth internals.

## Fail-Closed Traversal Policy

The implementation must fail closed before durable authority is written when it encounters:

- unset, relative, missing, non-directory, app-owned, local-outbox, or export-staging `LAYER3_SOURCE_INGESTION_DIR`;
- traversal beyond the selected maximum depth;
- normalized relative paths with more than `3` segments including filename;
- any path escape after resolve;
- symlink, junction, reparse-point, device path, socket, pipe, or non-regular-file entry;
- hidden file or hidden directory segment, including dot-prefixed segments and platform hidden/system entries where detectable;
- unsupported extension anywhere under the traversed policy scope;
- empty file;
- oversized file;
- oversized aggregate batch;
- more than `100` eligible files;
- duplicate normalized relative path;
- case-fold duplicate relative path;
- non-UTF-8 text;
- invalid JSON for `.json` files;
- stale file identity while hashing;
- empty configured root;
- no eligible files under the recursive policy; or
- caller-supplied path, URL, glob, file bytes, recursive flag, connector selector, provider URL, credential, source package ref, package ref, destination ref, RAG/vector input, optional-tool input, or auth/security override.

Archive files are rejected by extension and media classification; app-owned generated output, local-outbox, and export-staging paths are rejected by resolved path overlap. This policy does not select arbitrary archive-directory traversal by name.

## Durable Authority And Fingerprint

The implementation may reuse the current direct-child durable authority family:

- `L3SourceDirectoryIngestionBatch`;
- `L3SourceDirectoryIngestionFile`; and
- schema family `layer3.source_directory_ingestion_batch.v1`.

If reuse requires a schema/status marker, the implementation may add a policy field that distinguishes `recursive_server_configured_directory_text_table_policy_v1` from the current direct-child policy without changing source authority class or promoting source authority.

Directory fingerprint basis must include:

- runtime policy id;
- config authority;
- source root ref;
- allowed extensions;
- maximum recursion depth;
- normalized relative path for each admitted file;
- file size;
- mtime ns;
- content sha256; and
- file identity hash.

Same request id plus same recursive authority basis must return the same durable batch/status. Same request id plus different recursive authority basis must fail closed. Same recursive authority basis plus a new request id may return the existing durable batch/status, matching the current source-directory idempotency family.

## Status And Readiness Projection

The response and status surfaces may expose:

- schema id;
- mode;
- runtime policy id;
- source family;
- config authority;
- source root ref;
- direct child only: `false`;
- recursive traversal admitted: `true`;
- maximum recursion depth;
- allowed extensions;
- source ingestion batch id;
- request id;
- authority basis hash;
- directory fingerprint hash;
- normalized relative names;
- file identity hashes;
- file sizes;
- media types;
- created timestamp;
- readiness/status summary; and
- negative invariants.

The response and status surfaces must not expose raw configured roots, raw local nested paths, file bytes, credentials, provider URLs, connector targets, package payloads, prompt/model internals, optional-tool outputs, browser storage, or auth internals.

## Downstream Compatibility

The recursive scan may feed the existing source-directory material preview and downstream source-directory path only through the existing durable file authority contract, after the recursive batch/file authority is persisted and validated.

This freeze does not admit package construction, package mutation, handoff/export rerun, export/download behavior changes, connector dispatch, provider URL behavior, vector/RAG widening, prompt/model/provider qualitative generation, optional-tool runtime, Gate C/pass-entry optional-tool admission, rendered control changes, broad auth/security behavior, or source authority promotion.

## Required Implementation Proof

The implementation-bearing pass must prove:

1. Recursive happy path records only normalized relative path authority for `.csv`, `.json`, `.txt`, and `.md` files within the selected depth.
2. Same request id and same authority basis replays to the same batch/status.
3. Same request id and different authority basis fails closed.
4. Same authority basis and new request id returns existing batch/status unless duplicate dispatch behavior is separately frozen.
5. Traversal beyond depth `2` fails closed.
6. More than `3` normalized relative path segments including filename fails closed.
7. Symlink, junction/reparse point, device path, non-file entry, hidden path segment, unsupported extension, empty file, oversized file, oversized aggregate batch, too many files, non-UTF-8 file, invalid JSON, duplicate/case-fold duplicate relative path, path escape, and stale file identity fail closed.
8. Caller-supplied paths, URLs, globs, file bytes, recursive flags, connector selectors, provider URLs, credentials, source package refs, package refs, destination refs, RAG/vector inputs, optional-tool inputs, and auth/security overrides are rejected.
9. Responses, status, logs, and proof output redact configured roots and raw local nested paths.
10. Existing direct-child source-directory tests remain green.
11. No package/handoff/export/download, connector, provider URL, vector/RAG, prompt/model/provider, optional-tool, rendered-control, or broad auth/security behavior changes occur.

## Non-Admission Boundary

This freeze admits no runtime behavior by itself. It selects runtime policy only.

Still not admitted:

- recursive traversal before current-main sync and implementation;
- request-schema changes before implementation;
- rendered control changes;
- source authority promotion;
- PDFs, OCR, Office documents, images, archives, arbitrary binaries, browser uploads, web connectors, database connectors, caller-provided paths, caller-provided URLs, globs, or recursive flags;
- package/handoff/export/download integration changes;
- connector dispatch;
- provider-private or provider-public URL behavior;
- credentials or network behavior;
- semantic/vector RAG widening;
- prompt/model/provider qualitative generation;
- TabPFN runtime;
- NRC RAG runtime;
- optional-tool Gate C/pass-entry admission; and
- broad auth/security behavior.

## Next Posture

The next exact posture after this freeze is current-main sync for `recursive_server_configured_directory_text_table_policy_v1`.

After current-main sync, the next exact implementation posture is `implement_recursive_server_configured_operator_directory_text_table_ingestion`.
