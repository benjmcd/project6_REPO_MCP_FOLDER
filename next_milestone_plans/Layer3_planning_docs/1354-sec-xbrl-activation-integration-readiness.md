# 1354 SEC XBRL Activation Integration Readiness

Target: `sec_xbrl_activation_integration_readiness_v1`.

Branch: `claude/sec-xbrl-activation-integration` (from `claude/sec-xbrl-value-reveal`, tip `311a305a`).

## Purpose

Doc 1353 activated activation-lane items 2-3 (value-reveal authority + controlled
value-reveal submit). This readiness pass audits the remaining activation surfaces against
the live code and classifies each as ACTIVATE-NOW (offline/in-app, reversible) or HOLD-LIVE
(requires live SEC network egress or an arelle subprocess). It is the integration entry for
wiring the lane to "usable in full" through the API while keeping every authority-artifact
redaction invariant intact.

## Repo-Confirmed Baseline

- Full `test_sec_xbrl*.py` + `test_layer3_api.py` via the documented Tier-2 / short-basetemp
  invocation: **835 passed, 1 failed**.
- The single failure is
  `test_layer3_api_rejects_sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_stale_or_unsafe`:
  a `FileNotFoundError` writing `canonical_internal.json` under a **271-character** path
  (Windows MAX_PATH = 260), in the test's monkeypatched secondary storage dir. It is the
  known Windows MAX_PATH artifact-write noise (see project test-invocation note); commit
  `311a305a` does not touch that construction/handoff path. **No real regression.**

## Surface Classification

All flags live in `backend/app/core/config.py` (single source of truth).

| # | Surface | Class | Mechanism | Offline-safe |
|---|---------|-------|-----------|--------------|
| 1 | Default-on runtime posture | DONE | `layer3_sec_edgar_arelle_fact_authority_cutover_enabled=True` (config.py:93); assessment report decision `default_on_runtime_enabled` | yes |
| 2-3 | Value-reveal authority + controlled submit | DONE (1353) | `layer3_sec_xbrl_controlled_value_reveal_submit_enabled=True` (config.py:113) | yes |
| 4 | E2E integration live | ACTIVATE-NOW | NEW route in `api/layer3.py` calling `open_redacted_operator_review_from_offline_evidence`; NEW flag `layer3_sec_xbrl_e2e_offline_orchestrator_route_enabled` | yes (no source acquisition / arelle / value reveal at the route) |
| 5 | Multi-filing evidence authority gate | ACTIVATE-NOW | NEW route calling `inspect_sec_xbrl_multi_filing_evidence_authority_gate`; NEW flag `layer3_sec_xbrl_multi_filing_authority_gate_route_enabled` | yes (pure inspection; no network/db/subprocess) |
| 6 | In-app auth policy | ACTIVATE-NOW (partial gap) | `authorize_sec_xbrl_route` already enforced on 5 routes; remaining gap = no-id bypass on 3 review-workflow routes; close behind `layer3_sec_xbrl_auth_policy_route_enforcement_strict` | yes (headers + settings only) |
| - | Arelle governed-sibling reveal | ACTIVATE-NOW iff coherent | `layer3_sec_edgar_arelle_value_reveal_enabled` (config.py:109, False); route wired; depends on sidecars written with `layer3_sec_edgar_arelle_internal_value_store_enabled=True` | yes (reads pre-stored value store; no subprocess/network) |
| - | Live SEC acquisition | HOLD-LIVE | `layer3_sec_edgar_live_network_enabled` (config.py:83, False) + `LAYER3_SEC_EDGAR_USER_AGENT` | **no** (real HTTP to data.sec.gov) |

## Redaction Invariants (must remain intact through every activation)

- Authority-artifact redaction: email, local path, URL, proxy header, raw CIK/identity,
  secrets stay redacted in every response and log.
- Identity-looking value suppression on revealed facts.
- Every new route runs output through the existing leak guards
  (`reject_report_public_text_references` / `_reject_response_leaks` for the gate;
  `_reject_output_raw_or_local_authority` / `reject_e2e_public_output_policy` for e2e).
- `FORBIDDEN_REQUEST_FIELDS` (in-app auth policy) and the gate `RAW_VALUE_KEYS` /
  `RAW_AUTHORITY_KEYS` input guards are unchanged.

## Activation Rules

- Every new-surface flag is a reversible config default; new-route flags default ON
  (activated) and fail closed when flipped OFF. No schema / Alembic / data migration.
- Default-off / validate-only tests are reconciled to the activated posture while retaining
  explicit-off (flag-off -> fail-closed) coverage. No coverage is deleted.
- Live SEC network egress and live arelle subprocess remain HOLD-LIVE in this integration:
  documented with their exact recipe, not flipped. The acquisition route
  (`api/layer3.py` acquire endpoint) is additionally noted as lacking auth-policy binding;
  activating live acquisition must add that binding first.

## Verification (per surface and at reconciliation)

```powershell
$py = "C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.venvs\project6-py312\Scripts\python.exe"
$env:DATABASE_URL = "sqlite:///C:/p6xbrl/backend/test_method_aware.db"
$env:STORAGE_DIR = "C:\p6xbrl\backend\app\storage_test_runtime"
# from C:\p6xbrl\backend:
& $py -m pytest (Get-ChildItem tests\test_sec_xbrl*.py).FullName tests\test_layer3_api.py --basetemp=C:\pt -q
python tools/l3-progress-check.py
git diff --check
```
