# 938 - Source-Directory Package Supersession Current-Main Sync

## Status

Status: current-main sync and bounded trial-usable checkpoint for `source_directory_package_replacement_supersession_rendered_path`.

Doc: `938-source-supersession-current-main-sync.md`.

Predecessor implementation proof doc: `937-source-supersession-proof.md`.

Merged PR: `#1562`.

Source branch: `codex/l3-source-supersession-proof`.

Implementation commit: `5fe9bb6619135f51ca6e8654789a4c238b60a68a`.

Merge commit: `b53a62cb5b4ddaf0584fed01bde241c33d372717`.

Base authority before implementation: `project6-origin/main` at `2c46c06c62d2b7359c7971b2b5e2c99007783ed2`.

Synced rendered path: `/review/layer3` source-directory scan/status through material preview, Gate B, hybrid authority prepare, retrieval/context, qualitative analysis/status, package commit, package review submit, package supersession preview, replacement package-set authority, package supersession commit, handoff/export prepare, external export/download prepare, same-origin delivery/status, and internal webhook dispatch/status.

## Merge Gate

GitHub gate before merge:

- `backend-layer3-api`: `SUCCESS` in `3m38s`.
- `test`: `SUCCESS` in `4m34s`.
- Comments: `0`.
- Reviews: `0`.
- Review threads: `0`.
- Unresolved review threads: `0`.
- Merge state: `CLEAN`.
- Mergeable state: `MERGEABLE`.

PR `#1562` merged with the repo's existing merge-commit style. After refresh, `project6-origin/main` resolved to `b53a62cb5b4ddaf0584fed01bde241c33d372717`, whose parents are `2c46c06c62d2b7359c7971b2b5e2c99007783ed2` and `5fe9bb6619135f51ca6e8654789a4c238b60a68a`.

## Current-Main Authority

Current main now closes the source-directory package replacement/supersession proof gap that remained after the hybrid authority bridge current-main sync.

The rendered hybrid middle-lifecycle path now writes server-derived package supersession preview authority after package-review submit. The existing package supersession preview, replacement package-set authority, and package supersession commit controls can then be clicked in the focused rendered source-directory path.

Backend authority remains server-owned. Package supersession preview recognizes persisted hybrid package-commit reconciliation authority and derives preview authority from reconciliation/package rows. Replacement package-set authority and package supersession commit accept that hybrid package lifecycle authority without adding route, API, DTO, model, or migration behavior.

## Post-Merge Validation

Validation before merge:

- `node --check ./backend/app/review_ui/static/layer3.js`: `PASS`.
- `python -m pytest ./backend/tests/test_layer3_page.py -q`: `16 passed`.
- `python -m pytest ./backend/tests/test_layer3_source_directory_qualitative_analysis.py -q`: `13 passed`.
- `python -m pytest ./backend/tests/test_layer3_source_directory_vector_retrieval.py -q`: `23 passed`.
- `python -m json.tool ./next_milestone_plans/layer3_progress_manifest.json > $null`: `PASS`.
- `python -m json.tool ./next_milestone_plans/layer3_workbench_proof_manifest.json > $null`: `PASS`.
- `python ./tools/l3-progress-check.py`: `PASS`.
- `git diff --check`: `PASS` with line-ending warnings only.
- Headless Chromium focused proof for `Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path`: `PASS`.
- Headed Chromium focused proof for the same path: `PASS`.

Validation after merge:

- GitHub `backend-layer3-api`: `SUCCESS`.
- GitHub `test`: `SUCCESS`.
- Post-merge `project6-origin/main` refresh: `b53a62cb5b4ddaf0584fed01bde241c33d372717`.
- `git diff --stat project6-origin/main HEAD` on the merged implementation lane: no tree diff.

## Bounded Trial-Usable Checkpoint

Current main now has a bounded, server-authoritative, repeatable proof for the source-directory rendered operator path through package replacement/supersession:

1. Rendered source-directory scan/status establishes admitted source-directory authority without browser-supplied file paths or source expansion.
2. Rendered material preview and Gate B establish the server-owned session/material snapshot.
3. Rendered hybrid authority prepare derives middle-lifecycle authority from the admitted Gate B session/material snapshot through the production route.
4. The live middle lifecycle runs retrieval/context, qualitative analysis/status, package commit, and package review submit.
5. The rendered package supersession preview, replacement package-set authority, and package supersession commit controls run from persisted server-owned hybrid reconciliation/package authority.
6. The path continues through handoff/export prepare, external export/download prepare, same-origin delivery/status, and internal webhook dispatch/status.

This checkpoint is trial-usable for bounded operator proof because it covers the current-main-selected rendered source-directory path through the previously named package replacement/supersession gap and preserves the redaction, same-origin delivery, internal webhook, no-package-mutation, no-connector-dispatch, and no-frontend-durable-authority boundaries.

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
   python -m json.tool ./next_milestone_plans/layer3_progress_manifest.json > $null
   python -m json.tool ./next_milestone_plans/layer3_workbench_proof_manifest.json > $null
   ```

3. Run focused backend proof:

   ```powershell
   python -m pytest ./backend/tests/test_layer3_page.py -q
   python -m pytest ./backend/tests/test_layer3_source_directory_qualitative_analysis.py -q
   python -m pytest ./backend/tests/test_layer3_source_directory_vector_retrieval.py -q
   ```

4. Run both browser modes for the current source-directory path:

   ```powershell
   $env:CI='1'; npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"
   $env:CI='1'; npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --headed --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"
   ```

5. Treat the checkpoint as clean only if the proof still shows no requests to test-helper hybrid authority, raw mixed materialize, connector handoff, provider-private URL runtime, provider-public URL runtime, or package-mutation routes, and no browser-supplied raw paths, file bytes, provider URLs, connector destinations, webhook destinations, package payloads, browser-storage authority, or frontend durable authority.

## Remaining Whole-Program Sequence

Immediate next pass:

1. Run a final bounded readiness/runbook audit over the current-main source-directory path now that package replacement/supersession proof is merged.
2. Decide whether every critical mockup journey is live, read-only, intentionally excluded, or explicitly blocked by current-main evidence.
3. If the audit finds only governed blockers, record the final bounded-readiness posture. If it finds a concrete missing rendered control or proof drift, select the smallest current-main-admitted correction.

Mid-term passes:

1. Keep Analysis Environment/mockup projection evidence-bound and update it only from current-main live state, read-only exclusions, or explicit blockers.
2. Keep provider-private signed URL runtime, provider-public URL runtime, broader source/RAG/model/provider behavior, auth/security expansion, observability/performance hardening, and frontend-only durable authority blocked until separate current-main authority admits each one.
3. Re-run headed and headless Chromium after each rendered-control or proof-surface change and compare request surfaces, stale-state handling, disabled states, console/page errors, and forbidden payload keys.

Long-term closeout:

1. Produce the final whole-program readiness audit over bounded path coverage, durable state owners, browser-storage policy, redaction/security posture, isolated runtime setup, headed/headless parity, and residual blocker list.
2. Only after that audit should full mockup activation or frontend-only durable authority be considered.

## Non-Admission Boundary

This sync introduces no runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior, executable test behavior, production UI behavior, provider-private signed URL runtime admission, provider-public URL runtime admission, connector dispatch, caller-supplied destination write, package mutation, source expansion, broader RAG/model/provider behavior, browser-storage authority, frontend-only durable authority, auth/security expansion, or full mockup program activation.

Frontend-only durable authority remains `false`.

Full mockup program activation remains `false`.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Is the source-directory package replacement/supersession proof current-main authority now? | Yes. PR `#1562` merged to `project6-origin/main` at `b53a62cb5b4ddaf0584fed01bde241c33d372717`. |
| Did GitHub checks and review surfaces settle before merge? | Yes. Both checks passed, comments and reviews were empty, review threads were `0`, and merge state was `CLEAN`. |
| Did this add new route/API/DTO/model/migration behavior? | No. The implementation uses existing route contracts and adds service acceptance for persisted hybrid package lifecycle authority. |
| Does this mutate package payloads or source package rows? | No. The proof preserves package payload write and source package row mutation as disabled boundaries. |
| Does this authorize provider URL runtime, connector dispatch, or frontend-only durable authority? | No. Those remain blocked and explicitly non-admitted. |
| Does this activate the full mockup program? | No. Full activation remains blocked pending final whole-program readiness audit. |

## Next Posture

Next exact posture: `run_final_bounded_readiness_and_mockup_activation_blocker_audit_after_source_directory_replacement_supersession_current_main_sync`.
