# 646 - Rendered Package Supersession Commit Control Freeze

## Status

Status: branch-local implementation-entry freeze for `rendered_package_supersession_commit_control`.

Doc: `646_RENDERED_PACKAGE_SUPERSESSION_COMMIT_CONTROL_FREEZE.md`.

Predecessor doc: `645_RENDERED_REPLACEMENT_PACKAGE_SET_AUTHORITY_CONTROL_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `3403cf120b4565df637e1c7391afdf3bbde93a79`.

Selected surface: `package_mutation_reconstruction`.

Selected exact operator action: `commit_package_supersession_after_replacement_package_set_authority`.

Selected implementation-entry mode: `rendered_package_supersession_commit_control`.

Existing backend surface: `/api/v1/layer3/package/supersession/commit`.

Owner service: `backend/app/services/layer3_package_supersession_commit.py`.

Server runtime mode: `package_supersession_commit_entry`.

Source gate: `126_PACKAGE_COMMIT_FREEZE`.

Operator decision: `commit_package_supersession`.

Entry decision: `freeze_only`.

Runtime status in this pass: `not_implemented`.

## Why This Action Comes Next

Current main has the rendered package supersession preview control, server-owned replacement package artifact materialization request source, and rendered replacement package-set authority control all synced. The replacement package-set authority rendered control now produces the durable server authority needed by the already-live package supersession commit API.

The next useful package lifecycle step is therefore the rendered commit control over the existing lineage-only `/api/v1/layer3/package/supersession/commit` route. This remains narrower than package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement namespace row creation, replacement artifact manifest recording, downstream invalidation, or re-delivery.

This freeze selects the implementation-entry posture only. It does not implement the rendered control in this pass.

## Admitted Later Implementation Slice

After this freeze is merged and current-main synced, the exact later implementation slice may add a rendered `/review/layer3` control that:

- derives source package authority only from the existing package supersession preview and server-backed package state;
- derives replacement package-set authority only from the current server-owned `replacement_package_set_authority` response/status;
- computes or receives the same `commit_basis_hash` expected by `backend/app/services/layer3_package_supersession_commit.py` from server-governed fields already present in response state;
- submits only to `/api/v1/layer3/package/supersession/commit`;
- uses only operator decision `commit_package_supersession`;
- displays response-safe commit status, ids, hashes, source/replacement package kind rows, disabled capability flags, deferred downstream locks, and redacted failure state;
- keeps browser state transient and non-authoritative.

The rendered control must not accept browser/operator path editing, caller-supplied arbitrary paths, caller-supplied URLs, package payload bytes, edited package content, replacement package payloads, replacement output package row ids, package row mutation, package payload rewrite, rebuild commands, artifact manifest recording, downstream invalidation, re-delivery, connector/destination fields, provider-public fields, source expansion, RAG/vector fields, auth/security fields, or frontend-durable state.

If current server/browser response state cannot assemble a valid package supersession commit request from existing governed authority without backend widening or forbidden browser-provided refs/hashes, the implementation pass must stop and write a missing-authority freeze instead of widening runtime or UI scope.

## Required Authority Inputs For Later Implementation

The later implementation must prove how each request field reaches the API without broadening authority:

- `client_request_id`: generated transiently by the rendered submit action.
- `session_id`, `analysis_plan_id`, `pass_run_id`, `reconciliation_record_id`: existing server-backed Layer 3 session/pass/package authority.
- `package_supersession_preview_hash`, `source_package_set_hash`, `source_output_package_ids`, `source_package_kinds`, `source_payload_refs`, `source_payload_hashes`: existing immutable source package and supersession preview authority.
- `replacement_package_set_authority_id`, `replacement_package_set_id`, `replacement_package_set_hash`, `replacement_package_kinds`, `replacement_payload_refs`, `replacement_payload_hashes`, `replacement_authority_basis_hash`: existing server-owned replacement package-set authority response/state.
- `downstream_dependency_hash`: existing server-known downstream dependency basis expected by the package supersession commit API.
- `commit_basis_hash`: computed from the same server-governed basis expected by `package_supersession_commit_basis_hash`.
- `operator_decision`: exactly `commit_package_supersession`.

## Non-Admission Boundary

This freeze admits no backend route, DTO, response model, model, migration, service behavior, executable backend test behavior, rendered UI control, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement output package namespace rows, replacement artifact manifest recording, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, browser/operator path editing, caller-supplied arbitrary paths or URLs, or frontend-durable authority.

This freeze admits a future rendered control only for immutable lineage recording through the existing `package_supersession_commit_entry` runtime.

## Proof Plan For Later Implementation

The later implementation must prove:

- static page hooks for the rendered package supersession commit control;
- request assembly includes only the allowed fields listed in this freeze;
- request assembly excludes package payload bytes, edited package content, replacement payload bytes, replacement output package ids, path/URL entry, package row mutation, package payload rewrite, rebuild commands, artifact manifest recording, connector/destination dispatch, provider-public delivery/use, source expansion, RAG/vector behavior, and frontend-durable state;
- API success records only `L3PackageSupersessionCommit` lineage and does not mutate `L3OutputPackage`, write package payloads, create replacement output package rows, record replacement artifact manifests, invalidate downstream delivery, re-deliver output, or dispatch connector/provider/destination work;
- idempotency replays return existing commit/status for the same request/basis and fail closed for same request/different basis;
- stale preview hash, stale source package-set hash, stale replacement package-set hash, stale downstream dependency hash, stale commit basis hash, unsupported operator decision, and forbidden fields fail closed;
- rendered status/history shows response-safe commit status and redacts local path-shaped refs.

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

No headed/headless E2E run is required for this freeze-only pass because it changes only planning/control/proof/checker metadata.

## Next Posture

The next required action after merge is `current_main_sync_rendered_package_supersession_commit_control_freeze`.

After current-main sync, the next exact posture is `implement_rendered_package_supersession_commit_control_after_freeze_sync`, unless request-authority audit proves package supersession commit request fields cannot be assembled from existing governed server authority without forbidden path/ref/payload generation. In that case the exact stop posture is `package_supersession_commit_request_authority_freeze`.
