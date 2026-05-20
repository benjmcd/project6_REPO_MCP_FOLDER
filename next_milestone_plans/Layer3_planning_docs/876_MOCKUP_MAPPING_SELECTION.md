# 876 - Mockup Mapping Selection

## Status

Status: no-runtime mapping/inventory selection for `full_mockup_activation_mapping_inventory`.

Selection doc: `876_MOCKUP_MAPPING_SELECTION.md`.

Predecessor current-main sync doc: `875_INTERNAL_WEBHOOK_RENDERED_STATUS_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before this selection: `4a715e4c57206a0b3c30adbde9a27f9c94863bb9`.

Selected activation mode: `mockup_to_live_mapping_inventory_only`.

Selected first runtime slice after this inventory: `single_existing_rendered_control_extension`.

Preferred first target after this inventory: `source_directory_ingestion_scan_status_rendered_control`.

Runtime behavior introduced by this selection: `false`.

Rendered behavior introduced by this selection: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed next: `false`.

## Current-Main Authority

Current main still keeps mockups as target-state design inputs, not runtime authority:

- `backend/app/services/layer3_mockup_boundary.py` defines `MOCKUP_TRUTH_STATE_MODE = "mockups_target_state_only"`.
- `backend/app/services/layer3_mockup_boundary.py` defines `MOCKUP_AUTHORITY_ROLE = "target_state_design_specification"`.
- `next_milestone_plans/layer3-mockups/assets.md` records the operator-local mockup source inventory.
- `next_milestone_plans/layer3-mockups/mockup-spec.txt` records the target-state workflow specification and anti-assumption rules.
- `/review/layer3` is live only for server-authoritative rendered controls already proven by source, route/API contracts, and tests.

This selection does not convert mockup text, screenshots, SVG canvas state, browser state, local storage, manually clicked flows, or copied browser output into server authority.

## Mapping Inventory Decision

The first full-mockup activation pass is intentionally inventory-only. It selects the next runtime direction without changing code.

```yaml
full_mockup_activation_mapping_inventory:
  selected_mode: mockup_to_live_mapping_inventory_only
  first_runtime_mode_after_inventory: single_existing_rendered_control_extension
  preferred_first_target: source_directory_ingestion_scan_status_rendered_control
  alternate_safe_targets:
    - internal_webhook_rendered_status_panel_read_only
    - downstream_analysis_environment_projection_read_only
  deferred_modes:
    - single_mockup_screen_read_only_projection
    - single_mockup_screen_server_authoritative_activation
    - full_mockup_program_activation
  runtime_behavior_change: false
  rendered_behavior_change: false
```

## Target Ranking

| Rank | Target | Current live authority | Activation fit | Decision |
| ---: | --- | --- | --- | --- |
| 1 | Source-directory ingestion scan/status rendered control | `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`, `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`, `L3SourceDirectoryIngestionBatch`, `L3SourceDirectoryIngestionFile`, and `/review/layer3` `#source-directory-ingestion-rendered-controls` | Best fit for `single_existing_rendered_control_extension` because it already has server-configured authority, durable batch/file rows, redacted response contracts, rendered scan/status controls, and bounded page/API tests | Preferred first runtime target |
| 2 | Internal webhook rendered status panel | `internal_webhook_dispatch: dict[str, Any]`, durable `L3InternalWebhookDispatchReceipt` / `L3InternalWebhookDispatchAuditEvent`, and `/review/layer3` `#internal-webhook-dispatch-panel` | Safe read-only status projection, but not an action-capable activation target unless dispatch/rerun/destination behavior is separately reopened | Alternate read-only target |
| 3 | Downstream Analysis Environment projection | `State.sessionSummary.analysis_environment_projection` and read-only `/review/layer3` rendered panels | Safe read-only projection, useful for visibility but weaker as the first operator-control activation | Alternate read-only target |
| 4 | Single mockup screen read-only projection | Mockup target-state files plus an existing server projection would need an explicit field mapping | Viable after one exact screen is named, but weaker than extending an already-live rendered control | Deferred |
| 5 | Single mockup screen server-authoritative activation | Requires a new exact route/API/state/test contract before runtime | Higher value, higher risk; not ready until one screen and one operator journey are frozen | Deferred |
| 6 | Full mockup program activation | Would cross source expansion, package mutation, connector/destination, provider URL, qualitative/hybrid/RAG, auth/security, and browser-state surfaces | Too broad for current authority | Rejected for now |

## Preferred Target Contract

The next runtime freeze should target only `source_directory_ingestion_scan_status_rendered_control`.

Canonical source of truth:

- backend service: `backend/app/services/layer3_source_directory_ingestion.py`;
- API routes: `backend/app/api/layer3.py`;
- durable state: `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile`;
- rendered route: `/review/layer3`;
- rendered DOM: `#source-directory-ingestion-rendered-controls`;
- rendered JS owner: `sourceDirectoryIngestionRenderedControls()` in `backend/app/review_ui/static/layer3.js`;
- static page contract tests: `backend/tests/test_layer3_page.py`;
- backend/API tests: `backend/tests/test_layer3_source_directory_ingestion.py`.

The first runtime slice may extend or harden only the already-rendered server-configured scan/status control. It must not add caller-selected paths, browser file bytes, URL input, glob input, recursive flags from the caller, source upload widening, connector fetch, RAG/vector activation, package mutation, provider URL behavior, auth/security behavior, or frontend-only durable authority.

## Mockup-To-Live Mapping

| Mockup / target-state concept | Current live surface | Mapping result |
| --- | --- | --- |
| Operator source setup / chooseable source input | Source-intake upload/inventory/preview and source-directory ingestion scan/status surfaces | Live in bounded server-authoritative slices only; first activation should use server-configured source-directory scan/status, not broad source picker behavior |
| Local directory / file source intent | `LAYER3_SOURCE_INGESTION_DIR` backed scan/status, recursive server policy, redacted root refs | Partially live only as server-configured directory ingestion; caller-provided local paths remain blocked |
| Gate B material intake | Existing Gate B and material-preview chain | Live only for admitted source families and exact request contracts |
| Gate C typing / unit formation | Existing typing/readiness/session-summary surfaces | Not part of first activation target |
| Analysis execution environments | `State.sessionSummary.analysis_environment_projection` read-only rendered projection | Safe alternate read-only target, not first action target |
| Internal/external handoff and webhook visibility | Current internal webhook read-only rendered status panel | Safe alternate read-only target; dispatch controls remain blocked |
| Package / export / downstream delivery | Existing bounded package/handoff/export/download surfaces | Not part of first activation target |
| Provider URL, connector/destination, RAG/vector, hidden LLM, broad qualitative/hybrid behavior | Mixed current bounded capabilities and explicit blockers | Not eligible for first full-mockup activation pass |
| Full mockup canvas / complete target-state program | Mockup files and theme/proof artifacts | Target-state design reference only, not runtime authority |

## Required Next Freeze

Before code, the next freeze must name:

- selected implementation action: `extend_source_directory_ingestion_scan_status_rendered_control`;
- exact DOM and JS change scope under `#source-directory-ingestion-rendered-controls`;
- whether the extension is status enrichment, operator guidance, failure-state hardening, or browser proof hardening;
- exact server fields read from the existing scan/status responses;
- stale-authority and idempotency behavior for repeated `client_request_id` and status lookup;
- fail-closed behavior when `LAYER3_SOURCE_INGESTION_DIR` is unset or the batch is missing;
- negative tests proving no caller path, browser file bytes, URL, glob, recursive flag, connector, package, provider, RAG/vector, prompt/model, auth/security, or frontend durable state is admitted;
- headed Chromium proof and headless Chromium proof for `/review/layer3`;
- responsive/theme/accessibility checks for the rendered control; and
- progress-check guard terms before implementation.

## Non-Admission Boundary

This selection admits no runtime behavior, no rendered behavior, no route/API/DTO/model/migration/service behavior change, no UI control change, no test behavior change, no full mockup activation, no single mockup screen activation, no full-program scope, no frontend-only durable state, no browser-storage authority, no source expansion beyond existing server-configured authority, no caller-supplied path or file bytes, no package mutation, no connector/destination dispatch, no provider URL behavior, no RAG/vector widening, no hidden LLM planning, and no auth/security behavior.

## Validation Basis

Required validation for this selection:

- `python .\tools\l3-progress-check.py`;
- JSON validation for `next_milestone_plans/layer3_progress_manifest.json`;
- JSON validation for `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `git diff --check`.

No runtime, API, or browser test is required for this selection because it changes no runtime behavior, route, dependency, session-summary field, rendered UI, or browser behavior.

## Next Posture

The next exact posture is `freeze_source_directory_ingestion_scan_status_rendered_control_extension_before_runtime`.

Do not implement the source-directory rendered-control extension until that freeze is current-main selected, review-cleared, and checker-backed.
