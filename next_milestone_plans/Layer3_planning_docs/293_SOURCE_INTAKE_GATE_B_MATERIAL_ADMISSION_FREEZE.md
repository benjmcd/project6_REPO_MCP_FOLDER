# Source Intake Gate B Material Admission Freeze

## Decision

- Status: `completed_source_intake_gate_b_material_admission_freeze`.
- Branch: `codex/l3-source-intake-gate-b-freeze`.
- Selected runtime family: `source_breadth_runtime`.
- Selected runtime mode: `source_intake_gate_b_material_admission`.
- Named operator/product use case: `operator_uploaded_source_intake_feeds_gate_b_material_review`.
- Canonical source of truth: `L3SourceIntakeRecord`.
- This freeze is planning/control only. It makes no runtime behavior, rendered UI behavior, backend route, DTO, model, migration, or service change by itself.

## Why this is the next narrow boundary

Current source-intake authority already admits only the exact chain below:

- `operator_single_upload_source_intake` records one server-owned operator upload through `POST /api/v1/layer3/source/intake/upload`.
- `operator_source_intake_inventory_read_only` lists server-owned `L3SourceIntakeRecord` rows.
- `operator_source_intake_material_preview_read_only` returns bounded text preview over the same record authority.
- `operator_source_intake_rendered_controls` exposes upload, inventory, and bounded preview controls on `/review/layer3` without backend route, DTO, model, migration, or service expansion.

That chain still does not allow an uploaded record to participate in normal Gate B material review. The next useful product step is therefore not another upload surface and not package construction; it is the exact admission bridge from one already-recorded source-intake row into Gate B material review.

## Future runtime contract to prove before implementation

A later code-bearing PR may implement only `implement_source_intake_gate_b_material_admission_runtime`. That implementation must prove all of the following before merge:

- Request authority: the request identifies exactly one existing `L3SourceIntakeRecord` by server-owned identifier, not by browser path, local path, directory path, raw bytes, provider URL, connector target, or package payload.
- Response authority: the response may expose only admitted Gate B material-candidate state, source-intake record identity, content/metadata hash basis, bounded preview identity, status, blocked reason, and next allowed actions.
- Forbidden request fields: `file`, `file_bytes`, `absolute_path`, `local_path`, `directory_path`, `provider_url`, `public_url`, `web_connector`, `connector_target`, `destination`, `rag_index`, `vector_index`, `package_payload`, `execution_mode`, `auth_policy`, and frontend-only durable state.
- stale-authority rule: reject missing, stale, hash-mismatched, non-preview-eligible, non-operator-uploaded, or superseded `L3SourceIntakeRecord` rows fail closed before any Gate B candidate is created.
- Idempotency rule: replays over the same source-intake record, content hash, bounded-preview identity, session, and client request key must return the same admitted candidate or an explicit idempotent echo, not create duplicate candidates.
- Duplicate rule: conflicting replay, changed hash basis, changed preview basis, or second non-idempotent admission attempt must fail closed with a blocked field that points to `source_intake_record_id` or the conflicting idempotency basis.
- Rollback/failure rule: partial admission is not allowed; if Gate B candidate creation cannot be completed, no durable half-admitted material candidate may remain visible as normal Layer 3 flow state.
- Leakage rule: errors, logs, rendered state, screenshots, and API responses must not expose absolute filesystem paths, raw uploaded bytes, raw storage refs, provider tokens, connector credentials, hidden prompt text, or private runtime diagnostics.
- Rendered proof rule: if a later implementation changes `/review/layer3`, headed and headless Chrome plus `system`, `light`, `dark`, and `workbench` theme proof must cover the exact new controls.

## Explicit no-go list

This freeze does not admit any of the following:

- Generic source upload or broad file upload.
- Local path or local-directory authority.
- Web connector retrieval.
- RAG/vector indexing.
- Non-text binary preview.
- Package construction or package mutation from uploaded source material.
- Provider-private signed URL prepare/status/revoke behavior.
- Connector/destination dispatch.
- Execution start, qualitative/hybrid/RAG analysis, or hidden LLM planning.
- Auth/security runtime hardening.
- frontend-only durable authority.
- Backend expansion outside the exact Gate B material-admission contract.

## Required negative tests for the later runtime PR

The implementation PR must fail closed for:

- Unknown `source_intake_record_id`.
- Record owned by another session or outside the current Layer 3 authority boundary.
- Record with stale content hash, stale metadata hash, stale storage ref, or changed bounded-preview identity.
- Record that is not `material_candidate` eligible.
- Duplicate non-idempotent admission for the same source-intake record.
- Conflicting idempotency key over a different source-intake record or hash basis.
- Any forbidden field listed above, including nested occurrences.
- Attempts to trigger local directory ingestion, web connector retrieval, RAG/vector indexing, package construction, provider-private signed URL prepare, connector/destination dispatch, execution start, auth/security behavior, or frontend-only durable state.

## Stop condition

After this freeze merges, the next allowed code-bearing action is `implement_source_intake_gate_b_material_admission_runtime` only. If implementation discovers that Gate B admission requires source semantics outside `L3SourceIntakeRecord` plus existing Gate B material authority, the implementation must stop and return to planning instead of widening scope inside the runtime PR.
