# 903 - Mockup Output Review Package Handoff Live State Projection Freeze

## Status

Status: no-runtime/no-rendered implementation-entry freeze for `prove_mockup_output_review_package_handoff_live_state_projection_without_runtime_widening`.

Freeze doc: `903_MOCKUP_OUTPUT_REVIEW_PACKAGE_HANDOFF_LIVE_STATE_PROJECTION_FREEZE.md`.

Predecessor inventory doc: `902_MOCKUP_TO_LIVE_MAPPING_INVENTORY_AFTER_QUERY_SOURCE_SETUP_PROJECTION_SYNC.md`.

Current-main checkpoint before this freeze: `f9aa40a39a0e7cb0b8add5a926c029a890a08083`.

Selected activation mode: `single_mockup_screen_read_only_projection_freeze`.

Selected target: `mockup_output_review_package_handoff_live_state_projection`.

Selected proof action: `prove_mockup_output_review_package_handoff_live_state_projection_without_runtime_widening`.

Selected mockup surfaces: `/review/layer3 #mockup-userflow-board .mockup-userflow-node[data-stage="output-review"]`, `/review/layer3 .mockup-flow-card.mockup-3c`, `/review/layer3 .mockup-output-grid`, and `/review/layer3 .mockup-output-card`.

Selected live state/control sources: `/review/layer3 #result-review-band`, `/review/layer3 #package-review-band`, `/review/layer3 #package-review-preview-panel`, `/review/layer3 #package-lifecycle-dashboard-panel`, `/review/layer3 #handoff-export-band`, `/review/layer3 #aps-handoff-band`, `/review/layer3 #external-export-download-band`, `/review/layer3 #downstream-access-lifecycle-dashboard-panel`, `State.resultStatus`, `State.resultReview`, `State.packageReviewPreview`, `State.packageConstruction`, `State.packageReviewSubmit`, `State.packageSupersessionPreview`, `State.replacementPackageSetAuthority`, `State.packageSupersessionCommit`, `State.replacementPackageArtifactManifest`, `State.replacementPackageNamespace`, `State.handoffExportPrepare`, `State.apsHandoffDispatch`, `State.externalExportDownloadPrepare`, `State.externalExportDownloadDelivery`, `State.externalExportDownloadSignedReference`, and `State.sessionSummary`.

Rendered surface decision: `extend_existing_mockup_output_review_package_handoff_frame_as_read_only_projection`.

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
| Is this a new action target? | No. This freeze selects a read-only projection over existing output/review/package/handoff/export state. |
| Is there already server authority for the state? | Yes. Current main already has result review, package review, package construction, package lifecycle, handoff/export, APS handoff, external export/download, signed-reference, and session-summary state. |
| Should the mockup output/review frame own package or handoff state? | No. Mockup surfaces remain target-state inputs only. The later projection may render response-safe status, counts, and state labels from existing server state but must not persist frontend authority. |
| Should the future proof add package/handoff/export controls inside the mockup frame? | No. Existing action controls remain in their current workbands; the mockup projection must be read-only. |
| Is full mockup activation adequate now? | No. This freeze covers only one read-only projection target. Provider, connector, source expansion, RAG/vector, auth/security, browser-storage, and final readiness proof remain separate. |

## Canonical Source Of Truth

The canonical source of truth for the future output/review/package/handoff projection is existing server-owned post-result state and already-rendered live controls:

- static mockup review selector: `/review/layer3 #mockup-userflow-board .mockup-userflow-node[data-stage="output-review"]`;
- static mockup output/provenance selector: `/review/layer3 .mockup-flow-card.mockup-3c`;
- static mockup output-card selector: `/review/layer3 .mockup-output-grid`;
- live result-review workband: `/review/layer3 #result-review-band`;
- live package-review workband: `/review/layer3 #package-review-band`;
- live package preview panel: `/review/layer3 #package-review-preview-panel`;
- live package lifecycle dashboard: `/review/layer3 #package-lifecycle-dashboard-panel`;
- live handoff/export workband: `/review/layer3 #handoff-export-band`;
- live APS handoff workband: `/review/layer3 #aps-handoff-band`;
- live external export/download workband: `/review/layer3 #external-export-download-band`;
- live downstream access dashboard: `/review/layer3 #downstream-access-lifecycle-dashboard-panel`;
- result status route: `POST /api/v1/layer3/execution/result/status`;
- result review route: `POST /api/v1/layer3/execution/result/review`;
- package preview route: `POST /api/v1/layer3/package/review/preview`;
- package construction route: `POST /api/v1/layer3/package/review/commit`;
- package review submit route: `POST /api/v1/layer3/package/review/submit`;
- package supersession preview route: `POST /api/v1/layer3/package/mutation/preview`;
- handoff/export prepare route: `POST /api/v1/layer3/handoff/export/prepare`;
- APS handoff dispatch route: `POST /api/v1/layer3/handoff/aps/dispatch`;
- external export/download prepare route: `POST /api/v1/layer3/handoff/export/download/prepare`;
- external export/download delivery route: `POST /api/v1/layer3/handoff/export/download/deliver`;
- external export/download signed-reference generation route: `POST /api/v1/layer3/handoff/export/download/signed-reference/generate`;
- session route that may already populate projection context: `GET /api/v1/layer3/session/{session_id}`;
- durable state owners: `L3PassRun`, `L3OutputPackage`, `L3ReconciliationRecord`, `L3ExternalExportDownloadRecord`, and `L3ExternalExportSignedReferenceToken`;
- rendered owner files: `backend/app/review_ui/static/layer3.html`, `backend/app/review_ui/static/layer3.js`, and `backend/app/review_ui/static/layer3.css`;
- static page contract tests: `backend/tests/test_layer3_page.py`;
- browser proof file: `e2e/layer3-workbench.spec.js`.

Mockup image labels, fixture prose, DOM labels, local storage, session storage, browser-side package state, and frontend-only state are not authority for projection activation.

## Route And State Contract

The future projection may read only state already available from existing workbench paths:

- `State.resultStatus`;
- `State.resultReview`;
- `State.packageReviewPreview`;
- `State.packageConstruction`;
- `State.packageReviewSubmit`;
- `State.packageSupersessionPreview`;
- `State.replacementPackageSetAuthority`;
- `State.packageSupersessionCommit`;
- `State.replacementPackageArtifactManifest`;
- `State.replacementPackageNamespace`;
- `State.handoffExportPrepare`;
- `State.apsHandoffDispatch`;
- `State.externalExportDownloadPrepare`;
- `State.externalExportDownloadDelivery`;
- `State.externalExportDownloadSignedReference`;
- `State.sessionSummary`;
- `State.sessionSummary.package_review_preview`;
- `State.sessionSummary.package_construction`;
- `State.sessionSummary.package_review_submit`;
- `State.sessionSummary.handoff_export_prepare`;
- `State.sessionSummary.aps_handoff_dispatch`;
- `State.sessionSummary.external_export_download`.

The future projection must fail closed when those sources are missing. Empty state must render as unavailable, not loaded, or blocked. Empty state must not render as package approval, package construction, handoff/export readiness, APS dispatch, external export/download readiness, signed-reference readiness, connector readiness, provider readiness, or full mockup activation.

The future projection must not add route calls. It may only read state populated by existing controls or existing session refresh behavior.

## Rendered Projection Contract

The future projection may extend only the static output/review/package/handoff mockup area as a read-only projection over server-owned state.

The projection may show:

- result-status and result-review state labels;
- package preview, package construction, package review submit, and package lifecycle labels;
- handoff/export prepare, APS handoff dispatch, external export/download, and signed-reference labels;
- downstream unavailable or blocked labels;
- response-safe counts of packages, package kinds, payload hashes, or output cards when already present in existing state;
- fixed state-source labels;
- unavailable or blocked labels when server state is missing.

The projection must not render buttons, inputs, forms, links, write controls, package payload text, raw payload refs, raw local paths, provider URLs, public URLs, signed URLs, connector run ids, destination ids, credentials, unredacted artifact refs beyond existing safe labels, browser file bytes, or browser-storage state.

## Required Future Write Scope

The later proof should be limited to:

- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.js`;
- `backend/app/review_ui/static/layer3.css`;
- `backend/tests/test_layer3_page.py`;
- `e2e/layer3-workbench.spec.js`;
- progress/proof docs and manifests needed to record the projection proof;
- `tools/l3-progress-check.py` guard terms for this freeze and the later proof.

No production backend route, DTO, model, migration, service, durable-state write path, source traversal, package mutation/reconstruction, connector, provider, RAG/vector, auth/security, or browser-storage behavior may change under this freeze.

## Required Future Proof

The future projection proof must show:

- static page proof that the selected mockup output/review surfaces remain stable;
- static JS proof that the projection reads existing state only;
- browser proof that result/package/handoff/export state renders as read-only labels;
- browser proof that missing server state renders unavailable or not loaded;
- browser proof that no new buttons, inputs, forms, links, or write controls are added inside the mockup output/review frame;
- browser proof that the projection itself does not call result, package, handoff, APS, external export/download, connector, provider, source expansion, RAG/vector, optional-tool, or auth/security routes;
- browser proof that no raw path, payload ref, artifact ref, provider URL, public URL, signed URL, connector id, destination id, credential, or browser file byte renders;
- browser proof that no browser storage key becomes authority for the projection;
- headed Chromium proof;
- headless Chromium proof;
- responsive no-horizontal-overflow proof;
- no console errors and no page errors;
- progress-check guard coverage for this exact freeze and the later projection proof.

## No-Go Surface

The future projection proof must not admit package/handoff/export buttons inside the mockup frame, result-review submission from the mockup frame, package-review submission from the mockup frame, package construction from the mockup frame, package mutation/reconstruction expansion, handoff/export submission from the mockup frame, APS handoff submission from the mockup frame, external export/download submission from the mockup frame, signed-reference generation/use from the mockup frame, connector or destination dispatch, provider-private signed URL behavior expansion, provider-public URL behavior, source expansion, RAG/vector widening, hidden LLM planning, optional-tool runtime, auth/security behavior change, browser-storage authority, frontend-only durable state, or full mockup program activation.

## Immediate Milestone

Milestone 1: current-main sync this freeze, then prove `mockup_output_review_package_handoff_live_state_projection` as a single mockup-screen read-only projection without runtime widening.

Exit criteria for the later proof:

- the selected mockup output/review frame renders read-only live-state labels from existing server state;
- the projection handles unavailable state fail-closed;
- the projection introduces no route calls, write controls, or storage authority;
- headed and headless browser proof passes;
- progress-check guard coverage passes.

Next exact posture: `current_main_sync_mockup_output_review_package_handoff_live_state_projection_freeze_then_projection_proof`.
