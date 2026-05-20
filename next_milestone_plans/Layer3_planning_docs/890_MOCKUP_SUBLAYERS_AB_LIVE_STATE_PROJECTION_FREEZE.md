# 890 - Mockup Sublayers AB Live State Projection Freeze

## Status

Status: no-runtime/no-rendered implementation-entry freeze for `prove_mockup_sublayers_ab_live_state_projection_without_runtime_widening`.

Freeze doc: `890_MOCKUP_SUBLAYERS_AB_LIVE_STATE_PROJECTION_FREEZE.md`.

Predecessor inventory doc: `889_MOCKUP_TO_LIVE_MAPPING_INVENTORY_AFTER_SOURCE_DIRECTORY_ACTIVATION_SYNC.md`.

Current-main checkpoint before this freeze: `bc323f714dba7c1ee960e0758e5a48c4c46c2f2c`.

Selected activation mode: `single_mockup_screen_read_only_projection_freeze`.

Selected target: `mockup_sublayers_ab_live_state_projection`.

Selected proof action: `prove_mockup_sublayers_ab_live_state_projection_without_runtime_widening`.

Selected mockup surface: `/review/layer3` `#mockup-sublayers-ab-board`.

Selected live state sources: `/review/layer3` `#gate-b-band`, `/review/layer3` `#gate-c-band`, and `/review/layer3` `#sublayer-map-panel`.

Rendered surface decision: `extend_existing_mockup_sublayers_ab_board_as_read_only_projection`.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Backend behavior introduced by this freeze: `false`.

Route/API/DTO/model/migration/service behavior introduced by this freeze: `false`.

Single mockup screen read-only projection introduced by this freeze: `false`.

Single mockup screen server-authoritative activation introduced by this freeze: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed next: `false` until this freeze is current-main synced.

## Grill-Me Self-Check

The relevant decision questions were answerable from repo evidence, so this freeze does not need operator preference before landing:

| Question | Repo-derived answer |
| --- | --- |
| Is this a new action target? | No. It is a read-only projection target over existing Gate B/Gate C state. |
| Is there already server authority for the state? | Yes. Gate B commits session/material state and Gate C previews or commits typing state; session summary exposes read-only `sublayer_visualization`. |
| Should the mockup board own durable state? | No. It may render existing server state only. |
| Should the future proof add or duplicate Gate B/Gate C buttons? | No. The future projection must not add write controls or duplicate existing workflow actions. |
| Is full mockup activation adequate now? | No. This target covers only the Sublayer 3A/3B mockup frame; other frames still need separate proof or exclusion. |

## Canonical Source Of Truth

The canonical source of truth for the future Sublayer 3A/3B projection is the existing server-owned Gate B/Gate C session state and read-only session summary:

- mockup target selector: `/review/layer3` `#mockup-sublayers-ab-board`;
- current live material selector: `/review/layer3` `#gate-b-band`;
- current live typing selector: `/review/layer3` `#gate-c-band`;
- current live sublayer map selector: `/review/layer3` `#sublayer-map-panel`;
- session route: `GET /api/v1/layer3/session/{session_id}`;
- material preview route: `POST /api/v1/layer3/material-preview`;
- Gate B decision route: `POST /api/v1/layer3/gate-b/decision`;
- Gate C preview route: `POST /api/v1/layer3/gate-c/preview`;
- blocked typing override route: `POST /api/v1/layer3/gate-c/override`, which returns HTTP `409`;
- service authority: `backend/app/services/layer3_workbench.py` functions `material_preview`, `gate_b_decision`, `gate_c_preview`, and `session_summary`;
- read-only session projection owner: `backend/app/services/layer3_sublayer_state.py` function `session_sublayer_visualization_state`;
- rendered owner file: `backend/app/review_ui/static/layer3.js`;
- rendered shell file: `backend/app/review_ui/static/layer3.html`;
- static page contract tests: `backend/tests/test_layer3_page.py`;
- browser proof file: `e2e/layer3-workbench.spec.js`.

Mockup images, screenshots, static object labels, browser-local state, local storage, copied output, and frontend-only state are target-state aids only. They are not authority for projection activation.

## Route And State Contract

The future projection may read only state already available through existing workbench state paths:

- `State.materialPreview.material_candidates`;
- `State.gateB.session_id`;
- `State.gateB.approved_candidate_ids`;
- `State.gateB.denied_candidate_ids`;
- `State.gateB.isolated_candidate_ids`;
- `State.gateB.flagged_candidate_ids`;
- `State.gateB.authority_rail`;
- `State.gateC.typing_records`;
- `State.gateC.analysis_units`;
- `State.gateC.analysis_groups`;
- `State.gateC.analysis_sets`;
- `State.gateC.unsupported_material`;
- `State.gateC.authority_rail`;
- `State.sessionSummary.gate_b_summary`;
- `State.sessionSummary.gate_c_summary`;
- `State.sessionSummary.authority_rail`;
- `State.sessionSummary.sublayer_visualization`.

The projection must fail closed when none of those sources are loaded. Empty state must render as unavailable or not loaded, not as activated material or typing state.

## Durable Authority Contract

The durable authority owners for the future proof are:

- `L3SelectionManifest`;
- `L3MaterialSnapshot`;
- `L3TypingRecord`;
- `L3AnalysisUnit`;
- `L3AnalysisGroup`;
- `L3AnalysisSet`.

`L3SelectionManifest` and `L3MaterialSnapshot` represent the Gate B session/material authority. `L3TypingRecord`, `L3AnalysisUnit`, `L3AnalysisGroup`, and `L3AnalysisSet` represent Gate C typing and set-formation authority when typing is committed.

Preview-only `material-preview` and uncommitted Gate C preview responses may render as preview state only. The projection must not upgrade preview-only data into durable state.

## Rendered Projection Contract

The future projection may extend `#mockup-sublayers-ab-board` only as a read-only projection over server-owned state.

The projection may show:

- session id when available;
- material preview id and material preview hash when already present in state;
- material candidate count;
- material snapshot count;
- approved, denied, isolated, flagged, and pending material counts;
- source family or source shape labels already present in response-safe state;
- typing status from the authority rail;
- typing record count;
- analysis unit count;
- analysis group count;
- analysis set count;
- unsupported material count;
- quantitative, qualitative, hybrid, and unclassified lane counts;
- unavailable or blocked state when server state is missing.

The projection must not render:

- raw local paths;
- raw payload refs;
- raw diagnostics refs;
- provider URLs;
- public URLs;
- signed URLs;
- connector run ids;
- destination ids;
- provider credentials;
- browser file bytes;
- browser-owned durable state;
- unredacted output/package refs beyond existing safe status labels.

## Required Future Write Scope

The later proof should be limited to:

- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.js`;
- `backend/app/review_ui/static/layer3.css`;
- `backend/tests/test_layer3_page.py`;
- `e2e/layer3-workbench.spec.js`;
- progress/proof docs and manifests needed to record the projection proof;
- `tools/l3-progress-check.py` guard terms for this freeze and the later proof.

No production backend route, DTO, model, migration, service, durable-state write path, source traversal, package, connector, provider, RAG/vector, auth/security, or browser-storage behavior may change under this freeze.

## Required Future Proof

The future projection proof must show:

- static page proof that the mockup board selector remains stable;
- static JS proof that the projection reads existing state only;
- browser proof that the projection renders available Gate B and Gate C state;
- browser proof that missing server state renders unavailable or not loaded;
- browser proof that no new buttons, inputs, forms, or write controls are added to the mockup board;
- browser proof that the projection itself does not call `material-preview`, `gate-b/decision`, `gate-c/preview`, `gate-c/override`, plan, execution, package, handoff, connector, provider, source expansion, or optional-tool routes;
- browser proof that no raw path, payload ref, provider URL, public URL, signed URL, connector id, destination id, credential, or browser file byte renders;
- browser proof that no browser storage key becomes authority for the projection;
- headed Chromium proof;
- headless Chromium proof;
- responsive no-horizontal-overflow proof;
- no console errors and no page errors;
- progress-check guard coverage for this exact freeze and the later projection proof.

## No-Go Surface

The future projection proof must not admit:

- new Gate B action controls;
- new Gate C action controls;
- duplicate existing Gate B or Gate C buttons;
- material mutation;
- typing mutation;
- typing override;
- plan preview or plan approval;
- execution selection or execution start;
- result review;
- package construction or package mutation;
- handoff/export dispatch;
- connector or destination dispatch;
- provider-private signed URL behavior;
- provider-public URL behavior;
- source expansion;
- caller paths;
- caller directories;
- browser file bytes;
- URL input;
- glob input;
- caller-selected recursive flags;
- RAG/vector widening;
- hidden LLM planning;
- optional-tool runtime;
- auth/security behavior change;
- browser-storage authority;
- frontend-only durable state;
- full mockup program activation.

## Immediate Milestone

Milestone 1: current-main sync this freeze, then prove `mockup_sublayers_ab_live_state_projection` as a single mockup-screen read-only projection without runtime widening.

Exit criteria for the later proof:

- `#mockup-sublayers-ab-board` renders read-only live-state labels from existing server state;
- the projection handles unavailable state fail-closed;
- the projection adds no actions and sends no side-effect requests;
- the projection leaks no raw path, payload ref, provider URL, connector/destination, credential, or browser-byte authority;
- headed and headless Chromium proof pass;
- no backend/API/model/migration/service/source/package/connector/provider/RAG/auth/browser-storage behavior changes occur;
- `python .\tools\l3-progress-check.py` passes.

## Mid-Term Milestones

Milestone 2: current-main sync the Sublayer 3A/3B projection proof.

Milestone 3: freeze and prove `mockup_sublayer3c_execution_lanes_live_state_projection`.

Milestone 4: freeze and prove a query/source setup projection or control without broad source picker, caller path, URL/glob input, browser file bytes, or hidden LLM planning.

Milestone 5: freeze and prove a package/handoff/export live status projection or rendered control extension without new delivery actions.

## Long-Term Milestones

Milestone 6: rerun a full mockup-to-live coverage audit and classify every mockup frame/control as live action, live read-only projection, static visual context, explicitly excluded, or blocked.

Milestone 7: resolve or explicitly exclude broad source picker/local path/browser file bytes, real connector/destination dispatch, provider/public URL use, RAG/vector/semantic retrieval breadth, hidden LLM planning, auth/security, and browser persistence.

Milestone 8: run a full-program readiness audit after all critical controls are current-main synced.

Milestone 9: run one representative source-to-package-handoff/export browser/API proof with isolated runtime state.

Milestone 10: declare full mockup activation only after every critical mockup operator journey is live, read-only, explicitly excluded, or blocked with current-main evidence.

## Non-Admission Boundary

This freeze admits no runtime behavior, no rendered behavior, no backend behavior, no route/API/DTO/model/migration/service behavior change, no executable test behavior change, no production UI behavior change, no new write control, no material mutation, no typing mutation, no typing override, no plan, no execution, no package, no handoff/export dispatch, no connector/destination dispatch, no provider URL behavior, no source expansion, no caller path/directory/file-byte/URL/glob/recursive-flag support, no RAG/vector widening, no hidden LLM planning, no optional-tool runtime, no auth/security behavior, no browser-storage authority, no frontend-only durable authority, and no full mockup program activation.

## Validation Basis

Required validation for this freeze:

- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json`;
- `python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.

No API, runtime, or browser test is required for this freeze because it changes no runtime behavior, rendered UI behavior, route, dependency, session-summary field, executable test, or browser behavior.

## Next Posture

The next exact posture is `current_main_sync_mockup_sublayers_ab_live_state_projection_freeze_then_projection_proof`.

Do not implement the Sublayer 3A/3B projection until this freeze is current-main selected, review-cleared, and checker-backed.
