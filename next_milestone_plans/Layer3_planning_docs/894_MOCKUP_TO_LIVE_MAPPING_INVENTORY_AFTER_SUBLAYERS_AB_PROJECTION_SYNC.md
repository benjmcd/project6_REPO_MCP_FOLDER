# 894 - Mockup-To-Live Mapping Inventory After Sublayers AB Projection Sync

## Status

Status: no-runtime mockup-to-live mapping inventory after `current_main_synced_mockup_sublayers_ab_live_state_projection_proof`.

Inventory doc: `894_MOCKUP_TO_LIVE_MAPPING_INVENTORY_AFTER_SUBLAYERS_AB_PROJECTION_SYNC.md`.

Predecessor current-main sync doc: `893_MOCKUP_SUBLAYERS_AB_LIVE_STATE_PROJECTION_PROOF_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before this inventory: `e36507ff50c11ac9ce54522fe324ab2122644913`.

Selected activation mode for this pass: `mockup_to_live_mapping_inventory_after_sublayers_ab_live_state_projection_sync`.

Already current-main synced server-authoritative mockup-screen activation: `source_directory_ingestion_scan_status_mockup_screen_activation`.

Already current-main synced read-only mockup-screen projection: `mockup_sublayers_ab_live_state_projection`.

Selected next activation mode after this inventory: `single_mockup_screen_read_only_projection`.

Selected next target after this inventory: `mockup_sublayer3c_execution_lanes_live_state_projection`.

Selected next freeze: `freeze_mockup_sublayer3c_execution_lanes_live_state_projection_before_runtime`.

Runtime behavior introduced by this inventory: `false`.

Rendered behavior introduced by this inventory: `false`.

Backend behavior introduced by this inventory: `false`.

Route/API/DTO/model/migration/service behavior introduced by this inventory: `false`.

Executable test behavior introduced by this inventory: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed next: `false`.

## Current-Main Authority Baseline

Current `main` now has these bounded mockup activation/projection surfaces:

- source-directory scan/status as the only current-main synced server-authoritative mockup-screen activation proof;
- PDF-location available-state as a current-main synced read-only projection over `State.sessionSummary.pdf_location_projection`;
- downstream Analysis Environment rendered projection as a current-main synced read-only panel over `State.sessionSummary.analysis_environment_projection`;
- Sublayers 3A/3B live-state projection as a current-main synced read-only projection over `State.materialPreview`, `State.gateB`, `State.gateC`, `State.sessionSummary.authority_rail`, and `State.sessionSummary.sublayer_visualization`.

The remaining target-state mockup frames are still design inputs unless each frame is mapped to live route/state/durable authority and proven through tests.

## Grill-Me Self-Check

The relevant decision questions are answerable from current repo evidence:

| Question | Repo-derived answer |
| --- | --- |
| Should the next pass repeat Sublayers 3A/3B projection work? | No. It is current-main synced by doc `893` and PR `#1507`. |
| Should the next pass jump to full mockup activation? | No. `#mockup-execution-lanes`, query/source setup, package/handoff/export, connector/provider, RAG/vector, auth/security, and browser persistence are not fully classified as live or excluded. |
| Is another read-only projection adequate? | Yes. The static `#mockup-execution-lanes` frame can map to existing 3C visualization/session state without new actions. |
| Is a server-authoritative action target more optimal now? | Not yet. The next 3C target can close a visible mockup frame using existing state while preserving action routes for later one-by-one activation. |
| What is the most adequate next target? | `mockup_sublayer3c_execution_lanes_live_state_projection`, because live 3C state already exists in `currentSublayerVisualizationModel()` and `#sublayer-map-panel`, while the mockup `#mockup-execution-lanes` frame remains static. |

## Mockup-To-Live Inventory

| Mockup / target-state control | Current live authority | Current activation state | Required future pass |
| --- | --- | --- | --- |
| Full mockup workbench theme shell | `/review/layer3` `#mockup-theme-shell`, repo-local frame manifest `layer3.mockup_visual_acceptance_frames.v1` | Visual/static theme proof plus selected child projections; not durable workflow authority | Keep as target-state shell until every child control is live, read-only, excluded, or blocked |
| Query/spec fixture and user intent panels | Intent form, source-intake/source-preview/preflight family, raw-mixed materialization, server-configured source-directory controls | Partially live through bounded source intake and source-directory surfaces; broad natural-language orchestration remains under-specified | Later `mockup_query_source_setup_live_projection_or_control_freeze`; no hidden LLM planning or broad source picker by inference |
| PDF-location available-state card | `GET /api/v1/layer3/session/{session_id}`, `State.sessionSummary.pdf_location_projection`, `/review/layer3` `#mockup-pdf-location-projection` | Current-main synced read-only available-state browser proof | No immediate target; keep as already proved read-only projection |
| Source-directory scan/status control | Source-directory scan/status routes, service, durable batch/file rows, rendered controls, browser proof | Current-main synced server-authoritative mockup-screen activation proof | No immediate target; remains the first action-capable proof |
| Sublayer 3A / Gate B and Sublayer 3B / Gate C board | Existing Gate B/Gate C/session state and `/review/layer3` `#mockup-sublayers-ab-projection` | Current-main synced read-only mockup board projection | No immediate target; server-authoritative Gate B/Gate C actions remain separate live controls, not mockup-board write controls |
| Sublayer 3C execution lanes | `currentSublayerVisualizationModel()`, `#sublayer-map-panel`, `State.sessionSummary.sublayer_visualization`, `State.sessionSummary.analysis_environment_projection`, plan preview/approval state, execution selection/status/result state | Live state exists in current rendered map and analysis environment projection; the mockup `#mockup-execution-lanes` frame remains static | Selected next target: `mockup_sublayer3c_execution_lanes_live_state_projection` |
| Analysis environment projection | `State.sessionSummary.analysis_environment_projection`, `renderAnalysisEnvironmentProjectionStatus()`, `backend/app/services/layer3_analysis_environment_projection.py` | Current-main synced read-only rendered projection inside live 3C planes | Use as one authority source for the next 3C mockup projection; do not duplicate runtime |
| Package lifecycle, replacement, supersession, artifact manifest, namespace | Package review, package mutation preview, replacement/supersession/manifest/namespace routes and state | Many bounded server-authoritative surfaces exist; not yet unified into the mockup program view | Candidate after 3C projection: package/handoff/export status projection or one exact rendered control extension |
| Handoff/export/download and downstream delivery | Handoff/export prepare, APS dispatch, external export/download, signed-reference, local outbox, provider-private/public, internal webhook routes and durable receipt/audit state | Multiple bounded surfaces exist; broad connector/provider actions remain constrained | Candidate later: package/handoff/export status board projection; action widening needs separate freezes |
| Connector/destination, provider URL, public delivery, real network egress | Connector/local outbox/provider/internal webhook route families exist in bounded forms | Not full connector/destination program activation | Defer to separate authority/security lanes |
| RAG/vector/semantic retrieval and hybrid qualitative analysis | Bounded qualitative/hybrid/source-directory vector context families exist | Not broad RAG/vector or hidden LLM activation | Defer until exact source/embedding/vector/model authority and leakage proof are frozen |
| Browser persistence, auth/security, frontend durable state | Explicitly blocked by prior boundary docs and proof terms | Not admitted | Required before full-program activation can be declared |

## Options Going Forward

| Option | What it does | Adequacy | Decision |
| --- | --- | --- | --- |
| Inventory-only again | Continues no-runtime classification without choosing a target | Useful only after the next target is unclear | Not selected; current repo evidence identifies 3C execution-lanes projection |
| Rendered control extension | Extends an already-live rendered control with server-owned fields and browser proof | Good later for package/handoff/export or specific action-control ergonomics | Deferred until the static 3C mockup frame is closed |
| Single mockup screen read-only projection | Maps a static mockup frame to existing server state without new actions | Best current fit for `#mockup-execution-lanes` because live 3C state already exists outside the mockup frame | Selected |
| Single mockup screen server-authoritative activation | Proves an action-capable mockup control against route/state/durable authority | High value, but should target one remaining action after the 3C static frame is current-main synced | Deferred |
| Full mockup program activation | Declares the whole target-state workbench live | Not adequate while several controls remain unproved or blocked | Rejected until final readiness audit |

## Selected Next Target Contract

The next no-runtime freeze should target only `mockup_sublayer3c_execution_lanes_live_state_projection`.

Canonical source of truth to verify before implementation:

- mockup selector: `/review/layer3` `#mockup-execution-lanes`;
- live rendered state owner: `backend/app/review_ui/static/layer3.js::currentSublayerVisualizationModel()`;
- live rendered map selector: `/review/layer3` `#sublayer-map-panel`;
- session route: `GET /api/v1/layer3/session/{session_id}`;
- session-summary sources: `State.sessionSummary.sublayer_visualization` and `State.sessionSummary.analysis_environment_projection`;
- plan state sources: `State.planPreview`, `State.planApproval`, and planned-pass/session summary state where present;
- execution state sources: `State.executionSelection`, `State.executionStart`, `State.executionResultStatus`, `State.executionResultReview`, and session summary output state where present;
- durable state families: `L3AnalysisPlan`, `L3PassRun`, `L3TypingRecord`, `L3AnalysisUnit`, `L3AnalysisGroup`, `L3AnalysisSet`, and existing package/output refs where already surfaced by the live map;
- rendered owner files: `backend/app/review_ui/static/layer3.html`, `backend/app/review_ui/static/layer3.js`, and `backend/app/review_ui/static/layer3.css`;
- static page contract tests: `backend/tests/test_layer3_page.py`;
- browser proof file: `e2e/layer3-workbench.spec.js`.

The future freeze must name exact fields before implementation. It should prefer read-only counts/statuses/labels derived from existing live 3C state: per-plane input object counts, plan/pass state, process/status state, output count/ref count, analysis-environment readiness, fail-closed unavailable state, and fixed state-source labels.

The future proof must show that `#mockup-execution-lanes` renders only server-owned/read-only state and does not create plan approval, execution start, result review, package mutation, handoff/export, connector/provider, source expansion, RAG/vector, hidden LLM, browser-storage, auth/security, or frontend-only durable authority.

## Required Whole-Program Path

The full path remains staged:

1. Current pass: record this post-Sublayers-AB mapping inventory and selected next target.
2. Freeze `mockup_sublayer3c_execution_lanes_live_state_projection` with exact route/state/DOM/test contract.
3. Implement and prove the 3C execution-lanes read-only mockup projection in headless and headed Chromium.
4. Current-main sync the 3C projection proof.
5. Freeze, prove, and sync a query/source setup projection or control that maps the mockup intent/source panel to existing source-intake/source-directory authority without broad source picker, hidden LLM, or caller path widening.
6. Freeze, prove, and sync a package/handoff/export live status projection that maps downstream mockup delivery areas to existing package, replacement, handoff, export, webhook, provider, and connector state without adding new delivery actions.
7. Re-run a full mockup-to-live coverage audit: every mockup frame/control must be classified as live action, live read-only projection, static visual context, explicitly excluded, or blocked.
8. For any remaining action-capable gap, choose one bounded server-authoritative action lane at a time with exact route, DTO, durable state, idempotency, stale-authority behavior, fail-closed behavior, static tests, backend tests, and headed/headless browser proof.
9. Resolve or explicitly exclude broad source picker/local path/browser file bytes, real connector/destination dispatch, provider/public URL use, RAG/vector/semantic retrieval breadth, hidden LLM planning, auth/security, and browser persistence.
10. Run full-program readiness audit after all critical controls are current-main synced.
11. Run end-to-end browser/API proof for one representative mockup scenario from source through package/handoff/export, with isolated runtime state.
12. Declare full mockup activation only if every critical mockup operator journey is live, read-only, excluded, or explicitly blocked with current-main evidence.

## Non-Admission Boundary

This inventory admits no runtime behavior, no rendered behavior, no backend behavior, no route/API/DTO/model/migration/service behavior change, no executable test behavior change, no production UI behavior change, no new write control, no source expansion, no caller path/directory/file-byte/URL/glob/recursive-flag support, no package mutation, no connector/destination dispatch, no provider URL behavior, no RAG/vector widening, no hidden LLM planning, no optional-tool runtime, no auth/security behavior, no browser-storage authority, no frontend-only durable authority, and no full mockup program activation.

## Validation Basis

Required validation for this inventory:

- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json`;
- `python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.

No API, runtime, or browser test is required for this inventory because it changes no runtime behavior, rendered UI behavior, route, dependency, session-summary field, executable test, or browser behavior.

## Next Posture

The next exact posture is `freeze_mockup_sublayer3c_execution_lanes_live_state_projection_before_runtime`.

Do not implement the 3C execution-lanes projection until that freeze is current-main selected, review-cleared, and checker-backed.
