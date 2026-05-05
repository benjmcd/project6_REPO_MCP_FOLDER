# Layer 3 Replacement Package Artifact Manifest Freeze

Status: implementation-entry freeze only for `replacement_package_artifact_manifest_only`. No runtime behavior is admitted by this document.

This artifact satisfies the next-selection requirement in `128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md` by choosing exactly one replacement artifact authority mode: record a server-verified immutable manifest for replacement package payload refs and hashes, without generating replacement payload files, creating replacement `L3OutputPackage` rows, mutating source package rows, or rewriting package payloads.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- baseline_ref: `project6-origin/main`
- baseline_commit: `156e18517352d844da43afa457264908a6c2f525`
- predecessor planning/control freeze: `128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md`
- predecessor live metadata authority: `127_PACKAGE_REPLACEMENT_SET_FREEZE.md`
- predecessor live lineage authority: `126_PACKAGE_COMMIT_FREEZE.md`
- selected_package_artifact_authority_mode: `replacement_package_artifact_manifest_only`
- future runtime route: `/api/v1/layer3/package/replacement-artifact/manifest/record`
- future owner service: `backend/app/services/layer3_replacement_package_artifact_manifest.py`
- future authority model: `L3ReplacementPackageArtifactManifest`
- future migration: `0020_layer3_replacement_package_artifact_manifest.py`
- current package row authority: `backend/app/models/models.py` `L3OutputPackage`
- current uniqueness blocker: `uq_l3_output_package_session_kind` keeps one output package per `(session_id, package_kind)`
- evidence boundary: live source/tests and `tools/l3-progress-check.py` outrank this document

## Decision

The next package artifact authority implementation-entry mode is narrowed to exactly:

- selected_package_artifact_authority_mode: `replacement_package_artifact_manifest_only`

This mode may only record that replacement package artifact refs named by an existing `L3ReplacementPackageSetAuthority` have been server-verified against their claimed payload hashes. It must not create, rewrite, upload, or reconstruct package bytes.

The future runtime must be manifest-only. It may create only an immutable manifest authority record after server-side verification succeeds. It must fail closed when replacement payload refs are missing, unreadable, outside the allowed replacement artifact namespace, reused from source payload refs, hash-mismatched, stale relative to the replacement package-set authority, or stale relative to the package supersession lineage state.

## Why Manifest-Only Outranks Generation Or Rows

`replacement_package_artifact_generation_only` and `replacement_package_namespace_rows` remain too broad for the next step because they introduce payload writing or package-row namespace questions. Manifest-only authority reduces risk first by proving whether the already-declared replacement refs/hashes are real, server-readable, immutable inputs before any generation or row-creation behavior is considered.

This keeps current source package rows and payloads immutable while establishing the missing proof layer between metadata-only replacement package-set authority and any later package reconstruction lane.

## Required Future Contract

A later implementation PR for this freeze must define:

- request DTO: `Layer3ReplacementPackageArtifactManifestRequest`
- response DTO: `Layer3ReplacementPackageArtifactManifestResponse`
- schema id: `layer3.replacement_package_artifact_manifest.v1`
- operator decision: `record_replacement_package_artifact_manifest`
- source gate: `129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE`
- exact server-side artifact namespace allowlist;
- exact path/ref canonicalization rule;
- exact hash algorithm: SHA-256 over canonical artifact bytes;
- exact relation to `L3ReplacementPackageSetAuthority`;
- exact relation to `L3PackageSupersessionCommit`;
- immutable manifest id and `artifact_manifest_hash` basis;
- deterministic duplicate `client_request_id` behavior;
- concurrent duplicate behavior;
- stale replacement authority, stale source package, stale lineage, stale ref, stale hash, and missing file behavior;
- response-safe receipt fields and next allowed actions.

## Minimum Future Fields

A future manifest record must preserve at least:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `reconciliation_record_id`
- `replacement_package_set_authority_id`
- `replacement_package_set_id`
- `replacement_package_set_hash`
- `replacement_package_kinds`
- `replacement_payload_refs`
- `replacement_payload_hashes`
- `verified_artifact_refs`
- `verified_artifact_hashes`
- `verified_artifact_byte_sizes`
- `hash_algorithm`
- `artifact_namespace`
- `artifact_manifest_hash`
- `authority_basis_hash`
- `operator_decision`
- `status`

## Positive Invariants

The future runtime slice is acceptable only if:

- `replacement_package_artifact_manifest_only` is the only selected artifact authority mode;
- `package_mutation_reconstruction` remains deferred;
- existing `L3OutputPackage` rows remain immutable source authority;
- existing source package payload files remain immutable source authority;
- `replacement_package_set_authority` remains metadata-only until this manifest authority exists;
- manifest authority verifies replacement refs and hashes server-side before recording an immutable manifest;
- replacement package artifacts are server-side manifest verified before replacement refs/hashes are treated as reconstructable package content;
- manifest authority lives in a separate model/table from `L3OutputPackage`;
- no replacement `L3OutputPackage` rows are created;
- no replacement package payload files are created or rewritten;
- no browser-provided package bytes are accepted;
- package supersession commit remains lineage-only until a later freeze explicitly admits stronger package lifecycle behavior;
- future responses expose only response-safe manifest ids, refs, hashes, schema ids, status, and next actions.

## Negative Invariants

This freeze must not accidentally admit:

- replacement package artifact generation;
- replacement `L3OutputPackage` row creation;
- package row creation, update, or deletion;
- package payload creation, rewrite, overwrite, deletion, or reconstruction;
- package payload bytes accepted from the browser;
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

A future implementation must prove:

- missing replacement artifact manifest fails closed before package-set authority can be treated as reconstructable package content;
- missing replacement payload ref fails closed;
- unreadable replacement payload ref fails closed;
- replacement payload hash mismatch fails closed;
- replacement artifact refs cannot reuse source payload refs;
- replacement refs outside the allowed server artifact namespace fail closed;
- duplicate `client_request_id` behavior is deterministic;
- concurrent duplicate requests cannot create duplicate manifest authority records;
- existing `L3OutputPackage` rows are unchanged;
- existing source package payload files are unchanged;
- existing package construction, package-review submit, handoff/export, APS handoff, external export/download, signed-reference, internal connector record, replacement package-set authority, and package supersession commit behavior are unchanged;
- no provider/public URL, connector/destination dispatch, source expansion, qualitative/hybrid/RAG execution, full mockup activation, or auth/security behavior is admitted.

## Stop Conditions

Stop before implementation if the intended change requires:

- generating replacement package payload bytes;
- accepting package bytes or edited package content from the browser;
- weakening `uq_l3_output_package_session_kind`;
- creating replacement package rows;
- mutating existing `L3OutputPackage` rows;
- rewriting, deleting, or reconstructing existing source package payload files;
- using `replacement_package_set_authority` metadata as proof without server-side artifact verification;
- dispatching to connectors or destinations;
- creating provider/public URLs;
- widening source/upload/local-directory/RAG/vector inputs;
- broad qualitative, hybrid, or RAG execution;
- full mockup activation;
- authentication/security work while that lane remains deferred.

## Acceptance Criteria

This implementation-entry freeze is accepted when:

- this file exists and contains `selected_package_artifact_authority_mode: replacement_package_artifact_manifest_only`;
- `105_deferred-gates.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md` keep broad package mutation/reconstruction blocked while naming this manifest-only prerequisite;
- `tools/l3-progress-check.py` fails closed if this freeze is missing or if manifest-only authority is represented as live runtime before implementation;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` reports no whitespace errors.
