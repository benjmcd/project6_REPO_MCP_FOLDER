# Layer 3 Package Supersession Commit Entry Freeze

Status: implementation-entry freeze only for `package_supersession_commit_entry`; no runtime behavior admitted.

This artifact selects a future package lifecycle lane. It does not implement a route, service, model, migration, package row change, package payload change, UI control, connector dispatch, source expansion, qualitative/hybrid/RAG execution, provider/public URL behavior, full mockup activation, or authentication/security work.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- baseline_ref: `project6-origin/main`
- implementation_branch: `codex/l3-package-supersession-commit-freeze`
- predecessor runtime freeze: `122_PACKAGE_MUTATION_FREEZE.md`
- predecessor runtime mode: `package_supersession_preview_only`
- replacement authority prerequisite: `127_PACKAGE_REPLACEMENT_SET_FREEZE.md`
- current admitted runtime: `package_supersession_preview_only` remains the only admitted package lifecycle runtime
- current deferred capability: `package_mutation_reconstruction` remains deferred
- evidence boundary: live source, tests, and `tools/l3-progress-check.py` outrank this document

## Decision

The next package lifecycle question is narrowed to exactly this future mode:

- selected_package_lifecycle_mode: `package_supersession_commit_entry`

This is an implementation-entry freeze, not a runtime admission. It exists because the read-only preview route now proves package identity, payload identity, and downstream dependency inspection without side effects. A future commit path may be considered only if it preserves that immutable authority.

The selected future mode is not in-place package mutation. It must be modeled as an immutable supersession lineage event that points from an existing package set to a separately proven replacement package set. Existing `L3OutputPackage` rows and existing package payload files remain immutable authority. Doc `127_PACKAGE_REPLACEMENT_SET_FREEZE.md` records the replacement package-set authority prerequisite; package supersession commit runtime remains blocked until that prerequisite is implemented and proven separately.

## Why This Lane

This lane outranks broad package mutation/reconstruction because current code has already implemented a read-only package supersession preview, while broad mutation remains blocked. The next safe question is whether a commit can record immutable lineage after preview proof, not whether existing package bytes or rows can be rewritten.

This lane outranks connector/destination dispatch, broad source/upload expansion, broad qualitative/hybrid/RAG execution, provider/public URLs, and full mockup activation because those lanes still lack selected live runtime authority or have explicit fail-closed boundaries. Authentication/security remains deferred by operator instruction and is not reopened here.

## Future Runtime Shape

A later implementation may include only:

- future owner service candidate: `backend/app/services/layer3_package_supersession_commit.py`
- future API route candidate: `/api/v1/layer3/package/supersession/commit`
- future route method: `POST`
- future request schema: strict Pydantic body with `extra="forbid"`
- future response schema: `layer3.package_supersession_commit.v1`
- future operator decision: `commit_package_supersession`
- future persistence: a dedicated supersession lineage model/migration, not existing package row mutation
- future authority source: an existing successful `package_supersession_preview_only` response, existing package rows, existing payload refs/hashes, and current downstream dependency state

The future implementation must not rely on frontend-provided package bytes, edited package text, arbitrary artifact manifests, local paths, destination ids, provider URLs, source uploads, model flags, hidden LLM plans, or mockup-only fields.

## Required Future Request Fields

A future commit request must require at least:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `reconciliation_record_id`
- `package_supersession_preview_hash`
- `source_output_package_ids`
- `source_payload_refs`
- `source_payload_hashes`
- `replacement_output_package_ids`
- `replacement_payload_refs`
- `replacement_payload_hashes`
- `downstream_dependency_hash`
- `operator_decision`

`operator_decision` must be exactly `commit_package_supersession`.

## Required Future Model Boundary

A future implementation requires a dedicated supersession lineage model/migration before any commit route is admitted. The lineage record must preserve:

- source package ids, refs, and hashes;
- replacement package ids, refs, and hashes;
- preview hash;
- downstream dependency hash;
- operator decision;
- commit request id;
- immutable status vocabulary;
- created timestamp.

The model must not update or delete `L3OutputPackage` rows. It must not overwrite or delete package payload files.

## Positive Invariants

The current docs/proof slice is acceptable only when:

- `126_PACKAGE_COMMIT_FREEZE.md` exists and selects only `package_supersession_commit_entry`;
- `127_PACKAGE_REPLACEMENT_SET_FREEZE.md` exists and keeps replacement package-set authority as implementation-entry only;
- `package_supersession_preview_only` remains the only admitted package lifecycle runtime;
- `package_mutation_reconstruction` remains deferred in `backend/app/services/layer3_state_action_contract.py`;
- no runtime route, service, model, migration, UI control, package row mutation, package payload write, or package commit behavior is added by this slice;
- `105_deferred-gates.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md` label this as implementation-entry only;
- `tools/l3-progress-check.py` fails closed if this boundary drifts.

## Negative Invariants

This slice must not accidentally admit or implement:

- package row update or deletion;
- package payload rewrite, overwrite, deletion, or reconstruction;
- package supersession commit runtime;
- package variant editing;
- package-review submit/decision changes;
- handoff/export changes;
- APS handoff changes;
- external export/download changes;
- connector/destination dispatch changes;
- provider/public URL support;
- source/upload/local-directory/RAG/vector expansion;
- qualitative/hybrid/RAG execution;
- `L3PassRun` creation;
- `AnalysisRun` creation;
- `AnalysisArtifact` creation;
- `L3OutputPackage` creation, update, or deletion;
- `L3ReconciliationRecord` creation, update, or deletion;
- frontend-only durable state;
- hidden LLM planning;
- rendered package mutation controls;
- full mockup activation;
- authentication/security hardening.

## Future Test Requirements

Before any later runtime commit implementation can merge, it must prove:

- strict request-body rejection for all non-admitted fields before service mutation;
- stale preview hash fails closed;
- stale source or replacement package ids/refs/hashes fail closed;
- stale downstream dependency hash fails closed;
- duplicate `client_request_id` behavior is deterministic;
- concurrent duplicate commit attempts cannot create duplicate lineage records;
- existing package rows and payload files are unchanged;
- existing package construction, package review, handoff/export, APS handoff, external export/download, signed-reference, internal connector record, and package preview behavior are unchanged;
- no provider/public URL, connector/destination dispatch, source expansion, qualitative/hybrid/RAG execution, full mockup activation, or auth/security behavior is admitted.

Browser proof is not required for this docs/proof slice. Browser proof becomes required only if a later runtime implementation admits rendered controls.

## Stop Conditions

Stop before implementation if the intended change requires:

- in-place mutation of an existing package row;
- rewriting, deleting, or reconstructing an existing package payload file;
- accepting package bytes or edited package content from the browser;
- committing without a dedicated supersession lineage model/migration;
- dispatching to connectors or destinations;
- creating provider/public URLs;
- widening source/upload/local-directory/RAG/vector inputs;
- broad qualitative, hybrid, or RAG execution;
- full mockup activation;
- authentication/security work while that lane remains deferred.
