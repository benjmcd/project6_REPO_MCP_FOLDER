# Source Intake Provider Public URL Prepare/Status Backend API

Status: branch-local backend/API implementation; targeted validation passed.

Boundary: `source_intake_provider_public_url_prepare_status_backend_api`.

Implementation branch: `codex/l3-provider-public-prepare-status-api`.

## Scope admitted

This pass implements only the backend/API prepare and status surfaces selected by `341_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_ROUTE_ENTRY_FREEZE.md`.

Admitted runtime surface:

- owner service: `backend/app/services/layer3_provider_public_url.py`
- API route: POST `/api/v1/layer3/handoff/export/download/provider-public-url/prepare`
- API route: GET `/api/v1/layer3/handoff/export/download/provider-public-url/status/{provider_public_url_receipt_id}`
- API tests: `backend/tests/test_layer3_api.py`
- progress/proof docs and manifests

The prepare route derives provider-public durable state only from an existing provider-private signed URL receipt and the existing provider-public URL durable-state substrate. The status route reads only the redacted durable receipt state.

## Authority and non-exposure contract

- The request requires `provider_private_signed_url_receipt_id`, `recipient_scope`, `delivery_mode: provider_public_url`, and `operator_decision: prepare_provider_public_url`.
- Forbidden request fields remain fail-closed, including `provider_public_url`, `public_url`, `raw_public_url`, `public_proxy_url`, `download_url`, connector/destination fields, package mutation fields, source expansion fields, and auth/security override fields.
- No raw public URL value is persisted or returned.
- Responses expose only `provider_public_url_redacted: provider-public-url:redacted`.
- `raw_public_url_exposed` remains `false`.
- `public_url_enabled` remains `false`.
- Provider network and provider object-store writes remain disabled.
- The fake provider URL is an internal deterministic basis only for hashing/redacted durable state.

## Explicitly blocked

- No provider-public URL delivery/use route is added.
- No provider-public URL revoke route is added.
- No rendered provider-public controls are added.
- No `public_url_enabled: True` authority rail is admitted.
- No raw public URL persistence or response exposure is admitted.
- No provider network or object-store write behavior is admitted.
- No public proxy URL runtime is admitted.
- No connector/destination dispatch is admitted.
- No package mutation/reconstruction is admitted.
- No source expansion, local-directory authority, web connector retrieval, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-only durable authority is admitted.

## Validation

- `python -m pytest .\backend\tests\test_layer3_api.py -k "provider_public_url"` -> targeted API tests passed.
- `python -m pytest .\backend\tests\test_layer3_provider_public_url_state.py` -> provider-public durable-state tests passed.
- `python .\tools\l3-progress-check.py` -> PASS.
- `git diff --check` -> CRLF warnings only.

## Next boundary

After merge, the required next action is current-main proof/control sync for this prepare/status backend API slice before any provider-public delivery/use route, revoke route, rendered controls, `public_url_enabled: True` rail, public proxy runtime, connector/destination dispatch, package mutation/reconstruction, source expansion, RAG/vector behavior, broad qualitative behavior, auth/security behavior, or frontend-only durable authority can be frozen.

Next boundary: `source_intake_provider_public_url_prepare_status_backend_api_current_main_sync`.
