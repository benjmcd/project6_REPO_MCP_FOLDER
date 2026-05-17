# 702 - Operator Review Corrections Corrected Package Artifact Set Entry Freeze

## Status

Status: implementation-entry freeze for `operator_review_corrections_server_owned_corrected_package_artifact_set`.

Doc: `702_OPERATOR_REVIEW_CORRECTIONS_CORRECTED_PACKAGE_ARTIFACT_SET_ENTRY_FREEZE.md`.

Predecessor current-main sync doc: `701_PACKAGE_REBUILD_CORRECTED_ARTIFACT_SOURCE_AUTHORITY_SELECTION_FREEZE_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `efde2ef70a9d56fab451ca519041b771c27f1e88`.

Selected surface: `package_mutation_reconstruction`.

Selected package lifecycle action: `rebuild_package_from_corrected_artifacts`.

Selected corrected-artifact authority source: `operator_review_corrections_server_owned_corrected_package_artifact_set`.

Selected source class: `server_owned_corrected_package_artifact_authority`.

Implementation-entry decision: `freeze_runtime_entry_for_corrected_package_artifact_source_authority_only`.

Runtime status in this pass: `not_implemented_in_this_pass`.

## Admitted Runtime Slice For Later Implementation

A later runtime pass may implement exactly one source-authority slice:

- route: `POST /api/v1/layer3/package/corrected-artifact-set/record`;
- owner service: `backend/app/services/layer3_corrected_package_artifact_set.py`;
- durable model: `L3CorrectedPackageArtifactSet`;
- durable table: `l3_corrected_package_artifact_set`;
- migration owner: `backend/alembic/versions/0031_layer3_corrected_package_artifact_set.py`;
- targeted tests: `backend/tests/test_layer3_corrected_package_artifact_set.py`;
- API response schema id: `layer3.corrected_package_artifact_set.v1`;
- request mode: `operator_review_corrections_server_owned_corrected_package_artifact_set`;
- operator decision: `record_corrected_package_artifact_set_from_review_corrections`.

The slice may record server-owned corrected package artifact-set authority for package rebuild preparation only. It may not rebuild packages, activate packages, rewrite source package payloads, mutate source `L3OutputPackage` rows, re-run handoff/export, or deliver anything downstream.

## Required Request Authority

The future request must be allowlist-only and require:

- `client_request_id`;
- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- `reconciliation_record_id`;
- `source_package_set_hash`;
- `source_output_package_ids`;
- `source_package_kinds`;
- `source_payload_refs`;
- `source_payload_hashes`;
- `result_review_record_ref`;
- `reviewed_output_items_hash`;
- `package_review_preview_hash`;
- `operator_decision`.

Optional request fields may be limited to:

- `package_supersession_preview_hash`;
- `replacement_artifact_materialization_id`;
- `materialization_basis_hash`;
- `replacement_package_set_authority_id`;
- `replacement_authority_basis_hash`;
- `replacement_artifact_manifest_id`;
- `replacement_manifest_hash`;
- `correction_set_label`.

The runtime must derive or validate corrected artifact refs, hashes, byte sizes, artifact namespace, manifest hash, and corrected-artifact basis hash server-side from existing package/review authority. The request must not accept corrected artifact refs, corrected artifact hashes, corrected artifact bytes, package bytes, replacement bytes, browser-generated diffs, arbitrary paths, URLs, destination instructions, connector ids, credentials, provider URLs, source upload payloads, local directories, RAG/vector inputs, hidden LLM prompts, retry/rerun/cancel fields, auth context, or security context as authority.

## Required Behavior

The future runtime must:

- fail closed unless session, plan, pass, reconciliation, source package set, execution result review, and package review authority all match;
- treat free-form review notes as supporting metadata only, never as corrected-artifact authority by themselves;
- compute a deterministic corrected artifact set id and corrected-artifact basis hash;
- write or record corrected artifacts only under a server-owned artifact namespace such as `corrected-package-artifacts`;
- record durable status/history/audit fields without exposing raw local paths;
- return same receipt/status for same client request id and same basis;
- fail closed for same client request id with different basis;
- return existing status for same basis with a new client request id;
- fail closed for conflicting corrected artifacts or conflicting target state;
- preserve source `L3OutputPackage` rows and existing replacement package lifecycle rows;
- create no `ConnectorRun` or `ConnectorRunTarget` rows;
- create no provider-public delivery/use state.

Required failure codes must cover stale source package, stale review, stale package review, wrong session/pass/reconciliation, wrong package kind, missing artifact, tampered hash, partial artifact write, unsupported correction state, duplicate-key conflict, same-basis replay, and forbidden request fields.

## Non-Admission Boundary

This freeze admits no runtime implementation by itself. It does not add backend code, route registration, DTOs, response models, model definitions, migrations, tests, rendered UI controls, package rebuild runtime, package payload rewrite, source `L3OutputPackage` row mutation, package activation, downstream invalidation, handoff/export rerun, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, raw local path exposure, or hidden LLM planning.

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

After this freeze is merged, the next exact posture is `current_main_sync_operator_review_corrections_corrected_package_artifact_set_entry_freeze`.

After current-main sync, the next exact posture is `implement_operator_review_corrections_corrected_package_artifact_set_after_entry_freeze_sync`. Implementation must be limited to the admitted source-authority slice above.
