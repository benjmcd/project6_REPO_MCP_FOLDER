# 1356 SEC XBRL Activation Surface Map

Target: `sec_xbrl_activation_surface_operator_map_v1`.

This slice extends the SEC XBRL runtime posture projection with a server-owned operator map of the
remaining activation surfaces. It does not activate live SEC network access, Arelle invocation,
export/delivery, multi-filing gate enforcement, or nonlocal auth hardening. It makes the next
operator path explicit from the posture panel.

## Decision

```yaml
entry_decision: implemented
selected_surface: server_owned_activation_surface_map
api_route_extended: GET /api/v1/layer3/sec-xbrl/runtime/posture
rendered_panel_extended: backend/app/review_ui/static/layer3.js::secXbrlRuntimePostureRows
request_body_admitted: false
side_effects_performed: false
production_readiness_claimed: false
```

The projection reports activation surfaces for controlled value reveal, live SEC EDGAR source
acquisition, Arelle invocation/governed sibling value reveal, multi-filing gate enforcement,
delivery/export/package status, and nonlocal operator-auth hardening.

## Non-Goals

- no live SEC network request, Arelle subprocess invocation, value reveal, export/delivery, runtime
  default change, database write, storage write, model change, schema change, migration, or
  production-readiness claim;
- no browser-supplied URL, local path, raw operator identity, raw header, raw value, residual
  magnitude, or frontend durable authority;
- no new activation route. Existing route and panel identifiers are reported only as operator
  navigation/status metadata.

## Verification

```powershell
..\..\.venvs\project6-py312\Scripts\python.exe -m pytest .\backend\tests\test_sec_xbrl_runtime_posture.py -q
..\..\.venvs\project6-py312\Scripts\python.exe -m pytest .\backend\tests\test_layer3_page.py -k "sec_xbrl_runtime_posture or controlled_value_reveal or legacy_arelle_value_reveal" -q
$env:PLAYWRIGHT_USE_SYSTEM_CHROME='1'; $env:PLAYWRIGHT_PYTHON='..\..\.venvs\project6-py312\Scripts\python.exe'; npx playwright test --project=chromium -g "SEC XBRL runtime posture" --reporter=line
$env:PLAYWRIGHT_USE_SYSTEM_CHROME='1'; $env:PLAYWRIGHT_PYTHON='..\..\.venvs\project6-py312\Scripts\python.exe'; npx playwright test --project=chromium -g "SEC XBRL runtime posture" --headed --reporter=line
git diff --check
```

Result: focused posture tests pass (`5 passed`); focused static Layer3 page checks pass
(`3 passed, 22 deselected`); focused Playwright Chromium proof passes in headless and headed modes;
`git diff --check` is clean except standard Windows LF-to-CRLF warnings.

## Next Posture

Use the activation-surface map to select one implementation pass, preferably live SEC source
acquisition if operator authority enables `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED`; otherwise proceed
with Arelle invocation proof, delivery/export/status proof, multi-filing gate enforcement, or
nonlocal operator-auth hardening as separately bounded freezes.
