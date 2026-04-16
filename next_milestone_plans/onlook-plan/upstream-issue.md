## Purpose

This note freezes the current upstream-facing classification after the repo-side mitigation and the local repo-lane write-back proof were both completed.

Use it together with the local artifact bundle in `archive/upstream-issue.md` and the concrete repro artifacts under `archive/`.

## Current Classification

The repo lane is no longer blocked on preview hydration.

Local source Onlook can now:

- boot in source-dev mode
- complete demo-user login
- import `onlook-ui/` with a real `CSB_API_KEY`
- create a sandbox
- open the project route and render the editor shell
- hydrate the fresh sandbox preview once the sandbox app stays on `Next 15.5.15`
- render the populated review shell inside the Onlook iframe

The repo lane is now solved locally through write-back.

The remaining upstream-facing question is not repo hydration or repo-local write-back.
It is how to package the clean extracted Onlook patch set without overstating what was proven on the preserved local shimmed branch versus the shim-free upstream-clean branch.

## Proven Facts

- the old `Next 16` failure remains real evidence for upstream compatibility work:
  - direct control previews showed `Next 15` hydrating and `Next 16` staying SSR-only
  - old fresh-import previews on `Next 16` reproduced the same non-hydrated state
- the committed sandbox-app compatibility fix keeps React `19.2.4` but pins `next` and `eslint-config-next` to `15.5.15`
- a fresh local import of the current committed `onlook-ui/` folder now creates a new CodeSandbox preview that hydrates successfully
- direct preview of that fresh sandbox now logs the `review-shell` lifecycle, fetches:
  - `GET /api/v1/review/nrc-aps/runs`
  - `GET /api/v1/review/nrc-aps/runs/{run_id}/overview`
  and loads the populated review shell
- the same fresh sandbox now renders the populated review shell inside the Onlook iframe and editor shell
- from a fresh browser profile, switching to `Preview` and accepting the CodeSandbox trust interstitial now loads the real sandbox app inside the Onlook iframe
- direct local write-back is now proven on the preserved local operator branch `ext-onlook-fix/` at `c8cf5c16`: a bounded Onlook-authored save wrote into `onlook-ui/app/page.tsx` on disk and the host file was restored clean afterward
- the clean extracted upstream-ready branch `ext-onlook-pr/` at `6d4c463a` removes the workspace-specific `/api/local-project` shim and path-registration fallback, keeps the browser directory-handle persistence path, passes `@onlook/web-client` typecheck, and passes `@onlook/web-client` build when required envs are stubbed
- the local write-back proof used the file-input import path and the preserved local shim, so the shim-free extracted branch should not yet be described as end-to-end re-proven without an additional host write-back run there

## What This Proves

- the old `Next 16` preview failure had a narrow repo-side mitigation
- the current repo lane no longer needs more product-code changes to reach hydrated preview, populated iframe render, or bounded local write-back
- upstream issue context still matters for future `Next 16` re-upgrade work and for broader Onlook runtime hardening
- the remaining upstream-facing work is packaging and, if desired, shim-free re-proof on the clean extracted branch

## What Remains Unproven

- shim-free end-to-end host write-back on the clean extracted branch
- AI/chat readiness

## Evidence

Tracked packet context:

- `README.md`
- `strategy.md`
- `pilot-plan.md`
- `impl-plan.md`

Local artifact bundle:

- `archive/upstream-issue.md`
- `archive/clean-route-check.json`
- `archive/preview-click-check.json`
- `archive/repro-web.out.log`

## Next Correct Move

1. Keep the committed `Next 15.5.15` sandbox-app mitigation in place while CodeSandbox-backed Onlook preview is part of the workflow.
2. Use `ext-onlook-pr/` at `6d4c463a` as the clean upstream-ready patch baseline rather than the preserved shimmed local branch.
3. Use the current evidence bundle for any future upstream follow-up about `Next 16` compatibility, trust/interstitial handling, or generic local-project write-back hardening.
4. Treat AI/chat readiness or shim-free end-to-end re-proof as separate follow-up work, not as reasons to reopen repo product scope.
