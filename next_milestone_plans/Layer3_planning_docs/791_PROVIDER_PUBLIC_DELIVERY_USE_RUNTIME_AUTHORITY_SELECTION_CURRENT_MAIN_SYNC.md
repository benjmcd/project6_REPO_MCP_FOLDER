# 791 - Provider-Public Delivery/Use Runtime Authority Selection Current-Main Sync

## Status

Status: current-main proof/control sync for `provider_public_delivery_use_exposure_security_revocation_runtime_authority_selection_after_source_directory_vector_retrieval_runtime_sync`.

Sync doc: `791_PROVIDER_PUBLIC_DELIVERY_USE_RUNTIME_AUTHORITY_SELECTION_CURRENT_MAIN_SYNC.md`.

Selection doc: `790_PROVIDER_PUBLIC_DELIVERY_USE_RUNTIME_AUTHORITY_SELECTION_FREEZE.md`.

Selection PR: `#1395`.

Selection branch: `codex/l3-provider-public-runtime-select`.

Selection branch commit: `ceaf0071f989c8c4162810f11aa0ea68c5c0d387`.

Selection merge commit and current-main checkpoint: `e649f70446b4d2f533a5e33eec9bc3fbfb14065c`.

Sync branch: `codex/l3-provider-public-runtime-select-sync`.

Synced result: `current_main_synced_provider_public_delivery_use_exposure_security_revocation_runtime_authority_selection_after_source_directory_vector_retrieval_runtime_sync`.

Runtime behavior introduced by selection PR: `false`.

Runtime behavior introduced by this sync: `false`.

## Merge Gate

PR `#1395` merged cleanly after adding `provider_public_delivery_use_exposure_security_revocation_runtime_authority_selection_after_source_directory_vector_retrieval_runtime_sync`.

The merge gate was:

- `backend-layer3-api`: `SUCCESS`, `2m47s`;
- `test`: `SUCCESS`, `3m42s`;
- comments totalCount: `0`;
- reviews totalCount: `0`;
- latestReviews totalCount: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`; and
- merge state before merge: `CLEAN`.

## Current-Main Result

Current main now includes `790_PROVIDER_PUBLIC_DELIVERY_USE_RUNTIME_AUTHORITY_SELECTION_FREEZE.md`.

Current main now records `provider_public_delivery_use` as the next selected major deferred lane after source-directory vector retrieval runtime sync.

Current main now selects `fake_provider_only_contract_runtime` as the provider mode for the next contract question.

Current main now selects `provider_public_delivery_use_exposure_security_revocation_runtime_authority_contract` as the next authority question.

Current main now selects `write_provider_public_delivery_use_exposure_security_revocation_runtime_authority_contract_before_runtime` as the next exact posture.

Current main now selects `backend/app/services/layer3_provider_public_url_delivery_use.py` and `backend/tests/test_layer3_provider_public_url_delivery_use.py` as future owner/proof surfaces only if a later contract and implementation-entry freeze admit implementation.

Current main still records the live provider-public authority as redacted prepare/status/revoke state only through `backend/app/services/layer3_provider_public_url.py`, `backend/app/services/layer3_provider_public_url_state.py`, and `backend/app/api/layer3.py`.

Current main still uses `layer3_provider_public_url_fake_provider`, keeps `raw_public_url_exposed: False`, keeps `public_url_enabled: False`, and exposes no provider-public `/use` or `/deliver` runtime.

## Post-Merge Validation

Post-merge validation at `e649f70446b4d2f533a5e33eec9bc3fbfb14065c` passed:

- JSON manifest load;
- `python -m py_compile .\tools\l3-progress-check.py`;
- `python .\tools\l3-progress-check.py`;
- `python .\tools\l3-target-selection-validate.py --expect frozen`;
- `python -m pytest .\backend\tests\test_layer3_provider_public_url_state.py -q`; and
- `git diff --check`.

## Still Blocked

This sync admits no runtime behavior, backend route, API DTO, response model, database model, migration, provider adapter, provider credential, provider object write/copy/mutation/ACL change, raw public URL exposure, `public_url_enabled: true` rail, public proxy route, provider-public delivery/use route, rendered delivery/use control, frontend-durable authority, package construction, package mutation/reconstruction, package payload rewrite, handoff/export rerun, connector/destination dispatch, real connector invocation, credentials, network egress, source expansion, arbitrary source ingestion, arbitrary recursive ingestion, PDFs, OCR, Office documents, arbitrary binaries, web connectors, RAG/vector indexing expansion, embedding generation expansion, prompt/model/provider runtime, broad qualitative generation, auth/security behavior change, full mockup activation, raw local path exposure, or source `L3OutputPackage` mutation.

No provider-public runtime implementation begins in this sync.

## Next Posture

The next exact current-main posture is `write_provider_public_delivery_use_exposure_security_revocation_runtime_authority_contract_before_runtime`.

That posture must remain planning/control unless it proves exact authority for a bounded fake-provider, redacted provider-public delivery/use contract. It must not add provider-public delivery/use routes, raw public URL exposure, provider credentials/adapters/object writes, rendered controls, connector dispatch, network egress, package mutation/reconstruction, source expansion, RAG/vector expansion, auth/security broadening, full mockup activation, frontend-durable authority, or raw local path exposure.
