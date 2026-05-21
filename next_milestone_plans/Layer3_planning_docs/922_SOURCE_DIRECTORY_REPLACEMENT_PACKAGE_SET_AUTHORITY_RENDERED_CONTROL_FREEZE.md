# 922 - Source-Directory Replacement Package-Set Authority Rendered Control Freeze

## Status

Status: no-runtime/no-rendered freeze for `source_directory_replacement_package_set_authority_rendered_control`.

Doc: `922_SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_CONTROL_FREEZE.md`.

Predecessor current-main sync doc: `921_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RENDERED_CONTROL_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before freeze: `6ab8a141ea2ab50d1c330a32edfa122086987aac`.

Freeze branch: `codex/l3-next-target-freeze`.

Selected target: `source_directory_replacement_package_set_authority_rendered_control`.

Selected target classification: `live_server_authoritative_action`.

Selected activation target class: `single_existing_rendered_control_extension`.

Selected implementation action after freeze sync: `implement_source_directory_replacement_package_set_authority_rendered_control_after_freeze_sync`.

Stop action if route/state contract is not adequate: `source_directory_replacement_package_set_authority_route_state_gap_freeze`.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Backend behavior introduced by this freeze: `false`.

Route/API/DTO/model/migration/service behavior introduced by this freeze: `false`.

Executable test behavior introduced by this freeze: `false`.

Production UI behavior introduced by this freeze: `false`.

Full mockup program activation selected now: `false`.

Implementation-entry allowed by this freeze alone: `false`.

## Canonical Source Of Truth

The canonical source of truth is current `project6-origin/main` at `6ab8a141ea2ab50d1c330a32edfa122086987aac`.

The current-main rendered/source-state boundary is:

- source-directory preview state: `State.sourceDirectoryPackageSupersessionPreview`;
- source-directory preview route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/preview`;
- source-directory preview schema: `layer3.source_directory_qualitative_analysis_package_supersession_preview.v1`;
- source-directory preview mode: `source_directory_qualitative_analysis_package_supersession_preview_authority`;
- generic replacement package-set rendered state: `State.replacementPackageSetAuthority`;
- generic replacement artifact materialization state: `State.replacementPackageArtifactMaterialization`;
- existing server-owned materialization route: `POST /api/v1/layer3/package/replacement-artifact/materialize`;
- existing durable replacement package-set route: `POST /api/v1/layer3/package/replacement-set/record`;
- owner services: `backend/app/services/layer3_replacement_package_materialization.py` and `backend/app/services/layer3_replacement_package_set_authority.py`.

Current main already has the downstream server routes and services, but the rendered replacement package-set control still gates and builds payloads from `State.packageSupersessionPreview`, not from `State.sourceDirectoryPackageSupersessionPreview`.

This freeze therefore selects a source-directory-specific rendered control extension that can bridge the already-rendered source-directory preview authority into the existing server-owned materialization and replacement package-set authority routes, without adding a backend route or widening package mutation.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Is there a real server authority target after the source-directory preview? | Yes. Current main exposes `POST /api/v1/layer3/package/replacement-artifact/materialize` and `POST /api/v1/layer3/package/replacement-set/record`, backed by `layer3_replacement_package_materialization.py` and `layer3_replacement_package_set_authority.py`. |
| Is the current rendered control already source-directory-aware? | No. `canSubmitReplacementPackageSetAuthority()`, `replacementPackageArtifactMaterializationPayload()`, `renderReplacementPackageSetAuthorityPanel()`, and `packageSupersessionCommitPayload()` currently read `packageSupersessionPreviewState()` / `State.packageSupersessionPreview`, while the source-directory preview lands in `State.sourceDirectoryPackageSupersessionPreview`. |
| Is this a backend/runtime expansion? | No for this freeze. The future implementation must use existing routes unless the route/state contract audit proves that the source-directory authority cannot be carried safely. |
| Does this admit full mockup activation? | No. It retires one package lifecycle blocker candidate only. Full activation remains blocked until the final matrix proves every critical mockup journey is live, read-only, intentionally excluded, or explicitly blocked. |
| Is package supersession commit the better immediate target? | No. Commit depends on replacement package-set authority. The next adequate target is the replacement package-set authority bridge, then commit can be reconsidered. |

## Future Implementation Contract

The future implementation may add one rendered control extension that:

- treats `State.sourceDirectoryPackageSupersessionPreview` as the source package preview authority when the operator is in the source-directory package lifecycle path;
- materializes replacement package artifacts only through `POST /api/v1/layer3/package/replacement-artifact/materialize`;
- records replacement package-set authority only through `POST /api/v1/layer3/package/replacement-set/record`;
- uses operator decisions `materialize_replacement_package_artifacts_from_supersession_preview` and `record_replacement_package_set_authority`;
- stores server responses only in bounded rendered state, expected to remain `State.replacementPackageArtifactMaterialization` and `State.replacementPackageSetAuthority` if the implementation proves the shared downstream state is unambiguous;
- displays response-safe status, ids, hashes, kind lists, disabled capability flags, and redacted failure state;
- fails closed when source-directory preview authority, approved package review state, package-set hash, source package ids/kinds/refs/hashes, selected result authority, or replacement materialization authority is absent or stale; and
- preserves the generic package supersession preview and generic replacement package-set path unless a later freeze explicitly changes them.

The future implementation must stop and write `source_directory_replacement_package_set_authority_route_state_gap_freeze` instead of widening scope if:

- the existing backend routes cannot safely validate source-directory preview-derived fields;
- source-directory preview state lacks required materialization fields;
- shared `State.replacementPackageSetAuthority` would make the generic and source-directory package paths ambiguous;
- the only available implementation would require caller-entered paths, URLs, replacement refs, payload bytes, browser-owned artifact data, package row mutation, package payload rewrite, connector dispatch, provider URL delivery, or frontend-only durable state.

## Required Future Proof

The future implementation must prove:

- focused static/page coverage for the source-directory replacement package-set authority rendered control;
- request assembly uses source-directory preview authority and excludes browser/operator path editing, raw URL entry, payload bytes, package row mutation, and frontend durable state;
- API/service coverage for `POST /api/v1/layer3/package/replacement-artifact/materialize` and `POST /api/v1/layer3/package/replacement-set/record` using isolated runtime/artifact state;
- stale source package-set hash, stale payload hash, stale replacement package-set hash, stale authority basis hash, unsupported operator decision, forbidden fields, and ambiguous state fail closed;
- no source `L3OutputPackage` row mutation and no package payload rewrite;
- replacement artifact writes, if exercised, stay under server-owned artifact storage and expose only redacted refs in the rendered surface;
- headless Chromium proof;
- headed Chromium proof;
- no console or page errors on the focused rendered path;
- no raw local path, raw package bytes, raw payload ref, provider URL, signed URL, connector destination, credential, browser-storage authority, frontend-only durable authority, or full mockup activation; and
- `python ./tools/l3-progress-check.py` remains authoritative for the freeze/proof chain.

## Non-Admission Boundary

This freeze admits no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior change, executable test behavior, production UI behavior, package supersession commit, package replacement activation, source `L3OutputPackage` row mutation, source package payload write, source package payload rewrite, caller-entered replacement payload refs, browser-generated replacement artifacts, connector dispatch, destination write, `ConnectorRun`, `ConnectorRunTarget`, provider-public delivery, provider-private signed URL behavior, public proxy runtime, source expansion, RAG/vector/model/provider runtime, auth/security behavior, browser-storage authority, frontend-only durable authority, mockup-frame write controls beyond the selected future rendered control, or full mockup program activation.

## Next Posture

Next exact posture: `current_main_sync_source_directory_replacement_package_set_authority_rendered_control_freeze_then_implement_rendered_control`.

Do not implement the source-directory replacement package-set authority rendered control until this freeze is current-main synced and review-cleared.
