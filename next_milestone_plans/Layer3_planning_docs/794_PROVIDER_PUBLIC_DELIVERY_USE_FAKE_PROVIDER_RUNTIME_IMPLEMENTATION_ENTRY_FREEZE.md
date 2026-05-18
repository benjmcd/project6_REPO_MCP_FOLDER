# 794 - Provider-Public Delivery/Use Fake-Provider Runtime Implementation Entry Freeze

## Status

Status: branch-local implementation-entry freeze and runtime proof for `provider_public_delivery_use_fake_provider_redacted_runtime_implementation_entry`.

Runtime doc: `794_PROVIDER_PUBLIC_DELIVERY_USE_FAKE_PROVIDER_RUNTIME_IMPLEMENTATION_ENTRY_FREEZE.md`.

Runtime branch: `codex/l3-pp-use-runtime`.

Current-main preflight checkpoint: `bcf5cb3b196e56c4d3532c97c8eb8778e858cb2c`.

Predecessor current-main sync doc: `793_PROVIDER_PUBLIC_DELIVERY_USE_RUNTIME_AUTHORITY_CONTRACT_CURRENT_MAIN_SYNC.md`.

Predecessor synced result: `current_main_synced_provider_public_delivery_use_exposure_security_revocation_runtime_authority_contract_after_selection_sync`.

Selected from posture: `freeze_provider_public_delivery_use_fake_provider_redacted_runtime_implementation_entry`.

Selected implementation action: `implement_provider_public_delivery_use_fake_provider_redacted_runtime_after_contract_sync`.

Runtime result: `provider_public_delivery_use_fake_provider_redacted_runtime_implemented_branch_local`.

Runtime behavior introduced by this pass: `true`.

## Canonical Source Of Truth

The current live authority files for this implementation-entry freeze and runtime proof are:

- `backend/app/services/layer3_provider_public_url.py`;
- `backend/app/services/layer3_provider_public_url_state.py`;
- `backend/app/services/layer3_provider_public_url_fake_provider.py`;
- `backend/app/services/layer3_provider_public_url_delivery_use.py`;
- `backend/app/api/layer3.py`;
- `backend/tests/test_layer3_provider_public_url_state.py`;
- `backend/tests/test_layer3_provider_public_url_delivery_use.py`;
- `792_PROVIDER_PUBLIC_DELIVERY_USE_RUNTIME_AUTHORITY_CONTRACT.md`; and
- `793_PROVIDER_PUBLIC_DELIVERY_USE_RUNTIME_AUTHORITY_CONTRACT_CURRENT_MAIN_SYNC.md`.

The canonical runtime state remains existing provider-public durable state: `L3ProviderPublicUrlReceipt` and `L3ProviderPublicUrlObjectAuthority`.

No new model, migration, durable use row, provider object row, audit row, connector row, package row, source row, vector row, or auth/security row is added by this slice.

## Frozen Runtime Surface

This freeze admits only the read-only fake-provider redacted delivery/use decision over existing provider-public URL receipt and object-authority state.

The implemented service owner is `backend/app/services/layer3_provider_public_url_delivery_use.py`.

The implemented proof owner is `backend/tests/test_layer3_provider_public_url_delivery_use.py`.

The implemented API route is `POST /handoff/export/download/provider-public-url/use`.

The implemented response schema is `layer3.provider_public_url.delivery_use.v1`.

The implemented provider mode is `fake_provider_only_contract_runtime`.

The implemented request fixed values are:

- `delivery_use_mode: fake_provider_redacted_use_decision`; and
- `operator_decision: use_provider_public_url_redacted_fake_provider`.

The implemented request fields are:

- `client_request_id`;
- `provider_public_url_receipt_id`;
- `expected_authority_hash`;
- `expected_source_artifact_hash`;
- `expected_source_artifact_size_bytes`;
- `delivery_use_mode`; and
- `operator_decision`.

## Runtime Behavior

A prepared, unexpired, unrevoked provider-public receipt returns `delivery_use_decision: allowed`.

An expired provider-public receipt returns `delivery_use_decision: denied` with `delivery_use_denied_reason: provider_public_url_expired`.

A revoked provider-public receipt returns `delivery_use_decision: denied` with `delivery_use_denied_reason: provider_public_url_revoked`.

Missing receipt, malformed receipt id, missing authority row, stale `expected_authority_hash`, wrong `expected_source_artifact_hash`, wrong `expected_source_artifact_size_bytes`, non-admitted fixed values, missing required fields, and forbidden URL/provider/credential/network/package/source/RAG/auth/frontend fields fail closed.

The route returns response-safe decision state only. It does not stream bytes, redirect, proxy, read a provider object, write a provider object, call a provider network, invoke a connector, mutate a package, expand source intake, write retrieval/indexing state, or create frontend durable state.

## Leak-Control And No-Write Guarantees

The runtime always returns `provider_public_url_redacted: provider-public-url:redacted`.

The runtime always returns:

- `raw_public_url_exposed: False`;
- `public_url_enabled: False`;
- `provider_network_enabled: False`;
- `provider_object_write_enabled: False`;
- `public_redirect_enabled: False`;
- `byte_streaming_enabled: False`;
- `durable_use_row_created: False`;
- `audit_row_created: False`;
- `provider_credentials_enabled: False`;
- `connector_dispatch_enabled: False`;
- `package_mutation_enabled: False`;
- `source_expansion_enabled: False`;
- `rag_vector_indexing_enabled: False`; and
- `frontend_durable_authority_enabled: False`.

The runtime response, error path, route contract, and proof file must not contain raw public URLs, provider credentials, raw object keys, provider signatures, local paths, package payloads, source payloads, connector payloads, prompt/model/provider payloads, or browser/frontend durable state.

## Proof Coverage

Focused proof command:

`python -m pytest .\backend\tests\test_layer3_provider_public_url_delivery_use.py -q`

Branch-local result: `9 passed`.

The focused proof covers:

- prepared receipt allowed decision without raw URL exposure;
- no provider network, provider object write, public redirect, byte streaming, connector dispatch, package mutation, source expansion, RAG/vector indexing, or frontend durable authority;
- no durable use row or audit row creation during delivery/use;
- expired receipt denied decision;
- revoked receipt denied decision;
- missing receipt fail-closed behavior;
- missing authority fail-closed behavior;
- stale authority hash rejection;
- source artifact hash mismatch rejection;
- source artifact size mismatch rejection;
- forbidden URL/provider credential field rejection;
- API route redaction; and
- OpenAPI request schema guardrails for the implemented `/use` route.

## Non-Admission Boundary

This implementation-entry freeze and runtime proof admits no real provider adapter, provider credential, provider object write/copy/mutation/ACL change, raw public URL exposure, `public_url_enabled: true` rail, public proxy route, public anonymous access, public redirect, byte streaming, cross-origin HTTP delivery, CORS change, CSP change, referrer-policy change, content-disposition change, rendered delivery/use control, frontend-durable authority, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, source expansion, arbitrary source ingestion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, web connectors, RAG/vector indexing expansion, embedding generation expansion, prompt/model/provider runtime, broad qualitative generation, auth/security behavior change, full mockup activation, raw local path exposure, or source `L3OutputPackage` mutation.

## Next Posture

The next exact posture after merge is `await_current_main_sync_for_provider_public_delivery_use_fake_provider_redacted_runtime_implementation`.

After current-main sync, do not continue additional same-family provider-public delivery/use proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader. The next major lane should pivot to `select_source_expansion_ingestion_named_source_family_after_provider_public_delivery_use_runtime_sync`.
