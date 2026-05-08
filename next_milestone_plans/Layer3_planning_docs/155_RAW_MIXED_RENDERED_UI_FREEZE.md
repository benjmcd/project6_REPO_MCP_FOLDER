# Raw Mixed Rendered Manifest UI Freeze

Status: live bounded rendered `/review/layer3` raw mixed materialization workflow for `raw_mixed_server_owned_manifest_ref_ui_entry`.

This document now governs the implemented rendered UI runtime only. It does not add backend routes, DTOs, services, models, migrations, source adapters, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, provider/public URLs, connector/destination dispatch, package mutation, full mockup activation, hidden LLM planning, auth/security behavior, or theme-specific authority.

## Decision

The selected live rendered UI mode is exactly:

- selected_raw_mixed_rendered_ui_mode: `raw_mixed_server_owned_manifest_ref_ui_entry`

The live UI exposes only a human-facing `/review/layer3` entry point for the already-live `POST /api/v1/layer3/source/mixed-corpus/materialize` route. The UI collects a server-owned materialization manifest reference and hash, calls the existing materialization endpoint, refreshes source candidates, and then feeds only the returned `dataset_version` and `aps_content_document` IDs into the existing source selection, preflight, source preview, material preview, Gate B, Gate C, plan preview, and plan approval controls.

The UI must not imply that arbitrary raw ingestion is live. The operator input is a server-owned manifest reference and hash, not file bytes, a local path, a directory, a URL to fetch, a connector request, an upload, or a source adapter registry instruction.

## Current Authority

Current main already admits:

- `current_admitted_classes_with_server_owned_raw_materialization_only` from `153_SOURCE_BREADTH_FREEZE.md`;
- `raw_mixed_existing_source_materialization_entry` from `154_RAW_INGESTION_MATERIALIZATION_FREEZE.md`;
- `POST /api/v1/layer3/source/mixed-corpus/materialize`;
- a bounded API E2E proof that materialized source IDs can drive the associated-cohort path through external export/download delivery;
- a rendered Playwright smoke proving API/test setup can materialize source authority and drive existing `/review/layer3` controls through Gate C and plan approval without adding UI controls.

Current main now admits the bounded server-owned manifest-ref controls described here. It still does not admit a file picker, upload control, directory picker, web connector control, RAG/vector control, provider/public URL control, connector/destination control, or source adapter registry.

## Allowed UI Surface

The implementation governed by this freeze may touch only:

- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.css`;
- `backend/app/review_ui/static/layer3.js`;
- `backend/tests/test_layer3_page.py` or a similarly narrow rendered/static page test;
- `e2e/layer3-workbench.spec.js`;
- `e2e/layer3-helpers.js`;
- this freeze/contract pack, progress/proof manifests, and `tools/l3-progress-check.py`.

Backend service/API changes are not admitted by this freeze. If a later change needs a manifest catalog route, upload endpoint, source adapter registry, model, migration, or new backend field, stop and create a separate backend/API freeze.

## Input Boundary

The rendered request may include only fields already admitted by `Layer3RawMixedCorpusMaterializeRequest`:

- `schema_id`;
- `schema_version`;
- `client_request_id`;
- `materialization_mode`;
- `corpus_batch_id`;
- `artifact_manifest_ref`;
- `artifact_manifest_hash`;
- `requested_source_classes`;
- `operator_confirmation`.

The UI must not send deferred fields for local upload, local-directory ingestion, browser file bytes, arbitrary filesystem paths, URLs to fetch, connector credentials, connector/destination dispatch, provider/public URLs, RAG/vector instructions, package mutation, prompt/model or hidden LLM controls, full mockup activation, auth/security overrides, model/migration controls, or browser-only durable authority.

## Required UI Gating

Rendered materialization controls become enabled only when:

1. selected source classes are exactly both `dataset_version` and `aps_content_document`;
2. the materialization mode is exactly `raw_mixed_existing_source_materialization_entry`;
3. the manifest reference is treated as a server-owned storage-root ref, not as a local path;
4. a manifest SHA-256 hash is present;
5. the operator explicitly confirms server-owned manifest authority;
6. no deferred source, provider, connector, RAG/vector, package mutation, mockup, hidden LLM, auth/security, or frontend-only durable fields are present;
7. downstream source selection uses only IDs returned by the server materialization response; refreshed candidate APIs may only verify those returned IDs are visible and must not replace or expand the selected IDs;
8. normal Layer 3 flow state starts only after rendered preflight/source/material/Gate B progression.

The browser may keep in-flight request state and display response summaries. It must not repair failed materialization, synthesize missing source IDs, treat browser state as durable authority, or bypass server candidate refresh.

## Theme Posture

The rendered control implementation preserves the current `/review/layer3` theme system. Required proof includes:

- headless Chromium for the raw mixed rendered manifest path;
- headed Chromium for the same path;
- stable theme persistence across page reloads for touched controls;
- visible focus, disabled, loading, success, blocked, and error states in the current theme set;
- no text overlap, clipping, unstable resizing, or theme-specific state divergence in touched panels at the existing desktop and mobile breakpoints;
- no theme-specific request payload differences or theme-specific authority.

The implementation adds only control-scoped CSS and proves the new controls inside existing themes.

## Required Proof

The implementation PR must prove:

- API/test setup remains separate from rendered UI execution except for the human-facing manifest controls being implemented;
- rendered controls call only `POST /api/v1/layer3/source/mixed-corpus/materialize` for materialization;
- materialization response IDs are the only source IDs consumed by downstream rendered controls;
- source candidate refresh confirms those IDs before selection;
- normal rendered preflight/source/material/Gate B/Gate C/plan flow remains unchanged after source selection;
- failure cases render fail-closed status without creating Layer 3 flow state;
- no new backend route, DTO, model, migration, service behavior, or rendered source-class expansion is introduced;
- existing seed-only bridge UI smoke and materialization API-setup smoke continue to pass;
- headed and headless Chromium proof covers the raw mixed rendered manifest workflow and touched theme states.

## Explicit Non-Goals

This runtime does not admit:

- local upload, local-directory ingestion, broad file upload, or arbitrary local path input;
- web connector retrieval, connector credentials, real connector invocation, destination selection, or destination writes;
- source adapter registry behavior or new source classes;
- RAG/vector retrieval or index creation;
- provider/public URL or signed URL generation;
- package mutation, reconstruction, supersession, replacement, or payload rewrite;
- hidden LLM planning, prompt/model controls, or full mockup activation;
- auth/security behavior changes;
- no frontend-only durable authority;
- backend service/API/model/migration changes.

## Stop Conditions

Stop before any further implementation if the intended change requires:

- accepting local paths, file bytes, directories, uploads, or URLs to fetch;
- adding a manifest catalog route or storage browser route;
- adding or changing backend DTOs, services, models, or migrations;
- admitting source classes beyond `dataset_version` and `aps_content_document`;
- starting Layer 3 flow state inside materialization;
- adding provider/public URL, connector/destination, RAG/vector, package mutation, mockup, hidden LLM, or auth/security behavior;
- relying on browser-local state as durable authority;
- changing themes without headed/headless theme proof.

## Acceptance Criteria

This runtime is accepted only when:

- this file exists and names `selected_raw_mixed_rendered_ui_mode: raw_mixed_server_owned_manifest_ref_ui_entry`;
- the paired contract document exists;
- progress/proof references identify this as a bounded rendered UI runtime;
- `tools/l3-progress-check.py` requires the freeze/contract, progress/proof references, and negative UI/source/theme terms;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` passes.
