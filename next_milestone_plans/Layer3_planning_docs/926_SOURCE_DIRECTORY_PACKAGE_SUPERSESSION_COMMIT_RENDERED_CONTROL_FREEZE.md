# 926 - Source-Directory Package Supersession Commit Rendered Control Freeze

## Status

Status: no-runtime/no-rendered freeze for `source_directory_package_supersession_commit_rendered_control`.

Doc: `926_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_RENDERED_CONTROL_FREEZE.md`.

Predecessor current-main sync doc: `925_SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_CONTROL_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before freeze: `7c17530bd78f454567b519cb4b53ca75ce97aa19`.

Freeze branch: `codex/l3-package-commit-freeze`.

Selected target: `source_directory_package_supersession_commit_rendered_control`.

Selected target classification: `live_server_authoritative_action`.

Selected activation target class: `single_existing_rendered_control_extension`.

Selected rendered node: `/review/layer3 #package-supersession-commit-panel`.

Selected submit control: `/review/layer3 #package-supersession-commit-submit`.

Selected source authority: `State.sourceDirectoryPackageSupersessionPreview`.

Selected fallback authority: `State.packageSupersessionPreview`.

Selected replacement authority state: `State.replacementPackageSetAuthority`.

Selected commit route: `POST /api/v1/layer3/package/supersession/commit`.

Owner service: `backend/app/services/layer3_package_supersession_commit.py`.

Server runtime mode: `package_supersession_commit_entry`.

Selected implementation action after freeze sync: `implement_source_directory_package_supersession_commit_rendered_control_after_freeze_sync`.

Stop action if route/state contract is not adequate: `source_directory_package_supersession_commit_route_state_gap_freeze`.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Backend behavior introduced by this freeze: `false`.

Route/API/DTO/model/migration/service behavior introduced by this freeze: `false`.

Executable test behavior introduced by this freeze: `false`.

Production UI behavior introduced by this freeze: `false`.

Full mockup program activation selected now: `false`.

Implementation-entry allowed by this freeze alone: `false`.

## Canonical Source Of Truth

The canonical source of truth is current `project6-origin/main` at `7c17530bd78f454567b519cb4b53ca75ce97aa19`.

Current main has the source-directory package supersession preview rendered control, the source-directory replacement package-set authority rendered control, and the stale-response invalidation fix synced through doc `925`.

The current rendered commit boundary is still the existing package supersession commit panel:

- rendered node: `/review/layer3 #package-supersession-commit-panel`;
- submit control: `/review/layer3 #package-supersession-commit-submit`;
- existing source-directory source state: `State.sourceDirectoryPackageSupersessionPreview`;
- existing generic fallback state: `State.packageSupersessionPreview`;
- existing replacement authority state: `State.replacementPackageSetAuthority`;
- existing commit route: `POST /api/v1/layer3/package/supersession/commit`;
- owner service: `backend/app/services/layer3_package_supersession_commit.py`;
- server runtime mode: `package_supersession_commit_entry`.

Current main already has the downstream server route and service, but the rendered package supersession commit helpers still derive the commit source primarily from `packageSupersessionPreviewState()` / `State.packageSupersessionPreview`. The source-directory package lifecycle path now has a more specific preview authority in `State.sourceDirectoryPackageSupersessionPreview` plus durable replacement authority in `State.replacementPackageSetAuthority`.

This freeze therefore selects a source-directory-specific rendered commit control extension over the already-live lineage route. It does not admit implementation in this pass.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Is replacement package-set authority available before commit? | Yes. Doc `925` syncs the source-directory replacement package-set authority rendered control and its stale-response fix. |
| Is there an existing server route for commit? | Yes. The existing route is `POST /api/v1/layer3/package/supersession/commit`, owned by `backend/app/services/layer3_package_supersession_commit.py`. |
| Is the rendered commit path already source-directory-specific? | No. The current commit helpers still read the generic package supersession preview state first, so the next pass must prove source-directory source selection explicitly. |
| Does this freeze add runtime or rendered behavior? | No. It records a no-runtime/no-rendered implementation-entry target only. |
| Can full mockup activation be admitted now? | No. This selects one package lifecycle blocker. Connector/provider/source/RAG/auth coverage and final readiness audit remain blocked. |

## Future Implementation Contract

The future implementation may add one rendered control extension that:

- treats `State.sourceDirectoryPackageSupersessionPreview` as the source package preview authority when the operator is in the source-directory package lifecycle path;
- preserves `State.packageSupersessionPreview` only as the generic fallback path, with no ambiguous source mixing;
- derives replacement package-set authority only from `State.replacementPackageSetAuthority`;
- submits only to `POST /api/v1/layer3/package/supersession/commit`;
- uses operator decision `commit_package_supersession`;
- assembles request hashes and package arrays only from server-governed preview/replacement authority already present in response state;
- displays response-safe commit status, ids, hashes, package kind rows, disabled capability flags, deferred downstream locks, and redacted failure state;
- invalidates or blocks stale source-directory preview authority before submit; and
- keeps browser state transient and non-authoritative.

The future implementation must stop and write `source_directory_package_supersession_commit_route_state_gap_freeze` instead of widening scope if:

- the existing backend route cannot validate source-directory preview-derived fields;
- current browser/server response state cannot assemble `commit_basis_hash`, `downstream_dependency_hash`, or required source/replacement package fields from governed authority;
- shared rendered state would make generic and source-directory package commit paths ambiguous;
- the only available implementation would require caller-entered paths, URLs, replacement refs, payload bytes, browser-owned artifact data, package row mutation, package payload rewrite, connector dispatch, provider URL delivery, or frontend-only durable state.

## Required Future Proof

The future implementation must prove:

- focused static/page coverage for the source-directory package supersession commit rendered control;
- request assembly uses source-directory preview authority and replacement package-set authority, with generic fallback only where explicitly selected and unambiguous;
- request assembly excludes browser/operator path editing, raw URL entry, package payload bytes, replacement payload bytes, package row mutation, package payload rewrite, and frontend durable state;
- API/service behavior remains the existing `package_supersession_commit_entry` lineage write and does not mutate `L3OutputPackage`, write package payloads, create replacement output package rows, record artifact manifests, invalidate downstream delivery, re-deliver output, or dispatch connector/provider/destination work;
- stale preview hash, stale source package-set hash, stale replacement package-set hash, stale downstream dependency hash, stale commit basis hash, unsupported operator decision, forbidden fields, and ambiguous state fail closed;
- headless Chromium proof;
- headed Chromium proof;
- no console or page errors on the focused rendered path;
- no raw local path, raw package bytes, raw payload ref, provider URL, signed URL, connector destination, credential, browser-storage authority, frontend-only durable authority, or full mockup activation; and
- `python ./tools/l3-progress-check.py` remains authoritative for the freeze/proof chain.

## Non-Admission Boundary

This freeze admits no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior change, executable test behavior, production UI behavior, package replacement activation, source `L3OutputPackage` row mutation, source package payload write, source package payload rewrite, replacement output package namespace rows, replacement artifact manifest recording, downstream invalidation, re-delivery runtime, provider-public delivery/use, provider-private signed URL behavior, public proxy runtime, connector dispatch, destination write, `ConnectorRun`, `ConnectorRunTarget`, source expansion, RAG/vector/model/provider runtime, auth/security behavior, browser-storage authority, frontend-only durable authority, mockup-frame write controls beyond the selected future rendered control, or full mockup program activation.

## Next Posture

Next exact posture: `current_main_sync_source_directory_package_supersession_commit_rendered_control_freeze_then_implement_rendered_control`.

Do not implement the source-directory package supersession commit rendered control until this freeze is current-main synced and review-cleared.
