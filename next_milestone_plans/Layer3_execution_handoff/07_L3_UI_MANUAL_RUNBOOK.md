# 07 Layer 3 UI Manual Runbook

## Purpose and authority

This runbook is a practical operator checklist for current-main `/review/layer3` manual UI testing after the post-PR #694 raw mixed bridge UI smoke. It is documentation only. It does not admit a rendered raw mixed manifest picker, source upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, source adapter registry, package mutation, connector or destination dispatch, provider or public URLs, full mockup activation, hidden LLM behavior, model or migration changes, or auth/security behavior.

Authority order for this runbook:

1. live source and tests on `project6-origin/main`;
2. `backend/app/review_ui/static/layer3.html` and `backend/app/review_ui/static/layer3.js`;
3. `backend/tests/review_browser_server.py`;
4. `e2e/layer3-workbench.spec.js` and `e2e/layer3-handoff.spec.js`;
5. `backend/tests/test_layer3_raw_mixed_bridge.py` and `backend/tests/test_layer3_bounded_e2e.py`;
6. planning and proof manifests only as secondary context.

The raw mixed seed bridge remains API setup only. A human-facing raw mixed manifest workflow does not exist in the rendered workbench.

## Current rendered capability

The current `/review/layer3` page renders the bounded workbench shell with:

- intent entry;
- source-class checkboxes for `dataset_version` and `aps_content_document`;
- dataset-version candidate selection plus explicit dataset-version ids;
- APS content-document candidate selection plus explicit APS content-document ids;
- preflight, source preview, and material preview through the normal workbench flow;
- Gate B decision submission;
- Gate C preview and commit controls when server-authoritative state allows them;
- later plan, execution, result, package, handoff, APS dispatch, and external export/download panels that remain server-gated by the existing backend state contracts.

The current page does not render:

- raw mixed manifest selection;
- upload controls;
- directory-picking controls;
- web connector retrieval controls;
- RAG/vector controls;
- source adapter registry controls;
- provider or public URL controls for raw source setup;
- generic connector or destination dispatch controls;
- package mutation or reconstruction controls.

## Recommended manual mode

Use the browser test harness for practical manual testing unless the task explicitly needs a real deployment environment. The harness gives isolated in-memory database state and isolated temporary storage. It also exposes test-only seed routes that prepare admitted source authority without implying those routes exist in production.

From the repository root:

```powershell
cd .\backend\tests
py -3.12 -m uvicorn review_browser_server:create_app --factory --host 127.0.0.1 --port 8031
```

Open this route in the browser:

```text
http://127.0.0.1:8031/review/layer3
```

The harness exposes its seed routes at:

```text
http://127.0.0.1:8031/__test/harness-info
```

## Raw mixed setup boundary

Raw mixed setup is a two-call API setup sequence. It is not a rendered UI workflow.

1. Call the harness seed route:

```powershell
$seedSetup = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8031/__test/layer3/seed-raw-mixed"
```

2. Call the live raw mixed bridge endpoint with the returned request payload:

```powershell
$seed = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8031/api/v1/layer3/source/mixed-corpus/seed" `
  -ContentType "application/json" `
  -Body ($seedSetup.seed_request | ConvertTo-Json -Depth 20)
```

Expected seed evidence:

- `schema_id` is `layer3.raw_mixed_corpus_seed_result.v1`;
- `seed_mode` is `raw_mixed_corpus_bridge_seed_only`;
- `source_seed_state` is `seeded`;
- `source_classes` contains only `dataset_version` and `aps_content_document`;
- `dataset_version_ids` is populated;
- `aps_content_document_ids` is populated;
- `layer3_flow_started` is `false`;
- no provider URL, public URL, connector run, destination write, RAG/vector, upload, directory, package, handoff, or execution authority is returned.

## Manual UI steps

1. Open `/review/layer3`.
2. Confirm the source class checkboxes are limited to `Dataset version` and `APS content document`.
3. Confirm no upload, directory, web connector, RAG/vector, provider/public URL, source adapter registry, or raw manifest picker controls are visible.
4. Select only the dataset-version and APS content-document ids returned by the seed response. If candidate lists are not convenient, paste the returned ids into the explicit id fields.
5. Enter a concise intent, for example:

```text
Review raw mixed seed bridge setup through rendered Layer 3 material preview.
```

6. Click `Run Preflight`.
7. Expected UI evidence after preflight/source/material preview:
   - event/status panels show successful preflight/source/material progression;
   - material preview contains the selected admitted source records;
   - source identities correspond to the seed-returned dataset-version and APS content-document ids;
   - no deferred raw-ingestion controls appear.
8. Review the Gate B material ledger.
9. Submit Gate B using the rendered `Commit Gate B` control.
10. Expected UI evidence after Gate B:
   - Gate B state is recorded by the server response;
   - Gate C preview becomes available when the server-authoritative state allows it;
   - no browser-local state should be treated as durable authority.

The current raw mixed UI smoke stops at Gate B submission with Gate C preview enabled. Continuing beyond that point should be treated as a separate deeper UI proof pass unless the operator has deliberately prepared the required server-authoritative state.

## Backend and API evidence to check

For raw mixed bridge setup, inspect the seed response rather than the browser state:

- `layer3_flow_started` must remain `false`;
- source ids must come from the bridge response;
- the bridge must not create Layer 3 session, Gate B, Gate C, plan, pass-run, package, handoff, APS dispatch, or export/download state.

For the rendered workbench path, browser network evidence should show the normal flow:

- `POST /api/v1/layer3/preflight`;
- `POST /api/v1/layer3/source-preview`;
- `POST /api/v1/layer3/material-preview`;
- `POST /api/v1/layer3/gate-b/decision`.

The raw mixed bridge endpoint must not be called from a rendered UI control. It is setup only.

## Automation cross-check

The practical manual run can be cross-checked with the existing focused smoke:

```powershell
npx playwright test e2e/layer3-workbench.spec.js --grep "Layer 3 workbench uses raw mixed seed bridge setup for rendered material review"
```

A broader rendered workbench check can be run with:

```powershell
npx playwright test e2e/layer3-workbench.spec.js
```

These commands are proof aids. They do not replace source inspection when claiming a new capability.

## Stop conditions

Stop and do not continue the manual proof if any of these appear necessary:

- adding a rendered raw mixed seed button;
- adding a manifest picker;
- adding file upload or directory selection;
- using arbitrary local paths in a request;
- fetching web connector sources;
- adding RAG/vector setup;
- relying on browser state as durable authority;
- starting Layer 3 flow from the bridge response instead of the normal preflight/source/material/Gate B sequence;
- invoking real external connector or destination dispatch;
- generating provider/public URLs;
- mutating or reconstructing package payloads;
- changing auth/security behavior.

## Cleanup

For harness testing, stop the `uvicorn` process when finished. The harness uses isolated in-memory database state and temporary storage for the server process, but the browser may retain local or session storage. Use a fresh browser context or clear site data before rerunning recovery-sensitive checks.

For non-harness manual testing, use isolated database and storage state. Do not rely on shared seeded state as proof, and do not treat production-like state preparation as equivalent to the raw mixed seed bridge unless the seed endpoint response and normal workbench API calls are captured.

## Current next proof gap

The next automation gap after this runbook is a deeper Playwright bridge-to-rendered-UI path that uses the raw mixed bridge as API setup and then drives the existing rendered controls beyond Gate B only where server-authoritative state and existing controls already support the flow. That future pass should remain test-only unless it exposes a concrete production blocker.

Post-PR #695 planning note: `08_L3_POST_695_REFERENCE_PLAN.md` supersedes this paragraph for execution order. The deeper Playwright bridge-to-rendered-UI path remains the next UI proof gap, but the immediate prerequisite is a test-only browser-harness Layer 3 patch-restoration pass because same-process pytest ordering can leak Layer 3 browser harness patches into bounded E2E tests.
