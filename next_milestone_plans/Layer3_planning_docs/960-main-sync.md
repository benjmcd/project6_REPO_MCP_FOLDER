# 960 - Provider-Private Current-Main Sync

## Status

Status: current-main proof checkpoint after PR #1586 landed the source-directory provider-private redacted lifecycle.

Current-main authority: `project6-origin/main` at `7ed8ec1d Add source-directory provider-private lifecycle`.

Source implementation checkpoint: `959-provider-private-source-directory-use.md`.

## Scope

This checkpoint records post-merge evidence only. It introduces no route, DTO, database model, migration, service behavior, rendered UI behavior, provider object behavior, connector dispatch, source expansion, RAG/vector/model runtime, public URL/proxy behavior, frontend-only durable authority, or full mockup activation.

The merged runtime remains bounded to one exact artifact family:

- `source_directory_hybrid_context_packet_qualitative_analysis` external export/download package artifact;
- source-directory-specific provider-private prepare/status/use/revoke lifecycle;
- server-owned redacted use;
- durable receipt/audit state;
- TTL/expiry projection;
- revocation and fail-closed replay/stale-authority rejection.

The generic provider-private signed URL use route remains absent:

```yaml
blocked_route: POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use
```

## Current-Main Verification

Commands run from `worktrees/l3-provider-private-main-sync` against the detached current-main checkout before this checkpoint branch was created:

```powershell
python -m py_compile .\backend\app\api\layer3.py .\backend\app\services\layer3_source_directory_hybrid_analysis.py
node --check .\backend\app\review_ui\static\layer3.js
python .\tools\l3-progress-check.py
python -m pytest backend/tests/test_layer3_api.py::test_layer3_api_provider_private_signed_url_openapi_prepare_status_schema backend/tests/test_layer3_api.py::test_layer3_api_provider_private_signed_url_revoke_success_idempotency_and_fail_closed backend/tests/test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_provider_private_to_public_redacted_use -q
npx playwright test e2e/layer3-workbench.spec.js -g "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path" --project=chromium
npx playwright test e2e/layer3-workbench.spec.js -g "Layer 3 workbench proves source-directory scan to hybrid handoff delivery live server path" --project=chromium --headed
```

Observed result:

```yaml
py_compile: pass
node_check: pass
l3_progress_check: pass
focused_pytest: 3 passed
playwright_chromium_headless: 1 passed
playwright_chromium_headed: 1 passed
remote_pr_checks:
  backend-layer3-api: success
  test: success
```

## Remaining Work

Current-main follow-up: `961-provider-private-sync.md` records that the package replacement/supersession provider-private lifecycle proof and hybrid stale/replay/revoked rendered proof have since landed through PRs `#1592` through `#1596`.

Immediate next pass: run the bounded operator runbook from `952-bounded-trial-checkpoint-runbook.md` when a full readiness recheck is needed, or stop until product authority selects a new exact artifact family or journey-specific extension.

Mid-term remaining passes:

- admit any next provider-private artifact family only through a separate freeze;
- keep the operator runbook synchronized with current-main proof;
- preserve same-origin and redacted-provider delivery boundaries while adding any new controls;
- re-run headed/headless rendered proof after each operator-path extension.

Long-term remaining target:

- governed provider-private/redacted delivery lifecycle coverage for the bounded Layer 3 source-directory package/handoff path;
- every critical mockup operator journey live, read-only, intentionally excluded, or explicitly blocked by current-main evidence;
- no full mockup activation until a separate final readiness audit proves all blockers closed.
