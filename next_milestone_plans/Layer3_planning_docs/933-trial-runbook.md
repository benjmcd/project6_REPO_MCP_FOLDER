# Layer 3 Source-Directory Trial Runbook

Doc: `933-trial-runbook.md`.

Status: bounded trial-usable checkpoint for the current source-directory rendered/operator path through redacted provider delivery after PR `#1565`.

Predecessor current-main sync doc: `932-post1550-sync.md`.

Predecessor trial checkpoint: PR `#1552` source-directory scan/status to same-origin hybrid delivery proof at `1613db32127d4a411c0aeb3f1e88f535a56c7215`.

Base authority: `project6-origin/main` at `336f119f Add source-directory redacted delivery bridge (#1565)`.

Merged source PRs:

- PR `#1554`: source-directory internal webhook backend dispatch/status, merge commit `56953746f1e330681dc93e098146c6a9ef933384`.
- PR `#1555`: rendered source-directory internal webhook dispatch/status control, merge commit `2f0721bf44108eddfdfa0661d1f3b42fb84f5a1c`.
- PR `#1556`: rendered source-directory webhook live-server proof, merge commit `aeccceaa115ed3b613dfc32f67336bbb6bf8298c`.
- PR `#1565`: source-directory provider-private redacted prepare bridge and rendered provider-public redacted use proof, squash merge `336f119f`.

Recent proof branches include `codex/l3-webhook-proof` and `codex/l3-source-directory-redacted-bridge`.

Recent proof titles include `Prove rendered source-directory webhook path` and `Add source-directory redacted delivery bridge`.

GitHub gates for PRs `#1554`, `#1555`, `#1556`, and `#1565`: merged to current main with required checks passing and no admitted unresolved review/comment blocker before merge.

Changed live authority after PRs `#1554` through `#1565`:

- `backend/app/api/layer3.py` and supporting services admit source-directory internal webhook dispatch/status from server-owned handoff/package authority without caller-supplied durable destination authority.
- `backend/app/review_ui/static/layer3.js` and the rendered `/review/layer3` source-directory panels expose source-directory internal webhook dispatch/status controls and source-directory redacted provider bridge controls.
- `backend/tests/review_browser_server.py` installs deterministic browser-proof webhook authority and transport capture for isolated live-server verification.
- `backend/tests/review_browser_fixture.py` captures and restores the internal webhook transport patch.
- `e2e/layer3-workbench.spec.js` extends the focused proof `Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path` through rendered internal webhook dispatch/status and admitted redacted provider-private/provider-public delivery/use.

## Trial-Usable Checkpoint

Current main now has a bounded, server-authoritative, repeatable proof for the source-directory path from rendered source scan through same-origin hybrid delivery, redacted provider delivery/use, and source-directory internal webhook dispatch/status:

1. `/review/layer3` rendered source-directory scan submits only the admitted client request id.
2. Rendered source-directory status replays the server-owned ingestion batch.
3. Rendered source-directory material preview and Gate B admission commit a session without exposing raw absolute paths, file bytes, or caller-controlled source expansion.
4. Live API proof continues through source-directory vector retrieval, hybrid context packet, qualitative analysis, analysis status, package commit, package review submit, handoff/export prepare, and external export/download prepare.
5. `/review/layer3 #source-directory-hybrid-external-export-download-delivery-panel` verifies delivery status and submits browser-managed same-origin attachment-form delivery.
6. `/review/layer3 #source-directory-hybrid-internal-webhook-panel` dispatches against server-owned source-directory package/handoff authority and verifies status without accepting raw destination URL, token, header, payload, package, or provider URL authority from the browser.
7. The proof admits only the source-directory provider-private redacted prepare bridge and the existing provider-public redacted prepare/use rail; it rejects raw provider URL/token exposure, global/raw provider-private prepare for the source-directory flow, package mutation, raw mixed materialize, connector handoff path expansion, and frontend-only durable authority.

This checkpoint is trial-usable because the path is repeatable from current main with isolated test runtime state and proves the critical redaction, same-origin delivery, provider-public redacted use, and internal webhook authority boundaries. It is not a claim that every middle lifecycle step is fully manual-click rendered in one uninterrupted operator flow; the middle retrieval, context, qualitative analysis, package lifecycle, review, and prepare steps are live API-proven using server-authored authority after the rendered Gate B session.

## Minimal Operator Runbook

Use a clean worktree at current `project6-origin/main`. Do not run this from the preserved dirty root checkout.

1. Confirm authority:

   ```powershell
   git fetch project6-origin --prune
   git status --short --branch
   git rev-parse HEAD
   git rev-parse project6-origin/main
   ```

2. Run static/progress checks:

   ```powershell
   python ./tools/l3-progress-check.py
   node --check ./backend/app/review_ui/static/layer3.js
   git diff --check
   ```

3. Run focused backend proof:

   ```powershell
   python -m pytest ./backend/tests/test_layer3_api.py::test_layer3_bootstrap_readiness_openapi_contracts -q
   python -m pytest ./backend/tests/test_layer3_source_directory_vector_retrieval.py -q
   ```

4. Run both browser modes for the current trial path:

   ```powershell
   $env:PLAYWRIGHT_PYTHON = 'python'
   npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"
   npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --headed --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"
   ```

5. Treat the checkpoint as clean only if the proof shows exactly the admitted source-directory provider-private redacted prepare bridge and provider-public redacted prepare/use rail, still shows no requests to `/source/mixed-corpus/materialize`, `/handoff/connector`, generic/raw source-directory provider-private prepare, raw provider-private direct use, or `/package/mutation`, and rendered text still avoids absolute local paths, raw payload paths, file bytes, webhook tokens/headers, raw webhook destinations, raw package payloads, raw provider-private tokens, and raw HTTP/HTTPS provider URLs.

## Remaining Whole-Program Sequence

Immediate next pass:

1. Standardize the rendered proof runtime so operators do not need to override `PLAYWRIGHT_PYTHON=python`; the default Python 3.12 selector previously surfaced an existing session-summary `GET /session/{id}` 500.
2. Run one complete bounded source-directory trial from current main with isolated runtime state and capture the exact proof evidence.
3. Perform the final mockup readiness audit only after that bounded trial is clean.

Mid-term passes:

1. Keep the runbook and checkpoint docs aligned with the current bounded source-directory path, including redacted provider delivery/use.
2. Re-run headed and headless Chromium proofs after every rendered-control addition and compare request surfaces, console/page errors, overflow, stale response handling, and forbidden payload keys.
3. Extend Analysis Environment/mockup projection only as read-only evidence of live state, explicit exclusion, or explicit blocker status.
4. Keep broad source expansion, broader RAG/model/provider behavior, auth/security expansion, real provider object/network writes, connector destination writes, and frontend-only durable authority blocked until a current-main authority doc and implementation slice admit each one.

Long-term closeout:

1. Every critical mockup operator journey must be classified as live, read-only, intentionally excluded, or explicitly blocked by current-main evidence.
2. A final readiness audit must prove the bounded path, durable state owners, browser-storage policy, security/redaction posture, headed/headless parity, isolated runtime setup, and residual blocker list.
3. Only after that audit should full mockup activation or frontend-only durable authority be considered.

## Non-Admission Boundary

This checkpoint doc introduces no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior, executable test behavior, production UI behavior, connector handoff, caller-supplied destination write, package mutation, source expansion, RAG/model/provider expansion, browser-storage authority, frontend-only durable authority, or full mockup program activation.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Did current main close the prior source-directory internal webhook gap? | Yes for backend dispatch/status, rendered source-directory dispatch/status controls, and headed/headless live-server proof through that rendered control path. |
| Does this authorize provider-private or provider-public URL runtime? | It authorizes only the source-directory provider-private redacted prepare bridge and existing provider-public redacted prepare/use rail. Direct provider-private use, raw provider URLs/tokens, real provider object/network writes, and frontend-only durable authority remain blocked. |
| Does this authorize generic connector handoff or caller-supplied webhook destinations? | No. The proof avoids `/handoff/connector`, uses server-owned dispatch authority, and checks that raw destination, token, header, provider URL, and package payload authority do not leak from the browser. |
| Is the middle lifecycle now one uninterrupted manual-click rendered operator flow? | Partially. The focused rendered proof drives the current admitted path through server-authored authority and rendered controls where current main admits them, but the checkpoint remains a bounded trial proof rather than a claim that every middle lifecycle step is a manual-click-only flow. |
| Is another broad planning pass more valuable than implementation after this checkpoint? | No, unless current-main proof fails. The next useful pass is runtime standardization, complete bounded trial capture, and final mockup readiness audit. |
| Does this activate the full mockup program? | No. Full activation remains blocked until final readiness audit closure. |

## Next Posture

Next exact posture: `standardize_post1565_bounded_trial_runtime_then_final_mockup_readiness_audit`.
