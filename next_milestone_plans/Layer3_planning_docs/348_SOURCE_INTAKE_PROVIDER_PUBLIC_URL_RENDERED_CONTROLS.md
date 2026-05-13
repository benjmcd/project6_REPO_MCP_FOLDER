# Source Intake Provider Public URL Rendered Controls

Status: branch-local implementation; bounded rendered controls over existing provider-public prepare/status/revoke APIs.

Branch: `codex/l3-provider-public-rendered-controls`.

Boundary: `source_intake_provider_public_url_rendered_controls`.

## Implemented surface

- `/review/layer3` now includes provider-public prepare/status/revoke controls in the existing external export/download readiness band.
- The controls call only `POST /api/v1/layer3/handoff/export/download/provider-public-url/prepare`, `GET /api/v1/layer3/handoff/export/download/provider-public-url/status/{provider_public_url_receipt_id}`, and `POST /api/v1/layer3/handoff/export/download/provider-public-url/revoke`.
- The UI displays server-returned `provider_public_url_redacted` and status metadata only.
- Delivery/use, public proxy access, raw public URL display, and browser durable authority remain explicitly blocked.

## Authority and non-fragility constraints

- Canonical source of truth is the existing backend provider-public API and durable provider-public receipt state.
- Browser state is in-memory control state only for the active page session.
- No provider-public receipt recovery storage key was added.
- No `localStorage` or `sessionStorage` provider-public durable authority was added.
- The controls require an existing prepared provider-private receipt before provider-public prepare becomes available.
- Revoke requires an explicit operator button action and shows revoked state only after the server revoke/status response.

## Explicitly not admitted

- No provider-public delivery route.
- No provider-public use route.
- No raw public URL rendering.
- No raw public URL copy/download affordance.
- No public proxy runtime.
- No `public_url_enabled: True` UI authority.
- No provider network or object-store writes beyond the existing fake-provider backend authority.
- No connector/destination dispatch.
- No package mutation or reconstruction.
- No source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-only durable authority.

## Validation

Branch-local validation passed:

- `python -m pytest .\backend\tests\test_layer3_page.py -q` -> `3 passed, 3 warnings`
- `python -m pytest .\backend\tests\test_layer3_api.py -k "provider_public_url" -q` -> `3 passed, 146 deselected, 3 warnings`
- `python -m pytest .\backend\tests\test_layer3_provider_public_url_state.py -q` -> `5 passed`
- `node --check .\backend\app\review_ui\static\layer3.js` -> passed
- `npx playwright test e2e/layer3-workbench.spec.js --grep "provider-public URL prepare status revoke" --project=chromium` -> `1 passed`
- `npx playwright test e2e/layer3-workbench.spec.js --grep "provider-public URL prepare status revoke" --project=chromium --headed` -> `1 passed`
- `python .\tools\l3-progress-check.py` -> `PASS`
- `git diff --check` -> no actionable whitespace errors; CRLF normalization warnings only

## Next boundary

After this implementation is merged and current-main synced, the next action should be a current-main proof/control sync for this rendered-controls slice before selecting any delivery/use or downstream provider-public expansion.
