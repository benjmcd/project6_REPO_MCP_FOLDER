# 940 - Source-Directory Redacted Bridge Checkpoint

## Status

Status: bounded implementation checkpoint for the source-directory redacted delivery bridge selected by the `939` readiness audit.

Doc: `940-redacted-bridge.md`.

Predecessor readiness audit: `939-readiness-audit.md`.

Implementation branch: `codex/l3-source-directory-redacted-bridge`.

Base current-main authority: `project6-origin/main` at `68432ab3cbbb38234c3faf6e6bc93b45844b3794`.

Checkpoint result: the source-directory hybrid path now has an admitted redacted provider-private prepare bridge over validated source-directory external export/download delivery authority. Provider-public redacted prepare/use continues through the existing provider-public rail. Full mockup activation remains blocked.

## Slice Decision

The `939` audit proved the bounded source-directory path trial-usable through same-origin delivery/status and internal webhook dispatch/status, but left source-directory provider-redacted delivery/use explicitly blocked. This checkpoint implements the narrow bridge rather than changing the source-directory same-origin route into a raw provider route.

Canonical authority remains server-side:

1. source-directory hybrid qualitative analysis and package authority come from the reconciliation/package rows;
2. source-directory external export/download readiness validates the selected package artifact path, hash, size, and delivery authority;
3. provider-private prepare mints only a redacted durable receipt over that validated package authority;
4. provider-public prepare/use stays on the existing redacted provider-public rail.

The bridge does not admit raw provider-private URL/token exposure, direct provider-private use, provider object/network writes, connector dispatch, source expansion, package mutation, browser-storage authority, frontend-only durable authority, or full mockup activation.

## Implementation Evidence

Backend:

- `backend/app/api/layer3.py` adds `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/provider-private-signed-url/prepare`.
- `backend/app/services/layer3_source_directory_hybrid_analysis.py` validates source-directory delivery/package authority, prepares a redacted provider-private receipt, and persists durable provider-private state without exposing raw provider material.
- `backend/app/services/layer3_readiness_contract.py` now declares the source-directory hybrid external export/download prepare/deliver/status endpoints, the provider-private signed URL prepare bridge, and the existing internal webhook dispatch/status endpoints as admitted with explicit non-admission boundaries.

Rendered/operator surface:

- `backend/app/review_ui/static/layer3.js` routes source-directory provider-private prepare to the source-directory-specific bridge when the source-directory hybrid delivery authority is ready.
- The source-directory external export/download panel now exposes the redacted provider bridge status without converting same-origin delivery into raw provider delivery.
- `e2e/layer3-workbench.spec.js` proves the rendered source-directory journey calls the source-directory provider-private bridge, then the existing provider-public prepare/use rail, and still avoids global/raw provider-private prepare for this source-directory flow.

## Validation

Focused validation in this bridge lane:

- `python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_bootstrap_readiness_openapi_contracts -q`: `1 passed`.
- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py -q`: `24 passed`.
- `node --check .\backend\app\review_ui\static\layer3.js`: passed.
- Headless Chromium, `PLAYWRIGHT_PYTHON=python`, focused source-directory rendered path: `1 passed`.
- Headed Chromium, `PLAYWRIGHT_PYTHON=python`, focused source-directory rendered path: `1 passed`.
- `python .\tools\l3-progress-check.py`: `Layer 3 progress state check: PASS`.

Harness caveat: the default Playwright Python selector used `py -3.12` in this environment and surfaced an existing session-summary `GET /session/{id}` 500 during the focused run. The same focused rendered proof passes when Playwright is forced to the repo's Python 3.11 runtime with `PLAYWRIGHT_PYTHON=python`.

## Current Operator Path

The bounded current-main-selected path is now intended to be trial-usable through:

1. source-directory scan/status;
2. material preview;
3. Gate B admission;
4. hybrid authority prepare;
5. retrieval/context;
6. qualitative analysis/status;
7. package preview/commit/review;
8. package replacement/supersession preview, authority, and commit;
9. handoff/export prepare;
10. source-directory external export/download prepare;
11. same-origin delivery/status;
12. redacted provider-private prepare;
13. redacted provider-public prepare/use;
14. internal webhook dispatch/status;
15. read-only Analysis Environment and mockup live-state projection.

## Residual Work

Immediate:

1. review the bridge diff against source-directory delivery authority, provider redaction, and mockup non-activation boundaries;
2. open a narrow PR for this bridge after review;
3. after merge, re-run the focused bounded source-directory operator path from current main and update the trial runbook/checkpoint.

Mid-term:

1. standardize the Playwright Python runtime or fix the Python 3.12 session-summary failure so operator proof is not environment-sensitive;
2. refresh the bounded trial runbook/checkpoint with exact launch and proof commands;
3. run the complete bounded source-directory operator path as one trial, including internal webhook dispatch/status and provider-public redacted use;
4. reconcile every critical mockup journey as live, read-only, intentionally excluded, or explicitly blocked through current-main evidence.

Long-term:

1. perform the final full-mockup readiness audit after the bounded path trial is clean;
2. keep full mockup activation and frontend-only durable authority blocked unless that audit proves the full source-directory operator path and all named blockers are closed;
3. stop before any new source family, raw provider delivery, connector destination write, provider network/object write, or frontend durable authority unless current-main product authority explicitly admits that expansion.

## Non-Admission Boundary

This checkpoint does not admit full mockup activation, frontend-only durable authority, raw provider URL or token exposure, direct provider-private use, provider object writes, generic connector dispatch, destination writes, package payload rewrites, source expansion, RAG/vector expansion beyond the admitted deterministic source-directory path, or user-supplied provider/destination credentials.
