# Layer 3 Source Breadth Freeze

Status: current-main source-breadth implementation-entry freeze for the first later raw-ingestion/source-authority materialization pass after the bounded qualitative APS downstream UI runtime.

This artifact is planning/control only. It does not add a route, DTO, model, migration, service implementation, UI control, source adapter registry, source ingestion path, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, package mutation, connector/destination dispatch, provider/public URL, full mockup activation, hidden LLM planning, or auth/security behavior.

## Decision

The selected source-breadth mode is exactly:

- selected_source_breadth_mode: `current_admitted_classes_with_server_owned_raw_materialization_only`

Current runtime-admitted source classes remain exactly:

- `dataset_version`
- `aps_content_document`

The next eligible raw-ingestion/source-authority implementation may only target those existing authority families. It must use server-owned storage-root inputs, deterministic hashes, and explicit owner-service/DB authority checks. It must remain separate from normal Layer 3 flow execution.

No new source class is admitted by this freeze.

## Deferred Source Families

The following source families remain unsupported until a later, separate freeze chooses one exact family and its authority contract:

- `rag_vector_index`
- `arbitrary_local_directory`
- `broad_file_upload`
- `web_connector`
- `unbounded_runtime_db`
- generic source adapter registry expansion
- arbitrary operator-provided local file path input
- browser/frontend-only source authority

Any later pass that touches one of these families must define request fields, storage boundary, owner service, DB rows read/written, artifact rows/files read/written, idempotency, concurrency behavior, negative invariants, and source-boundary tests before implementation.

## Implementation-Entry Boundary

A later implementation branch may be considered only if it keeps all of the following true:

- admitted source classes remain `dataset_version` and `aps_content_document` unless a later source-family freeze says otherwise;
- source seeding/ingestion remains separate from Layer 3 preflight, source preview, material preview, Gate B, Gate C, plan, execution, package, handoff, and export flow execution;
- request input cannot point to arbitrary local paths;
- all source files or manifests are under a server-owned storage root and are SHA-256 checked;
- source authority rows are created or selected through explicit owner-service rules, not broad DB reflection;
- no RAG/vector retrieval or index creation occurs;
- no web connector fetch occurs;
- no connector/destination dispatch occurs;
- no provider/public URL or signed URL is generated;
- no rendered UI control is added unless a separate UI/theme freeze admits it;
- no model or migration work occurs unless the implementation-entry freeze for that exact pass names the schema change.

## Required Future Tests

The first implementation pass after this freeze must include tests for:

- storage-root confinement and path traversal rejection;
- missing manifest/file and bad hash fail-closed behavior;
- unsupported source family fail-closed behavior;
- forbidden/deferred request-field rejection;
- no Layer 3 flow state created by source materialization alone;
- DB row counts and artifact/file counts after success and failure;
- deterministic IDs/content/hash behavior where possible;
- normal bounded Layer 3 API flow consumption only after preflight/source/material/Gate B/Gate C steps;
- negative invariants for local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, provider/public URL generation, connector/destination dispatch, package mutation, hidden LLM planning, full mockup activation, and auth/security behavior.

If rendered controls are touched later, the UI proof must cover stable selectors, server-authoritative state, no frontend-only durable authority, and relevant UI themes in both headless and headed Chromium.

## Relationship To Existing Docs

- `123_SOURCE_EXPANSION_FREEZE.md` remains the current supported-source-only runtime boundary.
- `137_RAW_MIXED_BRIDGE_FREEZE.md` remains the seed-only bridge contract over existing source authority rows.
- `142_POST_709_ROADMAP_FREEZE.md` orders this source-breadth freeze before raw ingestion/source-adapter expansion.
- This document freezes the next source-breadth posture without making raw ingestion live.

## Acceptance Criteria

This source-breadth freeze is accepted only when:

- this file exists and names `selected_source_breadth_mode: current_admitted_classes_with_server_owned_raw_materialization_only`;
- progress/proof references identify this as planning/control only;
- `tools/l3-progress-check.py` requires this file and the current-main references;
- the current source-boundary runtime still reports only `dataset_version` and `aps_content_document`;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` passes.
