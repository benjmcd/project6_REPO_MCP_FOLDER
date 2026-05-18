# 795 - Provider-Public Delivery/Use Fake-Provider Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `provider_public_delivery_use_fake_provider_redacted_runtime_implementation`.

Sync doc: `795_PROVIDER_PUBLIC_DELIVERY_USE_FAKE_PROVIDER_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime doc: `794_PROVIDER_PUBLIC_DELIVERY_USE_FAKE_PROVIDER_RUNTIME_IMPLEMENTATION_ENTRY_FREEZE.md`.

Runtime PR: `#1399`.

Runtime branch: `codex/l3-pp-use-runtime`.

Runtime branch commit: `81625823561540d2c4ae17d5ee20e24cdd0515b9`.

Runtime merge commit: `15cd06a6c394d0fd49db1a5bc2e00956b2431834`.

Sync branch: `codex/l3-pp-use-main-sync`.

Synced result: `current_main_synced_provider_public_delivery_use_fake_provider_redacted_runtime_implementation`.

Next posture: `select_source_expansion_ingestion_named_source_family_after_provider_public_delivery_use_runtime_sync`.

## Current-Main Result

Current main now includes the bounded fake-provider redacted provider-public delivery/use runtime implementation from doc `794`.

Current main includes:

- `backend/app/services/layer3_provider_public_url_delivery_use.py`;
- `backend/tests/test_layer3_provider_public_url_delivery_use.py`;
- `POST /handoff/export/download/provider-public-url/use`;
- response schema `layer3.provider_public_url.delivery_use.v1`;
- request fixed value `delivery_use_mode: fake_provider_redacted_use_decision`; and
- request fixed value `operator_decision: use_provider_public_url_redacted_fake_provider`.

The current-main runtime reads existing `L3ProviderPublicUrlReceipt` and `L3ProviderPublicUrlObjectAuthority` state only. It returns response-safe fake-provider delivery/use decisions for prepared provider-public receipts, denies expired or revoked receipts, and fails closed for missing receipt, missing authority, stale authority hash, source artifact mismatch, or forbidden provider/url/credential/network/package/source/RAG/auth/frontend fields.

## Merge Gate

PR `#1399` merged on 2026-05-18 at merge commit `15cd06a6c394d0fd49db1a5bc2e00956b2431834`.

Before merge:

- `backend-layer3-api`: `SUCCESS`, `3m6s`;
- `test`: `SUCCESS`, `3m40s`;
- PR comments: `0`;
- PR reviews: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`; and
- merge state: `CLEAN`.

## Runtime Behavior

Runtime behavior introduced by implementation PR: `true`.

Runtime behavior introduced by this sync: `false`.

The current-main synced runtime keeps:

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

## Non-Admission Boundary

This current-main sync admits no real provider adapter, provider credential, provider object write/copy/mutation/ACL change, raw public URL exposure, `public_url_enabled: true` rail, public proxy route, public anonymous access, public redirect, byte streaming, rendered delivery/use control, frontend-durable authority, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, source expansion, arbitrary source ingestion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, web connectors, RAG/vector indexing expansion, embedding generation expansion, prompt/model/provider runtime, broad qualitative generation, auth/security behavior change, full mockup activation, raw local path exposure, or source `L3OutputPackage` mutation.

## Validation

Current-main sync validation:

- `python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_provider_public_url_openapi_prepare_status_schema -q` - `PASS`, `1 passed`;
- `python -m pytest .\backend\tests\test_layer3_provider_public_url_delivery_use.py -q` - `PASS`, `9 passed`;
- `python -m pytest .\backend\tests\test_layer3_provider_public_url_state.py .\backend\tests\test_layer3_provider_public_url_delivery_use.py -q` - `PASS`, `15 passed`;
- `python -m pytest .\backend\tests\test_layer3_api.py -q` - `PASS`, `187 passed`;
- `python -c "import json; [json.load(open(p, encoding='utf-8')) for p in ['next_milestone_plans/layer3_progress_manifest.json','next_milestone_plans/layer3_workbench_proof_manifest.json']]; print('json manifests ok')"` - `PASS`;
- `python -m py_compile .\tools\l3-progress-check.py .\backend\app\services\layer3_provider_public_url_delivery_use.py .\backend\app\api\layer3.py .\backend\tests\test_layer3_provider_public_url_delivery_use.py .\backend\tests\test_layer3_api.py` - `PASS`;
- `python .\tools\l3-progress-check.py` - `PASS`;
- `python .\tools\l3-target-selection-validate.py --expect frozen` - `PASS`; and
- `git diff --check` - `PASS`.

## Next Posture

The provider-public delivery/use fake-provider runtime lane is current-main synced.

Do not continue additional same-family provider-public delivery/use proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader.

The next major deferred lane is `select_source_expansion_ingestion_named_source_family_after_provider_public_delivery_use_runtime_sync`.

Preferred first source-expansion family remains a server-configured or local operator-provided directory containing CSV, JSON, TXT, and/or MD files only. PDFs, OCR, Office documents, arbitrary binaries, web connectors, arbitrary recursive ingestion, RAG/vector indexing, provider-public delivery/use broadening, real connector dispatch, credentials, network egress, package payload rewrite, source package row mutation, auth/security broadening, full mockup activation, and frontend-durable authority remain blocked until separately selected and frozen.
