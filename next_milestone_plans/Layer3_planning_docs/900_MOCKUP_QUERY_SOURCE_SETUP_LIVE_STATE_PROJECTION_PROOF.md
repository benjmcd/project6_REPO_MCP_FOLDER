# 900 - Mockup Query Source Setup Live State Projection Proof

## Status

Status: branch-local proof for `mockup_query_source_setup_live_state_projection`.

Proof doc: `900_MOCKUP_QUERY_SOURCE_SETUP_LIVE_STATE_PROJECTION_PROOF.md`.

Predecessor freeze doc: `899_MOCKUP_QUERY_SOURCE_SETUP_LIVE_STATE_PROJECTION_FREEZE.md`.

Proof branch: `codex/l3-query-source-projection`.

Current-main checkpoint before this proof: `18721e36d78044166db6e50ceb31dff170dfdb86`.

Selected activation mode: `single_mockup_screen_read_only_projection`.

Selected target: `mockup_query_source_setup_live_state_projection`.

Selected mockup surfaces: `/review/layer3 #mockup-fixture-scenario .mockup-fixture-query`, `/review/layer3 #mockup-userflow-board .mockup-userflow-prompt`, and `/review/layer3 .mockup-pre3a`.

Rendered projection node: `/review/layer3 #mockup-query-source-setup-projection`.

Canonical existing state/control sources: `State.preflight`, `State.sourcePreview`, `State.materialPreview`, source-intake rendered control state, source-directory rendered control state, and `State.sessionSummary`.

Runtime behavior introduced by this proof: `false`.

Rendered behavior introduced by this proof: `true`.

Backend behavior introduced by this proof: `false`.

Route/API/DTO/model/migration/service behavior introduced by this proof: `false`.

Executable test behavior introduced by this proof: `true`.

Single mockup screen read-only projection introduced by this proof: `true`.

Single mockup screen server-authoritative activation introduced by this proof: `false`.

Full mockup program activation introduced by this proof: `false`.

Implementation-entry allowed next: `false` until this proof is current-main synced.

## Implemented Projection

The proof adds a read-only live-state panel at `#mockup-query-source-setup-projection` inside the existing mockup query/source setup frame.

The panel reads only existing in-browser state already populated from server responses and rendered live controls:

- `State.preflight`;
- `State.sourcePreview`;
- `State.materialPreview`;
- source-intake rendered control state from the existing source-intake panel;
- source-directory rendered control state from the existing source-directory panel;
- `State.sessionSummary`.

The rendered projection reports:

- preflight availability and selected source-class labels;
- source-preview response-safe candidate count;
- material-preview response-safe candidate count;
- source-intake response-safe inventory or preview count/status;
- source-directory response-safe batch/file count/status;
- fixed state-source labels for preflight, source-preview, material-preview, source-intake, source-directory, and session-summary state.

The panel intentionally does not render raw local paths, raw payload refs, local file refs, provider URLs, public URLs, signed URLs, connector run IDs, destination IDs, provider credentials, browser file bytes, vector store state, optional-tool state, browser-storage authority, or frontend-only durable authority.

## Proof Boundaries

This proof adds no:

- new backend route;
- new DTO;
- new backend service;
- new database model;
- new migration;
- new API behavior;
- preflight call from the projection;
- source-preview call from the projection;
- material-preview call from the projection;
- source-intake upload, inventory, preview, or Gate B call from the projection;
- source-directory scan or status call from the projection;
- package, handoff, connector, provider, source expansion, optional-tool, RAG, vector, auth, or security behavior;
- browser-storage authority;
- write button, input, form, select, textarea, or link inside the projection.

Unavailable state fails closed with `data-projection-state="unavailable"` and the copy `Read-only query/source setup projection pending`.

Available state uses `data-projection-state="available"`, `data-query-source-projection-state="available"`, and `data-query-source-projection-read-only="true"`.

## Validation

Validation performed on branch `codex/l3-query-source-projection`:

- `node --check .\backend\app\review_ui\static\layer3.js` passed;
- `python -m pytest .\backend\tests\test_layer3_page.py -q` passed with `8 passed`;
- `npx playwright test .\e2e\layer3-workbench.spec.js --grep "query/source setup projection" --project=chromium` passed;
- `npx playwright test .\e2e\layer3-workbench.spec.js --grep "query/source setup projection" --project=chromium --headed` passed;
- `npx playwright test .\e2e\layer3-workbench.spec.js --grep "visual diff harness" --project=chromium` passed;
- in-app browser check at `/review/layer3` with the Mockup Workbench theme showed the projection visible, fail-closed as unavailable before server state is loaded, and browser warning/error logs empty.

## Still Blocked

This proof does not admit:

- single mockup screen server-authoritative activation;
- new mockup query/source write controls;
- preflight controls in the mockup frame;
- source-preview controls in the mockup frame;
- material-preview controls in the mockup frame;
- source-intake upload controls in the mockup frame;
- source-directory scan/status controls in the mockup frame;
- Gate B admission controls in the mockup frame;
- broad source picker;
- caller path, caller directory, browser file byte, URL, glob, or recursive flag support;
- package construction or mutation;
- handoff/export dispatch;
- connector/destination dispatch;
- provider URL behavior;
- source expansion;
- RAG/vector widening;
- hidden LLM planning;
- optional-tool runtime;
- auth/security behavior;
- browser-storage authority;
- frontend-only durable authority;
- full mockup program activation.

## Next Posture

The next exact posture is `current_main_sync_mockup_query_source_setup_live_state_projection_proof`.

Do not select package/handoff/export projection, rendered control extension beyond this frame, query/source setup server-authoritative activation, or full mockup program activation until this proof is merged and current-main synced.
