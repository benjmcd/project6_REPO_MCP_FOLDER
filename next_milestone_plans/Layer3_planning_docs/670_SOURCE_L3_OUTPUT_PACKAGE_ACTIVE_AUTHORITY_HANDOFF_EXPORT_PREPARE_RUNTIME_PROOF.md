# 670 - Source L3 Output Package Active Authority Handoff Export Prepare Runtime Proof

## Status

Status: branch-local implementation proof for `source_l3_output_package_active_authority_handoff_export_prepare_runtime`.

This implementation follows current-main sync doc `669_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_HANDOFF_EXPORT_PREPARE_FREEZE_CURRENT_MAIN_SYNC.md`.

Implementation branch: `codex/l3-active-authority-handoff-impl`.

Current-main checkpoint before implementation: `c6c3b51606e1afe8122cbd770e582ec8c2296c7e`.

Selected follow-on surface: `downstream_active_package_authority_read_adoption`.

Selected reader path: `handoff_export_prepare`.

Selected route: `POST /api/v1/layer3/handoff/export/prepare`.

Selected operator action: `adopt_active_replacement_package_authority_for_handoff_export_prepare`.

Selected implementation-entry mode: `source_l3_output_package_active_authority_handoff_export_prepare`.

Layer 3 placement: Data Structuring & Processing package lifecycle handoff/export authority boundary.

## Implemented Slice

The backend/API now implements the exact freeze-admitted downstream read-adoption slice for one reader path: `handoff_export_prepare`.

If no active replacement package authority exists for the session, the existing handoff/export prepare behavior is preserved. If active authority exists, the reader validates the active package kinds, source package ids, and source payload hashes against the package set being prepared, then uses the active replacement artifact refs/hashes for the prepared internal export envelope and response.

The implementation files are:

- `backend/app/services/layer3_package_replacement_activation.py`;
- `backend/app/services/layer3_handoff_contract.py`;
- `backend/app/services/layer3_handoff_export_response.py`;
- `backend/app/services/layer3_workbench.py`;
- `backend/app/api/layer3.py`;
- `backend/tests/test_layer3_api.py`.

The progress/proof owner files for this pass are:

- `next_milestone_plans/Layer3_planning_docs/670_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_HANDOFF_EXPORT_PREPARE_RUNTIME_PROOF.md`;
- `next_milestone_plans/layer3_progress_board.md`;
- `next_milestone_plans/layer3_progress_manifest.json`;
- `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `tools/l3-progress-check.py`.

## Runtime Behavior

The implementation extends `resolve_active_replacement_package_authority` only enough to expose source package ids, source payload hashes, replacement output package ids, response-safe active artifact refs/hashes, package kinds, and `replacement_activation_basis_hash`.

When active authority is present and valid, `handoff_export_prepare` records:

- `active_package_authority_applied`;
- `package_replacement_activation_id`;
- `source_output_package_ids`;
- `source_payload_hashes`;
- `active_replacement_output_package_ids`;
- `active_payload_refs`;
- `active_payload_hashes`;
- `replacement_activation_basis_hash`.

The prepared `payload_refs` and `payload_hashes` use the active replacement artifact refs/hashes for this reader only. Source `L3OutputPackage` rows, source payload refs/hashes, package ids, and `uq_l3_output_package_session_kind` remain unchanged.

## Failure Lifecycle

The implementation fails closed on:

- active authority package kinds that do not match the handoff/export package order;
- active authority source package ids that do not match the handoff/export package set;
- active authority source payload hashes that are stale for the handoff/export package set;
- missing replacement output package ids;
- missing active payload refs or hashes;
- active payload refs that are not response-safe `artifact://replacement-package-artifacts/...` refs;
- missing activation id or replacement activation basis hash;
- caller-supplied active authority fields on the handoff/export prepare request.

Existing handoff/export prepare checks for wrong session, pass, preview, reconciliation, package-review submit, package-construction basis, stale package-review authority, forbidden connector fields, package bytes, destination paths, URLs, credentials, and adjacent surfaces remain in force.

## Proof

Backend/API proof in `backend/tests/test_layer3_api.py` covers:

- unchanged no-active-authority `handoff_export_prepare` behavior and idempotency;
- a full API chain from package-review submit through replacement materialization, replacement-set authority, supersession commit, redacted manifest, namespace rows, replacement activation, and handoff/export prepare;
- active replacement refs/hashes applied to the prepare response, persisted prepare state, and internal export envelope;
- source output package rows unchanged after active-authority handoff/export prepare;
- no `ConnectorRun` or `ConnectorRunTarget` creation;
- no raw local filesystem paths in active payload refs;
- same-key replay returning `already_prepared`;
- fail-closed guardrails for wrong package kinds, wrong source package ids, stale source payload hashes, incomplete/non-redacted active authority, and caller-supplied active authority fields.

OpenAPI proof covers the added optional response fields and forbidden request fields for active authority projection.

No headed/headless E2E is required for this pass because rendered behavior does not change.

## Non-Admission Boundary

This pass does not admit rendered activation controls, APS handoff dispatch adoption, external export/download adoption, server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw local path exposure, or hidden LLM planning.

## Required Validation

This implementation branch must pass:

```powershell
python -m py_compile .\backend\app\services\layer3_package_replacement_activation.py .\backend\app\services\layer3_handoff_contract.py .\backend\app\services\layer3_handoff_export_response.py .\backend\app\services\layer3_workbench.py .\backend\app\api\layer3.py .\backend\tests\test_layer3_api.py
python -m pytest .\backend\tests\test_layer3_package_replacement_activation.py -q
python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_handoff_openapi_contracts .\backend\tests\test_layer3_api.py::test_layer3_api_handoff_export_prepare_records_reference_envelope_without_side_effects .\backend\tests\test_layer3_api.py::test_layer3_api_handoff_export_prepare_applies_active_replacement_authority .\backend\tests\test_layer3_api.py::test_layer3_api_handoff_export_prepare_active_authority_guardrails_fail_closed -q
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

## Next Posture

After this implementation merges, a current-main sync must record the PR, checks, comments, reviews, reviewThreads, merge commit, validation, and next posture.

The next exact posture is `await_current_main_sync_for_source_l3_output_package_active_authority_handoff_export_prepare_runtime`.

After sync, the next package-lifecycle decision should choose whether to freeze the next downstream active-package-authority reader adoption, rendered activation controls, or a separately named package rebuild/payload rewrite action. Package payload rewrite, source `L3OutputPackage` mutation, downstream invalidation, re-delivery, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, and caller-supplied arbitrary paths or URLs remain blocked until separately selected and frozen.
