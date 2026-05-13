# Source Intake Provider Public URL Revoke Backend API

Status: branch-local backend/API implementation; targeted validation passed.

Boundary: `source_intake_provider_public_url_revoke_backend_api`.

Implementation branch: `codex/l3-provider-public-revoke-api`.

## Scope admitted

This pass implements only the provider-public URL revoke backend/API slice selected by `344_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_REVOKE_ROUTE_FREEZE.md`.

Admitted runtime surface:

- owner service update: `backend/app/services/layer3_provider_public_url.py`
- API route: POST `/api/v1/layer3/handoff/export/download/provider-public-url/revoke`
- API DTOs and OpenAPI schema in `backend/app/api/layer3.py`
- API tests in `backend/tests/test_layer3_api.py`
- progress/proof docs and verifier updates

The revoke route uses existing provider-public durable receipt state and `revoke_provider_public_url_receipt`. It does not expose or deliver a usable public URL.

## Authority and non-exposure contract

- Required request authority includes `provider_public_url_receipt_id`, `idempotency_key`, `revoked_by`, `revocation_reason`, and `operator_decision: revoke_provider_public_url`.
- Forbidden request fields remain fail-closed, including `provider_public_url`, `public_url`, `raw_public_url`, `public_proxy_url`, `download_url`, provider credentials/secrets/tokens, connector/destination fields, package mutation fields, source expansion fields, local-directory/web-connector/RAG-vector fields, browser durable authority, and auth/security override fields.
- Idempotent retries over the same revocation basis return the same revoked receipt state.
- Conflicting idempotency for the same receipt fails closed.
- Missing receipt revocation fails closed.
- The existing status route observes revoked state.
- No raw public URL value is persisted or returned.
- `raw_public_url_exposed` remains `false`.
- `public_url_enabled` remains `false`.

## Explicitly blocked

- No provider-public URL delivery/use route is added.
- No rendered provider-public controls are added.
- No `public_url_enabled: True` authority rail is admitted.
- No raw public URL persistence or response exposure is admitted.
- No provider network or object-store write behavior is admitted.
- No public proxy URL runtime is admitted.
- No connector/destination dispatch is admitted.
- No package mutation/reconstruction is admitted.
- No source expansion, local-directory authority, web connector retrieval, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-only durable authority is admitted.

## Validation

- `python -m pytest .\backend\tests\test_layer3_api.py -k "provider_public_url"` -> 3 passed.
- `python -m pytest .\backend\tests\test_layer3_provider_public_url_state.py` -> provider-public durable-state tests passed.
- `python .\tools\l3-progress-check.py` -> PASS.
- `git diff --check` -> CRLF warnings only.

## Next boundary

After merge, the required next action is current-main proof/control sync for this revoke backend API slice before any provider-public delivery/use route, rendered controls, `public_url_enabled: True` rail, public proxy runtime, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector behavior, broad qualitative behavior, auth/security behavior, or frontend-only durable authority can be frozen.

Next boundary: `source_intake_provider_public_url_revoke_backend_api_current_main_sync`.
