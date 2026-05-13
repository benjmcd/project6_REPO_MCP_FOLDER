# 292 - Source Intake Rendered Controls

Status: branch-local implementation and proof for `source_intake_rendered_controls`.

implementation_branch: `codex/l3-source-intake-rendered-controls`

selected_runtime_family: `source_breadth_runtime`

selected_runtime_mode: `operator_source_intake_rendered_controls`

rendered_route: `/review/layer3`

## Canonical source of truth

The durable authority remains `L3SourceIntakeRecord`.

The rendered controls are not a new source authority. They only call the already-landed server-authoritative source-intake API chain:

- `POST /api/v1/layer3/source/intake/upload`
- `GET /api/v1/layer3/source/intake/inventory`
- `GET /api/v1/layer3/source/intake/{source_intake_record_id}/preview`

## Implemented surface

`/review/layer3` now includes a bounded `source-intake-rendered-controls` workband. The workband lets an operator upload one file to the existing source-intake writer, refresh the durable inventory, and request a bounded server preview for a selected durable record.

The browser state is display and interaction state only. Server response rows, hashes, relative storage pointers, and bounded preview text remain owned by the existing backend service.

## Scope admitted

- Render existing source-intake upload/inventory/preview controls on `/review/layer3`.
- Use multipart upload fields required by the existing API contract, including `operator_decision=record_operator_uploaded_source`.
- Display durable inventory rows from `L3SourceIntakeRecord`.
- Display bounded preview text from `material_candidate.preview_text`.
- Register the rendered workband with the operation dock so it is never an overlaying untracked panel.
- Prevent duplicate durable uploads by treating submit as a single-flight operation while the upload is pending.
- Preserve the successful durable upload message if the follow-up inventory refresh fails.
- Prove the rendered path in static page tests and a focused Playwright workbench test.

## Scope blocked

- No backend route, DTO, model, migration, or service change.
- No generic source upload, local path, local directory, web connector, or source adapter registry behavior.
- No RAG/vector indexing, embedding generation, qualitative/hybrid analysis, or hidden LLM planning.
- No package construction, package mutation, provider/public URL behavior, provider-private signed URL prepare, connector/destination dispatch, execution start, or auth/security behavior.
- no frontend-only durable authority.

## Proof plan

- `python .\tools\l3-progress-check.py`
- `python -m pytest .\backend\tests\test_layer3_page.py .\backend\tests\test_layer3_source_intake.py .\backend\tests\test_layer3_source_boundary.py -q`
- `npx playwright test layer3-workbench.spec.js --grep "rendered source-intake upload inventory and preview" --project=chromium`
- `npx playwright test layer3-workbench.spec.js --grep "rendered source-intake upload inventory and preview" --project=chromium --headed`
- `npx playwright test --project=chromium`

## Acceptance

This slice is accepted only if the checker, static/backend source-intake tests, and focused headless/headed browser proofs pass without requiring any backend runtime expansion.
