# Source Intake Provider Public URL Revoke Route Freeze

Status: planning/control revoke-route freeze only; no runtime route behavior admitted.

Boundary: `source_intake_provider_public_url_revoke_route_freeze`.

Selected next implementation: `implement_source_intake_provider_public_url_revoke_backend_api`.

## Reasoning

The current-main provider-public URL surface can prepare and inspect redacted provider-public URL durable state, but it does not expose or deliver a usable public URL. Before any public URL delivery/use exposure is admitted, revocation semantics must be frozen before public URL delivery/use exposure.

This is the narrowest next boundary because the durable-state substrate already contains provider-public revocation support, while the current route layer intentionally exposes only prepare/status. Freezing revoke next keeps the lifecycle non-fragile: a future public URL cannot become usable before the system has an explicit route/API contract for stopping that receipt state.

## Admitted future write surface

The next implementation may add only:

- POST `/api/v1/layer3/handoff/export/download/provider-public-url/revoke`
- request/response DTOs for provider-public URL revocation
- owner-service function `provider_public_url_revoke` in `backend/app/services/layer3_provider_public_url.py`
- API tests proving OpenAPI shape, idempotency, stale/missing receipt fail-closed behavior, forbidden raw URL fields, redaction, and absence of unrelated state mutation
- progress/proof doc and verifier updates

## Required revoke contract

- Required request authority must include a provider-public receipt id, idempotency key, revoker identity, revocation reason, and `operator_decision: revoke_provider_public_url`.
- Forbidden request fields must include raw public URL values, provider credentials/secrets/tokens, provider object write/copy controls, connector/destination dispatch fields, package mutation fields, source expansion fields, local-directory/web-connector/RAG-vector fields, browser durable authority, and auth/security override fields.
- The route must return only redacted provider-public receipt state.
- The route must not return, persist, log, or echo a raw public URL.
- Idempotent retries over the same revocation basis must return the same revoked state.
- Conflicting idempotency for the same receipt must fail closed.
- Revoked status must be observable through the existing status route.

## Explicitly blocked

- No provider-public URL delivery/use route is admitted.
- No rendered provider-public controls are admitted.
- No `public_url_enabled: True` authority rail is admitted.
- No raw public URL persistence or response exposure is admitted.
- No provider network or object-store write behavior is admitted.
- No public proxy URL runtime is admitted.
- No connector/destination dispatch is admitted.
- No package mutation/reconstruction is admitted.
- No source expansion, local-directory authority, web connector retrieval, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-only durable authority is admitted.

## Validation required for this freeze

- `python .\tools\l3-progress-check.py` must pass.
- `git diff --check` must pass with no actionable whitespace errors.

## Next boundary

After this freeze is current-main synced, the next allowed implementation is `implement_source_intake_provider_public_url_revoke_backend_api` only.
