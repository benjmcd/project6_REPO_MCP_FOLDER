# 952 - Bounded Trial Checkpoint Runbook

## Status

Status: branch-local bounded trial-usable checkpoint and minimal operator runbook proven after the current-main Analysis Environment projection contract.

Doc: `952-bounded-trial-checkpoint-runbook.md`.

Current-main authority before this branch: `project6-origin/main` at `2bbb1976 Add Analysis Environment projection contract (#1576)`.

Predecessor docs:

- `943-bounded-trial-capture.md`
- `944-final-readiness-audit.md`
- `945-activation-readiness-package.md`
- `951-analysis-environment-read-only-projection-contract.md`

This checkpoint records the current bounded operator-trial path and proof requirements. It does not add runtime authority, Analysis Environment interactivity, frontend-only durable state, raw provider/path exposure, connector/provider writes, package/execution side effects, or full mockup activation.

## Immediate Next Pass

This pass syncs the Analysis Environment projection contract posture to current-main truth and proves the bounded trial path with the runbook below. The next exact pass after this checkpoint is a final readiness audit that decides whether a governed full mockup activation phase is eligible; if the audit cannot prove every critical journey as live, read-only, intentionally excluded, or explicitly blocked, full mockup activation remains blocked.

## Covered Operator Path

The bounded trial path is:

1. source-directory scan/status;
2. material preview;
3. Gate B admission;
4. retrieval/context and qualitative analysis authority;
5. qualitative analysis/status;
6. package preview, package commit, and package review submit;
7. package replacement/supersession preview, authority, and commit;
8. handoff/export prepare;
9. external export/download prepare;
10. same-origin delivery/status;
11. admitted redacted delivery prepare/use where current-main authority permits it;
12. internal webhook dispatch/status;
13. status/projection visibility;
14. Analysis Environment and mockup projection read-only evidence.

## Operator Runbook

Run from the repository root on the selected branch:

```powershell
python ./tools/l3-progress-check.py
node --check ./backend/app/review_ui/static/layer3.js
python -m json.tool ./next_milestone_plans/layer3_progress_manifest.json > $null
python -m json.tool ./next_milestone_plans/layer3_workbench_proof_manifest.json > $null
python -m pytest ./backend/tests/test_layer3_api.py::test_layer3_bootstrap_readiness_openapi_contracts ./backend/tests/test_layer3_page.py::test_layer3_static_assets_are_mounted ./backend/tests/test_layer3_page.py::test_layer3_analysis_environment_projection_rendered_reader_is_bounded -q
npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"
npx playwright test e2e/layer3-workbench.spec.js --project=chromium --headed --grep "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path"
npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "Layer 3 mockup (activation readiness dashboard classifies next-phase journeys from bootstrap authority|Sublayer 3C execution lanes projection renders read-only server state without runtime widening)"
npx playwright test e2e/layer3-workbench.spec.js --project=chromium --headed --grep "Layer 3 mockup (activation readiness dashboard classifies next-phase journeys from bootstrap authority|Sublayer 3C execution lanes projection renders read-only server state without runtime widening)"
git diff --check
```

## Expected Rendered And Status Evidence

Expected evidence:

- `/api/v1/layer3/bootstrap` exposes `mockup_activation_readiness`.
- `analysis_environment_projection` remains a session-summary read-only projection.
- `analysis_environment_read_only_live_projection_contract` remains selected for the Analysis Environment journey.
- `.analysis-environment-projection` renders without `button`, `input`, `select`, `textarea`, or `a[href]` controls inside the projection panels.
- The path shows source-directory scan/status through delivery/webhook/status/projection visibility without raw path, provider URL/token, object reference, output payload reference, diagnostics reference, connector destination credential, or browser-storage durable authority.
- Full mockup activation remains blocked.

## Verification Results

Branch-local proof on `codex/l3-bounded-trial-checkpoint`:

- `python ./tools/l3-progress-check.py`: PASS.
- `node --check ./backend/app/review_ui/static/layer3.js`: PASS.
- `python -m json.tool ./next_milestone_plans/layer3_progress_manifest.json > $null`: PASS.
- `python -m json.tool ./next_milestone_plans/layer3_workbench_proof_manifest.json > $null`: PASS.
- `python -m pytest ./backend/tests/test_layer3_api.py::test_layer3_bootstrap_readiness_openapi_contracts ./backend/tests/test_layer3_page.py::test_layer3_static_assets_are_mounted ./backend/tests/test_layer3_page.py::test_layer3_analysis_environment_projection_rendered_reader_is_bounded -q`: PASS, `3 passed`.
- Headless Chromium source-directory path proof: PASS, `1 passed`.
- Headed Chromium source-directory path proof: PASS, `1 passed`.
- Headless Chromium mockup/read-only projection group: PASS, `2 passed`.
- Headed Chromium mockup/read-only projection group: PASS, `2 passed`.
- `git diff --check`: PASS.

## No-Go Boundaries

This checkpoint does not admit:

- new runtime authority;
- Analysis Environment interactivity;
- frontend-only durable state;
- raw provider/path/token/object exposure;
- connector/provider writes;
- package construction or mutation beyond existing admitted controls;
- execution side effects;
- route/API/DTO/model/migration/service widening;
- full mockup activation.

## Stop Conditions

Stop and return to audit/reconciliation if:

- any runbook command fails;
- headed and headless browser proof diverge;
- the rendered path exposes raw provider/path/token/object references, output payload references, diagnostics references, destination credentials, or browser-storage durable authority;
- any read-only projection gains write controls;
- branch-local status remains in the manifests after the branch is merged and current main is refreshed;
- the diff includes runtime/model/route/migration/UI behavior changes beyond this docs and manifest checkpoint;
- current-main evidence cannot classify a critical mockup journey as live, read-only, intentionally excluded, or explicitly blocked.

## Future Steps

Immediate:

1. Land this checkpoint on current main after the runbook proof is clean.
2. Refresh `project6-origin/main` and re-run `python ./tools/l3-progress-check.py`.
3. Confirm doc 951 and both manifests no longer claim the Analysis Environment contract is only branch-local.

Mid-term:

1. Run the final readiness audit against current main.
2. Classify every critical mockup operator journey as live, read-only, intentionally excluded, or explicitly blocked.
3. Record any blockers as named current-main evidence, not inferred backlog.
4. Keep full mockup activation blocked unless the audit proves the full bounded path and all required blockers are closed.

Long-term:

1. If the audit passes, select a governed full-mockup activation entry with explicit authority, proof, and rollback boundaries.
2. If the audit does not pass, choose the next current-main-admitted slice that closes the highest-value named blocker.
3. Preserve server authority over runtime state and reject frontend-only durable authority.
4. Treat Analysis Environment interactivity, provider/connector writes, and package/execution side effects as separate future admissions that require their own freeze, proof, and current-main sync.
