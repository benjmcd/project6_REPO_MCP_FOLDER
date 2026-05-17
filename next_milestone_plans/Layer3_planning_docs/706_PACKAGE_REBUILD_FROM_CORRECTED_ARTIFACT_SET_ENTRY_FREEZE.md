# 706 - Package Rebuild From Corrected Artifact Set Entry Freeze

## Status

Status: implementation-entry freeze for `package_rebuild_from_corrected_artifact_set`.

Doc: `706_PACKAGE_REBUILD_FROM_CORRECTED_ARTIFACT_SET_ENTRY_FREEZE.md`.

Predecessor current-main sync: `705_OPERATOR_REVIEW_CORRECTIONS_CORRECTED_PACKAGE_ARTIFACT_SET_RUNTIME_CURRENT_MAIN_SYNC.md`.

Freeze branch: `codex/l3-package-rebuild-corrected-set-freeze`.

Current-main preflight commit: `8168dc2306b2e3f9cf05398ed7ed3be918b80f57`.

Selected surface: `package_mutation_reconstruction`.

Selected package lifecycle action: `rebuild_package_from_corrected_artifacts`.

Selected source authority: `operator_review_corrections_server_owned_corrected_package_artifact_set`.

Selected implementation-entry posture: `freeze_package_rebuild_from_corrected_artifact_set_implementation_entry_after_runtime_sync`.

Implementation-entry decision: `freeze_replacement_package_set_authority_from_corrected_artifact_set_only`.

Runtime behavior change in this pass: false.

Runtime status in this pass: `not_implemented_in_this_pass`.

## Current-Main Authority

Current main now proves a durable corrected package artifact set source authority through:

- route `POST /api/v1/layer3/package/corrected-artifact-set/record`;
- service `backend/app/services/layer3_corrected_package_artifact_set.py`;
- model/table `L3CorrectedPackageArtifactSet` / `l3_corrected_package_artifact_set`;
- migration `backend/alembic/versions/0033_layer3_corrected_package_artifact_set.py`;
- schema id `layer3.corrected_package_artifact_set.v1`;
- request mode `operator_review_corrections_server_owned_corrected_package_artifact_set`; and
- operator decision `record_corrected_package_artifact_set_from_review_corrections`.

The existing downstream package lifecycle already has a proven replacement chain: `L3ReplacementPackageSetAuthority`, package supersession commit, replacement artifact manifest, replacement namespace rows, package replacement activation, and active replacement authority adoption by handoff/export/local delivery surfaces.

## Admitted Later Runtime Slice

This freeze admits only a later replacement package-set authority bridge from the recorded corrected package artifact set:

- route: `POST /api/v1/layer3/package/replacement-set/record-from-corrected-artifact-set`;
- owner service: `backend/app/services/layer3_replacement_package_set_authority.py`;
- API owner: `backend/app/api/layer3.py`;
- durable model/table: `L3ReplacementPackageSetAuthority` / `l3_replacement_package_set_authority`;
- source model/table: `L3CorrectedPackageArtifactSet` / `l3_corrected_package_artifact_set`;
- targeted tests: `backend/tests/test_layer3_replacement_package_set_authority.py` and `backend/tests/test_layer3_api.py`;
- response schema id: `layer3.replacement_package_set_authority.v1`;
- request mode: `replacement_package_set_authority_from_corrected_artifact_set`;
- operator decision: `record_replacement_package_set_authority`.

The later runtime must validate an existing corrected package artifact set id and corrected artifact basis hash, derive replacement package-set id/hash/kinds/payload refs/payload hashes from the corrected artifact set authority, compute the existing replacement package-set authority basis hash server-side, and record or replay an `L3ReplacementPackageSetAuthority` row using the existing table constraint-compatible operator decision.

The later runtime must be idempotent: same `client_request_id` plus same corrected artifact set basis returns the same authority receipt; same `client_request_id` plus different corrected artifact set basis fails closed; same corrected artifact set basis plus a new `client_request_id` returns existing status rather than creating duplicate authority.

The later runtime must fail closed on missing corrected artifact set authority, stale corrected artifact basis hash, wrong session/pass/reconciliation/source package basis, incomplete corrected artifact vectors, corrected artifact hash mismatch, duplicate client-request conflict, missing source package authority, and any caller-supplied package bytes, paths, URLs, diffs, connector/destination fields, source expansion fields, RAG/vector fields, auth/security fields, or frontend-durable state.

## Non-Admission Boundary

This freeze does not admit runtime implementation in this pass, direct source `L3OutputPackage` row mutation, package payload rewrite, package activation, downstream invalidation, handoff/export rerun, replacement namespace row creation, replacement artifact manifest recording, package supersession commit, connector/destination dispatch, `ConnectorRun` creation, `ConnectorRunTarget` creation, credentials, external network egress, provider-public delivery/use, raw public URL exposure, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, raw local path exposure, or hidden LLM planning.

## Required Proof For Later Implementation

The later implementation must prove:

- API boundary error-envelope behavior for `record-from-corrected-artifact-set`;
- OpenAPI request/response contract exposure;
- successful replacement package-set authority recording from an existing corrected package artifact set;
- same-key replay and same-basis/new-key replay;
- same-key/different-basis conflict;
- stale corrected artifact basis hash failure;
- missing corrected artifact set failure;
- wrong session/pass/reconciliation/source package basis failure;
- forbidden package bytes, paths, URLs, diffs, connector/destination, source expansion, RAG/vector, auth/security, and frontend-durable fields failing closed;
- no source `L3OutputPackage` row mutation;
- no replacement namespace rows, package activation rows, `ConnectorRun`, or `ConnectorRunTarget` rows created; and
- response redaction with no raw local path exposure.

## Next Posture

The next exact posture after merge is `current_main_sync_package_rebuild_from_corrected_artifact_set_entry_freeze`.

After sync, the next exact posture is `implement_replacement_package_set_authority_from_corrected_artifact_set_after_entry_freeze_sync`.
