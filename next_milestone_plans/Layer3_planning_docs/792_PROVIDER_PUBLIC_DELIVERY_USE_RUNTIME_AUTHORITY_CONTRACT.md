# 792 - Provider-Public Delivery/Use Runtime Authority Contract

## Status

Status: planning/control authority contract for `provider_public_delivery_use_exposure_security_revocation_runtime_authority_contract`.

Contract doc: `792_PROVIDER_PUBLIC_DELIVERY_USE_RUNTIME_AUTHORITY_CONTRACT.md`.

Predecessor current-main sync doc: `791_PROVIDER_PUBLIC_DELIVERY_USE_RUNTIME_AUTHORITY_SELECTION_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_provider_public_delivery_use_exposure_security_revocation_runtime_authority_selection_after_source_directory_vector_retrieval_runtime_sync`.

Contract branch: `codex/l3-pp-use-contract`.

Current-main preflight checkpoint: `534500dffc9b60934232a8fe5780e402da8d78a0`.

Selected from posture: `write_provider_public_delivery_use_exposure_security_revocation_runtime_authority_contract_before_runtime`.

Contract result: `admit_bounded_fake_provider_redacted_provider_public_delivery_use_implementation_entry_freeze`.

Runtime behavior introduced by this contract: `false`.

## Canonical Source Of Truth

The current live authority files for this contract are:

- `backend/app/services/layer3_provider_public_url.py`;
- `backend/app/services/layer3_provider_public_url_state.py`;
- `backend/app/services/layer3_provider_public_url_fake_provider.py`;
- `backend/app/api/layer3.py`;
- `backend/tests/test_layer3_provider_public_url_state.py`;
- `790_PROVIDER_PUBLIC_DELIVERY_USE_RUNTIME_AUTHORITY_SELECTION_FREEZE.md`; and
- `791_PROVIDER_PUBLIC_DELIVERY_USE_RUNTIME_AUTHORITY_SELECTION_CURRENT_MAIN_SYNC.md`.

Current main already records redacted provider-public prepare/status/revoke state over `L3ProviderPublicUrlReceipt` and `L3ProviderPublicUrlObjectAuthority`.

Current main uses `layer3_provider_public_url_fake_provider`, records `PROVIDER_PUBLIC_URL_REDACTED_MARKER`, keeps `raw_public_url_exposed: False`, keeps `public_url_enabled: False`, sets `provider_network_enabled: False`, sets `provider_object_write_enabled: False`, and enforces `PROVIDER_PUBLIC_URL_REPLAY_POLICY_STATUS_ONLY`.

Current main exposes only:

- `POST /handoff/export/download/provider-public-url/prepare`;
- `GET /handoff/export/download/provider-public-url/status/{provider_public_url_receipt_id}`; and
- `POST /handoff/export/download/provider-public-url/revoke`.

Current main does not expose provider-public `/use` or `/deliver`, does not stream bytes, does not redirect, does not read a provider object, does not return a raw public URL, and does not admit `public_url_enabled: true`.

## Contract Decision

This contract admits the next implementation-entry freeze only.

The admitted future implementation question is a bounded fake-provider redacted delivery/use decision over existing provider-public durable state. The later implementation-entry freeze may select a read-only service and optional API surface that answers whether an existing provider-public receipt is usable under the already-recorded redacted fake-provider authority.

The admitted future provider mode is `fake_provider_only_contract_runtime`.

The admitted future response schema is `layer3.provider_public_url.delivery_use.v1`.

The admitted future service owner is `backend/app/services/layer3_provider_public_url_delivery_use.py`.

The admitted future proof owner is `backend/tests/test_layer3_provider_public_url_delivery_use.py`.

The admitted future route candidate, only if the next implementation-entry freeze admits a route, is `POST /handoff/export/download/provider-public-url/use`.

The future implementation must be read-only against provider-public durable state. It may reload existing `L3ProviderPublicUrlReceipt` and `L3ProviderPublicUrlObjectAuthority` rows, but it must not add a model, migration, durable use row, provider object row, audit row, connector row, package row, source row, vector row, or auth/security row.

## Admitted Future Request Contract

The next implementation-entry freeze may admit only these request fields:

- `client_request_id`;
- `provider_public_url_receipt_id`;
- `expected_authority_hash`;
- `expected_source_artifact_hash`;
- `expected_source_artifact_size_bytes`;
- `delivery_use_mode`; and
- `operator_decision`.

The fixed future values must be:

- `delivery_use_mode: fake_provider_redacted_use_decision`; and
- `operator_decision: use_provider_public_url_redacted_fake_provider`.

The future request must reject missing receipt id, malformed receipt id, missing authority row, stale `expected_authority_hash`, wrong `expected_source_artifact_hash`, wrong `expected_source_artifact_size_bytes`, expired receipt, revoked receipt, unknown fields, forbidden URL/provider/credential fields, and any request for real provider/network/public exposure.

## Admitted Future Response Contract

The future response may report response-safe decision state only:

- `schema_id: layer3.provider_public_url.delivery_use.v1`;
- `provider_public_url_receipt_id`;
- `provider_public_url_object_authority_id`;
- `provider_public_url_state`;
- `delivery_use_decision`;
- `delivery_use_denied_reason`;
- `provider_public_url_redacted: provider-public-url:redacted`;
- `provider_public_url_replay_policy: status_only`;
- `authority_hash`;
- `source_artifact_hash`;
- `source_artifact_size_bytes`;
- `raw_public_url_exposed: False`;
- `public_url_enabled: False`;
- `provider_network_enabled: False`;
- `provider_object_write_enabled: False`;
- `public_redirect_enabled: False`;
- `byte_streaming_enabled: False`; and
- `next_allowed_actions`.

A prepared, unexpired, unrevoked receipt may return `delivery_use_decision: allowed`.

An expired or revoked receipt must return `delivery_use_decision: denied` with response-safe state only.

The future response must never include `provider_public_url`, `public_url`, `raw_public_url`, `public_proxy_url`, `download_url`, `signed_url`, `provider_url`, `provider_credentials`, `provider_secret`, `provider_token`, `provider_bucket`, `provider_container`, `provider_object_key`, raw object identity, raw provider signature, raw local path, package payload, source payload, prompt/model/provider payload, connector payload, or browser/frontend durable state.

## Exposure, Security, And Revocation Contract

Exposure class: `redacted_fake_provider_receipt_use_decision_only`.

Audience: `server_authorized_layer3_operator_or_internal_backend_caller_only`.

Public access: `no_public_anonymous_access`.

Raw URL policy: `never_return_raw_public_url`.

Replay policy: `status_only_replay_no_download_bytes_public_redirect_provider_read_or_raw_url_replay`.

Revocation semantics: expired or revoked receipts deny future fake-provider delivery/use decisions.

HTTP delivery policy: no cross-origin HTTP delivery, no public redirect, no byte streaming, no proxy body, no CORS change, no CSP change, no referrer-policy change, and no content-disposition change.

Leak-control policy: responses, logs, errors, traces, screenshots, DOM, browser storage, audit payloads, and proof manifests must not contain raw public URLs, provider credentials, raw object keys, tokens, signatures, or local paths.

## Non-Admission Boundary

This contract admits no runtime behavior, backend route, API DTO, response model, database model, migration, durable use row, audit row, provider adapter, provider credential, provider object write/copy/mutation/ACL change, raw public URL exposure, `public_url_enabled: true` rail, public proxy route, rendered delivery/use control, frontend-durable authority, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, source expansion, arbitrary source ingestion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, web connectors, RAG/vector indexing expansion, embedding generation expansion, prompt/model/provider runtime, broad qualitative generation, auth/security behavior change, full mockup activation, raw local path exposure, or source `L3OutputPackage` mutation.

No provider-public runtime implementation begins in this contract.

## Proof Obligations For The Next Freeze

The next implementation-entry freeze must prove that its selected runtime surface can cover:

- prepared receipt allowed decision without raw URL exposure;
- expired receipt denied decision;
- revoked receipt denied decision;
- missing receipt and missing authority fail-closed behavior;
- stale authority hash rejection;
- source artifact hash and size mismatch rejection;
- forbidden URL/provider/credential/network/package/source/RAG/auth/frontend fields;
- no durable row creation beyond reading existing provider-public state; and
- no `provider_public_url`, `public_url`, `raw_public_url`, provider credential, provider object key, local path, package payload, source payload, connector payload, prompt/model/provider payload, or browser/frontend durable state in responses or proof artifacts.

## Next Posture

The next exact posture after merge is `current_main_sync_provider_public_delivery_use_exposure_security_revocation_runtime_authority_contract_after_selection_sync`.

After that sync, the next exact posture is `freeze_provider_public_delivery_use_fake_provider_redacted_runtime_implementation_entry`.

Do not proceed to implementation until that implementation-entry freeze is current-main selected, review-cleared, synced, and guarded.
