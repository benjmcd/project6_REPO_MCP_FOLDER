# 714 - Corrected Artifact Replacement Manifest Authority Freeze

## Status

Status: branch-local implementation-entry freeze for `corrected_artifact_replacement_manifest_from_supersession_authority`.

Doc: `714_CORRECTED_ARTIFACT_REPLACEMENT_MANIFEST_AUTHORITY_FREEZE.md`.

Predecessor current-main sync: `713_CORRECTED_ARTIFACT_PACKAGE_SUPERSESSION_COMMIT_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before freeze: `6884a545d5ea66286af40425be5cfb47027f1ccb`.

Branch: `codex/l3-corrected-artifact-manifest-freeze`.

Selected surface: `package_mutation_reconstruction`.

Selected package lifecycle action: `rebuild_package_from_corrected_artifacts`.

Selected source authority: `operator_review_corrections_server_owned_corrected_package_artifact_set`.

Selected downstream authority bridge: `corrected_artifact_replacement_manifest_from_supersession_authority`.

Entry decision: `freeze_only`.

Runtime behavior in this pass: `false`.

Live behavior change in this pass: `false`.

## Current-Main Evaluation

Current main already contains the generic server-computed manifest route `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`, owned by `backend/app/services/layer3_replacement_package_artifact_manifest.py`.

That existing route is not the correct authority bridge for the corrected-artifact package rebuild path. It requires `replacement_artifact_materialization_id` and validates that `L3ReplacementPackageArtifactMaterialization.authority_basis_hash` matches `L3ReplacementPackageSetAuthority.authority_basis_hash`.

The corrected-artifact path now uses:

- `L3CorrectedPackageArtifactSet` as the server-owned corrected artifact authority;
- `L3ReplacementPackageSetAuthority` with mode `replacement_package_set_authority_from_corrected_artifact_set`;
- `L3PackageSupersessionCommit` produced by `package_supersession_commit_from_corrected_artifact_set_authority`; and
- durable corrected artifact refs/hashes stored in the backend row, with raw refs redacted from operator/API responses.

Because the corrected-artifact replacement authority is derived from `L3CorrectedPackageArtifactSet`, not from the older materialization authority basis, current main still needs a server-computed manifest bridge that reads the corrected artifact set and the corrected-artifact supersession commit authority directly. Reusing the old materialization-gated route would either fail closed on the authority-basis mismatch or force caller/browser-supplied raw refs, which remains forbidden.

## Frozen Later Runtime

This freeze admits only a later backend/API bridge:

`POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-corrected-artifact-set-authority`

The later implementation owner files are:

- service: `backend/app/services/layer3_replacement_package_artifact_manifest.py`;
- API: `backend/app/api/layer3.py`;
- tests: `backend/tests/test_layer3_api.py`; and
- progress checker: `tools/l3-progress-check.py`.

The later runtime may persist only the existing durable target:

- `L3ReplacementPackageArtifactManifest`; and
- `l3_replacement_package_artifact_manifest`.

The later request may accept only these authority identity and basis fields:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `corrected_package_artifact_set_id`;
- `corrected_artifact_basis_hash`;
- `replacement_package_set_authority_id`;
- `replacement_authority_basis_hash`;
- `package_supersession_commit_id`;
- `package_supersession_commit_basis_hash`; and
- `operator_decision`.

The later operator decision is `record_replacement_package_artifact_manifest_from_corrected_artifact_set_authority`.

The later request mode is `replacement_package_artifact_manifest_from_corrected_artifact_set_authority`.

The later implementation must derive replacement package set id, replacement package set hash, package kinds, replacement artifact refs, replacement artifact hashes, verified byte sizes, artifact manifest hash, and manifest authority basis hash server-side from `L3CorrectedPackageArtifactSet`, corrected-artifact `L3ReplacementPackageSetAuthority`, and corrected-artifact `L3PackageSupersessionCommit`.

The later response must redact replacement artifact refs as `artifact://replacement-package-artifacts/...` and must not expose raw local paths.

## Required Guards

The later implementation must fail closed for:

- missing corrected artifact set;
- stale `corrected_artifact_basis_hash`;
- missing replacement package-set authority;
- stale `replacement_authority_basis_hash`;
- replacement package-set authority not produced from corrected artifact set;
- missing package supersession commit;
- stale `package_supersession_commit_basis_hash`;
- supersession commit not produced from corrected artifact authority;
- wrong session, plan, pass, or reconciliation;
- source package vector mismatch;
- corrected package vector mismatch;
- replacement authority vector mismatch;
- supersession commit vector mismatch;
- tampered corrected artifact hash or byte size;
- duplicate `client_request_id` with different authority basis;
- same authority basis with a new `client_request_id`;
- caller-supplied replacement refs, replacement hashes, manifest hash, authority basis hash, byte sizes, artifact namespace, package payload bytes, path, URL, connector, credential, source expansion, RAG/vector, auth/security, browser state, or frontend-durable fields.

## Proof Requirements

The later implementation must add targeted backend/API proof for:

- OpenAPI request schema and workbench error envelope coverage;
- successful manifest record from corrected artifact set authority;
- idempotent same-key replay;
- same-basis/new-key replay;
- redacted response refs and redacted manifest snapshot;
- fail-closed stale corrected artifact basis;
- fail-closed stale replacement authority basis;
- fail-closed stale supersession commit basis;
- fail-closed wrong corrected artifact set versus replacement authority;
- fail-closed wrong supersession commit versus replacement authority;
- fail-closed tampered artifact hash;
- fail-closed caller-supplied path/URL/ref/hash/byte/payload fields;
- no source `L3OutputPackage` mutation;
- no replacement namespace rows;
- no package replacement activation rows;
- no `ConnectorRun` or `ConnectorRunTarget` creation;
- no credentials or network egress;
- no source expansion; and
- no RAG/vector or broad qualitative-hybrid execution.

No headed/headless E2E proof is required for this freeze or later backend/API bridge unless rendered behavior changes.

## Non-Admission Boundary

This freeze admits no runtime behavior by itself. It does not add replacement namespace row creation, package replacement activation, package payload rewrite, source `L3OutputPackage` mutation, downstream invalidation, re-running handoff/export or delivery, provider-public delivery/use, connector/destination dispatch, `ConnectorRun` creation, `ConnectorRunTarget` creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, rendered UI authority, caller-supplied arbitrary paths or URLs, browser-supplied refs/hashes/bytes, raw local path exposure, or hidden LLM planning.

## Next Posture

After this freeze merges, the next exact posture is `current_main_sync_corrected_artifact_replacement_manifest_authority_freeze`.

After current-main sync, the next exact implementation posture is `implement_corrected_artifact_replacement_manifest_from_supersession_authority_after_freeze_sync`.
