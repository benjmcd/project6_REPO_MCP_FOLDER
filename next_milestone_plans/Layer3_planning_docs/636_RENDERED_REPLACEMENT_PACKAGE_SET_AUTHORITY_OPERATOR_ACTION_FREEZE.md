# 636 - Rendered Replacement Package-Set Authority Operator Action Freeze

## Status

Status: branch-local planning/control freeze for `rendered_replacement_package_set_authority_control`.

Doc: `636_RENDERED_REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_ACTION_FREEZE.md`.

Predecessor doc: `635_PACKAGE_SUPERSESSION_PREVIEW_RENDERED_CONTROL_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `ef936ae066f8ac6f356b5cacb56635f1d9b80420`.

Selected surface: `package_mutation_reconstruction`.

Selected exact operator action: `record_replacement_package_set_authority_after_supersession_preview`.

Selected implementation-entry mode: `rendered_replacement_package_set_authority_control`.

Existing backend surface: `/api/v1/layer3/package/replacement-set/record`.

Owner service: `backend/app/services/layer3_replacement_package_set_authority.py`.

Server runtime mode: `replacement_package_set_authority`.

Source gate: `127_PACKAGE_REPLACEMENT_SET_FREEZE`.

Operator decision: `record_replacement_package_set_authority`.

Entry decision: `freeze_only`.

Runtime status in this pass: `not_implemented`.

## Why This Action Comes Next

Current main already has the rendered package supersession preview control synced as `current_main_synced_package_supersession_preview_rendered_control`.

The next useful package lifecycle step is not a package supersession commit control yet. The existing `/api/v1/layer3/package/supersession/commit` runtime requires an existing `replacement_package_set_authority_id`, `replacement_package_set_hash`, replacement refs/hashes, and `replacement_authority_basis_hash`. The rendered workbench currently exposes preview state only and does not provide a governed replacement package-set authority action.

This freeze therefore selects the missing prerequisite: a rendered operator action over the already-live replacement package-set authority API. It is an implementation-preparing selection, not runtime implementation.

## Admitted Later Implementation Slice

After this freeze is merged and current-main synced, the exact later implementation slice may add a rendered `/review/layer3` control that:

- derives source package authority only from existing server-authoritative package supersession preview/package state;
- submits only to `/api/v1/layer3/package/replacement-set/record`;
- uses only operator decision `record_replacement_package_set_authority`;
- records a durable `replacement_package_set_authority` response/status/history projection;
- displays response-safe status, ids, hashes, kind lists, disabled capability flags, and redacted failure state;
- keeps browser state transient and non-authoritative.

The rendered control must not accept browser/operator path editing, caller-supplied arbitrary paths, caller-supplied URLs, package payload bytes, package variant content, source row mutation, replacement payload generation, package supersession commit, connector/destination fields, provider-public fields, source expansion, RAG/vector fields, auth/security fields, or frontend-durable state.

If source audit proves current server/browser state cannot assemble a valid replacement package-set authority request without new artifact generation, raw path entry, or arbitrary ref entry, the implementation pass must stop and write `replacement_package_set_authority_request_source_authority_freeze` instead of widening the UI or runtime.

## Required Authority Inputs For Later Implementation

The later implementation must prove how each request field reaches the API without broadening authority:

- `client_request_id`: generated transiently by the rendered submit action.
- `session_id`, `analysis_plan_id`, `pass_run_id`, `reconciliation_record_id`: existing server-backed Layer 3 session/pass/package authority.
- `source_package_set_hash`, `source_output_package_ids`, `source_package_kinds`, `source_payload_refs`, `source_payload_hashes`: existing immutable source package authority, preferably from the `package_supersession_preview_only` response and/or server-backed package state.
- `replacement_package_set_id`, `replacement_package_set_hash`, `replacement_package_kinds`, `replacement_payload_refs`, `replacement_payload_hashes`: existing governed replacement package-set identity only; no browser path editing, arbitrary path entry, or replacement payload generation is admitted by this freeze.
- `authority_basis_hash`: computed from the same server-governed basis expected by `backend/app/services/layer3_replacement_package_set_authority.py`.
- `operator_decision`: exactly `record_replacement_package_set_authority`.

## Non-Admission Boundary

This freeze admits no backend route, DTO, response model, model, migration, service behavior, executable backend test behavior, rendered UI control, package supersession commit control, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement payload generation, replacement package row creation, replacement namespace review, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, connector-run creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-durable authority.

`package_supersession_commit_enabled` remains false for this selected action until a later separate freeze admits a commit control after replacement package-set authority is rendered/proven.

## Proof Plan For Later Implementation

The later implementation must prove:

- static page hooks for the rendered replacement package-set authority control;
- request assembly includes only the allowed fields listed in this freeze;
- request assembly excludes package payload, replacement payload bytes, path/URL entry, package supersession commit, package row mutation, package payload rewrite, replacement payload generation, connector/destination dispatch, provider-public delivery/use, source expansion, RAG/vector behavior, and frontend-durable state;
- API success records only `replacement_package_set_authority` and does not create or mutate `L3OutputPackage`, write package payloads, create replacement package rows, or dispatch connector/provider/destination work;
- idempotency replays return existing authority/status for the same request/basis and fail closed for same request/different basis;
- stale source package set, stale source payload hash, stale replacement package set hash, stale authority basis hash, unsupported operator decision, and forbidden fields fail closed;
- rendered status/history shows response-safe authority status and redacts local path-shaped refs.

## Required Validation

This branch must pass:

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

The next required action after merge is `current_main_sync_rendered_replacement_package_set_authority_operator_action_freeze`.

After current-main sync, the next exact posture is `implement_rendered_replacement_package_set_authority_control_after_freeze_sync`, unless request-authority audit proves replacement package-set request fields cannot be assembled from existing governed server authority without forbidden path/ref/payload generation. In that case the exact stop posture is `replacement_package_set_authority_request_source_authority_freeze`.
