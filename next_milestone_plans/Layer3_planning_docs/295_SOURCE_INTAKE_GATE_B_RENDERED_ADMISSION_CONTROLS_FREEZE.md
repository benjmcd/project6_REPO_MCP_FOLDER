# 295 Source Intake Gate B Rendered Admission Controls Freeze

## Status

Status: planning/control freeze for `source_intake_gate_b_rendered_admission_controls_freeze`.

Branch: `codex/l3-source-intake-gate-b-rendered-freeze`.

Selected runtime family: `source_breadth_runtime`.

Selected rendered-control mode: `source_intake_gate_b_rendered_admission_controls`.

Canonical source of truth: `L3SourceIntakeRecord`.

Runtime predecessor: `source_intake_gate_b_material_admission_runtime`.

Runtime predecessor doc: `294_SOURCE_INTAKE_GATE_B_MATERIAL_ADMISSION_RUNTIME.md`.

Next allowed action: `implement_source_intake_gate_b_rendered_admission_controls`.

## Freeze Decision

The next implementation slice may add rendered `/review/layer3` controls that submit an already-admitted source-intake material candidate to the existing Gate B decision route.

This freeze does not implement rendered UI behavior. It only defines the exact boundary that a later implementation must satisfy.

The rendered controls may use only these existing server-authoritative APIs:

- `POST /api/v1/layer3/source/intake/upload`
- `GET /api/v1/layer3/source/intake/inventory`
- `GET /api/v1/layer3/source/intake/{source_intake_record_id}/preview`
- `POST /api/v1/layer3/gate-b/decision`

The rendered controls must treat `material_candidate`, `material_preview_id`, and `material_preview_hash` from source-intake preview as server authority. Browser state may stage form input and selected row identity only; it must not become durable authority.

## Required Future Implementation Proof

The implementation PR must prove:

- rendered controls surface one eligible source-intake preview candidate for Gate B admission
- submitted `candidate_id` uses `mat-source_intake_record-`
- submitted `decision_basis` copies `source_ref`, `query_basis`, `provenance_ref`, `source_identity`, `source_provenance`, `payload`, and `load_summary` from the server preview response
- submitted `material_preview_hash` matches the server preview response
- success projects the Gate B session id, approved candidate, and next state without fabricating authority
- replay or duplicate submit is guarded by a single-flight or idempotent client path
- forbidden adjacent controls for local path, local directory, web connector, RAG/vector, package construction, connector/destination dispatch, provider URL, execution start, and auth/security are not exposed
- failed Gate B responses preserve the workbench error envelope without leaking absolute paths, storage-root paths, file bytes, connector secrets, provider URLs, or browser-local durable authority
- headed and headless Chromium evidence both exercise the rendered admission path

## Required Future Tests

The implementation PR must include focused tests for:

- static page/API wiring for rendered source-intake Gate B admission controls
- successful browser-level upload or preview fixture to Gate B submit flow
- error rendering for `source_intake_gate_b_forbidden_field_not_admitted`
- error rendering for stale source-intake authority such as `source_intake_gate_b_record_not_admitted`
- no rendered controls for blocked adjacent modes
- no new backend route, DTO, model, migration, service, package, connector, provider URL, RAG/vector, execution, or auth/security behavior
- both headed and headless browser proof if Playwright is used

## Blocked Scope

The following remain blocked in this freeze and in the next rendered-control implementation unless separately frozen:

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

## Stop Condition

If implementation requires any new backend route, model, migration, package construction, connector/destination dispatch, execution start, RAG/vector behavior, provider URL, auth/security change, local path/local directory authority, or frontend-only durable authority, stop and create a separate freeze before editing.
