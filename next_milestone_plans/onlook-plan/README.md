# Onlook Plan Index

## Purpose
This folder contains the bounded planning set for one specific question:

- whether and how Onlook can be used for this repo without changing the current live static review UI by default
- how to create a separate frontend lane that Onlook can edit safely
- how later promotion back into repo authority should be controlled

This folder is not a claim that Onlook is already integrated.
It is the decision packet for an isolated Onlook pilot lane.

## Status
This folder is repo-local planning material on branch `codex/onlook-next`.

It is intended to guide a new isolated frontend lane from clean mainline.
It does not replace live implementation authority.

Current lane state:

- the planning packet is committed
- the sandbox app has been scaffolded at `onlook-ui/`
- the first bounded shell slice is implemented inside `onlook-ui/*`
- the sandbox shell now loads `/runs` and `/runs/{run_id}/overview` through the existing review API seam
- the app now includes a committed `onlook-ui/.env.example` as the reproducible frontend env template
- actual Onlook use now assumes a local ignored `onlook-ui/.env.local` for the frontend API base
- the repo-local backend startup helper is `tools/start-review-api.ps1`
- the canonical local Onlook operator and debug surface for this lane is the source clone at `ext-onlook/` in this worktree, last verified at revision `a242be584fa9c71ca5be9e5e7a2640595c4200be`
- a same-revision sibling clone may still exist at `../onlook-lane/ext-onlook/`, but it is not the canonical debug surface for this lane
- the repo-local Onlook web startup helper is `tools/start-onlook-web.ps1`, but the direct Bun launch path on port `3007` is the currently proven reproduction path for the project-route blocker
- canonical local Onlook env files now exist at:
  - `ext-onlook/apps/web/client/.env`
  - `ext-onlook/packages/db/.env`
- local source Onlook now boots through the current proven direct launch path at `http://127.0.0.1:3007/login`
- local source Onlook dev login has been validated through the seeded demo-user flow
- with a real `CSB_API_KEY`, actual project import and sandbox creation inside local source Onlook are now validated through the current CodeSandbox-backed flow
- the imported `onlook-ui` project now reaches the Onlook project route and editor shell, but not editor readiness
- the first current blocking chain is at the preview boundary: the CodeSandbox-backed preview iframe does not become a usable app document, the bridge never becomes ready, and the editor surfaces bridge/theme errors instead of reaching stable edit interactions
- a temporary minimal `Next.js + TailwindCSS` control app outside tracked repo content reproduces the same preview and bridge failure under the same local Onlook runtime, which materially weakens `onlook-ui` as the cause of the current first failure
- same-runtime repros for both `onlook-ui` and the minimal control app reach the project route and editor shell before failing at the preview boundary, and neither repro reached preview-side requests to `127.0.0.1:8000` before that failure
- archived current-lane evidence also shows a separate route-init crash path inside Onlook filesystem and branch initialization, including `IDBFactory is not defined` and `Invalid value used as weak map key`, which may explain historical hard exits after route open
- no live static review UI files have been modified as part of this lane

## Canonical Authority
For the current shipped review UI and review API behavior, authority remains:

- `backend/main.py`
- `backend/app/api/review_nrc_aps.py`
- `backend/app/schemas/review_nrc_aps.py`
- `backend/app/review_ui/static/*`

For the current UI platform boundary, authority also includes:

- `frontend_UI_plans/README.md`
- `frontend_UI_plans/nrc_aps_review_ui_dependency_and_asset_strategy.md`

Those files confirm that the current shipped review UI is a build-free static surface served by FastAPI and should not be reinterpreted as an existing React frontend.

## Current Top-Level Determinations
1. The current shipped review UI should remain untouched by default.
2. Onlook should not be treated as an in-place editor for `backend/app/review_ui/static/*`.
3. If Onlook is used here, it should be used against a separate frontend sandbox app in a clean mainline-based worktree.
4. The backend review API should remain the first integration seam.
5. The narrowest supported target shape for the sandbox app is `Next.js + TailwindCSS`.
6. Slice 1 should use client-side, non-credentialed browser fetches only.
7. The adopted demo runtime is a local cross-worktree dependency, not a repo-native sandbox fixture.
8. The default promotion posture should be `sandbox-first`, not immediate replacement of the live UI.
9. Promotion into live authority should happen only after explicit parity and acceptance checks.

## Documents In This Folder
- `strategy.md`
  - source-of-truth hierarchy
  - verified repo fit
  - external Onlook fit
  - recommended sandbox model
- `pilot-plan.md`
  - exact lane shape
  - folder layout recommendation
  - before/during/after operating rules
  - validation and promotion gates
- `impl-plan.md`
  - exact sandbox scaffold choice
  - exact backend connection rule
  - exact adopted demo runtime/data context
  - exact runtime preflight and path-resolution rules
  - exact first-slice component map
  - exact validation commands

## Explicit Non-Claims
This packet does not claim:

- that the hosted desktop OAuth path is reliable here
- that the current static review UI can safely support Onlook write-back
- that the current root checkout is the correct place to run this lane
- that self-hosted production Onlook has been tested in this workspace
- that direct local write-back, editor readiness, or full Onlook AI/chat features are validated here beyond import, sandbox creation, project-route reachability, and editor-shell render
- that a final promotion model has already been approved

## Next Step
Use `strategy.md` as the settled authority and boundary model for this lane, and use `impl-plan.md` as the checklist for resolving the current preview and editor blocker before the first write-back proof.

Use `pilot-plan.md` and `impl-plan.md` together to move from the validated sandbox shell into actual Onlook targeting or the next bounded UI slice without changing the current live static review UI.
