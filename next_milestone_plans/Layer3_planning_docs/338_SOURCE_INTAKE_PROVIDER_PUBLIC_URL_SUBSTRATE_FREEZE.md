# 338 - Source Intake Provider Public URL Substrate Freeze

Status: planning/control freeze only; no runtime behavior admitted.

## Selected next implementation

`source_intake_provider_public_url_durable_state_substrate` is selected as the next bounded code-bearing slice.

The slice may add only a provider-public URL durable-state substrate and fake-provider contract double sufficient to prove identity, redaction, TTL, revocation, stale-authority, and audit semantics without exposing a public URL route or rendered control.

## Canonical source of truth

The substrate must derive authority from server-owned source-intake state:

- `layer3.source_intake_external_export_download_prepare.v1`
- `layer3.source_intake_external_export_download_delivery.v1`
- `source_intake_external_export_download_signed_reference_gate`
- source-intake provider-private signed URL receipt state
- a new provider-public URL authority/receipt/audit state family, unless implementation proves an equivalent existing state family without broadening provider-private semantics

## Required implementation boundaries

The next implementation may touch only the minimal durable-state/fake-provider/test surface needed for the substrate:

- model definitions for provider-public URL authority, receipt, revocation, and audit state
- migration definitions for those rows if model persistence is selected
- a provider-public URL state service with deterministic receipt identity, token/URL hashing, TTL, revocation, stale-authority, and redacted audit behavior
- a fake-provider contract double that never performs network or object-store writes
- owner-service tests for idempotency, expiry, revocation, stale authority, redaction, and no raw public URL persistence
- progress-control updates proving no route, DTO, rendered UI, connector/destination, package mutation, source expansion, or auth/security behavior changed

## Runtime remains blocked

The substrate implementation must not add or alter API routes.
It must not expose a raw public URL to operators, browser state, logs, persisted audit payloads, or existing same-origin delivery responses.
It must not enable `public_url_enabled: True` on current rendered or API authority rails.
It must not change provider-private signed URL route behavior.
It must not introduce real provider network, object-store, ACL, or public proxy behavior.

## Explicit non-goals

No provider-public URL prepare/status/revoke route is admitted.
No public URL delivery/use route is admitted.
No rendered provider-public URL controls are admitted.
No public proxy URL runtime is admitted.
No connector/destination dispatch is admitted.
No package mutation or reconstruction is admitted.
No source expansion, local-directory authority, web connector retrieval, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-only durable authority is admitted.

## Next required action

The next allowed implementation is `implement_source_intake_provider_public_url_durable_state_substrate` only.

If that implementation cannot prove no raw public URL persistence/exposure, deterministic idempotency, stale-authority failure, expiry/revocation fail-closed behavior, and no route/UI/runtime activation, it must stop in audit/recon rather than broaden scope.
