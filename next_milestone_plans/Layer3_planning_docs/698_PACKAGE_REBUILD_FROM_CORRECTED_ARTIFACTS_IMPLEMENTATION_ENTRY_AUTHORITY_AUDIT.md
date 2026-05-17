# 698 - Package Rebuild From Corrected Artifacts Implementation-Entry Authority Audit

## Status

Status: implementation-entry authority audit for `rebuild_package_from_corrected_artifacts`.

Doc: `698_PACKAGE_REBUILD_FROM_CORRECTED_ARTIFACTS_IMPLEMENTATION_ENTRY_AUTHORITY_AUDIT.md`.

Predecessor sync doc: `697_PACKAGE_REBUILD_FROM_CORRECTED_ARTIFACTS_OPERATOR_ACTION_FREEZE_CURRENT_MAIN_SYNC.md`.

Current-main audit commit: `5484d35355e7aaabeea39f586be1fe89245f773d`.

Selected surface: `package_mutation_reconstruction`.

Selected package lifecycle action: `rebuild_package_from_corrected_artifacts`.

Audit result: `no_runtime_now_rebuild_package_from_corrected_artifacts_source_authority_absent`.

Runtime status: `blocked_no_implementation_entry_freeze`.

## Authority Findings

Current main contains these package lifecycle authorities:

- package supersession preview through `/api/v1/layer3/package/mutation/preview`;
- server-owned replacement package artifact materialization through `/api/v1/layer3/package/replacement-artifact/materialize`;
- replacement artifact manifest recording through `/api/v1/layer3/package/replacement-artifact/manifest/record` and `/api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`;
- replacement namespace rows through `/api/v1/layer3/package/replacement-namespace/record`;
- source L3 output package replacement activation through `/api/v1/layer3/package/replacement-activation/commit`;
- downstream active-package-authority read adoption through handoff/export, connector-local receipt, server-owned local outbox write, local-outbox provider-private handoff, and external local export.

Current main also contains execution result review notes and reviewed output item state through `/api/v1/layer3/execution/result/review`, but that state is review metadata only. It does not define corrected package artifact bytes, corrected package artifact refs, corrected artifact hashes, a corrected-artifact manifest, or a rebuild basis hash.

Current main still treats `rebuild_package` as a forbidden request field in package preview, replacement artifact materialization, replacement artifact manifest, replacement namespace, replacement activation, and downstream handoff/export surfaces. The existing replacement artifact materialization service derives replacement artifacts from the immutable source package set and supersession preview authority; it does not consume a governed corrected-artifact authority source.

## Audited Owner Files

The implementation-entry audit checked the current package and review owner surfaces:

- `backend/app/api/layer3.py`;
- `backend/app/services/layer3_execution_review.py`;
- `backend/app/services/layer3_package_mutation_entry.py`;
- `backend/app/services/layer3_replacement_package_materialization.py`;
- `backend/app/services/layer3_replacement_package_artifact_manifest.py`;
- `backend/app/services/layer3_replacement_package_namespace.py`;
- `backend/app/services/layer3_package_replacement_activation.py`;
- `backend/tests/test_layer3_api.py`;
- `backend/tests/test_layer3_execution_review.py`;
- `backend/tests/test_layer3_package_review_contract.py`.

The audit found no route, service, model, migration, or test authority that names a governed corrected-artifact source for `rebuild_package_from_corrected_artifacts`.

## Non-Admission Boundary

This audit admits no runtime implementation. It does not add an implementation-entry freeze, backend route, DTO, response model, model, migration, service behavior, executable backend test behavior, rendered UI control, package payload rewrite, source `L3OutputPackage` row mutation, corrected package artifact bytes, browser-supplied package bytes, browser-supplied replacement bytes, arbitrary artifact refs, arbitrary hashes, local paths, URLs, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, raw local path exposure, or hidden LLM planning.

## Required Next Decision

The next exact posture is `select_governed_corrected_artifact_source_authority_for_package_rebuild`.

That decision must name exactly one corrected-artifact authority source before runtime can be frozen. Acceptable future shapes include one of:

- operator review corrections captured as a server-owned corrected package artifact set;
- server-derived corrected artifacts from an already-recorded review/correction state;
- a bounded correction-capture surface that records corrected artifact refs/hashes without accepting arbitrary local paths, URLs, package bytes, browser-generated diffs, or package payload rewrites.

The next decision must define the corrected-artifact source owner route/service, allowed request fields, artifact/hash/size authority, basis hash, stale and duplicate failure lifecycle, idempotency rules, redaction contract, and whether rendered status/history is required before or after backend proof.

Until that decision is frozen, runtime remains blocked at `no_runtime_now_rebuild_package_from_corrected_artifacts_source_authority_absent`.

## Required Validation

This audit branch must pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

No backend runtime test or headed/headless E2E run is required because this audit changes planning/control metadata only.
