# Layer 3 Source-Directory Trial Runbook

Doc: `933-trial-runbook.md`.

Status: bounded trial-usable checkpoint for `source_directory_scan_to_handoff_delivery_internal_webhook_after_pr1556`.

Predecessor current-main sync doc: `932-post1550-sync.md`.

Predecessor trial checkpoint: PR `#1552` source-directory scan/status to same-origin hybrid delivery proof at `1613db32127d4a411c0aeb3f1e88f535a56c7215`.

Base authority: `project6-origin/main` at `aeccceaa115ed3b613dfc32f67336bbb6bf8298c`.

Merged source PRs:

- PR `#1554`: source-directory internal webhook backend dispatch/status, merge commit `56953746f1e330681dc93e098146c6a9ef933384`.
- PR `#1555`: rendered source-directory internal webhook dispatch/status control, merge commit `2f0721bf44108eddfdfa0661d1f3b42fb84f5a1c`.
- PR `#1556`: rendered source-directory webhook live-server proof, merge commit `aeccceaa115ed3b613dfc32f67336bbb6bf8298c`.

Merged proof branch: `codex/l3-webhook-proof`.

Merged proof title: `Prove rendered source-directory webhook path`.

GitHub gates for PRs `#1554`, `#1555`, and `#1556`: merged to current main with required checks passing and no admitted unresolved review/comment blocker before merge.

Changed live authority after PRs `#1554` through `#1556`:

- `backend/app/api/layer3.py` and supporting services admit source-directory internal webhook dispatch/status from server-owned handoff/package authority without caller-supplied durable destination authority.
- `backend/app/review_ui/static/layer3.js` and the rendered `/review/layer3` source-directory panels expose source-directory internal webhook dispatch/status controls.
- `backend/tests/review_browser_server.py` installs deterministic browser-proof webhook authority and transport capture for isolated live-server verification.
- `backend/tests/review_browser_fixture.py` captures and restores the internal webhook transport patch.
- `e2e/layer3-workbench.spec.js` extends the focused proof `Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path` through rendered internal webhook dispatch/status.

## Trial-Usable Checkpoint

Current main now has a bounded, server-authoritative, repeatable proof for the source-directory path from rendered source scan through same-origin hybrid delivery and source-directory internal webhook dispatch/status:

1. `/review/layer3` rendered source-directory scan submits only the admitted client request id.
2. Rendered source-directory status replays the server-owned ingestion batch.
3. Rendered source-directory material preview and Gate B admission commit a session without exposing raw absolute paths, file bytes, or caller-controlled source expansion.
4. Live API proof continues through source-directory vector retrieval, hybrid context packet, qualitative analysis, analysis status, package commit, package review submit, handoff/export prepare, and external export/download prepare.
5. `/review/layer3 #source-directory-hybrid-external-export-download-delivery-panel` verifies delivery status and submits browser-managed same-origin attachment-form delivery.
6. `/review/layer3 #source-directory-hybrid-internal-webhook-panel` dispatches against server-owned source-directory package/handoff authority and verifies status without accepting raw destination URL, token, header, payload, package, or provider URL authority from the browser.
7. The proof rejects provider-private signed URL, provider-public URL, package mutation, raw mixed materialize, and connector handoff path expansion.

This checkpoint is trial-usable because the path is repeatable from current main with isolated test runtime state and proves the critical redaction, same-origin delivery, and internal webhook authority boundaries. It is not a claim that every middle lifecycle step is fully manual-click rendered in one uninterrupted operator flow; the middle retrieval, context, qualitative analysis, package lifecycle, review, and prepare steps are live API-proven using server-authored authority after the rendered Gate B session.

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
   python -m pytest ./backend/tests/test_review_browser_server.py -q
   python -m pytest ./backend/tests/test_layer3_source_directory_vector_retrieval.py -k representative_mockup_scenario_source_to_output_handoff_e2e_proof -q
   python -m pytest ./backend/tests/test_layer3_source_directory_qualitative_analysis.py::test_source_directory_qualitative_analysis_external_export_download_prepare_records_readiness -q
   ```

4. Run both browser modes for the current trial path:

   ```powershell
   npm run test:e2e:chromium -- ./e2e/layer3-workbench.spec.js -g "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"
   npm run test:e2e:headed -- ./e2e/layer3-workbench.spec.js -g "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"
   ```

5. Treat the checkpoint as clean only if the proof still shows no requests to `/source/mixed-corpus/materialize`, `/handoff/connector`, `/provider-private-signed-url`, `/provider-public-url`, or `/package/mutation`, and rendered text still avoids absolute local paths, raw payload paths, file bytes, webhook tokens/headers, raw webhook destinations, raw package payloads, and HTTP/HTTPS provider URLs.

## Remaining Whole-Program Sequence

Immediate next pass:

1. Merge the branch-local rendered middle lifecycle control only if the focused static checks and headed/headless live-server proof stay clean.
2. Select the smallest Gate B to source-directory hybrid authority/index-generation bridge so the rendered middle lifecycle can run from operator-visible source-directory authority instead of test-only helper authority.
3. If current main does not yet admit that bridge, freeze the exact route/control/contract boundary instead of inferring product authority.

Mid-term passes:

1. Close the Gate B to source-directory hybrid authority/index-generation bridge so the rendered middle lifecycle no longer depends on test-only helper authority.
2. Convert the remaining package replacement/supersession steps into the rendered/operator-continuous source-directory path where current main admits controls.
3. Re-run headed and headless Chromium proofs after every rendered-control addition and compare request surfaces, console/page errors, overflow, stale response handling, and forbidden payload keys.
4. Extend Analysis Environment/mockup projection only as read-only evidence of live state, explicit exclusion, or explicit blocker status.
5. Keep provider-private signed URL runtime, provider-public URL runtime, broad source expansion, broader RAG/model/provider behavior, auth/security expansion, and frontend-only durable authority blocked until a current-main authority doc and implementation slice admit each one.

Long-term closeout:

1. Every critical mockup operator journey must be classified as live, read-only, intentionally excluded, or explicitly blocked by current-main evidence.
2. A final readiness audit must prove the bounded path, durable state owners, browser-storage policy, security/redaction posture, headed/headless parity, isolated runtime setup, and residual blocker list.
3. Only after that audit should full mockup activation or frontend-only durable authority be considered.

## Non-Admission Boundary

This checkpoint doc introduces no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior, executable test behavior, production UI behavior, provider-private signed URL runtime admission, provider-public URL runtime admission, connector handoff, caller-supplied destination write, package mutation, source expansion, RAG/model/provider expansion, browser-storage authority, frontend-only durable authority, or full mockup program activation.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Did current main close the prior source-directory internal webhook gap? | Yes for backend dispatch/status, rendered source-directory dispatch/status controls, and headed/headless live-server proof through that rendered control path. |
| Does this authorize provider-private or provider-public URL runtime? | No. The proof explicitly avoids `/provider-private-signed-url` and `/provider-public-url`, and provider runtime admission remains separately gated. |
| Does this authorize generic connector handoff or caller-supplied webhook destinations? | No. The proof avoids `/handoff/connector`, uses server-owned dispatch authority, and checks that raw destination, token, header, provider URL, and package payload authority do not leak from the browser. |
| Is the middle lifecycle now one uninterrupted manual-click rendered operator flow? | Partially. Branch `codex/l3-middle-flow-operator` adds a rendered control that sequences retrieval/context, qualitative analysis/status, package commit, package review submit, handoff/export prepare, and external export/download prepare from server-derived authority, then populates delivery/webhook authority. The remaining interruption is the Gate B to source-directory hybrid authority/index-generation bridge, which still depends on test-only helper authority in the proof. |
| Is another broad planning pass more valuable than implementation after this checkpoint? | No, unless current-main proof fails. The next useful pass is the smallest Gate B to hybrid-authority bridge that removes test-helper authority from the rendered source-directory path, or an explicit freeze if current main does not admit that runtime bridge. |
| Does this activate the full mockup program? | No. Full activation remains blocked until final readiness audit closure. |

## Next Posture

Next exact posture: `freeze_source_directory_hybrid_authority_generation_operator_bridge_before_runtime`.
