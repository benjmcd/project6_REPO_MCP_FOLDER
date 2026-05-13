# 341 - Source Intake Provider Public URL Route Entry Freeze

Status: planning/control route-entry freeze only; no runtime route behavior admitted.

## Selected next implementation

`source_intake_provider_public_url_prepare_status_backend_api` is selected as the next bounded code-bearing slice.

The first route implementation may add only backend/API prepare and status surfaces over the current-main provider-public URL durable-state substrate from PR `#929`. It may not add public URL delivery/use, rendered controls, public proxy behavior, connector/destination dispatch, package mutation, source expansion, auth/security behavior, or frontend-only durable authority.

## Canonical authority chain

The future route implementation must derive authority from:

- source-intake external export/download prepare authority
- source-intake same-origin delivery authority
- source-intake signed-reference use receipt authority
- source-intake provider-private signed URL receipt authority
- provider-public URL durable-state authority/receipt rows from `0024_layer3_provider_public_url_state.py`

Request fields may not become authority for source artifact identity, provider-private receipt identity, raw public URL exposure, or browser state.

## Route shape constraints

The next implementation may add:

- a prepare endpoint that records a provider-public URL durable receipt using server-owned authority and hashed/redacted public URL material
- a status endpoint that returns receipt state and redacted metadata only
- API request/response DTO/schema proof for forbidden raw public URL leakage and blocked non-admitted fields
- owner-service/API tests proving idempotency, stale authority, TTL, revocation awareness, and redaction

The next implementation must not add:

- public URL delivery/use route
- revoke route unless separately frozen
- rendered controls
- `public_url_enabled: True` on existing rails
- raw public URL persistence or response exposure
- provider network/object-store writes
- public proxy URL runtime
- connector/destination dispatch
- package mutation/reconstruction
- source expansion or RAG/vector behavior
- broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-only durable authority

## Stop conditions

Stop in audit/recon if implementation requires auth/security policy changes, real object-store ACL behavior, raw public URL response semantics, rendered-control state, connector/destination dispatch, or any route beyond prepare/status.

## Next required action

The next allowed implementation is `implement_source_intake_provider_public_url_prepare_status_backend_api` only.
