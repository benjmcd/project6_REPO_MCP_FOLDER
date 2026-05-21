# 943 - Bounded Trial Capture

## Status

Status: current-main bounded trial evidence capture for the Layer 3 source-directory rendered/operator path.

Doc: `943-bounded-trial-capture.md`.

Predecessor runtime sync: `942-playwright-runtime-sync.md`.

Current main authority: `project6-origin/main` at `feabbb0e Use repo Python for Playwright runtime (#1567)`.

Trial branch: `codex/l3-bounded-trial-capture`.

Trial result: the current-main selected source-directory path is bounded trial-usable through the admitted redacted delivery/use bridge, same-origin delivery/status, internal webhook dispatch/status, and read-only projection evidence. This is not full mockup activation.

## Evidence

Canonical proof commands run from the current-main trial branch:

- `python .\tools\l3-progress-check.py`: `Layer 3 progress state check: PASS`.
- `node --check .\backend\app\review_ui\static\layer3.js`: passed.
- `git diff --check`: passed.
- `python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_bootstrap_readiness_openapi_contracts -q`: `1 passed`.
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py -q`: `24 passed`.
- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"`: `1 passed`.
- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --headed --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"`: `1 passed`.

The headed/headless rendered proof ran without `PLAYWRIGHT_PYTHON`, using the repo-standard Playwright runtime default from `playwright.config.js`.

## Covered Bounded Path

The captured proof covers:

1. source-directory scan/status;
2. material preview;
3. Gate B admission;
4. source-directory retrieval/context and qualitative analysis authority;
5. qualitative analysis/status;
6. package preview, package commit, and package review submit;
7. package replacement/supersession preview, authority, and commit;
8. handoff/export prepare;
9. external export/download prepare;
10. same-origin delivery/status;
11. source-directory provider-private redacted prepare;
12. provider-public redacted prepare/use;
13. internal webhook dispatch/status;
14. Analysis Environment and mockup live-state projection as read-only evidence.

## Boundary Result

The trial remains inside the bounded authority model:

- no full mockup activation;
- no frontend-only durable authority;
- no raw provider-private URL/token exposure;
- no direct provider-private use;
- no real provider object/network write;
- no generic connector dispatch or destination write;
- no caller-supplied destination credential;
- no new source family or broad RAG/model/provider expansion.

## Next Posture

The next useful pass is the final mockup readiness audit. That audit must classify every critical mockup operator journey as live, read-only, intentionally excluded, or explicitly blocked through current-main evidence before any full mockup activation or frontend-only durable authority can be considered.
