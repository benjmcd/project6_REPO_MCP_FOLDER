# 962 - Provider-Private Runbook Refresh

## Status

Status: current-main bounded operator runbook refresh after `961-provider-private-sync.md`.

Current-main authority: `project6-origin/main` at `ee708cb4 Merge pull request #1597 from benjmcd/codex/l3-provider-private-checkpoint-sync`.

Predecessor checkpoint: `961-provider-private-sync.md`.

This refresh introduces no route, DTO, database model, migration, service behavior, rendered UI behavior, executable behavior, provider object behavior, connector dispatch, source expansion, RAG/vector/model runtime, public URL/proxy behavior, frontend-only durable authority, or full mockup activation.

## Runbook Evidence

Commands run from `worktrees/l3-provider-main` against detached current main:

```powershell
python ./tools/l3-progress-check.py
node --check ./backend/app/review_ui/static/layer3.js
python -m json.tool ./next_milestone_plans/layer3_progress_manifest.json > $null
python -m json.tool ./next_milestone_plans/layer3_workbench_proof_manifest.json > $null
python -m pytest ./backend/tests/test_layer3_api.py::test_layer3_bootstrap_readiness_openapi_contracts ./backend/tests/test_layer3_page.py::test_layer3_static_assets_are_mounted ./backend/tests/test_layer3_page.py::test_layer3_analysis_environment_projection_rendered_reader_is_bounded -q
npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"
npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --headed --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"
npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --grep "Layer 3 mockup (activation readiness dashboard classifies next-phase journeys from bootstrap authority|Sublayer 3C execution lanes projection renders read-only server state without runtime widening)"
npx playwright test ./e2e/layer3-workbench.spec.js --project=chromium --headed --grep "Layer 3 mockup (activation readiness dashboard classifies next-phase journeys from bootstrap authority|Sublayer 3C execution lanes projection renders read-only server state without runtime widening)"
git diff --check
```

Observed result:

```yaml
l3_progress_check: PASS
layer3_js_node_check: PASS
layer3_progress_manifest_json: PASS
layer3_workbench_proof_manifest_json: PASS
focused_pytest: 3 passed
source_directory_live_path_chromium_headless: 1 passed
source_directory_live_path_chromium_headed: 1 passed
mockup_read_only_projection_chromium_headless: 2 passed
mockup_read_only_projection_chromium_headed: 2 passed
git_diff_check: PASS
```

## Current-Main Result

Current main continues to prove the bounded operator path from source-directory scan/status through material preview, Gate B, retrieval/context, qualitative analysis, package lifecycle, package replacement/supersession, handoff/export, same-origin or admitted redacted delivery, internal webhook/status, and read-only Analysis Environment/mockup projection evidence.

The provider-private/redacted lifecycle remains bounded to current-main-admitted artifact families and rendered proof:

- source-directory hybrid handoff/export package artifact prepare/status/use/revoke;
- source-directory package replacement/supersession artifact prepare/status/use/revoke;
- local-outbox provider-private handoff prepare/status/expiry as a local/fake handoff substrate with real-target selection still gated.

The runbook proof preserves:

- no raw provider URL or raw provider token exposure;
- no provider-public URL enablement;
- no public proxying;
- no provider object write/copy/mutation;
- no arbitrary connector dispatch or real destination write;
- no credential exposure;
- no frontend-only durable authority;
- no source expansion;
- no RAG/vector/model runtime;
- no full mockup activation.

## Next Posture

Immediate next pass:

1. Stop at the refreshed bounded runbook evidence unless a failed check, stale proof, or named current-main-admitted artifact-family gap appears.
2. If product authority selects another exact provider-private artifact family, write a separate freeze before implementation.
3. If product authority selects full mockup activation, run a separate final readiness audit and record rollback/no-go authority before implementation.

Mid-term:

1. Keep provider-public URL, public proxy, connector dispatch, real provider object operations, credentials, source expansion, RAG/vector/model runtime, Analysis Environment interactivity, and full mockup activation as separate blocked or intentionally excluded tracks unless explicitly frozen.
2. Re-run headed and headless rendered proof after any operator-path extension.
3. Keep current-main checkpoints synchronized only when they close a named proof gap or materially refresh readiness evidence.

Long-term:

1. Maintain server authority over every admitted provider-private/redacted delivery lifecycle.
2. Classify every critical mockup operator journey as live, read-only, intentionally excluded, or explicitly blocked from current-main evidence.
3. Admit broader activation only after requirement-by-requirement readiness evidence proves every blocker closed.
