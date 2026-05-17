# 722 - Corrected Artifact Replacement Activation Authority Evaluation

## Status

Status: branch-local satisfied-state evaluation for `corrected_artifact_replacement_activation_authority`.

Doc: `722_CORRECTED_ARTIFACT_REPLACEMENT_ACTIVATION_AUTHORITY_EVALUATION.md`.

Predecessor current-main sync doc: `721_CORRECTED_ARTIFACT_REPLACEMENT_NAMESPACE_RUNTIME_CURRENT_MAIN_SYNC.md`.

Evaluation branch: `codex/l3-corrected-artifact-activation-eval`.

Current-main checkpoint before evaluation branch: `c15f96b7159a7b4e1d152c23df6d6a7bf33ab516`.

Evaluated posture: `evaluate_package_replacement_activation_authority_after_corrected_artifact_namespace_runtime_sync`.

Evaluation result: `current_main_satisfies_corrected_artifact_replacement_activation_authority`.

Runtime behavior change in this pass: `false`.

Test/proof behavior change in this pass: `true`.

## Authority Finding

Current main already contains the generic package replacement activation runtime from `667_SOURCE_L3_OUTPUT_PACKAGE_REPLACEMENT_ACTIVATION_RUNTIME_CURRENT_MAIN_SYNC.md`.

That runtime commits `POST /api/v1/layer3/package/replacement-activation/commit` through `backend/app/services/layer3_package_replacement_activation.py` and persists `L3PackageReplacementActivation` / `l3_package_replacement_activation`.

The corrected-artifact namespace runtime from `721_CORRECTED_ARTIFACT_REPLACEMENT_NAMESPACE_RUNTIME_CURRENT_MAIN_SYNC.md` records the same durable namespace target family, `L3ReplacementOutputPackage`, from corrected-artifact manifest authority.

Because activation consumes durable `L3ReplacementOutputPackage` rows plus their replacement artifact manifest, replacement package-set authority, package supersession commit, source package ids, package kinds, response-safe artifact refs, and artifact hashes, no new activation runtime is required for the corrected-artifact bridge.

## Added Proof

This branch adds focused regression proof in `backend/tests/test_layer3_package_replacement_activation.py`.

The added proof builds the full corrected-artifact chain:

1. `L3CorrectedPackageArtifactSet`;
2. corrected-artifact `L3ReplacementPackageSetAuthority`;
3. corrected-artifact `L3PackageSupersessionCommit`;
4. corrected-artifact `L3ReplacementPackageArtifactManifest`;
5. corrected-artifact complete `L3ReplacementOutputPackage` namespace set; and
6. `L3PackageReplacementActivation`.

The proof verifies that current activation:

- activates the corrected-artifact namespace set;
- records one durable activation receipt;
- preserves source `L3OutputPackage` rows;
- preserves package payload files;
- returns only response-safe active artifact refs;
- keeps package payload rewrite disabled;
- keeps downstream handoff rebinding disabled;
- keeps connector dispatch disabled;
- keeps provider-public URL disabled;
- keeps source widening disabled;
- keeps qualitative-hybrid/RAG execution disabled;
- resolves active replacement package authority;
- resolves active replacement package payload authority internally; and
- replays the same basis with a new request id as `already_activated`.

Observed branch-local validation:

```powershell
python -m pytest .\backend\tests\test_layer3_package_replacement_activation.py -q
```

Result observed: `5 passed`.

## Current-Main Satisfied State

The current-main behavior is satisfied for corrected-artifact replacement activation authority. No separate implementation-entry freeze is required for activating corrected-artifact namespace rows, because the already-merged activation runtime consumes the same durable namespace row family and authority basis.

This is a test/proof and planning-control pass only. It does not add a route, DTO, model, migration, service runtime behavior, rendered UI, package payload write, package payload rewrite, source package row mutation, downstream invalidation, handoff/export rebinding, delivery rerun, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, caller-supplied arbitrary paths or URLs, browser-supplied refs/hashes/bytes, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact posture after this evaluation merges is `await_current_main_sync_for_corrected_artifact_replacement_activation_authority_evaluation`.

After the evaluation is current-main synced, the next exact implementation-preparing posture is `select_downstream_active_package_authority_read_adoption_after_corrected_artifact_activation_sync`.

That next selection should choose exactly one downstream reader path to adopt `resolve_active_replacement_package_authority` or `resolve_active_replacement_package_payload_authority`. The likely highest-value reader is handoff/export preparation, because it is the next end-to-end step that must consume activated replacement package authority before controlled outbox/export/delivery can represent the corrected package set.

The next selection must not implement downstream invalidation, handoff/export rebinding, delivery rerun, package payload rewrite, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, rendered controls, auth/security behavior, or frontend-durable authority without a separate explicit freeze.
