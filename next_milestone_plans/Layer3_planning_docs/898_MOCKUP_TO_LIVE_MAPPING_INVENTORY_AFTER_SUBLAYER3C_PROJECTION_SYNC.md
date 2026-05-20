# 898 - Mockup-To-Live Mapping Inventory After Sublayer 3C Projection Sync

## Status

Status: no-runtime mockup-to-live mapping inventory after `current_main_synced_mockup_sublayer3c_execution_lanes_live_state_projection_proof`.

Inventory doc: `898_MOCKUP_TO_LIVE_MAPPING_INVENTORY_AFTER_SUBLAYER3C_PROJECTION_SYNC.md`.

Predecessor current-main sync doc: `897_MOCKUP_SUBLAYER3C_EXECUTION_LANES_LIVE_STATE_PROJECTION_PROOF_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before this inventory: `f36d592c04f7ac245dae99c0dc0dd0d4916fb080`.

Selected activation mode for this pass: `mockup_to_live_mapping_inventory_after_sublayer3c_execution_lanes_live_state_projection_sync`.

Already current-main synced server-authoritative mockup-screen activation: `source_directory_ingestion_scan_status_mockup_screen_activation`.

Already current-main synced read-only mockup-screen projections: `mockup_pdf_location_available_state`, `downstream_analysis_environment_projection`, `mockup_sublayers_ab_live_state_projection`, and `mockup_sublayer3c_execution_lanes_live_state_projection`.

Selected next activation mode after this inventory: `single_mockup_screen_read_only_projection`.

Selected next target after this inventory: `mockup_query_source_setup_live_state_projection`.

Selected next freeze: `freeze_mockup_query_source_setup_live_state_projection_before_runtime`.

Runtime behavior introduced by this inventory: `false`.

Rendered behavior introduced by this inventory: `false`.

Backend behavior introduced by this inventory: `false`.

Route/API/DTO/model/migration/service behavior introduced by this inventory: `false`.

Executable test behavior introduced by this inventory: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed next: `false`.

## Current Mockup-To-Live State

Current `main` now has these bounded mockup activation/projection surfaces:

- source-directory scan/status as the only current-main synced server-authoritative mockup-screen activation proof;
- PDF-location available-state as a current-main synced read-only projection over `State.sessionSummary.pdf_location_projection`;
- downstream Analysis Environment rendered projection as a current-main synced read-only panel over `State.sessionSummary.analysis_environment_projection`;
- Sublayers 3A/3B live-state projection as a current-main synced read-only projection over existing Gate B/Gate C/session state;
- Sublayer 3C execution-lanes projection as a current-main synced read-only projection over existing session, plan, execution, result, and analysis-environment state.

The remaining target-state mockup frames are still design inputs unless each frame is mapped to live route/state/durable authority and proven through tests.

## Decision Check

| Question | Answer |
| --- | --- |
| Should the next pass repeat Sublayer 3C projection work? | No. It is current-main synced by doc `897` and PR `#1511`. |
| Should the next pass jump to full mockup activation? | No. Query/source setup, package/handoff/export, connector/provider, RAG/vector, auth/security, and browser persistence are not fully classified as live or excluded. |
| Should the next pass select package/handoff/export first? | Not yet. The required whole-program path in doc `894` places query/source setup before package/handoff/export status projection. |
| Is a server-authoritative query/source action target optimal now? | Not as the next slice. Existing preflight/source-preview/material-preview and source-intake/source-directory actions are live, but the mockup query/source frame itself still mixes target-state natural-language orchestration with blocked broad source picker, hidden LLM, caller path, file-byte, URL, glob, connector, provider, and RAG/vector concerns. |
| Is a read-only query/source projection adequate? | Yes. It can map the static mockup query/source frame to existing server-owned intent, source-class, preflight, source-preview, material-preview, source-intake, and source-directory authority without adding new actions. |
| What is the most adequate next target? | `mockup_query_source_setup_live_state_projection`, because it closes the next static mockup frame while preserving all action-capable widening for later frozen lanes. |

## Mockup-To-Live Inventory

| Mockup / target-state control | Current live authority | Current activation state | Required future pass |
| --- | --- | --- | --- |
| Full mockup workbench theme shell | `/review/layer3` `#mockup-theme-shell`, repo-local frame manifest `layer3.mockup_visual_acceptance_frames.v1` | Visual/static theme proof plus selected child projections; not durable workflow authority | Keep as target-state shell until every child control is live, read-only, excluded, or blocked |
| Query/spec fixture and natural-language user intent panels | `/review/layer3` `#mockup-fixture-scenario` `.mockup-fixture-query`, `/review/layer3` `#mockup-userflow-board` `.mockup-userflow-prompt`, live `/review/layer3` `#intent-band`, `#intent-form`, `#source-fieldset`, `POST /api/v1/layer3/preflight`, `POST /api/v1/layer3/source-preview`, `POST /api/v1/layer3/material-preview`, `State.preflight`, `State.sourcePreview`, and `State.materialPreview` | Static mockup frame plus existing live rendered intent/source controls outside the mockup frame | Selected next target: `mockup_query_source_setup_live_state_projection` |
| Source-intake rendered controls | `/review/layer3` `#source-intake-rendered-controls`, `POST /api/v1/layer3/source/intake/upload`, `GET /api/v1/layer3/source/intake/inventory`, `GET /api/v1/layer3/source/intake/{source_intake_record_id}/preview`, and existing Gate B admission path | Existing server-authoritative rendered source-intake control surface; not yet mapped into the mockup query/source frame | Use as one authority source for read-only query/source setup projection; do not add source-intake actions inside the mockup frame in this next slice |
| Source-directory scan/status control | `/review/layer3` `#source-directory-ingestion-rendered-controls`, source-directory scan/status routes, service, durable batch/file rows, and browser proof | Current-main synced server-authoritative mockup-screen activation proof | Use as one authority source for query/source setup projection; do not add caller path, caller directory, recursive flag, URL, glob, or browser file-byte support |
| PDF-location available-state card | `GET /api/v1/layer3/session/{session_id}`, `State.sessionSummary.pdf_location_projection`, `/review/layer3` `#mockup-pdf-location-projection` | Current-main synced read-only available-state browser proof | No immediate target; keep as already proved read-only projection |
| Sublayer 3A / Gate B and Sublayer 3B / Gate C board | Existing Gate B/Gate C/session state and `/review/layer3` `#mockup-sublayers-ab-projection` | Current-main synced read-only mockup board projection | No immediate target; server-authoritative Gate B/Gate C actions remain separate live controls, not mockup-board write controls |
| Sublayer 3C execution lanes | `currentSublayerVisualizationModel()`, `#sublayer-map-panel`, session summary, plan, execution, result, and analysis-environment state | Current-main synced read-only mockup projection | No immediate target; server-authoritative plan/execution/result-review actions remain separate lanes |
| Package lifecycle, replacement, supersession, artifact manifest, namespace | Package review, package mutation preview, replacement/supersession/manifest/namespace routes and state | Many bounded server-authoritative surfaces exist; not yet unified into the mockup program view | Candidate after query/source setup projection: package/handoff/export status projection or one exact rendered control extension |
| Handoff/export/download and downstream delivery | Handoff/export prepare, APS dispatch, external export/download, signed-reference, local outbox, provider-private/public, internal webhook routes and durable receipt/audit state | Multiple bounded surfaces exist; broad connector/provider actions remain constrained | Candidate later: package/handoff/export status board projection; action widening needs separate freezes |
| Connector/destination, provider URL, public delivery, real network egress | Connector/local outbox/provider/internal webhook route families exist in bounded forms | Not full connector/destination program activation | Defer to separate authority/security lanes |
| RAG/vector/semantic retrieval and hybrid qualitative analysis | Bounded qualitative/hybrid/source-directory vector context families exist | Not broad RAG/vector or hidden LLM activation | Defer until exact source/embedding/vector/model authority and leakage proof are frozen |
| Browser persistence, auth/security, frontend durable state | Explicitly blocked by prior boundary docs and proof terms | Not admitted | Required before full-program activation can be declared |

## Options Going Forward

| Option | What it does | Adequacy | Decision |
| --- | --- | --- | --- |
| Inventory-only again | Continues no-runtime classification without choosing a target | Useful only if the post-3C target is unclear | Not selected; current repo evidence identifies query/source setup projection as the next bounded frame |
| Rendered control extension | Extends an already-live rendered control with server-owned fields and browser proof | Useful later for source-intake/source-directory or package/handoff/export ergonomics | Deferred until the query/source mockup frame has a read-only live-state projection |
| Single mockup screen read-only projection | Maps a static mockup frame to existing server state without new actions | Best current fit for query/source setup because live intent/source state exists outside the mockup frame while broad source orchestration remains blocked | Selected |
| Single mockup screen server-authoritative activation | Proves an action-capable mockup control against route/state/durable authority | High value later, but premature while the mockup query/source frame still mixes blocked broad source picker, hidden LLM, and source expansion concerns | Deferred |
| Full mockup program activation | Declares the whole target-state workbench live | Not adequate while several controls remain unproved or blocked | Rejected until final readiness audit |

## Selected Next Target Contract

The next no-runtime freeze should target only `mockup_query_source_setup_live_state_projection`.

The selected authority chain is:

- static mockup surfaces: `/review/layer3 #mockup-fixture-scenario .mockup-fixture-query`, `/review/layer3 #mockup-userflow-board .mockup-userflow-prompt`, and `/review/layer3 .mockup-pre3a`;
- live rendered intent/source surfaces: `/review/layer3 #intent-band`, `/review/layer3 #intent-form`, `/review/layer3 #source-fieldset`, `/review/layer3 #source-intake-rendered-controls`, and `/review/layer3 #source-directory-ingestion-rendered-controls`;
- live route authority: `POST /api/v1/layer3/preflight`, `POST /api/v1/layer3/source-preview`, `POST /api/v1/layer3/material-preview`, `POST /api/v1/layer3/source/intake/upload`, `GET /api/v1/layer3/source/intake/inventory`, `GET /api/v1/layer3/source/intake/{source_intake_record_id}/preview`, `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`, and `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`;
- live state sources: `State.preflight`, `State.sourcePreview`, `State.materialPreview`, `source-intake rendered control state`, `source-directory rendered control state`, and `State.sessionSummary`;
- rendered owner files: `backend/app/review_ui/static/layer3.html`, `backend/app/review_ui/static/layer3.js`, and `backend/app/review_ui/static/layer3.css`;
- static page contract tests: `backend/tests/test_layer3_page.py`.

The future proof must show that the mockup query/source frame renders only server-owned/read-only setup state and does not create new natural-language orchestration, source picker behavior, source upload, caller path, caller directory, browser file byte, URL, glob, recursive-flag support, package mutation, handoff/export dispatch, connector/destination dispatch, provider URL behavior, RAG/vector widening, hidden LLM planning, browser-storage authority, auth/security behavior, or frontend-only durable authority.

## Required Whole-Program Path

The full path remains staged:

1. Current pass: record this post-3C mapping inventory and selected next target.
2. Freeze `mockup_query_source_setup_live_state_projection` with exact route/state/DOM/test contract.
3. Implement and prove the query/source setup read-only mockup projection in headless and headed Chromium.
4. Current-main sync the query/source setup projection proof.
5. Freeze, prove, and sync a package/handoff/export live status projection that maps downstream mockup delivery areas to existing package, replacement, handoff, export, webhook, provider, and connector state without adding new delivery actions.
6. Re-run a full mockup-to-live coverage audit: every mockup frame/control must be classified as live action, live read-only projection, static visual context, explicitly excluded, or blocked.
7. For any remaining action-capable gap, choose one bounded server-authoritative action lane at a time with exact route, DTO, durable state, idempotency, stale-authority behavior, fail-closed behavior, static tests, backend tests, and headed/headless browser proof.
8. Resolve or explicitly exclude broad source picker/local path/browser file bytes, real connector/destination dispatch, provider/public URL use, RAG/vector/semantic retrieval breadth, hidden LLM planning, auth/security, and browser persistence.
9. Run full-program readiness audit after all critical controls are current-main synced.
10. Run end-to-end browser/API proof for one representative mockup scenario from source through package/handoff/export, with isolated runtime state.
11. Declare full mockup activation only if every critical mockup operator journey is live, read-only, excluded, or explicitly blocked with current-main evidence.

## Non-Admission Boundary

This inventory admits no runtime behavior, no rendered behavior, no backend behavior, no route/API/DTO/model/migration/service behavior change, no executable test behavior change, no production UI behavior change, no new write control, no source expansion, no caller path/directory/file-byte/URL/glob/recursive-flag support, no package mutation, no connector/destination dispatch, no provider URL behavior, no RAG/vector widening, no hidden LLM planning, no optional-tool runtime, no auth/security behavior, no browser-storage authority, no frontend-only durable authority, and no full mockup program activation.

## Validation Basis

This inventory is validated by:

- JSON syntax validation for `next_milestone_plans/layer3_progress_manifest.json`;
- JSON syntax validation for `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `python -m py_compile tools/l3-progress-check.py`;
- `python tools/l3-progress-check.py`;
- `git diff --check`.

No API, runtime, or browser test is required for this inventory because it changes no runtime behavior, rendered UI behavior, route, dependency, session-summary field, executable test, or browser behavior.

## Next Posture

The next exact posture is `freeze_mockup_query_source_setup_live_state_projection_before_runtime`.

Do not implement the query/source setup projection until that freeze is current-main selected, review-cleared, and checker-backed.
