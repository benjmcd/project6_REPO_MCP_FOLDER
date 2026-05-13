# 296 Source Intake Gate B Rendered Admission Controls

## Status

Status: current-main implementation with targeted validation passed for `source_intake_gate_b_rendered_admission_controls`.

Implementation branch: `codex/l3-source-intake-gate-b-rendered-controls`.

Implementation commit: `f079d0ffc3d760bc24a948141745d5852ccd061c`.

Merged PR: `#879`.

Merge commit/current-main authority: `204d551a88b136882d1ee27a2c31d02798e2547c`.

Merged at: `2026-05-13T05:43:29Z`.

Runtime predecessor: `source_intake_gate_b_material_admission_runtime`.

Freeze predecessor: `295_SOURCE_INTAKE_GATE_B_RENDERED_ADMISSION_CONTROLS_FREEZE.md`.

Canonical source of truth: `L3SourceIntakeRecord`.

Rendered route: `/review/layer3`.

Gate B route: `POST /api/v1/layer3/gate-b/decision`.

Source-intake preview route: `GET /api/v1/layer3/source/intake/{source_intake_record_id}/preview`.

## Implemented Boundary

The rendered source-intake panel now supports the exact operator path frozen in doc 295:

- upload a single source through the existing source-intake upload API
- refresh the existing durable source-intake inventory API
- request the existing bounded source-intake preview API
- commit exactly the server-previewed `mat-source_intake_record-` material candidate through the existing Gate B decision API

The implementation does not add a backend route, DTO, model, migration, owner service, package path, connector path, provider URL path, execution path, RAG/vector path, auth/security path, local-directory path, or frontend-only durable authority.

## Authority Rules

The rendered control treats these preview fields as server authority:

- `material_candidate`
- `material_preview_id`
- `material_preview_hash`
- `material_candidate.source_ref`
- `material_candidate.query_basis`
- `material_candidate.provenance_ref`
- `material_candidate.source_identity`
- `material_candidate.source_provenance`
- `material_candidate.payload`
- `material_candidate.load_summary`

Browser state is transient only:

- current preview payload
- one in-flight Gate B submit guard
- reusable client request id for retry after a blocked or interrupted submit
- committed preview id for duplicate-click suppression after success

No `preflight_id` or `source_set_id` is fabricated for source-intake Gate B admission.

## Rendered Behavior

After a successful source-intake preview, the panel renders a Gate B admission card showing the candidate id, preview id, and preview hash. The `Commit Preview To Gate B` control submits one approved candidate decision to Gate B with `commit_reason="source_intake_gate_b_rendered_admission"`.

On success, the workbench projects the returned Gate B session id, marks the preview as committed, updates the in-memory material preview to the same server-previewed candidate, and enables the existing Gate C controls from the normal workbench state.

On failure, the workbench preserves the server error envelope by showing the returned message plus nested `detail.error_code` when present. The forced browser proof covers:

- `source_intake_gate_b_forbidden_field_not_admitted`
- `source_intake_gate_b_record_not_admitted`

## Proof Files

- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.css`
- `backend/app/review_ui/static/layer3.js`
- `backend/tests/test_layer3_page.py`
- `e2e/layer3-workbench.spec.js`
- `next_milestone_plans/Layer3_planning_docs/296_SOURCE_INTAKE_GATE_B_RENDERED_ADMISSION_CONTROLS.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `tools/l3-progress-check.py`

## Required Validation

- `python .\tools\l3-progress-check.py`
- `python -m pytest .\backend\tests\test_layer3_page.py .\backend\tests\test_layer3_source_intake.py .\backend\tests\test_layer3_source_boundary.py .\backend\tests\test_layer3_gate_b_state.py -q`
- `npx playwright test layer3-workbench.spec.js --grep "rendered source-intake upload inventory and preview" --project=chromium`
- `npx playwright test layer3-workbench.spec.js --grep "rendered source-intake upload inventory and preview" --project=chromium --headed`

## Validation Result

- `python .\tools\l3-progress-check.py`: passed after proof-ledger sync.
- `python -m pytest .\backend\tests\test_layer3_page.py .\backend\tests\test_layer3_source_intake.py .\backend\tests\test_layer3_source_boundary.py .\backend\tests\test_layer3_gate_b_state.py -q`: `37 passed, 3 warnings`.
- `npx playwright test layer3-workbench.spec.js --grep "rendered source-intake upload inventory and preview" --project=chromium`: `1 passed`.
- `npx playwright test layer3-workbench.spec.js --grep "rendered source-intake upload inventory and preview" --project=chromium --headed`: `1 passed`.
- GitHub `backend-layer3-api`: passed for PR `#879`.
- GitHub `test`: passed for PR `#879`.
- Post-merge `python .\tools\l3-progress-check.py`: passed against `project6-origin/main` at `204d551a88b136882d1ee27a2c31d02798e2547c`.

## Blocked Scope Preserved

The following remain blocked:

- new backend route
- backend DTO widening beyond existing response/request contracts
- model or migration change
- package construction or mutation
- connector/destination dispatch
- provider-private signed URL prepare
- provider/public URL behavior
- execution start
- RAG/vector indexing
- web connector retrieval
- generic source upload
- broad file upload
- local path authority
- local directory authority
- non-text binary preview
- auth/security behavior
- frontend-only durable authority
