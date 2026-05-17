# 676 - Source L3 Output Package Active Authority External Export Download Delivery Freeze

## Status

Status: implementation-entry freeze for `source_l3_output_package_active_authority_external_export_download_delivery`.

Doc: `676_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md`.

Predecessor sync doc: `675_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_APS_HANDOFF_DISPATCH_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before freeze: `7b7e813cc51a74bb95fc959a743aff8dce4e35ab`.

Selected follow-on surface: `downstream_active_package_authority_read_adoption`.

Selected reader path: `external_export_download_deliver`.

Selected route: `POST /api/v1/layer3/handoff/export/download/deliver`.

Selected owner services:

- `backend/app/services/layer3_workbench.py`;
- `backend/app/services/layer3_external_export_response.py`;
- `backend/app/services/layer3_package_replacement_activation.py`.

Selected validation seam: `external_export_download_prepare` through `_external_export_download_prepare_payload_for_delivery`.

Selected operator action: `adopt_active_replacement_package_authority_for_external_export_download_delivery`.

Selected implementation-entry mode: `source_l3_output_package_active_authority_external_export_download_delivery`.

No runtime begins in this freeze.

## Decision

The next Layer 3 package-lifecycle follow-on surface is downstream active-package-authority read adoption for exactly one named reader path: `external_export_download_deliver`.

This is the first delivery reader after current main's active-authority APS handoff dispatch runtime. Current main proves active replacement authority through `handoff_export_prepare`, `aps_handoff_dispatch`, and compatibility with `external_export_download_prepare`, but it does not yet separately freeze or prove same-origin external export/download delivery over an active-authority readiness record.

Rendered activation controls remain useful and may be selected later. Package rebuild or payload rewrite remains deferred unless activation by indirection is proven insufficient. They are not selected by this freeze.

## Authority Source

Future implementation or proof must use only current durable authority:

- approved package construction and package-review submit authority;
- recorded `handoff_export_prepare` state and internal export envelope;
- recorded `aps_handoff_dispatch` state and APS bundle descriptor;
- recorded `external_export_download_prepare` readiness state;
- source `L3OutputPackage` rows for provenance and stale-authority checks only;
- durable `L3PackageReplacementActivation` state;
- replacement namespace and replacement artifact manifest authority;
- response-safe active replacement artifact refs and hashes already projected into upstream handoff/export, APS dispatch, and external export/download readiness state.

Future implementation must fail closed if delivery authority cannot be tied back to the exact source package set, active replacement authority, APS handoff dispatch state, and external export/download readiness record being delivered.

## Future Runtime Contract

After this freeze is current-main synced, a future implementation may update or prove `external_export_download_deliver` so that:

- if no active replacement package authority exists for the session, the existing delivery behavior remains unchanged;
- if active replacement package authority exists, delivery validates against the recorded `external_export_download_prepare` readiness that carries active refs/hashes and source refs/hashes as distinct authority fields;
- delivery revalidation must continue through `external_export_download_prepare` via `_external_export_download_prepare_payload_for_delivery` or an equivalently governed server-side helper;
- the delivered APS bundle artifact must be the artifact authorized by recorded readiness and APS descriptor state, not a browser-supplied path, URL, artifact ref, package ref, or package byte payload;
- source `L3OutputPackage` ids, refs, hashes, payloads, and `uq_l3_output_package_session_kind` remain unchanged;
- response/output shape may add active-authority fields only if tests prove response redaction and downstream contract safety for delivery responses and persisted delivery state.

The selected slice may add server-side helper functions only enough to let external export/download delivery validate and use already-governed active replacement artifact authority. It must not expose raw local filesystem paths, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied arbitrary artifact refs, or browser-supplied delivery bytes.

## Required Failure Lifecycle

Future implementation must fail closed on:

- stale source package authority;
- external export/download readiness state that does not already include the same active authority when active authority is present upstream;
- APS handoff dispatch state that does not match recorded readiness;
- active authority source package ids that do not match the readiness source package ids;
- active authority package kinds that do not match canonical package order;
- active authority source payload hashes that are stale for the source package set;
- active artifact refs or hashes that do not match recorded readiness;
- missing replacement output package ids;
- missing or incomplete active replacement package authority;
- missing activation row;
- missing replacement artifact manifest or namespace authority;
- non-response-safe active artifact refs;
- wrong session, pass, preview, reconciliation, package-review submit, handoff/export prepare, APS handoff, external export/download readiness, or package-construction basis;
- caller-supplied active refs, active hashes, replacement ids, destination paths, URLs, credentials, package bytes, replacement bytes, delivery bytes, connector fields, or local filesystem paths;
- any attempt to use this slice for connector-local receipt adoption, server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, rendered activation controls, package rebuild, package payload rewrite, source package mutation, or downstream invalidation.

## Idempotency And Existing State

The future implementation must preserve existing `external_export_download_deliver` idempotency and state behavior:

- same delivery request and same resolved active authority returns the existing delivery state;
- stale or changed active authority after an existing delivery fails closed unless current-main authority explicitly admits a replay/status-only projection;
- active authority must become part of the delivery authority basis when applied;
- source package row mutation, package payload rewrite, package rebuild, connector receipt creation, local outbox write, provider-private handoff, external local export, re-delivery runtime, and downstream invalidation remain out of scope.

## Proof Requirements

Future implementation proof must include:

- targeted backend tests where no active replacement authority preserves current `external_export_download_deliver` behavior;
- targeted backend tests where active replacement authority is carried from handoff/export prepare through APS handoff dispatch and external export/download prepare into delivery validation for this reader only;
- proof that delivery serves only the APS bundle artifact authorized by the active-authority readiness descriptor;
- proof that source `L3OutputPackage` rows, source payload refs/hashes, package ids, and `uq_l3_output_package_session_kind` remain unchanged;
- negative tests for wrong readiness record, wrong descriptor, wrong APS bundle ref, wrong source package ids, wrong package kinds, stale source payload hash, readiness without matching active authority, missing activation row, missing replacement namespace or manifest authority, incomplete active authority, non-response-safe active refs, caller-supplied active refs/hashes, and forbidden adjacent surfaces;
- response redaction tests proving no raw local filesystem paths are exposed;
- proof of no `ConnectorRun` or `ConnectorRunTarget` creation;
- targeted API/OpenAPI tests only if request/response schema changes;
- no headed/headless E2E unless rendered behavior changes.

## Non-Admission Boundary

This freeze admits no runtime. It does not admit rendered activation controls, connector-local receipt adoption, server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied delivery bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw local path exposure, or hidden LLM planning.

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

The next exact posture is `current_main_sync_source_l3_output_package_active_authority_external_export_download_delivery_freeze`.

After sync, the next implementation posture is `implement_source_l3_output_package_active_authority_external_export_download_delivery_after_freeze_sync`, unless implementation audit proves the slice cannot be implemented without package payload rewrite, raw path exposure, downstream invalidation, connector-local receipt adoption, local outbox adoption, provider-private handoff adoption, external local export adoption, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, or frontend-durable authority.
