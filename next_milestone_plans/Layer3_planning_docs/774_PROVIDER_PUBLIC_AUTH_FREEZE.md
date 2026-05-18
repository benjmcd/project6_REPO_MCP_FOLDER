# 774 - Provider-Public Delivery/Use Authority Selection Freeze

## Status

Status: planning/control selection freeze for `provider_public_delivery_use_authority_selection_after_source_directory_qualitative_analysis_runtime_sync`.

Doc: `774_PROVIDER_PUBLIC_AUTH_FREEZE.md`.

Predecessor current-main sync doc: `773_SOURCE_DIRECTORY_MATERIAL_CONTEXT_PACKET_QUALITATIVE_HYBRID_ANALYSIS_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main preflight checkpoint: `16c7e09f7d66863eef6e55b522c3f3839711f649`.

Selected from posture: `select_next_major_layer3_deferred_lane_after_source_directory_qualitative_analysis_runtime_sync`.

Entry decision: `freeze_only`.

Runtime status: `not_implemented`.

Runtime behavior introduced by this freeze: `false`.

## Selection Basis

Current main has synced the source-directory chain through governed local-directory intake, material admission, deterministic source indexing, lexical retrieval, response-safe context packet assembly, and deterministic context-packet-grounded qualitative-hybrid analysis.

The pivot rule now applies: do not continue additional same-family source-directory qualitative-analysis proof loops unless current-main evidence names a concrete unresolved defect or a named downstream reader.

The next major deferred lane selected by this freeze is `provider_public_delivery_use`, but only as an authority-selection lane. Provider-public delivery/use is not implementation-ready because current main has previously recorded raw public URL delivery/use as blocked until exposure, security, revocation, public access, leak-control, provider/object-store, and audit authority are selected and proved.

This freeze therefore selects the next authority question, not runtime implementation.

## Selected Lane

Selected major deferred lane: `provider_public_delivery_use`.

Selected authority question: `provider_public_delivery_use_exposure_security_revocation_authority_contract`.

Selected future contract posture: `write_provider_public_delivery_use_exposure_security_revocation_authority_contract_before_runtime`.

Canonical prior provider-public no-runtime authority surfaces include:

- `187_PROVIDER_PUBLIC_URL_ENTRY_FREEZE.md`;
- `188_PROVIDER_PUBLIC_URL_ENTRY_CONTRACT.md`;
- `383_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_DELIVERY_USE_RUNTIME_FREEZE.md`;
- `384_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_DELIVERY_USE_RUNTIME_FREEZE_CURRENT_MAIN_SYNC.md`;
- `569_LAYER3_PROVIDER_PUBLIC_AUTHORITY_AUDIT_AFTER_SOURCE_INTAKE_PROVIDER_PRIVATE_AUTHORITY_SYNC.md`;
- `570_LAYER3_PROVIDER_PUBLIC_AUTHORITY_AUDIT_AFTER_SOURCE_INTAKE_PROVIDER_PRIVATE_AUTHORITY_CURRENT_MAIN_SYNC.md`;
- `backend/app/services/layer3_provider_public_url.py`;
- `backend/app/services/layer3_provider_public_url_state.py`;
- `backend/app/api/layer3.py`; and
- `backend/tests/test_layer3_provider_public_url_state.py`.

Those surfaces are authority for the existing redacted provider-public substrate and no-runtime delivery/use boundary. They are not authority to expose a raw public URL, create a provider-public `/use` or `/deliver` route, enable `public_url_enabled: true`, or add public proxy behavior.

## Required Future Contract

The next implementation-facing planning pass must write `provider_public_delivery_use_exposure_security_revocation_authority_contract`.

That contract must name, before code:

- one provider/public delivery-use mode, or an explicit no-runtime result;
- provider/object-store authority and whether the lane remains fake-provider-only;
- exposure class, audience, artifact sensitivity, and public access semantics;
- caller authority, auth/security owner, and protected-surface policy;
- TTL, expiry, replay, revocation, post-revoke access, and clock behavior;
- raw public URL redaction policy for responses, logs, traces, browser storage, DOM, screenshots, and audit records;
- cache-control, referrer, CORS, CSP, and content-disposition posture if any URL can leave origin;
- stale-authority, wrong-package, wrong-artifact, expired, revoked, malformed, missing-provider, and provider-failure behavior;
- receipt/audit/idempotency contract; and
- isolated proof architecture with fake-provider or contract-double tests before any real provider/network use.

If any field remains unknown, the later contract must stop as no-runtime and must not proceed to implementation.

## Non-Admission Boundary

This freeze admits no runtime behavior, backend route, API DTO, response model, database model, migration, provider adapter, provider credential, provider object write/copy/mutation/ACL change, raw public URL exposure, `public_url_enabled: true` rail, public proxy route, provider-public delivery/use route, rendered delivery/use control, frontend-durable authority, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, network egress, source expansion, arbitrary source ingestion, RAG/vector indexing, embedding generation, prompt/model/provider runtime, broad qualitative generation, auth/security behavior change, full mockup activation, or raw local path exposure.

No closed or blocked provider-public, connector, package, source, RAG/vector, auth/security, or frontend-durable lane is reopened by implication.

## Future Step Chain

1. Merge this selection freeze only after review/check clearance.
2. Sync this freeze to current main.
3. Write `provider_public_delivery_use_exposure_security_revocation_authority_contract` as planning/control only.
4. Sync that contract to current main.
5. If the contract admits a bounded implementation-entry freeze, write that freeze before code; otherwise stop as no-runtime.
6. Implement only the exact route/service/status surface admitted by the later freeze, then run targeted proof, review clearance, merge, and current-main sync.
7. Do not proceed to real provider/network use, public exposure, connector dispatch, package mutation, RAG/vector indexing, frontend-durable authority, or auth/security broadening until a later exact freeze admits that behavior.

## Next Posture

The next exact posture after merge is `current_main_sync_provider_public_delivery_use_authority_selection_after_source_directory_qualitative_analysis_runtime_sync`.

After that sync, the next exact posture is `write_provider_public_delivery_use_exposure_security_revocation_authority_contract_before_runtime`.
