# 652 - Replacement Package Artifact Manifest Request Authority Source Selection Freeze

## Status

Status: implementation-entry freeze only for `server_computed_replacement_package_artifact_manifest_record_from_authority`.

Doc: `652_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUEST_AUTHORITY_SOURCE_SELECTION_FREEZE.md`.

Predecessor doc: `651_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUEST_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `d300b8b4a18f47ff14e78fb5159979859c4ae735`.

Selected surface: `package_mutation_reconstruction`.

Selected request-authority source: `server_computed_replacement_package_artifact_manifest_record_from_materialization_authority`.

Selected operator action: `record_replacement_package_artifact_manifest_from_authority`.

Selected implementation-entry mode: `server_computed_replacement_package_artifact_manifest_record_from_authority`.

Future owner service: `backend/app/services/layer3_replacement_package_artifact_manifest.py`.

Future route: `/api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`.

Runtime status in this pass: `not_implemented`.

Entry decision: `freeze_only`.

## Selection Decision

Current main requires one governed request-authority source before `/review/layer3` can safely offer a replacement package artifact manifest submit control.

The selected source is a server-computed manifest record-from-authority runtime. A future implementation may accept only stable server-owned authority identifiers and basis hashes from the rendered page, then fetch the existing replacement artifact materialization row, replacement package-set authority row, and package supersession commit row server-side. It must verify replacement artifacts server-side, compute `artifact_manifest_hash`, compute `authority_basis_hash`, and record the durable `L3ReplacementPackageArtifactManifest` row without requiring the browser to supply raw artifact refs, replacement artifact hashes, byte sizes, local paths, URLs, package bytes, or manifest hashes.

This source is selected over a prepare-only helper because a prepare-only helper would still leave a second browser submit shape that either echoes server-local refs/hashes or requires another request-shape freeze before the durable manifest can be recorded. This selected source is the narrower direct path to the required end-to-end package lifecycle state: one server-owned manifest record operation from existing materialization, replacement authority, and supersession commit authority.

## Required Future Runtime Shape

A future implementation may include only:

- strict request DTO: `Layer3ReplacementPackageArtifactManifestFromAuthorityRequest`;
- strict response DTO: `Layer3ReplacementPackageArtifactManifestFromAuthorityResponse`;
- owner service: `backend/app/services/layer3_replacement_package_artifact_manifest.py`;
- route: `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`;
- schema id: `layer3.replacement_package_artifact_manifest_from_authority.v1`;
- operator decision: `record_replacement_package_artifact_manifest_from_authority`;
- source authority: existing session, plan, pass, reconciliation, `replacement_artifact_materialization_id`, `materialization_basis_hash`, `replacement_package_set_authority_id`, `replacement_authority_basis_hash`, `package_supersession_commit_id`, and `package_supersession_commit_basis_hash`;
- existing server-owned artifact namespace: `replacement-package-artifacts`;
- hash algorithm: `sha256`;
- durable output: existing `L3ReplacementPackageArtifactManifest` only;
- idempotency: same `client_request_id` and same computed authority basis returns the existing manifest; same `client_request_id` and different computed basis fails closed; same computed basis with a new `client_request_id` returns existing manifest status;
- response authority: response-safe manifest status with `artifact_manifest_hash`, `authority_basis_hash`, verified artifact count, verified byte-size basis, and redacted artifact refs only.

The future runtime must not require or accept `replacement_payload_refs`, `replacement_payload_hashes`, `artifact_manifest_hash`, `authority_basis_hash`, browser-supplied byte sizes, browser-supplied package bytes, browser-supplied artifact bytes, arbitrary local paths, URLs, connector ids, destination ids, credentials, provider URLs, source-upload widening, qualitative instructions, RAG/vector settings, or frontend-durable state.

## Required Future Fields

The future request must require at least:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `replacement_artifact_materialization_id`;
- `materialization_basis_hash`;
- `replacement_package_set_authority_id`;
- `replacement_authority_basis_hash`;
- `package_supersession_commit_id`;
- `package_supersession_commit_basis_hash`;
- `operator_decision`.

The future response must preserve at least:

- `replacement_package_artifact_manifest_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `replacement_artifact_materialization_id`;
- `materialization_basis_hash`;
- `replacement_package_set_authority_id`;
- `replacement_authority_basis_hash`;
- `package_supersession_commit_id`;
- `package_supersession_commit_basis_hash`;
- `artifact_manifest_hash`;
- `authority_basis_hash`;
- `artifact_namespace`;
- `hash_algorithm`;
- `verified_artifact_count`;
- `verified_artifact_byte_sizes`;
- `redacted_artifact_refs`;
- `operator_decision`;
- `status`;
- `created_at`;
- `updated_at`.

Raw local filesystem paths must not be exposed in the new API response or rendered UI. Existing server-owned raw refs may be read only inside the backend from existing durable rows.

## Positive Invariants

This selected request-authority lane is acceptable only when:

- it is the only selected request-authority source after `651_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUEST_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC.md`;
- `rendered_replacement_package_artifact_manifest_control` remains blocked until this server-computed record-from-authority source is implemented and proven;
- replacement artifact materialization remains the source of server-owned replacement artifact refs and hashes;
- replacement package-set authority remains the source of replacement package-set lineage;
- package supersession commit remains the source of package lifecycle lineage;
- manifest hash and authority basis hash are computed by the server, not supplied by the browser;
- raw local refs are never exposed by the new response or rendered status;
- existing `L3OutputPackage` rows remain immutable source authority;
- existing source and replacement artifact files remain immutable input authority;
- no replacement namespace rows, package rebuild, package payload rewrite, downstream invalidation, re-delivery runtime, real connector invocation, connector-run creation, destination write, credentials, provider-public delivery/use, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, frontend-durable authority, arbitrary path, arbitrary URL, or browser/operator path editing is admitted.

## Negative Invariants

This freeze must not accidentally admit:

- implementation in this pass;
- rendered UI control in this pass;
- modifying the existing caller-supplied `/api/v1/layer3/package/replacement-artifact/manifest/record` request contract in this pass;
- browser-supplied replacement artifact refs or hashes;
- browser-supplied artifact manifest hashes or authority basis hashes;
- browser-supplied byte sizes, package bytes, replacement bytes, or artifact bytes;
- raw local path exposure in the new response or rendered UI;
- package row mutation;
- source `L3OutputPackage` row mutation;
- source package payload rewrite, overwrite, deletion, or reconstruction;
- replacement output package namespace rows;
- downstream invalidation;
- re-delivery runtime;
- connector or destination dispatch;
- provider-public delivery/use;
- raw public URL exposure;
- credentials;
- external network egress;
- source expansion;
- RAG/vector behavior;
- broad qualitative/hybrid execution;
- full mockup activation;
- auth/security implementation;
- frontend-durable authority.

## Required Future Validation

A future implementation must prove:

- missing materialization authority fails closed;
- stale materialization id or `materialization_basis_hash` fails closed;
- stale replacement package-set authority id or `replacement_authority_basis_hash` fails closed;
- stale package supersession commit id or `package_supersession_commit_basis_hash` fails closed;
- wrong session, analysis plan, pass, or reconciliation fails closed;
- missing replacement artifact file fails closed;
- replacement artifact hash mismatch fails closed;
- outside-namespace replacement artifact ref fails closed;
- unsupported operator decision fails closed;
- forbidden browser-provided refs, hashes, byte sizes, artifact bytes, package bytes, paths, or URLs fail closed;
- duplicate `client_request_id` with same computed basis is deterministic;
- duplicate `client_request_id` with different computed basis conflicts fail closed;
- same computed basis with a new `client_request_id` returns existing manifest status;
- new response and rendered status do not expose raw local filesystem paths;
- existing `L3OutputPackage` rows remain unchanged;
- existing source package and replacement artifact files remain unchanged;
- no replacement namespace rows are recorded;
- no connector-run, destination write, provider-public delivery/use, source expansion, RAG/vector, auth/security, full mockup, or frontend-durable behavior is created.

## Required Validation

This branch must pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

No headed/headless E2E run is required for this freeze-only selection because no rendered behavior is changed.

## Next Posture

The next required action after merge is `current_main_sync_replacement_package_artifact_manifest_request_authority_source_selection_freeze`.

After current-main sync, the next exact posture is `implement_server_computed_replacement_package_artifact_manifest_record_from_authority_after_selection_sync`.
