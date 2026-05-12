# Layer 3 PDF Location Theme Projection

Status: current-branch rendered mockup-theme implementation proof for PDF-location projection.

```yaml
selected_runtime_mode: rendered_pdf_location_projection_from_session_summary
entry_proof: 273_PDF_LOCATION_PROJECTION.md
base_branch: main
implementation_branch: codex/l3-pdf-location-theme-projection
live_behavior_change: true
route_api_behavior_change: false
model_migration_behavior_change: false
rendered_ui_behavior_change: true
selected_theme_target: layer3_mockup_workbench_theme
server_state_source: State.sessionSummary.pdf_location_projection
no_new_backend_requests: true
```

This pass renders the already-implemented `layer3.pdf_location_projection.v1` session-summary state inside the dedicated `layer3_mockup_workbench_theme` user-flow/PDF-location board. The UI panel is `#mockup-pdf-location-projection`, and its only authority is `State.sessionSummary.pdf_location_projection` from the existing session-summary response.

The implementation deliberately does not add a new endpoint, model, migration, source adapter, connector dispatch, package mutation path, auth/security behavior, full durable mockup activation, PDF byte stream, or browser-owned authoritative PDF location. When server-authoritative projection state is unavailable, the panel stays read-only and fail-closed with an unavailable marker.

## Implemented surface

- `backend/app/review_ui/static/layer3.html` adds the rendered projection slot inside the existing mockup PDF-location card.
- `backend/app/review_ui/static/layer3.js` defensively reads `State.sessionSummary.pdf_location_projection`, renders available `location_items`, and falls back to `Read-only server projection pending` without issuing new requests.
- `backend/app/review_ui/static/layer3.css` adds bounded visual treatment for unavailable and available projection states without changing the mockup theme's backend authority.
- `backend/tests/test_layer3_page.py` adds static route/asset proof for the projection slot and renderer.
- `e2e/layer3-workbench.spec.js` verifies the projection panel is visible, remains unavailable when no session summary is loaded, keeps the mockup shell non-interactive, and does not widen backend API requests.

## Non-goals kept blocked

- no raw PDF blob streaming;
- no browser-owned authoritative PDF location;
- no new source family, local upload, local directory, or arbitrary path input;
- no RAG/vector retrieval admission;
- no connector/destination dispatch;
- no package mutation or package reconstruction;
- no auth/security widening;
- no full durable mockup activation;
- no frontend-only durable workflow authority.

## Validation scope

The required proof is static asset/page coverage, progress-manifest coverage, and headed/headless Playwright coverage of the existing mockup workbench theme test. Backend projection correctness remains covered by `273_PDF_LOCATION_PROJECTION.md` and `backend/tests/test_layer3_pdf_location.py`; this pass only renders that state in the mockup theme.
