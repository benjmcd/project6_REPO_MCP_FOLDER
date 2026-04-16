# Onlook Pilot Plan

## 1. Purpose
Define the exact narrow pilot for starting Onlook usage in this repo from a clean worktree without changing the current live static review UI by default.

## 2. Pilot Goal
Create a separate frontend sandbox that can render the main NRC APS review page against the existing backend review APIs and serve as the only Onlook-editable surface.

Current verified state:

- the sandbox app exists at `onlook-ui/`
- the first shell slice renders the main review surface with:
  - run selector
  - pipeline pane
  - tree pane
  - details pane shell
- the current slice consumes `GET /api/v1/review/nrc-aps/runs`
- the current slice consumes `GET /api/v1/review/nrc-aps/runs/{run_id}/overview`

This pilot is successful if:

- the sandbox app can load real review data through the existing review API
- Onlook can target the sandbox app instead of the live static UI
- the pilot leaves current live UI authority untouched

## 3. Exact Scope

### In scope
- one isolated frontend app in this worktree
- one initial page: the main review page shell
- read-only consumption of existing review API endpoints
- local planning and validation needed to keep the lane bounded

### Out of scope
- replacing the current live static review UI
- immediate migration of document trace
- backend route redesign
- runtime seeding or artifact generation for validation
- repo-wide frontend platform migration

## 4. Exact Initial Surface
The first pilot should cover only the current review page shell concepts already present in:

- `backend/app/review_ui/static/index.html`
- `backend/app/review_ui/static/review.js`
- `backend/app/review_ui/static/review.css`

Initial page capabilities:

- run selector
- pipeline overview container
- filesystem tree container
- details panel shell
- navigation boundary note for document trace

Do not start with document trace first.

Reason:

- document trace adds source streaming, diagnostics tabs, and PDF/source-viewer complexity
- the main review page is the smaller proof of whether the Onlook lane is viable at all

## 5. Exact Backend API Scope
Frontend API scope for this pilot remains bounded to:

- current implemented slice:
  - `GET /api/v1/review/nrc-aps/runs`
  - `GET /api/v1/review/nrc-aps/runs/{run_id}/overview`
- reserved next-slice expansion endpoints only if needed:
  - `GET /api/v1/review/nrc-aps/pipeline-definition`
  - `GET /api/v1/review/nrc-aps/runs/{run_id}/nodes/{node_id}`
  - `GET /api/v1/review/nrc-aps/runs/{run_id}/files/{tree_id}`
  - `GET /api/v1/review/nrc-aps/runs/{run_id}/files/{tree_id}/preview`

Do not expand backend scope unless the sandbox proves a concrete UI/API mismatch that cannot be handled client-side.

## 6. Proposed Repo Shape
Recommended future implementation layout inside this worktree:

- `onlook-ui/`
- `onlook-ui/app/`
- `onlook-ui/app/page.tsx`
- `onlook-ui/app/layout.tsx`
- `onlook-ui/app/globals.css`
- `onlook-ui/components/`
- `onlook-ui/lib/`

Intent:

- keep the sandbox app clearly separate from `backend/app/review_ui/static/*`
- keep path names short
- avoid a broad monorepo restructure for the first slice

Tooling boundary:

- keep sandbox frontend tooling local to `onlook-ui/*`
- do not repurpose the current repo-root `package.json` as the sandbox app manifest
- do not change backend Python dependencies for the first slice

Reason:

- this keeps the Onlook experiment isolated
- this avoids mixing Playwright root tooling with a new frontend build target
- this reduces accidental coupling between the sandbox lane and the current shipped UI

## 7. Operating Rules

### 7.1 Before using Onlook
1. The sandbox app must exist and run independently in this worktree.
2. The backend static UI remains untouched.
3. The backend review API remains the authority seam.
4. The runtime/data context used by the sandbox must be explicit, not implied from missing root-local historical fixtures.
5. The frontend-to-backend connection rule must be explicit:
   - direct cross-port API calls in slice 1
   - client-side browser fetches only in slice 1
   - non-credentialed requests only in slice 1
   Do not leave this implicit.
6. If the hosted desktop Onlook login path is blocked, use the local source development path under `ext-onlook-fix/` for the solved repo lane instead of treating hosted OAuth as a prerequisite for this lane.
7. Do not treat local Onlook boot and dev login alone as proof that project import or editing is ready; the current local lane now proves import, sandbox creation, hydrated iframe preview, trust-click recovery, and bounded host write-back, but that proof should not be flattened into a claim that the clean extracted upstream branch has already re-proven shim-free host write-back.
8. Treat `ext-onlook-fix/` as the canonical local operator and debug surface for the solved repo lane, and treat `ext-onlook-pr/` as the clean upstream packaging surface.
9. Do not alternate between sibling local Onlook clones or launch paths unless you are explicitly comparing behavior.

### 7.2 During Onlook usage
1. The lowest-risk default is to let Onlook edit a duplicate sandbox app created by `tools/copy-onlook-ui.ps1`, not `onlook-ui/` directly.
2. Importing `onlook-ui/` directly is an explicit choice that makes `onlook-ui/*` the direct host write-back target.
3. No writes are made to:
   - `backend/main.py`
   - `backend/app/api/review_nrc_aps.py`
   - `backend/app/schemas/review_nrc_aps.py`
   - `backend/app/review_ui/static/*`
   unless a separate explicit decision expands scope.
4. Any Onlook-produced change must still be reviewed like normal repo code.
5. The sandbox remains non-authoritative until promotion is explicitly approved.
6. If browser state on the default Onlook origin becomes sticky or keeps reopening an old imported project, restart local Onlook on a fresh port such as `3011` instead of reusing the stale browser origin blindly.

### 7.3 After Onlook usage
Every saved sandbox iteration must be classified as one of:

- discard
- keep in sandbox only
- candidate for promotion review

Do not silently treat saved Onlook edits as live-product truth.

## 8. Validation Rules

### 8.1 Baseline validation before frontend work
Keep one narrow validate-only review slice passing from this clean worktree or another explicitly adopted clean surface.

Current already-supported slice:

- `backend/tests/test_review_nrc_aps_catalog.py`
- `backend/tests/test_review_nrc_aps_api.py`

with an explicitly adopted runtime root when needed.

### 8.2 Pilot validation after frontend work
Minimum acceptance for the sandbox app:

1. app boots locally
2. run selector loads from the live review API seam
3. overview/pipeline data renders without backend contract changes
4. chosen API connection rule works consistently in local development
5. slice-1 browser fetches work without cookies, sessions, or auth headers
6. generated sandbox-local `.gitignore` remains intact after scaffold and covers local build/env artifacts
7. no changes leak into the current static UI files
8. git diff stays limited to the sandbox lane plus intentional planning updates
9. local Onlook source development can boot and pass the dev-login flow without touching live static UI files
10. with a real `CSB_API_KEY`, local project import and sandbox creation can complete for `onlook-ui/` and reach the project route and editor shell without touching live static UI files
11. with the committed sandbox-app compatibility fix in place, a fresh local import of `onlook-ui/` now produces a preview that hydrates and loads the populated review shell
12. the same fresh sandbox now renders the populated review shell inside the Onlook iframe and editor shell, not just in a top-level preview tab
13. from a fresh browser profile, Preview mode can clear the CodeSandbox trust interstitial and load the real sandbox app inside the Onlook iframe
14. in the preserved local operator branch, a bounded Onlook-authored save can write back into `onlook-ui/*` and the changed host file can be audited and restored clean
15. the clean extracted upstream branch remains a separate packaging surface and should not be overclaimed as end-to-end re-proven until shim-free host write-back is rechecked there
16. upstream runtime evidence from the old `Next 16` failure remains useful context for future re-upgrade work, but it no longer blocks the current repo lane

### 8.3 Promotion validation
Before any promotion decision:

1. compare sandbox behavior against the current static UI on the same backend data
2. identify any contract gaps or regressions
3. decide explicitly whether promotion means:
   - selective manual port
   - broader migration plan
   - rejection of the sandbox changes

## 9. Commit Boundaries

### Planning commit
Only the docs in `next_milestone_plans/onlook-plan/*`.

### Sandbox scaffold commit
Only the new sandbox app files and the minimum tooling needed for that app.

### Sandbox feature commits
Only incremental frontend work inside the sandbox app unless a separately approved backend blocker appears.

### Promotion commit
Separate from sandbox iteration history.

Reason:

- this preserves review clarity
- this avoids mixing planning, exploration, and live-surface migration into one diff

## 10. Stop Rules
Stop and reassess if any of these happen:

- the pilot requires immediate backend redesign
- the pilot requires direct edits to `backend/app/review_ui/static/*` to be useful
- the pilot requires credentialed browser requests or an early proxy/rewrite layer
- the adopted `pr45-postmerge-audit` runtime root, summary, or database is unavailable
- the path or toolchain shape starts forcing a broad repo restructure
- the sandbox cannot reach acceptable parity without excessive duplicated logic

## 11. Recommended Next Move
Use `impl-plan.md` as the bridge from the now-solved local repo lane into the clean upstream packaging split.

For lowest-risk local use:

1. create a duplicate sandbox target with `tools/copy-onlook-ui.ps1`
2. import that duplicate into Onlook
3. keep `onlook-ui/` untouched unless direct canonical write-back is the explicit goal

Do not broaden repo scope beyond the sandbox app until the clean extracted upstream branch is either sent upstream or re-proven shim-free end-to-end.
