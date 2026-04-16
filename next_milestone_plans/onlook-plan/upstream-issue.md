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

## Next Correct Move

1. Keep repo product code unchanged.
2. Re-establish one new fresh same-SHA local clone before more operator debugging.
3. Use the current evidence bundle for upstream follow-up.
4. Only resume write-back proof after the project route reaches stable edit interactions.
