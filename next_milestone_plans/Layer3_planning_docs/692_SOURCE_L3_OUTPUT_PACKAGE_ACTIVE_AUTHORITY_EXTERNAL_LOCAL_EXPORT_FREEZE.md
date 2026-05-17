# 692 - Source L3 Output Package Active Authority External Local Export Freeze

## Status

Status: implementation-entry freeze for `source_l3_output_package_active_authority_external_local_export`.

Doc: `692_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_EXTERNAL_LOCAL_EXPORT_FREEZE.md`.

Predecessor sync doc: `691_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before freeze: `96140c0474806f65132517df44d6d7e2788f0c39`.

Selected follow-on surface: `downstream_active_package_authority_read_adoption`.

Selected reader path: `external_local_export`.

Selected route: `POST /api/v1/layer3/handoff/connector/local-outbox/external-local-export/write`.

Selected owner services:

- `backend/app/services/layer3_external_local_export.py`;
- `backend/app/services/layer3_local_outbox_provider_private_handoff.py`;
- `backend/app/services/layer3_server_owned_local_outbox_write.py`;
- `backend/app/services/layer3_server_owned_local_outbox_target.py`;
- `backend/app/services/layer3_connector_local_destination_receipt.py`;
- `backend/app/services/layer3_package_replacement_activation.py`.

Selected validation seam: recorded `local_outbox_provider_private_handoff` where present, `server_owned_local_outbox_write`, `server_owned_local_outbox_target`, `connector_local_destination_receipt`, `connector_dispatch_record`, `external_export_download_prepare`, local outbox artifact and manifest hash/size validation, and server-configured `LAYER3_EXTERNAL_LOCAL_EXPORT_DIR` target authority.

Selected operator action: `adopt_active_replacement_package_authority_for_external_local_export`.

Selected implementation-entry mode: `source_l3_output_package_active_authority_external_local_export`.

No runtime begins in this freeze.

## Decision

The next Layer 3 package-lifecycle follow-on surface is downstream active-package-authority read adoption for exactly one named reader path: `external_local_export`.

Current main now proves active replacement authority through handoff/export prepare, APS handoff dispatch, external export/download prepare, same-origin delivery, connector dispatch, connector-local destination receipt, fake target, server-owned local outbox write, and local-outbox provider-private handoff. The next downstream export boundary is `POST /api/v1/layer3/handoff/connector/local-outbox/external-local-export/write`, which writes finalized outbox artifact and manifest bytes from durable server-owned local outbox authority to one server-configured external local export directory.

This freeze selects external local export because it is the next stale downstream reader after local-outbox provider-private handoff. Rendered activation controls remain useful and may be selected later. Package rebuild, package payload rewrite, package mutation/reconstruction, source expansion, and RAG/vector behavior remain deferred unless current-main authority separately selects them.

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
- recorded `local_outbox_provider_private_handoff` state where present;
- server-configured `LAYER3_EXTERNAL_LOCAL_EXPORT_DIR` target authority;
- source `L3OutputPackage` rows for provenance and stale-authority checks only;
- response-safe active replacement artifact refs and hashes already projected into upstream handoff/export, APS dispatch, external export/download readiness, delivery, connector dispatch, connector-local receipt, fake target, server-owned local outbox write, and provider-private handoff proof.

Future implementation must fail closed if external local export authority cannot be tied back to the exact source package set, active replacement authority, APS handoff dispatch state, external export/download readiness record, delivery validation, connector dispatch record, connector-local receipt, fake target, server-owned local outbox write receipt, provider-private handoff receipt when applicable, and server-configured external local export target being used.

## Future Runtime Contract

After this freeze is current-main synced, a future implementation or proof may update or prove `external_local_export` so that:

- if no active replacement package authority exists for the session, existing external local export behavior remains unchanged;
- if active replacement package authority exists, external local export validates durable local outbox and provider-private authority that already carries active refs/hashes and source refs/hashes as distinct authority fields;
- external local export must derive its written artifact authority from durable server-owned local outbox write artifact and manifest refs, hashes, sizes, and authority basis, not from browser-supplied active refs, hashes, package refs, artifact refs, package bytes, replacement bytes, delivery bytes, destination paths, URLs, credentials, or local files;
- the external local export authority basis must include the relevant local outbox write authority basis hash, provider-private handoff authority basis hash when present, and server-configured target identity while remaining response-safe;
- source `L3OutputPackage` ids, refs, hashes, payloads, and `uq_l3_output_package_session_kind` remain unchanged;
- `L3ExternalLocalExportReceipt` remains durable write/status authority and may carry active-authority basis fields only if tests prove response redaction and downstream contract safety;
- existing redacted `external-local-export://...` response refs remain response-safe and no raw local filesystem path, raw provider token, raw provider object key, provider-public URL, or caller-supplied destination path is exposed.

The selected slice may add server-side helper functions only enough to let external local export validate and use already-governed active replacement artifact authority through local outbox write and provider-private handoff authority. It must not expose raw local filesystem paths, raw provider tokens, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied arbitrary artifact refs, browser-supplied hashes, browser-supplied delivery bytes, browser path authority, destination path editing, or raw local path authority.

## Required Failure Lifecycle

Future implementation must fail closed on:

- stale source package authority;
- local outbox provider-private handoff state that does not match local outbox write authority when provider-private handoff exists;
- local outbox write state that does not match fake-target, connector-local receipt, connector dispatch, or external export/download readiness authority;
- fake-target state that does not match connector-local receipt authority;
- connector-local receipt state that does not match recorded external export/download readiness or connector dispatch authority;
- external export/download readiness state that does not already include the same active authority when active authority is present upstream;
- delivery authority that cannot be revalidated against recorded readiness where required by the upstream receipt chain;
- local outbox artifact or manifest hash or size mismatch;
- tampered persisted local outbox artifact or manifest;
- server-configured external local export directory unavailable, inside app-owned storage, inside local outbox storage, or conflicting with existing output;
- active authority source package ids that do not match the readiness source package ids;
- active authority package kinds that do not match canonical package order;
- active authority source payload hashes that are stale for the source package set;
- active artifact refs or hashes that do not match recorded readiness, delivery, connector dispatch, connector-local receipt, fake-target, local outbox write, provider-private handoff, or external local export authority;
- missing replacement output package ids;
- missing or incomplete active replacement package authority;
- missing activation row;
- missing replacement artifact manifest or namespace authority;
- non-response-safe active artifact refs;
- wrong session, pass, preview, reconciliation, package-review submit, handoff/export prepare, APS handoff, external export/download readiness, connector dispatch, delivery, connector-local receipt, fake target, local outbox write, provider-private handoff, external local export, or package-construction basis;
- caller-supplied active refs, active hashes, replacement ids, destination paths, URLs, credentials, package bytes, replacement bytes, delivery bytes, connector fields, artifact bytes, provider tokens, provider object keys, or local filesystem paths;
- any attempt to use this slice for rendered activation controls, package rebuild, package payload rewrite, source package mutation, downstream invalidation, provider-public delivery/use, real connector invocation, ConnectorRun creation, or ConnectorRunTarget creation.

## Idempotency And Existing State

The future implementation must preserve existing `external_local_export` idempotency and state behavior:

- same `client_request_id` and same resolved request basis returns the existing external local export receipt status after verifying the existing authority basis and output hashes;
- same `client_request_id` and different resolved request basis fails closed as `external_local_export_client_request_conflict`;
- same resolved authority basis with a different `client_request_id` returns the governed existing status without duplicate output;
- duplicate target write returns existing status if identical and fails closed if conflicting;
- stale or changed active authority after an existing external local export fails closed unless current-main authority explicitly admits replay/status-only projection;
- active authority must become part of the external local export authority basis when applied;
- source package row mutation, package payload rewrite, package rebuild, re-delivery runtime, provider-public delivery/use, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, and downstream invalidation remain out of scope.

## Proof Requirements

Future implementation proof must include:

- targeted backend tests where no active replacement authority preserves current `external_local_export` behavior;
- targeted backend tests where active replacement authority is carried from handoff/export prepare through APS handoff dispatch, external export/download prepare, external export/download delivery, connector dispatch record, connector-local receipt, fake target, server-owned local outbox write, local-outbox provider-private handoff, and external local export for this reader only;
- proof that external local export writes only the local outbox artifact and manifest bytes authorized by recorded active-authority local outbox write and provider-private handoff state;
- proof that source `L3OutputPackage` rows, source payload refs/hashes, package ids, and `uq_l3_output_package_session_kind` remain unchanged;
- negative tests for wrong readiness record, wrong delivery basis, wrong connector dispatch record, wrong connector-local receipt, wrong fake target, wrong local outbox write, wrong provider-private handoff, wrong descriptor, wrong APS bundle ref, wrong source package ids, wrong package kinds, stale source payload hash, readiness without matching active authority, missing activation row, missing replacement namespace or manifest authority, incomplete active authority, non-response-safe active refs, caller-supplied active refs/hashes/paths/provider fields, tampered local outbox artifact, tampered local outbox manifest, conflicting external output, and forbidden adjacent surfaces;
- response redaction tests proving no raw local filesystem paths, raw provider tokens, raw provider object keys, raw public URLs, or provider-public URLs are exposed;
- proof of no `ConnectorRun` or `ConnectorRunTarget` creation;
- targeted API/OpenAPI tests only if request/response schema changes;
- no headed/headless E2E unless rendered behavior changes.

## Non-Admission Boundary

This freeze admits no runtime. It does not admit rendered activation controls, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, package mutation/reconstruction, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch beyond the already-selected external local export write, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied delivery bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw provider token exposure, raw provider object key exposure, raw local path exposure, or hidden LLM planning.

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

The next exact posture is `current_main_sync_source_l3_output_package_active_authority_external_local_export_freeze`.

After sync, the next implementation posture is `implement_source_l3_output_package_active_authority_external_local_export_after_freeze_sync`, unless implementation audit proves the slice cannot be implemented without package payload rewrite, raw path exposure, downstream invalidation, provider-public delivery/use, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, connector/destination dispatch beyond the selected external local export write, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, rendered activation controls, browser/operator path editing, caller-supplied arbitrary paths or URLs, or raw local path exposure.
