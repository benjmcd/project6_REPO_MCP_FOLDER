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
- the sandbox app now carries a committed compatibility fix that keeps React `19.2.4` but pins `next` and `eslint-config-next` to `15.5.15`
- the app now includes a committed `onlook-ui/.env.example` as the reproducible frontend env template
- actual Onlook use now assumes a local ignored `onlook-ui/.env.local` for the frontend API base
- the repo-local backend startup helper is `tools/start-review-api.ps1`
- the original clean upstream base reference for this lane is the source clone lineage rooted at `ext-onlook/`, last verified from upstream revision `a242be584fa9c71ca5be9e5e7a2640595c4200be`
- the current proven local operator and debug surface for the resolved repo lane is `ext-onlook-fix/` on local branch `codex/local-writeback-fix` at commit `c8cf5c16`
- the clean upstream packaging surface is `ext-onlook-pr/` on local branch `codex/upstream-clean` at commit `6d4c463a`
- the repo-local Onlook web startup helper is `tools/start-onlook-web.ps1`; it now defaults to `ext-onlook-fix/` on port `3000` and can be pointed at a different local clone with `-OnlookDir`
- canonical local Onlook env files for the proven local operator surface now exist at:
  - `ext-onlook-fix/apps/web/client/.env`
  - `ext-onlook-fix/packages/db/.env`
- local source Onlook now boots through the current proven direct launch path at `http://127.0.0.1:3000/login`
- local source Onlook dev login has been validated through the seeded demo-user flow
- with a real `CSB_API_KEY`, actual project import and sandbox creation inside local source Onlook are now validated through the current CodeSandbox-backed flow
- the earlier `Next 16` preview blocker is now resolved for this repo lane by the committed sandbox-app compatibility fix
- a fresh local Onlook import of the current `onlook-ui/` folder now creates a new sandbox preview that hydrates successfully
- direct preview of that fresh sandbox now logs the `review-shell` lifecycle, fetches `/runs` and `/runs/{run_id}/overview`, and loads the populated review shell
- the same fresh sandbox now renders the populated review shell inside the Onlook iframe and editor shell, not just in a top-level preview tab
- from a fresh browser profile, switching the canvas to `Preview` and accepting the CodeSandbox trust interstitial now loads the real sandbox app inside the Onlook iframe
- direct local write-back is now proven for this repo lane: a bounded Onlook-authored save wrote into `onlook-ui/app/page.tsx` on disk and the host file was restored clean afterward
- that local write-back proof ran on the preserved local operator surface at `ext-onlook-fix/` and used the file-input import path, so it should not be flattened into a claim that the clean extracted upstream branch has already re-proven host write-back end-to-end without the local shim
- the clean extracted upstream branch at `ext-onlook-pr/` removes the workspace-specific `/api/local-project` shim and path-registration fallback, keeps the browser directory-handle persistence path, passes `@onlook/web-client` typecheck, and passes `@onlook/web-client` build with placeholder required envs
- official upstream issue reports now also match this boundary:
  - Onlook issue `#2336`: CodeSandbox preview URLs return `400` in iframe context
  - Onlook issue `#3087`: trust interstitial and Penpal timeout on self-hosted Onlook
- those upstream issues still matter for future `Next 16` re-upgrade work and for generic Onlook runtime hardening, but they no longer block the current repo lane once the sandbox app stays on `Next 15`
- end-to-end write-back is solved for the current local repo lane, but shim-free re-proof of the extracted upstream branch and full AI/chat readiness remain separate questions
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
6. While CodeSandbox-backed Onlook preview remains part of this lane, the sandbox app should stay on `Next 15.5.15`; `Next 16` is not the currently working target version here.
7. Slice 1 should use client-side, non-credentialed browser fetches only.
8. The adopted demo runtime is a local cross-worktree dependency, not a repo-native sandbox fixture.
9. The default promotion posture should be `sandbox-first`, not immediate replacement of the live UI.
10. Promotion into live authority should happen only after explicit parity and acceptance checks.

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
- that the clean extracted upstream branch has already re-proven host write-back end-to-end after removing the local `/api/local-project` shim
- that full Onlook AI/chat features are validated here
- that a final promotion model has already been approved

## Next Step
Use `strategy.md` as the settled authority and boundary model for this lane, and use `impl-plan.md` as the record of the now-solved local write-back lane plus the cleaned upstream packaging split.

Use `pilot-plan.md` and `impl-plan.md` together to keep the current repo lane stable while treating `ext-onlook-pr/` as the upstream-ready patch baseline and any future AI/chat or shim-free end-to-end re-proof as separate follow-up work.
