# Layer 3 Package Supersession Commit Entry Freeze

Status: implementation-entry freeze plus bounded runtime contract for `package_supersession_commit_entry`.

This artifact governs the bounded package supersession commit lineage runtime admitted after the replacement package-set authority prerequisite. The runtime records an immutable supersession lineage event only. It does not update or create `L3OutputPackage` rows, write package payload files, render UI controls, dispatch connectors, widen sources, run qualitative/hybrid/RAG work, create provider/public URLs, activate mockups, or perform authentication/security work.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- baseline_ref: `project6-origin/main`
- implementation_branch: `codex/l3-package-supersession-commit-runtime`
- merged_pr: `#556`
- merged_main_head: `93fe525b`
- predecessor runtime freeze: `122_PACKAGE_MUTATION_FREEZE.md`
- predecessor runtime mode: `package_supersession_preview_only`
- replacement authority prerequisite: `127_PACKAGE_REPLACEMENT_SET_FREEZE.md` is implemented as `replacement_package_set_authority`
- selected runtime route: `/api/v1/layer3/package/supersession/commit`
- owner service: `backend/app/services/layer3_package_supersession_commit.py`
- lineage model: `L3PackageSupersessionCommit`
- migration: `0019_layer3_package_supersession_commit.py`
- current admitted package lifecycle runtimes: `package_supersession_preview_only`, `replacement_package_set_authority`, and `package_supersession_commit_entry`
- current deferred capability: `package_mutation_reconstruction` remains deferred
- evidence boundary: live source, tests, and `tools/l3-progress-check.py` outrank this document

## Decision

The next package lifecycle question is narrowed to exactly this future mode:

- selected_package_lifecycle_mode: `package_supersession_commit_entry`

This is a bounded runtime admission, not broad package mutation/reconstruction. It exists because the read-only preview route proves source package identity, payload identity, and downstream dependency inspection without side effects, and `replacement_package_set_authority` proves a separate replacement package-set authority record without creating replacement `L3OutputPackage` rows.

The selected mode is not in-place package mutation. It is modeled as an immutable supersession lineage event that points from an existing package set to a separately proven replacement package set. Existing `L3OutputPackage` rows and existing package payload files remain immutable authority. Doc `127_PACKAGE_REPLACEMENT_SET_FREEZE.md` records the replacement package-set authority prerequisite through a bounded metadata-authority runtime; broad package mutation/reconstruction remains blocked after this lineage runtime.

## Why This Lane

This lane outranks broad package mutation/reconstruction because current code has already implemented a read-only package supersession preview, while broad mutation remains blocked. The next safe question is whether a commit can record immutable lineage after preview proof, not whether existing package bytes or rows can be rewritten.

This lane outranks connector/destination dispatch, broad source/upload expansion, broad qualitative/hybrid/RAG execution, provider/public URLs, and full mockup activation because those lanes still lack selected live runtime authority or have explicit fail-closed boundaries. Authentication/security remains deferred by operator instruction and is not reopened here.

## Runtime Shape

This implementation may include only:

- owner service: `backend/app/services/layer3_package_supersession_commit.py`
- API route: `/api/v1/layer3/package/supersession/commit`
- route method: `POST`
- request schema: strict Pydantic body with `extra="forbid"`
- response schema: `layer3.package_supersession_commit.v1`
- operator decision: `commit_package_supersession`
- persistence: `L3PackageSupersessionCommit` via `0019_layer3_package_supersession_commit.py`, not existing package row mutation
- authority source: an existing `package_supersession_preview_only` hash, existing package rows, existing payload refs/hashes, existing `replacement_package_set_authority`, and current downstream dependency state

The implementation must not rely on frontend-provided package bytes, edited package text, arbitrary artifact manifests, local paths, destination ids, provider URLs, source uploads, model flags, hidden LLM plans, or mockup-only fields.

## Required Request Fields

The commit request must require:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `reconciliation_record_id`
- `package_supersession_preview_hash`
- `source_package_set_hash`
- `source_output_package_ids`
- `source_package_kinds`
- `source_payload_refs`
- `source_payload_hashes`
- `replacement_package_set_authority_id`
- `replacement_package_set_id`
- `replacement_package_set_hash`
- `replacement_package_kinds`
- `replacement_payload_refs`
- `replacement_payload_hashes`
- `replacement_authority_basis_hash`
- `downstream_dependency_hash`
- `commit_basis_hash`
- `operator_decision`

`operator_decision` must be exactly `commit_package_supersession`.

## Runtime Model Boundary

The implementation uses a dedicated supersession lineage model/migration. The lineage record must preserve:

- source package set hash, ids, kinds, refs, and hashes;
- replacement package-set authority id, replacement package-set id/hash, kinds, refs, and hashes;
- preview hash;
- downstream dependency hash;
- replacement authority basis hash;
- commit basis hash;
- operator decision;
- commit request id;
- immutable status vocabulary;
- created timestamp.

The model must not update or delete `L3OutputPackage` rows. It must not overwrite, create, or delete package payload files.

## Positive Invariants

The current bounded runtime slice is acceptable only when:

- `126_PACKAGE_COMMIT_FREEZE.md` exists and selects only `package_supersession_commit_entry`;
- `127_PACKAGE_REPLACEMENT_SET_FREEZE.md` exists and keeps replacement package-set authority limited to a metadata-authority runtime;
- `backend/app/services/layer3_package_supersession_commit.py` owns the lineage runtime;
- `/api/v1/layer3/package/supersession/commit` is the only package supersession commit route;
- `L3PackageSupersessionCommit` records immutable lineage without mutating package rows or payloads;
- `0019_layer3_package_supersession_commit.py` preserves unique `client_request_id` and `commit_basis_hash`;
- `package_supersession_preview_only`, `replacement_package_set_authority`, and `package_supersession_commit_entry` are the only admitted package lifecycle runtimes;
- `package_mutation_reconstruction` remains deferred in `backend/app/services/layer3_state_action_contract.py`;
- no UI control, package row mutation, package payload write, replacement package row creation, connector dispatch, source widening, qualitative/hybrid/RAG execution, provider/public URL behavior, full mockup activation, or auth/security behavior is added by this slice;
- `105_deferred-gates.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md` label this as a bounded lineage-only runtime;
- `tools/l3-progress-check.py` fails closed if this boundary drifts.

## Negative Invariants

This slice must not accidentally admit or implement:

- package row creation, update, or deletion;
- package payload creation, rewrite, overwrite, deletion, or reconstruction;
- package mutation/reconstruction beyond immutable lineage recording;
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

## Runtime Test Requirements

Before merge, this runtime implementation must prove:

- strict request-body rejection for all non-admitted fields before service mutation;
- stale preview hash fails closed;
- stale source package set, ids, kinds, refs, or hashes fail closed;
- stale replacement package-set authority id, package-set id/hash, refs, hashes, or basis hash fail closed;
- stale downstream dependency hash fails closed;
- stale commit basis hash fails closed;
- duplicate `client_request_id` behavior is deterministic;
- concurrent duplicate commit attempts cannot create duplicate lineage records;
- existing package rows and payload files are unchanged;
- existing package construction, package review, handoff/export, APS handoff, external export/download, signed-reference, internal connector record, and package preview behavior are unchanged;
- no provider/public URL, connector/destination dispatch, source expansion, qualitative/hybrid/RAG execution, full mockup activation, or auth/security behavior is admitted.

Browser proof is not required for this lineage-only backend/API slice. Browser proof becomes required only if a later runtime implementation admits rendered controls.

## Stop Conditions

Stop before implementation if the intended change requires:

- in-place mutation of an existing package row;
- rewriting, deleting, or reconstructing an existing package payload file;
- accepting package bytes or edited package content from the browser;
- updating or deleting existing `L3OutputPackage` rows;
- writing package payload files;
- dispatching to connectors or destinations;
- creating provider/public URLs;
- widening source/upload/local-directory/RAG/vector inputs;
- broad qualitative, hybrid, or RAG execution;
- full mockup activation;
- authentication/security work while that lane remains deferred.
