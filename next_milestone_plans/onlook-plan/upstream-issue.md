## Purpose

This note freezes the current upstream-facing classification after the repo-side mitigation was proven locally.

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

The remaining repo-local unknown is direct write-back/editing, not preview hydration.

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
- direct local write-back/editing is still unproven

## What This Proves

- the old `Next 16` preview failure had a narrow repo-side mitigation
- the current repo lane no longer needs more product-code changes to reach hydrated preview and populated iframe render
- upstream issue context still matters for future `Next 16` re-upgrade work and for broader Onlook runtime hardening
- the next repo-local proof step is write-back, not more preview debugging

## What Remains Unproven

- successful write-back/editing
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
2. Use the current evidence bundle for any future upstream follow-up about `Next 16` compatibility or generic Onlook runtime hardening.
3. Treat the next repo-local proof step as direct write-back/editing.
