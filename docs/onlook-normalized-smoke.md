# Onlook Normalized Smoke

Current scoped status:
- This is a current-project first gate, not a general Onlook gate.
- The default pair now comes from [`tools/onlook-active-pair.json`](../tools/onlook-active-pair.json). It is the single source of truth for the active verified pair.
- The saved default-proof metadata lives in [`tools/onlook-active-pair.json`](../tools/onlook-active-pair.json).
- The current runtime-clone provenance also comes from [`tools/onlook-active-pair.json`](../tools/onlook-active-pair.json) and the ledger it references.
- The currently passing runtime surface is the restored runtime-clone state recorded in the referenced proof ledger.
- The active verified pair also lives in [`tools/onlook-active-pair.json`](../tools/onlook-active-pair.json).
- Read `projectUrl` and `previewOrigin` there for the live pair instead of pinning them in this doc.
- The canonical current proof pointer is `tools/onlook-active-pair.json`.
- Do not pin a ledger path from this doc. Read `sourceLedgerPath` and `verifiedAt` from `tools/onlook-active-pair.json` for the live proof pointer.
- Default invocation validates the referenced durable proof ledger plus the local helper surfaces and runtime-clone provenance before it trusts the active pair.
- Proof-pointer or helper commits can advance repo `HEAD` without invalidating the active pair when the referenced helper fingerprint and the runtime-clone state still match.
- The current-project first gate also requires a real `CSB_API_KEY` to reach the local Onlook web runtime because `sandbox.start` must create a browser session for the active sandbox.
- The supported low-friction path is `ext-onlook-fix/apps/web/client/.env.local`, which overrides the placeholder key in `apps/web/client/.env` during wrapper startup.
- A placeholder parent-shell `CSB_API_KEY` does not block the gate when `ext-onlook-fix/apps/web/client/.env.local` holds the real key.
- `./tools/check-onlook.ps1 -ShowGateStatusOnly` is the quickest read-only way to inspect the current default pair, proof source, and `CSB_API_KEY` readiness before running the gate.
- Older active pairs are historical context only. Read `statusReason` in `tools/onlook-active-pair.json` or Git history if prior defaults matter; do not pin them in this doc.
- The currently verified browser mode is headed Chrome with a fresh browser context.
- The currently covered mouse route-chip checks are only:
  - `Workbench Compare`
  - `Document Trace`

Normalization steps for the current pair:
1. Open the host project URL.
2. If the host lands on `/login`, use `DEV MODE: Sign in as demo user`.
3. If the embedded preview shows the CodeSandbox trust interstitial, clear it.
4. Force the host editor mode to `Preview`.
5. Verify the root review shell is visible before starting the smoke verdict.
6. Restore the preview to root review before each covered route verdict.

Runtime note:
- The wrapper will start the local Onlook backend first when the dev-login ports are missing, then start the web host if `3011` is down.
- The default host origin for this gate is `http://127.0.0.1:3011`; `3000` remains the broader local Onlook web default outside this specific gate.
- Host startup now imports the client env surface into the startup process, with `.env.local` overriding `.env`, before it launches the Onlook web runtime.
- If `3011` is down but a stale Onlook preload helper is still holding `8083`, the wrapper will clear that recoverable stale helper before retrying host startup.
- If startup fails before Chrome opens, the wrapper still writes a fail-closed ledger with the startup classification.
- Use `host-started-by-wrapper` and `host-already-up` for host runtime state.
- Do not describe this gate as a warm browser/session proof. The current smoke runs in a fresh browser context.

Interpretation:
- If login, trust, preview-mode, root-review restoration, or overlay-clear normalization fails, classify that as current-pair session/runtime or tooling state, not immediate general product proof.
- A passing normalized smoke does not prove that there never was a product bug. It only proves that the current fixed runtime surface passes the current covered route checks on the current pair.
- The authoritative smoke uses headed actual Chrome and real mouse route-chip clicks only.
- Do not use direct URL typing, deep-links, or fallback navigation for the route verdict itself.
- Resume product debugging only from a failed normalized-smoke artifact for the active verified pair or an explicit override pair, or after widening coverage on purpose.
- Operator proof is broader secondary proof. It is not equivalent to this current-project first gate.
- Sandbox `onlook-ui/.env.local` is not part of this gate unless you are intentionally overriding the sandbox app away from the committed same-origin fixture route.
- Default invocation uses the active verified pair only.
- Explicit `-ProjectUrl` and `-PreviewOrigin` are an override pair.
- If `tools/onlook-active-pair.json` is missing, stale, or no longer matches the referenced proof ledger, local helper surfaces, or runtime-clone provenance, default invocation fails closed.
- `no-active-default` means the gate has no trustworthy default pair and requires explicit override args.

Fail-closed buckets:
1. host startup / 3011 unavailable
2. auth / dev-login failure
3. preview frame missing
4. CodeSandbox trust interstitial not cleared
5. preview mode not reached
6. root review not restored
7. loading overlay never cleared
8. route-chip mouse verdict failed after normalization
9. unclassified normalization/tooling failure

Current-project first-gate command:
```powershell
./tools/run-onlook-normalized-smoke.ps1
```

Explicit override pair command:
```powershell
./tools/run-onlook-normalized-smoke.ps1 -ProjectUrl 'http://127.0.0.1:3011/project/<project-id>' -PreviewOrigin 'https://<preview-origin>/'
```

Smoke verdict:
- `Workbench Compare` must navigate from `/` to `/workbench-compare` via a real mouse route-chip click.
- `Document Trace` must navigate from `/` to `/document-trace` via a real mouse route-chip click.
- Any failure should be treated as a new current-pair artifact and investigated from that normalized state.
