# 666 - Source L3 Output Package Replacement Activation Runtime Proof

## Status

Status: branch-local implementation proof for `source_l3_output_package_replacement_activation_runtime`.

This implementation follows current-main sync doc `665_SOURCE_L3_OUTPUT_PACKAGE_REPLACEMENT_ACTIVATION_FREEZE_CURRENT_MAIN_SYNC.md`.

Implementation branch: `codex/l3-package-activation-runtime`.

Current-main checkpoint before implementation: `a06a1a71f9612b5785ec3021461c23a2d3bbfc9e`.

Selected surface: `package_mutation_reconstruction`.

Selected operator action: `activate_replacement_output_package_namespace`.

Selected implementation-entry mode: `source_l3_output_package_replacement_activation`.

New backend route: `POST /api/v1/layer3/package/replacement-activation/commit`.

Owner service: `backend/app/services/layer3_package_replacement_activation.py`.

Durable state model: `L3PackageReplacementActivation`.

Durable state table: `l3_package_replacement_activation`.

Migration: `backend/alembic/versions/0032_layer3_package_replacement_activation.py`.

Layer 3 placement: Data Structuring & Processing package lifecycle authority boundary.

## Implemented Slice

The backend/API now implements the exact freeze-admitted activation slice: one durable activation receipt/state row selects one complete already-recorded replacement namespace set as the active package authority for a session.

The activation binds these existing authority records:

- `L3ReplacementOutputPackage`;
- `L3ReplacementPackageArtifactManifest`;
- `L3ReplacementPackageSetAuthority`;
- `L3PackageSupersessionCommit`;
- source `L3OutputPackage`.

The implementation files are:

- `backend/app/models/models.py`;
- `backend/alembic/versions/0032_layer3_package_replacement_activation.py`;
- `backend/app/services/layer3_package_replacement_activation.py`;
- `backend/app/api/layer3.py`;
- `backend/app/services/layer3_state_action_contract.py`;
- `backend/app/services/layer3_state_model_contract.py`;
- `backend/app/services/layer3_workbench.py`;
- `backend/tests/test_layer3_package_replacement_activation.py`;
- `backend/tests/test_layer3_api.py`.

The progress/proof owner files for this pass are:

- `next_milestone_plans/Layer3_planning_docs/666_SOURCE_L3_OUTPUT_PACKAGE_REPLACEMENT_ACTIVATION_RUNTIME_PROOF.md`;
- `next_milestone_plans/layer3_progress_board.md`;
- `next_milestone_plans/layer3_progress_manifest.json`;
- `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `tools/l3-progress-check.py`.

## Storage Boundary

The implementation uses a dedicated activation table rather than mutating `L3OutputPackage.payload_ref`, `L3OutputPackage.payload_hash`, or the unique `(session_id, package_kind)` package rows.

This preserves:

- `uq_l3_output_package_session_kind`;
- existing source package payload refs and hashes;
- existing replacement namespace rows;
- response-safe replacement artifact refs;
- no raw local path exposure in the new activation response.

The new resolver `resolve_active_replacement_package_authority` returns the durable activation authority for later downstream adoption under a separate freeze. This pass does not rebind existing handoff/export readers to the activation table and does not claim downstream invalidation or re-delivery.

## Request Boundary

The route accepts only:

- `client_request_id`;
- `session_id`;
- `replacement_artifact_manifest_id`;
- `replacement_package_set_authority_id`;
- `package_supersession_commit_id`;
- `replacement_output_package_ids`;
- `source_output_package_ids`;
- `package_kinds`;
- `replacement_activation_basis_hash`;
- `operator_decision`.

The operator decision must be `activate_replacement_output_package_namespace`.

`client_request_id` is the idempotency key and remains outside canonical `replacement_activation_basis_hash`.

The activation basis is computed by `package_replacement_activation_basis_hash` over source package ids/kinds/hashes, replacement namespace ids/basis hashes/response-safe artifact refs/hashes, manifest authority, replacement package-set authority, supersession commit authority, package kinds, and operator decision.

## Runtime Behavior

The activation service:

- validates the complete canonical package-kind set;
- validates source package ids and payload hashes against durable replacement authority;
- validates replacement namespace rows against manifest, package-set authority, supersession commit, source package id, package kind, package schema, response-safe artifact ref, and verified artifact hash;
- validates the supplied `replacement_activation_basis_hash`;
- records one `L3PackageReplacementActivation` receipt/state row;
- returns existing status for same-basis replay with a new `client_request_id`;
- fails closed on same-key different-basis conflicts, stale authority, incomplete namespace sets, wrong package vectors, missing rows, wrong session/lineage, tampered artifact hash, and conflicting active session state;
- rolls back partial writes on integrity conflict;
- returns no raw local filesystem paths.

## Proof

Backend/runtime proof:

- `backend/tests/test_layer3_package_replacement_activation.py` proves migration constraints, successful activation without source package row mutation or package payload write, durable receipt persistence, resolver projection, same-key/same-basis replay, same-basis/new-key existing-status replay, stale authority rejection, forbidden-field rejection, wrong operator rejection, wrong package-kind vector rejection, bad basis rejection, wrong source vector rejection, and incomplete namespace rejection.
- `backend/tests/test_layer3_api.py` proves the OpenAPI request/response contract and workbench error envelope for `POST /api/v1/layer3/package/replacement-activation/commit`.

Response and side-effect proof:

- response active artifact refs are `artifact://replacement-package-artifacts/...`;
- `activation_snapshot` omits raw local paths;
- `source_l3_output_package_mutated` is false;
- `package_row_mutation_enabled` is false;
- `package_payload_write_enabled` is false;
- `package_payload_rewrite_enabled` is false;
- `downstream_handoff_rebinding_enabled` is false;
- connector dispatch, provider-public URL, source widening, qualitative hybrid/RAG execution, and frontend-only durable state remain false.

## Non-Admission Boundary

This pass does not admit package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, downstream handoff/export re-binding, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied arbitrary artifact refs/hashes, raw local path exposure, or hidden LLM planning.

## Required Validation

This implementation branch must pass:

```powershell
python -m py_compile .\backend\app\models\models.py .\backend\app\services\layer3_package_replacement_activation.py .\backend\app\services\layer3_state_action_contract.py .\backend\app\services\layer3_state_model_contract.py .\backend\app\services\layer3_workbench.py .\backend\app\api\layer3.py .\backend\alembic\versions\0032_layer3_package_replacement_activation.py
python -m py_compile .\backend\tests\test_layer3_package_replacement_activation.py .\backend\tests\test_layer3_api.py
python -m pytest .\backend\tests\test_layer3_package_replacement_activation.py -q
python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_package_openapi_contracts .\backend\tests\test_layer3_api.py::test_layer3_json_workbench_error_openapi_contracts .\backend\tests\test_layer3_api.py::test_layer3_package_replacement_activation_api_boundary_returns_workbench_error_envelope -q
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

No headed/headless E2E is required for this pass because no rendered activation control is implemented and no rendered behavior changes.

## Next Posture

After this implementation merges, a current-main sync must record the PR, checks, comments, reviews, reviewThreads, merge commit, validation, and next posture.

The next exact posture is `await_current_main_sync_for_source_l3_output_package_replacement_activation_runtime`.

After sync, the next package-lifecycle decision should choose whether to freeze rendered activation controls or a downstream active-package-authority read adoption slice. Package rebuild, package payload rewrite, downstream invalidation, re-delivery, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, and caller-supplied arbitrary paths or URLs remain blocked until separately selected and frozen.
