# 861 - Downstream Analysis Environment Authority Projection Freeze

## Status

Status: no-runtime implementation-entry freeze for `downstream_analysis_environment_authority_projection`.

Freeze doc: `861_DOWNSTREAM_ANALYSIS_ENVIRONMENT_AUTHORITY_PROJECTION_FREEZE.md`.

Predecessor gap-selection doc: `860_DOWNSTREAM_ANALYSIS_ENVIRONMENT_AUTHORITY_GAP_SELECTION.md`.

Selected implementation action: `implement_downstream_analysis_environment_authority_projection_read_only_session_summary`.

Runtime behavior introduced by this freeze: `false`.

Implementation-entry allowed next: true only after current-main sync for this freeze, and only for the read-only projection named here.

## Canonical Source Of Truth

The canonical source of truth for the downstream Analysis Environment projection is existing server-owned Layer 3 session state, surfaced through `backend/app/services/layer3_workbench.py::session_summary`.

The projection must derive only from existing server-owned summary fields:

- `sublayer_visualization`, currently owned by `backend/app/services/layer3_sublayer_state.py::session_sublayer_visualization_state`;
- `package_review_preview`, `package_construction`, `package_review_submit`, `handoff_export_prepare`, `aps_handoff_dispatch`, `external_export_download`, `server_owned_local_outbox_write`, `local_outbox_provider_private_handoff`, and `external_local_export`;
- `current_gate`, `downstream_unavailable`, and `authority_rail`.

Browser state, localStorage, rendered DOM labels, mockup copy, operator-supplied paths, and frontend-only durable state are not authority.

## Owner Service And API Contract

The implementation owner service is `backend/app/services/layer3_analysis_environment_projection.py`.

The first API surface is the existing session-summary route:

- `GET /api/v1/layer3/session/{session_id}`;
- response model owner: `backend/app/api/layer3.py::Layer3SessionSummaryResponse`;
- new response field: `analysis_environment_projection: dict[str, Any]`;
- schema id: `layer3.analysis_environment_projection.v1`;
- authority source: `read_only_session_summary_projection`;
- no write endpoint, no new route family, no model, and no migration in the first implementation.

`backend/app/services/layer3_workbench.py::session_summary` may call the new owner service after the existing source, plan, execution, package, handoff, export, delivery, and `sublayer_visualization` summaries have been assembled.

## Relationship To Sublayer Visualization

`session_sublayer_visualization_state` remains the owner for the structural 3A/3B/3C material, typing, analysis-set, pass-run, and latest-plan projection. The new Analysis Environment projection may read that state, but it must not replace it, mutate it, or change its schema.

The Analysis Environment projection must explain the downstream readiness of the rendered 3C planes. It may classify planes as structural, input-ready, planned, active, output-ready, package-ready, delivery-ready, or blocked by existing `downstream_unavailable` state. It must preserve `no_side_effects: True`.

## Relationship To Source-Directory Qualitative And Hybrid Status

The first implementation must treat source-directory qualitative/hybrid analysis status as an existing server-owned downstream chain, not a new analysis runtime. It may report whether existing session-summary package, handoff/export, external export/download, and external local export state makes downstream consumption inspectable.

It must not start qualitative execution, rerun package construction, prepare or deliver exports, write local outbox files, dispatch connectors, generate embeddings, call providers, or promote source authority.

## Rendered Surface

No rendered control is admitted by this freeze.

If a later implementation changes rendered behavior, the only admitted rendered reader is the existing `/review/layer3` Sublayer 3C surface in `backend/app/review_ui/static/layer3.js`, specifically the `State.sessionSummary`-backed `currentSublayerVisualizationModel()` and `renderAnalysisPlane()` path under the `#mockup-execution-lanes` / Sublayer 3C Analysis Execution Environments surface.

Rendered behavior must remain read-only. Browser storage cannot become projection authority.

## Idempotency, Stale Authority, Side Effects, And Leakage

The projection must be deterministic for the same persisted session-summary inputs.

Missing, stale, or partial upstream state must fail closed into an explicit blocked/read-only projection state. Empty runtime must not seed, generate, or backfill artifacts.

No side effects are admitted:

- no `AnalysisRun`, `L3PassRun`, `L3OutputPackage`, `L3ReconciliationRecord`, `ConnectorRun`, or `ConnectorRunTarget` row creation;
- no package mutation, package reconstruction, handoff/export rerun, external export/download rerun, or delivery rerun;
- no file writes, provider calls, credentials, network egress, vector store writes, model calls, or browser storage authority.

The response must expose only redacted refs and response-safe status fields already present in session summary. It must not expose raw filesystem paths, raw provider/public URLs, raw tokens, credentials, package payload bytes, source file bytes, or connector destination secrets.

## Proof Obligations

The implementation proof must include:

- owner-service tests for deterministic projection, missing upstream state, blocked downstream state, package/export/delivery readiness, no mutation of input summaries, and no forbidden row/file side effects;
- API proof that `GET /api/v1/layer3/session/{session_id}` includes `analysis_environment_projection` without changing existing `sublayer_visualization` semantics;
- negative proof for caller-supplied path, URL, package ref, source ref, provider, connector, credential, vector, model, and auth/security sentinels if any request surface is touched;
- `python -m py_compile` for the new service, API, workbench, and checker files touched;
- targeted pytest for the owner service and session-summary response;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- pending/checkpoint fixture validation.

If rendered code changes, proof must additionally include `node --check .\backend\app\review_ui\static\layer3.js`, headed Chromium proof, headless Chromium proof, and desktop/mobile no-overlap/no-horizontal-overflow checks for the affected Sublayer 3C surface.

## Non-Admission Boundary

Still blocked:

- runtime behavior before current-main sync and implementation;
- new write routes or a new route family;
- model or migration changes;
- package mutation, package reconstruction, or payload rewrite;
- handoff/export rerun, external export/download rerun, delivery rerun, or local outbox write;
- source authority promotion, caller-provided paths, caller-provided URLs, globs, file bytes, recursive flags, browser uploads, web connectors, or database connectors;
- connector dispatch, destination writes, `ConnectorRun`, or `ConnectorRunTarget`;
- provider-private or provider-public URL behavior;
- credentials, network egress, provider/object-store behavior, raw public URL exposure, or raw token exposure;
- semantic/vector RAG widening, embedding generation, persistent vector-store behavior, TabPFN runtime, NRC RAG runtime, prompt/model/provider qualitative generation, or broad qualitative/hybrid/RAG runtime;
- optional-tool Gate C/pass-entry admission;
- broad auth/security behavior;
- frontend-only durable authority, localStorage authority, or browser-only persistence.

## Next Posture

The next exact posture is `current_main_sync_downstream_analysis_environment_authority_projection_freeze_then_implementation`.

After that sync, the only admitted implementation action is `implement_downstream_analysis_environment_authority_projection_read_only_session_summary`.
