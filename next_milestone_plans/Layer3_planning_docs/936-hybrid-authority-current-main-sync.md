# 936 - Source-Directory Hybrid Authority Bridge Current-Main Sync

## Status

Status: current-main sync and bounded trial-usable checkpoint for `source_directory_hybrid_authority_generation_operator_bridge`.

Doc: `936-hybrid-authority-current-main-sync.md`.

Predecessor implementation doc: `935-hybrid-authority-implementation.md`.

Merged PR: `#1560`.

Source branch: `codex/l3-hybrid-authority-bridge`.

Implementation commit: `5fe4fe29`.

CI remediation commit: `55a67378771a21a47b46fe934eb0c3b9f8d18c8f`.

Merge commit: `225954dc665084b2320ff955d517acf29803cc10`.

Base authority before implementation: `project6-origin/main` at `d8a3cc3b6e723fb1b29adad34be0e9a2bb54da18`.

Synced route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-authority/prepare`.

Synced rendered control: `/review/layer3 #source-directory-hybrid-authority-prepare`.

## Merge Gate

PR `#1560` merged on `2026-05-21T11:13:47Z`.

GitHub gate before merge:

- `backend-layer3-api`: `SUCCESS` in `3m33s`.
- `test`: `SUCCESS` in `4m29s`.
- Comments: `0`.
- Reviews: `0`.
- Review threads: `0`.
- Unresolved review threads: `0`.
- Merge state: `CLEAN`.
- Mergeable state: `MERGEABLE`.

The first PR check run failed because the rendered button label `Prepare Hybrid Authority` matched an existing raw-mixed deferred-control guard that searches button names for `auth`. The remediation commit changed only the operator-facing and busy-state label to `Prepare Hybrid Packet`; route names, DOM ids, state names, backend service names, request contracts, and proof semantics remained authority-scoped.

## Current-Main Authority

Current main now includes a production server-owned bridge from source-directory Gate B/session/material authority to the source-directory hybrid middle-lifecycle authority payload. The browser prepares the payload by sending only `client_request_id` and `session_id` to the production route. The route derives the text-index and embedding-vector-index authority from the admitted source-directory material snapshot by reusing the existing source-directory text-index and embedding-vector-index owner services.

The focused rendered E2E no longer calls `POST /__test/layer3/source-directory-hybrid-authority`. The bounded operator path now runs from rendered source-directory scan/status through material preview, Gate B, production hybrid authority prepare, retrieval/context, qualitative analysis/status, package commit, package review submit, handoff/export prepare, external export/download prepare, same-origin delivery/status, and internal webhook dispatch/status without test-helper authority in the middle-lifecycle start.

## Post-Merge Validation

Validation run before the follow-up docs sync:

- `python -m py_compile ./backend/app/services/layer3_source_directory_hybrid_authority.py`: `PASS`.
- `node --check ./backend/app/review_ui/static/layer3.js`: `PASS`.
- `python -m pytest ./backend/tests/test_layer3_page.py -q`: `16 passed`.
- `python -m pytest ./backend/tests/test_layer3_source_directory_vector_retrieval.py -q`: `22 passed`.
- Headless Chromium focused proof for `Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path`: `PASS`.
- Headed Chromium focused proof for the same path: `PASS`.
- Representative failing-slice rerun after remediation in headless Chromium: `3 passed`.
- Representative failing-slice rerun after remediation in headed Chromium: `3 passed`.
- Full local Chromium Playwright suite after remediation: `68 passed`.
- GitHub `backend-layer3-api` after remediation: `SUCCESS`.
- GitHub `test` after remediation: `SUCCESS`.
- Post-merge `project6-origin/main` refresh: `225954dc665084b2320ff955d517acf29803cc10`.
- `git diff --stat project6-origin/main HEAD`: no tree diff.
- `python ./tools/l3-progress-check.py`: `PASS`.

## Minimal Operator Runbook

Use a clean worktree at current `project6-origin/main`. Do not run this from a preserved dirty root checkout.

1. Confirm authority:

   ```powershell
   git fetch project6-origin --prune
   git status --short --branch
   git rev-parse HEAD
   git rev-parse project6-origin/main
   ```

2. Run static and progress checks:

   ```powershell
   python ./tools/l3-progress-check.py
   node --check ./backend/app/review_ui/static/layer3.js
   git diff --check
   ```

3. Run focused backend proof:

   ```powershell
   python -m py_compile ./backend/app/services/layer3_source_directory_hybrid_authority.py
   python -m pytest ./backend/tests/test_layer3_page.py -q
   python -m pytest ./backend/tests/test_layer3_source_directory_vector_retrieval.py -q
   ```

4. Run both browser modes for the current source-directory path:

   ```powershell
   $env:CI='1'; npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"
   $env:CI='1'; npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --headed --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"
   ```

5. Treat the checkpoint as clean only if the proof still shows no `POST /__test/layer3/source-directory-hybrid-authority`, no requests to `/source/mixed-corpus/materialize`, `/handoff/connector`, provider-private URL routes, provider-public URL routes, or package-mutation routes, and no browser-supplied index hashes, raw paths, file bytes, provider URLs, connector destinations, webhook destinations, package payloads, browser-storage authority, or frontend durable authority.

## Remaining Whole-Program Sequence

Immediate next pass:

1. Re-audit current-main source-directory package replacement/supersession proof coverage now that the Gate B to hybrid authority bridge is production-backed.
2. If current main already proves package replacement/supersession in the bounded source-directory path, record that as a no-new-runtime checkpoint.
3. If the proof gap remains, select the smallest source-directory package replacement/supersession rendered path proof or control drift fix.
4. Do not activate full mockup behavior from this sync alone.

Mid-term passes:

1. Complete any remaining package replacement/supersession proof gap in the source-directory operator path.
2. Re-run headed and headless Chromium after each rendered-control addition and compare request surfaces, stale-state handling, disabled states, console/page errors, and forbidden payload keys.
3. Keep Analysis Environment/mockup projection evidence-bound: each critical mockup journey must be live, read-only, intentionally excluded, or explicitly blocked by current-main evidence.
4. Keep provider-private signed URL runtime, provider-public URL runtime, broader source/RAG/model/provider behavior, auth/security expansion, and frontend-only durable authority blocked until separate current-main authority admits them.

Long-term closeout:

1. Produce a final whole-program readiness audit over the bounded path, current-main runbook, isolated runtime setup, browser-storage policy, redaction/security posture, headed/headless parity, and residual blocker list.
2. Only after that audit should full mockup activation or frontend-only durable authority be considered.

## Non-Admission Boundary

This sync introduces no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior, executable test behavior, production UI behavior, provider-private signed URL runtime admission, provider-public URL runtime admission, connector dispatch, caller-supplied destination write, package mutation, source expansion, broader RAG/model/provider behavior, browser-storage authority, frontend-only durable authority, auth/security expansion, or full mockup program activation.

Frontend-only durable authority remains `false`.

Full mockup program activation remains `false`.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Is the implementation current-main authority now? | Yes. PR `#1560` merged to `project6-origin/main` at `225954dc665084b2320ff955d517acf29803cc10`. |
| Did GitHub checks and review surfaces settle before merge? | Yes. Both checks passed, comments and reviews were empty, review threads were `0`, and merge state was `CLEAN`. |
| Did the CI remediation weaken the authority contract? | No. It only changed the rendered button label from `Prepare Hybrid Authority` to `Prepare Hybrid Packet`; route, service, id, request, and proof contracts remain unchanged. |
| Is test-helper authority still in the bounded source-directory operator path? | No. The focused rendered E2E clicks `#source-directory-hybrid-authority-prepare` and asserts the production prepare request carries only `client_request_id` and `session_id`. |
| Does this complete package replacement/supersession proof? | Not by itself. The next immediate pass must re-audit whether current main already proves that source-directory package replacement/supersession path or needs one more bounded proof/control slice. |
| Does this activate the full mockup program? | No. Full activation remains blocked pending package replacement/supersession proof disposition and final whole-program readiness audit. |

## Next Posture

Next exact posture: `audit_source_directory_package_replacement_supersession_proof_after_hybrid_authority_current_main_sync`.
