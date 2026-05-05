# Layer 3 Connector Dispatch Entry Freeze

Status: implementation-entry freeze only for `internal_dispatch_record_only` after PR #536 merged at `project6-origin/main=ee40c7c2`.

This artifact selects the first connector/destination dispatch implementation mode, but it does not implement runtime behavior. It does not create a route, connector run, destination write, provider/public URL, package mutation, source expansion, qualitative/hybrid/RAG execution, rendered control, queue, retry, cancellation, model, migration, or full mockup activation.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- planning_branch: `codex/l3-next-roadmap-slice`
- baseline_ref: `project6-origin/main`
- baseline_commit: `ee40c7c2`
- source gates: `105_deferred-gates.md`, `112_CONNECTOR_DISPATCH_FREEZE.md`, `113_CONNECTOR_DISPATCH_CONTRACT.md`, `116_SECURITY_SOURCE_DELIVERY_BOUNDARY_FREEZE.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md`
- source code checked: `backend/app/services/layer3_state_action_contract.py`, `backend/app/services/layer3_workbench.py`, `backend/app/api/layer3.py`, `backend/app/models/models.py`, and focused Layer 3 tests
- local caveat: `.omc/state/*` and local sidecars are operator/tooling state and are not evidence for this freeze

## Decision

The first connector/destination dispatch lane must use exactly this mode:

- selected_dispatch_mode: `internal_dispatch_record_only`

This mode records an operator-approved dispatch intent and response-safe receipt inside the existing Layer 3 control plane. It does not invoke an external connector, write to a destination, create a connector-run row, generate a provider/public URL, mutate package bytes, widen source classes, or activate mockup-only controls.

The other candidate modes remain blocked:

- `single_named_connector_dispatch` remains blocked because no repo-confirmed connector key, connector target, credential authority, connector-run lifecycle, retry/cancel semantics, or destination authorization boundary is selected here.
- `single_named_destination_dispatch` remains blocked because no repo-confirmed destination id, destination credential, write target, delivery receipt contract, or failure lifecycle is selected here.

## Why This Outranks Broader Dispatch

The active roadmap asks for connector/destination dispatch, but current repo authority still rejects external connector and destination behavior. The only dependency-respecting next step is a narrow entry freeze that can support a future implementation without pretending external dispatch is already safe.

`internal_dispatch_record_only` is selected because it can prove the authority chain, request shape, receipt shape, idempotency, and fail-closed boundaries before any external destination is involved. This reduces risk before later package mutation, broad source expansion, qualitative/hybrid/RAG execution, or full mockup activation can be considered.

## Future Implementation Scope

The next code slice may implement only:

- owner service: `backend/app/services/layer3_connector_dispatch_entry.py`
- API route: one new route under `backend/app/api/layer3.py`, tentatively `/handoff/connector/record`
- request schema: strict Pydantic request model with `extra="forbid"`
- response schema: response-safe `layer3.connector_dispatch_record.v1`
- state key: `connector_dispatch_record` in an existing `L3ReconciliationRecord.summary_json`
- artifact family: existing associated-cohort APS evidence-bundle authority only
- dispatch mode: `internal_dispatch_record_only`
- terminal state: `connector_dispatch_recorded`
- idempotency basis: fresh `client_request_id` plus session, plan, pass, package, handoff/export, APS handoff, external export/download readiness, delivery, artifact ref/hash/size, and signed-reference authority when supplied

The next code slice must fail closed if no existing `L3ReconciliationRecord` is present. It must not create a new schema/model/migration or new `L3ReconciliationRecord` row as part of this first connector entry lane.

## Required Request Fields

A future request must include or server-derive:

- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `reconciliation_record_id`
- `result_review_record_ref`
- `package_review_preview_hash`
- `output_package_ids`
- `package_kinds`
- `payload_refs`
- `payload_hashes`
- `package_review_submit_record_ref`
- `prepare_record_ref`
- `handoff_export_state`
- `aps_handoff_record_ref`
- `aps_handoff_state`
- `aps_handoff_target`
- `aps_output_package_id`
- `aps_output_package_kind`
- `aps_bundle_ref`
- `source_artifact_hash`
- `source_artifact_size_bytes`
- `external_export_download_record_ref`
- `external_export_download_state`
- `delivery_mode`
- `operator_decision`
- `client_request_id`

`operator_decision` must be exactly `record_internal_connector_dispatch`.
`delivery_mode` must remain same-origin or internal-record-only; it must not become a provider/public URL or external destination delivery mode.

## Forbidden Request Fields

A future request must reject these before service mutation:

- `connector_key`
- `connector_run_id`
- `connector_secret`
- `destination_id`
- `destination_secret`
- `destination_url`
- `provider_url`
- `public_url`
- `signed_url`
- `download_url`
- `bucket`
- `object_key`
- `local_path`
- `package_payload`
- `package_variant_content`
- `rebuild_package`
- `rewrite_output`
- `source_upload`
- `local_directory`
- `rag_vector_index`
- `runtime_db_write`
- `retry`
- `rerun`
- `cancel`
- `hybrid_execution`
- `rag_execution`
- `hidden_llm_planning`

## Positive Invariants

The future implementation is acceptable only when:

- `internal_dispatch_record_only` is the only admitted connector entry mode.
- The existing state/action contract still keeps broad `connector_destination_dispatch` unadmitted until this exact internal record action is separately added and tested.
- The record binds to the existing associated-cohort APS evidence-bundle authority chain.
- The receipt exposes only response-safe fields.
- Duplicate `client_request_id` returns the existing record or fails closed in a specified way.
- Stale session, plan, pass, package, handoff/export, APS handoff, external export/download, delivery, artifact hash, or artifact size authority fails closed.

## Negative Invariants

The future implementation must prove no accidental:

- external connector invocation
- destination write
- generic downstream dispatch
- connector-run creation
- provider/public URL generation
- package mutation or reconstruction
- package payload byte rewrite
- source/upload/local-directory/RAG/vector expansion
- `L3PassRun` creation
- `AnalysisRun` creation
- new `L3OutputPackage` creation
- new handoff/export artifact creation
- runtime schema widening
- qualitative/hybrid/RAG execution
- frontend-only durable state
- hidden LLM planning
- full mockup activation
- authentication/security scope reopening

## Test Plan For The Next Code Slice

The next implementation must include focused backend/API tests proving:

- missing required authority fails closed before service mutation;
- forbidden connector/destination/provider/package/source fields return validation errors before service mutation;
- correct internal record request creates or returns a response-safe receipt in existing `L3ReconciliationRecord.summary_json`;
- duplicate `client_request_id` is deterministic;
- stale artifact hash/size and wrong session fail closed;
- no `ConnectorRun`, `AnalysisRun`, `L3PassRun`, `L3OutputPackage`, provider URL, destination write, package mutation, source widening, or qualitative/RAG side effect occurs;
- existing APS handoff, same-origin delivery, signed-reference, and external export/download paths keep their existing behavior.

Browser proof is not required unless the implementation admits rendered connector/destination controls. This freeze does not admit rendered controls.

## Current Slice Validation

This docs/proof slice is accepted when:

- this file exists and contains `selected_dispatch_mode: internal_dispatch_record_only`;
- `105_deferred-gates.md` and `118_L3_GOAL_AUDIT.md` mention this entry freeze without claiming runtime implementation;
- `tools/l3-progress-check.py` requires this entry freeze and still verifies broad connector/destination dispatch remains unadmitted;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` reports no whitespace errors.

## Non-Goals

Do not implement in this slice:

- connector-run creation
- external connector invocation
- destination selection or destination write
- provider/public URL support
- package mutation/reconstruction
- broad source/upload expansion
- qualitative/hybrid/RAG execution
- rendered connector/destination controls
- retry/cancel/recovery/queue behavior
- schema/model/migration changes
- full mockup activation
- authentication/security hardening
