## Purpose

This note freezes the current upstream-facing classification for the local Onlook blocker in this lane.

Use it together with the local artifact bundle in `archive/upstream-issue.md` and the concrete repro artifacts under `archive/`.

## Current Classification

Fresh clean-clone repro on Windows shows that local Onlook can:

- boot in source-dev mode
- complete demo-user login
- import a project with a real `CSB_API_KEY`
- create a sandbox
- open the project route and render the editor shell

But the editor still does not reach a usable preview or stable bridge child.

This is not currently specific to `onlook-ui`. A temporary minimal `Next.js + TailwindCSS` control app fails the same way in the same runtime.

## Proven Facts

- both `onlook-ui` and the control import reach `/project/...`
- both hit the same preview boundary:
  - `*.csb.app`
  - `CodeSandbox Preview`
  - `400`
  - `iframeRemote is null`
  - `frameData.view.getTheme is not a function`
- neither repro reaches preview-side requests to `127.0.0.1:8000` before failure
- in the fresh clean-clone repro, a forced click on `Yes, proceed to preview` is accepted but remains a no-op
- the same clean runtime also logs:
  - `ReferenceError: IDBFactory is not defined`
  - `TypeError: Invalid value used as weak map key`

## What This Proves

- the current first blocker is upstream of the repo review API seam
- the current blocker is not yet justified as a repo product-code fault
- the trust/interstitial page is not the sole explanation
- route-init/filesystem faults are current and co-occurring evidence, not just archived history

## What Remains Unproven

- strict causal ordering between preview failure and route-init/filesystem faults
- editor readiness
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

## Current Upstream State

As of 2026-04-15, the current relevant upstream issue state is:

- `onlook-dev/onlook#2336` is `closed`
- `onlook-dev/onlook#3087` is `open`
- `#3087` currently has no comments

This means the narrowest correct upstream follow-up is:

1. do not open a brand-new issue yet
2. do not treat `#2336` as the main update target, because it was closed and redirected to documentation
3. add a focused update to `#3087`, because it is the still-open issue closest to the current local repro

## Suggested Upstream Update

Suggested comment body:

> Fresh Windows repro on a clean same-SHA local clone still hits this issue.
>
> What is now proven:
> - local source-dev boot works
> - demo-user login works
> - import works with a real `CSB_API_KEY`
> - sandbox creation works
> - project route and editor shell render
>
> What still fails:
> - the preview iframe remains at `CodeSandbox Preview` / `400`
> - `iframeRemote is null`
> - `frameData.view.getTheme is not a function`
> - no preview-side requests reach the local app before failure
>
> New detail:
> - a forced click on `Yes, proceed to preview` is accepted but remains a no-op in this flow
> - the same clean runtime also logs co-occurring route-init/filesystem faults:
>   - `ReferenceError: IDBFactory is not defined`
>   - `TypeError: Invalid value used as weak map key`
>
> This same failure class reproduces on both the real imported app and a minimal Next.js + Tailwind control app, so the current first blocker does not appear repo-specific.
>
> Current open question: whether the preview/interstitial failure and the route-init/filesystem faults are one causal chain or parallel defects surfacing in the same run.

## Next Correct Move

1. Keep repo product code unchanged.
2. Use the current evidence bundle to update `onlook-dev/onlook#3087`.
3. Re-establish one new fresh same-SHA local clone before any further operator debugging after that update.
4. Only resume write-back proof after the project route reaches stable edit interactions.
