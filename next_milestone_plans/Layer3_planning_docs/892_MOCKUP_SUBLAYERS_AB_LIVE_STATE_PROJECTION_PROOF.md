# 892 - Mockup Sublayers AB Live State Projection Proof

## Status

Status: branch-local proof for `mockup_sublayers_ab_live_state_projection`.

Proof doc: `892_MOCKUP_SUBLAYERS_AB_LIVE_STATE_PROJECTION_PROOF.md`.

Predecessor sync doc: `891_MOCKUP_SUBLAYERS_AB_LIVE_STATE_PROJECTION_FREEZE_CURRENT_MAIN_SYNC.md`.

Proof branch: `codex/l3-sublayers-ab-projection-proof`.

Current-main checkpoint before this proof: `2605377bf64c935b2db3fd79e700932bacfb3d8f`.

Selected activation mode: `single_mockup_screen_read_only_projection`.

Selected target: `mockup_sublayers_ab_live_state_projection`.

Selected mockup surface: `/review/layer3` `#mockup-sublayers-ab-board`.

Rendered projection node: `/review/layer3` `#mockup-sublayers-ab-projection`.

Canonical existing state sources: `State.materialPreview`, `State.gateB`, `State.gateC`, `State.sessionSummary.authority_rail`, and `State.sessionSummary.sublayer_visualization`.

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

The proof adds a read-only live-state panel inside `#mockup-sublayers-ab-board`.

The panel reads only existing in-browser state already populated from server responses:

- `State.materialPreview`;
- `State.gateB`;
- `State.gateC`;
- `State.sessionSummary.authority_rail`;
- `State.sessionSummary.sublayer_visualization`.

The rendered projection reports:

- 3A material object count;
- 3B typing object count;
- Gate rail posture;
- modality bucket counts;
- fixed state-source labels.

The panel intentionally does not render candidate IDs, material snapshot IDs, local paths, payload refs, provider URLs, signed URLs, connector IDs, destination IDs, credentials, or browser file bytes.

## Proof Boundaries

This proof adds no:

- new route;
- new DTO;
- new backend service;
- new database model;
- new migration;
- new API behavior;
- material-preview call from the projection;
- Gate B decision call from the projection;
- Gate C preview call from the projection;
- Gate C override call from the projection;
- plan, execution, package, handoff, connector, provider, source expansion, optional-tool, RAG, vector, auth, or security behavior;
- browser-storage authority;
- write button, input, form, select, textarea, or link inside the projection.

Unavailable state fails closed with `data-projection-state="unavailable"` and the copy `Read-only server state projection pending`.

Available state uses `data-projection-state="available"` and `data-read-only="true"`.

## Validation

Validation performed on branch `codex/l3-sublayers-ab-projection-proof`:

- `node --check .\backend\app\review_ui\static\layer3.js` passed;
- `python -m pytest .\backend\tests\test_layer3_page.py -q` passed with `6 passed`;
- `npx playwright test e2e/layer3-workbench.spec.js --grep "Sublayers AB projection" --project=chromium` passed;
- `npx playwright test e2e/layer3-workbench.spec.js --grep "Sublayers AB projection" --project=chromium --headed` passed;
- `npx playwright test e2e/layer3-workbench.spec.js --grep "mockup workbench theme exposes" --project=chromium` passed.

The first attempted Playwright selector using a Windows path plus the exact title fragment failed with `No tests found`; the rerun used repo-relative `e2e/layer3-workbench.spec.js` and a stable grep fragment.

The headed proof initially surfaced an unrelated `favicon.ico` 404 console message; the focused test now routes that browser resource to `204` so the no-console-errors assertion is scoped to the page/projection behavior.

## Still Blocked

This proof does not admit:

- single mockup screen server-authoritative activation;
- new mockup board write controls;
- duplicate Gate B or Gate C actions;
- material mutation;
- typing mutation;
- typing override;
- plan preview or approval;
- execution selection or start;
- package construction or mutation;
- handoff/export dispatch;
- connector/destination dispatch;
- provider URL behavior;
- source expansion;
- caller path/directory/file-byte/URL/glob/recursive-flag support;
- RAG/vector widening;
- hidden LLM planning;
- optional-tool runtime;
- auth/security behavior;
- browser-storage authority;
- frontend-only durable authority;
- full mockup program activation.

## Next Posture

The next exact posture is `current_main_sync_mockup_sublayers_ab_live_state_projection_proof`.

Do not select Sublayer 3C, query/source setup, package/handoff/export projection, rendered control extension beyond this board, or full mockup program activation until this proof is merged and current-main synced.
