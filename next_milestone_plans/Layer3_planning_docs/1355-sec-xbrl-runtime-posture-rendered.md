# 1355 SEC XBRL Runtime Posture Rendered Status

Target: `sec_xbrl_runtime_posture_rendered_status_v1`.

This slice renders the read-only runtime posture projection from
`1354-sec-xbrl-runtime-posture.md` in `/review/layer3`. It makes the current SEC XBRL
activation/gating state visible to operators without enabling live SEC network access, Arelle
invocation, value reveal, export, default mutation, identity override, or frontend durable
authority.

## Decision

```yaml
entry_decision: implemented
selected_surface: rendered_read_only_runtime_posture_panel
html_panel: backend/app/review_ui/static/layer3.html#sec-xbrl-runtime-posture-panel
js_renderer: backend/app/review_ui/static/layer3.js::renderSecXbrlRuntimePosturePanel
api_route_consumed: GET /api/v1/layer3/sec-xbrl/runtime/posture
request_body_admitted: false
operator_supplied_authority_fields: false
```

The panel has one action, `Inspect Runtime Posture`, and stores the returned
`sec_xbrl_runtime_posture` projection in browser state for display only. It renders runtime flags,
identity-authority posture, protected route families, activated capabilities, gated capabilities,
negative boundaries, and next actions.

## Non-Goals

- no POST route, request body, local storage authority, browser-supplied identity, path, URL, raw
  value, sidecar, dataset, or value-store field;
- no SEC EDGAR network fetch, Arelle invocation, value reveal, export/delivery, runtime default
  change, database write, storage write, schema change, model change, or migration;
- no production-readiness claim. The rendered panel keeps `data-production-readiness-claimed=false`.

## Verification

```powershell
..\..\.venvs\project6-py312\Scripts\python.exe -m pytest .\backend\tests\test_layer3_page.py -k "sec_xbrl_runtime_posture or controlled_value_reveal or legacy_arelle_value_reveal" -q
$env:PLAYWRIGHT_USE_SYSTEM_CHROME='1'; $env:PLAYWRIGHT_PYTHON='C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.venvs\project6-py312\Scripts\python.exe'; npx playwright test --project=chromium -g "SEC XBRL runtime posture" --reporter=line
$env:PLAYWRIGHT_USE_SYSTEM_CHROME='1'; $env:PLAYWRIGHT_PYTHON='C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.venvs\project6-py312\Scripts\python.exe'; npx playwright test --project=chromium -g "SEC XBRL runtime posture" --headed --reporter=line
git diff --check
```

## Next Posture

Use this rendered posture panel as the operator-facing readiness entry before activating any live
SEC/Arelle path. The next bounded production pass should choose one of: live SEC source acquisition
operator proof, Arelle invocation proof, export/package/status delivery, or nonlocal operator-auth
hardening.
