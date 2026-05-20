# 889 - Mockup-To-Live Mapping Inventory After Source Directory Activation Sync

## Status

Status: no-runtime mockup-to-live mapping inventory after `current_main_synced_source_directory_ingestion_scan_status_mockup_screen_activation_proof`.

Inventory doc: `889_MOCKUP_TO_LIVE_MAPPING_INVENTORY_AFTER_SOURCE_DIRECTORY_ACTIVATION_SYNC.md`.

Predecessor current-main sync doc: `888_SOURCE_DIRECTORY_ACTIVATION_PROOF_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before this inventory: `296d50b120ebe9f3b503b743c90110f4f6209cfe`.

Selected activation mode for this pass: `mockup_to_live_mapping_inventory_after_source_directory_activation_proof_sync`.

Source-directory scan/status activation status: `current_main_synced_source_directory_ingestion_scan_status_mockup_screen_activation_proof`.

Selected next activation mode after this inventory: `single_mockup_screen_read_only_projection`.

Selected next target after this inventory: `mockup_sublayers_ab_live_state_projection`.

Selected next freeze: `freeze_mockup_sublayers_ab_live_state_projection_before_runtime`.

Runtime behavior introduced by this inventory: `false`.

Rendered behavior introduced by this inventory: `false`.

Backend behavior introduced by this inventory: `false`.

Route/API/DTO/model/migration/service behavior introduced by this inventory: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed next: `false`.

## Current-Main Authority Baseline

Current `main` now has one bounded server-authoritative mockup-screen activation proof:

- `/review/layer3` `#source-directory-ingestion-rendered-controls`;
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`;
- request DTO `Layer3SourceDirectoryIngestionScanRequest`;
- backend service `backend/app/services/layer3_source_directory_ingestion.py`;
- durable state `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile`;
- browser proof in `e2e/layer3-workbench.spec.js`;
- current-main sync in `888_SOURCE_DIRECTORY_ACTIVATION_PROOF_CURRENT_MAIN_SYNC.md`.

That proof activates only the source-directory scan/status surface. It does not activate the full mockup program, any other mockup control, any new source picker, caller path support, browser file bytes, URL/glob input, connector/provider behavior, package mutation, hidden LLM planning, auth/security behavior, browser-storage authority, or frontend-only durable authority.

The mockup corpus remains target-state design input unless a specific control is mapped to live route/state/durable authority and proven through tests.

## Grill-Me Self-Check

The relevant decision questions were answerable from the repo, so this pass does not need to ask the operator for preference:

| Question | Repo-derived answer |
| --- | --- |
| Is the first preferred activation target already done? | Yes. Source-directory scan/status is current-main synced as a bounded server-authoritative mockup-screen activation proof. |
| Should the next step repeat source-directory scan/status work? | No. Further scan/status work would duplicate the proved target unless a separate defect appears. |
| Should the next step jump to full-program activation? | No. Several remaining mockup controls still lack one-by-one route/state/durable/test classification. |
| Is another read-only projection adequate? | Yes, if it maps a remaining mockup frame to server state and closes a visible target-state gap without new actions. |
| What is the most adequate next target? | `mockup_sublayers_ab_live_state_projection`, because it maps a remaining mockup frame to existing Gate B/Gate C route and durable state without widening runtime scope. |

## Mockup-To-Live Inventory

| Mockup / target-state control | Current live authority | Current activation state | Required future pass |
| --- | --- | --- | --- |
| Full mockup workbench theme shell | `/review/layer3` `#mockup-theme-shell`, repo-local frame manifest `layer3.mockup_visual_acceptance_frames.v1` | Visual/static theme proof only; not durable workflow authority | Keep as target-state visual frame until each child control has live proof |
| Query/spec fixture and user intent panels | Current source-intake/source-preview/preflight family plus server-configured source-directory controls | Partially live through bounded source intake and source-directory surfaces; natural-language/manual-spec orchestration remains under-specified | Later `mockup_query_source_setup_live_projection_or_control_freeze`; do not admit hidden LLM planning or broad source picker by inference |
| PDF-location available-state card | `GET /api/v1/layer3/session/{session_id}`, `State.sessionSummary.pdf_location_projection`, `backend/app/services/layer3_pdf_location.py`, `/review/layer3` `#mockup-pdf-location-projection` | Current-main synced read-only available-state browser proof | No immediate target; keep as already proved read-only projection |
| Source-directory scan/status control | Existing source-directory scan/status routes, service, durable batch/file rows, rendered controls, and browser proof | Current-main synced server-authoritative mockup-screen activation proof | No immediate target; use only as predecessor evidence |
| Sublayer 3A / Gate B material ledger | `/material-preview`, `/gate-b/decision`, `L3SelectionManifest`, `L3MaterialSnapshot`, source-intake/source-directory material families, `/review/layer3` `#gate-b-band` | Live in bounded workflow controls, but the mockup `#mockup-sublayers-ab-board` still remains static target-state projection | Selected next target: freeze read-only live-state projection into `#mockup-sublayers-ab-board` |
| Sublayer 3B / Gate C typing, units, groups, sets | `/gate-c/preview`, `/gate-c/override`, `L3TypingRecord`, `L3AnalysisUnit`, `L3AnalysisGroup`, `L3AnalysisSet`, `/review/layer3` `#gate-c-band` | Live in bounded workflow controls; not yet mapped into the mockup Sublayer 3A/3B board as server-state projection | Selected next target with Gate B because the mockup frame spans both sublayers |
| Sublayer 3C execution lanes | `/readiness`, `/plan/preview`, `/plan/approve`, `/execution/select`, `/execution/start`, `/execution/result/status`, `/execution/result/review`, `L3AnalysisPlan`, `L3PassRun`, `/review/layer3` `#mockup-execution-lanes` and `#result-review-band` | Several bounded route/control surfaces are live; the mockup execution-lanes frame is still static | Candidate after Sublayer 3A/3B projection: `mockup_sublayer3c_execution_lanes_live_state_projection` |
| Analysis environment projection | `State.sessionSummary.analysis_environment_projection`, `/review/layer3` rendered analysis environment panels | Current-main read-only rendered projection already exists | Not selected now; preserve as already-admitted read-only visibility |
| Package lifecycle, replacement, supersession, artifact manifest, namespace | `/package/review/*`, `/package/mutation/preview`, replacement/supersession/manifest/namespace routes, `L3OutputPackage`, replacement package state models, `/review/layer3` package panels | Many bounded server-authoritative surfaces exist; not all are mockup-frame activated as one coherent program view | Candidate after Sublayer 3C: package/handoff live status projection or rendered-control extension |
| Handoff/export/download and downstream delivery | `/handoff/export/prepare`, APS dispatch, external export/download, signed-reference, local outbox, provider-private/public, internal webhook routes and durable receipt/audit state | Multiple bounded surfaces exist; internal webhook read-only status is already current-main synced | Candidate later: package/handoff/export status board projection; action widening requires separate freezes |
| Connector/destination, provider URL, public delivery, real network egress | Connector/local outbox and provider-private/public route families exist in bounded forms | Not full real connector/destination program activation; external/network/credential/raw URL behavior remains constrained | Defer to separate authority/security lanes |
| RAG/vector/semantic retrieval and hybrid qualitative analysis | Source-directory vector, hybrid context packet, qualitative/hybrid analysis route families exist in bounded forms | Not full broad RAG/vector/hidden LLM activation | Defer until exact source/embedding/vector/model authority and leakage proof are frozen |
| Browser persistence, auth/security, frontend durable state | Explicitly blocked by prior boundary docs and proof terms | Not admitted | Required before full-program activation can be declared |

## Options Going Forward

| Option | What it does | Adequacy | Decision |
| --- | --- | --- | --- |
| Continue inventory-only | Produces more no-runtime planning without selecting a concrete next screen | Useful only if evidence is missing | Not selected because the next target is now adequate |
| Rendered control extension | Extends an already-live rendered control with server-owned fields and browser proof | Good when a live control exists but the operator view is under-instrumented | Available later for package/handoff/execution controls; source-directory version is already complete |
| Single mockup screen read-only projection | Maps a static mockup frame to existing server state without admitting new actions | Best current fit because the remaining Sublayer 3A/3B frame can be backed by Gate B/Gate C state | Selected: `mockup_sublayers_ab_live_state_projection` |
| Single mockup screen server-authoritative activation | Proves an action-capable control as live route/state/durable authority | High value, but should follow a freeze for exactly one remaining action surface | Deferred until the selected read-only frame projection is frozen/proved or a stronger action target is named |
| Full mockup program activation | Declares the whole target-state workbench live | Not adequate now; too many controls still need per-surface proof or explicit exclusion | Rejected until final readiness audit |

## Selected Next Target Contract

The next no-runtime freeze should target only `mockup_sublayers_ab_live_state_projection`.

Canonical source of truth to verify before implementation:

- mockup selector: `/review/layer3` `#mockup-sublayers-ab-board`;
- live material selector: `/review/layer3` `#gate-b-band`;
- live typing selector: `/review/layer3` `#gate-c-band`;
- session route: `GET /api/v1/layer3/session/{session_id}`;
- material routes: `POST /api/v1/layer3/material-preview` and `POST /api/v1/layer3/gate-b/decision`;
- typing routes: `POST /api/v1/layer3/gate-c/preview` and blocked `POST /api/v1/layer3/gate-c/override`;
- durable state: `L3SelectionManifest`, `L3MaterialSnapshot`, `L3TypingRecord`, `L3AnalysisUnit`, `L3AnalysisGroup`, and `L3AnalysisSet`;
- rendered owner file: `backend/app/review_ui/static/layer3.js`;
- rendered shell file: `backend/app/review_ui/static/layer3.html`;
- static page contract tests: `backend/tests/test_layer3_page.py`;
- browser proof file: `e2e/layer3-workbench.spec.js`.

The future freeze must name exact fields before implementation. It should prefer read-only counts/statuses/labels derived from existing session summary or existing Gate B/Gate C responses: material count, accepted/blocked/pending status, source family labels, typing readiness, unit/group/set counts, and fail-closed unavailable state.

The future proof must show that the mockup board renders only server-owned state and does not create write controls, duplicate Gate B/Gate C actions, mutate material or typing state, create plans, start execution, package outputs, dispatch handoff/export, expose raw local paths, expose raw payload refs, use browser storage as authority, or admit frontend-only durable state.

## Required Whole-Program Path

The full path remains staged. These are the future passes left as a whole:

1. Current pass: record this post-source-activation mockup-to-live mapping inventory and selected next target.
2. Freeze `mockup_sublayers_ab_live_state_projection` with exact route/state/DOM/test contract.
3. Implement and prove the Sublayer 3A/3B read-only live-state projection in headless and headed Chromium.
4. Current-main sync the Sublayer 3A/3B proof.
5. Freeze and prove `mockup_sublayer3c_execution_lanes_live_state_projection`.
6. Current-main sync the Sublayer 3C proof.
7. Freeze and prove a query/source setup projection or control that maps the mockup intent/source panel to existing source-intake/source-directory authority without broad source picker, hidden LLM, or caller path widening.
8. Freeze and prove a package/handoff/export live status projection that maps the downstream mockup delivery areas to existing package, replacement, handoff, export, webhook, provider, and connector state without adding new delivery actions.
9. Re-run a full mockup-to-live coverage audit: every mockup frame/control must be classified as live action, live read-only projection, static visual context, explicitly excluded, or blocked.
10. For any remaining action-capable gap, choose one bounded server-authoritative action lane at a time: exact route, DTO, durable state, idempotency, stale-authority behavior, fail-closed behavior, static tests, backend tests, and headed/headless browser proof.
11. Resolve or explicitly exclude broad source picker/local path/browser file bytes, real connector/destination dispatch, provider/public URL use, RAG/vector/semantic retrieval breadth, hidden LLM planning, auth/security, and browser persistence.
12. Run full-program readiness audit after all critical controls are current-main synced.
13. Run end-to-end browser/API proof for one representative mockup scenario from source through package/handoff/export, with isolated runtime state.
14. Declare full mockup activation only if every critical mockup operator journey is live, read-only, excluded, or explicitly blocked with current-main evidence.

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

The next exact posture is `freeze_mockup_sublayers_ab_live_state_projection_before_runtime`.

Do not implement the Sublayer 3A/3B projection until that freeze is current-main selected, review-cleared, and checker-backed.
