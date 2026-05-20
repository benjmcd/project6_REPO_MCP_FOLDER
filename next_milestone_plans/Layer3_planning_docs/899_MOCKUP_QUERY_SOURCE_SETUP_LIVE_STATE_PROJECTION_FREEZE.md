# 899 - Mockup Query Source Setup Live State Projection Freeze

## Status

Status: no-runtime/no-rendered implementation-entry freeze for `prove_mockup_query_source_setup_live_state_projection_without_runtime_widening`.

Freeze doc: `899_MOCKUP_QUERY_SOURCE_SETUP_LIVE_STATE_PROJECTION_FREEZE.md`.

Predecessor inventory doc: `898_MOCKUP_TO_LIVE_MAPPING_INVENTORY_AFTER_SUBLAYER3C_PROJECTION_SYNC.md`.

Current-main checkpoint before this freeze: `e0f644a4f5ea5a4844bd168e752cac126c4e493a`.

Selected activation mode: `single_mockup_screen_read_only_projection_freeze`.

Selected target: `mockup_query_source_setup_live_state_projection`.

Selected proof action: `prove_mockup_query_source_setup_live_state_projection_without_runtime_widening`.

Selected mockup surfaces: `/review/layer3 #mockup-fixture-scenario .mockup-fixture-query`, `/review/layer3 #mockup-userflow-board .mockup-userflow-prompt`, and `/review/layer3 .mockup-pre3a`.

Selected live state/control sources: `/review/layer3 #intent-band`, `/review/layer3 #intent-form`, `/review/layer3 #source-fieldset`, `/review/layer3 #source-intake-rendered-controls`, `/review/layer3 #source-directory-ingestion-rendered-controls`, `State.preflight`, `State.sourcePreview`, `State.materialPreview`, source-intake rendered control state, source-directory rendered control state, and `State.sessionSummary`.

Rendered surface decision: `extend_existing_mockup_query_source_frame_as_read_only_projection`.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Backend behavior introduced by this freeze: `false`.

Route/API/DTO/model/migration/service behavior introduced by this freeze: `false`.

Executable test behavior introduced by this freeze: `false`.

Single mockup screen read-only projection introduced by this freeze: `false`.

Single mockup screen server-authoritative activation introduced by this freeze: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed next: `false` until this freeze is current-main synced.

## Decision Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Is this a new action target? | No. This freeze selects a read-only projection over existing intent/source setup state. |
| Is there already server authority for the state? | Yes. Current routes expose preflight, source-preview, material-preview, source-intake, source-directory scan/status, and session summary state. |
| Should the mockup query/source frame own durable state? | No. Mockup surfaces remain target-state inputs only. The future projection may render existing response-safe state but must not persist frontend authority. |
| Should the future proof add source picker, upload, directory, URL, glob, or file-byte controls in the mockup frame? | No. Existing source-intake and source-directory controls remain separate live controls; broad source expansion remains blocked. |
| Is full mockup activation adequate now? | No. This freeze covers only the query/source setup mockup frame. Package/handoff/export, connector/provider, RAG/vector, auth/security, browser persistence, and final readiness proof remain separate. |

## Canonical Source Of Truth

The canonical source of truth for the future query/source setup projection is existing server-owned query/source setup state and already-rendered live controls:

- static mockup fixture selector: `/review/layer3 #mockup-fixture-scenario .mockup-fixture-query`;
- static mockup userflow selector: `/review/layer3 #mockup-userflow-board .mockup-userflow-prompt`;
- static mockup source-intent selector: `/review/layer3 .mockup-pre3a`;
- live intent surface: `/review/layer3 #intent-band`;
- live intent form: `/review/layer3 #intent-form`;
- live source fieldset: `/review/layer3 #source-fieldset`;
- live source-intake surface: `/review/layer3 #source-intake-rendered-controls`;
- live source-directory surface: `/review/layer3 #source-directory-ingestion-rendered-controls`;
- preflight route: `POST /api/v1/layer3/preflight`;
- source-preview route: `POST /api/v1/layer3/source-preview`;
- material-preview route: `POST /api/v1/layer3/material-preview`;
- source-intake upload route: `POST /api/v1/layer3/source/intake/upload`;
- source-intake inventory route: `GET /api/v1/layer3/source/intake/inventory`;
- source-intake preview route: `GET /api/v1/layer3/source/intake/{source_intake_record_id}/preview`;
- source-directory scan route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- source-directory status route: `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`;
- session route that may already populate projection context: `GET /api/v1/layer3/session/{session_id}`;
- workbench service owners: `backend/app/services/layer3_workbench.py::preflight`, `backend/app/services/layer3_workbench.py::source_preview`, `backend/app/services/layer3_workbench.py::material_preview`, and `backend/app/services/layer3_workbench.py::session_summary`;
- source-directory service owner: `backend/app/services/layer3_source_directory_ingestion.py`;
- rendered owner files: `backend/app/review_ui/static/layer3.html`, `backend/app/review_ui/static/layer3.js`, and `backend/app/review_ui/static/layer3.css`;
- static page contract tests: `backend/tests/test_layer3_page.py`;
- browser proof file: `e2e/layer3-workbench.spec.js`.

Mockup image labels, fixture prose, DOM labels, local storage, session storage, browser file inputs, and frontend-only state are not authority for projection activation.

## Route And State Contract

The future projection may read only state already available from existing workbench paths:

- `State.preflight`;
- `State.sourcePreview`;
- `State.materialPreview`;
- source-intake rendered control state returned by the existing source-intake upload, inventory, preview, and Gate B admission flow;
- source-directory rendered control state returned by the existing server-configured-directory scan/status flow;
- `State.sessionSummary`;
- `State.sessionSummary.pdf_location_projection` only as already-proved context, not as new PDF-location behavior;
- `State.sessionSummary.analysis_environment_projection` only as already-proved context, not as new analysis behavior.

The future projection must fail closed when those sources are missing. Empty state must render as unavailable, not loaded, or blocked. Empty state must not render as preflight success, source readiness, material readiness, Gate B admission, source-directory ingestion, package readiness, handoff/export readiness, connector readiness, provider readiness, RAG/vector readiness, or full mockup activation.

The future projection must not add route calls. It may only read state populated by existing controls or existing session refresh behavior.

## Durable Authority Contract

The durable authority owners for the future proof are existing rows and service responses only:

- `L3SourceIntakeRecord`;
- `L3SourceDirectoryIngestionBatch`;
- `L3SourceDirectoryIngestionFile`;
- `L3SelectionManifest`;
- `L3MaterialSnapshot`.

`preflight`, `source_preview`, and `material_preview` response state may render only as server response state. Source-intake and source-directory state may render only from existing durable records and response-safe summaries. Preview-only or in-memory state may render only as preview, pending, blocked, or unavailable state. The projection must not upgrade preview-only data into durable source ingestion, durable material admission, package readiness, or delivery readiness.

## Rendered Projection Contract

The future projection may extend only the static query/source mockup frame as a read-only projection over server-owned state.

The projection may show:

- normalized intent/preflight status;
- selected source-class status;
- source-preview status and source candidate counts;
- material-preview status and material candidate counts;
- source-intake inventory/preview availability as response-safe counts or state labels;
- source-directory batch/status availability as response-safe counts or state labels;
- fixed state-source labels;
- unavailable or blocked labels when server state is missing.

The projection must not render:

- buttons;
- inputs;
- forms;
- write controls;
- broad source-picker controls;
- caller paths;
- caller directories;
- browser file bytes;
- URL input;
- glob input;
- caller-selected recursive flags;
- raw local paths;
- raw payload refs;
- raw diagnostics refs;
- provider URLs;
- public URLs;
- signed URLs;
- connector run ids;
- destination ids;
- credentials;
- unredacted package/output refs beyond existing safe status labels.

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

- static page proof that the selected mockup query/source surfaces remain stable;
- static JS proof that the projection reads existing state only;
- browser proof that the projection renders available preflight/source/material setup state;
- browser proof that source-intake and source-directory state render only as response-safe status/count/readiness labels;
- browser proof that missing server state renders unavailable or not loaded;
- browser proof that no new buttons, inputs, forms, or write controls are added inside the mockup query/source frame;
- browser proof that the projection itself does not call preflight, source-preview, material-preview, source-intake, source-directory, Gate B, package, handoff, connector, provider, source expansion, RAG/vector, optional-tool, or auth/security routes;
- browser proof that no raw path, payload ref, provider URL, public URL, signed URL, connector id, destination id, credential, or browser file byte renders;
- browser proof that no browser storage key becomes authority for the projection;
- headed Chromium proof;
- headless Chromium proof;
- responsive no-horizontal-overflow proof;
- no console errors and no page errors;
- progress-check guard coverage for this exact freeze and the later projection proof.

## No-Go Surface

The future projection proof must not admit:

- new preflight submission controls in the mockup frame;
- new source-preview submission controls in the mockup frame;
- new material-preview submission controls in the mockup frame;
- new source-intake upload controls in the mockup frame;
- new source-directory scan/status controls in the mockup frame;
- new Gate B admission controls in the mockup frame;
- broad source picker;
- caller paths;
- caller directories;
- browser file bytes;
- URL input;
- glob input;
- caller-selected recursive flags;
- hidden LLM planning;
- package construction or package mutation;
- handoff/export dispatch;
- connector or destination dispatch;
- provider-private signed URL behavior;
- provider-public URL behavior;
- RAG/vector widening;
- optional-tool runtime;
- auth/security behavior change;
- browser-storage authority;
- frontend-only durable state;
- full mockup program activation.

## Immediate Milestone

Milestone 1: current-main sync this freeze, then prove `mockup_query_source_setup_live_state_projection` as a single mockup-screen read-only projection without runtime widening.

Exit criteria for the later proof:

- the selected mockup query/source frame renders read-only live-state labels from existing server state;
- the projection handles unavailable state fail-closed;
- the projection adds no actions and sends no side-effect requests;
- the projection leaks no raw path, payload ref, provider URL, connector/destination, credential, package/output payload, or browser-byte authority;
- headed and headless Chromium proof pass;
- no backend/API/model/migration/service/source/package/connector/provider/RAG/auth/browser-storage behavior changes occur;
- `python .\tools\l3-progress-check.py` passes.

## Mid-Term Milestones

Milestone 2: current-main sync the query/source setup projection proof.

Milestone 3: freeze, prove, and current-main sync a package/handoff/export live status projection or one exact rendered control extension without new delivery actions.

Milestone 4: re-run a full mockup-to-live coverage audit and classify every mockup frame/control as live action, live read-only projection, static visual context, explicitly excluded, or blocked.

## Long-Term Milestones

Milestone 5: for remaining action-capable gaps, choose one bounded server-authoritative action lane at a time with exact route, DTO, durable state, idempotency, stale-authority behavior, fail-closed behavior, static tests, backend tests, and headed/headless browser proof.

Milestone 6: resolve or explicitly exclude broad source picker/local path/browser file bytes, real connector/destination dispatch, provider/public URL use, RAG/vector/semantic retrieval breadth, hidden LLM planning, auth/security, and browser persistence.

Milestone 7: run a full-program readiness audit after all critical controls are current-main synced.

Milestone 8: run one representative source-to-package-handoff/export browser/API proof with isolated runtime state.

Milestone 9: declare full mockup activation only after every critical mockup operator journey is live, read-only, explicitly excluded, or blocked with current-main evidence.

## Non-Admission Boundary

This freeze admits no runtime behavior, no rendered behavior, no backend behavior, no route/API/DTO/model/migration/service behavior change, no executable test behavior change, no production UI behavior change, no new write control, no new preflight/source/material action, no source upload inside the mockup frame, no source-directory scan/status action inside the mockup frame, no Gate B admission action inside the mockup frame, no broad source picker, no source expansion, no caller path/directory/file-byte/URL/glob/recursive-flag support, no package mutation, no handoff/export dispatch, no connector/destination dispatch, no provider URL behavior, no RAG/vector widening, no hidden LLM planning, no optional-tool runtime, no auth/security behavior, no browser-storage authority, no frontend-only durable authority, and no full mockup program activation.

## Validation Basis

Required validation for this freeze:

- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json`;
- `python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.

No API, runtime, or browser test is required for this freeze because it changes no runtime behavior, rendered UI behavior, route, dependency, session-summary field, executable test, or browser behavior.

## Next Posture

Next exact posture: `current_main_sync_mockup_query_source_setup_live_state_projection_freeze_then_projection_proof`.

Do not implement the query/source setup projection until this freeze is current-main synced, review-cleared, and checker-backed.
