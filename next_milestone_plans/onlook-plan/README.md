# Onlook Plan Index

## Purpose
This folder contains the bounded planning set for one specific question:

- whether and how Onlook can be used for this repo without changing the current live static review UI by default
- how to create a separate frontend lane that Onlook can edit safely
- how later promotion back into repo authority should be controlled

This folder is not a claim that Onlook is already integrated.
It is the decision packet for an isolated Onlook pilot lane.

## Status
This packet is now merged repo-local planning and operating material on `main`.

The original implementation lane lived on branch `codex/onlook-next` in worktree `worktrees/onlook-next`.
Those names now matter as provenance only.
Use the merged copy on `main` as the current tracked authority for this lane.

Current lane state:

- the planning packet is committed
- the sandbox app has been scaffolded at `onlook-ui/`
- the sandbox app now implements a bounded multi-route review UI family inside `onlook-ui/*`:
  - `/`
  - `/document-trace`
  - `/workbench-compare`
  - `/candidate-b-trace`
  - `/analyst-insight`
- the root review shell now loads `/runs` and `/runs/{run_id}/overview` through a committed same-origin fixture snapshot generated from the existing review API seam and exposes route navigation for the full sandbox family
- the document-trace route now loads manifest, diagnostics, normalized-text, indexed-chunks, and extracted-units payloads through that same committed fixture seam
- the analyst-insight route now exercises the three existing aliased POST endpoints through the existing backend services without changing the shipped static UI authority
- the compare-family routes now support two bounded states:
  - graceful degradation when same-checkout compare prep is absent
  - populated compare and Candidate-B-trace rendering when same-checkout compare prep has been created locally
- the sandbox app now carries a committed compatibility fix that keeps React `19.2.4` but pins `next` and `eslint-config-next` to `15.5.15`
- the app now includes a committed `onlook-ui/.env.example` as the reproducible frontend env template
- actual Onlook use now assumes a local ignored `onlook-ui/.env.local` for the frontend API base
- the committed default frontend API base is now same-origin via `onlook-ui/.env.example`, and `onlook-ui/.env.local` is only needed when a direct localhost override is intentionally required
- the repo-local backend startup helper is `tools/start-review-api.ps1`; it now auto-resolves the repo-native same-checkout runtime under `backend/app/storage_test_runtime` first and only falls back to the historical sibling adopted runtime when the repo-native runtime is unavailable
- the sandbox fixture exporter is now `tools/export-onlook-fixture.py`; it snapshots the existing review API and analyst aliases into `onlook-ui/data/fixture.json` plus split binary assets under `onlook-ui/data/review-src/` and `onlook-ui/data/candidate-pdf/`
- that fixture packaging now keeps every imported file under the current Onlook local-folder 10 MB per-file ceiling, so manual import no longer drops the sandbox data payload silently
- the original clean upstream base reference for this lane is the source clone lineage rooted at `ext-onlook/`, last verified from upstream revision `a242be584fa9c71ca5be9e5e7a2640595c4200be`
- the current proven local operator and debug surface for the resolved repo lane is `ext-onlook-fix/` on local branch `codex/restored-local-writeback` at commit `14dbc96e`
- that preserved local operator surface now includes the local import/runtime stabilization fixes needed for the current lane:
  - safe git-config probing during repo init
  - deferred frame-theme reads until a live frame view exists
  - safe gesture handling while preview connections are not ready
  - guarded text-cleanup teardown when branch history has already been cleared
  - destroyed-connection-safe preload child-state lookups for frame and branch identifiers
- current local-folder import proof on that preserved surface no longer reproduces the earlier:
  - `failed to exec in podman container`
  - `No frame view found`
  - `No element found`
  - `No branch selected`
  - destroyed-connection child-state crashes during import and preview reload
- the clean upstream packaging surface is `ext-onlook-pr/` on local branch `codex/upstream-clean` at commit `6d4c463a`
- the repo-local Onlook web startup helper is `tools/start-onlook-web.ps1`; it now defaults to `ext-onlook-fix/` on port `3000`, pins known-good commits by default, refuses dirty clones by default, fails closed if the fixed preload helper port `8083` is already occupied, can be pointed at a different local clone with `-OnlookDir`, and now normalizes line-ending-only drift in the known runtime-generated files before enforcing the dirty-clone guard, but only when both the worktree delta and the staged/index delta are line-ending-only
- the repo-local integrity helper is `tools/check-onlook.ps1`; it verifies the preserved clones or tree-equivalent restored clones, required env files, preserved patch archives, can optionally rerun the bounded repo validations with `-RunValidation`, and treats line-ending-only drift in the known runtime-generated files as non-blocking rather than misclassifying it as a semantic source edit, but only when both the worktree delta and the staged/index delta are line-ending-only
- the repo-local duplication helper is `tools/copy-onlook-ui.ps1`; it creates a clean source duplicate of `onlook-ui/` without carrying `.next/` or `node_modules/`, and can copy the local frontend env when the duplicate should point at the same backend
- that duplication helper now refuses a dirty canonical `onlook-ui/` source tree by default, so scratch copies do not silently fork from an in-progress or partially validated state unless explicitly overridden
- the repo-local duplicate-prep helper is `tools/prep-onlook-copy.ps1`; it wraps duplicate creation, local `npm install`, `npm run lint`, and `npm run build`, and can optionally run the tracked sandbox smoke before any Onlook import step
- the default duplicate target `onlook-ui-copy/` is now tracked in `.gitignore`, so the low-risk scratch path does not depend on workstation-local exclude rules
- that duplicate-prep helper now fails closed when a custom target is not git-ignored unless `-AllowVisibleTarget` is passed explicitly
- that duplicate-prep helper now also materializes an upload-safe duplicate `.env` with only the public `NEXT_PUBLIC_REVIEW_API_BASE`, because Onlook intentionally skips `.env.local` during project upload
- a fresh duplicate prepared with `tools/prep-onlook-copy.ps1 -TargetDir onlook-ui-copy` now passes local install, lint, build, and fixture-backed route smoke in one repo-owned path, so producing a clean duplicate sandbox source is a proven path rather than a theoretical recovery step
- the repo-local duplicate diff helper is `tools/diff-onlook-copy.ps1`; it compares meaningful duplicate source files back to canonical `onlook-ui/` while ignoring local-only build/install/env artifacts, including the generated duplicate `.env`, so duplicate-to-canonical promotion review is explicit instead of ad hoc
- the lowest-risk default for exploratory Onlook work is now: prepare a duplicate sandbox source with `tools/prep-onlook-copy.ps1`, import that duplicate, and keep `onlook-ui/` untouched unless direct canonical write-back is the explicit goal
- the repo-local restore helper is `tools/restore-onlook.ps1`; it can rebuild either preserved Onlook patch set from the tracked patch archives and the pinned upstream base commit instead of relying on the local solved clones remaining untouched forever
- on a fresh worktree, the restore helper now recreates the expected helper-facing clone names by default:
  - `ext-onlook-fix/` for the local-writeback patch set
  - `ext-onlook-pr/` for the upstream-clean patch set
- when those restored clones do not already carry local env files, the restore helper now bootstraps `apps/web/client/.env` and `packages/db/.env` from the upstream templates using local-demo Supabase defaults plus placeholder OpenRouter/Codesandbox keys
- when those restored clones do not already carry installed workspace dependencies, the restore helper now runs `bun install`
- if that dependency install rewrites `bun.lock`, the restore helper now restores the tracked lockfile back to `HEAD` and still fails closed on any broader tracked drift
- the startup and integrity helpers now accept either the preserved solved Onlook commits or a clean restored clone whose tree hash matches the preserved solved state exactly, so fresh recovery no longer requires `-SkipCommitCheck`
- the startup and integrity helpers now also explicitly tolerate the current runtime-generated line-ending-only drift in:
  - `apps/web/client/messages/en.d.json.ts`
  - `apps/web/client/public/onlook-preload-script.js`
  so using the preserved local operator clone no longer breaks the next helper pass on Windows
- the tracked patch archives are now stored under `.gitattributes` with `patches/*.patch -text`, so Windows line-ending normalization no longer corrupts the restore inputs
- the restore helper now validates the rebuilt tree hash against the preserved solved tree, and it has successfully rebuilt both preserved Onlook patch sets from the pinned upstream base commit into fresh local clones, so clone recovery is also a proven path rather than a manual fallback
- canonical local Onlook env files for the proven local operator surface now exist at:
  - `ext-onlook-fix/apps/web/client/.env`
  - `ext-onlook-fix/packages/db/.env`
- local source Onlook now boots through the current proven direct launch path at `http://127.0.0.1:3000/login`
- if browser state on `http://127.0.0.1:3000` becomes sticky or points at an old imported project, `tools/start-onlook-web.ps1 -Port 3011` is now the bounded fresh-origin fallback for local use
- local source Onlook dev login has been validated through the seeded demo-user flow
- with a real `CSB_API_KEY`, actual project import and sandbox creation inside local source Onlook are now validated through the current CodeSandbox-backed flow
- the earlier `Next 16` preview blocker is now resolved for this repo lane by the committed sandbox-app compatibility fix
- a fresh local Onlook import of the current `onlook-ui/` folder now creates a new sandbox preview that hydrates successfully
- direct preview of that fresh sandbox now logs the `review-shell` lifecycle, fetches `/runs` and `/runs/{run_id}/overview`, and loads the populated review shell
- the same fresh sandbox now renders the populated review shell inside the Onlook iframe and editor shell, not just in a top-level preview tab
- from a fresh browser profile, switching the canvas to `Preview` and accepting the CodeSandbox trust interstitial now loads the real sandbox app inside the Onlook iframe
- direct local write-back is now proven for this repo lane: a bounded Onlook-authored save wrote into `onlook-ui/app/page.tsx` on disk and the host file was restored clean afterward
- same-checkout compare prep is now a repo-native, validated local path for this lane:
  - `tools/seed_wb_compare.py` can seed baseline and Candidate-A review runtimes under `backend/app/storage_test_runtime/lc_e2e/`
  - `tools/run_nrc_aps_candidate_b_compare.py` can generate a local Candidate-B bundle under `tests/reports/cb-compare-*`
  - `tools/validate_wb_prep.py` can validate the resulting same-checkout compare selection and emit recommended review, trace, and compare URLs
- the compare prep tooling now works from a clean worktree by resolving the expected `phase7a-py311` interpreter from the nearest ancestor `./.venvs/` when the worktree itself does not carry a local copy
- the Candidate-B compare tooling now correctly recognizes wrapped `opendataloader_pdf --help` output when checking for annotated-PDF capability, so CLI help formatting no longer creates a false negative
- the repo-local sandbox browser smoke helper is `tools/run-onlook-sandbox-smoke.ps1`; it starts an isolated sandbox dev server, proves the hydrated sandbox routes against the committed same-origin fixture snapshot before any Onlook import step, can target either canonical `onlook-ui/` or a prepared duplicate with `-AppDir`, and supports two bounded profiles:
  - `-Profile core` for review, document-trace, and analyst-insight
  - `-Profile full` for the full route family, including compare-family routes after `tools/validate_wb_prep.py` emits the recommended same-checkout live-review URLs that the helper then remaps into sandbox routes
- the repo-local duplicate-target operator proof helper is `tools/run-onlook-operator-proof.ps1`; it reuses or starts local Onlook web, verifies that the prepared duplicate still has the import-safe same-origin fixture API route and a sub-10 MB fixture index, restarts the expected local Onlook clone once if a reused browser session is stale, imports that duplicate, proves trusted preview navigation across the full sandbox route family, runs the analyst flow, and proves duplicate-only write-back while restoring the duplicate file and leaving canonical `onlook-ui/` untouched
- the canonical host-write-back target remains `onlook-ui/`; duplicate copies created with the duplicate helpers are for scratch imports or comparison work, do not auto-promote changes back into the canonical sandbox app, and should be reviewed first with `tools/diff-onlook-copy.ps1`
- that local write-back proof ran on the preserved local operator surface at `ext-onlook-fix/` and used the file-input import path, so it should not be flattened into a claim that the clean extracted upstream branch has already re-proven host write-back end-to-end without the local shim
- the clean extracted upstream branch at `ext-onlook-pr/` removes the workspace-specific `/api/local-project` shim and path-registration fallback, keeps the browser directory-handle persistence path, passes `@onlook/web-client` typecheck, and passes `@onlook/web-client` build with placeholder required envs
- the current preserved local Onlook patch stacks are now also stored inside this tracked repo lane as:
  - `patches/local-writeback.patch`
  - `patches/upstream-clean.patch`
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
7. The sandbox route family should continue to use client-side, non-credentialed browser fetches only unless the lane is explicitly re-scoped.
8. The default demo runtime is the repo-native same-checkout `backend/app/storage_test_runtime`; the older sibling adopted runtime is fallback/provenance only.
9. Same-checkout compare prep is an optional local runtime/input layer for populated compare-family validation, not a product-code dependency of the shipped UI.
10. The default promotion posture should be `sandbox-first`, not immediate replacement of the live UI.
11. Promotion into live authority should happen only after explicit parity and acceptance checks.

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
  - exact local demo runtime/data context
  - exact runtime preflight and path-resolution rules
  - exact multi-route sandbox component map
  - exact validation and compare-prep commands

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

Use `pilot-plan.md` and `impl-plan.md` together to keep the current repo lane stable while:

- using duplicate sandbox copies as the default experimental write target
- preparing those duplicate targets with `tools/prep-onlook-copy.ps1` before any Onlook import step
- treating `onlook-ui/` as the canonical sandbox source only when direct canonical write-back is intentional
- using `tools/run-onlook-sandbox-smoke.ps1` as the repeatable pre-Onlook browser proof for the bounded route family
- using `tools/run-onlook-operator-proof.ps1` as the repeatable duplicate-target Onlook proof before relying on editor-side save/write-back behavior
- using `tools/diff-onlook-copy.ps1` as the explicit duplicate-to-canonical review step before any later promotion decision
- treating same-checkout compare prep as an opt-in local runtime/data layer when populated compare-family route validation is required
- treating `ext-onlook-pr/` as the upstream-ready patch baseline
- keeping any future AI/chat or shim-free end-to-end re-proof as separate follow-up work
