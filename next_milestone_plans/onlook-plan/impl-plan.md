# Onlook Implementation Plan

## 1. Purpose
This document fixes the exact repo-side implementation choices for the first Onlook sandbox slice.

It does not approve live promotion.

It approves only the bounded sandbox scaffold and the minimum supporting runtime/context choices needed to make that scaffold real.

## 2. Verified Preconditions

### 2.1 Clean execution surface
This lane runs from:

- branch `codex/onlook-next`
- worktree `worktrees/onlook-next`

Current status:

- the planning packet is committed on this branch
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
- `npm run lint` passes in `onlook-ui/`
- `npm run build` passes in `onlook-ui/`
- `npm run dev -- --hostname 127.0.0.1 --port 3000` serves `GET /` successfully

Practical meaning:

- the sandbox app is now real, bootable, and was a valid base for the first feature-wiring slice

### 2.6 First-slice shell validation
Verified locally after the first bounded UI slice:

- `onlook-ui/` now contains the typed review API layer under `lib/`
- `onlook-ui/` now contains the slice-1 shell components under `components/`
- the sandbox shell renders:
  - run selector
  - pipeline pane
  - tree pane
  - details pane shell
- runtime smoke through the sandbox dev server caused real backend requests for:
  - `GET /api/v1/review/nrc-aps/runs`
  - `GET /api/v1/review/nrc-aps/runs/{run_id}/overview`

Practical meaning:

- the first shell slice is implemented and validated against the adopted runtime context

### 2.7 Local Onlook operator path
Verified locally against the current official Onlook development setup docs:

- Bun is installed locally
- Docker Desktop is installed and the local Supabase backend is running
- the canonical local Onlook source clone for this lane exists at `ext-onlook/`
- that clone was last verified at revision `a242be584fa9c71ca5be9e5e7a2640595c4200be`
- a same-revision sibling clone may still exist at `../onlook-lane/ext-onlook/`, but it is not the canonical debug surface for this lane
- the canonical local env files for that source tree now exist at:
  - `ext-onlook/apps/web/client/.env`
  - `ext-onlook/packages/db/.env`
- `bun db:seed` now succeeds from `ext-onlook/`
- the current proven direct source-launch path serves `GET /login` successfully at `http://127.0.0.1:3007/login`
- the dev-only demo-user login path succeeds and redirects into the app shell

Practical meaning:

- the current working Onlook path for this lane is local source development, not the hosted desktop OAuth flow
- the repo-side sandbox and the local Onlook operator path are both now real
- placeholder `CSB_API_KEY` values are sufficient for local boot and dev login only
- with a real `CSB_API_KEY`, actual project import and sandbox creation are now proven through the current CodeSandbox-backed flow
- the imported `onlook-ui` project now reaches the project route and editor shell, but not editor readiness
- the current first live blocker is preview and bridge non-readiness: the CodeSandbox-backed preview iframe does not become a usable app document, and the editor then hits bridge and theme errors instead of reaching stable edit interactions
- a temporary minimal `Next.js + TailwindCSS` control import outside tracked repo content reproduces the same preview and bridge failure under the same runtime, so the current first failure is not specific to `onlook-ui`
- same-runtime repros for both `onlook-ui` and the minimal control import show no preview-side requests to `127.0.0.1:8000` before the preview and bridge failure, so the current first failure is upstream of the repo review API seam
- archived current-lane evidence also shows a separate upstream route-init crash path during filesystem and branch initialization, including `IDBFactory is not defined` and `Invalid value used as weak map key`
- direct local write-back/editing still remains a separate proof step
- placeholder or absent `OPENROUTER_API_KEY` values still do not prove AI/chat feature readiness

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
Preferred scaffold command for this lane:

```powershell
npx create-next-app@16 onlook-ui --ts --tailwind --eslint --app --use-npm --import-alias "@/*" --disable-git --no-agents-md --no-src-dir --no-react-compiler --empty --turbopack --yes
```

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
Use direct cross-port browser calls from the sandbox app to FastAPI in the first slice.

Slice-1 fetch model is fixed to:

- client-side browser fetches only
- non-credentialed requests only
- no cookies, session dependence, or auth headers
- no frontend proxy or rewrite layer

Do not move to server-side data fetching, credentialed requests, or a frontend proxy in slice 1 without a separate reassessment.

### 4.2 Why
Verified repo facts:

- FastAPI currently allows broad CORS in `backend/main.py`
- the initial pilot only needs read-only JSON review endpoints
- the current shipped review UI uses plain browser `fetch()` calls without credential options
- adding a proxy now would widen scope before proving the sandbox lane is useful

Practical constraint:

- the current CORS posture is acceptable for plain non-credentialed browser fetches
- it is not a safe basis for quietly introducing credentialed cross-origin requests in slice 1

### 4.3 Exact frontend env
For manual shell-driven validation, use:

```powershell
$env:NEXT_PUBLIC_REVIEW_API_BASE='http://127.0.0.1:8000/api/v1/review/nrc-aps'
```

The frontend should build all review API requests from that base.

Use `NEXT_PUBLIC_REVIEW_API_BASE` only from slice-1 client components or client-side helper code.
Do not use server-side data fetching in the first slice.

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

- `ext-onlook/apps/web/client/.env`
- `ext-onlook/packages/db/.env`

Do not treat `ext-onlook/.env` as the canonical current setup contract for this lane.

When using Onlook itself:

- treat `onlook-ui/` as the intended local project source for Onlook import
- do not point Onlook at the repo root
- in the current local source Onlook path, use the proven CodeSandbox-backed local import flow for `onlook-ui/`, but do not treat direct local write-back as already proven

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
- the validate-only review test fixture passes `STORAGE_DIR` directly into runtime-root discovery, which resolves relative paths from the current working directory

Practical rule:

- use repo-relative `./../pr45-postmerge-audit/...` only for the validate-only test command in section 7.2
- resolve to absolute paths before starting the backend server in section 7.3
- do not reuse the section 7.2 relative `STORAGE_DIR` value for the backend server

### 5.5 Cross-worktree dependency rule
The adopted demo runtime is a local dependency on the sibling `pr45-postmerge-audit` worktree.

Practical rule:

- if that sibling worktree, runtime root, summary file, or database file disappears, stop and reassess
- do not silently substitute a different runtime without updating the packet and re-validating the adopted context

## 6. Exact First-Slice Component Map

### 6.1 Route shell
- `onlook-ui/app/layout.tsx`
- `onlook-ui/app/page.tsx`

### 6.2 API and state layer
- `onlook-ui/lib/review-api.ts`
- `onlook-ui/lib/review-types.ts`
- `onlook-ui/lib/review-adapter.ts`

Responsibilities:

- read-only fetches from `NEXT_PUBLIC_REVIEW_API_BASE`
- local normalization for display
- no business-logic duplication from backend services

### 6.3 UI components
- `onlook-ui/components/review-shell.tsx`
- `onlook-ui/components/run-select.tsx`
- `onlook-ui/components/header-bar.tsx`
- `onlook-ui/components/pipeline-pane.tsx`
- `onlook-ui/components/tree-pane.tsx`
- `onlook-ui/components/details-pane.tsx`

### 6.4 Slice-1 behavior boundary
Required in slice 1:

- header shell
- run selector
- load runs
- load overview
- tree rendering
- details panel shell
- explicit document-trace boundary note or link placeholder

Deferred from slice 1 unless the sandbox proves it is necessary:

- full Mermaid parity
- theme persistence parity
- run-light vs run-heavy mode parity
- document-trace migration

Reason:

- slice 1 should prove the React/Tailwind + Onlook lane is viable
- it should not immediately recreate every behavior of the current static page

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
$env:STORAGE_DIR='../pr45-postmerge-audit/backend/app/storage_test_runtime'
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
- use `onlook-ui/` as the local project source for the proven import flow
- treat direct local write-back as the next proof step, not as already-proven behavior

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
- `next build` completes without the Turbopack workspace-root warning once `next.config.ts` sets `turbopack.root`

### 7.7 Diff boundary check
```powershell
git status --short
```

Expected first-slice change boundary:

- `onlook-ui/*`
- `next_milestone_plans/onlook-plan/*`

Explicit non-commit surface:

- `.omc/state/*`

Anything broader requires explicit reassessment.

### 7.8 Local Onlook source startup, import proof, and current blocker
If the hosted desktop OAuth path is blocked, use the local source path instead.

Repo-local helper:

```powershell
./tools/start-onlook-web.ps1
```

Equivalent direct source-launch path:

```powershell
Set-Location ./ext-onlook
$env:PATH = "$env:USERPROFILE/.bun/bin;$env:PATH"
bun run dev -- --hostname 127.0.0.1 --port 3007
```

The helper and direct source-launch path both target the same local source clone. The direct source-launch path is the canonical and currently proven post-key reproduction path in this workspace.

The helper:

- starts from `ext-onlook/`
- prepends Bun to `PATH` so Onlook child processes can resolve `bun` correctly on Windows
- checks that the current canonical local env files exist
- warns if the local Supabase backend ports are not listening
- warns when placeholder `CSB_API_KEY` or `OPENROUTER_API_KEY` values are still in use

Expected current result:

- `GET http://127.0.0.1:3007/login` succeeds through the direct source-launch path
- the page shows the dev demo-user login button in development mode
- the dev-login flow redirects into the app shell
- with a real `CSB_API_KEY`, local import of `onlook-ui/` reaches project verification, completes sandbox creation, and opens the imported project route and editor shell
- current first live blocker: the preview iframe still does not become a usable app document, observed as CodeSandbox Preview interstitial or `400`, Penpal and `iframeRemote` failures, and `frameData.view.getTheme is not a function`
- the same current first live blocker also reproduces on a temporary minimal `Next.js + TailwindCSS` control import outside tracked repo content
- archived current-lane evidence also keeps alive a separate route-init crash path during filesystem and branch initialization
- this proves local operator boot, auth, import, sandbox creation, project-route reachability, and editor-shell render; it does not yet prove editor readiness, direct local write-back, or AI/chat readiness

## 8. Stop Rules
Stop and reassess if:

- the scaffold command prompts unexpectedly or emits generated agent-instruction files
- the scaffold requires touching `backend/app/review_ui/static/*`
- the sandbox cannot render the first page without backend contract changes
- direct cross-port calls require credentialed requests, server-side fetching, or early proxy work
- the adopted `pr45-postmerge-audit` runtime root, summary, or database path fails preflight
- the first slice starts duplicating backend business logic instead of consuming backend outputs
- the imported project route still fails to reach a usable preview iframe and live bridge child
- the archived filesystem and branch-init crash path reappears in current repros

## 9. Immediate Next Move
The next justified move is:

1. treat the preview and bridge failure as an operator blocker, not as a repo-code problem to patch around
2. keep `ext-onlook/` in this worktree as the canonical debug surface and treat the control-import reproduction as strong evidence that the blocker currently lives at the broader Onlook and CodeSandbox runtime boundary
3. capture one synchronized repro that records iframe body state, browser console, network, and any filesystem-init exceptions in the same run when comparing preview and route-init failures
4. only after the project route reaches stable edit interactions, attempt one tiny bounded Onlook-authored change
5. then audit exactly what files change and confirm writes stay inside `onlook-ui/*`
