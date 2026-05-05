# Layer 3 Replacement Package Namespace Entry Freeze

Status: live bounded runtime for `replacement_package_namespace_rows`.

This artifact governs the bounded runtime contract after `130_PACKAGE_REPLACEMENT_NAMESPACE_FREEZE.md`. The predecessor freeze selected a separate replacement package namespace because current `L3OutputPackage` source rows are unique by `(session_id, package_kind)` through `uq_l3_output_package_session_kind`. This runtime creates authority metadata rows only in `l3_replacement_output_package`, preserves source package rows as immutable authority, and keeps payload writes plus broad package mutation/reconstruction blocked.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- baseline_ref: `project6-origin/main`
- baseline_commit: `c208c424bda012892c0dab7412fd2cb6a1fbb460`
- predecessor package mutation freeze: `122_PACKAGE_MUTATION_FREEZE.md`
- predecessor package lineage freeze: `126_PACKAGE_COMMIT_FREEZE.md`
- predecessor replacement set freeze: `127_PACKAGE_REPLACEMENT_SET_FREEZE.md`
- predecessor artifact authority freeze: `128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md`
- predecessor artifact manifest runtime freeze: `129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE.md`
- predecessor namespace mode freeze: `130_PACKAGE_REPLACEMENT_NAMESPACE_FREEZE.md`
- current source package model: `backend/app/models/models.py` `L3OutputPackage`
- current source package uniqueness: `uq_l3_output_package_session_kind`
- selected_package_lifecycle_mode: `replacement_package_namespace_rows`
- selected_namespace_design: `separate_replacement_output_package_table`
- runtime route: `/api/v1/layer3/package/replacement-namespace/record`
- owner service: `backend/app/services/layer3_replacement_package_namespace.py`
- authority model: `L3ReplacementOutputPackage`
- table: `l3_replacement_output_package`
- migration: `0021_layer3_replacement_output_package.py`
- request DTO: `Layer3ReplacementPackageNamespaceRecordRequest`
- response DTO: `Layer3ReplacementPackageNamespaceRecordResponse`
- evidence boundary: live source/tests and `tools/l3-progress-check.py` outrank this document

## Entry Decision

The only runtime this entry freeze admits is `replacement_package_namespace_rows`.

The runtime may create replacement output-package authority rows only in `l3_replacement_output_package`, never in the source `l3_output_package` table. It must not weaken, remove, or reinterpret `uq_l3_output_package_session_kind`.

The runtime must bind each replacement row to existing, immutable authority:

- one `L3ReplacementPackageArtifactManifest` row;
- one `L3ReplacementPackageSetAuthority` row;
- one `L3PackageSupersessionCommit` row;
- one source `L3OutputPackage` row for the same `session_id` and `package_kind`;
- one verified replacement artifact ref/hash from the manifest for that `package_kind`.

This document now governs the bounded runtime route, service, model, migration, DTOs, and row contract.

## Runtime Row Contract

The `L3ReplacementOutputPackage` row must be authority metadata only:

- `replacement_output_package_id`;
- `session_id`;
- `source_output_package_id`;
- `replacement_artifact_manifest_id`;
- `replacement_package_set_authority_id`;
- `package_supersession_commit_id`;
- `package_kind`;
- `package_schema_id`;
- `artifact_ref`;
- `artifact_hash`;
- `authority_basis_hash`;
- `client_request_id`;
- `operator_decision`;
- `status`;
- `created_at`;
- `summary_json`.

The migration must include:

- primary key on `replacement_output_package_id`;
- foreign keys to source `l3_output_package`, `l3_replacement_package_artifact_manifest`, `l3_replacement_package_set_authority`, `l3_package_supersession_commit`, and `l3_session`;
- `uq_l3_replacement_output_package_manifest_kind` on `(replacement_artifact_manifest_id, package_kind)`;
- `uq_l3_replacement_output_package_client_request` on `client_request_id`;
- `uq_l3_replacement_output_package_basis_hash` on `authority_basis_hash`;
- indexes for session, source output package, manifest, replacement set, supersession commit, and package kind;
- check constraints for `operator_decision == "record_replacement_package_namespace"` and `status == "recorded"`.

The response must expose only response-safe ids, refs, hashes, package kind, schema id, status, authority basis hash, idempotency result, blocked downstream capabilities, and next allowed actions. It must not expose package bytes, file contents, secret paths, connector credentials, or provider URLs.

## Runtime Request Contract

The request body must be strict and fail closed on extra fields. Required fields:

- `session_id`;
- `replacement_artifact_manifest_id`;
- `replacement_package_set_authority_id`;
- `package_supersession_commit_id`;
- `source_output_package_id`;
- `package_kind`;
- `package_schema_id`;
- `artifact_ref`;
- `artifact_hash`;
- `authority_basis_hash`;
- `client_request_id`;
- `operator_decision: "record_replacement_package_namespace"`.

Forbidden request fields include package bytes, package payloads, replacement content, generated file bytes, connector destination, provider URL, source upload, source directory, RAG/vector input, qualitative execution instruction, hidden LLM prompt/plan, rendered-control state, and auth/security directives.

## Runtime Authority Basis

The `authority_basis_hash` must include:

- session id;
- source output package id, kind, schema id, payload ref, and payload hash;
- replacement artifact manifest id, authority basis hash, verified ref, and verified hash;
- replacement package-set authority id and basis hash;
- package supersession commit id and lineage hash;
- package kind and package schema id;
- operator decision;
- client request id.

Changing any basis value after a row is recorded must fail closed rather than mutate an existing row.

## Positive Invariants

This runtime is acceptable only if:

- `replacement_package_namespace_rows` is the only new package lifecycle runtime selected;
- rows are created only in `l3_replacement_output_package`;
- existing `L3OutputPackage` rows remain immutable source authority;
- existing source package payload files remain immutable source authority;
- `uq_l3_output_package_session_kind` remains intact;
- every replacement row is bound to an existing verified artifact manifest, replacement package-set authority, supersession commit, source package row, and session;
- duplicate `client_request_id` with the same basis is deterministic;
- duplicate `client_request_id` with a different basis fails closed;
- concurrent duplicate requests create at most one replacement namespace row;
- response contracts expose only response-safe metadata;
- `package_mutation_reconstruction` remains deferred.

## Negative Invariants

This freeze must not accidentally admit:

- runtime behavior outside the exact namespace route and owner service;
- model or migration changes outside `L3ReplacementOutputPackage` and `0021_layer3_replacement_output_package.py`;
- route or DTO changes outside `/api/v1/layer3/package/replacement-namespace/record`;
- replacement package row creation outside `l3_replacement_output_package`;
- source `L3OutputPackage` row creation, update, or deletion;
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

## Required Tests

The implementation must include tests proving:

- migration constraints, unique indexes, and foreign keys exist;
- the API rejects extra fields before service execution;
- namespace rows cannot be created without a verified replacement artifact manifest;
- namespace rows cannot be created without replacement package-set authority;
- namespace rows cannot be created without package supersession commit lineage;
- namespace rows cannot be created without a source `L3OutputPackage` row matching the session and package kind;
- stale manifest authority fails closed;
- stale replacement package-set authority fails closed;
- stale supersession lineage fails closed;
- stale source package authority fails closed;
- manifest ref/hash mismatch fails closed;
- source payload ref reuse as a replacement artifact fails closed;
- duplicate `client_request_id` same basis returns the recorded row deterministically;
- duplicate `client_request_id` different basis fails closed;
- concurrent duplicate requests create one replacement namespace row;
- no source `L3OutputPackage` row is created, updated, or deleted;
- no package payload file is created, rewritten, overwritten, deleted, or reconstructed;
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
- using artifact manifest metadata without package supersession lineage;
- dispatching to connectors or destinations;
- creating provider/public URLs;
- widening source/upload/local-directory/RAG/vector inputs;
- broad qualitative, hybrid, or RAG execution;
- full mockup activation;
- authentication/security work while that lane remains deferred.

## Acceptance Criteria

This bounded runtime is accepted when:

- this file exists and contains `selected_package_lifecycle_mode: replacement_package_namespace_rows`;
- this file preserves `selected_namespace_design: separate_replacement_output_package_table`;
- this file names the route, owner service, model, table, migration, request DTO, response DTO, idempotency basis, stale-authority behavior, and required tests;
- `105_deferred-gates.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md` classify `replacement_package_namespace_rows` as a live bounded runtime while keeping broad package mutation/reconstruction blocked;
- `tools/l3-progress-check.py` fails closed if this runtime contract is missing, if the contract terms are missing, if `uq_l3_output_package_session_kind` is not preserved, or if broad package mutation/reconstruction is accidentally marked admitted;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` reports no whitespace errors.
