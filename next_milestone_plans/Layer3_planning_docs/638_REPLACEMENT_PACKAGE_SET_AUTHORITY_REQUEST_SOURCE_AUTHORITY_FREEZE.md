# 638 - Replacement Package-Set Authority Request Source Authority Freeze

## Status

Status: branch-local blocker/freeze for `replacement_package_set_authority_request_source_authority_freeze`.

Doc: `638_REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUEST_SOURCE_AUTHORITY_FREEZE.md`.

Predecessor doc: `637_RENDERED_REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_ACTION_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `fda325cc76ad971c521a5a696cb4e3535153de84`.

Selected surface: `package_mutation_reconstruction`.

Attempted implementation-entry mode: `rendered_replacement_package_set_authority_control`.

Audit result: `rendered_replacement_package_set_authority_control_blocked_by_missing_governed_replacement_request_source`.

Required stop posture: `replacement_package_set_authority_request_source_authority_freeze`.

Entry decision: `freeze_only`.

Runtime status in this pass: `not_implemented`.

## Source-Audit Finding

Current main cannot safely implement `rendered_replacement_package_set_authority_control` yet.

The existing backend runtime `backend/app/services/layer3_replacement_package_set_authority.py` requires these replacement-side fields before it can record authority:

- `replacement_package_set_id`;
- `replacement_package_set_hash`;
- `replacement_package_kinds`;
- `replacement_payload_refs`;
- `replacement_payload_hashes`;
- `authority_basis_hash`.

The rendered workbench can assemble the source-side package fields from existing server authority, including source output package ids, kinds, payload refs, payload hashes, and `package_set_hash` from the package supersession preview response. It cannot assemble the replacement-side fields from governed server authority.

## Evidence

- `backend/app/services/layer3_package_mutation_entry.py` returns `package_supersession_preview_only` state with source package rows, source package-set hash, downstream dependencies, and disabled capability flags. It does not return `replacement_package_set_id`, `replacement_package_set_hash`, replacement refs/hashes, or a replacement authority basis hash.
- `backend/app/review_ui/static/layer3.js` exposes `State.packageSupersessionPreview`, `packageSupersessionPreviewPayload`, `packagePayloadRefs`, and `packagePayloadHashes` for source package authority. It has no rendered replacement package-set authority state, no replacement request-source authority, and no `replacement_package_set_authority` request builder.
- `backend/app/services/layer3_replacement_package_set_authority.py` intentionally records supplied replacement set identity and refs/hashes; it does not generate replacement payloads or replacement package rows.
- `backend/tests/test_layer3_api.py` and package lifecycle unit tests fabricate replacement refs/hashes in test helpers. That proves backend contract shape and guardrails, not live rendered server authority for replacement request fields.

## Decision

Do not implement the rendered replacement package-set authority control in this pass.

Do not add browser/operator path editing, caller-supplied arbitrary refs, caller-supplied URLs, replacement payload generation, package payload rewrite, package row mutation, package supersession commit, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, or frontend-durable authority.

The next product/implementation-prep decision must name one governed source for replacement package-set request fields before a rendered submit control can exist.

## Missing Authority To Resolve

One exact governed replacement request-source authority must be selected later. Acceptable future candidates must be separately frozen and may include only one named path, such as:

- server-owned replacement package artifact materialization from a named operator package-rebuild action;
- server-verified replacement artifact manifest authority that exists before replacement package-set authority without circular dependency;
- another explicit server-owned source for replacement refs/hashes that does not require browser path editing or caller-supplied arbitrary refs.

This doc does not select any of those candidates. It only records that current main lacks the authority required to implement the rendered control safely.

## Non-Admission Boundary

This freeze admits no backend route, DTO, response model, model, migration, service behavior, executable backend test behavior, rendered UI control, package supersession commit control, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement payload generation, replacement package row creation, replacement namespace review, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, connector-run creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, frontend-durable authority, browser/operator path editing, or caller-supplied arbitrary paths/URLs.

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

No headed/headless E2E run is required for this freeze-only blocker because no rendered behavior is changed.

## Next Posture

The next required action after merge is `current_main_sync_replacement_package_set_authority_request_source_authority_freeze`.

After current-main sync, the next exact posture is `select_one_governed_replacement_package_set_request_source_authority_after_blocker_sync`.
