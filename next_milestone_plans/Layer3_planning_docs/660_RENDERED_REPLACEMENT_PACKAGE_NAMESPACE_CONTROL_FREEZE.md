# 660 - Rendered Replacement Package Namespace Control Freeze

## Status

Status: implementation-entry freeze only for `rendered_replacement_package_namespace_control`.

Doc: `660_RENDERED_REPLACEMENT_PACKAGE_NAMESPACE_CONTROL_FREEZE.md`.

Predecessor current-main sync: `659_RENDERED_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_CONTROL_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `b7320cf0ab12ed2e1102b5e513cc839113bb2a37`.

Selected surface: `package_mutation_reconstruction`.

Selected exact operator action: `record_replacement_package_namespace_row`.

Selected implementation-entry mode: `rendered_replacement_package_namespace_control`.

Existing backend surface: `POST /api/v1/layer3/package/replacement-namespace/record`.

Owner service already live: `backend/app/services/layer3_replacement_package_namespace.py`.

Server runtime mode already live: `replacement_package_namespace_rows`.

Source gate: `131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE`.

Layer 3 placement: Data Structuring & Processing package lifecycle boundary.

Entry decision: `freeze_only`.

Runtime status: `not_implemented_in_this_pass`.

## Selected Slice

A future rendered `/review/layer3` package review control may expose a bounded `Record Namespace` submit action and read-only status/history panel for the existing replacement namespace API runtime.

The future rendered control may call exactly one route:

1. `POST /api/v1/layer3/package/replacement-namespace/record`.

The future control must submit one package-kind namespace row per operator submit. It must not add a bulk endpoint, automatic background sweep, package row mutation, package payload write, package rebuild, package payload rewrite, or replacement artifact generation.

The future control may derive request authority only from existing server responses:

- `State.replacementPackageArtifactManifest`;
- `State.replacementPackageSetAuthority`;
- `State.packageSupersessionCommit`;
- existing source package row authority exposed through package construction, review submit, supersession preview, replacement package-set authority, or package supersession commit state.

The rendered status surface may persist only response-safe `State.replacementPackageNamespace` state, plus response-safe status/history for the selected package-kind row. It must not become durable frontend authority.

## Future Request Boundary

The future rendered namespace payload may submit only:

- `client_request_id`;
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
- `operator_decision`.

The future rendered control may map `package_schema_id` only from the repo-owned package-kind mapping:

- `canonical_internal` -> `layer3.canonical_internal_package.v1`;
- `user_facing` -> `layer3.user_facing_package.v1`;
- `review_facing` -> `layer3.review_facing_package.v1`.

The future rendered control may compute `authority_basis_hash` only from the exact `replacement_package_namespace_authority_basis_hash` basis already enforced by `backend/app/services/layer3_replacement_package_namespace.py`. If browser SHA-256 support is unavailable or the current rendered state cannot reproduce that server basis, the implementation must fail closed or stop for a separate server-computed request-authority freeze. It must not submit guessed, operator-entered, or browser-edited authority hashes.

## Future Rendered Identifiers

The future implementation may introduce:

- `REPLACEMENT_PACKAGE_NAMESPACE_RENDERED_MODE = rendered_replacement_package_namespace_control`;
- `REPLACEMENT_PACKAGE_NAMESPACE_USE_CASE = operator_records_replacement_package_namespace_row_from_manifest_authority`;
- `REPLACEMENT_PACKAGE_NAMESPACE_RESPONSE_AUTHORITY = State.replacementPackageNamespace`;
- `REPLACEMENT_PACKAGE_NAMESPACE_OPERATOR_DECISION = record_replacement_package_namespace`;
- `#replacement-package-namespace-submit`;
- `#replacement-package-namespace-panel`.

The future rendered panel may display unavailable, ready, recording, recorded, already-recorded, and failed states. It may display only response-safe ids, package kind, package schema id, redacted `artifact://replacement-package-artifacts/...` refs, artifact hash, authority basis hash, disabled capability flags, deferred downstream locks, and redacted failure codes.

## Non-Admission Boundary

This freeze does not implement runtime or rendered behavior.

This freeze does not admit backend route changes, DTO changes, response model changes, service behavior changes, database model changes, migrations, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, source package row reuse, weakening `uq_l3_output_package_session_kind`, replacement artifact generation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, or hidden LLM planning.

The future rendered control may use only server-returned artifact refs/hashes from `State.replacementPackageArtifactManifest`. It may not let the browser, operator, URL, local path, file input, or hidden state provide replacement artifact refs, package payload refs, package bytes, artifact bytes, destination ids, destination URLs, connector ids, provider URLs, source ids, RAG/vector ids, or auth/security directives.

## Required Proof For Future Implementation

The future implementation must include static and headed/headless E2E proof covering:

- the rendered button, panel, rendered mode, payload builder, endpoint call, operator decision, ready state, and panel renderer;
- request allowlist contains only the future request boundary fields;
- per-package-kind row submit uses one package kind at a time;
- `authority_basis_hash` matches the server namespace basis for the selected package kind;
- failure-state projection for stale authority or basis mismatch;
- same-key replay returns existing response-safe status;
- same-key conflict fails closed;
- same manifest/package-kind duplicate returns existing status if identical and fails closed if conflicting;
- source `L3OutputPackage` rows are not created, updated, or deleted;
- package payloads are not written, rewritten, overwritten, generated, or deleted;
- no package rebuild or package payload rewrite behavior begins;
- no replacement namespace row is created from browser-edited refs, hashes, package bytes, paths, URLs, or destination fields;
- no handoff/export, direct connector, provider-public, source expansion, RAG/vector, auth/security, or frontend-durable authority behavior is triggered.

## Required Validation

This freeze branch must pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

No headed/headless E2E run is required for this freeze because it records an implementation-entry decision and changes only planning/control metadata.

## Next Posture

After this freeze merges, a current-main sync must record the PR, checks, comments, reviews, reviewThreads, merge commit, validation, and next posture.

The next required action after merge is `current_main_sync_rendered_replacement_package_namespace_control_freeze`.

The next exact posture is `await_current_main_sync_for_rendered_replacement_package_namespace_control_freeze`.

After that current-main sync, the next implementation pass may implement only the rendered replacement namespace control admitted here. If implementation proves the browser cannot assemble the exact server namespace basis from response-safe authority without arbitrary refs/hashes or frontend-durable authority, the next required posture is `select_server_computed_replacement_package_namespace_request_authority_after_freeze_sync`.
