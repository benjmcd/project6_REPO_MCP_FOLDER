# Provider Private Signed URL Rendered UI Proof

Status: implemented proof for `provider_private_signed_url_rendered_ui`.

This document follows `245_PROVIDER_PRIVATE_SIGNED_URL_RENDERED_UI_FREEZE.md` and `246_PROVIDER_PRIVATE_SIGNED_URL_RENDERED_UI_CONTRACT.md`. It records the bounded `/review/layer3` rendered UI implementation over the already-live provider-private prepare/status/revoke backend APIs.

## Implemented scope

```yaml
selected_planning_mode: provider_private_signed_url_rendered_ui
implementation_branch: codex/l3-provider-rendered-ui
allowed_runtime_slice: rendered_prepare_status_revoke_controls_only
live_route: /review/layer3
backend_api_change: false
model_or_migration_change: false
use_route_status: closed_not_implemented
raw_token_display: false
provider_network_behavior: false
```

The implementation adds rendered controls inside the existing external export/download band:

- `#provider-private-signed-url-prepare`
- `#provider-private-signed-url-status`
- `#provider-private-signed-url-revoke`
- `#provider-private-signed-url-panel`

## Authority flow

The prepare request is derived from the already-recorded external export/download authority state. The UI does not ask the operator for provider credentials, provider URLs, local paths, connector destinations, package mutation details, source expansion details, or provider-private token material.

The rendered flow is:

1. external export/download readiness is prepared through the existing canonical raw-mixed rendered path;
2. provider-private prepare posts only the backend DTO allowlist plus `delivery_mode: provider_private_signed_url` and `operator_decision: prepare_provider_private_signed_url`;
3. the returned `provider_signed_url_receipt_id` becomes the only receipt handle used by rendered status and revoke;
4. status uses `GET /api/v1/layer3/handoff/export/download/provider-private-signed-url/status/{provider_signed_url_receipt_id}`;
5. revoke posts the receipt id, idempotency key, fixed rendered-workbench revocation actor, fixed revocation reason, and `operator_decision: revoke_provider_private_signed_url`;
6. status-after-revoke confirms `provider_private_signed_url_revoked`.

## Negative invariants preserved

- no `POST /api/v1/layer3/handoff/export/download/provider-private-signed-url/use` route call;
- no `#provider-private-signed-url-use` rendered control;
- no raw provider-private token request field;
- no raw provider-private token display;
- no provider/public URL exposure beyond the existing redacted marker;
- no connector/destination dispatch;
- no package mutation/reconstruction;
- no source expansion;
- no same-origin delivery or same-origin signed-reference behavior change;
- no backend/API/model/migration/service change.

## Proof

The focused Playwright proof is:

```text
Layer 3 workbench drives raw mixed rendered provider-private signed URL prepare status revoke
```

It proves:

- prepare request payload allowlist;
- status-after-prepare;
- revoke request payload allowlist;
- status-after-revoke;
- redacted response display;
- provider-private `use` control absence;
- provider-private `use` route-call absence;
- forbidden connector/destination, package mutation/replacement/supersession, and source expansion absence;
- live theme parity across `system`, `light`, `dark`, and `workbench` at `materialized-source-selection` and `provider-private-signed-url-revoked` checkpoints.

Required validation commands:

```powershell
python .\tools\l3-progress-check.py
python -m pytest .\backend\tests\test_layer3_api.py -q -k provider_private_signed_url
python -m pytest .\backend\tests\test_layer3_provider_private_signed_url_state.py -q
npx playwright test e2e/layer3-workbench.spec.js --grep "provider-private signed URL prepare status revoke" --project=chromium
npx playwright test e2e/layer3-workbench.spec.js --grep "provider-private signed URL prepare status revoke" --project=chromium --headed
git diff --check
```
