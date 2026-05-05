# Layer 3 Merged-Main Closeout

Status: bounded merged-main proof snapshot. Functional boundary evidence currently targets PR #556 at `project6-origin/main=93fe525b`; PR #558 adds qualitative owner-service error-boundary proof at `project6-origin/main=5831ff2f`; later docs/proof synchronization lanes do not change the functional boundary or admit new runtime capability.

This file is post-merge documentation/proof synchronization only. It is a bounded snapshot, not an evergreen manifest, and it does not replace live source/tests as authority. The package supersession preview row admits only the exact read-only preview route and does not admit broad package mutation/reconstruction. The replacement package-set authority row admits only the exact durable metadata authority record and does not admit replacement package rows or package payload writes. The package supersession commit entry row admits only the exact durable lineage record and does not admit package row mutation, package payload writes, replacement package row creation, UI controls, or broad package mutation/reconstruction. The qualitative/hybrid/RAG row admits only the exact single APS-document qualitative pass and does not admit broad qualitative, hybrid, RAG/vector, hidden LLM, source widening, connector, or package mutation behavior. The mockup truth-state row keeps mockups as target-state design/specification artifacts and does not admit full mockup activation.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- snapshot_target_ref: `project6-origin/main`
- functional_boundary_head: `93fe525b`
- functional_boundary_role: last runtime-affecting Layer 3 boundary captured in this snapshot
- proof_snapshot_head: `5831ff2f`
- proof_snapshot_role: latest proof-hardening Layer 3 boundary captured in this snapshot
- snapshot_role: bounded proof snapshot after PR #558 qualitative owner-service error-boundary proof; not an evergreen manifest and not a self-updating current-main marker
- latest_functional_boundary_pr: `#556`
- latest_proof_boundary_pr: `#558`
- docs_sync_reference_pr: `#551`
- docs_sync_reference_role: historical proof synchronization only; do not infer the live `project6-origin/main` SHA from this field.
- current_main_rule: re-read live git and rerun `python .\tools\l3-progress-check.py` before new work; do not treat any SHA in this file as an evergreen current-main assertion.
- known local caveat: `.omc/state/hud-state.json`, `.omc/state/hud-stdin-cache.json`, `.codesight/`, `.cursorrules`, `.github/copilot-instructions.md`, `CLAUDE.md`, and `codex.md` are local operator/sidecar state and are not implementation evidence.

Authority order for this closeout:

1. Live source and tests.
2. Local command output.
3. `tools/l3-progress-check.py`.
4. `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md` and `118_L3_GOAL_AUDIT.md`.
5. Older planning docs and mockups only as target-state or historical context.

Historical current-main proof after PR #538 remains retained for source-boundary, DTO-boundary, signed-reference, and session-status invariant checks; PR #540 package preview proof, PR #554 replacement package-set authority proof, PR #556 package supersession commit lineage proof, and PR #558 qualitative owner-service error-boundary proof are additive and must not be treated as broad package mutation/reconstruction, broad qualitative/hybrid/RAG, connector/destination dispatch, source widening, provider/public URL, full mockup activation, or auth/security proof.

## Prompt-To-Artifact Checklist

| Goal item | Closeout disposition | Concrete evidence | Scope limit |
| --- | --- | --- | --- |
| Synthesis critical items before broader work | Partially complete and bounded | `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`; `118_L3_GOAL_AUDIT.md`; `tools/l3-progress-check.py`; PR #558 qualitative owner-service error-boundary proof | Auth/security remains deferred; broad activation remains blocked. |
| Canonical state/action contract | Implemented and guarded | `backend/app/services/layer3_state_action_contract.py`; `backend/tests/test_layer3_workbench.py`; `backend/tests/test_layer3_api.py`; progress checker verifies admitted/deferred capability split | Deferred capability ids are not action ids. |
| Session-status migration constraint | Implemented and guarded | `backend/alembic/versions/0012_layer3_session_entry.py`; `backend/tests/test_layer3_session_entry.py::test_layer3_session_entry_migration_defines_status_check_constraint`; progress checker verifies the migration/test/doc proof terms | `L3Session.status` vocabulary only; no broad state-machine rewrite, lifecycle recovery, supersession, execution, source, package, connector, mockup, or auth/security behavior change. |
| Durable Gate B idempotency claim | Implemented and guarded | `backend/alembic/versions/0017_layer3_gate_b_idempotency.py`; `backend/app/models/models.py` `L3GateBIdempotencyKey`; `backend/app/services/layer3_gate_b_state.py`; `backend/tests/test_layer3_gate_b_state.py::test_gate_b_decision_concurrent_duplicate_client_request_id_uses_durable_claim`; progress checker verifies the unique claim table, service helpers, readiness contract, and negative invariant proof | Gate B duplicate protection only; no L3PassRun, AnalysisRun, AnalysisArtifact, L3OutputPackage, broad execution, source widening, package mutation/reconstruction, connector/destination dispatch, provider/public URL support, full mockup activation, or auth/security behavior change. |
| Frontend session recovery | Implemented and merged via PR #535 | `backend/app/review_ui/static/layer3.js`; `backend/tests/test_layer3_page.py`; `e2e/layer3-workbench.spec.js`; recorded headed/headless proof in `118_L3_GOAL_AUDIT.md`; PR #535 checks and post-merge `main` workflow passed | Server-revalidated recovery only; not frontend-only durable state or full mockup activation. |
| Service extraction to reduce workbench risk | Implemented narrowly | `backend/app/services/layer3_plan_revision_state.py`; `backend/app/services/layer3_gate_b_state.py`; `backend/app/services/layer3_source_boundary.py`; related tests | No broad `layer3_workbench.py` rewrite. |
| Same-origin signed-reference service proof | Implemented and guarded | `backend/app/services/layer3_signed_reference_state.py`; `backend/tests/test_layer3_signed_reference_state.py`; progress checker verifies the atomic conditional update and lifecycle/concurrent-use proof | Same-origin signed-reference state only; no provider/public URL, revocation API, connector/destination dispatch, or broad delivery behavior. |
| Preflight DTO boundary | Implemented and guarded | `backend/app/api/layer3.py` `Layer3PreflightRequest`; `backend/tests/test_layer3_api.py::test_layer3_api_preflight_rejects_extra_fields_before_service_execution`; progress checker verifies the strict request boundary | Preflight known top-level fields only; nested `manual_constraints` context remains intentionally flexible. No broad upload, local directory ingestion, RAG/vector source, web connector source, runtime DB widening, connector/destination dispatch, package mutation/reconstruction, provider/public URL, mockup, or auth/security behavior change. |
| Plan-preview DTO boundary | Implemented and guarded | `backend/app/api/layer3.py` `Layer3PlanPreviewRequest`; `backend/tests/test_layer3_api.py::test_layer3_api_plan_preview_rejects_extra_fields_before_service_mutation`; progress checker verifies the strict request boundary | Plan preview known fields only; no plan materialization, execution, package, handoff, source widening, mockup, or auth/security behavior change. |
| Source-preview DTO boundary | Implemented and guarded | `backend/app/api/layer3.py` `Layer3SourcePreviewRequest`; `backend/tests/test_layer3_api.py::test_layer3_api_source_preview_rejects_extra_fields_before_service_execution`; progress checker verifies the strict request boundary | Source preview known fields only; no broad upload, local directory ingestion, RAG/vector source, web connector source, runtime DB widening, connector/destination dispatch, package mutation/reconstruction, provider/public URL, mockup, or auth/security behavior change. |
| Material-preview DTO boundary | Implemented and guarded | `backend/app/api/layer3.py` `Layer3MaterialPreviewRequest`; `backend/tests/test_layer3_api.py::test_layer3_api_material_preview_rejects_extra_fields_before_service_execution`; progress checker verifies the strict request boundary | Material preview known fields only; no broad upload, local directory ingestion, RAG/vector source, web connector source, runtime DB widening, connector/destination dispatch, package mutation/reconstruction, provider/public URL, mockup, or auth/security behavior change. |
| Internal connector dispatch record | Implemented narrowly; broad dispatch remains blocked | `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md`; `backend/app/services/layer3_connector_dispatch_entry.py`; `backend/app/api/layer3.py`; `backend/tests/test_layer3_api.py`; `backend/app/services/layer3_state_action_contract.py` admits exact `internal_dispatch_record_only` while keeping `connector_destination_dispatch` deferred | Records a response-safe internal receipt in existing `L3ReconciliationRecord.summary_json` only; no external connector invocation, destination write, connector-run creation, provider/public URL, package mutation/reconstruction, source widening, qualitative/hybrid/RAG execution, rendered controls, full mockup activation, or auth/security behavior. |
| Generic connector/destination dispatch | Not implemented; remains blocked | `backend/app/services/layer3_state_action_contract.py` keeps `connector_destination_dispatch` deferred; `116_SECURITY_SOURCE_DELIVERY_BOUNDARY_FREEZE.md` and `118_L3_GOAL_AUDIT.md` keep broad dispatch unsupported | Needs a later implementation-entry freeze selecting exactly one broader dispatch mode. |
| Package mutation/reconstruction | Read-only preview route is live; package supersession commit lineage route is live; broad package mutation/reconstruction remains blocked. | `122_PACKAGE_MUTATION_FREEZE.md` selects and bounds `package_supersession_preview_only`; `126_PACKAGE_COMMIT_FREEZE.md` selects and bounds `package_supersession_commit_entry`; `backend/app/services/layer3_package_mutation_entry.py`; `backend/app/services/layer3_package_supersession_commit.py`; `backend/app/api/layer3.py`; `backend/app/models/models.py` `L3PackageSupersessionCommit`; `backend/alembic/versions/0019_layer3_package_supersession_commit.py`; `backend/tests/test_layer3_api.py`; `backend/tests/test_layer3_package_supersession_commit.py`; `backend/app/services/layer3_state_action_contract.py` admits exact read-only preview and lineage-only commit while keeping `package_mutation_reconstruction` deferred; `118_L3_GOAL_AUDIT.md` rejects relabeling package construction/submit/lineage as broad mutation/reconstruction | Existing package construction/submit is bounded and not package rewrite, amendment, supersession, or reconstruction. The preview route does not add persistence. The commit route records immutable lineage only and does not add package row mutation, payload write, replacement package rows, or UI control. |
| Package supersession commit entry | Implemented and guarded as bounded lineage-only runtime | `126_PACKAGE_COMMIT_FREEZE.md`; `backend/app/services/layer3_package_supersession_commit.py`; `backend/app/models/models.py` `L3PackageSupersessionCommit`; `backend/alembic/versions/0019_layer3_package_supersession_commit.py`; `backend/tests/test_layer3_api.py`; `backend/tests/test_layer3_package_supersession_commit.py`; `tools/l3-progress-check.py`; `118_L3_GOAL_AUDIT.md` | Admits only `/api/v1/layer3/package/supersession/commit` as immutable lineage recording from existing source package set to existing replacement package-set authority. No package row mutation, package payload write, replacement package row creation, UI control, connector/destination dispatch, source widening, qualitative/hybrid/RAG execution, provider/public URL, full mockup activation, or auth/security behavior is live. |
| Replacement package-set authority | Implemented and guarded as bounded metadata authority runtime | `127_PACKAGE_REPLACEMENT_SET_FREEZE.md`; `backend/app/services/layer3_replacement_package_set_authority.py`; `backend/app/models/models.py` `L3ReplacementPackageSetAuthority`; `backend/alembic/versions/0018_layer3_replacement_package_set_authority.py`; `backend/tests/test_layer3_api.py`; `backend/tests/test_layer3_replacement_package_set_authority.py`; `tools/l3-progress-check.py`; `118_L3_GOAL_AUDIT.md` | Admits only `replacement_package_set_authority` through `/api/v1/layer3/package/replacement-set/record` and records the live uniqueness blocker `uq_l3_output_package_session_kind`. No replacement `L3OutputPackage` rows, replacement payload writes, UI control, package row mutation, package payload rewrite, connector/destination dispatch, source widening, qualitative/hybrid/RAG execution, provider/public URL, full mockup activation, or auth/security behavior is live. |
| Broad source/upload expansion | Not implemented; remains blocked | `123_SOURCE_EXPANSION_FREEZE.md`; `backend/app/services/layer3_source_boundary.py`; `backend/tests/test_layer3_source_boundary.py`; progress checker verifies supported and unsupported source classes plus the `supported_source_classes_only` contract | Only `dataset_version` and `aps_content_document` are admitted. |
| Qualitative/hybrid/RAG execution | Exact single APS-document qualitative pass implemented; qualitative owner-service errors are proof-hardened; broad qualitative/hybrid/RAG remains blocked | `124_QUAL_HYBRID_RAG_FREEZE.md`; `backend/app/services/layer3_qual_aps_execution.py`; `qualitative_hybrid_rag_boundary_contract()` exposes `single_aps_doc_qualitative_pass_only`; `backend/tests/test_layer3_qual_aps_execution.py`; `test_qualitative_hybrid_rag_boundary_contract_keeps_broad_execution_fail_closed`; `test_single_aps_doc_qualitative_owner_error_maps_without_side_effects`; `backend/app/services/layer3_state_action_contract.py`; progress checker verifies exact/broad split and qualitative owner-service error proof terms | Only `single_aps_doc_qualitative_pass` is admitted. Broad qualitative execution, qualitative cohort execution, comparative execution, cross-document synthesis, hybrid execution, RAG/vector execution, hidden LLM planning, qualitative package/handoff/export, source widening, connector/destination dispatch, and package mutation/reconstruction remain blocked. |
| Full mockup activation | Not implemented; remains blocked with explicit truth-state contract | `125_MOCKUP_TRUTH_STATE_FREEZE.md`; `backend/app/services/layer3_mockup_boundary.py`; `mockup_truth_state_contract()` exposes `mockups_target_state_only`; `backend/app/services/layer3_state_action_contract.py` keeps `full_mockup_activation` admitted false; `backend/tests/test_layer3_mockup_boundary.py`; `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`; `118_L3_GOAL_AUDIT.md` | Mockups are target-state artifacts and do not admit runtime behavior. full mockup activation remains blocked until a later lane names a live source owner, route/API contract, server authority contract, headed/headless browser proof, and negative invariant proof. |
| Authority-boundary preservation | Preserved | `python .\tools\l3-progress-check.py` must pass; focused Layer 3 backend suite must pass; broad capabilities remain `admitted: false` | This is functional-boundary proof through PR #556 plus proof hardening through PR #558, not proof of deferred broad lanes. |

## Validation Evidence

Run from `C:\Users\benny\Downloads\worktree_for_audits`.

```powershell
python .\tools\l3-progress-check.py
```

Expected and observed result during the PR #540 package preview pass:

```text
Layer 3 progress state check: PASS
```

Expected and observed result during the qualitative/hybrid/RAG boundary freeze pass:

```text
Layer 3 progress state check: PASS
```

Expected and observed result during the mockup truth-state boundary freeze pass:

```text
Layer 3 progress state check: PASS
```

Focused backend proof command:

```powershell
$files = Get-ChildItem -Path '.\backend\tests' -Filter 'test_layer3_*.py' | Sort-Object Name | ForEach-Object { ".\backend\tests\$($_.Name)" }; python -m pytest $files -q
```

Observed result during the PR #540 package preview pass:

```text
271 passed, 4 warnings
```

Observed result during the qualitative/hybrid/RAG boundary freeze pass:

```text
273 passed, 4 warnings
```

Observed result during the mockup truth-state boundary freeze pass:

```text
274 passed, 4 warnings
```

Focused qualitative proof:

```text
python -m pytest .\backend\tests\test_layer3_qual_aps_execution.py -q
6 passed
```

Focused qualitative/hybrid/RAG boundary regression:

```text
python -m pytest .\backend\tests\test_layer3_api.py .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_qual_aps_execution.py -q -k "single_aps_doc_qualitative or broad_qualitative or hybrid or rag_vector"
6 passed, 139 deselected, 3 warnings
```

Focused mockup truth-state proof:

```text
python -m pytest .\backend\tests\test_layer3_mockup_boundary.py -q
1 passed
```

Focused mockup/page regression:

```text
python -m pytest .\backend\tests\test_layer3_mockup_boundary.py .\backend\tests\test_layer3_page.py -q
4 passed, 3 warnings
```

The repeated Windows pytest temp cleanup `PermissionError` appeared after successful pytest exit in some runs and did not change the command exit code.

Historical PR #538 local proof retained for earlier invariant checks:

```text
267 passed, 4 warnings
```

PR #538 CI proof:

```text
Pre-merge PR #538 checks: backend-layer3-api SUCCESS; test SUCCESS.
Post-merge main workflow run 25365937051 for 329fc6d5: backend-layer3-api SUCCESS; test SUCCESS.
```

PR #540 CI proof:

```text
Pre-merge PR #540 checks: backend-layer3-api SUCCESS; test SUCCESS.
Merged main head after PR #540: c23a48c1755e7a4f4db6963d0ca430d35b0d80fd.
```

PR #544 CI proof:

```text
Pre-merge PR #544 checks: backend-layer3-api SUCCESS; test SUCCESS.
Merged main head after PR #544: 005ef212753adf2feb859b28362a0bee3d7d72d1.
Post-merge progress proof: Layer 3 progress state check: PASS.
```

PR #545 docs/proof synchronization proof:

```text
Pre-merge PR #545 checks: backend-layer3-api SUCCESS; test SUCCESS.
Merged main head after PR #545: 36526ee1.
Post-merge progress proof: Layer 3 progress state check: PASS.
```

PR #547 preflight DTO boundary proof:

```text
Local focused Layer 3 backend suite: 275 passed, 4 warnings.
Pre-merge PR #547 checks: backend-layer3-api SUCCESS; test SUCCESS.
Merged main head after PR #547: 54c5d8ef.
Post-merge progress proof: Layer 3 progress state check: PASS.
```

PR #548 docs/proof synchronization proof:

```text
Pre-merge PR #548 checks: backend-layer3-api SUCCESS; test SUCCESS.
Merged main head after PR #548: e0183721.
Post-merge progress proof: Layer 3 progress state check: PASS.
```

PR #550 durable Gate B idempotency proof:

```text
Local focused Layer 3 backend suite: 278 passed, 4 warnings.
Pre-merge PR #550 checks: backend-layer3-api SUCCESS; test SUCCESS.
Merged main head after PR #550: 4793d8d1.
Post-merge progress proof: Layer 3 progress state check: PASS.
```

PR #556 package supersession commit lineage proof:

```text
Local focused Layer 3 backend suite: 286 passed, 4 warnings.
Pre-merge PR #556 checks: backend-layer3-api SUCCESS; test SUCCESS.
Merged main head after PR #556: 93fe525b.
Post-merge progress proof: Layer 3 progress state check: PASS.
```

PR #558 qualitative owner-service error-boundary proof:

```text
Focused qualitative owner-service proof: 1 passed.
Focused qualitative APS suite: 7 passed.
Local focused Layer 3 backend suite: 287 passed, 4 warnings.
Pre-merge PR #558 checks: backend-layer3-api SUCCESS; test SUCCESS.
Merged main head after PR #558: 5831ff2f.
Post-merge progress proof: Layer 3 progress state check: PASS.
```

## Merge-Readiness Boundary

Merged as bounded current-main scope:

- canonical state/action contract hardening;
- session-status migration constraint alignment;
- durable Gate B idempotency claim hardening;
- frontend session recovery;
- narrow service extractions;
- same-origin signed-reference service proof;
- preflight DTO boundary hardening;
- plan-preview DTO boundary hardening;
- source-preview DTO boundary hardening;
- material-preview DTO boundary hardening;
- source-boundary extraction and verifier guard;
- single APS-document qualitative execution;
- qualitative/hybrid/RAG boundary proof;
- qualitative owner-service error-boundary proof;
- mockup truth-state boundary proof;
- read-only package supersession preview;
- metadata-only replacement package-set authority;
- lineage-only package supersession commit entry;
- proof/state drift checks;
- goal-audit closeout state.

Not ready to claim:

- generic connector/destination dispatch beyond `internal_dispatch_record_only`;
- package mutation/reconstruction beyond read-only `package_supersession_preview_only`, metadata-only `replacement_package_set_authority`, and lineage-only `package_supersession_commit_entry`;
- broad source/upload expansion;
- broad qualitative execution outside `single_aps_doc_qualitative_pass`;
- hybrid execution;
- RAG/vector execution;
- provider/public URL support;
- full mockup activation;
- authentication/security hardening.

## Next Decision

After this functional-boundary snapshot, any later runtime expansion must start with a separate implementation-entry freeze that selects exactly one currently deferred lane and proves live authority for it. Without that evidence, the next admissible work remains narrow proof/state/refactor hardening or docs/proof synchronization only.
