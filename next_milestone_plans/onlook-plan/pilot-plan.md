# Onlook Pilot Plan

## 1. Purpose
Define the exact bounded Onlook lane for using a separate sandbox frontend in this repo without changing the current live static review UI by default.

## 2. Pilot Goal
Keep a separate frontend sandbox that can cover the bounded NRC APS review UI family against the existing backend review APIs and remain the only Onlook-editable surface by default.

Current verified state:

- the sandbox app exists at `onlook-ui/`
- the sandbox now exposes these routes:
  - `/`
  - `/document-trace`
  - `/workbench-compare`
  - `/candidate-b-trace`
  - `/analyst-insight`
- the root review route consumes:
  - `GET /api/v1/review/nrc-aps/runs`
  - `GET /api/v1/review/nrc-aps/runs/{run_id}/overview`
- the document-trace route consumes the existing selector, manifest, diagnostics, normalized-text, indexed-chunks, and extracted-units review endpoints
- the analyst-insight route consumes the existing aliased POST endpoints without changing backend authority
- the compare-family routes now:
  - degrade explicitly when same-checkout compare prep is absent
  - render populated compare and Candidate-B-trace payloads when same-checkout compare prep exists locally

This pilot is successful if:

- the sandbox app can load real review data through the existing review API family
- Onlook can target the sandbox app instead of the live static UI
- the pilot leaves current live UI authority untouched

## 3. Exact Scope

### In scope
- one isolated frontend app in this worktree
- the bounded NRC APS review UI family inside that app:
  - main review
  - document trace
  - workbench compare
  - Candidate B trace
  - analyst insight
- read-only consumption of existing review API endpoints plus the existing analyst POST aliases
- local compare-data prep when populated compare-family validation is explicitly needed
- local planning and validation needed to keep the lane bounded

### Out of scope
- replacing the current live static review UI
- backend route redesign
- repo-wide frontend platform migration beyond the bounded review UI family
- automatic promotion of sandbox edits into live authority

## 4. Exact Current Sandbox Surface
The current sandbox now mirrors this bounded live review UI family:

- `backend/app/review_ui/static/index.html`
- `backend/app/review_ui/static/document_trace.html`
- `backend/app/review_ui/static/workbench_compare.html`
- `backend/app/review_ui/static/candidate_b_trace.html`
- `backend/app/review_ui/static/analyst_insight.html`

Current sandbox route capabilities:

- `/`
  - run selector
  - pipeline overview container
  - filesystem tree container
  - details panel shell
- `/document-trace`
  - document selector
  - source artifact view
  - diagnostics, normalized-text, indexed-chunks, and extracted-units tabs
- `/workbench-compare`
  - three-way source selection
  - aligned fixture selection
  - compare manifest and tab payload rendering
  - deep-link remapping back into sandbox routes
- `/candidate-b-trace`
  - compare-family selection reuse
  - Candidate B trace manifest
  - annotated PDF, raw JSON, and raw Markdown artifact views when available
- `/analyst-insight`
  - aliased stage 1/2/3 POST calls
  - chained full-flow execution

The compare-family routes keep a bounded runtime rule:

- if same-checkout compare prep is absent, they must fail soft with explicit empty-state messaging
- if same-checkout compare prep is present, they must render the same selection model and data family as the live static compare pages

## 5. Exact Backend API Scope
Frontend API scope for this sandbox family remains bounded to existing review and analyst routes only.

Current implemented families:

- main review:
  - runs
  - overview
- document trace:
  - document selector
  - trace manifest
  - diagnostics
  - normalized text
  - indexed chunks
  - extracted units
- workbench compare:
  - sources
  - targets
  - manifest
  - tab payloads
- Candidate B trace:
  - manifest
  - annotated PDF
  - raw JSON
  - raw Markdown
- analyst insight:
  - market-data integration alias
  - market-data validation alias
  - market-insight alias

Do not expand backend scope unless the sandbox proves a concrete UI/API mismatch that cannot be handled client-side.

## 6. Proposed Repo Shape
Recommended implementation layout inside this worktree:

- `onlook-ui/`
- `onlook-ui/app/`
- `onlook-ui/app/page.tsx`
- `onlook-ui/app/document-trace/page.tsx`
- `onlook-ui/app/workbench-compare/page.tsx`
- `onlook-ui/app/candidate-b-trace/page.tsx`
- `onlook-ui/app/analyst-insight/page.tsx`
- `onlook-ui/components/`
- `onlook-ui/lib/`

Intent:

- keep the sandbox app clearly separate from `backend/app/review_ui/static/*`
- keep path names short
- avoid a broad monorepo restructure for the lane

Tooling boundary:

- keep sandbox frontend tooling local to `onlook-ui/*`
- do not repurpose the current repo-root `package.json` as the sandbox app manifest
- do not change backend Python dependencies for the route-family port itself

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
5. The default runtime for the current lane is the repo-native same-checkout `backend/app/storage_test_runtime`; the older sibling adopted runtime is fallback only.
6. The frontend-to-backend connection rule must remain explicit:
   - direct cross-port API calls
   - client-side browser fetches only
   - non-credentialed requests only
7. If the hosted desktop Onlook login path is blocked, use the local source development path under `ext-onlook-fix/` for the solved repo lane instead of treating hosted OAuth as a prerequisite for this lane.
8. Do not treat local Onlook boot and dev login alone as proof that project import or editing is ready; the current local lane now proves import, sandbox creation, hydrated iframe preview, trust-click recovery, and bounded host write-back, but that proof should not be flattened into a claim that the clean extracted upstream branch has already re-proven shim-free host write-back.
9. Treat `ext-onlook-fix/` as the canonical local operator and debug surface for the solved repo lane, and treat `ext-onlook-pr/` as the clean upstream packaging surface.
10. Do not alternate between sibling local Onlook clones or launch paths unless you are explicitly comparing behavior.
11. When populated compare-family validation matters, prepare same-checkout compare data explicitly instead of assuming it exists.

### 7.2 During Onlook usage
1. The lowest-risk default is to let Onlook edit a duplicate sandbox app prepared by `tools/prep-onlook-copy.ps1`, not `onlook-ui/` directly.
2. That prepared duplicate now includes an upload-safe `.env` with only the public review API base, because Onlook intentionally skips `.env.local` during project upload.
3. Importing `onlook-ui/` directly is an explicit choice that makes `onlook-ui/*` the direct host write-back target.
4. No writes are made to:
   - `backend/main.py`
   - `backend/app/api/review_nrc_aps.py`
   - `backend/app/schemas/review_nrc_aps.py`
   - `backend/app/review_ui/static/*`
   unless a separate explicit decision expands scope.
5. Any Onlook-produced change must still be reviewed like normal repo code.
6. The sandbox remains non-authoritative until promotion is explicitly approved.
7. If browser state on the default Onlook origin becomes sticky or keeps reopening an old imported project, restart local Onlook on a fresh port such as `3011` instead of reusing the stale browser origin blindly.

### 7.3 After Onlook usage
Every saved sandbox iteration must be classified as one of:

- discard
- keep in sandbox only
- candidate for promotion review

Do not silently treat saved Onlook edits as live-product truth.
Before any duplicate-to-canonical merge-back, review the duplicate against `onlook-ui/` with `tools/diff-onlook-copy.ps1`.

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
5. the sandbox route family continues to use browser fetches without cookies, sessions, or auth headers
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
17. the document-trace route renders populated manifest and tab payloads against a live review runtime without backend contract changes
18. the analyst-insight route can complete the bounded three-stage POST flow against the existing aliased backend services
19. the compare-family routes either:
    - render explicit empty states when same-checkout compare prep is absent
    - or render populated compare-family payloads once same-checkout compare prep passes `tools/validate_wb_prep.py`
20. any compare-family population proof must come from repo-native same-checkout prep, not from silently mutating shipped static UI files or widening backend contracts
21. before any duplicate-target Onlook operator proof, `tools/run-onlook-sandbox-smoke.ps1` must pass:
    - `-Profile core` for the non-compare routes
    - `-Profile full` for the full route family when same-checkout compare prep is in scope

### 8.3 Promotion validation
Before any promotion decision:

1. compare sandbox behavior against the current static UI on the same backend data
2. review duplicate-to-canonical sandbox changes explicitly with `tools/diff-onlook-copy.ps1`
3. identify any contract gaps or regressions
4. decide explicitly whether promotion means:
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

- the lane requires immediate backend redesign
- the lane requires direct edits to `backend/app/review_ui/static/*` to be useful
- the lane requires credentialed browser requests or an early proxy/rewrite layer
- the adopted runtime context or same-checkout compare prep becomes unavailable and no bounded substitute has been audited
- the path or toolchain shape starts forcing a broad repo restructure
- the sandbox cannot reach acceptable parity without excessive duplicated logic

## 11. Recommended Next Move
Use `impl-plan.md` as the bridge from the now-solved local repo lane into the current multi-route sandbox family.

For lowest-risk local use:

1. prepare a duplicate sandbox target with `tools/prep-onlook-copy.ps1 -TargetDir onlook-ui-copy -CopyLocalEnv`
2. review the duplicate against canonical `onlook-ui/` with `tools/diff-onlook-copy.ps1 -TargetDir onlook-ui-copy`
3. import that duplicate into Onlook
4. keep `onlook-ui/` untouched unless direct canonical write-back is the explicit goal

When populated compare-family work is required:

1. seed same-checkout baseline and Candidate-A runtimes with `tools/seed_wb_compare.py`
2. generate a local Candidate-B compare bundle with `tools/run_nrc_aps_candidate_b_compare.py`
3. validate the resulting selection and recommended URLs with `tools/validate_wb_prep.py`
4. prove the hydrated full route family with `tools/run-onlook-sandbox-smoke.ps1 -Profile full`
5. if the duplicate target is the intended Onlook import, re-run that proof against the duplicate with `tools/run-onlook-sandbox-smoke.ps1 -Profile full -AppDir onlook-ui-copy`
6. if editor-side proof is required, run `tools/run-onlook-operator-proof.ps1`; it now proves duplicate-target import, trusted preview navigation, analyst flow, and duplicate-only write-back with duplicate restoration and canonical protection

Do not broaden repo scope beyond the sandbox app until the clean extracted upstream branch is either sent upstream or re-proven shim-free end-to-end.
