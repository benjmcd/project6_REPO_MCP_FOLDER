# 942 - Playwright Runtime Sync

## Status

Status: bounded harness/runtime fix for the source-directory rendered proof.

Doc: `942-playwright-runtime-sync.md`.

Predecessor current-main sync: `941-redacted-bridge-current-main-sync.md`.

Base current-main authority: `project6-origin/main` at `ec6d283c Sync Layer 3 redacted bridge runbook (#1566)`.

Implementation branch: `codex/l3-playwright-python-runtime`.

Result: the focused Layer 3 rendered proof now uses the repo-standard `python` command on Windows by default instead of `py -3.12`, while preserving `PLAYWRIGHT_PYTHON` as an override.

## Authority Boundary

This slice changes only `playwright.config.js` and the operator runbook wording. It does not alter backend runtime behavior, application routes, models, DTOs, rendered Layer 3 behavior, provider authority, package authority, mockup activation, or frontend durable authority.

The reason for the change is operational proof stability: the post-bridge source-directory rendered path passed under the repo's Python 3.11 runtime with `PLAYWRIGHT_PYTHON=python`, while the prior Windows default `py -3.12` surfaced an existing session-summary failure. The repo's package scripts already use `python`, so the Playwright web-server default now matches the rest of the local harness.

## Validation

Validated on branch `codex/l3-playwright-python-runtime` without setting `PLAYWRIGHT_PYTHON`:

- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"`: `1 passed`.
- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --headed --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"`: `1 passed`.

The canonical runbook command in `933-trial-runbook.md` no longer needs to set `PLAYWRIGHT_PYTHON=python`.

## Remaining Work

1. Run one complete bounded source-directory trial from current main with isolated runtime state and capture the exact proof evidence.
2. Perform the final mockup readiness audit after that trial is clean.
3. Keep full mockup activation and frontend-only durable authority blocked unless the final audit proves every critical journey is live, read-only, intentionally excluded, or explicitly blocked through current-main evidence.
