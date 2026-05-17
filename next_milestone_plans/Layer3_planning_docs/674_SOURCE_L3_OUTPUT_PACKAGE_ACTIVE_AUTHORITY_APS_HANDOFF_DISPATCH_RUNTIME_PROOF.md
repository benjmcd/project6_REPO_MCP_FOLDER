# Source L3 Output Package Active Authority APS Handoff Dispatch Runtime Proof

## Status

Status: branch-local implementation proof for `source_l3_output_package_active_authority_aps_handoff_dispatch_runtime`.

Doc: `674_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_APS_HANDOFF_DISPATCH_RUNTIME_PROOF.md`.

Predecessor sync doc: `673_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_APS_HANDOFF_DISPATCH_FREEZE_CURRENT_MAIN_SYNC.md`.

Branch: `codex/l3-active-authority-aps-dispatch-impl`.

Current-main preflight commit: `8cf6a62a53c5acea2c10787a159c09e2bff5ff7e`.

## Implemented Slice

The implemented reader path is `aps_handoff_dispatch` through `POST /api/v1/layer3/handoff/aps/dispatch`.

The selected operator action remains `adopt_active_replacement_package_authority_for_aps_handoff_dispatch`.

The runtime uses `resolve_active_replacement_package_payload_authority` over the existing `resolve_active_replacement_package_authority` response-safe projection so APS handoff dispatch can consume the server-private active replacement package artifact authority for this reader only.

The implementation updates:

- `backend/app/services/layer3_package_replacement_activation.py`
- `backend/app/services/layer3_aps_handoff.py`
- `backend/app/services/layer3_external_export_response.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/api/layer3.py`
- `backend/tests/review_browser_server.py`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_workbench.py`

## Runtime Behavior

When no active replacement package authority exists, `aps_handoff_dispatch` preserves the existing source `L3OutputPackage` behavior.

When active replacement package authority exists, APS handoff dispatch validates the active package kinds, source output package ids, source payload hashes, replacement output package ids, active artifact refs, active artifact hashes, replacement activation basis hash, replacement namespace, and replacement artifact manifest authority before using active replacement package artifact authority.

The applied state records `active_package_authority_applied`, `package_replacement_activation_id`, `source_output_package_ids`, `source_payload_hashes`, `active_replacement_output_package_ids`, `active_payload_refs`, `active_payload_hashes`, and `replacement_activation_basis_hash` in the dispatch authority basis, persisted dispatch state, session summary, API response, and APS handoff package summary where applicable.

APS handoff dispatch accepts the active payload refs/hashes emitted by the existing handoff/export prepare state when active authority exists. Source package refs/hashes remain the immutable package-review source basis, while active refs/hashes become the effective APS handoff payload basis after active authority validation.

The session readiness summary uses active replacement canonical artifact authority for APS compatibility checks when active authority exists, so the read-only status surface does not remain blocked by stale or superseded source canonical payload contents.

The recorded handoff/export summary projection preserves the existing qualitative APS and source-intake identity fields already stored in handoff/export prepare state, so rendered status refreshes can continue to evaluate downstream APS-readiness admission after `handoff_export_prepared`.

Existing external export/download prepare remains reachable after active APS dispatch by comparing handoff/export prepare and APS dispatch state against the same effective active payload refs/hashes. Its response and recorded readiness project the active refs/hashes when the upstream active dispatch state uses them. This is downstream compatibility for the already-existing external export/download readiness lane, not a new external export/download implementation or delivery admission.

The APS handoff package materialization reads the canonical internal payload from active replacement artifact authority when the active authority is valid. This proves APS handoff output is derived from active replacement artifact authority when active authority is present.

Source `L3OutputPackage` rows, source payload refs/hashes, package ids, source payload files, and `uq_l3_output_package_session_kind` remain unchanged by this reader adoption.

## Guardrails

The runtime fails closed when:

- active authority package kinds do not match APS handoff package order;
- active authority source package ids do not match the APS dispatch source packages;
- active authority source payload hashes do not match source package hashes;
- active authority replacement output package ids, active artifact refs, active artifact hashes, replacement activation basis hash, replacement namespace, or replacement artifact manifest authority are incomplete;
- supplied APS dispatch or external export/download readiness payload refs/hashes match neither the source package basis nor the validated active effective basis;
- handoff/export prepare state does not already include the exact active authority and effective payload refs/hashes;
- external export/download readiness state does not match the effective active APS dispatch refs/hashes;
- the active canonical artifact wrapper schema, package kind, source output package id, source payload hash, or active artifact hash does not match authority;
- caller-supplied active authority fields are submitted to APS handoff dispatch.

Active refs remain response-safe `artifact://replacement-package-artifacts/...` refs. The active-authority API/UI projection does not expose raw local filesystem paths.

## Proof

Targeted backend/API proof covers:

- unchanged no-active-authority APS handoff dispatch behavior;
- active refs/hashes emitted by handoff/export prepare accepted by APS handoff dispatch;
- `active_package_authority_applied` and active replacement refs/hashes applied to the APS handoff dispatch response, dispatch state, session summary, and APS handoff output package summary;
- session readiness stays `aps_handoff_ready` using active canonical artifact authority after the original source canonical payload is tampered;
- APS handoff canonical payload read from the active replacement artifact even if the original source canonical artifact is tampered after prepare;
- existing external export/download prepare accepts the active dispatch state and projects active refs/hashes in the readiness response;
- source `L3OutputPackage` rows unchanged;
- exactly one APS handoff output package added on successful dispatch;
- no `ConnectorRun` or `ConnectorRunTarget` creation;
- response-safe `artifact://replacement-package-artifacts/...` active refs and no raw local path exposure in active refs;
- same-key replay returning the existing APS handoff dispatch state;
- fail-closed behavior for prepare state without matching active authority;
- caller-supplied active authority fields rejected by the APS handoff dispatch request schema.

Rendered proof remains limited to existing controls. The branch updates the browser-test APS handoff stubs to accept the optional active-authority keyword and verifies that refreshed status continues to enable the existing rendered APS handoff path after handoff/export prepare.

## Validation

Branch-local validation:

```powershell
python -m py_compile .\backend\app\services\layer3_package_replacement_activation.py .\backend\app\services\layer3_aps_handoff.py .\backend\app\services\layer3_external_export_response.py .\backend\app\services\layer3_workbench.py .\backend\app\api\layer3.py
python -m py_compile .\backend\tests\review_browser_server.py .\backend\tests\test_layer3_api.py .\backend\tests\test_layer3_workbench.py
python -m pytest .\backend\tests\test_layer3_workbench.py::test_execution_start_runs_source_intake_selected_pass_without_analysis_run -q
python -m pytest .\backend\tests\test_layer3_api.py -k "aps_handoff_dispatch_applies_active_replacement_authority or aps_handoff_dispatch_active_authority_requires_matching_prepare_state" --maxfail=1
python -m pytest .\backend\tests\test_layer3_api.py -k "aps_handoff_dispatch or external_export_download_prepare" --maxfail=1
$files = Get-ChildItem .\backend\tests\test_layer3_*.py | ForEach-Object { ".\backend\tests\$($_.Name)" }
python -m pytest @files -q
npm run test:e2e:chromium
```

Final branch validation must also include:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

## Non-Admission

This runtime proof does not admit rendered activation controls, new external export/download adoption beyond compatibility with the already-existing readiness lane, server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, connector/destination dispatch, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, or raw local path exposure.

## Next Posture

After this implementation merges, a current-main sync must record the PR, checks, comments, reviews, reviewThreads, merge commit, validation, and next posture.

The next exact posture after merge is `await_current_main_sync_for_source_l3_output_package_active_authority_aps_handoff_dispatch_runtime`.
