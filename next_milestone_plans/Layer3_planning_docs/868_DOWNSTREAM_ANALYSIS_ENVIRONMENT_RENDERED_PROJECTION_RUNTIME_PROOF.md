# 868 - Downstream Analysis Environment Rendered Projection Runtime Proof

## Status

Status: branch-local rendered implementation proof for `implement_downstream_analysis_environment_rendered_projection_read_only_panel`.

Runtime proof doc: `868_DOWNSTREAM_ANALYSIS_ENVIRONMENT_RENDERED_PROJECTION_RUNTIME_PROOF.md`.

Predecessor current-main sync doc: `867_DOWNSTREAM_ANALYSIS_ENVIRONMENT_RENDERED_PROJECTION_FREEZE_CURRENT_MAIN_SYNC.md`.

Runtime branch: `codex/l3-analysis-environment-rendered-runtime`.

Current-main checkpoint before implementation: `16b3f79f3e0f3c9fe7aceefbce622342af5591b2`.

Rendered behavior introduced by this pass: `true`, limited to a read-only `/review/layer3` Sublayer 3C server projection panel.

Backend runtime behavior introduced by this pass: `false`.

## Implemented Surface

The rendered implementation stays inside:

- `backend/app/review_ui/static/layer3.js`;
- `backend/app/review_ui/static/layer3.css`;
- `backend/tests/test_layer3_page.py`.

The canonical source of truth is still `State.sessionSummary.analysis_environment_projection`, backed by the existing session-summary response field `analysis_environment_projection: dict[str, Any]`, schema `layer3.analysis_environment_projection.v1`, and authority source `read_only_session_summary_projection`.

The rendered reader adds:

- `currentAnalysisEnvironmentProjection()`;
- `analysisEnvironmentProjectionStatus()`;
- `analysisEnvironmentPlaneReadiness()`;
- `renderAnalysisEnvironmentProjectionStatus()`.

The rendered panel is inserted only through existing Sublayer 3C Analysis Environment planes in `currentSublayerVisualizationModel()` and `renderAnalysisPlane()`.

## Fail-Closed Behavior

The reader fails closed when the server projection is missing, malformed, or not explicitly read-only:

- `analysis_environment_projection_missing`;
- `analysis_environment_projection_schema_invalid`;
- `analysis_environment_projection_not_read_only`.

The empty local runtime state renders all three Analysis Environment planes as `blocked` with `data-projection-available="false"`, `data-schema-valid="false"`, and `data-read-only="false"`.

## Browser Proof

Headed in-app Chromium proof passed for `http://127.0.0.1:8012/review/layer3`:

- title: `Layer 3 Workbench`;
- `.analysis-environment-projection` count: `3`;
- all three panels rendered `state="blocked"`;
- all three panels rendered blocked reason `analysis_environment_projection_missing`;
- console logs: `[]`;
- framework/error overlay count: `0`;
- horizontal overflow: `false`.

Headless Chromium desktop proof passed at `1365x900`:

- `.analysis-environment-projection` count: `3`;
- all three panels rendered `state="blocked"`;
- all three panels rendered blocked reason `analysis_environment_projection_missing`;
- console/page errors: `[]`;
- framework/error overlay count: `0`;
- horizontal overflow: `false`.

Headless Chromium mobile proof passed at `390x844`:

- `.analysis-environment-projection` count: `3`;
- first projection panel grid columns: `206px`;
- console/page errors: `[]`;
- framework/error overlay count: `0`;
- horizontal overflow: `false`.

## Static Validation

Validation passed:

- `node --check .\backend\app\review_ui\static\layer3.js`;
- `python -m pytest .\backend\tests\test_layer3_page.py -q -k "static_assets_are_mounted or analysis_environment_projection_rendered_reader_is_bounded"` with `2 passed, 4 deselected`.

## Non-Admission Boundary

Still blocked:

- backend route/API/DTO/model/migration/service behavior changes;
- new submit controls, write buttons, operation dock steps, delivery triggers, connector dispatch triggers, provider URL controls, or new request fields;
- frontend-only durable authority, localStorage authority, browser-generated projection authority, DOM-derived readiness authority, or mockup-copy authority;
- package mutation, package reconstruction, payload rewrite, handoff/export rerun, external export/download rerun, delivery rerun, or local outbox write;
- source authority promotion, caller-provided paths, caller-provided URLs, globs, file bytes, recursive flags, browser uploads, web connectors, or database connectors;
- connector dispatch, destination writes, `ConnectorRun`, or `ConnectorRunTarget`;
- provider-private or provider-public URL behavior, raw URL exposure, raw token exposure, credentials, network egress, or provider/object-store behavior;
- semantic/vector RAG widening, embedding generation, persistent vector-store behavior, TabPFN runtime, NRC RAG runtime, prompt/model/provider qualitative generation, or broad qualitative/hybrid/RAG runtime;
- optional-tool Gate C/pass-entry admission;
- broad auth/security behavior.

## Next Posture

After merge, the next exact posture is `current_main_sync_downstream_analysis_environment_rendered_projection_read_only_panel_runtime`.
