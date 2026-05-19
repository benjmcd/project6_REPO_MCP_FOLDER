# 866 - Downstream Analysis Environment Rendered Projection Freeze

## Status

Status: no-runtime implementation-entry freeze for `downstream_analysis_environment_rendered_projection_read_only`.

Freeze doc: `866_DOWNSTREAM_ANALYSIS_ENVIRONMENT_RENDERED_PROJECTION_FREEZE.md`.

Predecessor gap-selection doc: `865_DOWNSTREAM_ANALYSIS_ENVIRONMENT_RENDERED_PROJECTION_GAP_SELECTION.md`.

Current-main checkpoint before this freeze: `9f68fe8b56f6d268cc0dbb2cce167b596c5ee4ca`.

Selected implementation action: `implement_downstream_analysis_environment_rendered_projection_read_only_panel`.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Implementation-entry allowed next: true only after current-main sync for this freeze, and only for the read-only rendered projection named here.

## Canonical Source Of Truth

The canonical source of truth for the rendered downstream Analysis Environment projection is `State.sessionSummary.analysis_environment_projection`, which is populated by the existing `GET /api/v1/layer3/session/{session_id}` session-summary response.

The server authority remains:

- owner service: `backend/app/services/layer3_analysis_environment_projection.py`;
- response field: `analysis_environment_projection: dict[str, Any]`;
- schema id: `layer3.analysis_environment_projection.v1`;
- authority source: `read_only_session_summary_projection`;
- projection mode: `read_only_session_summary_projection`;
- no-side-effect marker: `no_side_effects: True`.

The rendered implementation may compare this server projection with `State.sessionSummary.sublayer_visualization` and the existing Sublayer 3C rendered model, but it must not treat browser state, localStorage, DOM labels, CSS state, operator notes, or mockup copy as authority.

## Exact Rendered Surface

The only admitted rendered surface for the later implementation is the existing `/review/layer3` page in `backend/app/review_ui/static/layer3.js`.

The future implementation is limited to this path:

- `State.sessionSummary` as the response holder;
- a read-only helper, tentatively `currentAnalysisEnvironmentProjection()`, that returns only `State.sessionSummary.analysis_environment_projection` when it is an object;
- `currentSublayerVisualizationModel()` to attach a response-derived read-only projection summary to the existing Sublayer 3C model;
- `renderSublayerMap()` and `renderAnalysisPlane()` to render projection state inside the existing Sublayer 3C Analysis Execution Environments lane;
- the existing `.analysis-plane` / `.analysis-planes` DOM region, without adding a new submit form or new operation step.

The rendered reader may display only response-safe fields from `analysis_environment_projection`: `projection_state`, `available_for_downstream_analysis`, `blocked_reasons`, `plane_readiness`, `package_authority`, `downstream_unavailable`, `forbidden_runtime_authority`, `schema_id`, and `authority_source`.

## Fail-Closed And Stale-State Policy

If `State.sessionSummary.analysis_environment_projection` is absent, not an object, has a schema id other than `layer3.analysis_environment_projection.v1`, lacks `no_side_effects: True`, or reports blocked state, the UI must render a read-only blocked/unknown projection status.

The future rendered implementation must not seed a session summary, generate projection fields, infer package/export readiness from DOM state, or backfill from localStorage.

The rendered implementation must preserve the current refresh authority: `refreshSessionSummary()` remains the way current session summary state is reloaded, and it must continue to call the existing session endpoint only.

## Non-Admission Boundary

This freeze admits no runtime behavior and no rendered behavior now.

Still blocked:

- implementation before current-main sync for this freeze;
- new route family, write route, request schema, DTO write field, model, migration, or backend service behavior change;
- new submit control, write button, operation dock step, delivery trigger, connector dispatch trigger, or provider URL control;
- frontend-only durable authority, localStorage authority, browser-generated projection authority, DOM-derived readiness authority, or mockup-copy authority;
- package mutation, package reconstruction, payload rewrite, handoff/export rerun, external export/download rerun, delivery rerun, or local outbox write;
- source authority promotion, caller-provided paths, caller-provided URLs, globs, file bytes, recursive flags, browser uploads, web connectors, or database connectors;
- connector dispatch, destination writes, `ConnectorRun`, or `ConnectorRunTarget`;
- provider-private or provider-public URL behavior, raw URL exposure, raw token exposure, credentials, network egress, or provider/object-store behavior;
- semantic/vector RAG widening, embedding generation, persistent vector-store behavior, TabPFN runtime, NRC RAG runtime, prompt/model/provider qualitative generation, or broad qualitative/hybrid/RAG runtime;
- optional-tool Gate C/pass-entry admission;
- broad auth/security behavior.

## Proof Obligations

The later implementation proof must include:

- `node --check .\backend\app\review_ui\static\layer3.js`;
- targeted static/page tests proving the rendered reader is bounded in `backend/tests/test_layer3_page.py`;
- proof that no backend route/API/model/migration/service file changed unless a current-main blocker is separately proven;
- proof that no new submit control, endpoint call, request field, package mutation, source promotion, connector dispatch, provider URL, credential, network, vector/RAG, optional-tool, or auth/security behavior was added;
- headed Chromium proof for the affected `/review/layer3` Sublayer 3C surface;
- headless Chromium proof for the same surface;
- desktop and mobile no-overlap/no-horizontal-overflow checks for the affected `.analysis-plane` / `.analysis-planes` region;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- pending/checkpoint fixture validation.

## Next Posture

The next exact posture is `current_main_sync_downstream_analysis_environment_rendered_projection_freeze_then_implementation`.

After that sync, the only admitted implementation action is `implement_downstream_analysis_environment_rendered_projection_read_only_panel`.
