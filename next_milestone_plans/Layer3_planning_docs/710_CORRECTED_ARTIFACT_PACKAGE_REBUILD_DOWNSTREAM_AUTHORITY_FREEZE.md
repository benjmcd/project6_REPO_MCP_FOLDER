# 710 - Corrected Artifact Package Rebuild Downstream Authority Freeze

## Status

Status: implementation-entry freeze after downstream authority evaluation for `package_rebuild_from_corrected_artifact_set`.

Doc: `710_CORRECTED_ARTIFACT_PACKAGE_REBUILD_DOWNSTREAM_AUTHORITY_FREEZE.md`.

Predecessor current-main sync: `709_REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_RUNTIME_CURRENT_MAIN_SYNC.md`.

Freeze branch: `codex/l3-corrected-artifact-downstream-freeze`.

Current-main preflight commit: `02f8145f04bd736bcd3162aeddbaf16cf293e8ce`.

Selected surface: `package_mutation_reconstruction`.

Selected package lifecycle action: `rebuild_package_from_corrected_artifacts`.

Selected source authority: `operator_review_corrections_server_owned_corrected_package_artifact_set`.

Selected downstream bridge: `server_computed_package_supersession_commit_from_corrected_artifact_replacement_authority`.

Selected future route: `POST /api/v1/layer3/package/supersession/commit-from-corrected-artifact-set-authority`.

Future owner service: `backend/app/services/layer3_package_supersession_commit.py`.

Future API owner: `backend/app/api/layer3.py`.

Entry decision: `freeze_only`.

Runtime status in this pass: `not_implemented_in_this_pass`.

## Evaluation Result

Current main now proves the upstream corrected-artifact package rebuild authority chain:

- corrected artifact source authority through `POST /api/v1/layer3/package/corrected-artifact-set/record`;
- corrected-artifact replacement package-set authority through `POST /api/v1/layer3/package/replacement-set/record-from-corrected-artifact-set`;
- durable source model/table `L3CorrectedPackageArtifactSet` / `l3_corrected_package_artifact_set`;
- durable replacement authority model/table `L3ReplacementPackageSetAuthority` / `l3_replacement_package_set_authority`; and
- redacted API responses that do not expose raw local paths.

The current downstream package lifecycle also exists and remains valuable:

- package supersession commit through `POST /api/v1/layer3/package/supersession/commit`;
- replacement artifact manifest through `POST /api/v1/layer3/package/replacement-artifact/manifest/record`;
- server-computed manifest from authority through `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`;
- replacement namespace rows through `POST /api/v1/layer3/package/replacement-namespace/record`;
- package replacement activation through `POST /api/v1/layer3/package/replacement-activation/commit`; and
- downstream active package authority adoption by handoff/export, local receipt, outbox, provider-private handoff, and external local export lanes.

The evaluation found the next missing bridge is not the downstream tables themselves. It is the operator-safe, server-computed package supersession commit bridge for the corrected-artifact replacement authority.

The existing generic `commit_package_supersession` service reads `L3ReplacementPackageSetAuthority`, but its public request contract still requires the caller to supply replacement payload refs and hashes for comparison. The corrected-artifact authority responses intentionally redact those refs. Using the generic public request directly would either require exposing raw local artifact refs to the caller or asking the caller to echo authority data that should remain server-owned.

The existing `record-from-authority` replacement manifest route is also not the next bridge for this corrected-artifact path because it requires an existing `L3ReplacementPackageArtifactMaterialization` row from the older supersession-preview materialization lane. The corrected-artifact path already has corrected artifact refs/hashes through `L3CorrectedPackageArtifactSet` and replacement package-set authority through `L3ReplacementPackageSetAuthority`; it must not be forced through a supersession-preview materialization row that is not its source authority.

## Admitted Later Runtime Slice

This freeze admits only a later server-computed package supersession commit bridge from an existing corrected-artifact replacement package-set authority:

- route: `POST /api/v1/layer3/package/supersession/commit-from-corrected-artifact-set-authority`;
- owner service: `backend/app/services/layer3_package_supersession_commit.py`;
- API owner: `backend/app/api/layer3.py`;
- durable target: `L3PackageSupersessionCommit` / `l3_package_supersession_commit`;
- required upstream authority: `L3ReplacementPackageSetAuthority` recorded with request mode `replacement_package_set_authority_from_corrected_artifact_set`;
- required source authority: `L3CorrectedPackageArtifactSet`;
- response schema id: `layer3.package_supersession_commit.v1`;
- future request mode: `package_supersession_commit_from_corrected_artifact_set_authority`;
- operator decision: `commit_package_supersession`.

The later runtime may compute and validate the existing package supersession commit basis server-side by reading existing source package rows, current package construction/review authority, downstream dependency state, corrected artifact set authority, and corrected-artifact replacement package-set authority. It may call the existing commit helper internally only with server-owned payload values if that preserves the same durable table constraints and idempotency behavior.

## Future Request Contract

The later request must be allowlisted and should accept only:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `corrected_package_artifact_set_id`;
- `corrected_artifact_basis_hash`;
- `replacement_package_set_authority_id`;
- `replacement_authority_basis_hash`;
- `operator_decision`.

The future request must not accept replacement payload refs, replacement payload hashes, source payload refs, source payload hashes, package bytes, corrected artifact refs, arbitrary artifact refs, hashes generated by the caller, local paths, URLs, connector ids, destination ids, credentials, source-upload fields, local directories, RAG/vector inputs, hidden LLM prompts, auth context, security context, retry/rerun/cancel instructions, or rendered/browser-only state as authority.

## Future Runtime Boundary

The later runtime may perform exactly one bounded mutation:

- persist or replay a durable `L3PackageSupersessionCommit` row for the corrected-artifact replacement package-set authority.

The later runtime must:

- derive `source_package_set_hash`, source package ids/kinds/refs/hashes, replacement package-set id/hash/kinds/refs/hashes, downstream dependency hash, package supersession preview hash, and commit basis hash server-side;
- verify the replacement authority belongs to the supplied corrected artifact set authority;
- verify current source package refs/hashes still match replacement authority source vectors;
- verify the replacement authority mode is `replacement_package_set_authority_from_corrected_artifact_set`;
- preserve existing `L3OutputPackage` rows and payload bytes;
- return response-safe/redacted replacement refs rather than raw local paths; and
- keep all downstream manifest, namespace, activation, handoff/export, delivery, source expansion, and RAG/vector behavior unchanged.

The later runtime must not:

- generate replacement artifacts;
- rewrite package payloads;
- mutate source `L3OutputPackage` rows;
- record replacement artifact manifests;
- record replacement namespace rows;
- activate packages;
- invalidate downstream artifacts;
- re-run handoff/export or delivery;
- create `ConnectorRun` or `ConnectorRunTarget` rows;
- use credentials;
- perform network egress;
- expose provider-public delivery/use or public URLs;
- add source expansion;
- add RAG/vector or qualitative-hybrid execution;
- broaden auth/security behavior;
- activate the full mockup; or
- create frontend-durable authority.

## Idempotency Contract

The later runtime must enforce:

- same `client_request_id` plus same complete corrected-artifact supersession basis returns the same commit receipt/status;
- same `client_request_id` plus different basis fails closed;
- same complete basis plus new `client_request_id` returns existing commit status rather than creating duplicate lineage;
- same replacement package-set authority plus conflicting corrected artifact set fails closed;
- same corrected artifact set plus conflicting replacement authority fails closed; and
- partial commit writes are not observable.

## Failure Lifecycle

The later runtime must fail closed on:

- missing session, plan, pass, or reconciliation authority;
- missing corrected artifact set authority;
- missing corrected-artifact replacement package-set authority;
- stale corrected artifact basis hash;
- stale replacement authority basis hash;
- wrong session, plan, pass, or reconciliation;
- wrong source package set hash;
- stale current source package refs/hashes;
- missing package construction/review authority needed for the package supersession preview hash;
- replacement authority not produced from corrected artifact set authority;
- duplicate client request conflict;
- same-basis conflict;
- unsupported operator decision;
- caller-supplied refs, hashes, package bytes, local paths, URLs, connector/destination fields, credential fields, source expansion fields, RAG/vector fields, auth/security fields, or frontend-durable fields; and
- any raw local path exposure.

Failures must return redacted error codes, blocked fields, recoverability, and next allowed actions. They must not expose raw filesystem paths, package payload bytes, credential material, connector payloads, public URLs, or hidden planning content.

## Required Proof For Later Implementation

Implementation proof for the later slice must include:

- OpenAPI request/response contract exposure;
- API error-envelope behavior;
- successful server-computed package supersession commit from corrected-artifact replacement authority;
- same-key replay and same-basis/new-key replay;
- same-key/different-basis conflict;
- stale corrected artifact basis hash failure;
- stale replacement authority basis hash failure;
- wrong corrected artifact set versus replacement authority failure;
- wrong session/pass/reconciliation failure;
- stale current source package authority failure;
- missing package construction/review authority failure;
- forbidden payload refs/hashes/package bytes/path/URL/connector/source/RAG/auth fields fail closed;
- response redaction with no raw local path exposure;
- no source `L3OutputPackage` mutation;
- no replacement artifact manifest rows;
- no replacement namespace rows;
- no package activation rows;
- no `ConnectorRun` or `ConnectorRunTarget` rows; and
- no provider-public delivery, source expansion, RAG/vector, auth/security, full mockup, or frontend-durable behavior.

## Non-Admission Boundary

This freeze admits no runtime implementation in this pass. It does not add backend route behavior, DTO behavior, response-model behavior, migration behavior, rendered controls, package payload rewrite, source `L3OutputPackage` mutation, replacement artifact generation, replacement artifact manifest recording, replacement namespace row creation, package activation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, `ConnectorRun` creation, `ConnectorRunTarget` creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw local path exposure, or hidden LLM planning.

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

No backend runtime test or headed/headless E2E run is required because this freeze changes planning/control metadata only.

## Next Posture

After this freeze is merged, the next exact posture is `current_main_sync_corrected_artifact_package_rebuild_downstream_authority_freeze`.

After sync, the next exact implementation posture is `implement_server_computed_package_supersession_commit_from_corrected_artifact_replacement_authority_after_freeze_sync`.
