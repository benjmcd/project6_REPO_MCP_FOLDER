# Onlook Normalized Smoke

Current scoped status:
- This is a current-project first gate, not a general Onlook gate.
- The default pair now comes from [`tools/onlook-active-pair.json`](../tools/onlook-active-pair.json). It is the single source of truth for the active verified pair.
- The saved default-proof metadata lives in [`tools/onlook-active-pair.json`](../tools/onlook-active-pair.json).
- The current runtime-clone provenance also comes from [`tools/onlook-active-pair.json`](../tools/onlook-active-pair.json) and the ledger it references.
- The currently passing runtime surface is the restored runtime-clone state recorded in the referenced proof ledger.
- The active verified pair is:
  - project URL `http://127.0.0.1:3011/project/34743ff9-9eb2-4172-a3e0-b4154853e608`
  - preview origin `https://72nw5n-3000.csb.app/`
- The canonical current proof pointer is `tools/onlook-active-pair.json`.
- Do not pin a ledger path from this doc. Read `sourceLedgerPath` and `verifiedAt` from `tools/onlook-active-pair.json` for the live proof pointer.
- Default invocation validates the referenced durable proof ledger plus the local helper surfaces and runtime-clone provenance before it trusts the active pair.
- Proof-pointer or helper commits can advance repo `HEAD` without invalidating the active pair when the referenced helper fingerprint and the runtime-clone state still match.
- The current-project first gate also requires a real `CSB_API_KEY` to reach the local Onlook web runtime because `sandbox.start` must create a browser session for the active sandbox.
- The supported low-friction path is `ext-onlook-fix/apps/web/client/.env.local`, which overrides the placeholder key in `apps/web/client/.env` during wrapper startup.
- The historical stale/unhealthy pair is retained only as prior context and is no longer a default:
  - project URL `http://127.0.0.1:3011/project/c2486161-3bad-4958-b2c9-7c6502bc76a0`
  - preview origin `https://vzyzj3-3000.csb.app/`
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
