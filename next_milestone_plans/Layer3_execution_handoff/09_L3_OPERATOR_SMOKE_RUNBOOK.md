# 09 Layer 3 Operator Smoke Runbook

Current main. Post-PR #2238 (Operator Workbench MVP). This runbook is executable without reading prior planning documents.

## What is currently available

The `/review/layer3` workbench supports:

- Dataset-version and APS content-document source selection (preflight → source → material → Gate B → Gate C)
- Plan preview and approval
- Synchronous single-pass execution
- Result status and result-review (approve / changes-requested)
- Package review preview, commit, and submit (approve / changes-requested)
- Handoff export prepare
- APS dispatch (blocked by default — `aps_handoff_enabled: false`)
- External export download (blocked by default — `external_export_download_enabled: false`)
- Connector dispatch (blocked by default — `connector_dispatch_enabled: false`)
- Provider/public URL delivery (blocked by default — `provider_public_url_enabled: false`)

## Harness quick-start

Start the in-process test harness. From the worktree root:

```powershell
cd backend\tests
py -3.12 -m uvicorn review_browser_server:create_app --factory --host 127.0.0.1 --port 8031
```

Open the workbench:

```text
http://127.0.0.1:8031/review/layer3
```

The harness uses an in-memory SQLite database and isolated temporary storage. It is reset on every process restart.

## Automated smoke (fastest)

Run the G7 server-backed tests. These prove the core execution/result/package and downstream handoff/delivery paths entirely through real server responses — no page.evaluate injection.

```powershell
npx playwright test e2e/layer3-workbench.spec.js --grep "server-backed" --project=chromium
```

Expected: 5 passed. Tests cover:
- Real failed-pass state (empty CSV → `PASS_STATUS_FAILED`)
- Real missing-output state (deleted manifest → `output_metadata_file_missing`)
- Result-review approval survives reload (session summary drives `result_review_ui_recorded`)
- Package-review approval survives reload (session summary drives `package_review_approved`, submit disabled)
- Raw-mixed handoff delivery readiness (real `handoff/export/prepare` → `aps/dispatch` → `external/export/download/prepare` → `signed-reference/generate`, with safety flags confirmed closed, and reload restore)

Run time: ~2 minutes.

## Full rendered path smoke

This exercises the rendered UI from source selection through package review. Requires the harness running on port 8031.

```powershell
npx playwright test e2e/layer3-workbench.spec.js --grep "drives raw mixed rendered package-review preview commit and submit" --project=chromium
```

Expected: 1 passed. This test drives the complete rendered workbench path:
raw-mixed seed bridge → preflight → source preview → material preview → Gate B → Gate C preview/commit → plan preview/approve → execution select/start → result status → result review (approved) → package preview → package commit → package review submit (approved).

## Backend API smoke (PowerShell, quant path)

This proves the quant execution path via direct API calls. Requires the harness on port 8031.

```powershell
# 1. Seed a quant-ready session
$seed = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8031/__test/layer3/seed-quant"
$sid = $seed.session_id

# 2. Plan preview
$pp = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8031/api/v1/layer3/plan/preview" `
  -ContentType "application/json" `
  -Body (@{schema_id="layer3.plan_preview_request.v1"; client_request_id="smoke-pp-$(Get-Random)"; session_id=$sid; include_exclusions=$true; preview_scope="owner_service_default"} | ConvertTo-Json)
Write-Host "plan/preview: $($pp.schema_id) status=$($pp.status)"

# 3. Plan approve
$pa = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8031/api/v1/layer3/plan/approve" `
  -ContentType "application/json" `
  -Body (@{schema_id="layer3.plan_approval_request.v1"; client_request_id="smoke-pa-$(Get-Random)"; session_id=$sid; preview_id=$pp.preview_id; preview_hash=$pp.preview_hash; operator_confirmation=$true; approval_scope="owner_service_default"} | ConvertTo-Json)
Write-Host "plan/approve: analysis_plan_id=$($pa.analysis_plan_id)"

# 4. Execution select
$sel = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8031/api/v1/layer3/execution/select" `
  -ContentType "application/json" `
  -Body (@{client_request_id="smoke-sel-$(Get-Random)"; session_id=$sid; analysis_plan_id=$pa.analysis_plan_id; preview_id=$pp.preview_id; preview_hash=$pp.preview_hash; operator_reason="smoke"} | ConvertTo-Json)
$prid = $sel.pass_run_ids[0]
Write-Host "execution/select: pass_run_id=$prid"

# 5. Execution start (synchronous)
$start = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8031/api/v1/layer3/execution/start" `
  -ContentType "application/json" `
  -Body (@{client_request_id="smoke-start-$(Get-Random)"; session_id=$sid; analysis_plan_id=$pa.analysis_plan_id; pass_run_id=$prid; preview_id=$pp.preview_id; preview_hash=$pp.preview_hash; execution_mode="synchronous_single_pass"; operator_reason="smoke"} | ConvertTo-Json)
Write-Host "execution/start: pass_run_status=$($start.pass_run_status)"
# Expected: completed or completed_with_warnings

# 6. Result status
$rs = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8031/api/v1/layer3/execution/result/status" `
  -ContentType "application/json" `
  -Body (@{client_request_id="smoke-rs-$(Get-Random)"; session_id=$sid; analysis_plan_id=$pa.analysis_plan_id; pass_run_id=$prid; preview_id=$pp.preview_id; preview_hash=$pp.preview_hash; analysis_run_id=$start.analysis_run_id; operator_view_mode="status_only"} | ConvertTo-Json)
Write-Host "result/status: result_status_available=$($rs.result_status_available) next_state=$($rs.next_state)"
# Expected: result_status_available=True, next_state=execution_result_status_available
```

Expected evidence at each step:
- `seed-quant`: `session_id` is populated
- `plan/preview`: `status` is `available`
- `plan/approve`: `analysis_plan_id` is populated
- `execution/select`: `pass_run_ids` has one entry
- `execution/start`: `pass_run_status` is `completed` or `completed_with_warnings`
- `result/status`: `result_status_available` is `True`, `next_state` is `execution_result_status_available`

## Backend unit tests

```powershell
python -B -m pytest backend/tests/test_layer3_api.py backend/tests/test_layer3_page.py -q
python -B -m pytest backend/tests/test_layer3_workbench.py -q
```

Expected: 325 passed + 28 passed (4 warnings total, no failures).

## Safety gates that must remain blocked

After any smoke run, verify that these are NOT enabled:

- `connector_dispatch_enabled: false` in execution/start response
- `provider_public_url_enabled: false` in package review submit response
- `handoff_enabled: false` in package review submit response for quant sessions
- `aps_handoff_enabled: false` in package review submit response
- `external_export_download_enabled: false` in package review submit response

The workbench renders these as downstream-unavailable and disables all related buttons. Do not accept a smoke pass if any of these surfaces are enabled.

## Current known deferred gaps

The downstream handoff/delivery path now has real server-backed coverage: the
`raw-mixed handoff delivery readiness` test drives `handoff/export/prepare` →
`aps/dispatch` → `external/export/download/prepare` → `signed-reference/generate`
through real APIs (harness fakes the external dispatch; safety flags stay closed)
and proves reload restore. The `prepareRawMixedHandoffDeliverySession` helper in
`e2e/layer3-helpers.js` is the reusable entry point.

These tests still use `page.evaluate` state injection (UI-rendering-in-isolation
simulation). They are not blocked — the paths are implemented, working, and now
covered server-backed by the test above — but these specific render tests simulate
rather than exercise the endpoints:

- Handoff export prepare restore after reload (lines 8184+ in `e2e/layer3-workbench.spec.js`)
- APS dispatch / external export download / signed-reference render tests (lines 8527+)

Converting these in place is a low-priority follow-up; the real coverage already
exists via the server-backed test. They do not affect the safety or correctness of
the tested paths.

## Stop conditions

Stop and do not extend the smoke if any of the following would be required:

- enabling live SEC acquisition or Arelle
- enabling provider dispatch, connector dispatch, or external network dispatch
- enabling unsafe value reveal or default-on production behavior
- introducing schema or migration changes
- fabricating evidence for passing tests
