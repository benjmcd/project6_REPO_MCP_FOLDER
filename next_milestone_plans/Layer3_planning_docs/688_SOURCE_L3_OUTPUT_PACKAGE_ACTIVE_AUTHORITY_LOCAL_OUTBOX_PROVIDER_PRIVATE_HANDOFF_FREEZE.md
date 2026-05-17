# 688 - Source L3 Output Package Active Authority Local Outbox Provider-Private Handoff Freeze

## Status

Status: implementation-entry freeze for `source_l3_output_package_active_authority_local_outbox_provider_private_handoff`.

Doc: `688_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_FREEZE.md`.

Predecessor sync doc: `687_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_SERVER_OWNED_LOCAL_OUTBOX_WRITE_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before freeze: `80eaddb27335a560ab2275d0a901954f7d96dfd1`.

Selected follow-on surface: `downstream_active_package_authority_read_adoption`.

Selected reader path: `local_outbox_provider_private_handoff`.

Selected route: `POST /api/v1/layer3/handoff/connector/local-outbox/provider-private/prepare`.

Selected owner services:

- `backend/app/services/layer3_local_outbox_provider_private_handoff.py`;
- `backend/app/services/layer3_server_owned_local_outbox_write.py`;
- `backend/app/services/layer3_server_owned_local_outbox_target.py`;
- `backend/app/services/layer3_connector_local_destination_receipt.py`;
- `backend/app/services/layer3_package_replacement_activation.py`.

Selected validation seam: recorded `server_owned_local_outbox_write`, `server_owned_local_outbox_target`, `connector_local_destination_receipt`, `connector_dispatch_record`, `external_export_download_prepare`, and local outbox artifact hash/size validation.

Selected operator action: `adopt_active_replacement_package_authority_for_local_outbox_provider_private_handoff`.

Selected implementation-entry mode: `source_l3_output_package_active_authority_local_outbox_provider_private_handoff`.

No runtime begins in this freeze.

## Decision

The next Layer 3 package-lifecycle follow-on surface is downstream active-package-authority read adoption for exactly one named reader path: `local_outbox_provider_private_handoff`.

Current main now proves active replacement authority through handoff/export prepare, APS handoff dispatch, external export/download prepare, same-origin delivery, connector dispatch, connector-local destination receipt, fake target, and server-owned local outbox write. The next downstream provider-private preparation boundary is `POST /api/v1/layer3/handoff/connector/local-outbox/provider-private/prepare`, which prepares a fake/provider-private handoff from the durable server-owned local outbox write receipt after validating the receipt chain and stored outbox artifact.

This freeze selects provider-private handoff because it is the next stale downstream reader after server-owned local outbox write. Rendered activation controls remain useful and may be selected later. External local export adoption, package rebuild, and package payload rewrite remain deferred unless current-main authority separately selects them.

## Authority Source

Future implementation or proof must use only current durable authority:

- approved package construction and package-review submit authority;
- recorded `source_l3_output_package_replacement_activation` state;
- replacement namespace and replacement artifact manifest authority;
- recorded `handoff_export_prepare` state and internal export envelope;
- recorded `aps_handoff_dispatch` state and APS bundle descriptor;
- recorded `external_export_download_prepare` readiness state;
- recorded same-origin `external_export_download_deliver` authority;
- recorded internal connector dispatch state;
- recorded `connector_local_destination_receipt` state;
- recorded `server_owned_local_outbox_target` state;
- recorded `server_owned_local_outbox_write` state;
- source `L3OutputPackage` rows for provenance and stale-authority checks only;
- response-safe active replacement artifact refs and hashes already projected into upstream handoff/export, APS dispatch, external export/download readiness, delivery, connector dispatch, connector-local receipt, fake target, and server-owned local outbox write proof.

Future implementation must fail closed if provider-private handoff authority cannot be tied back to the exact source package set, active replacement authority, APS handoff dispatch state, external export/download readiness record, delivery validation, connector dispatch record, connector-local receipt, fake target, and server-owned local outbox write receipt being received.

## Future Runtime Contract

After this freeze is current-main synced, a future implementation or proof may update or prove `local_outbox_provider_private_handoff` so that:

- if no active replacement package authority exists for the session, existing local-outbox provider-private handoff behavior remains unchanged;
- if active replacement package authority exists, provider-private handoff validates the durable server-owned local outbox write authority that already carries active refs/hashes and source refs/hashes as distinct authority fields;
- provider-private handoff must derive its provider artifact authority from the durable local outbox write artifact ref/hash/size, not from browser-supplied active refs, hashes, package refs, artifact refs, package bytes, replacement bytes, delivery bytes, paths, URLs, or local files;
- the provider-private handoff authority basis must include the relevant local outbox write authority basis hash and must remain response-safe;
- source `L3OutputPackage` ids, refs, hashes, payloads, and `uq_l3_output_package_session_kind` remain unchanged;
- `L3LocalOutboxProviderPrivateHandoffReceipt` remains durable handoff/status authority and may carry active-authority basis fields only if tests prove response redaction and downstream contract safety;
- existing redacted `storage://server-owned-local-outbox/...` response refs remain response-safe and no raw local filesystem path, raw provider token, raw provider object key, or provider-public URL is exposed.

The selected slice may add server-side helper functions only enough to let local-outbox provider-private handoff validate and use already-governed active replacement artifact authority through local outbox write authority. It must not expose raw local filesystem paths, raw provider tokens, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied arbitrary artifact refs, browser-supplied hashes, browser-supplied delivery bytes, browser path authority, or raw local path authority.

## Required Failure Lifecycle

Future implementation must fail closed on:

- stale source package authority;
- local outbox write state that does not match fake-target, connector-local receipt, connector dispatch, or external export/download readiness authority;
- fake-target state that does not match connector-local receipt authority;
- connector-local receipt state that does not match recorded external export/download readiness or connector dispatch authority;
- external export/download readiness state that does not already include the same active authority when active authority is present upstream;
- delivery authority that cannot be revalidated against recorded readiness where required by the upstream receipt chain;
- local outbox artifact hash or size mismatch;
- tampered persisted local outbox artifact or manifest;
- active authority source package ids that do not match the readiness source package ids;
- active authority package kinds that do not match canonical package order;
- active authority source payload hashes that are stale for the source package set;
- active artifact refs or hashes that do not match recorded readiness, delivery, connector dispatch, connector-local receipt, fake-target, or local outbox write authority;
- missing replacement output package ids;
- missing or incomplete active replacement package authority;
- missing activation row;
- missing replacement artifact manifest or namespace authority;
- non-response-safe active artifact refs;
- wrong session, pass, preview, reconciliation, package-review submit, handoff/export prepare, APS handoff, external export/download readiness, connector dispatch, delivery, connector-local receipt, fake target, local outbox write, or package-construction basis;
- caller-supplied active refs, active hashes, replacement ids, destination paths, URLs, credentials, package bytes, replacement bytes, delivery bytes, connector fields, artifact bytes, provider tokens, provider object keys, or local filesystem paths;
- any attempt to use this slice for external local export adoption, rendered activation controls, package rebuild, package payload rewrite, source package mutation, downstream invalidation, provider-public delivery/use, real connector invocation, ConnectorRun creation, or ConnectorRunTarget creation.

## Idempotency And Existing State

The future implementation must preserve existing `local_outbox_provider_private_handoff` idempotency and state behavior:

- same `client_request_id` and same resolved request basis returns the existing handoff receipt status after verifying the existing authority basis;
- same `client_request_id` and different resolved request basis fails closed as `local_outbox_provider_private_handoff_client_request_conflict`;
- same resolved authority basis with a different `client_request_id` continues to return the governed existing-basis conflict/status behavior selected by current main;
- stale or changed active authority after an existing provider-private handoff fails closed unless current-main authority explicitly admits replay/status-only projection;
- active authority must become part of the local-outbox provider-private handoff authority basis when applied;
- source package row mutation, package payload rewrite, package rebuild, external local export, re-delivery runtime, provider-public delivery/use, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, and downstream invalidation remain out of scope.

## Proof Requirements

Future implementation proof must include:

- targeted backend tests where no active replacement authority preserves current `local_outbox_provider_private_handoff` behavior;
- targeted backend tests where active replacement authority is carried from handoff/export prepare through APS handoff dispatch, external export/download prepare, external export/download delivery, connector dispatch record, connector-local receipt, fake target, server-owned local outbox write, and local-outbox provider-private handoff for this reader only;
- proof that provider-private handoff uses only the local outbox artifact/hash/size authorized by recorded active-authority local outbox write state;
- proof that source `L3OutputPackage` rows, source payload refs/hashes, package ids, and `uq_l3_output_package_session_kind` remain unchanged;
- negative tests for wrong readiness record, wrong delivery basis, wrong connector dispatch record, wrong connector-local receipt, wrong fake target, wrong local outbox write, wrong descriptor, wrong APS bundle ref, wrong source package ids, wrong package kinds, stale source payload hash, readiness without matching active authority, missing activation row, missing replacement namespace or manifest authority, incomplete active authority, non-response-safe active refs, caller-supplied active refs/hashes/paths/provider fields, tampered local outbox artifact, tampered local outbox manifest, and forbidden adjacent surfaces;
- response redaction tests proving no raw local filesystem paths, raw provider tokens, raw provider object keys, raw public URLs, or provider-public URLs are exposed;
- proof of no `ConnectorRun` or `ConnectorRunTarget` creation;
- targeted API/OpenAPI tests only if request/response schema changes;
- no headed/headless E2E unless rendered behavior changes.

## Non-Admission Boundary

This freeze admits no runtime. It does not admit rendered activation controls, external local export adoption, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied delivery bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw provider token exposure, raw provider object key exposure, raw local path exposure, or hidden LLM planning.

## Required Validation

This freeze branch must pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

## Next Posture

After this freeze merges, a current-main sync must record the PR, checks, comments, reviews, reviewThreads, merge commit, validation, and next posture.

The next exact posture is `current_main_sync_source_l3_output_package_active_authority_local_outbox_provider_private_handoff_freeze`.

After sync, the next implementation posture is `implement_source_l3_output_package_active_authority_local_outbox_provider_private_handoff_after_freeze_sync`, unless implementation audit proves the slice cannot be implemented without package payload rewrite, raw path exposure, downstream invalidation, external local export adoption, provider-public delivery/use, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, or frontend-durable authority.
