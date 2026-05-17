# 718 - Corrected Artifact Replacement Namespace Authority Freeze

## Status

Status: implementation-entry freeze for `corrected_artifact_replacement_namespace_authority`.

Doc: `718_CORRECTED_ARTIFACT_REPLACEMENT_NAMESPACE_AUTHORITY_FREEZE.md`.

Predecessor current-main sync: `717_CORRECTED_ARTIFACT_REPLACEMENT_MANIFEST_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before freeze: `3d60756b94cc6d95f868db6db7d042a9a45f3c46`.

Freeze branch: `codex/l3-corrected-artifact-namespace-freeze`.

Selected surface: `package_mutation_reconstruction`.

Selected package lifecycle action: `rebuild_package_from_corrected_artifacts`.

Selected downstream authority bridge: `server_computed_replacement_namespace_from_corrected_artifact_manifest_authority`.

Frozen route: `POST /api/v1/layer3/package/replacement-namespace/record-from-corrected-artifact-manifest-authority`.

Owner service frozen: `backend/app/services/layer3_replacement_package_namespace.py`.

API owner frozen: `backend/app/api/layer3.py`.

Durable target frozen: `L3ReplacementOutputPackage` / `l3_replacement_output_package`.

Required source authority frozen: `L3CorrectedPackageArtifactSet`.

Required replacement authority frozen: `L3ReplacementPackageSetAuthority`.

Required supersession authority frozen: `L3PackageSupersessionCommit`.

Required manifest authority frozen: `L3ReplacementPackageArtifactManifest`.

Request mode frozen: `replacement_package_namespace_from_corrected_artifact_manifest_authority`.

Operator decision frozen: `record_replacement_package_namespace_from_corrected_artifact_manifest_authority`.

Runtime behavior in this freeze: `false`.

## Current-Main Evaluation

Current main already contains `POST /api/v1/layer3/package/replacement-namespace/record`, `backend/app/services/layer3_replacement_package_namespace.py`, and the durable `L3ReplacementOutputPackage` table.

That existing route is not sufficient for the corrected-artifact end-to-end path because it requires caller-supplied `source_output_package_id`, `package_kind`, `package_schema_id`, response-safe `artifact_ref`, `artifact_hash`, and `authority_basis_hash` for one package row at a time.

The corrected-artifact manifest runtime synced by Doc `717_CORRECTED_ARTIFACT_REPLACEMENT_MANIFEST_RUNTIME_CURRENT_MAIN_SYNC.md` now gives current main enough server-side authority to derive those values from `L3CorrectedPackageArtifactSet`, corrected-artifact `L3ReplacementPackageSetAuthority`, corrected-artifact `L3PackageSupersessionCommit`, and `L3ReplacementPackageArtifactManifest`.

The existing `l3_replacement_output_package` table has a unique `client_request_id` per row, so the future complete-set bridge must not reuse the top-level request id across all package kinds. It must derive deterministic per-kind row idempotency keys from the top-level `client_request_id` and `package_kind`, while treating the top-level request as the replay/conflict basis for the complete namespace set.

## Frozen Implementation Entry

The later implementation may add exactly one server-computed namespace bridge that:

- accepts top-level authority ids and basis hashes only;
- verifies one complete corrected-artifact package authority chain;
- derives source output package ids, package kinds, package schema ids, response-safe artifact refs, artifact hashes, and per-row authority basis hashes server-side;
- records or replays one `L3ReplacementOutputPackage` row per replacement package kind in the existing `l3_replacement_output_package` table;
- derives deterministic per-kind row `client_request_id` values from the top-level `client_request_id` and package kind;
- returns a response-safe namespace-set summary with replacement output package ids and redacted `artifact://replacement-package-artifacts/...` refs; and
- reuses existing namespace row constraints without weakening `uq_l3_output_package_session_kind` or mutating source `L3OutputPackage` rows.

The frozen request may include only:

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
- `package_supersession_commit_basis_hash`;
- `replacement_artifact_manifest_id`;
- `replacement_artifact_manifest_authority_basis_hash`; and
- `operator_decision`.

The implementation must reject caller-supplied source output package ids, package kinds, package schema ids, artifact refs, artifact hashes, authority basis hashes, package payloads, package bytes, source package mutation fields, namespace row ids, replacement activation fields, connector or destination fields, credentials, paths, URLs, source expansion fields, RAG/vector fields, auth/security fields, rendered UI state, browser state, retry/rerun/cancel fields, and hidden LLM planning fields.

## Required Proof

The later implementation must prove:

- success records or replays exactly the complete replacement namespace set derived from corrected-artifact manifest authority;
- same top-level `client_request_id` plus same authority basis returns the same namespace set;
- same top-level `client_request_id` plus different authority basis fails closed;
- same authority basis plus new top-level `client_request_id` returns existing namespace rows rather than duplicating output;
- stale corrected artifact set, replacement authority, supersession commit, or manifest basis fails closed;
- wrong session, analysis plan, pass run, reconciliation record, source package, package kind vector, source vector, replacement vector, or manifest vector fails closed;
- duplicate per-kind target row with identical authority replays;
- duplicate per-kind target row with conflicting authority fails closed;
- response refs are redacted and no raw local paths are exposed;
- source `L3OutputPackage` rows are not mutated;
- no package payload rewrite or package payload write occurs;
- no package activation row is created;
- no handoff/export rerun or delivery rerun occurs;
- no connector dispatch, destination write, `ConnectorRun`, or `ConnectorRunTarget` is created;
- no credentials, provider-public delivery/use, network egress, source expansion, RAG/vector behavior, auth/security behavior, rendered UI authority, frontend-durable authority, or hidden LLM planning is introduced; and
- targeted API/service tests cover success, replay, conflict, stale authority, forbidden fields, redaction, and disabled side effects.

## Non-Admission Boundary

This freeze admits no runtime behavior by itself. Package replacement activation, package payload rewrite, package payload writes, source `L3OutputPackage` mutation, downstream invalidation, handoff/export rerun, delivery rerun, provider-public delivery/use, connector/destination dispatch, `ConnectorRun` creation, `ConnectorRunTarget` creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, rendered UI authority, caller-supplied arbitrary paths or URLs, browser-supplied refs/hashes/bytes, raw local path exposure, and hidden LLM planning remain blocked.

## Next Posture

The next exact posture after merge is `current_main_sync_corrected_artifact_replacement_namespace_authority_freeze`.

After that sync, the next exact implementation posture is `implement_server_computed_replacement_namespace_from_corrected_artifact_manifest_authority_after_freeze_sync`.
