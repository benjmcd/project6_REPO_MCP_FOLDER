# 885 - Source Directory Activation Selection

## Status

Status: no-runtime/no-rendered server-authoritative mockup-screen activation target selection after `current_main_synced_mockup_pdf_location_available_state_browser_proof`.

Selection doc: `885_SOURCE_DIRECTORY_ACTIVATION_SELECTION.md`.

Predecessor current-main sync doc: `884_MOCKUP_PDF_LOCATION_AVAILABLE_STATE_BROWSER_PROOF_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before this selection: `49cfd61a2fe4c8b958b08303e9396e566a4399d4`.

Selected activation mode: `single_mockup_screen_server_authoritative_activation_target_selection`.

Selected target: `source_directory_ingestion_scan_status_mockup_screen_activation`.

Selected future freeze: `freeze_source_directory_ingestion_scan_status_mockup_screen_activation_before_runtime`.

Runtime behavior introduced by this selection: `false`.

Rendered behavior introduced by this selection: `false`.

Backend behavior introduced by this selection: `false`.

Route/API/DTO/model/migration/service behavior introduced by this selection: `false`.

Single mockup screen server-authoritative activation introduced by this selection: `false`.

Full mockup program activation selected: `false`.

## Current-Main Authority

The selected target has the strongest current-main authority for the first server-authoritative mockup-screen activation candidate:

- scan route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- status route: `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`;
- service authority: `backend/app/services/layer3_source_directory_ingestion.py`;
- durable state: `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile`;
- rendered route: `/review/layer3`;
- rendered surface: `#source-directory-ingestion-rendered-controls`;
- rendered proof: `Layer 3 workbench renders source-directory scan and status authority fields`;
- static/API proof: `backend/tests/test_layer3_source_directory_ingestion.py`, `backend/tests/test_layer3_page.py`, and `e2e/layer3-workbench.spec.js`.

The current route contract already forbids caller paths, caller directories, browser file bytes, URL input, glob input, and caller-selected recursive flags. Current responses already expose redacted server authority fields including `runtime_policy_id`, `recursive_traversal_admitted`, `max_recursion_depth`, `max_relative_path_segments`, `caller_selected_recursive_flag_allowed`, `source_root_absolute_path_exposed`, response schema/status, and idempotency/replay state.

## Target Ranking

| Rank | Candidate | Current authority | Decision |
| ---: | --- | --- | --- |
| 1 | `source_directory_ingestion_scan_status_mockup_screen_activation` | Existing scan/status routes, durable batch/file authority, rendered source-directory control, static tests, headed proof, and headless proof | Selected as the next activation target |
| 2 | `internal_webhook_rendered_status_panel_read_only` | Existing durable dispatch receipt/audit state and read-only status panel | Safe visibility target, but already read-only and weaker for activation progress |
| 3 | `downstream_analysis_environment_projection_read_only` | Existing Analysis Environment read-only projection | Safe visibility target, but not an operator action activation |
| 4 | `mockup_sublayers_ab_gate_b_material_ledger_projection` | Existing Gate B/material authority exists, but exact mockup field mapping is not frozen here | Later read-only projection candidate |
| 5 | `mockup_sublayer3c_execution_lane_projection` | Existing execution/result/package surfaces exist, but activation would cross larger workflow scope | Deferred until a narrower contract is frozen |
| 6 | `full_mockup_program_activation` | Crosses source, package, connector, provider, RAG/vector, browser-state, and auth/security surfaces | Rejected for now |

This target is optimal because it is the only candidate that is both action-capable and already server-authoritative on current main. It moves beyond read-only mockup visibility while staying inside the existing server-configured source-directory boundary.

## Required Next Freeze

The next freeze must be `freeze_source_directory_ingestion_scan_status_mockup_screen_activation_before_runtime`.

That freeze must decide the exact single-screen activation contract before any runtime or rendered implementation:

- whether the activation reuses the existing `#source-directory-ingestion-rendered-controls` surface or adds a dedicated mockup-theme projection anchored to that server authority;
- exact operator action and request fields, limited to `client_request_id`, `operator_decision`, optional `source_family`, and optional `ingestion_mode`;
- exact stale-authority and idempotency behavior for repeated `client_request_id`;
- exact fail-closed behavior for unset `LAYER3_SOURCE_INGESTION_DIR`, missing batch, blocked scan, and blocked status lookup;
- exact browser proof for no raw local path exposure, no forbidden payload keys, no package/source-mixed/connector/provider/execution side-effect requests, no console errors, no page errors, and no horizontal overflow;
- exact headed Chromium and headless Chromium proof requirements;
- exact static/API proof surface and progress-check guard terms.

## Non-Admission Boundary

This selection admits no runtime behavior, no rendered behavior, no backend behavior, no route/API/DTO/model/migration/service behavior change, no UI control change, no executable test behavior change, no single mockup screen server-authoritative activation, and no full mockup program activation.

It also admits no caller-supplied path, caller-supplied directory, browser file bytes, URL input, glob input, caller-selected recursive flag, source expansion, package mutation/construction, connector/destination dispatch, provider URL behavior, cloud object-store write, RAG/vector widening, prompt/model/provider qualitative generation, hidden LLM planning, optional-tool runtime, auth/security behavior, browser-storage authority, or frontend-only durable authority.

## Validation Basis

Required validation for this no-runtime selection:

- `python ./tools/l3-progress-check.py`;
- JSON validation for `next_milestone_plans/layer3_progress_manifest.json`;
- JSON validation for `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `git diff --check`.

No runtime, API, or browser test is required for this selection because it changes no runtime behavior, route, dependency, session-summary field, rendered UI, or browser behavior.

## Next Posture

The next exact posture is `freeze_source_directory_ingestion_scan_status_mockup_screen_activation_before_runtime`.

Do not implement source-directory mockup-screen activation or full mockup program activation until that freeze is current-main selected, review-cleared, and checker-backed.
