# 337 - Source Intake Provider Public URL Authority Contract

Status: planning/control authority contract only; no runtime behavior admitted.

## Selected contract

`source_intake_provider_public_url_authority_contract` is the required predecessor to any `source_intake_provider_public_url_boundary` implementation.

The selected implementation-entry posture is `provider_public_url_runtime_blocked_until_substrate_freeze`.

## Canonical source of truth

The future provider-public URL path may not derive authority from browser state, free-form request fields, or frontend-only durable state. It must derive authority from server-owned state that proves:

- a complete source-intake external export/download prepare authority chain
- a same-origin source-intake delivery authority chain
- a used source-intake same-origin signed-reference receipt authority chain
- a provider-private signed URL receipt authority chain
- a separate provider-public URL authority row or explicitly proven existing equivalent

Current-main authority does not contain the last item, so runtime remains blocked.

## Required future substrate decisions

Before implementation, the next freeze must decide and prove:

- provider/object-store owner: fake-provider-only, real provider object store, or an explicitly bounded adapter
- public URL identity: deterministic receipt id, object identity hash, and authority hash basis
- public URL value handling: redaction in all persisted/audit/response contexts unless a specific delivery endpoint must return it
- TTL and expiry: maximum TTL, clock source, expired-state transition, and failure code
- revocation: idempotency key, revoked-by authority, reason hashing, and fail-closed use/status behavior
- stale authority: exact mismatch fields and next allowed actions
- replay and use model: whether public URLs are status-only, externally consumed, single-use, multi-use, or no-use API
- route/DTO contract: prepare, status, revoke, and any delivery/use endpoint shape
- model/migration contract: required rows, indexes, uniqueness constraints, and audit rows
- rendered controls: when controls may appear, what browser state may store, and what raw URL material must stay absent
- auth/security: authorization, leakage, log safety, response headers, cache policy, and access revocation behavior
- tests: owner-service, API schema, negative forbidden-field, durable-state, rendered UI, and headed/headless proof obligations

## Runtime admission rule

No implementation may proceed until a later freeze names exactly one provider-public URL runtime mode and proves the substrate above. The first allowed code-bearing slice must be narrower than the full public URL lifecycle if any route/model/migration/auth decision remains unsettled.

## Explicit non-goals

No provider-public URL runtime is admitted.
No public proxy URL runtime is admitted.
No connector/destination dispatch is admitted.
No package mutation or reconstruction is admitted.
No source expansion, local-directory authority, web connector retrieval, RAG/vector behavior, broad qualitative behavior, full mockup activation, route/model/migration change, auth/security behavior, or frontend-only durable authority is admitted.

## Next required decision

The next decision is `source_intake_provider_public_url_substrate_freeze`.

That freeze must choose whether provider-public URL support can reuse or extend the existing provider-private fake-provider/durable-state family, or whether a new provider-public row family and route contract is required. If that cannot be proven from repository authority, the correct output remains audit/recon rather than runtime implementation.
