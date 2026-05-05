# Layer 3 Bounded Branch Closeout

Status: local branch closeout for `codex/l3-frontend-session-recovery` after material-preview DTO boundary hardening.

This file is review/merge preparation only. It does not admit new runtime behavior, implement a deferred lane, or replace live source/tests as authority.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- branch: `codex/l3-frontend-session-recovery`
- latest committed branch head before this material-preview closeout update: `789a00c3`
- current baseline ref: `project6-origin/main`
- known local caveat: `.omc/state/hud-state.json`, `.omc/state/hud-stdin-cache.json`, `.codesight/`, `.cursorrules`, `.github/copilot-instructions.md`, `CLAUDE.md`, and `codex.md` are local operator/sidecar state and are not implementation evidence.

Authority order for this closeout:

1. Live source and tests.
2. Local command output.
3. `tools/l3-progress-check.py`.
4. `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md` and `118_L3_GOAL_AUDIT.md`.
5. Older planning docs and mockups only as target-state or historical context.

## Prompt-To-Artifact Checklist

| Goal item | Closeout disposition | Concrete evidence | Scope limit |
| --- | --- | --- | --- |
| Synthesis critical items before broader work | Partially complete and bounded | `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`; `118_L3_GOAL_AUDIT.md`; `tools/l3-progress-check.py` | Auth/security remains deferred; broad activation remains blocked. |
| Canonical state/action contract | Implemented and guarded | `backend/app/services/layer3_state_action_contract.py`; `backend/tests/test_layer3_workbench.py`; `backend/tests/test_layer3_api.py`; progress checker verifies admitted/deferred capability split | Deferred capability ids are not action ids. |
| Frontend session recovery | Implemented earlier on this branch | `backend/app/review_ui/static/layer3.js`; `backend/tests/test_layer3_page.py`; `e2e/layer3-workbench.spec.js`; recorded headed/headless proof in `118_L3_GOAL_AUDIT.md` | Server-revalidated recovery only; not frontend-only durable state or full mockup activation. |
| Service extraction to reduce workbench risk | Implemented narrowly | `backend/app/services/layer3_plan_revision_state.py`; `backend/app/services/layer3_gate_b_state.py`; `backend/app/services/layer3_source_boundary.py`; related tests | No broad `layer3_workbench.py` rewrite. |
| Same-origin signed-reference service proof | Implemented and guarded | `backend/app/services/layer3_signed_reference_state.py`; `backend/tests/test_layer3_signed_reference_state.py`; progress checker verifies the atomic conditional update and lifecycle/concurrent-use proof | Same-origin signed-reference state only; no provider/public URL, revocation API, connector/destination dispatch, or broad delivery behavior. |
| Plan-preview DTO boundary | Implemented and guarded | `backend/app/api/layer3.py` `Layer3PlanPreviewRequest`; `backend/tests/test_layer3_api.py::test_layer3_api_plan_preview_rejects_extra_fields_before_service_mutation`; progress checker verifies the strict request boundary | Plan preview known fields only; no plan materialization, execution, package, handoff, source widening, mockup, or auth/security behavior change. |
| Source-preview DTO boundary | Implemented and guarded | `backend/app/api/layer3.py` `Layer3SourcePreviewRequest`; `backend/tests/test_layer3_api.py::test_layer3_api_source_preview_rejects_extra_fields_before_service_execution`; progress checker verifies the strict request boundary | Source preview known fields only; no broad upload, local directory ingestion, RAG/vector source, web connector source, runtime DB widening, connector/destination dispatch, package mutation/reconstruction, provider/public URL, mockup, or auth/security behavior change. |
| Material-preview DTO boundary | Implemented and guarded | `backend/app/api/layer3.py` `Layer3MaterialPreviewRequest`; `backend/tests/test_layer3_api.py::test_layer3_api_material_preview_rejects_extra_fields_before_service_execution`; progress checker verifies the strict request boundary | Material preview known fields only; no broad upload, local directory ingestion, RAG/vector source, web connector source, runtime DB widening, connector/destination dispatch, package mutation/reconstruction, provider/public URL, mockup, or auth/security behavior change. |
| Connector/destination dispatch | Not implemented; remains blocked | `backend/app/services/layer3_state_action_contract.py` keeps `connector_destination_dispatch` deferred; `116_SECURITY_SOURCE_DELIVERY_BOUNDARY_FREEZE.md` and `118_L3_GOAL_AUDIT.md` keep broad dispatch unsupported | Needs a later implementation-entry freeze selecting exactly one dispatch mode. |
| Package mutation/reconstruction | Not implemented; remains blocked | `backend/app/services/layer3_state_action_contract.py` keeps `package_mutation_reconstruction` deferred; `118_L3_GOAL_AUDIT.md` rejects relabeling package construction/submit as mutation/reconstruction | Existing package construction/submit is bounded and not package rewrite, amendment, supersession, or reconstruction. |
| Broad source/upload expansion | Not implemented; remains blocked | `backend/app/services/layer3_source_boundary.py`; `backend/tests/test_layer3_source_boundary.py`; progress checker verifies supported and unsupported source classes | Only `dataset_version` and `aps_content_document` are admitted. |
| Qualitative/hybrid/RAG execution | Exact single APS-document qualitative pass implemented; broad qualitative/hybrid/RAG remains blocked | `backend/app/services/layer3_qual_aps_execution.py`; `backend/tests/test_layer3_qual_aps_execution.py`; `backend/app/services/layer3_state_action_contract.py`; progress checker verifies exact/broad split | Only `single_aps_doc_qualitative_pass` is admitted. |
| Full mockup activation | Not implemented; remains blocked | `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`; `118_L3_GOAL_AUDIT.md` | Mockups are target-state artifacts and do not admit runtime behavior. |
| Authority-boundary preservation | Preserved | `python .\tools\l3-progress-check.py` passes; focused Layer 3 backend suite passed with `263 passed`; broad capabilities remain `admitted: false` | This is branch-local proof, not merged-main proof. |

## Validation Evidence

Run from `C:\Users\benny\Downloads\worktree_for_audits`.

```powershell
python .\tools\l3-progress-check.py
```

Expected and observed result after material-preview DTO boundary hardening:

```text
Layer 3 progress state check: PASS
```

Focused backend proof command:

```powershell
$layer3Tests = Get-ChildItem -Path '.\backend\tests' -Filter 'test_layer3_*.py' | Sort-Object Name | ForEach-Object { ".\backend\tests\$($_.Name)" }; python -m pytest @layer3Tests -q
```

Observed result during this closeout pass:

```text
263 passed, 4 warnings
```

The repeated Windows pytest temp cleanup `PermissionError` appeared after successful pytest exit in some runs and did not change the command exit code.

## Merge-Readiness Boundary

Ready to review as a bounded branch:

- canonical state/action contract hardening;
- frontend session recovery;
- narrow service extractions;
- same-origin signed-reference service proof;
- plan-preview DTO boundary hardening;
- source-preview DTO boundary hardening;
- material-preview DTO boundary hardening;
- source-boundary extraction and verifier guard;
- single APS-document qualitative execution;
- proof/state drift checks;
- goal-audit closeout state.

Not ready to claim:

- generic connector/destination dispatch;
- package mutation/reconstruction;
- broad source/upload expansion;
- broad qualitative execution outside `single_aps_doc_qualitative_pass`;
- hybrid execution;
- RAG/vector execution;
- provider/public URL support;
- full mockup activation;
- authentication/security hardening.

## Next Decision

The next productive step is local review/merge preparation for this bounded branch. Any later runtime expansion must start with a separate implementation-entry freeze that selects exactly one currently deferred lane and proves live authority for it.
