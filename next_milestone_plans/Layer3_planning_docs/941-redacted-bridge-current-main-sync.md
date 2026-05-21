# 941 - Source-Directory Redacted Bridge Current-Main Sync

## Status

Status: post-merge current-main sync for the source-directory redacted delivery bridge.

Doc: `941-redacted-bridge-current-main-sync.md`.

Predecessor bridge checkpoint: `940-redacted-bridge.md`.

Merged PR: `#1565`, `Add source-directory redacted delivery bridge`.

Current main authority: `project6-origin/main` at `336f119f Add source-directory redacted delivery bridge (#1565)`.

Sync branch: `codex/l3-post1565-trial-runbook`.

Sync result: current main now includes the source-directory hybrid provider-private redacted prepare bridge and the rendered proof path through provider-public redacted use. The bounded source-directory path is current-main trial-usable through the admitted redacted delivery/use bridge, same-origin delivery/status, internal webhook dispatch/status, and read-only projection evidence. Full mockup activation remains blocked.

## Current-Main Proof

Validated on current main after PR `#1565` merged:

- `python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_bootstrap_readiness_openapi_contracts -q`: `1 passed`.
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py -q`: `24 passed`.
- `node --check .\backend\app\review_ui\static\layer3.js`: passed.
- Headless Chromium, `PLAYWRIGHT_PYTHON=python`, focused source-directory rendered path: `1 passed`.
- Headed Chromium, `PLAYWRIGHT_PYTHON=python`, focused source-directory rendered path: `1 passed`.
- `python .\tools\l3-progress-check.py`: `Layer 3 progress state check: PASS`.

The focused rendered proof is `Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path` in `e2e/layer3-workbench.spec.js`.

## Current Bounded Operator Path

Current main is proven through:

1. source-directory scan/status;
2. material preview;
3. Gate B admission;
4. hybrid context/retrieval/qualitative analysis authority;
5. qualitative analysis/status;
6. package preview, package commit, and package review submit;
7. replacement/supersession preview, authority, and commit;
8. handoff/export prepare;
9. external export/download prepare;
10. same-origin delivery/status;
11. source-directory provider-private redacted prepare;
12. provider-public redacted prepare/use;
13. internal webhook dispatch/status;
14. Analysis Environment and mockup live-state projection as read-only evidence.

This is a bounded trial-usable path, not a full activation claim. The proof remains deliberately constrained to server-authoritative source-directory material, deterministic package authority, redacted provider receipts, and read-only projection surfaces.

## Non-Admission Boundary

Still not admitted:

- full mockup activation;
- frontend-only durable authority;
- raw provider-private URL or token exposure;
- direct provider-private use;
- provider object writes or real provider network writes;
- generic connector dispatch or destination writes;
- caller-supplied destination credentials;
- package payload rewrites outside the admitted replacement/supersession authority;
- new source families or broader RAG/model/provider runtime expansion.

## Immediate Next Work

1. Standardize the rendered proof runtime so the focused Playwright path does not depend on overriding `PLAYWRIGHT_PYTHON=python`; the default Python 3.12 selector previously surfaced an existing session-summary `GET /session/{id}` 500.
2. Refresh the minimal operator runbook so the canonical commands use the current proven path, including source-directory provider-private prepare and provider-public redacted use.
3. Run one complete bounded source-directory trial from current main with isolated runtime state and capture the exact proof evidence.
4. After that trial, perform a final mockup readiness audit that classifies every critical mockup operator journey as live, read-only, intentionally excluded, or explicitly blocked.

## Stop Conditions

Stop before any new source family, raw provider delivery, real provider object/network write, connector destination write, frontend durable authority, or full mockup activation unless current-main product authority explicitly admits that expansion.
