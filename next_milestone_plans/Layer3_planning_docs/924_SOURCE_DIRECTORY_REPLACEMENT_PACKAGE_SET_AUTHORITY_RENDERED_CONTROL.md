# 924 - Source-Directory Replacement Package-Set Authority Rendered Control

## Status

Status: implementation proof for `source_directory_replacement_package_set_authority_rendered_control` with follow-up stale-response review fix.

Doc: `924_SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_CONTROL.md`.

Predecessor sync doc: `923_SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_CONTROL_FREEZE_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before implementation: `6228a3a0aad41fc53be1a65e958beb52fc11bfe8`.

Implementation branch: `codex/l3-replacement-set-control`.

Implementation PR: `#1539`.

Implementation commit: `655a76563db041d523e29a4f047d9c3666f460e4`.

Implementation merge commit: `7116ed4eca19109dc972580c53a2900d6feea347`.

Review-fix branch: `codex/l3-replacement-set-current-main-sync`.

Review-fix PR: `#1540`.

Review-fix commit: `c0ae6c43176b43cce0238d5281723f2ec2cc1a5f`.

Review-fix merge commit: `0d873c11c325600dff4b08dbe6a2f14ad95a9c74`.

Selected target: `source_directory_replacement_package_set_authority_rendered_control`.

Selected rendered node: `/review/layer3 #replacement-package-set-authority-panel`.

Selected source authority: `State.sourceDirectoryPackageSupersessionPreview`.

Selected fallback authority: `State.packageSupersessionPreview`.

Selected materialization state: `State.replacementPackageArtifactMaterialization`.

Selected replacement authority state: `State.replacementPackageSetAuthority`.

Selected materialization route: `POST /api/v1/layer3/package/replacement-artifact/materialize`.

Selected replacement authority route: `POST /api/v1/layer3/package/replacement-set/record`.

## Implemented Scope

PR `#1539` implements the Doc `922` and Doc `923` selected rendered-control extension over the existing replacement package artifact materialization and replacement package-set authority routes.

The control now:

- prefers `State.sourceDirectoryPackageSupersessionPreview` when present;
- falls back to `State.packageSupersessionPreview` for the existing generic path;
- derives `source_package_set_hash` from `source_package_set_hash || package_set_hash`;
- renders selected source authority and selected source mode in the replacement package-set panel;
- submits only to `POST /api/v1/layer3/package/replacement-artifact/materialize` and `POST /api/v1/layer3/package/replacement-set/record`;
- clears downstream replacement, package supersession commit, artifact manifest, namespace, handoff, connector, provider, and export state when replacement authority changes; and
- preserves the server-owned backend route/service contracts without route, DTO, model, migration, or service changes.

PR `#1540` retires the post-merge review finding from PR `#1539` by adding request-token invalidation for in-flight source-directory package supersession preview responses. A late source-directory preview response is ignored after the source authority is cleared or changed, so replacement materialization cannot record from stale preview state.

## Review Surface

PR `#1539` review state was not empty after merge:

- review state: `COMMENTED`;
- reviewThreads totalCount: `1`;
- unresolved reviewThreads totalCount: `1`;
- finding: stale source-directory preview response could repopulate `State.sourceDirectoryPackageSupersessionPreview` after generic preview/source authority changes.

PR `#1540` review state before merge:

- comments: `0`;
- reviews: `0`;
- latestReviews: `0`;
- reviewThreads totalCount: `0`.

## Files Changed

PR `#1539` changed:

- `backend/app/review_ui/static/layer3.js`;
- `backend/tests/test_layer3_page.py`;
- `e2e/layer3-workbench.spec.js`.

PR `#1540` changed the same three files to add stale-response invalidation and proof coverage.

## Proof Coverage

Static/page proof verifies:

- source-directory preview response authority is tracked through a request token;
- source-directory preview clears invalidate in-flight source responses;
- stale responses are ignored before they can repopulate `State.sourceDirectoryPackageSupersessionPreview`;
- replacement package-set authority still prefers valid source-directory preview state over generic preview state;
- replacement package-set authority remains disabled during pending source preview state;
- selected source authority and source mode render in the replacement package-set panel; and
- no browser storage, provider URL, connector destination, package supersession commit, or frontend-only durable authority is introduced.

Browser proof verifies:

- source-directory preview can drive replacement package-set authority end to end;
- stale source-directory preview responses do not render previewed state after authority input changes;
- stale source-directory preview responses do not expose the stale source package-set hash;
- replacement package-set authority submit remains disabled after stale response invalidation; and
- headless and headed Chromium produce the same result for the original journey and the stale-response regression.

## Validation

Implementation validation for PR `#1539`:

- `node --check .\backend\app\review_ui\static\layer3.js` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_page.py -q` - `PASS`, `13 passed, 3 warnings`;
- focused Layer 3 API/source-directory pytest set - `PASS`, `5 passed, 3 warnings`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "source-directory preview state"` - `PASS`, `1 passed`;
- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "source-directory preview state" --headed` - `PASS`, `1 passed`;
- full `e2e/layer3-workbench.spec.js` headless Chromium - `PASS`, `48 passed`;
- full `e2e/layer3-workbench.spec.js` headed Chromium - `PASS`, `48 passed`.

Review-fix validation for PR `#1540`:

- `node --check .\backend\app\review_ui\static\layer3.js` - `PASS`;
- `python -m pytest .\backend\tests\test_layer3_page.py::test_layer3_source_directory_replacement_package_set_authority_control_is_bounded .\backend\tests\test_layer3_page.py::test_layer3_source_directory_package_supersession_preview_control_is_bounded -q` - `PASS`, `2 passed, 3 warnings`;
- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "stale source-directory"` - `PASS`, `1 passed`;
- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "stale source-directory" --headed` - `PASS`, `1 passed`;
- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "source-directory preview state"` - `PASS`, `1 passed`;
- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "source-directory preview state" --headed` - `PASS`, `1 passed`;
- `git diff --check` - `PASS`.

Post-merge validation after PR `#1540`:

- `python .\tools\l3-progress-check.py` - `PASS`.

## Explicit Behavior Classification

Runtime behavior introduced by this implementation: `false`.

Rendered behavior introduced by this implementation: `true`.

Backend behavior introduced by this implementation: `false`.

Route/API/DTO/model/migration/service behavior introduced by this implementation: `false`.

Executable test behavior introduced by this implementation: `true`.

Production UI behavior introduced by this implementation: `true`.

Server-authoritative full mockup activation introduced by this implementation: `false`.

Frontend-only durable authority enabled: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed for full mockup activation by this implementation alone: `false`.

## Still Blocked

Still blocked after this implementation and review fix:

- full mockup program activation;
- package supersession commit source-directory rendered authority;
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
| Did PR `#1539` have an unresolved review finding? | Yes. It had one COMMENTED review thread after merge, and this doc records that rather than treating the surface as clean. |
| Did PR `#1540` retire that finding? | Yes. It invalidates in-flight source-directory preview responses before stale responses can become replacement authority, with static and headed/headless browser proof. |
| Did the fix widen backend or route authority? | No. It changes frontend request-state handling and tests only. |
| Is replacement package-set authority now current-main rendered behavior? | Yes, after PR `#1539`, with the stale-response guard from PR `#1540`. |
| What must happen next? | Current-main sync of this implementation and review fix, then selection of the next exact blocker-retirement lane from live evidence. |

## Next Posture

Next exact posture: `current_main_sync_source_directory_replacement_package_set_authority_rendered_control_after_review_fix`.
