# 656 - Rendered Replacement Package Artifact Manifest Control Freeze

## Status

Status: implementation-entry freeze only for `rendered_replacement_package_artifact_manifest_control_from_authority`.

Doc: `656_RENDERED_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_CONTROL_FREEZE.md`.

Predecessor doc: `655_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_RECORD_FROM_AUTHORITY_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main preflight commit: `d9cf08c7b3c584904e21f9b3bf784bb6845f4352`.

Branch: `codex/l3-rendered-manifest-control-admission-freeze`.

Selected surface: `package_mutation_reconstruction`.

Selected implementation-entry mode: `rendered_replacement_package_artifact_manifest_control`.

Selected operator action: `record_replacement_package_artifact_manifest_from_authority`.

Selected route: `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`.

Backend authority owner: `backend/app/services/layer3_replacement_package_artifact_manifest.py`.

Future rendered owner files:

- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.css`;
- `backend/app/review_ui/static/layer3.js`;
- `backend/tests/test_layer3_page.py`;
- `e2e/layer3-workbench.spec.js`.

Entry decision: `freeze_only`.

Runtime status: `not_implemented_in_this_pass`.

## Admission Basis

Current main now has the server-computed record-from-authority route from doc `654`, synced by doc `655`.

The existing rendered package lifecycle already records the required upstream authority in browser-visible server response state:

- `State.replacementPackageArtifactMaterialization.replacement_artifact_materialization_id`;
- `State.replacementPackageArtifactMaterialization.materialization_basis_hash`;
- `State.replacementPackageSetAuthority.replacement_package_set_authority_id`;
- `State.replacementPackageSetAuthority.authority_basis_hash`;
- `State.packageSupersessionCommit.package_supersession_commit_id`;
- `State.packageSupersessionCommit.commit_basis_hash`;
- the shared session, plan, pass, and reconciliation identity already used by the package lifecycle controls.

The admitted future rendered control may submit only:

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

The future control must not compute or supply `artifact_manifest_hash`, manifest `authority_basis_hash`, artifact byte sizes, raw replacement artifact refs, raw local paths, URLs, package bytes, replacement bytes, artifact bytes, package payload rewrites, or replacement output package rows.

## Frozen Future Implementation

A future implementation pass may add a rendered submit/status panel after package supersession commit is recorded.

Expected rendered identifiers:

- `#replacement-package-artifact-manifest-submit`;
- `#replacement-package-artifact-manifest-panel`;
- `data-rendered-mode="rendered_replacement_package_artifact_manifest_control"`.

Expected rendered behavior:

- enable the submit control only when replacement artifact materialization, replacement package-set authority, and package supersession commit response authority are present;
- call only `/api/v1/layer3/package/replacement-artifact/manifest/record-from-authority`;
- persist the response in `State.replacementPackageArtifactManifest`;
- show the response status, schema id, record-from-authority operator decision, manifest id, package kinds, redacted artifact refs, computed manifest hash, computed authority basis hash, and disabled side-effect flags;
- clear or disable downstream package/handoff/export controls only as needed to avoid stale authority after a new manifest record;
- keep raw local paths and raw artifact refs out of rendered text.

Expected tests:

- static page assertions for the new button, panel, rendered mode, and route string;
- focused rendered JavaScript assertions that the request uses only the admitted fields and excludes forbidden browser fields;
- headed/headless E2E proof that the rendered flow records the manifest after package supersession commit and displays redacted refs;
- negative E2E/API proof for missing authority, stale basis-hash failure, forbidden field absence, no connector-run creation, no replacement namespace row, no package row mutation, no provider-public delivery/use, no source expansion, no RAG/vector behavior, and no raw local path exposure.

## Non-Admission Boundary

This freeze admits no implementation in this pass. It does not add rendered controls yet, replacement namespace rows, package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, full mockup activation, auth/security behavior, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied artifact refs, browser-supplied replacement hashes, browser-supplied manifest hashes, browser-supplied byte sizes, browser-supplied package bytes, browser-supplied replacement bytes, or browser-supplied artifact bytes.

## Validation

This freeze must pass:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

No headed/headless E2E run is required in this freeze pass because no rendered behavior changes.

## Next Posture

The next required action after merge is `current_main_sync_rendered_replacement_package_artifact_manifest_control_freeze`.

After merge and current-main sync, the next exact posture is `implement_rendered_replacement_package_artifact_manifest_control_after_freeze_sync`.

That future implementation may touch only the rendered package lifecycle control files and focused static/E2E tests unless a current-main blocker proves a backend/API test update is required. It may not add package rebuild, package payload rewrite, source `L3OutputPackage` row mutation, replacement namespace rows, downstream invalidation, re-delivery runtime, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, or browser-supplied artifact refs/hashes/bytes.
