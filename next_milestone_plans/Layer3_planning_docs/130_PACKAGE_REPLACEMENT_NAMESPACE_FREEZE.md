# Layer 3 Replacement Package Namespace Freeze

Status: planning/control freeze only for `replacement_package_namespace_rows`. No runtime behavior is admitted by this document.

This artifact narrows the next package lifecycle question after the live `replacement_package_artifact_manifest_only` runtime. Current main can server-verify existing replacement artifact refs and hashes, but live `L3OutputPackage` still has one authoritative source package row per `(session_id, package_kind)` through `uq_l3_output_package_session_kind`. Therefore replacement package rows remain blocked until a separate namespace model preserves that source-row authority instead of weakening it.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- baseline_ref: `project6-origin/main`
- baseline_commit: `f4698f7cdc1cb1ddd01511eb47de5ad37f1b8b56`
- predecessor planning/control freeze: `128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md`
- predecessor manifest runtime freeze: `129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE.md`
- current output package model: `backend/app/models/models.py` `L3OutputPackage`
- current uniqueness blocker: `uq_l3_output_package_session_kind`
- selected_future_package_lifecycle_mode: `replacement_package_namespace_rows`
- selected_namespace_design: `separate_replacement_output_package_table`
- future owner surface: package namespace authority only; no payload generation or payload rewrite
- evidence boundary: live source/tests and `tools/l3-progress-check.py` outrank this document

## Decision

The next package row namespace question is narrowed to exactly:

- selected_future_package_lifecycle_mode: `replacement_package_namespace_rows`
- selected_namespace_design: `separate_replacement_output_package_table`

This is not live runtime. A later implementation-entry PR may only create replacement package row authority in a separate replacement table keyed to an existing `L3ReplacementPackageArtifactManifest` and `L3PackageSupersessionCommit`.

The future design must not weaken, remove, or reinterpret `uq_l3_output_package_session_kind`. Existing `L3OutputPackage` rows remain source-package authority. Replacement rows, if later admitted, must be separate replacement-package authority with their own namespace, source lineage, manifest binding, package-kind uniqueness, idempotency, and negative proof.

## Why Namespace Outranks Broad Reconstruction

Broad package mutation/reconstruction would be an overclaim today. The manifest runtime proves replacement refs and hashes can be server-verified, but it still creates no replacement package rows, no payload bytes, no rendered controls, and no package rewrite authority.

Freezing a separate replacement namespace first reduces risk because it blocks accidental reuse of source package rows as replacement rows and prevents the existing uniqueness constraint from being weakened just to make broad package reconstruction convenient.

## Required Future Contract

A later implementation-entry freeze or PR must define:

- future model/table name for replacement package rows;
- relation to `L3ReplacementPackageArtifactManifest`;
- relation to `L3ReplacementPackageSetAuthority`;
- relation to `L3PackageSupersessionCommit`;
- package-kind uniqueness within the replacement namespace;
- source `L3OutputPackage` immutability rule;
- replacement artifact ref/hash authority copied only from the manifest authority;
- idempotency key and authority hash basis;
- stale manifest, stale replacement set, stale lineage, stale source package, stale ref, and stale hash behavior;
- response-safe receipt fields and next allowed actions;
- rollback path that leaves source package rows, source payloads, manifest rows, and lineage rows unchanged.

## Positive Invariants

The future namespace slice is acceptable only if:

- `replacement_package_namespace_rows` is the only selected row namespace mode;
- `package_mutation_reconstruction` remains deferred;
- existing `L3OutputPackage` rows remain immutable source authority;
- existing source package payload files remain immutable source authority;
- the existing `uq_l3_output_package_session_kind` constraint remains intact;
- replacement package row authority uses a separate table or equivalent separate namespace that does not collide with source package rows;
- replacement row creation is impossible without an existing verified replacement artifact manifest;
- replacement row creation is impossible without existing package supersession lineage;
- replacement row creation does not generate, rewrite, overwrite, delete, or reconstruct package payload bytes;
- future responses expose only response-safe ids, refs, hashes, schema ids, status, and next actions.

## Negative Invariants

This freeze must not accidentally admit:

- runtime behavior;
- package row creation, update, or deletion;
- replacement `L3OutputPackage` row creation in the source table;
- weakening or removing `uq_l3_output_package_session_kind`;
- package payload creation, rewrite, overwrite, deletion, or reconstruction;
- package payload bytes accepted from the browser;
- replacement package artifact generation;
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
- `L3ReconciliationRecord` creation, update, or deletion;
- frontend-only durable state;
- hidden LLM planning;
- rendered package mutation controls;
- full mockup activation;
- authentication/security hardening.

## Required Future Tests

A later implementation-entry PR must prove:

- namespace rows cannot be created without a verified replacement artifact manifest;
- namespace rows cannot be created without immutable package supersession lineage;
- stale manifest authority fails closed;
- stale replacement package-set authority fails closed;
- stale source package authority fails closed;
- duplicate `client_request_id` behavior is deterministic;
- concurrent duplicate requests cannot create duplicate replacement namespace rows;
- replacement rows do not use the source `l3_output_package` table;
- existing `L3OutputPackage` rows are unchanged;
- existing source package payload files are unchanged;
- existing package construction, package-review submit, handoff/export, APS handoff, external export/download, signed-reference, internal connector record, replacement package-set authority, package supersession commit, and replacement artifact manifest behavior are unchanged;
- no provider/public URL, connector/destination dispatch, source expansion, qualitative/hybrid/RAG execution, full mockup activation, or auth/security behavior is admitted.

## Stop Conditions

Stop before implementation if the intended change requires:

- creating replacement rows in `l3_output_package`;
- weakening `uq_l3_output_package_session_kind`;
- mutating existing `L3OutputPackage` rows;
- generating replacement package payload bytes;
- accepting package bytes or edited package content from the browser;
- rewriting, deleting, or reconstructing existing source package payload files;
- using replacement package-set metadata without verified artifact manifest authority;
- dispatching to connectors or destinations;
- creating provider/public URLs;
- widening source/upload/local-directory/RAG/vector inputs;
- broad qualitative, hybrid, or RAG execution;
- full mockup activation;
- authentication/security work while that lane remains deferred.

## Acceptance Criteria

This planning/control slice is accepted when:

- this file exists and contains `selected_future_package_lifecycle_mode: replacement_package_namespace_rows`;
- this file preserves `selected_namespace_design: separate_replacement_output_package_table`;
- `105_deferred-gates.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md` keep broad package mutation/reconstruction blocked while naming this namespace prerequisite;
- `tools/l3-progress-check.py` fails closed if this freeze is missing, if `uq_l3_output_package_session_kind` is not preserved, or if broad package mutation/reconstruction is accidentally marked admitted;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` reports no whitespace errors.
