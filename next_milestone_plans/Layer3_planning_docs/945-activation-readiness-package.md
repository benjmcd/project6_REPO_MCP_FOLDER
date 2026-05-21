# 945 - Activation Readiness Package

## Status

Status: current-main next-phase activation-readiness package for governed Layer 3 mockup/projection evolution.

Doc: `945-activation-readiness-package.md`.

Predecessor final audit: `944-final-readiness-audit.md`.

Current main authority: `project6-origin/main` at `31d0c528 Merge pull request #1570 from benjmcd/codex/l3-next-phase-activation-readiness`.

Follow-up branch: `codex/l3-next-operator-path-proof`.

Selected first slice: `query_source_setup_interactive_live_classification`.

Selected next slice: `output_review_package_handoff_interactive_live_contract`.

## Classification

This package does not activate the full mockup program. It makes the next-phase activation posture server-authored and rendered in the workbench bootstrap/readiness surface.

| Mockup journey | Classification | Reason |
| --- | --- | --- |
| Query/source setup | Interactive-live | Existing intent, source-intake, server-configured source-directory, material-preview, and Gate B APIs already own the interactive controls. |
| PDF-location evidence | Read-only | Current authority is session-summary PDF-location projection; no write/navigation authority is selected. |
| Sublayers 3A/3B | Read-only | Current authority is session-summary sublayer visualization; no edit/drilldown control is selected. |
| Sublayer 3C execution lanes | Read-only | Current authority is analysis-environment and execution-state projection; no execution-lane control is selected. |
| Output review/package/handoff | Interactive-live | Current authority includes existing result-review, package lifecycle, handoff/export, same-origin/admitted redacted delivery/use, local outbox, provider-private, external-local export, and internal webhook route/control/status surfaces. This classification adds no new runtime authority. |
| Full mockup program | Blocked | Full mockup activation and frontend-only durable authority still require a later freeze and readiness audit. |

## Admitted Behavior

- `backend/app/services/layer3_mockup_activation_readiness.py` owns `layer3.mockup_activation_readiness.v1`.
- `/api/v1/layer3/bootstrap` exposes `mockup_activation_readiness` as server-owned bootstrap state.
- `/review/layer3` renders `#mockup-activation-readiness-panel` from `State.bootstrap.mockup_activation_readiness`.
- `output_review_package_handoff_interactive_live_contract` records the existing route/control/status contract for the output review, package, handoff, delivery, local outbox, provider-private, external-local export, and internal webhook path without admitting new package mutation, raw package bytes, raw provider tokens, destination credentials, connector/provider writes, frontend-only durable authority, or full mockup activation.

## Non-Admission Boundary

This slice does not admit frontend-only durable authority, raw provider URL/token exposure, unapproved connector/provider writes, broad source-family expansion, broad model/provider/RAG expansion, or full mockup program activation.

## Verification

- `python -m py_compile ./backend/app/services/layer3_mockup_activation_readiness.py ./backend/app/services/layer3_bootstrap_contract.py ./backend/app/services/layer3_workbench.py ./backend/app/api/layer3.py`: passed.
- `node --check ./backend/app/review_ui/static/layer3.js`: passed.
- `python -m pytest ./backend/tests/test_layer3_mockup_activation_readiness.py ./backend/tests/test_layer3_mockup_boundary.py -q`: `2 passed`.
- `python -m pytest ./backend/tests/test_layer3_api.py::test_layer3_bootstrap_readiness_openapi_contracts ./backend/tests/test_layer3_mockup_activation_readiness.py -q`: `2 passed`.
- `python -m pytest ./backend/tests/test_layer3_page.py::test_layer3_page_route_serves_workbench_shell -q`: `1 passed`.
- `python -m pytest ./backend/tests/test_layer3_page.py::test_layer3_static_assets_are_mounted -q`: `1 passed`.
- Headless Chromium, `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --grep "Layer 3 mockup activation readiness dashboard classifies next-phase journeys from bootstrap authority"`: `1 passed`.
- Headed Chromium, `npx playwright test e2e/layer3-workbench.spec.js --project=chromium --headed --grep "Layer 3 mockup activation readiness dashboard classifies next-phase journeys from bootstrap authority"`: `1 passed`.
- `python .\tools\l3-progress-check.py`: `Layer 3 progress state check: PASS`.
- `git diff --check`: passed.

## Next Posture

The next useful pass is to prove the existing output review/package/handoff controls from current main with headed/headless browser evidence, then select the next still-read-only projection journey only after current-main server authority identifies an exact interaction contract.
