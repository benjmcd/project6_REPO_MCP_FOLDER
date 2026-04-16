# Onlook Implementation Plan

## 1. Purpose
This document fixes the exact repo-side implementation choices for the first Onlook sandbox slice.

It does not approve live promotion.

It approves only the bounded sandbox scaffold and the minimum supporting runtime/context choices needed to make that scaffold real.

## 2. Verified Preconditions

### 2.1 Clean execution surface
This lane was implemented from:

- branch `codex/onlook-next`
- worktree `worktrees/onlook-next`

Current tracked authority for the completed lane is now merged `main`.

For a clean post-merge validation surface, use a fresh mainline worktree such as `worktrees/mainline-lane`.

Current status:

- the planning packet is now merged and committed on `main`
- the sandbox app exists at `onlook-ui/`
- tracked tool-state files under `.omc/state/*` may drift during interactive sessions and are not part of the planned commit surface for this lane

### 2.2 Local frontend tool availability
Verified locally:

- `node`: `v24.13.0`
- `npm`: `11.6.2`
- `npx`: `11.6.2`
- `uvicorn`: `0.40.0`
- `bun`: `1.3.11`

Practical meaning:

- use `npm`, not Bun, for the sandbox app in this lane

### 2.3 Backend baseline slice
Verified locally from this worktree:

- `backend/tests/test_review_nrc_aps_catalog.py`
- `backend/tests/test_review_nrc_aps_api.py`

Result:

- `15 passed, 4 warnings`

Practical meaning:

- the review API/catalog seam is stable enough for a sandbox frontend pilot

### 2.4 Demo runtime smoke
Verified locally with:

- `DB_INIT_MODE=none`
- `DATABASE_URL` pointed at the adopted runtime database
- `STORAGE_DIR` pointed at the adopted `storage_test_runtime` root

Result:

- `GET /api/v1/review/nrc-aps/runs` returned `200`
- `default_run_id` resolved to `f6e34493-270c-4d93-afa9-bf85bf699f0c`
- the `runs` array length was `2`
- `GET /api/v1/review/nrc-aps/runs/f6e34493-270c-4d93-afa9-bf85bf699f0c/overview` returned `200`

Practical meaning:

- the adopted demo runtime context is real and usable

### 2.5 Scaffold validation
Verified locally:

- `onlook-ui/` exists in this worktree
- no nested git repository was created inside `onlook-ui/`
- no generated `AGENTS.md` or `CLAUDE.md` exists in `onlook-ui/`
- `onlook-ui/` now carries the committed compatibility fix for CodeSandbox-backed Onlook preview:
  - `next`: `15.5.15`
  - `eslint-config-next`: `15.5.15`
  - `@eslint/eslintrc`: `^3`
  - `next.config.ts`: `outputFileTracingRoot`
  - `eslint.config.mjs`: `FlatCompat`-based Next 15 config
- `npm run lint` passes in `onlook-ui/`
- `npm run build` passes in `onlook-ui/`
- `npm run dev -- --hostname 127.0.0.1 --port 3000` serves `GET /` successfully

Practical meaning:

- the sandbox app is now real, bootable, and was a valid base for the first feature-wiring slice

### 2.6 Multi-route sandbox validation
Verified locally after the route-family expansion:

- `onlook-ui/` now contains the typed review API layer under `lib/`
- `onlook-ui/` now contains the route-family shell components under `components/`
- `onlook-ui/` now exposes these Next routes:
  - `/`
  - `/document-trace`
  - `/workbench-compare`
  - `/candidate-b-trace`
  - `/analyst-insight`
- tracked browser validation against the local sandbox dev server confirmed:
  - the root review route renders the populated review shell
  - the document-trace route renders populated manifest and tab data against a live review runtime
  - the analyst-insight route completes the bounded three-stage POST flow
  - the workbench-compare route renders populated compare data once same-checkout compare prep exists
  - the Candidate-B-trace route renders populated artifact-backed tabs once same-checkout compare prep exists
- the repo-local harness for that proof is now `tools/run-onlook-sandbox-smoke.ps1`:
  - `-Profile core` proves the hydrated review, document-trace, and analyst-insight routes
  - `-Profile full` first requires `tools/validate_wb_prep.py`, then remaps the resulting recommended live review URLs into the sandbox route table to prove the full route family without using Onlook yet

Practical meaning:

- the sandbox is no longer a single-page proof-of-fit
- the bounded review UI family is now implemented and validated against the adopted backend seams

### 2.7 Local Onlook operator path
Verified locally against the current official Onlook development setup docs:

- Bun is installed locally
- Docker Desktop is installed and the local Supabase backend is running
- the original clean upstream base reference for this lane exists at `ext-onlook/`
- that base clone was last verified at revision `a242be584fa9c71ca5be9e5e7a2640595c4200be`
- the current proven local operator surface for the solved repo lane is `ext-onlook-fix/` on local branch `codex/local-writeback-fix` at commit `c8cf5c16`
- the clean upstream packaging surface is `ext-onlook-pr/` on local branch `codex/upstream-clean` at commit `6d4c463a`
- the exact local Onlook commits are now also preserved inside this tracked repo lane as:
  - `patches/local-writeback.patch`
  - `patches/upstream-clean.patch`
- the repo-local duplication helper `tools/copy-onlook-ui.ps1` now creates clean duplicates of `onlook-ui/` without `.next/` or `node_modules/`, and copies `.env.local` only when explicitly requested
- on a fresh worktree, the first frontend bootstrap step is `Copy-Item ./onlook-ui/.env.example ./onlook-ui/.env.local` unless a different local review API base is intentionally needed
- that duplication helper now refuses a dirty canonical `onlook-ui/` source tree by default unless `-AllowDirtySource` is supplied
- the repo-local duplicate-prep helper `tools/prep-onlook-copy.ps1` now wraps duplicate creation, local install, `npm run lint`, and `npm run build`, and can optionally run the tracked sandbox smoke before any Onlook import
- that duplicate-prep helper now fails closed when a custom target is not git-ignored unless `-AllowVisibleTarget` is passed explicitly
- a fresh duplicate prepared with `tools/prep-onlook-copy.ps1 -TargetDir onlook-ui-copy -CopyLocalEnv` now passes local install, lint, and build in one repo-owned path
- the repo-local duplicate diff helper `tools/diff-onlook-copy.ps1` now makes duplicate-to-canonical sandbox review explicit before any manual merge-back step while ignoring local-only `.next/`, `node_modules/`, and `.env.local` noise
- the safest default operator posture is now: prepare a duplicate sandbox target first, import that duplicate into Onlook, and leave `onlook-ui/` untouched unless direct canonical write-back is the explicit goal
- the repo-local restore helper `tools/restore-onlook.ps1` can now recreate either preserved Onlook patch set from the tracked patch archives and the pinned upstream base commit
- on a fresh worktree, that restore helper now recreates the expected helper-facing clone names by default:
  - `ext-onlook-fix/`
  - `ext-onlook-pr/`
- when those restored clones do not already carry local env files, the restore helper now bootstraps `apps/web/client/.env` and `packages/db/.env` from the upstream templates using local-demo Supabase defaults plus placeholder OpenRouter/Codesandbox keys
- when those restored clones do not already carry installed workspace dependencies, the restore helper now runs `bun install`
- if that dependency install rewrites `bun.lock`, the restore helper now restores the tracked lockfile back to `HEAD` and still fails closed on any broader tracked drift
- the startup and integrity helpers now accept either the preserved solved Onlook commits or a clean restored clone whose tree hash matches the preserved solved state exactly
- the startup helper now normalizes line-ending-only drift in the known runtime-generated files before enforcing the dirty-clone guard, but only when both the worktree delta and the staged/index delta are line-ending-only
- the integrity helper now treats that same line-ending-only drift as non-blocking rather than misclassifying it as a semantic source edit, but only when both the worktree delta and the staged/index delta are line-ending-only
- the startup helper also fails closed if the fixed Onlook preload helper port `8083` is already in use, instead of allowing a second runtime to degrade into a runtime `EADDRINUSE` failure
- the currently tolerated runtime-generated files are:
  - `apps/web/client/messages/en.d.json.ts`
  - `apps/web/client/public/onlook-preload-script.js`
- the tracked patch archives are now protected by `.gitattributes` with `patches/*.patch -text`, so the stored restore inputs are not silently rewritten by Windows line-ending conversion
- the restore helper now validates the rebuilt tree hash against the preserved solved tree, and it has successfully recreated both preserved Onlook patch sets from the pinned upstream base commit into fresh local clones
- the canonical local env files for the proven local operator surface now exist at:
  - `ext-onlook-fix/apps/web/client/.env`
  - `ext-onlook-fix/packages/db/.env`
- `bun db:seed` now succeeds from `ext-onlook-fix/`
- the current proven direct source-launch path serves `GET /login` successfully at `http://127.0.0.1:3000/login`
- if the browser keeps sticky state on the default `3000` origin, `tools/start-onlook-web.ps1 -Port 3011` is now the bounded fresh-origin fallback instead of reusing stale browser state
- the dev-only demo-user login path succeeds and redirects into the app shell

Practical meaning:

- the current working Onlook path for this lane is local source development, not the hosted desktop OAuth flow
- the repo-side sandbox and the local Onlook operator path are both now real
- placeholder `CSB_API_KEY` values are sufficient for local boot and dev login only
- with a real `CSB_API_KEY`, actual project import and sandbox creation are now proven through the current CodeSandbox-backed flow
- the earlier repo-side preview blocker was `Next 16`; the sandbox app now carries the committed compatibility fix that keeps React `19.2.4` but pins `next` and `eslint-config-next` to `15.5.15`
- a fresh local import of the current `onlook-ui/` folder now produces a new sandbox preview that hydrates successfully
- direct preview of that fresh sandbox now logs the `review-shell` lifecycle, fetches `/runs` and `/runs/{run_id}/overview`, and loads the populated review shell
- the same fresh sandbox now renders the populated review shell inside the Onlook iframe and editor shell, so the repo lane is no longer blocked at preview hydration
- from a fresh browser profile, switching the canvas to `Preview` and accepting the CodeSandbox trust interstitial now loads the real sandbox app inside the Onlook iframe
- direct local write-back/editing is now proven for this repo lane on the preserved local operator surface: a bounded save wrote into `onlook-ui/app/page.tsx` on disk and the host file was restored clean afterward
- that write-back proof used the file-input import path and the preserved local `/api/local-project` shim, so it should not be overstated as proof that the clean extracted upstream branch has already re-proven shim-free host write-back end-to-end
- the clean extracted upstream branch removes the workspace-specific `/api/local-project` shim and path-registration fallback, keeps the browser directory-handle persistence path, passes `bun --filter @onlook/web-client typecheck`, and passes `bun --filter @onlook/web-client build` when the required envs are stubbed
- upstream issue reports for the old preview/runtime failures remain relevant for future `Next 16` re-upgrade work and for generic Onlook runtime hardening, but they no longer block the current repo lane while the sandbox app stays on `Next 15`
- placeholder or absent `OPENROUTER_API_KEY` values still do not prove AI/chat feature readiness

### 2.8 Same-checkout compare prep validation
Verified locally in this worktree:

- `./../../.venvs/phase7a-py311/Scripts/python.exe ./tools/seed_wb_compare.py --runtime-root ./backend/app/storage_test_runtime/lc_e2e/wb-b0 --visual-lane-mode baseline`
- `./../../.venvs/phase7a-py311/Scripts/python.exe ./tools/seed_wb_compare.py --runtime-root ./backend/app/storage_test_runtime/lc_e2e/wb-a0 --visual-lane-mode candidate_a_page_evidence_v1`
- `./../../.venvs/phase7a-py311/Scripts/python.exe ./tools/run_nrc_aps_candidate_b_compare.py`
- `python ./tools/validate_wb_prep.py`

Result:

- a same-checkout baseline review runtime now exists at `backend/app/storage_test_runtime/lc_e2e/wb-b0`
- a same-checkout Candidate-A review runtime now exists at `backend/app/storage_test_runtime/lc_e2e/wb-a0`
- a same-checkout Candidate-B compare bundle now exists under `tests/reports/cb-compare-*`
- `tools/validate_wb_prep.py` now passes and emits recommended compare and trace URLs for the sandbox route family

Practical meaning:

- populated compare-family validation is now a repo-native local path in a clean worktree
- compare-family population no longer depends on silently borrowing stale external runtime state

## 3. Exact Scaffold Choice

### 3.1 App type
Use:

- Next.js
- App Router
- TypeScript
- Tailwind CSS
- npm-local package management

Do not use:

- Bun
- root-level `package.json`
- a repo-wide frontend monorepo restructure

### 3.2 App root
Create the sandbox app at:

- `onlook-ui/`

Reason:

- short path
- separate from the shipped static UI
- keeps sandbox tooling local

### 3.3 Preferred scaffold invocation
Historical scaffold command used early in this lane:

```powershell
npx create-next-app@16 onlook-ui --ts --tailwind --eslint --app --use-npm --import-alias "@/*" --disable-git --no-agents-md --no-src-dir --no-react-compiler --empty --turbopack --yes
```

Current rule:

- treat the command above as historical setup context only
- the authoritative dependency/config state for this lane is the committed `Next 15.5.15` compatibility fix described in section `2.5`
- do not leave a recreated sandbox app on the raw scaffolded `Next 16` dependency set if you are rebuilding this lane from scratch

Expected scaffold posture:

- no nested git repository
- no generated `AGENTS.md` or `CLAUDE.md` inside `onlook-ui/`
- no `src/` directory
- no React Compiler
- no default starter page content
- no broader repo restructuring

Stop and reassess instead of scaffolding if:

- the CLI still prompts for settings after `--yes`
- `--no-agents-md` is rejected by the current CLI
- the scaffold still emits `AGENTS.md` or `CLAUDE.md` under `onlook-ui/`

Reason:

- current official Next.js CLI docs confirm `--agents-md` is default, `--yes` uses defaults or prior preferences, and `--no-*` negates default options
- empirical scaffold verification in this worktree showed `--reset-preferences` still prompts interactively here, so it is not part of the bounded non-interactive command
- this keeps the sandbox local and compatible with the verified Onlook target shape
- this avoids creating a nested git repository inside the worktree

## 4. Exact Backend Connection Rule

### 4.1 Rule
Use direct cross-port browser calls from the sandbox app to FastAPI in this lane.

The sandbox-family fetch model is fixed to:

- client-side browser fetches only
- non-credentialed requests only
- no cookies, session dependence, or auth headers
- no frontend proxy or rewrite layer

Do not move to server-side data fetching, credentialed requests, or a frontend proxy in this lane without a separate reassessment.

### 4.2 Why
Verified repo facts:

- FastAPI currently allows broad CORS in `backend/main.py`
- the initial pilot only needs read-only JSON review endpoints
- the current shipped review UI uses plain browser `fetch()` calls without credential options
- adding a proxy now would widen scope before proving the sandbox lane is useful

Practical constraint:

- the current CORS posture is acceptable for plain non-credentialed browser fetches
- it is not a safe basis for quietly introducing credentialed cross-origin requests in this lane

### 4.3 Exact frontend env
For manual shell-driven validation, use:

```powershell
$env:NEXT_PUBLIC_REVIEW_API_BASE='http://127.0.0.1:8000/api/v1/review/nrc-aps'
```

The frontend should build all review API requests from that base.

Use `NEXT_PUBLIC_REVIEW_API_BASE` only from sandbox client components or client-side helper code.
Do not use server-side data fetching in this lane.

For actual Onlook-driven startup, prefer a local ignored file at:

- `onlook-ui/.env.local`
- created from the committed template `onlook-ui/.env.example`

with:

```dotenv
NEXT_PUBLIC_REVIEW_API_BASE=http://127.0.0.1:8000/api/v1/review/nrc-aps
```

Reason:

- manual shell validation and Onlook-driven startup are different launch paths
- Onlook is expected to start the frontend from the project root and should not depend on inherited shell env from a separate terminal session
- keeping this in ignored local config preserves the sandbox boundary without repurposing repo-root config

For the local Onlook source operator path itself, follow the current official env layout:

- `ext-onlook-fix/apps/web/client/.env`
- `ext-onlook-fix/packages/db/.env`

Do not treat `ext-onlook/.env` as the canonical current setup contract for the solved local lane.

When using Onlook itself:

- treat `onlook-ui/` as the intended local project source for Onlook import
- do not point Onlook at the repo root
- for immediate local repo-lane work, use the preserved local operator surface at `ext-onlook-fix/`
- for upstream packaging work, use the clean extracted branch at `ext-onlook-pr/`
- do not treat the clean extracted upstream branch as already re-proven shim-free end-to-end until host write-back is exercised there without the local `/api/local-project` shim

Reason:

- the repo root is not the sandbox frontend app
- the repo root already contains unrelated tooling and non-frontend files

## 5. Exact Demo Runtime And Data Context

### 5.1 Adopted runtime root
Use this runtime root for the first sandbox demo:

- `./../pr45-postmerge-audit/backend/app/storage_test_runtime`

Do not point the backend at the nested runtime `storage` directory.

Reason:

- current review runtime discovery expects a `storage` or `storage_test_runtime` root and then resolves `lc_e2e` under it

### 5.2 Adopted runtime summary
Current verified summary:

- `./../pr45-postmerge-audit/backend/app/storage_test_runtime/lc_e2e/20260412_182041/local_corpus_e2e_summary.json`

Verified useful values:

- `run_id`: `f6e34493-270c-4d93-afa9-bf85bf699f0c`
- `visual_lane_mode`: `candidate_a_page_evidence_v1`
- `passed`: `true`

### 5.3 Exact backend env for the pilot
Use shell env, not a local `.env`, for the first pilot.

Resolve the repo-local sibling paths first, then pass absolute values to the backend server:

```powershell
$runtimeRoot = (Resolve-Path ./../pr45-postmerge-audit/backend/app/storage_test_runtime).Path
$runtimeDb = (Resolve-Path ./../pr45-postmerge-audit/backend/app/storage_test_runtime/lc_e2e/20260412_182041/lc.db).Path.Replace('\', '/')
$env:DB_INIT_MODE='none'
$env:DATABASE_URL="sqlite:///$runtimeDb"
$env:STORAGE_DIR=$runtimeRoot
```

Reason:

- `DB_INIT_MODE=none` avoids write-on-start migration behavior
- the backend server must receive absolute resolved paths here because `config.py` normalizes relative `STORAGE_DIR` values against the backend root
- the database points at the adopted runtime that the current review UI can discover
- the storage root points at the correct discovery boundary
- this keeps the sandbox backend context explicit and reproducible

### 5.4 Path-resolution rule
There are two different path-resolution paths in this repo:

- the backend server reads `STORAGE_DIR` through `app.core.config`, which resolves relative paths against the backend root
- the validate-only review test fixture discovers review roots directly, but the `/runs` API assertions inside that same test slice still execute through the FastAPI app and therefore still depend on `app.core.config`

Practical rule:

- resolve the adopted sibling runtime root to an absolute path both for the validate-only backend test slice in section 7.2 and for the backend server in section 7.3
- do not reuse older relative `STORAGE_DIR` examples once same-checkout compare prep exists, because the API assertions in the validation slice can otherwise miss the intended sibling runtime root

### 5.5 Cross-worktree dependency rule
The adopted demo runtime is a local dependency on the sibling `pr45-postmerge-audit` worktree.

Practical rule:

- if that sibling worktree, runtime root, summary file, or database file disappears, stop and reassess
- do not silently substitute a different runtime without updating the packet and re-validating the adopted context

## 6. Exact Multi-Route Sandbox Component Map

### 6.1 Route shell
- `onlook-ui/app/layout.tsx`
- `onlook-ui/app/page.tsx`
- `onlook-ui/app/document-trace/page.tsx`
- `onlook-ui/app/workbench-compare/page.tsx`
- `onlook-ui/app/candidate-b-trace/page.tsx`
- `onlook-ui/app/analyst-insight/page.tsx`

### 6.2 API and state layer
- `onlook-ui/lib/review-api.ts`
- `onlook-ui/lib/review-types.ts`
- `onlook-ui/lib/review-adapter.ts`
- `onlook-ui/lib/sandbox-routes.ts`
- `onlook-ui/lib/sandbox-links.ts`
- `onlook-ui/lib/display.ts`
- `onlook-ui/lib/analyst-samples.ts`

Responsibilities:

- read-only fetches from `NEXT_PUBLIC_REVIEW_API_BASE`
- local normalization for display and sandbox-route remapping
- no business-logic duplication from backend services
- no change to shipped static UI authority

### 6.3 UI components
- `onlook-ui/components/review-shell.tsx`
- `onlook-ui/components/document-trace-shell.tsx`
- `onlook-ui/components/workbench-compare-shell.tsx`
- `onlook-ui/components/candidate-b-trace-shell.tsx`
- `onlook-ui/components/analyst-insight-shell.tsx`
- `onlook-ui/components/sandbox-primitives.tsx`
- existing shared slice-1 components reused by the root review route:
  - `run-select.tsx`
  - `header-bar.tsx`
  - `pipeline-pane.tsx`
  - `tree-pane.tsx`
  - `details-pane.tsx`

### 6.4 Behavior boundary
Required in the current route family:

- route navigation across the bounded sandbox family
- main review loading against the live review API seam
- document-trace manifest and tab rendering against a live review runtime
- analyst-insight alias execution against the existing POST endpoints
- compare-family graceful degradation when same-checkout compare prep is absent
- compare-family populated rendering when same-checkout compare prep is present

Still intentionally deferred:

- full Mermaid parity
- theme persistence parity
- run-light vs run-heavy mode parity
- automatic promotion from sandbox state into live authority

Reason:

- the current route family proves the React/Tailwind + Onlook lane is viable across the bounded review UI family
- it still keeps live-product authority, backend contracts, and promotion policy separate

## 7. Exact Commands For The First Implementation Slice

### 7.1 Adopted runtime preflight
```powershell
Test-Path ./../pr45-postmerge-audit/backend/app/storage_test_runtime
Test-Path ./../pr45-postmerge-audit/backend/app/storage_test_runtime/lc_e2e/20260412_182041/local_corpus_e2e_summary.json
Test-Path ./../pr45-postmerge-audit/backend/app/storage_test_runtime/lc_e2e/20260412_182041/lc.db
```

Expected result:

- all three return `True`

### 7.2 Baseline backend validation
```powershell
$runtimeRoot = (Resolve-Path ./../pr45-postmerge-audit/backend/app/storage_test_runtime).Path
$env:STORAGE_DIR=$runtimeRoot
$env:PYTHONDONTWRITEBYTECODE='1'
python -B -m pytest ./backend/tests/test_review_nrc_aps_catalog.py ./backend/tests/test_review_nrc_aps_api.py -p no:cacheprovider
```

Expected result:

- `15 passed`

### 7.3 Backend demo server
Preferred helper:

```powershell
./tools/start-review-api.ps1
```

Equivalent explicit command path:

```powershell
$runtimeRoot = (Resolve-Path ./../pr45-postmerge-audit/backend/app/storage_test_runtime).Path
$runtimeDb = (Resolve-Path ./../pr45-postmerge-audit/backend/app/storage_test_runtime/lc_e2e/20260412_182041/lc.db).Path.Replace('\', '/')
$env:DB_INIT_MODE='none'
$env:DATABASE_URL="sqlite:///$runtimeDb"
$env:STORAGE_DIR=$runtimeRoot
python -m uvicorn main:app --app-dir ./backend --host 127.0.0.1 --port 8000
```

### 7.4 Backend API smoke after server start
```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/review/nrc-aps/runs'
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/review/nrc-aps/runs/f6e34493-270c-4d93-afa9-bf85bf699f0c/overview'
```

Expected result:

- both return `200`-equivalent successful responses

### 7.5 Frontend env and dev server
For manual shell-driven startup:

```powershell
Set-Location ./onlook-ui
$env:NEXT_PUBLIC_REVIEW_API_BASE='http://127.0.0.1:8000/api/v1/review/nrc-aps'
npm run dev -- --hostname 127.0.0.1 --port 3000
```

For actual Onlook use:

- ensure `onlook-ui/.env.local` exists with `NEXT_PUBLIC_REVIEW_API_BASE`
- for the lowest-risk exploratory path, create a duplicate first with `tools/copy-onlook-ui.ps1 -TargetDir onlook-ui-copy -CopyLocalEnv` and import that duplicate
- use `onlook-ui/` as the local project source only when direct canonical write-back is intentional
- use `ext-onlook-fix/` when you need the already-proven local operator path
- use `ext-onlook-pr/` when you need the clean extracted upstream packaging surface

### 7.6 Frontend static checks
```powershell
Set-Location ./onlook-ui
Get-Content ./.gitignore
npm run lint
npm run build
```

Expected checks:

- local `.gitignore` covers `.next/`
- local `.gitignore` covers `node_modules/`
- local `.gitignore` covers `.env.local`
- no generated `AGENTS.md` or `CLAUDE.md` exists in `onlook-ui/`
- `next build` completes under the committed `Next 15` compatibility config once `next.config.ts` sets `outputFileTracingRoot`

### 7.7 Diff boundary check
```powershell
git status --short
```

Expected route-family change boundary:

- `onlook-ui/*`
- `next_milestone_plans/onlook-plan/*`

Expected narrow helper/support additions only when same-checkout compare prep needs worktree support:

- `tools/run_nrc_aps_local_corpus_e2e.py`
- `tests/support_nrc_aps_candidate_b_opendataloader.py`

Explicit non-commit surface:

- `.omc/state/*`

Anything broader requires explicit reassessment.

### 7.8 Local Onlook source startup, import proof, and current blocker
If the hosted desktop OAuth path is blocked, use the local source path instead.

Repo-local helper:

```powershell
./tools/start-onlook-web.ps1
```

Fresh-origin fallback when browser state on the default `3000` origin is stale:

```powershell
./tools/start-onlook-web.ps1 -Port 3011
```

Repo-local integrity check:

```powershell
./tools/check-onlook.ps1
./tools/check-onlook.ps1 -RunValidation
```

Tracked sandbox browser smoke before any duplicate-target Onlook proof:

```powershell
./tools/run-onlook-sandbox-smoke.ps1 -Profile core
./tools/run-onlook-sandbox-smoke.ps1 -Profile full
./tools/run-onlook-sandbox-smoke.ps1 -Profile full -AppDir onlook-ui-copy
```

Repo-local duplicate sandbox copy:

```powershell
./tools/copy-onlook-ui.ps1 -TargetDir onlook-ui-copy -CopyLocalEnv
./tools/prep-onlook-copy.ps1 -TargetDir onlook-ui-copy -CopyLocalEnv
./tools/prep-onlook-copy.ps1 -TargetDir onlook-ui-copy -CopyLocalEnv -RunSmokeProfile full
./tools/diff-onlook-copy.ps1 -TargetDir onlook-ui-copy
```

Repo-local Onlook clone restore:

```powershell
./tools/restore-onlook.ps1 -PatchSet local-writeback
./tools/restore-onlook.ps1 -PatchSet upstream-clean
```

Equivalent direct source-launch path:

```powershell
Set-Location ./ext-onlook-fix
$env:PATH = "$env:USERPROFILE/.bun/bin;$env:PATH"
bun run dev -- --hostname 127.0.0.1 --port 3000
```

The helper and direct source-launch path both target the same proven local operator clone by default. The direct source-launch path is the canonical and currently proven local write-back path in this workspace.

The helper:

- starts from `ext-onlook-fix/` by default
- can be pointed at a different local clone with `-OnlookDir`
- pins `ext-onlook-fix/` and `ext-onlook-pr/` to their known-good commits by default unless `-SkipCommitCheck` is supplied
- refuses dirty local clones by default unless `-AllowDirty` is supplied
- prepends Bun to `PATH` so Onlook child processes can resolve `bun` correctly on Windows
- checks that the current canonical local env files exist
- warns if the local Supabase backend ports are not listening
- warns when placeholder `CSB_API_KEY` or `OPENROUTER_API_KEY` values are still in use
- keeps the solved local operator path fail-closed by refusing drift from the pinned local commits unless explicitly overridden

Expected current result:

- `GET http://127.0.0.1:3000/login` succeeds through the direct source-launch path
- the page shows the dev demo-user login button in development mode
- the dev-login flow redirects into the app shell
- `./tools/check-onlook.ps1` confirms the preserved local and upstream-clean clones are still pinned, clean, and backed by tracked patch archives
- `./tools/copy-onlook-ui.ps1 -TargetDir onlook-ui-copy -CopyLocalEnv` produces a clean duplicate frontend source tree for scratch imports without reusing `.next/` or `node_modules/`
- `./tools/prep-onlook-copy.ps1 -TargetDir onlook-ui-copy -CopyLocalEnv` turns that into a one-command duplicate-prep path by adding local install, lint, and build
- `./tools/restore-onlook.ps1` can recreate the preserved local or upstream-clean Onlook trees from the tracked patch archives if the local solved clones ever drift or need to be rebuilt from the pinned upstream base
- that restore path is now proven: both preserved patch sets were rebuilt successfully into fresh local clones from the pinned upstream base commit
- with a real `CSB_API_KEY`, local import of the current committed `onlook-ui/` folder reaches project verification, completes sandbox creation, and opens the imported project route and editor shell
- fresh local import of the current committed `onlook-ui/` folder now yields a new CodeSandbox preview that hydrates successfully
- direct preview of that fresh sandbox logs the `review-shell` lifecycle, fetches `/runs` and `/runs/{run_id}/overview`, and loads the populated review shell
- the same fresh sandbox now renders the populated review shell inside the Onlook iframe and editor shell
- from a fresh browser profile, switching to `Preview` and accepting the CodeSandbox trust interstitial now loads the real sandbox app inside the Onlook iframe
- a bounded Onlook-authored save now writes into `onlook-ui/app/page.tsx` on disk and the host file can be restored clean afterward
- this proves local operator boot, auth, import, sandbox creation, hydrated preview, populated iframe render, trust-click recovery, and bounded host write-back on the preserved local operator surface; it does not yet prove full AI/chat readiness or shim-free re-proof on the clean extracted upstream branch

### 7.9 Same-checkout compare prep and route-family proof
Repo-native local compare prep commands:

```powershell
./../../.venvs/phase7a-py311/Scripts/python.exe ./tools/seed_wb_compare.py --runtime-root ./backend/app/storage_test_runtime/lc_e2e/wb-b0 --visual-lane-mode baseline
./../../.venvs/phase7a-py311/Scripts/python.exe ./tools/seed_wb_compare.py --runtime-root ./backend/app/storage_test_runtime/lc_e2e/wb-a0 --visual-lane-mode candidate_a_page_evidence_v1
./../../.venvs/phase7a-py311/Scripts/python.exe ./tools/run_nrc_aps_candidate_b_compare.py
python ./tools/validate_wb_prep.py
```

Expected result:

- `tools/validate_wb_prep.py` passes
- the output includes recommended same-checkout URLs for:
  - `/review/nrc-aps/workbench-compare`
  - `/review/nrc-aps/candidate-b-trace`
  - baseline and Candidate-A document trace follow-through
- `./tools/run-onlook-sandbox-smoke.ps1 -Profile full` then consumes those recommended URLs, remaps them into sandbox routes, and proves the populated compare-family surfaces before any Onlook import step
- `./tools/run-onlook-sandbox-smoke.ps1 -Profile full -AppDir onlook-ui-copy` can now prove a prepared duplicate target before the later Onlook operator proof
- the sandbox `workbench-compare` route then renders populated compare data
- the sandbox `candidate-b-trace` route then renders populated artifact-backed tabs
- the compare-family proof remains local runtime/input prep only; it does not modify shipped static UI authority

## 8. Stop Rules
Stop and reassess if:

- the scaffold command prompts unexpectedly or emits generated agent-instruction files
- the scaffold requires touching `backend/app/review_ui/static/*`
- the sandbox cannot render the first page without backend contract changes
- direct cross-port calls require credentialed requests, server-side fetching, or early proxy work
- the adopted `pr45-postmerge-audit` runtime root, summary, or database path fails preflight
- the sandbox route family starts duplicating backend business logic instead of consuming backend outputs
- a fresh import of the current committed sandbox app stops hydrating in direct preview or stops loading the populated shell in the Onlook iframe
- future work starts depending on the clean extracted upstream branch as if shim-free host write-back had already been re-proven there

## 9. Immediate Next Move
The next justified move is:

1. treat preview hydration, local repo-lane write-back, and populated compare-family prep as resolved for the current local lane
2. use `ext-onlook-fix/` when you need the preserved solved local operator path
3. use `ext-onlook-pr/` as the clean upstream-ready patch baseline
4. use same-checkout compare prep when populated compare-family work is the goal, and do not silently assume that data is present
5. treat upstream issue evidence as future `Next 16` re-upgrade and runtime-hardening context, not as the current repo blocker
6. keep AI/chat readiness and any shim-free end-to-end re-proof on the clean extracted branch as separate follow-up work
7. for routine exploratory work, treat a duplicate prepared by `tools/prep-onlook-copy.ps1` as the default write target and review it first with `tools/diff-onlook-copy.ps1` before any manual merge-back
8. treat `onlook-ui/` as the canonical write-back target only when direct canonical sandbox edits are the explicit goal
