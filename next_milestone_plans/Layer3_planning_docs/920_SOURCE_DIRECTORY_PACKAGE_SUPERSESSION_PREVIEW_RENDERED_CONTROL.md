# 920 - Source-Directory Package Supersession Preview Rendered Control

## Status

Status: branch-local implementation proof for `source_directory_package_supersession_preview_rendered_control`.

Doc: `920_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RENDERED_CONTROL.md`.

Predecessor sync doc: `919_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RENDERED_CONTROL_FREEZE_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before implementation: `d19b7ae31f360b62bbc6316d09c5d2ae1accc562`.

Implementation branch: `codex/l3-package-preview-control`.

Selected rendered target: `source_directory_package_supersession_preview_rendered_control`.

Selected rendered node: `/review/layer3 #source-directory-package-supersession-preview-panel`.

Selected request authority input: `/review/layer3 #source-directory-package-supersession-preview-authority`.

Selected submit control: `/review/layer3 #source-directory-package-supersession-preview-submit`.

Selected route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/preview`.

Selected schema: `layer3.source_directory_qualitative_analysis_package_supersession_preview.v1`.

Selected mode: `source_directory_qualitative_analysis_package_supersession_preview_authority`.

Selected state owner: `State.sourceDirectoryPackageSupersessionPreview`.

## Implemented Scope

This pass implements the Doc `918` and Doc `919` selected rendered control extension over the existing source-directory qualitative-analysis package supersession preview route.

The control:

- renders unavailable/fail-closed state until server-derived source-directory package authority JSON is provided;
- derives a bounded request payload from allowlisted authority fields only;
- requires `package_review_state` to be exactly `package_review_approved`;
- requires exactly three `output_package_ids`, `package_kinds`, and `payload_hashes`;
- forces `operator_decision` to `preview_source_directory_package_supersession`;
- posts only to the selected source-directory package supersession preview route;
- stores the response only in `State.sourceDirectoryPackageSupersessionPreview`;
- displays only bounded ids, hashes, state labels, disabled capability flags, source package rows, and downstream dependency refs; and
- preserves the existing generic `/package/mutation/preview` rendered control.

## Files Changed

- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.js`
- `backend/tests/test_layer3_page.py`
- `e2e/layer3-workbench.spec.js`
- `next_milestone_plans/Layer3_planning_docs/920_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RENDERED_CONTROL.md`
- progress board, progress prompt, refresh spec, manifests, and progress checker

## Proof Coverage

Static/page proof verifies:

- the rendered control node exists;
- `data-rendered-mode="rendered_source_directory_package_supersession_preview_control"`;
- `data-read-only="true"`;
- `data-frontend-durable-authority="false"`;
- the selected route constant is the source-directory package supersession preview route;
- `State.sourceDirectoryPackageSupersessionPreview` is the response authority;
- `sourceDirectoryPackageSupersessionPreviewPayload` allowlists only the selected source-directory package authority fields;
- package-review state must be approved;
- package id/kind/hash arrays must have exactly three entries; and
- request/submit slices do not introduce raw payload refs, local paths, URLs, provider credentials, browser storage, generic package mutation, package supersession commit, or replacement package routes.

API/service proof verifies current source-directory package supersession preview authority remains read-only, redacted, and fail-closed over stale package-set input.

Browser proof verifies:

- the submit control is disabled until server-derived authority JSON is provided;
- the rendered control transitions from unavailable to ready to previewed;
- the request payload contains only the selected fields;
- the request posts exactly once to the selected source-directory route;
- the rendered response uses `State.sourceDirectoryPackageSupersessionPreview`;
- schema, mode, source package-set hash, downstream dependency hash, approved submit state, and disabled capability flags render;
- no raw local path, raw payload ref, public URL, signed URL, connector destination, credential, browser-byte, or browser-storage authority is exposed;
- no generic package mutation, package supersession commit, replacement package, connector, provider URL, or source mixed-corpus materialization route is called;
- no console errors and no page errors are emitted; and
- no horizontal overflow is introduced.

## Validation

- `node --check ./backend/app/review_ui/static/layer3.js` passed.
- `python -m pytest ./backend/tests/test_layer3_page.py::test_layer3_page_route_serves_workbench_shell ./backend/tests/test_layer3_page.py::test_layer3_static_assets_are_mounted ./backend/tests/test_layer3_page.py::test_layer3_source_directory_package_supersession_preview_control_is_bounded -q` passed with `3 passed, 3 warnings`.
- `python -m pytest ./backend/tests/test_layer3_source_directory_qualitative_analysis.py::test_source_directory_qualitative_analysis_handoff_export_prepare_records_bounded_authority -q` passed with `1 passed, 3 warnings`.
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "source-directory package supersession preview rendered control" --project=chromium` passed with `1 passed`.
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "source-directory package supersession preview rendered control" --project=chromium --headed` passed with `1 passed`.

Headless/headed comparison result: no behavioral divergence observed; both runs passed the same fail-closed, ready, previewed, no-overflow, no-console-error, no-page-error, no-forbidden-route, and no-forbidden-data proof.

Focused headless Chromium proof passed for this rendered control.

Focused headed Chromium proof passed for this rendered control.

## Explicit Behavior Classification

Runtime behavior introduced by this implementation: `false`.

Rendered behavior introduced by this implementation: `true`.

Backend behavior introduced by this implementation: `false`.

Route/API/DTO/model/migration/service behavior introduced by this implementation: `false`.

Executable test behavior introduced by this implementation: `true`.

Production UI behavior introduced by this implementation: `true`.

Server-authoritative full mockup activation introduced by this implementation: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed for full mockup activation by this implementation alone: `false`.

## Still Blocked

Still blocked after this implementation:

- full mockup program activation;
- mockup-frame write controls without complete route/state/proof contracts;
- replacement package-set authority;
- replacement artifact materialization;
- package supersession commit;
- package replacement activation;
- source `L3OutputPackage` row mutation;
- package payload write/rewrite;
- connector dispatch and destination writes;
- provider-public delivery and provider-private signed URL behavior;
- source expansion beyond already admitted server-configured source-directory behavior;
- broad RAG/vector/model/provider runtime;
- optional-tool runtime;
- auth/security behavior;
- browser-storage authority; and
- frontend-only durable authority.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Did this change activate full mockup behavior? | No. It activates one rendered control extension over one existing server-authoritative preview route. |
| Did this change widen backend/runtime authority? | No. The selected backend route, request DTO, response schema, and tests already existed. |
| Did this change preserve the generic package preview control? | Yes. The existing `/package/mutation/preview` control and `State.packageSupersessionPreview` remain separate. |
| Does the browser become durable authority? | No. The panel is read-only/non-durable, and the request is derived from pasted server authority JSON. |
| What must happen next? | Current-main sync of this implementation after PR merge, then selection of the next exact blocker retirement lane from live evidence. |

## Next Posture

Next exact posture: `current_main_sync_source_directory_package_supersession_preview_rendered_control_then_select_next_blocker_retirement_lane`.
