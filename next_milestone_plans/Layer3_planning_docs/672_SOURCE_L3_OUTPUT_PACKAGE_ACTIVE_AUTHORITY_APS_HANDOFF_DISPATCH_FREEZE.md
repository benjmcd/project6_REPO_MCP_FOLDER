# 672 - Source L3 Output Package Active Authority APS Handoff Dispatch Freeze

## Status

Status: implementation-entry freeze for `source_l3_output_package_active_authority_aps_handoff_dispatch`.

Doc: `672_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_APS_HANDOFF_DISPATCH_FREEZE.md`.

Predecessor sync doc: `671_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_HANDOFF_EXPORT_PREPARE_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before freeze: `75ff03173b185d434335831ed382183d58403946`.

Selected follow-on surface: `downstream_active_package_authority_read_adoption`.

Selected reader path: `aps_handoff_dispatch`.

Selected route: `POST /api/v1/layer3/handoff/aps/dispatch`.

Selected owner services:

- `backend/app/services/layer3_workbench.py`;
- `backend/app/services/layer3_aps_handoff.py`;
- `backend/app/services/layer3_package_replacement_activation.py`.

Selected resolver: `resolve_active_replacement_package_authority`.

Selected operator action: `adopt_active_replacement_package_authority_for_aps_handoff_dispatch`.

Selected implementation-entry mode: `source_l3_output_package_active_authority_aps_handoff_dispatch`.

No runtime begins in this freeze.

## Decision

The next Layer 3 package-lifecycle follow-on surface is downstream active-package-authority read adoption for exactly one named reader path: `aps_handoff_dispatch`.

This is higher utility than jumping directly to external export/download, server-owned local outbox, provider-private handoff, or external local export because those downstream delivery surfaces depend on APS handoff dispatch state and APS bundle authority. Current main already makes `handoff_export_prepare` consume active replacement package authority, but `aps_handoff_dispatch` still validates and materializes from source `L3OutputPackage` rows through `materialize_aps_handoff`.

Rendered activation controls remain useful and may be selected later. They are not selected by this freeze.

## Authority Source

Future implementation must use only current durable authority:

- approved package construction and package-review submit authority already required by `aps_handoff_dispatch`;
- the already-recorded `handoff_export_prepare` state and internal export envelope;
- source `L3OutputPackage` rows for provenance and stale-authority checks;
- durable `L3PackageReplacementActivation` state;
- replacement namespace and replacement artifact manifest authority;
- `resolve_active_replacement_package_authority`;
- response-safe active replacement artifact refs and hashes already projected into handoff/export prepare state.

Future implementation must fail closed if the active authority cannot be tied back to the exact source package set, handoff/export prepare state, and replacement namespace set being dispatched to APS handoff.

## Future Runtime Contract

After this freeze is current-main synced, a future implementation may update `aps_handoff_dispatch` so that:

- if no active replacement package authority exists for the session, the existing source package behavior remains unchanged;
- if active replacement package authority exists, the reader validates activation package kinds, source package ids, source payload hashes, replacement output package ids, active artifact refs, active artifact hashes, activation id, and replacement activation basis hash against the handoff/export prepare state and the source package set;
- APS handoff dispatch may use the active replacement package artifact authority as the package payload authority for this reader only;
- any server-side artifact resolution from `artifact://replacement-package-artifacts/...` refs must resolve through existing replacement namespace or replacement artifact manifest authority, not through browser-supplied refs or raw local paths;
- source `L3OutputPackage` ids, refs, hashes, payloads, and `uq_l3_output_package_session_kind` remain unchanged;
- the APS handoff dispatch authority basis and recorded dispatch state may include explicit active-authority fields such as `active_package_authority_applied`, `package_replacement_activation_id`, `source_output_package_ids`, `source_payload_hashes`, `active_replacement_output_package_ids`, `active_payload_refs`, `active_payload_hashes`, and `replacement_activation_basis_hash`;
- response/output shape may add active-authority fields only if tests prove response redaction and downstream contract safety for `aps_handoff_dispatch` responses and persisted dispatch state.

The selected slice may expand `resolve_active_replacement_package_authority` or add server-side helper functions only enough to let APS handoff dispatch validate and read the already-governed replacement artifacts. It must not expose raw local filesystem paths, browser-supplied package bytes, browser-supplied replacement bytes, or browser-supplied arbitrary artifact refs.

## Required Failure Lifecycle

Future implementation must fail closed on:

- stale source package authority;
- handoff/export prepare state that does not already include the same active authority;
- active authority source package ids that do not match the APS handoff source package ids;
- active authority package kinds that do not match canonical package order;
- active authority source payload hashes that are stale for the source package set;
- active artifact refs or hashes that do not match the prepared handoff/export active authority;
- missing replacement output package ids;
- missing or incomplete active replacement package authority;
- missing activation row;
- missing replacement artifact manifest or namespace authority;
- non-response-safe active artifact refs;
- wrong session, pass, preview, reconciliation, package-review submit, handoff/export prepare, or package-construction basis;
- caller-supplied active refs, active hashes, replacement ids, destination paths, URLs, credentials, package bytes, replacement bytes, or connector fields;
- any attempt to use this slice for external export/download readiness, local outbox write, provider-private handoff, external local export, rendered activation controls, package rebuild, package payload rewrite, source package mutation, or downstream invalidation.

## Idempotency And Existing State

The future implementation must preserve existing `aps_handoff_dispatch` idempotency and state behavior:

- same APS handoff dispatch request and same resolved active authority returns the existing dispatch state;
- stale or changed active authority after an existing dispatch fails closed unless current-main authority explicitly admits a replay/status-only projection;
- active authority must become part of the APS handoff dispatch authority basis when applied;
- source package row mutation, package payload rewrite, package rebuild, re-delivery, and downstream invalidation remain out of scope.

## Proof Requirements

Future implementation proof must include:

- targeted backend tests where no active replacement authority preserves current `aps_handoff_dispatch` behavior;
- targeted backend tests where active replacement authority is applied to APS handoff dispatch for this reader only;
- proof that APS handoff output is derived from active replacement artifact authority when active authority is present;
- proof that source `L3OutputPackage` rows, source payload refs/hashes, package ids, and `uq_l3_output_package_session_kind` remain unchanged;
- negative tests for wrong source package ids, wrong package kinds, stale source payload hash, prepare state without matching active authority, missing activation row, missing replacement namespace or manifest authority, incomplete active authority, non-response-safe active refs, caller-supplied active refs/hashes, and forbidden adjacent surfaces;
- response redaction tests proving no raw local filesystem paths are exposed;
- targeted API/OpenAPI tests only if request/response schema changes;
- no headed/headless E2E unless rendered behavior changes.

## Non-Admission Boundary

This freeze admits no runtime. It does not admit rendered activation controls, external export/download adoption, server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw local path exposure, or hidden LLM planning.

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

The next exact posture is `current_main_sync_source_l3_output_package_active_authority_aps_handoff_dispatch_freeze`.

After sync, the next implementation posture is `implement_source_l3_output_package_active_authority_aps_handoff_dispatch_after_freeze_sync`, unless implementation audit proves the slice cannot be implemented without package payload rewrite, raw path exposure, downstream invalidation, external export/download adoption, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, or frontend-durable authority.
