# 776 - Provider-Public Delivery/Use Exposure Security Revocation Authority Contract

## Status

Status: planning/control authority contract for `provider_public_delivery_use_exposure_security_revocation_authority_contract`.

Contract doc: `776_PROVIDER_PUBLIC_AUTH_CONTRACT.md`.

Predecessor sync doc: `775_PROVIDER_PUBLIC_AUTH_SYNC.md`.

Predecessor synced result: `current_main_synced_provider_public_delivery_use_authority_selection_after_source_directory_qualitative_analysis_runtime_sync`.

Contract branch: `codex/l3-provider-public-contract`.

Current-main preflight checkpoint: `9904ece3a6d34c910fe33231253e952f2d3e6811`.

Selected from posture: `write_provider_public_delivery_use_exposure_security_revocation_authority_contract_before_runtime`.

Contract result: `no_runtime_now_provider_public_delivery_use_exposure_security_revocation_authority_absent`.

Runtime behavior introduced by this contract: `false`.

## Canonical Source Of Truth

The current live authority files for this contract are:

- `backend/app/services/layer3_provider_public_url.py`;
- `backend/app/services/layer3_provider_public_url_state.py`;
- `backend/app/api/layer3.py`;
- `next_milestone_plans/Layer3_planning_docs/774_PROVIDER_PUBLIC_AUTH_FREEZE.md`; and
- `next_milestone_plans/Layer3_planning_docs/775_PROVIDER_PUBLIC_AUTH_SYNC.md`.

The provider-public code currently implements redacted prepare, status, and revoke state only. It uses the fake provider authority `layer3_provider_public_url_fake_provider`, records hashed/redacted provider-public URL state, returns `provider_public_url_redacted`, keeps `raw_public_url_exposed: False`, keeps `public_url_enabled: False`, and reports no provider network or provider object write.

The API currently exposes:

- `POST /handoff/export/download/provider-public-url/prepare`;
- `GET /handoff/export/download/provider-public-url/status/{provider_public_url_receipt_id}`; and
- `POST /handoff/export/download/provider-public-url/revoke`.

The API does not expose a provider-public delivery/use route, does not return a raw public URL, and does not admit `public_url_enabled: true`.

## Contract Decision

This pass does not admit provider-public delivery/use runtime.

The admitted authority remains the existing redacted lifecycle substrate only:

- prepare a redacted provider-public receipt from an already prepared provider-private signed URL receipt;
- inspect redacted provider-public status;
- revoke the redacted provider-public receipt; and
- audit that raw provider-public URL material is hashed/redacted rather than exposed.

The following authority is still absent and must be selected before any future delivery/use runtime can begin:

- exposure classification for artifact sensitivity, audience, and operator intent;
- caller authorization and access-control policy for public delivery/use;
- raw URL leak-control policy for storage, return, logging, browser, clipboard, DOM, screenshot, and trace surfaces;
- revocation-after-exposure semantics, including post-revoke observability and stale-link behavior;
- cache, referrer, CORS, CSP, content-disposition, and downstream sharing policy;
- provider or object-store owner, adapter, network-egress boundary, credential boundary, bucket/container/object identity, and ACL policy;
- audit receipt requirements for exposure, access, revocation, and leakage controls; and
- proof architecture for fake-provider contract tests before any real provider or public access.

Because those authority inputs are not current-main selected, this contract freezes the current result as `no_runtime_now_provider_public_delivery_use_exposure_security_revocation_authority_absent`.

## Explicit No-Go Surface

This contract admits no backend route, API DTO, response model, database model, migration, provider adapter, provider credential, provider object write/copy/mutation/ACL change, raw public URL exposure, `public_url_enabled: true`, public proxy route, rendered delivery/use control, frontend-durable authority, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, network egress, source expansion, arbitrary source ingestion, RAG/vector indexing, embedding generation, prompt/model/provider runtime, broad qualitative generation, auth/security behavior change, full mockup activation, or raw local path exposure.

## Future Admission Requirements

A future provider-public delivery/use runtime pass may begin only after a fresh current-main freeze selects all of the following:

1. Provider mode: fake-provider-only contract runtime or a named real provider, but not both.
2. Exposure model: what public means, who may see it, whether the artifact is shareable, and what is never exposed.
3. Security model: caller identity, operator authorization, tenant/project boundary, rate limiting, and abuse handling.
4. Revocation model: TTL, one-time or replay semantics, post-revoke link behavior, expired-link status, and audit retention.
5. Leak-control model: raw URL redaction in server logs, API responses, browser state, frontend DOM, clipboard paths, screenshots, traces, and error bodies.
6. Provider/object-store model: credential source, network-egress policy, object identity, write/copy rules, ACL update rules, and receipt evidence.
7. HTTP delivery model: cache-control, referrer policy, CORS, CSP, content-disposition, content-type, and byte-range behavior.
8. Proof model: isolated fake-provider tests first, negative forbidden-field tests, revocation transition tests, no-raw-secret assertions, and explicit no-network proof unless real provider authority is separately frozen.

## Next Posture

The next exact posture after merge is `current_main_sync_provider_public_delivery_use_exposure_security_revocation_authority_contract`.

After that sync, if current-main proof still shows no concrete provider-public delivery/use runtime authority, the next exact posture is `select_next_major_layer3_deferred_lane_after_provider_public_delivery_use_authority_contract_no_runtime_sync`.

No additional same-family provider-public proof loop should continue unless current-main evidence names a concrete unresolved defect or a newly selected provider-public downstream reader.
