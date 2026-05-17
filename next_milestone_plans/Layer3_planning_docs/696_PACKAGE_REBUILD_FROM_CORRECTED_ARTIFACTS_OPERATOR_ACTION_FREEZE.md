# 696 - Package Rebuild From Corrected Artifacts Operator Action Freeze

## Status

Status: package mutation/reconstruction operator-action selection freeze for `rebuild_package_from_corrected_artifacts`.

Doc: `696_PACKAGE_REBUILD_FROM_CORRECTED_ARTIFACTS_OPERATOR_ACTION_FREEZE.md`.

Predecessor current-main sync doc: `695_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_EXTERNAL_LOCAL_EXPORT_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `9950ec0c4900638fa6be81a73e67b43ac3723c11`.

Current selected surface: `package_mutation_reconstruction`.

Selected package lifecycle action: `rebuild_package_from_corrected_artifacts`.

Selected implementation-entry posture: `audit_rebuild_package_from_corrected_artifacts_implementation_entry_after_operator_action_sync`.

Entry decision: `freeze_only`.

Runtime status in this pass: `not_implemented_in_this_pass`.

## Selection Basis

Current main already proves package supersession preview, server-owned replacement artifact materialization, replacement package-set authority, replacement artifact manifest recording, replacement namespace rows, source L3 output package replacement activation, downstream active-package-authority read adoption, and controlled external local export through `external_local_export`.

Those slices let an operator activate an already-governed replacement namespace and make downstream readers consume it. They do not yet admit a first-class package rebuild action from corrected artifacts. Current source confirms `rebuild_package` is still treated as a forbidden request field in package preview, materialization, manifest, namespace, activation, and downstream handoff/export surfaces.

This freeze selects the next exact package mutation/reconstruction action as `rebuild_package_from_corrected_artifacts`, because it is the missing operator action needed to turn reviewed corrections into a governed replacement package set before source expansion or RAG/vector indexing consumes the outputs.

This freeze deliberately does not select:

- package payload rewrite from browser-supplied bytes;
- direct source `L3OutputPackage` row mutation;
- arbitrary artifact ref/hash/path submission;
- downstream invalidation;
- re-delivery or re-export;
- source expansion;
- RAG/vector behavior;
- provider-public delivery/use;
- connector/destination dispatch.

## Current Authority Inputs For Later Audit

The next implementation-entry audit/freeze may use only current-main authority already proven in the package lifecycle:

- package supersession preview authority from `/api/v1/layer3/package/mutation/preview`;
- server-owned replacement package artifact materialization authority from `/api/v1/layer3/package/replacement-artifact/materialize`;
- replacement package-set authority;
- replacement artifact manifest authority;
- replacement namespace rows;
- package replacement activation authority;
- source `L3OutputPackage` row refs/hashes as read-only source basis;
- server-owned corrected artifact refs/hashes only if the next audit proves they are already produced by a governed review/correction surface.

If current main does not contain a governed corrected-artifact source, the next implementation-entry audit must stop as `no_runtime_now_rebuild_package_from_corrected_artifacts_source_authority_absent`.

## Future Contract Requirements

A later implementation-entry freeze must define, before runtime:

- exact owner route and owner service;
- exact corrected-artifact authority source;
- complete request allowlist;
- canonical rebuild basis hash;
- idempotency contract for same-key replay, same-key conflict, same-basis replay, and conflicting rebuild output;
- stale source package, stale correction, stale manifest, stale namespace, stale activation, and wrong-session failure behavior;
- all-or-nothing artifact generation behavior;
- response redaction for artifact refs, hashes, size, status, and audit history;
- durable receipt/status/audit table requirements if new durable state is needed;
- whether rendered controls are required or deferred.

The future request must not accept package bytes, browser-generated diffs, arbitrary local paths, URLs, destination instructions, connector ids, credentials, provider URLs, source upload payloads, local directories, RAG/vector inputs, hidden LLM prompts, retry/rerun/cancel fields, auth context, or security context as authority.

## Non-Admission Boundary

This freeze admits no runtime implementation. It does not add a backend route, DTO, response model, model, migration, service behavior, executable backend test behavior, rendered UI control, package payload rewrite, source `L3OutputPackage` row mutation, replacement artifact generation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw local path exposure, or hidden LLM planning.

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

No headed/headless E2E run is required for this freeze because it changes planning/control metadata only.

## Next Posture

After this freeze is merged, the next exact posture is `current_main_sync_package_rebuild_from_corrected_artifacts_operator_action_freeze`.

After the freeze is current-main synced, the next exact posture is `audit_rebuild_package_from_corrected_artifacts_implementation_entry_after_operator_action_sync`. That audit may write an implementation-entry freeze only if it can prove a governed corrected-artifact authority source and exact owner files/routes without package payload rewrite, browser-supplied bytes, arbitrary refs/hashes/paths, source expansion, RAG/vector behavior, connector/destination dispatch, provider-public delivery/use, or auth/security broadening.
