# 1357 SEC EDGAR Live Source Service Gate

Target: `sec_edgar_live_source_artifact_service_level_feature_gate_v1`.

This slice hardens the existing SEC EDGAR live source-artifact acquisition lane by making the owner
service enforce the live-network feature flag before any acquisition client can run. It also extends
the SEC XBRL runtime posture projection so the operator can see that live source acquisition requires
both live-network authorization and a server-configured SEC User-Agent, without exposing the raw
User-Agent value.

## Decision

```yaml
entry_decision: implemented
owner_service: backend/app/services/layer3_sec_edgar_live_source_artifact.py
posture_surface: live_sec_edgar_network_source_acquisition
service_level_gate: LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED
redacted_configuration_status: LAYER3_SEC_EDGAR_USER_AGENT
raw_user_agent_exposed: false
browser_supplied_url_allowed: false
production_readiness_claimed: false
```

The service now fails closed before operator confirmation, User-Agent lookup, cache replay,
rate-limit state, or `SEC_EDGAR_CLIENT.fetch_complete_submission_text` can run when the live-network
flag is disabled. Test-only fake clients must opt into the flag explicitly.

## Non-Goals

- no default-on change for live SEC network acquisition;
- no live SEC EDGAR request during validation;
- no Arelle invocation, value reveal, delivery/export, runtime DB write, schema/model/migration
  change, or production-readiness claim;
- no raw SEC URL, local path, artifact bytes, raw User-Agent, frontend durable authority, connector
  dispatch, provider write, parser expansion, or browser-supplied acquisition authority.

## Verification

```powershell
..\..\.venvs\project6-py312\Scripts\python.exe -m pytest .\backend\tests\test_sec_xbrl_runtime_posture.py -q
..\..\.venvs\project6-py312\Scripts\python.exe -m pytest .\backend\tests\test_layer3_api.py -k "sec_edgar_text_table_live_source_artifact" -q
..\..\.venvs\project6-py312\Scripts\python.exe -m pytest .\backend\tests\test_review_browser_server.py -k "patch_state or sec_edgar_live_source_artifact_acquisition" -q
..\..\.venvs\project6-py312\Scripts\python.exe -m pytest .\backend\tests\test_layer3_page.py -k "sec_xbrl_runtime_posture or controlled_value_reveal or legacy_arelle_value_reveal" -q
$env:PLAYWRIGHT_USE_SYSTEM_CHROME='1'; $env:PLAYWRIGHT_PYTHON='..\..\.venvs\project6-py312\Scripts\python.exe'; npx playwright test --project=chromium -g "SEC EDGAR live source artifact|SEC XBRL runtime posture" --reporter=line
$env:PLAYWRIGHT_USE_SYSTEM_CHROME='1'; $env:PLAYWRIGHT_PYTHON='..\..\.venvs\project6-py312\Scripts\python.exe'; npx playwright test --project=chromium -g "SEC EDGAR live source artifact|SEC XBRL runtime posture" --headed --reporter=line
```

Result: focused posture tests pass (`6 passed`); focused live source-artifact API tests pass
(`3 passed, 293 deselected`); focused review-browser server tests pass (`2 passed, 18 deselected`);
focused static Layer3 page checks pass (`3 passed, 22 deselected`); focused Playwright Chromium
proof passes in headless and headed modes (`2 passed` each).

## Next Posture

Use the hardened live acquisition gate as the prerequisite for one bounded live-source activation
run, or move to Arelle invocation proof, delivery/export/package status, multi-filing gate
enforcement, or nonlocal operator-auth hardening as separately bounded implementation passes.
