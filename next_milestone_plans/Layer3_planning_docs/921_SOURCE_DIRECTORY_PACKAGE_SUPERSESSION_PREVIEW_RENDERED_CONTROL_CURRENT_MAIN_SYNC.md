# 921 - Source-Directory Package Supersession Preview Rendered Control Current-Main Sync

## Status

Status: current-main sync for `source_directory_package_supersession_preview_rendered_control`.

Doc: `921_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RENDERED_CONTROL_CURRENT_MAIN_SYNC.md`.

Predecessor implementation doc: `920_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RENDERED_CONTROL.md`.

Merged PR: `#1535`.

Source branch: `codex/l3-package-preview-control`.

Implementation commit: `cb0c4aebd4757f10b51966213fb3c2deedc34cf0`.

Merge commit: `5b2310cfefc3bb597d872495149f49283e2787a9`.

Sync branch: `codex/l3-package-preview-control-sync`.

Base authority: `project6-origin/main` at `5b2310cfefc3bb597d872495149f49283e2787a9`.

Synced target: `source_directory_package_supersession_preview_rendered_control`.

Synced rendered node: `/review/layer3 #source-directory-package-supersession-preview-panel`.

Synced request authority input: `/review/layer3 #source-directory-package-supersession-preview-authority`.

Synced submit control: `/review/layer3 #source-directory-package-supersession-preview-submit`.

Synced route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/preview`.

Synced schema: `layer3.source_directory_qualitative_analysis_package_supersession_preview.v1`.

Synced mode: `source_directory_qualitative_analysis_package_supersession_preview_authority`.

Synced state owner: `State.sourceDirectoryPackageSupersessionPreview`.

Runtime behavior introduced by this sync: `false`.

Rendered behavior introduced by this sync: `false`.

Backend behavior introduced by this sync: `false`.

Route/API/DTO/model/migration/service behavior introduced by this sync: `false`.

Executable test behavior introduced by this sync: `false`.

Production UI behavior introduced by this sync: `false`.

Full mockup program activation selected now: `false`.

Implementation-entry allowed for full mockup activation by this sync alone: `false`.

## Current-Main Authority

PR `#1535` is current-main truth for the source-directory package supersession preview rendered control selected by Docs `918` and `919` and implemented by Doc `920`.

Current main now includes one rendered control extension that:

- renders the source-directory package supersession preview state in `/review/layer3`;
- derives a bounded request payload from server-derived source-directory package authority JSON;
- requires approved package-review submit authority;
- posts only to `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/preview`;
- stores returned state only in `State.sourceDirectoryPackageSupersessionPreview`;
- displays bounded ids, hashes, state labels, disabled capability flags, source package rows, and downstream dependency refs;
- fails closed when the server authority input is absent, malformed, stale, or not approved; and
- preserves the existing generic `/package/mutation/preview` rendered control and `State.packageSupersessionPreview`.

The canonical server-authority route, schema, and response mode remain:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/preview`;
- `layer3.source_directory_qualitative_analysis_package_supersession_preview.v1`;
- `source_directory_qualitative_analysis_package_supersession_preview_authority`.

## Merge Gate

PR `#1535` merged at merge commit `5b2310cfefc3bb597d872495149f49283e2787a9`.

Review/check state before merge:

- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- comments: `0`;
- reviews: `0`;
- latestReviews: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`;
- merge state before ready/merge: `CLEAN`.

## Validation

Branch-local implementation validation from Doc `920`:

- `node --check ./backend/app/review_ui/static/layer3.js` - `PASS`;
- `python -m pytest ./backend/tests/test_layer3_page.py::test_layer3_page_route_serves_workbench_shell ./backend/tests/test_layer3_page.py::test_layer3_static_assets_are_mounted ./backend/tests/test_layer3_page.py::test_layer3_source_directory_package_supersession_preview_control_is_bounded -q` - `PASS`, `3 passed, 3 warnings`;
- `python -m pytest ./backend/tests/test_layer3_source_directory_qualitative_analysis.py::test_source_directory_qualitative_analysis_handoff_export_prepare_records_bounded_authority -q` - `PASS`, `1 passed, 3 warnings`;
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "source-directory package supersession preview rendered control" --project=chromium` - `PASS`, `1 passed`;
- `npx playwright test ./e2e/layer3-workbench.spec.js -g "source-directory package supersession preview rendered control" --project=chromium --headed` - `PASS`, `1 passed`;
- `python ./tools/l3-progress-check.py` - `PASS`;
- `git diff --check` - `PASS`.

Current-main sync validation:

- `python -m json.tool ./next_milestone_plans/layer3_progress_manifest.json > $null` - `PASS`;
- `python -m json.tool ./next_milestone_plans/layer3_workbench_proof_manifest.json > $null` - `PASS`;
- `python -m py_compile ./tools/l3-progress-check.py` - `PASS`;
- `python ./tools/l3-progress-check.py` - `PASS`;
- `git diff --check` - `PASS`.

## Non-Admission Boundary

This sync introduces no new runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior, executable test behavior, production UI behavior, replacement package-set authority, replacement artifact materialization, package supersession commit, package replacement activation, source `L3OutputPackage` row mutation, package payload write, package payload rewrite, connector dispatch, destination write, provider-public delivery, provider-private signed URL behavior, public proxy runtime, source expansion, RAG/vector/model/provider runtime, optional-tool runtime, auth/security behavior, browser-storage authority, frontend-only durable authority, mockup-frame write controls beyond the selected rendered control, or full mockup program activation.

The synced rendered behavior remains one bounded source-directory-specific preview control over existing server authority.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Is Doc `920` now current-main truth? | Yes. PR `#1535` merged to `project6-origin/main` at `5b2310cfefc3bb597d872495149f49283e2787a9`. |
| Does this sync itself add behavior beyond PR `#1535`? | No. It is docs/progress/checker metadata only. |
| Is the generic package mutation preview preserved? | Yes. The synced control uses `State.sourceDirectoryPackageSupersessionPreview`; generic `/package/mutation/preview` remains separate. |
| Can full mockup activation be admitted now? | No. The package supersession preview blocker is narrowed, but replacement, commit, connector/provider/source/RAG/auth and final program audit blockers remain. |
| What comes next? | Select the next exact blocker-retirement lane from current-main evidence. |

## Next Posture

Next exact posture: `select_next_blocker_retirement_lane_after_source_directory_package_supersession_preview_rendered_control_current_main_sync`.
