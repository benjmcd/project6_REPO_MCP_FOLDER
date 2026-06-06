# SEC XBRL Usable-In-Full Runbook

Status: branch-local activation integration on `claude/sec-xbrl-activation-integration`.

This runbook records the operator path that is live on this branch: default-on
SEC XBRL fact authority, controlled value reveal, offline evidence workflow open,
multi-filing authority-gate inspection, route-level posture visibility, and strict
in-app route policy on the operator-review no-id branches.

It does not claim live SEC network acquisition, live Arelle subprocess execution,
provider/export delivery, or unrestricted production readiness.

## Launch

From the repository root:

```powershell
.\project6.ps1 -Action start-api -BaseUrl http://127.0.0.1:8000
```

The wrapper starts `uvicorn main:app` from `backend` and waits for
`http://127.0.0.1:8000/health`.

The direct equivalent is:

```powershell
Set-Location .\backend
py -3.12 -m uvicorn main:app --host 127.0.0.1 --port 8000
```

## Active Surfaces

The activation posture endpoint is:

```text
GET /api/v1/layer3/sec-xbrl/activation-posture
```

Expected branch-local active surfaces:

- `value_reveal_submit`: active through
  `layer3_sec_xbrl_controlled_value_reveal_submit_enabled=True`.
- `arelle_fact_authority_cutover`: active through
  `layer3_sec_edgar_arelle_fact_authority_cutover_enabled=True`.
- `multi_filing_gate_route`: active through
  `layer3_sec_xbrl_multi_filing_authority_gate_route_enabled=True`.
- `e2e_offline_orchestrator_route`: active through
  `layer3_sec_xbrl_e2e_offline_orchestrator_route_enabled=True`.
- `arelle_value_reveal`: inactive by default.
- `live_sec_acquisition`: hold-live by default.

The posture response is capability state only. It does not expose identities,
accessions, local paths, SEC URLs, proxy headers, raw values, or authority
artifacts.

## Full Offline-Safe Workflow

The branch-local operator workflow starts from already available offline evidence.
The e2e open route does not perform live SEC acquisition and does not invoke
Arelle.

```text
POST /api/v1/layer3/sec-xbrl/e2e/offline-operator-review/open
```

The route opens the redacted operator-review workflow and returns a workflow id
plus basis hash when the offline evidence lineage is valid. Its controls report:

- `offline_evidence_input_only=True`
- `source_acquisition_performed=False`
- `arelle_invoked=False`
- `value_reveal_performed=False`

The operator-review routes are:

```text
POST /api/v1/layer3/sec-xbrl/operator-review/workflow/status
POST /api/v1/layer3/sec-xbrl/operator-review/workflow/decision/submit
POST /api/v1/layer3/sec-xbrl/operator-review/workflow/decision/status
```

Strict no-id enforcement is active through
`layer3_sec_xbrl_auth_policy_route_enforcement_strict=True`. If that flag is
set false, the old no-id bypass behavior is restored for rollback.

After an approved operator decision, prepare the value-reveal authority receipt:

```text
POST /api/v1/layer3/sec-xbrl/value-reveal/authority/prepare
```

Then submit controlled value reveal with the authority receipt id, authority
basis hash, and explicit operator confirmation:

```text
POST /api/v1/layer3/sec-xbrl/value-reveal/submit
```

Inspect the hash/count receipt status with:

```text
GET /api/v1/layer3/sec-xbrl/value-reveal/submit/status/{sec_xbrl_controlled_value_reveal_submit_receipt_id}
```

The submit route may return transient revealed figures. The status route remains
hash/count only.

## Multi-Filing Gate

The multi-filing authority gate is live through:

```text
POST /api/v1/layer3/sec-xbrl/multi-filing-authority-gate/inspect
```

It inspects supplied filing evidence and returns ready/blocked state with hashes
and counts only. When
`layer3_sec_xbrl_multi_filing_authority_gate_route_enabled=False`, it fails
closed with `sec_xbrl_multi_filing_authority_gate_route_feature_flag_disabled`.

## Hold-Live Boundaries

Live SEC acquisition remains gated:

```text
LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED=false
```

Do not flip this as part of the activation-integration lane. A future live
acquisition lane must bind the acquisition route to the in-app route policy and
record separate network, rate-limit, user-agent, rollback, and containment proof.

The Arelle governed-sibling value reveal remains gated:

```text
LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED=false
```

It is not coherent to flip that flag alone. The governed-sibling reveal reads
from the internal value store written during sidecar authority creation. A
coherent operator exercise requires this two-flag recipe in a controlled lane:

```text
LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED=true
LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED=true
```

That recipe changes sidecar-write persistence behavior, so this integration lane
keeps it out of the default posture. Controlled value reveal through the SEC XBRL
authority/submit lineage is already the default operator value-reveal path.

## Rollback

Each new activation surface is reversible by config:

```text
LAYER3_SEC_XBRL_MULTI_FILING_AUTHORITY_GATE_ROUTE_ENABLED=false
LAYER3_SEC_XBRL_E2E_OFFLINE_ORCHESTRATOR_ROUTE_ENABLED=false
LAYER3_SEC_XBRL_AUTH_POLICY_ROUTE_ENFORCEMENT_STRICT=false
LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED=false
LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED=false
```

Flag-off tests cover the new route fail-closed behavior and the strict-auth
rollback path.

## Verification

Use the Windows short basetemp to avoid unrelated MAX_PATH noise:

```powershell
$py = "C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.venvs\project6-py312\Scripts\python.exe"
$env:DATABASE_URL = "sqlite:///C:/p6xbrl/backend/test_method_aware.db"
$env:STORAGE_DIR = "C:\p6xbrl\backend\app\storage_test_runtime"
Set-Location .\backend
& $py -m pytest (Get-ChildItem .\tests\test_sec_xbrl*.py).FullName .\tests\test_layer3_api.py --basetemp=C:\pt -q
```

Expected branch-local result before final reconciliation: `854 passed, 1 failed`,
where the single failure is the known Windows MAX_PATH path-length case in
`test_layer3_api_rejects_sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_stale_or_unsafe`.
