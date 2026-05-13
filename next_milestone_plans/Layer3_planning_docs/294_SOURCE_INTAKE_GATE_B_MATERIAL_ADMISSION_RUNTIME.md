# 294 Source Intake Gate B Material Admission Runtime

## Status

Status: branch-local implementation entry for `source_intake_gate_b_material_admission_runtime`.

Branch: `codex/l3-source-intake-gate-b-runtime`.

Runtime proof name: `source_intake_gate_b_material_admission_runtime`.

Selected runtime family: `source_breadth_runtime`.

Selected runtime mode: `source_intake_gate_b_material_admission`.

Canonical source of truth: `L3SourceIntakeRecord`.

## Implemented Boundary

This pass admits operator-uploaded source-intake material into the existing Gate B decision path without adding a new route, model, migration, rendered UI behavior, package path, connector path, RAG/vector path, provider URL path, execution start, or auth/security behavior.

Admitted routes:

- `GET /api/v1/layer3/source/intake/{source_intake_record_id}/preview`
- `POST /api/v1/layer3/gate-b/decision`

Admitted material candidate shape:

- `material_candidate.candidate_id` uses `mat-source_intake_record-`.
- `material_candidate.source_class` remains `operator_uploaded_single_source`.
- `material_preview_hash` is derived from the same Gate B material-preview hash basis used by normal Gate B decisions.
- `decision_basis.source_ref`, `decision_basis.source_identity`, and `decision_basis.payload` must match the persisted `L3SourceIntakeRecord`.

## Runtime Guards

Gate B admission is fail-closed unless the submitted material decision traces back to one recorded `L3SourceIntakeRecord`, an existing server-owned storage object, and a matching persisted content hash.

The runtime rejects:

- missing source-intake authority rows
- non-recorded source-intake rows
- source families other than `operator_uploaded_single_source`
- non-text-like media types that cannot pass bounded material preview
- storage objects missing from `raw/layer3-source-intake`
- storage hash mismatches against `content_sha256`
- stale or mismatched `source_ref`
- stale or mismatched `source_identity`
- stale or mismatched source-intake preview `payload`
- decision-basis fields from adjacent deferred modes

Explicitly forbidden adjacent fields include local path authority, local directory authority, raw file bytes, web connector targets, provider/public URLs, RAG/vector indexes, package payloads, execution mode, auth policy, frontend durable state, and destination dispatch.

## Side-Effect Boundary

Successful admission creates only the existing Gate B selection state:

- `L3Session`
- `L3SelectionManifest`
- `L3Descriptor`
- `L3MaterialSnapshot`
- `L3GateBIdempotencyKey`

It does not create:

- `L3PassRun`
- `AnalysisRun`
- `AnalysisArtifact`
- `L3OutputPackage`
- package/handoff/export artifacts
- connector/destination dispatch records
- provider/public URL records
- RAG/vector indexes

## Blocked Scope

The following remain blocked after this runtime pass:

- generic source upload
- broad file upload
- local path authority
- local directory authority
- web connector retrieval
- RAG/vector indexing
- package construction or mutation from uploaded source material
- connector/destination dispatch
- provider-private signed URL prepare
- execution start
- auth/security behavior
- frontend-only durable authority
- non-text binary preview
- rendered Gate B source-intake controls

## Next Boundary

The next likely boundary is `source_intake_gate_b_rendered_admission_controls_freeze`.

That later freeze must decide whether the rendered `/review/layer3` source-intake controls may submit the admitted Gate B material candidate, and it must separately prove headed and headless browser behavior before any rendered UI admission claim is made.
