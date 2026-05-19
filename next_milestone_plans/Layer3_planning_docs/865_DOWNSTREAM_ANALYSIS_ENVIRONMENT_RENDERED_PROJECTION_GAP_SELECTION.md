# 865 - Downstream Analysis Environment Rendered Projection Gap Selection

## Status

Status: no-runtime current-main gap-selection control for `downstream_analysis_environment_rendered_projection_read_only`.

Selection doc: `865_DOWNSTREAM_ANALYSIS_ENVIRONMENT_RENDERED_PROJECTION_GAP_SELECTION.md`.

Predecessor current-main sync doc: `864_DOWNSTREAM_ANALYSIS_ENVIRONMENT_AUTHORITY_PROJECTION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before this selection: `61441742337a66f6793a5985987fec8a94d9d518`.

Selected gap: `downstream_analysis_environment_rendered_projection_read_only`.

Selected next posture: `freeze_downstream_analysis_environment_rendered_projection_read_only_before_runtime`.

Runtime behavior introduced by this selection: `false`.

Rendered behavior introduced by this selection: `false`.

Implementation-entry allowed next: false until a later freeze names exact rendered reader, DOM/state contract, browser proof, leakage policy, and no-go surfaces for the read-only downstream Analysis Environment rendered projection.

## Current-Main Evidence

Current main now contains the bounded backend authority projection:

- `backend/app/services/layer3_analysis_environment_projection.py` owns the read-only `analysis_environment_projection` projection;
- `backend/app/services/layer3_workbench.py::session_summary` exposes it through existing session summary state;
- `backend/app/api/layer3.py::Layer3SessionSummaryResponse` includes `analysis_environment_projection: dict[str, Any]`;
- the projection schema is `layer3.analysis_environment_projection.v1`;
- the authority source is `read_only_session_summary_projection`.

Current main also contains a separate rendered Sublayer 3C surface in `backend/app/review_ui/static/layer3.js`. That surface refreshes `State.sessionSummary`, builds rendered 3C plane state through `currentSublayerVisualizationModel()`, and renders `Analysis Execution Environments / Planes` through `renderAnalysisPlane()`.

The current rendered surface does not use `analysis_environment_projection` as a named reader. That is enough current-main evidence to select a rendered read-only projection gap, but not enough to implement rendered behavior in this pass.

## Canonical Source Of Truth

The canonical source of truth for any future rendered projection is the server response field `State.sessionSummary.analysis_environment_projection`.

The future rendered reader may also compare against existing `State.sessionSummary.sublayer_visualization` and the existing rendered 3C model to prevent UI-only drift, but browser state, localStorage, DOM labels, CSS state, mockup copy, and operator-provided values are not durable authority.

The future rendered reader must treat missing, invalid, or blocked `analysis_environment_projection` as a fail-closed read-only status. It must not seed, generate, mutate, or backfill backend artifacts.

## Selected Gap Boundary

The selected gap is the missing explicit rendered relationship between the server-owned `analysis_environment_projection` contract and the existing `/review/layer3` Sublayer 3C Analysis Execution Environments surface.

A later freeze must decide the exact read-only UI shape, but the first eligible surface is limited to the existing `/review/layer3` path in `backend/app/review_ui/static/layer3.js`, specifically the `State.sessionSummary` refresh path, `currentSublayerVisualizationModel()`, `renderAnalysisPlane()`, and the Sublayer 3C lane container.

The later freeze must keep the rendered change read-only and response-derived. It may expose projection state, plane readiness, package/export/delivery readiness, blocked reasons, and forbidden-runtime authority from the server projection. It must not add new submit controls, new routes, new request fields, or browser-only authority.

## Non-Admission Boundary

This selection admits no runtime behavior and no rendered behavior.

Still blocked:

- implementation before a rendered projection freeze is current-main selected, review-cleared, and checker-backed;
- new route family, write route, request schema, DTO write field, model, migration, or service behavior changes;
- frontend-only durable authority, localStorage authority, or browser-generated projection authority;
- package mutation, package reconstruction, payload rewrite, handoff/export rerun, external export/download rerun, delivery rerun, or local outbox write;
- source authority promotion, caller-provided paths, caller-provided URLs, globs, file bytes, recursive flags, browser uploads, web connectors, or database connectors;
- connector dispatch, destination writes, `ConnectorRun`, or `ConnectorRunTarget`;
- provider-private or provider-public URL behavior, raw URL exposure, raw token exposure, credentials, network egress, or provider/object-store behavior;
- semantic/vector RAG widening, embedding generation, persistent vector-store behavior, TabPFN runtime, NRC RAG runtime, prompt/model/provider qualitative generation, or broad qualitative/hybrid/RAG runtime;
- optional-tool Gate C/pass-entry admission;
- broad auth/security behavior;
- treating rendered copy, DOM state, CSS classes, browser storage, or operator-entered text as Analysis Environment projection authority.

## Required Future Freeze

Before any rendered implementation, the next freeze must name:

- exact rendered read-only surface and target DOM/JS functions;
- exact server fields read from `State.sessionSummary.analysis_environment_projection`;
- fallback behavior when the projection is absent, invalid, blocked, or stale;
- relationship to `State.sessionSummary.sublayer_visualization`, `currentSublayerVisualizationModel()`, and `renderAnalysisPlane()`;
- no-side-effect and leakage policy for response-safe fields only;
- headed and headless Chromium proof obligations, including desktop and mobile no-overlap/no-horizontal-overflow checks; and
- negative invariants proving no package/source/provider/connector/auth/security/runtime widening.

## Next Posture

The next exact posture is `freeze_downstream_analysis_environment_rendered_projection_read_only_before_runtime`.

Do not implement rendered Analysis Environment projection behavior until that freeze is current-main selected, review-cleared, and checker-backed.
