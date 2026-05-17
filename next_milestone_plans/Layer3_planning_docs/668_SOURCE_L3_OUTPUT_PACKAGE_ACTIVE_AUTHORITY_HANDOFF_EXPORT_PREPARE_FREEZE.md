# 668 - Source L3 Output Package Active Authority Handoff Export Prepare Freeze

## Status

Status: implementation-entry freeze for `source_l3_output_package_active_authority_handoff_export_prepare`.

Doc: `668_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_HANDOFF_EXPORT_PREPARE_FREEZE.md`.

Predecessor sync doc: `667_SOURCE_L3_OUTPUT_PACKAGE_REPLACEMENT_ACTIVATION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before freeze: `b526d1d5f181a90ae8693f0d4c00dc70fab0bbb3`.

Selected follow-on surface: `downstream_active_package_authority_read_adoption`.

Selected reader path: `handoff_export_prepare`.

Selected route: `POST /api/v1/layer3/handoff/export/prepare`.

Selected owner services:

- `backend/app/services/layer3_workbench.py`;
- `backend/app/services/layer3_handoff_export_response.py`;
- `backend/app/services/layer3_package_replacement_activation.py`.

Selected resolver: `resolve_active_replacement_package_authority`.

Selected operator action: `adopt_active_replacement_package_authority_for_handoff_export_prepare`.

Selected implementation-entry mode: `source_l3_output_package_active_authority_handoff_export_prepare`.

No runtime begins in this freeze.

## Decision

The next Layer 3 package-lifecycle follow-on surface is downstream active-package-authority read adoption for exactly one named reader path: `handoff_export_prepare`.

This is higher utility than rendered activation controls for the immediate end-to-end objective because the activation runtime is already callable by API, but downstream handoff/export preparation still reads source `L3OutputPackage` payload refs/hashes. The selected slice prepares the first downstream read boundary to consume the already-durable active replacement package authority without mutating source package rows.

Rendered activation controls remain useful and may be selected later. They are not selected by this freeze.

## Authority Source

Future implementation must use only current durable authority:

- approved package construction and package-review submit authority already required by `handoff_export_prepare`;
- source `L3OutputPackage` rows for provenance and stale-authority checks;
- durable `L3PackageReplacementActivation` state;
- `resolve_active_replacement_package_authority`;
- replacement namespace response-safe artifact refs and hashes recorded by the activation runtime.

Future implementation must fail closed if the activation cannot be tied back to the exact source package set being prepared for handoff/export.

## Future Runtime Contract

After this freeze is current-main synced, a future implementation may update `handoff_export_prepare` so that:

- if no active replacement package authority exists for the session, the existing source package behavior remains unchanged;
- if active replacement package authority exists, the reader validates that activation package kinds, source package basis, and package-review/construct authority match the handoff/export preparation basis;
- the prepared internal export envelope may include active replacement package refs/hashes as the prepared payload authority for this reader;
- source `L3OutputPackage` ids, refs, hashes, and `uq_l3_output_package_session_kind` remain unchanged;
- response/output shape may add explicit active-authority fields such as `active_package_authority_applied`, `package_replacement_activation_id`, `active_replacement_output_package_ids`, `active_payload_refs`, and `active_payload_hashes`;
- existing `payload_refs` and `payload_hashes` may reflect the active replacement refs/hashes only for this selected reader if tests prove downstream contract safety for `handoff_export_prepare` responses and persisted prepare state.

The selected slice may expand `resolve_active_replacement_package_authority` only enough to expose response-safe source ids, replacement ids, package kinds, artifact refs, artifact hashes, and `replacement_activation_basis_hash` needed for stale-authority checks. It must not expose raw local filesystem paths.

## Required Failure Lifecycle

Future implementation must fail closed on:

- stale source package authority;
- active authority source package ids that do not match the handoff/export preparation source package ids;
- active authority package kinds that do not match canonical package order;
- missing or incomplete active replacement package authority;
- missing replacement artifact refs/hashes;
- wrong session, pass, preview, reconciliation, package-review submit, or package-construction basis;
- caller-supplied active refs, active hashes, replacement ids, destination paths, URLs, credentials, package bytes, or connector fields;
- any attempt to use active replacement authority for APS dispatch, external export/download readiness, local outbox write, provider-private handoff, external local export, or another downstream reader in this slice.

## Idempotency And Existing State

The future implementation must preserve existing `handoff_export_prepare` idempotency and state behavior:

- same handoff/export prepare request and same resolved active authority returns the existing prepared state;
- stale or changed active authority after an existing prepare fails closed unless current-main authority explicitly admits a replay/status-only projection;
- active authority must become part of the prepare authority basis when applied;
- source package row mutation, package payload rewrite, package rebuild, re-delivery, and downstream invalidation remain out of scope.

## Proof Requirements

Future implementation proof must include:

- targeted backend tests where no active replacement authority preserves current `handoff_export_prepare` behavior;
- targeted backend tests where active replacement authority is applied to the prepared envelope/response for this reader;
- negative tests for wrong source package ids, wrong package kinds, stale source payload hash, missing activation row, incomplete activation authority, caller-supplied active refs/hashes, and forbidden adjacent surfaces;
- response redaction tests proving no raw local filesystem paths are exposed;
- targeted API/OpenAPI tests only if request/response schema changes;
- no headed/headless E2E unless rendered behavior changes.

## Non-Admission Boundary

This freeze admits no runtime. It does not admit rendered activation controls, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, APS handoff dispatch adoption, external export/download adoption, server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw local path exposure, or hidden LLM planning.

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

The next exact posture is `current_main_sync_source_l3_output_package_active_authority_handoff_export_prepare_freeze`.

After sync, the next implementation posture is `implement_source_l3_output_package_active_authority_handoff_export_prepare_after_freeze_sync`, unless implementation audit proves the slice cannot be implemented without package payload rewrite, raw path exposure, downstream invalidation, APS dispatch adoption, external export/download adoption, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, or frontend-durable authority.
