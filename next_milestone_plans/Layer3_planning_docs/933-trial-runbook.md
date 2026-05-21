# Layer 3 Source-Directory Trial Runbook

Doc: `933-trial-runbook.md`.

Status: bounded trial-usable checkpoint for `source_directory_scan_to_handoff_delivery_after_pr1552`.

Predecessor current-main sync doc: `932-post1550-sync.md`.

Base authority: `project6-origin/main` at `1613db32127d4a411c0aeb3f1e88f535a56c7215`.

Merged proof PR: `#1552`.

Merged proof branch: `codex/l3-source-directory-operator-proof`.

Merged proof title: `Prove source-directory hybrid operator path`.

Merged at: `2026-05-21T08:05:38Z`.

GitHub gate for PR `#1552`: state `MERGED`, merge commit `1613db32127d4a411c0aeb3f1e88f535a56c7215`, checks `backend-layer3-api` `SUCCESS` and `test` `SUCCESS`, comments `0`, reviews `0`, reviewThreads totalCount `0`.

Changed live authority in PR `#1552`:

- `backend/app/api/layer3.py` accepts browser attachment-form delivery payloads for source-directory qualitative and hybrid external export/download delivery routes through the same request-parsing path already used by generic same-origin delivery.
- `backend/tests/review_browser_server.py` adds a deterministic source-directory hybrid authority fixture for the browser proof.
- `e2e/layer3-workbench.spec.js` adds the focused live-server proof `Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path`.

## Trial-Usable Checkpoint

Current main now has a bounded, server-authoritative, repeatable proof for the source-directory path from rendered source scan through same-origin hybrid delivery:

1. `/review/layer3` rendered source-directory scan submits only the admitted client request id.
2. Rendered source-directory status replays the server-owned ingestion batch.
3. Rendered source-directory material preview and Gate B admission commit a session without exposing raw absolute paths, file bytes, or caller-controlled source expansion.
4. Live API proof continues through source-directory vector retrieval, hybrid context packet, qualitative analysis, analysis status, package commit, package review submit, handoff/export prepare, and external export/download prepare.
5. `/review/layer3 #source-directory-hybrid-external-export-download-delivery-panel` verifies delivery status and submits browser-managed same-origin attachment-form delivery.
6. The proof rejects provider-private signed URL, provider-public URL, package mutation, raw mixed materialize, and connector handoff path expansion.

This checkpoint is trial-usable because the path is repeatable from current main with isolated test runtime state and proves the critical redaction and same-origin delivery boundaries. It is not a claim that every middle lifecycle step is fully manual-click rendered in one uninterrupted operator flow; the middle retrieval, context, qualitative analysis, package lifecycle, review, and prepare steps are live API-proven using server-authored authority after the rendered Gate B session.

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

5. Treat the checkpoint as clean only if the proof still shows no requests to `/source/mixed-corpus/materialize`, `/handoff/connector`, `/provider-private-signed-url`, `/provider-public-url`, or `/package/mutation`, and rendered text still avoids absolute local paths, raw payload paths, file bytes, and HTTP/HTTPS provider URLs.

## Remaining Whole-Program Sequence

Immediate next pass:

1. Keep this checkpoint synced to current main and do not reopen broad planning unless the runbook fails.
2. Select the smallest current-main-admitted source-directory internal webhook/status slice. The existing rendered internal webhook status surface is read-only; the source-directory trial proof intentionally makes no `/handoff/connector` request and does not add dispatch/rerun/cancel/queue behavior.
3. If product authority admits it, prove server-owned internal webhook dispatch/status from the source-directory package/handoff record while preserving redaction, idempotency, and no caller-supplied destination URL authority.

Mid-term passes:

1. Convert the remaining middle source-directory lifecycle steps into one rendered/operator-continuous flow where current main admits controls: retrieval/context, qualitative analysis/status, package commit, package review submit, handoff/export prepare, external export/download prepare, and replacement/supersession.
2. Re-run headed and headless Chromium proofs after every rendered-control addition and compare request surfaces, console/page errors, overflow, stale response handling, and forbidden payload keys.
3. Extend Analysis Environment/mockup projection only as read-only evidence of live state, explicit exclusion, or explicit blocker status.
4. Keep provider-private signed URL runtime, provider-public URL runtime, broad source expansion, broader RAG/model/provider behavior, auth/security expansion, and frontend-only durable authority blocked until a current-main authority doc and implementation slice admit each one.

Long-term closeout:

1. Every critical mockup operator journey must be classified as live, read-only, intentionally excluded, or explicitly blocked by current-main evidence.
2. A final readiness audit must prove the bounded path, durable state owners, browser-storage policy, security/redaction posture, headed/headless parity, isolated runtime setup, and residual blocker list.
3. Only after that audit should full mockup activation or frontend-only durable authority be considered.

## Non-Admission Boundary

This checkpoint doc introduces no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior, executable test behavior, production UI behavior, provider-private signed URL runtime admission, provider-public URL runtime admission, connector dispatch, destination write, package mutation, source expansion, RAG/model/provider expansion, browser-storage authority, frontend-only durable authority, or full mockup program activation.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Did PR `#1552` close the `932` proof gap? | Yes for a repeatable current-main proof from rendered source-directory scan/status/material preview/Gate B to same-origin hybrid delivery, with the caveat that middle lifecycle steps are live API-proven rather than one continuous manual-click flow. |
| Does this authorize provider-private or provider-public URL runtime? | No. The proof explicitly avoids `/provider-private-signed-url` and `/provider-public-url`, and provider runtime admission remains separately gated. |
| Does this complete internal webhook dispatch? | No. The existing internal webhook surface is read-only status projection; the source-directory proof intentionally avoids `/handoff/connector`. |
| Is another planning pass more valuable than implementation after this checkpoint? | No, unless current-main proof fails. The next useful pass is the narrow internal webhook/status slice or the next rendered middle-control gap. |
| Does this activate the full mockup program? | No. Full activation remains blocked until final readiness audit closure. |

## Next Posture

Next exact posture: `select_source_directory_internal_webhook_status_or_rendered_middle_lifecycle_gap_from_current_main`.
