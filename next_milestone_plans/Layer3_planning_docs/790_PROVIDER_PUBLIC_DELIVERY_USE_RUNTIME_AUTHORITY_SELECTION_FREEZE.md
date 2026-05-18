# 790 - Provider-Public Delivery/Use Runtime Authority Selection Freeze

## Status

Status: planning/control selection freeze for `provider_public_delivery_use_exposure_security_revocation_runtime_authority_selection_after_source_directory_vector_retrieval_runtime_sync`.

Doc: `790_PROVIDER_PUBLIC_DELIVERY_USE_RUNTIME_AUTHORITY_SELECTION_FREEZE.md`.

Predecessor current-main sync doc: `789_SOURCE_DIRECTORY_MATERIAL_DETERMINISTIC_VECTOR_RETRIEVAL_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main preflight checkpoint: `ff1a8dec534d99823c667da5ca7f051c7ccb437c`.

Selected from posture: `select_provider_public_delivery_use_exposure_security_revocation_runtime_authority_after_source_directory_vector_retrieval_runtime_sync`.

Entry decision: `freeze_only`.

Runtime status: `not_implemented`.

Runtime behavior introduced by this freeze: `false`.

## Selection Basis

Current main has synced the source-directory chain through governed local-directory intake, material admission, deterministic text indexing, deterministic lexical retrieval, response-safe context packet assembly, deterministic context-packet-grounded qualitative-hybrid analysis, deterministic embedding/vector index authority, and deterministic local source-directory vector retrieval.

The pivot rule now applies to the source-directory vector retrieval family: do not continue additional same-family vector retrieval proof loops unless current-main evidence names a concrete unresolved defect or named downstream reader.

Current main also records `provider_public_delivery_use_exposure_security_revocation_authority_contract` as no-runtime in `776_PROVIDER_PUBLIC_AUTH_CONTRACT.md` and synced in `777_PROVIDER_PUBLIC_AUTH_CONTRACT_SYNC.md`, because exposure, security, revocation-after-exposure, provider/object-store, public access, leak-control, and audit authority were absent.

The next selected authority question is therefore a runtime-authority selection/freeze for provider-public delivery/use, not implementation. This pass selects only a fake-provider, redacted, contract-runtime authority question so the next contract can determine whether a bounded provider-public delivery/use runtime may be admitted without real provider/network/public exposure.

## Current Live Authority

The current live provider-public authority is:

- `backend/app/services/layer3_provider_public_url.py`;
- `backend/app/services/layer3_provider_public_url_state.py`;
- `backend/app/api/layer3.py`;
- `backend/tests/test_layer3_provider_public_url_state.py`;
- `383_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_DELIVERY_USE_RUNTIME_FREEZE.md`;
- `384_SOURCE_INTAKE_PROVIDER_PUBLIC_URL_DELIVERY_USE_RUNTIME_FREEZE_CURRENT_MAIN_SYNC.md`;
- `776_PROVIDER_PUBLIC_AUTH_CONTRACT.md`; and
- `777_PROVIDER_PUBLIC_AUTH_CONTRACT_SYNC.md`.

That authority currently supports redacted provider-public prepare, status, and revoke state only.

Current main uses `layer3_provider_public_url_fake_provider`, returns `provider_public_url_redacted`, keeps `raw_public_url_exposed: False`, keeps `public_url_enabled: False`, and records `provider_network_enabled: False` and `provider_object_write_enabled: False`.

Current main exposes only:

- `POST /handoff/export/download/provider-public-url/prepare`;
- `GET /handoff/export/download/provider-public-url/status/{provider_public_url_receipt_id}`; and
- `POST /handoff/export/download/provider-public-url/revoke`.

Current main does not expose provider-public `/use` or `/deliver` runtime, does not persist or return a raw public URL, and does not admit `public_url_enabled: true`.

## Selected Future Authority Question

Selected major deferred lane: `provider_public_delivery_use`.

Selected provider mode for the next contract question: `fake_provider_only_contract_runtime`.

Selected future authority question: `provider_public_delivery_use_exposure_security_revocation_runtime_authority_contract`.

Selected future contract posture: `write_provider_public_delivery_use_exposure_security_revocation_runtime_authority_contract_before_runtime`.

Selected future owner surface, if the next contract admits implementation: `backend/app/services/layer3_provider_public_url_delivery_use.py`.

Selected future proof surface, if the next contract admits implementation: `backend/tests/test_layer3_provider_public_url_delivery_use.py`.

The next contract must decide whether to admit only a bounded fake-provider redacted delivery/use decision over existing provider-public receipts. It must not select a real provider, network egress, raw URL exposure, public proxy, provider object write, provider credential, rendered control, or frontend-durable authority.

## Selected Authority Inputs For The Next Contract

The next contract must bind any future fake-provider delivery/use decision to:

- an existing `L3ProviderPublicUrlReceipt`;
- an existing `L3ProviderPublicUrlObjectAuthority`;
- the authority hash and source artifact hash/size already recorded by provider-public prepare;
- current provider-public receipt state: prepared, expired, or revoked;
- server clock authority for TTL and expiry;
- existing redacted fake-provider authority `layer3_provider_public_url_fake_provider`;
- existing `raw_public_url_exposed: False`;
- existing `public_url_enabled: False`; and
- existing no-network/no-provider-object-write authority.

The next contract must fail closed for missing receipt, missing authority row, stale authority hash, wrong artifact hash, wrong source artifact size, expired receipt, revoked receipt, malformed receipt id, forbidden URL/provider/credential fields, and any attempt to request real provider/network/public exposure.

## Selected Exposure, Security, And Revocation Question

Exposure class selected for the next contract question: `redacted_fake_provider_receipt_use_decision_only`.

Audience selected for the next contract question: `server_authorized_layer3_operator_or_internal_backend_caller_only`.

Artifact sensitivity selected for the next contract question: `existing_finalized_external_export_artifact_reference_only`.

Raw URL policy selected for the next contract question: `never_return_raw_public_url`.

Public access selected for the next contract question: `no_public_anonymous_access`.

Revocation semantics selected for the next contract question: expired or revoked receipts must deny future fake-provider delivery/use decisions and return response-safe state only.

Replay semantics selected for the next contract question: status-only replay; no download bytes, public redirect, provider object read, or raw URL replay.

Leak-control selected for the next contract question: responses, logs, errors, traces, screenshots, DOM, browser storage, audit payloads, and proof manifests must not contain raw public URLs, provider credentials, raw object keys, tokens, signatures, or local paths.

HTTP delivery selected for the next contract question: no cross-origin HTTP delivery, no public redirect, no byte streaming, no proxy body, no CORS change, no CSP change, no referrer-policy change, and no content-disposition change unless a later freeze separately admits rendered or HTTP delivery behavior.

## Non-Admission Boundary

This freeze admits no runtime behavior, backend route, API DTO, response model, database model, migration, provider adapter, provider credential, provider object write/copy/mutation/ACL change, raw public URL exposure, `public_url_enabled: true` rail, public proxy route, provider-public delivery/use route, rendered delivery/use control, frontend-durable authority, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, network egress, source expansion, arbitrary source ingestion, RAG/vector indexing expansion, embedding generation expansion, prompt/model/provider runtime, broad qualitative generation, auth/security behavior change, full mockup activation, raw local path exposure, or source `L3OutputPackage` mutation.

No closed or blocked provider-public, connector, package, source, RAG/vector, auth/security, or frontend-durable lane is reopened by implication.

## Future Step Chain

1. Merge this selection freeze only after review/check clearance.
2. Sync this freeze to current main.
3. Write `provider_public_delivery_use_exposure_security_revocation_runtime_authority_contract` as planning/control only.
4. Sync that contract to current main.
5. If the contract admits a bounded fake-provider implementation-entry freeze, write that freeze before code; otherwise stop as no-runtime.
6. Implement only the exact fake-provider/redacted service, route, DTO, response, and proof surface admitted by the later freeze.
7. Do not proceed to real provider/network use, raw public URL exposure, public proxy behavior, provider object writes, connector dispatch, package mutation, source expansion, additional RAG/vector behavior, rendered controls, frontend-durable authority, or auth/security broadening until a later exact freeze admits that behavior.

## Next Posture

The next exact posture after merge is `current_main_sync_provider_public_delivery_use_exposure_security_revocation_runtime_authority_selection_after_source_directory_vector_retrieval_runtime_sync`.

After that sync, the next exact posture is `write_provider_public_delivery_use_exposure_security_revocation_runtime_authority_contract_before_runtime`.
