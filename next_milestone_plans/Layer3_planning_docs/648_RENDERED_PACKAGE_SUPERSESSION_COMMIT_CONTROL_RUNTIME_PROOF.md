# 648 - Rendered Package Supersession Commit Control Runtime Proof

## Status

Status: branch-local implementation proof for `rendered_package_supersession_commit_control`.

This implementation follows current-main sync doc `647_RENDERED_PACKAGE_SUPERSESSION_COMMIT_CONTROL_FREEZE_CURRENT_MAIN_SYNC.md`.

Implementation branch: `codex/l3-rendered-supersession-commit-control`.

Current-main checkpoint before implementation: `9296983bd9d7ae0d775c74cd11db9d13b61470f7`.

Selected surface: `package_mutation_reconstruction`.

Selected exact operator action: `commit_package_supersession_after_replacement_package_set_authority`.

Selected implementation-entry mode: `rendered_package_supersession_commit_control`.

Existing commit surface: `/api/v1/layer3/package/supersession/commit`.

Owner service: `backend/app/services/layer3_package_supersession_commit.py`.

Server runtime mode already live: `package_supersession_commit_entry`.

Source gate: `126_PACKAGE_COMMIT_FREEZE`.

Layer 3 placement: Data Structuring & Processing package lifecycle boundary.

## Implemented Slice

The rendered `/review/layer3` package review area now includes a bounded `Commit Supersession` control and read-only `package-supersession-commit-panel`.

The control performs exactly one server-authoritative call:

1. `POST /api/v1/layer3/package/supersession/commit`.

The browser derives the request only from existing server-governed package supersession preview authority and replacement package-set authority. It uses `stableHash` with Web Crypto SHA-256 over `stableStringify` to compute `downstream_dependency_hash` and `commit_basis_hash` from the same stable JSON basis used by `backend/app/services/layer3_package_supersession_commit.py`.

The implementation files are:

- `backend/app/services/layer3_package_supersession_commit.py`;
- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.css`;
- `backend/app/review_ui/static/layer3.js`;
- `backend/tests/test_layer3_api.py`;
- `backend/tests/test_layer3_page.py`;
- `e2e/layer3-workbench.spec.js`.

The progress/proof owner files for this pass are:

- `next_milestone_plans/Layer3_planning_docs/648_RENDERED_PACKAGE_SUPERSESSION_COMMIT_CONTROL_RUNTIME_PROOF.md`;
- `next_milestone_plans/layer3_progress_board.md`;
- `next_milestone_plans/layer3_progress_manifest.json`;
- `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `tools/l3-progress-check.py`.

Backend service behavior changed only to align `layer3_package_supersession_commit.py` current downstream dependency projection with the existing package supersession preview downstream dependency projection, preserving `schema_id` and `request_ref_field` in the stable hash basis. No backend route, DTO, response model, database model, migration, package row mutation service, package payload write service, source expansion service, connector service, provider-public service, RAG/vector service, auth/security behavior, or frontend-durable authority changed in this pass.

## Request Boundary

The package supersession commit request submits only:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `package_supersession_preview_hash`;
- `source_package_set_hash`;
- `source_output_package_ids`;
- `source_package_kinds`;
- `source_payload_refs`;
- `source_payload_hashes`;
- `replacement_package_set_authority_id`;
- `replacement_package_set_id`;
- `replacement_package_set_hash`;
- `replacement_package_kinds`;
- `replacement_payload_refs`;
- `replacement_payload_hashes`;
- `replacement_authority_basis_hash`;
- `downstream_dependency_hash`;
- `commit_basis_hash`;
- `operator_decision`.

The browser implementation owner is `packageSupersessionCommitPayload`. Browser state is transient request assembly only and is not durable authority.

The rendered status/history projection owner is `renderPackageSupersessionCommitPanel`.

The rendered control does not submit package payload bytes, browser-provided replacement refs or hashes, package row mutation fields, replacement namespace fields, replacement artifact manifest fields, arbitrary destination ids or URLs, connector ids, connector run ids, source expansion fields, RAG/vector fields, auth/security fields, hidden LLM fields, retry/rerun/cancel fields, or frontend-durable state.

## Rendered State

The rendered state uses:

- `PACKAGE_SUPERSESSION_COMMIT_RENDERED_MODE = rendered_package_supersession_commit_control`;
- `PACKAGE_SUPERSESSION_COMMIT_USE_CASE = operator_commits_package_supersession_lineage_after_replacement_package_set_authority`;
- `PACKAGE_SUPERSESSION_COMMIT_RESPONSE_AUTHORITY = State.packageSupersessionCommit`;
- `PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION = commit_package_supersession`.

The panel renders unavailable, ready, recording, committed, already-committed, and failed states from response-safe data.

The display helper `safePackagePayloadRefForDisplay` redacts raw local path-shaped source and replacement payload refs as `redacted_local_payload_ref`.

The panel displays only response-safe status, ids, hashes, package kind rows, disabled capability flags, deferred downstream locks, and redacted failure codes. It does not expose package payload bytes or create durable frontend authority.

## Proof

Static proof:

- `backend/tests/test_layer3_page.py` asserts the rendered button, panel, mode, JavaScript hash/payload builder, endpoint call, operator decision, ready state, panel renderer, and CSS selectors.

API proof:

- `backend/tests/test_layer3_api.py -k "package_supersession_commit"` proves the existing server-authoritative package supersession commit API, idempotency, failure guardrails, disabled side effects, and the downstream dependency hash basis alignment for package review submit authority without backend widening beyond the admitted commit service guardrail.

Rendered E2E proof:

- `e2e/layer3-workbench.spec.js` adds `Layer 3 workbench records rendered package supersession commit control`.
- The test drives source intake, plan approval, execution selection/start, result review, package preview, package construction, package review submit, supersession preview, replacement package-set authority, and package supersession commit.
- It proves the rendered request body contains only admitted fields.
- It proves forbidden fields are absent.
- It proves failure-state projection with `package_supersession_commit_basis_hash_mismatch`.
- It proves the commit record is persisted by `/api/v1/layer3/package/supersession/commit`.
- It proves the rendered panel redacts local path-shaped refs and displays recorded/failure state.
- It proves the rendered control does not trigger handoff/export, replacement artifact manifest, replacement namespace, connector dispatch, source expansion, package payload write, package row mutation, provider-public delivery/use, RAG/vector, or broad downstream runtime requests.

## Non-Admission Boundary

This pass does not admit package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement output package namespace rows, replacement artifact manifest recording, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, connector-run creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, or frontend-durable authority.

No browser/operator path editing, caller-supplied arbitrary path/URL, package payload byte edit, replacement payload byte edit, destination write, connector run, provider-public URL, source row, vector index, credential, or frontend durable authority is created by this rendered control.

## Required Validation

This implementation branch must pass:

```powershell
node --check .\backend\app\review_ui\static\layer3.js
python -m py_compile .\backend\tests\test_layer3_page.py
python -m py_compile .\backend\app\services\layer3_package_supersession_commit.py .\backend\tests\test_layer3_api.py
python -m pytest .\backend\tests\test_layer3_page.py -q
python -m pytest .\backend\tests\test_layer3_api.py -k "package_supersession_commit" -q
npx playwright test e2e/layer3-workbench.spec.js --project=chromium -g "Layer 3 workbench records rendered package supersession commit control"
npx playwright test e2e/layer3-workbench.spec.js --project=chromium --headed -g "Layer 3 workbench records rendered package supersession commit control"
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

## Next Posture

After this implementation merges, a current-main sync must record the PR, checks, comments, reviews, reviewThreads, merge commit, validation, and next posture.

The next exact posture is `await_current_main_sync_for_rendered_package_supersession_commit_control`.

After that current-main sync, the next capability decision must remain inside current-main-selected authority. Any package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement artifact manifest recording, replacement namespace row creation, downstream invalidation, re-delivery runtime, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector, auth/security, full mockup activation, or frontend-durable authority requires a separate named freeze before implementation.
