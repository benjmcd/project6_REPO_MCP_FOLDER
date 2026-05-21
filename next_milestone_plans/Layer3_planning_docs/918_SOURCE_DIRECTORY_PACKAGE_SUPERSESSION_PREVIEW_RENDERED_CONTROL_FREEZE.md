# 918 - Source-Directory Package Supersession Preview Rendered Control Freeze

## Status

Status: no-runtime/no-rendered freeze for `source_directory_package_supersession_preview_rendered_control`.

Doc: `918_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RENDERED_CONTROL_FREEZE.md`.

Predecessor selection doc: `917_FULL_MOCKUP_ACTIVATION_NEXT_BLOCKER_SELECTION.md`.

Current-main checkpoint before freeze: `b6ba2a45c8075e8d5305974231b7baa53ffaa820`.

Freeze branch: `codex/l3-package-preview-freeze`.

Selected target: `source_directory_package_supersession_preview_rendered_control`.

Selected target classification: `live_server_authoritative_action`.

Selected implementation action after freeze sync: `implement_source_directory_package_supersession_preview_rendered_control_after_freeze_sync`.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Backend behavior introduced by this freeze: `false`.

Route/API/DTO/model/migration/service behavior introduced by this freeze: `false`.

Executable test behavior introduced by this freeze: `false`.

Production UI behavior introduced by this freeze: `false`.

Full mockup program activation selected now: `false`.

Implementation-entry allowed by this freeze alone: `false`.

## Canonical Source Of Truth

The canonical source of truth is current `project6-origin/main` at `b6ba2a45c8075e8d5305974231b7baa53ffaa820`.

The target route already exists on current main:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/preview`

The target route is governed by current-main Docs `820_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RUNTIME_ENTRY_FREEZE.md` and `821_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RUNTIME_CURRENT_MAIN_SYNC.md`.

The response authority is:

- schema `layer3.source_directory_qualitative_analysis_package_supersession_preview.v1`;
- mode `source_directory_qualitative_analysis_package_supersession_preview_authority`;
- required upstream source-directory qualitative-analysis package construction and approved package-review submit authority;
- server recomputation of qualitative-analysis authority, package-review preview authority, package construction basis, approved submit state, package ids, package kinds, and payload hashes; and
- redacted source package-set and downstream dependency hashes.

The current rendered workbench already has a generic package supersession preview panel and state object, but it posts to `/package/mutation/preview`. This freeze selects a future rendered control extension over the source-directory-specific supersession preview route, not a generic package mutation widening.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Is there current-main server authority for this target? | Yes. Docs `820` and `821` current-main sync the source-directory package supersession preview route and response authority. |
| Is this a broad package mutation admission? | No. The selected route is a read-only preview over existing source-directory package authority. It does not persist a preview row, mutate package rows, write payloads, create replacement authority, or commit supersession. |
| Is there an existing rendered surface to extend? | Yes. `/review/layer3` already has package supersession preview state and panel wiring, but the future extension must target the source-directory-specific route only when source-directory package authority is present. |
| Does this freeze allow implementation now? | No. It names the target and future proof contract only; implementation follows only after this freeze is current-main synced. |
| Does this advance full mockup activation? | Yes. It turns the package blocker from a broad family into one exact server-authoritative target, which is required before any full-program activation audit can mark package lifecycle behavior live, read-only, excluded, or blocked. |

## Future Implementation Contract

The future implementation may add one rendered control extension that:

- renders source-directory package supersession preview readiness in `/review/layer3`;
- posts only to `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/preview`;
- uses current server-owned source-directory qualitative-analysis package construction and approved package-review submit state;
- stores returned state only in a bounded rendered response object, expected to be `State.sourceDirectoryPackageSupersessionPreview` or an equivalently named source-directory-specific state owner;
- displays only redacted package-set hashes, downstream dependency hashes, bounded state labels, and server-returned non-sensitive summaries;
- fails closed when source-directory package construction or approved package-review submit authority is absent or stale; and
- preserves the existing generic `/package/mutation/preview` behavior unless a later freeze explicitly changes it.

The future implementation must prove:

- focused static/page coverage for the source-directory supersession preview rendered control;
- focused API or service coverage proving the source-directory preview remains read-only and fails closed on stale package-set input;
- headed Chromium proof;
- headless Chromium proof;
- no console or page errors on the focused rendered path;
- no raw local path, raw payload ref, package bytes, package payload write, replacement payload, provider URL, signed URL, connector destination, credential, browser byte, browser-storage authority, frontend-only durable authority, or full mockup activation; and
- `python ./tools/l3-progress-check.py` remains authoritative for the freeze/proof chain.

## Non-Admission Boundary

This freeze admits no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior change, executable test behavior, production UI behavior, replacement package-set authority, replacement artifact materialization, package supersession commit, package replacement activation, source `L3OutputPackage` row mutation, package payload write, package payload rewrite, source package row mutation, connector dispatch, destination write, `ConnectorRun`, `ConnectorRunTarget`, provider-public delivery, provider-private signed URL behavior, public proxy runtime, source expansion, RAG/vector/model/provider runtime, auth/security behavior, browser-storage authority, frontend-only durable authority, mockup-frame write controls beyond the selected future rendered control, or full mockup program activation.

## Next Posture

Next exact posture: `current_main_sync_source_directory_package_supersession_preview_rendered_control_freeze_then_implement_rendered_control`.

Do not implement the source-directory package supersession preview rendered control until this freeze is current-main synced and review-cleared.
