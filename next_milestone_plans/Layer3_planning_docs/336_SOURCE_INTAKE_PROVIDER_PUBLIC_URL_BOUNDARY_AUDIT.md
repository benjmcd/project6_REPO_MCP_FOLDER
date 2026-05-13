# 336 - Source Intake Provider Public URL Boundary Audit

Status: current-main implementation-entry audit; no runtime behavior admitted.

## Decision

`source_intake_provider_public_url_boundary` is not safe to implement as the next code-bearing slice from current-main authority.

The next required action is `source_intake_provider_public_url_authority_contract` as planning/control only. It must define the provider/object-store or fake-provider public URL authority substrate before any route, DTO, model, migration, service, or rendered-control implementation can proceed.

## Repo-confirmed authority

- Current branch authority starts after PR `#925` merged the post-PR924 provider-private proof/control sync and doc `335_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_BOUNDARY_FREEZE.md`.
- `backend/app/models/models.py` contains durable `L3ProviderPrivateSignedUrl*` authority, receipt, revocation, and audit rows, but no provider-public URL row family.
- `backend/app/services/layer3_provider_private_signed_url_state.py` persists only provider-private signed URL durable state, token hashes, receipt state, single-use replay, expiry, revocation, and audit events.
- `backend/app/services/layer3_provider_private_signed_url.py` forbids `public_url`, `public_proxy_url`, `provider_url`, `download_url`, and `signed_url` in provider-private prepare and keeps `public_url_enabled: False`.
- `backend/app/services/layer3_provider_private_signed_url_fake_provider.py` keeps the fake provider as provider-private only and returns `public_url_enabled: False`.
- `backend/app/services/layer3_external_export_response.py` keeps same-origin delivery public URL and signed URL controls disabled.
- `backend/tests/test_layer3_api.py`, `backend/tests/test_layer3_workbench.py`, and `backend/tests/test_layer3_page.py` prove provider-public URL fields remain deferred, forbidden, absent, or disabled.

## Why implementation is blocked

The current repository has negative contracts for provider-public URL behavior, but no positive public URL lifecycle contract. A correct implementation would require decisions that are not yet frozen:

- provider/object-store or fake-provider public URL owner authority
- public URL identity and receipt schema
- TTL, expiry, revocation, stale-authority, and replay semantics
- redaction and leak-control rules for public URL values
- status/revoke/audit behavior and idempotency policy
- route and DTO contract shape
- rendered control affordance and stored browser state
- auth/security implications for making any public URL reachable

Implementing runtime behavior without those decisions would broaden scope beyond doc `335` and would risk converting existing negative sentinels into an under-specified public delivery mechanism.

## Explicit non-goals

No provider-public URL runtime is admitted.
No public proxy URL runtime is admitted.
No connector/destination dispatch is admitted.
No package mutation or reconstruction is admitted.
No source expansion, local-directory authority, web connector retrieval, RAG/vector behavior, broad qualitative behavior, full mockup activation, route/model/migration change, auth/security behavior, or frontend-only durable authority is admitted.

## Next required artifact

Create `source_intake_provider_public_url_authority_contract` before code. That contract must either:

- prove an existing repo-owned substrate can safely represent provider-public URL authority without schema or route widening; or
- explicitly freeze the minimal new substrate, routes, DTOs, model/migration, security, tests, and rendered-control boundaries required for provider-public URL runtime.

Until then, the correct next operational posture is audit/recon, not implementation.
