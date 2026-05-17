# 680 - Source L3 Output Package Active Authority Connector Local Receipt Freeze

## Status

Status: implementation-entry freeze for `source_l3_output_package_active_authority_connector_local_receipt`.

Doc: `680_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_CONNECTOR_LOCAL_RECEIPT_FREEZE.md`.

Predecessor sync doc: `679_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before freeze: `2eadecbf74c6bf24bcb6e1ab53301f9c0a76e49c`.

Selected follow-on surface: `downstream_active_package_authority_read_adoption`.

Selected reader path: `connector_local_destination_receipt`.

Selected route: `POST /api/v1/layer3/handoff/connector/local-destination/receipt`.

Selected owner services:

- `backend/app/services/layer3_connector_local_destination_receipt.py`;
- `backend/app/services/layer3_connector_dispatch_entry.py`;
- `backend/app/services/layer3_workbench.py`;
- `backend/app/services/layer3_package_replacement_activation.py`.

Selected validation seam: `external_export_download_delivery` authority revalidation through `external_export_download_prepare` and `_external_export_download_prepare_payload_for_delivery`.

Selected operator action: `adopt_active_replacement_package_authority_for_connector_local_receipt`.

Selected implementation-entry mode: `source_l3_output_package_active_authority_connector_local_receipt`.

No runtime begins in this freeze.

## Decision

The next Layer 3 package-lifecycle follow-on surface is downstream active-package-authority read adoption for exactly one named reader path: `connector_local_destination_receipt`.

Current main now proves active replacement authority through handoff/export prepare, APS handoff dispatch, external export/download prepare, and external export/download delivery. The next downstream receipt creation path is `POST /api/v1/layer3/handoff/connector/local-destination/receipt`, which records the internal fake/local destination receipt after validating connector dispatch and external export/download delivery authority.

This freeze selects that reader because it is the next durable receipt boundary after delivery and before server-owned local outbox target/write, provider-private handoff, and external local export adoption. Rendered activation controls remain useful and may be selected later. Package rebuild or payload rewrite remains deferred unless activation by indirection is proven insufficient. They are not selected by this freeze.

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
- source `L3OutputPackage` rows for provenance and stale-authority checks only;
- response-safe active replacement artifact refs and hashes already projected into upstream handoff/export, APS dispatch, external export/download readiness, and delivery proof.

Future implementation must fail closed if connector-local receipt authority cannot be tied back to the exact source package set, active replacement authority, APS handoff dispatch state, external export/download readiness record, delivery validation, and connector dispatch record being received.

## Future Runtime Contract

After this freeze is current-main synced, a future implementation or proof may update or prove `connector_local_destination_receipt` so that:

- if no active replacement package authority exists for the session, the existing connector-local receipt behavior remains unchanged;
- if active replacement package authority exists, connector-local receipt validates against recorded delivery/readiness/connector dispatch authority that carries active refs/hashes and source refs/hashes as distinct authority fields;
- connector-local receipt revalidation must continue through the existing server-side delivery/readiness validation seam and must not trust browser-supplied active refs, hashes, package refs, artifact refs, package bytes, replacement bytes, delivery bytes, paths, or URLs;
- the accepted artifact hash and size must be derived from the recorded active-authority delivery/readiness basis when active authority exists;
- source `L3OutputPackage` ids, refs, hashes, payloads, and `uq_l3_output_package_session_kind` remain unchanged;
- `L3ConnectorLocalDestinationReceipt` rows remain durable receipt/status authority and may carry active-authority basis fields only if tests prove response redaction and downstream contract safety.

The selected slice may add server-side helper functions only enough to let connector-local receipt validate and use already-governed active replacement artifact authority. It must not expose raw local filesystem paths, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied arbitrary artifact refs, browser-supplied hashes, browser-supplied delivery bytes, or raw local path authority.

## Required Failure Lifecycle

Future implementation must fail closed on:

- stale source package authority;
- connector dispatch state that does not match recorded external export/download readiness;
- external export/download readiness state that does not already include the same active authority when active authority is present upstream;
- delivery authority that cannot be revalidated against recorded readiness;
- active authority source package ids that do not match the readiness source package ids;
- active authority package kinds that do not match canonical package order;
- active authority source payload hashes that are stale for the source package set;
- active artifact refs or hashes that do not match recorded readiness or delivery authority;
- missing replacement output package ids;
- missing or incomplete active replacement package authority;
- missing activation row;
- missing replacement artifact manifest or namespace authority;
- non-response-safe active artifact refs;
- wrong session, pass, preview, reconciliation, package-review submit, handoff/export prepare, APS handoff, external export/download readiness, connector dispatch, delivery, or package-construction basis;
- caller-supplied active refs, active hashes, replacement ids, destination paths, URLs, credentials, package bytes, replacement bytes, delivery bytes, connector fields, or local filesystem paths;
- any attempt to use this slice for server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, rendered activation controls, package rebuild, package payload rewrite, source package mutation, downstream invalidation, real connector invocation, ConnectorRun creation, or ConnectorRunTarget creation.

## Idempotency And Existing State

The future implementation must preserve existing `connector_local_destination_receipt` idempotency and state behavior:

- same `client_request_id` and same resolved authority basis returns the existing receipt status;
- same `client_request_id` and different resolved authority basis fails closed as `connector_local_destination_receipt_client_request_conflict`;
- same resolved authority basis with a different `client_request_id` continues to return the governed existing-basis conflict/status behavior selected by current main;
- stale or changed active authority after an existing receipt fails closed unless current-main authority explicitly admits replay/status-only projection;
- active authority must become part of the connector-local receipt authority basis when applied;
- source package row mutation, package payload rewrite, package rebuild, server-owned local outbox write, provider-private handoff, external local export, re-delivery runtime, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, and downstream invalidation remain out of scope.

## Proof Requirements

Future implementation proof must include:

- targeted backend tests where no active replacement authority preserves current `connector_local_destination_receipt` behavior;
- targeted backend tests where active replacement authority is carried from handoff/export prepare through APS handoff dispatch, external export/download prepare, external export/download delivery, connector dispatch record, and connector-local receipt for this reader only;
- proof that the receipt accepts only the APS bundle artifact/hash/size authorized by recorded active-authority readiness/delivery and connector dispatch state;
- proof that source `L3OutputPackage` rows, source payload refs/hashes, package ids, and `uq_l3_output_package_session_kind` remain unchanged;
- negative tests for wrong readiness record, wrong delivery basis, wrong connector dispatch record, wrong descriptor, wrong APS bundle ref, wrong source package ids, wrong package kinds, stale source payload hash, readiness without matching active authority, missing activation row, missing replacement namespace or manifest authority, incomplete active authority, non-response-safe active refs, caller-supplied active refs/hashes, and forbidden adjacent surfaces;
- response redaction tests proving no raw local filesystem paths are exposed;
- proof of no `ConnectorRun` or `ConnectorRunTarget` creation;
- targeted API/OpenAPI tests only if request/response schema changes;
- no headed/headless E2E unless rendered behavior changes.

## Non-Admission Boundary

This freeze admits no runtime. It does not admit rendered activation controls, server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied delivery bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw local path exposure, or hidden LLM planning.

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

The next exact posture is `current_main_sync_source_l3_output_package_active_authority_connector_local_receipt_freeze`.

After sync, the next implementation posture is `implement_source_l3_output_package_active_authority_connector_local_receipt_after_freeze_sync`, unless implementation audit proves the slice cannot be implemented without package payload rewrite, raw path exposure, downstream invalidation, server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, provider-public delivery/use, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, or frontend-durable authority.
