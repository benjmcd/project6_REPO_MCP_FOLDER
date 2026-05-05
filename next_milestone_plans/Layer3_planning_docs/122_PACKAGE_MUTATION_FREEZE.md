# Layer 3 Package Mutation Freeze

Status: implementation-entry freeze plus bounded runtime contract for `package_supersession_preview_only`, implemented on current main by PR #540 at `project6-origin/main=c23a48c1`.

This artifact selects and governs the first safe package mutation/reconstruction entry mode. Runtime implementation scope is limited to `/api/v1/layer3/package/mutation/preview` and `backend/app/services/layer3_package_mutation_entry.py`. It does not add a commit route, model, migration, package row update, payload rewrite, payload deletion, handoff/export change, connector dispatch, source expansion, qualitative/hybrid/RAG execution, rendered control, full mockup activation, or authentication/security work.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- implementation_branch: `codex/l3-package-supersession-preview`
- merged_pr: `#540`
- baseline_ref: `project6-origin/main`
- baseline_commit: `c23a48c1`
- source gates: `105_deferred-gates.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, `120_L3_CLOSEOUT.md`, package construction docs `50`/`51` and `88`/`89`, and connector entry doc `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md`
- source code checked: `backend/app/services/layer3_state_action_contract.py`, `backend/app/services/layer3_workbench.py`, `backend/app/services/layer3_package_mutation_entry.py`, `backend/app/api/layer3.py`, focused Layer 3 API tests, and package construction planning docs
- local caveat: `.omc/state/*` and local sidecars are operator/tooling state and are not evidence for this freeze

## Decision

The first package mutation/reconstruction lane must use exactly this mode:

- selected_package_lifecycle_mode: `package_supersession_preview_only`

This mode is a read-only server preview of a possible immutable package supersession. It compares an existing package set, existing payload refs, existing payload hashes, and existing downstream receipts against a proposed reconstruction intent. It must not mutate, overwrite, delete, rebuild, replace, or append package payload bytes or package rows.

The immutable package rule is frozen here:

- immutable_package_rule: existing `L3OutputPackage` rows and package payload files are immutable after construction; any future reconstruction must be represented as a new, separately admitted supersession lineage after preview proof, not as in-place package mutation.

The other candidate modes remain blocked:

- `in_place_package_payload_rewrite` remains blocked because package rows, payload refs, hashes, handoff/export records, APS handoff records, external export/download readiness, and connector dispatch records may already depend on the original package bytes.
- `package_reconstruction_commit` remains blocked because no repo-confirmed supersession row model, lifecycle state, migration, or downstream invalidation contract is selected here.
- `package_variant_editing` remains blocked because editable package variants are target-state/mockup concepts and do not have live authority.

## Why This Outranks Runtime Mutation

Current repo authority proves bounded package construction and review-submit paths, not package mutation/reconstruction. Existing service boundaries list `package_payload`, `package_variant_content`, `rewrite_output`, and `rebuild_package` as forbidden downstream fields; existing tests prove the related package payload and rewrite request paths fail closed.

Runtime mutation before an immutable supersession rule would be fragile because it could invalidate:

- `L3OutputPackage.payload_ref`
- `L3OutputPackage.payload_hash`
- `L3ReconciliationRecord.summary_json`
- package-review submit authority
- handoff/export preparation authority
- APS handoff dispatch authority
- external export/download readiness
- signed-reference delivery authority
- internal connector dispatch records

The narrow preview-only mode reduces this risk by forcing future work to prove package identity, downstream dependency detection, and supersession semantics before any package bytes or package rows can change.

## Runtime Implementation Scope

This implementation may include only:

- owner service: `backend/app/services/layer3_package_mutation_entry.py`
- API route: exactly one preview route, `/api/v1/layer3/package/mutation/preview`
- request schema: strict Pydantic request model with `extra="forbid"`
- response schema: response-safe `layer3.package_supersession_preview.v1`
- mode: `package_supersession_preview_only`
- persistence: none
- write behavior: no database writes and no filesystem writes
- authority source: existing package construction rows, existing reconciliation record, existing payload refs/hashes, and existing downstream state only

This freeze does not admit a commit route. Doc `126_PACKAGE_COMMIT_FREEZE.md` now records that separate implementation-entry freeze for a future `package_supersession_commit_entry`; it is docs/proof-only and still does not admit a commit route, model, migration, package row update, package payload write, UI control, or runtime behavior.

## Required Preview Request Fields

The preview request must require:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `reconciliation_record_id`
- `output_package_ids`
- `package_kinds`
- `payload_refs`
- `payload_hashes`
- `package_review_preview_hash`
- `package_review_submit_record_ref`, if package-review submit already exists
- `handoff_export_record_ref`, if handoff/export preparation already exists
- `aps_handoff_record_ref`, if APS handoff dispatch already exists
- `external_export_download_record_ref`, if external export/download readiness already exists
- `connector_dispatch_record_ref`, if internal connector dispatch record already exists
- `operator_decision`

`operator_decision` must be exactly `preview_package_supersession`.

## Forbidden Preview Request Fields

The request must reject these before mutation or downstream side effects:

- `package_payload`
- `package_variant_content`
- `rewrite_output`
- `rebuild_package`
- `mutate_package`
- `replace_package`
- `delete_package`
- `update_payload_ref`
- `update_payload_hash`
- `artifact_manifest`
- `analysis_artifact`
- `handoff`
- `export`
- `connector_key`
- `connector_run_id`
- `destination_id`
- `destination_url`
- `provider_public_url`
- `public_url`
- `signed_url`
- `download_url`
- `source_upload`
- `local_directory`
- `rag_vector_index`
- `runtime_db_write`
- `qualitative_plan`
- `hybrid_execution`
- `rag_execution`
- `hidden_llm_planning`
- `schema_migration`
- `approved_plan_supersession`
- `result_review_amendment`
- `package_review_amendment`
- `handoff_export_amendment`
- `aps_handoff_amendment`
- `retry`
- `rerun`
- `cancel`

## Positive Invariants

The implementation is acceptable only when:

- `package_supersession_preview_only` is the only admitted package mutation/reconstruction entry mode.
- Broad `package_mutation_reconstruction` remains unadmitted until a separate commit freeze exists.
- Existing package rows and payload files are treated as immutable authority.
- The preview detects existing downstream dependencies before claiming any package can be superseded.
- The response exposes only response-safe preview metadata.
- Duplicate preview requests are deterministic without persistence side effects.

## Negative Invariants

The future implementation must prove no accidental:

- `L3OutputPackage` row creation, update, or deletion
- `L3ReconciliationRecord` row creation, update, or deletion
- package payload file creation, overwrite, or deletion
- package-review submit/decision state
- handoff/export preparation or delivery state
- APS handoff dispatch state
- external export/download readiness or delivery state
- connector dispatch state
- provider/public URL generation
- source/upload/local-directory/RAG/vector expansion
- `L3PassRun` creation
- `AnalysisRun` creation
- `AnalysisArtifact` creation
- schema/model/migration changes
- qualitative/hybrid/RAG execution
- frontend-only durable state
- hidden LLM planning
- full mockup activation
- authentication/security scope reopening

## Runtime Test Plan

This implementation must include focused backend/API tests proving:

- missing package authority fails closed before service execution;
- stale package ids, payload refs, payload hashes, package-review submit refs, handoff/export refs, APS handoff refs, external export/download refs, and connector dispatch refs fail closed;
- forbidden package mutation, package rewrite, source, connector, provider, schema, runtime, qualitative, hybrid, RAG, and mockup fields are rejected before mutation or downstream side effects;
- correct preview request returns a response-safe `layer3.package_supersession_preview.v1` body without persistence;
- duplicate preview requests are deterministic;
- no `L3OutputPackage`, `L3ReconciliationRecord`, `AnalysisArtifact`, `AnalysisRun`, `L3PassRun`, connector, source, handoff/export, delivery, provider URL, or payload file side effect occurs;
- existing package construction, package-review submit, handoff/export, APS dispatch, external export/download, signed-reference, and connector-record paths keep their existing behavior.

Browser proof is not required unless the implementation admits rendered package mutation controls. This freeze does not admit rendered controls.

## Current Slice Validation

This runtime slice is accepted when:

- this file exists and contains `selected_package_lifecycle_mode: package_supersession_preview_only`;
- `105_deferred-gates.md` and `118_L3_GOAL_AUDIT.md` distinguish exact read-only preview runtime from broad package mutation/reconstruction;
- `backend/app/services/layer3_state_action_contract.py` admits only `package_supersession_preview_only` and keeps `package_mutation_reconstruction` deferred;
- `backend/app/services/layer3_package_mutation_entry.py` implements `package_supersession_preview_only` with no database writes and no filesystem writes;
- `backend/app/api/layer3.py` exposes only `/api/v1/layer3/package/mutation/preview` for this mode;
- `backend/app/services/layer3_workbench.py` still treats `package_payload`, `package_variant_content`, `rewrite_output`, and `rebuild_package` as forbidden downstream fields;
- `backend/tests/test_layer3_api.py` contains success, downstream-dependency, no-side-effect, API-boundary, and fail-closed proof for this exact preview route;
- `tools/l3-progress-check.py` requires this runtime contract and still verifies package mutation/reconstruction commit remains unadmitted;
- `126_PACKAGE_COMMIT_FREEZE.md` may exist only as docs/proof-only implementation-entry and must not make `package_mutation_reconstruction` or `package_supersession_commit` admitted runtime behavior;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` reports no whitespace errors.

## Explicit Non-Goals

- package payload rewrite
- package row mutation
- package row deletion
- package reconstruction commit
- package supersession commit
- editable package variants
- package-review submit/decision changes
- handoff/export changes
- APS handoff changes
- external export/download changes
- connector/destination dispatch changes
- provider/public URL support
- source/upload/local-directory/RAG/vector expansion
- qualitative/hybrid/RAG execution
- rendered package mutation controls
- retry/cancel/recovery/queue behavior
- schema/model/migration changes
- full mockup activation
- authentication/security hardening
