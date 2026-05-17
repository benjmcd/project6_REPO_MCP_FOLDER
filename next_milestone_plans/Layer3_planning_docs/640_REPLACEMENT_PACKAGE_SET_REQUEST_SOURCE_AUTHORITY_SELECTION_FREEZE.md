# 640 - Replacement Package-Set Request Source Authority Selection Freeze

## Status

Status: implementation-entry freeze only for `server_owned_replacement_package_artifact_materialization_request_source`.

Doc: `640_REPLACEMENT_PACKAGE_SET_REQUEST_SOURCE_AUTHORITY_SELECTION_FREEZE.md`.

Predecessor doc: `639_REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUEST_SOURCE_AUTHORITY_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `62f587b0642e9b472e2d476ece96f5c68269e718`.

Selected surface: `package_mutation_reconstruction`.

Selected request-source authority: `server_owned_replacement_package_artifact_materialization_from_supersession_preview`.

Selected operator action: `materialize_replacement_package_artifacts_from_supersession_preview`.

Selected implementation-entry mode: `server_owned_replacement_package_artifact_materialization_request_source`.

Future owner service: `backend/app/services/layer3_replacement_package_materialization.py`.

Future route: `/api/v1/layer3/package/replacement-artifact/materialize`.

Runtime status in this pass: `not_implemented`.

Entry decision: `freeze_only`.

## Selection Decision

Current main requires one governed server-owned source for replacement package-set request fields before the rendered replacement package-set authority control can be implemented.

The selected source is a server-owned replacement artifact materialization runtime that derives replacement artifact refs and hashes from existing package supersession preview authority and existing immutable package rows, then writes only into a separate server-owned replacement artifact namespace. The runtime may later return the exact fields needed by `/api/v1/layer3/package/replacement-set/record`:

- `replacement_package_set_id`;
- `replacement_package_set_hash`;
- `replacement_package_kinds`;
- `replacement_payload_refs`;
- `replacement_payload_hashes`;
- `authority_basis_hash`.

This source is selected over `replacement_package_artifact_manifest_only` because the current manifest runtime is downstream of `L3ReplacementPackageSetAuthority` and `L3PackageSupersessionCommit`; it cannot be the missing upstream request-source authority. It is selected over browser/operator path editing because caller-supplied paths, arbitrary refs, URLs, and package bytes remain forbidden.

## Required Future Runtime Shape

A future implementation may include only:

- strict request DTO: `Layer3ReplacementPackageArtifactMaterializationRequest`;
- strict response DTO: `Layer3ReplacementPackageArtifactMaterializationResponse`;
- owner service: `backend/app/services/layer3_replacement_package_materialization.py`;
- route: `POST /api/v1/layer3/package/replacement-artifact/materialize`;
- schema id: `layer3.replacement_package_artifact_materialization.v1`;
- operator decision: `materialize_replacement_package_artifacts_from_supersession_preview`;
- source authority: existing session, plan, pass, reconciliation, package supersession preview hash, source package set hash, source package ids/kinds/refs/hashes, package review construction authority, and server-owned package artifact storage root;
- artifact namespace: server-owned `replacement-package-artifacts`;
- hash algorithm: `sha256` over canonical replacement artifact bytes;
- idempotency: same `client_request_id` and same materialization basis returns the same materialization receipt; same `client_request_id` and different basis fails closed; same basis with a new `client_request_id` returns the existing materialization status;
- response authority: response-safe materialization receipt with replacement refs/hashes and computed replacement package-set authority basis fields.

The future runtime must not require or accept browser-supplied artifact refs, browser-supplied package bytes, browser-supplied replacement payload hashes, arbitrary local paths, URLs, connector ids, destination ids, credentials, provider URLs, source-upload widening, qualitative instructions, RAG/vector settings, or frontend-durable state.

## Required Future Fields

The future materialization request must require at least:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `package_supersession_preview_hash`;
- `source_package_set_hash`;
- `source_output_package_ids`;
- `source_package_kinds`;
- `source_payload_refs`;
- `source_payload_hashes`;
- `operator_decision`.

The future materialization response must preserve at least:

- `replacement_artifact_materialization_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `package_supersession_preview_hash`;
- `source_package_set_hash`;
- `source_output_package_ids`;
- `source_package_kinds`;
- `source_payload_refs`;
- `source_payload_hashes`;
- `replacement_package_set_id`;
- `replacement_package_set_hash`;
- `replacement_package_kinds`;
- `replacement_payload_refs`;
- `replacement_payload_hashes`;
- `authority_basis_hash`;
- `materialization_basis_hash`;
- `operator_decision`;
- `status`;
- `created_at`;
- `updated_at`.

Raw local filesystem paths must not be exposed in rendered UI. API responses may carry server-owned refs only as authority inputs for subsequent server calls; rendered surfaces must display redacted refs.

## Positive Invariants

This selected source-authority lane is acceptable only when:

- it is the only selected request-source authority after `639_REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUEST_SOURCE_AUTHORITY_CURRENT_MAIN_SYNC.md`;
- `rendered_replacement_package_set_authority_control` remains blocked until this materialization source is implemented and proven;
- existing `L3OutputPackage` rows remain immutable source authority;
- existing source package payload files remain immutable source authority;
- replacement artifacts are written only into a server-owned replacement artifact namespace;
- replacement package-set request fields are computed by the server, not supplied by the browser;
- replacement package-set authority remains a separate durable authority record consumed after materialization;
- package supersession commit remains lineage-only and is not admitted by this selection;
- replacement artifact manifest and replacement namespace rows remain downstream surfaces and are not used to bypass materialization;
- no real connector invocation, connector-run creation, destination write, credentials, provider-public delivery/use, source expansion, RAG/vector behavior, broad qualitative behavior, full mockup activation, auth/security behavior, frontend-durable authority, arbitrary path, arbitrary URL, or browser/operator path editing is admitted.

## Negative Invariants

This freeze must not accidentally admit:

- implementation in this pass;
- rendered UI control in this pass;
- package supersession commit control;
- package row mutation;
- source `L3OutputPackage` row mutation;
- source package payload rewrite, overwrite, deletion, or reconstruction;
- browser-provided package bytes or edited package content;
- browser-provided replacement refs or hashes;
- arbitrary caller-supplied local paths or URLs;
- replacement output package namespace rows;
- replacement artifact manifest recording before materialization exists;
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

- stale package supersession preview hash fails closed;
- stale source package set hash fails closed;
- stale source package ids, kinds, refs, or hashes fail closed;
- missing source package payload ref fails closed;
- unsupported operator decision fails closed;
- forbidden browser-provided package bytes fail closed;
- forbidden browser-provided replacement refs/hashes fail closed;
- arbitrary path or URL fields fail closed;
- duplicate `client_request_id` with same basis is deterministic;
- duplicate `client_request_id` with different basis conflicts fail closed;
- same basis with a new `client_request_id` returns existing status;
- existing `L3OutputPackage` rows are unchanged;
- existing source package payload files are unchanged;
- no replacement package-set authority is recorded by materialization itself;
- no package supersession commit is recorded by materialization itself;
- no replacement artifact manifest or namespace row is recorded by materialization itself;
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

The next required action after merge is `current_main_sync_replacement_package_set_request_source_authority_selection_freeze`.

After current-main sync, the next exact posture is `implement_server_owned_replacement_package_artifact_materialization_request_source_after_selection_sync`.
