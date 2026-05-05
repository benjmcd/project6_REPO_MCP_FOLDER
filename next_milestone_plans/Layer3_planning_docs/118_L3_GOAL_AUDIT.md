# Layer 3 Goal Audit

Status: current-main completion audit after PR #538 merged at `project6-origin/main=329fc6d5`, later refreshed after PR #539 merged at `project6-origin/main=c44a8762`, refreshed again after PR #540 merged at `project6-origin/main=c23a48c1`, and refreshed after PR #542 merged at `project6-origin/main=c134b581`.

This file is not itself an implementation freeze. It maps the active goal to current local evidence so future work does not confuse exact bounded slices with still-blocked broad capabilities.

## Authority Boundary

- Live source, tests, and local command output outrank this note.
- `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md` remains the current post-synthesis overclaim guardrail.
- Authentication/security hardening remains deferred by operator instruction and is not reopened here.
- Mockups, Codesight sidecars, progress prose, and prior PR numbers are not completion proof without live source/test evidence.

Historical merged-main proof is retained as authority for earlier invariant checks, not upgraded into proof of broader deferred lanes: PR #538 established current-main proof with `267 passed`; it covered `Layer3PlanPreviewRequest`, `Layer3SourcePreviewRequest`, `Layer3MaterialPreviewRequest`, `test_layer3_api_plan_preview_rejects_extra_fields_before_service_mutation`, `test_layer3_api_source_preview_rejects_extra_fields_before_service_execution`, `test_layer3_api_material_preview_rejects_extra_fields_before_service_execution`, `0012_layer3_session_entry.py`, and `test_layer3_session_entry_migration_defines_status_check_constraint`. PR #540 separately established the exact read-only `package_supersession_preview_only` runtime on current main. PR #542 separately established the `supported_source_classes_only` source boundary with `272 passed`.

## Prompt-To-Artifact Checklist

| Goal item | Current disposition | Evidence | Missing or blocked scope |
| --- | --- | --- | --- |
| Synthesis critical items before broader work | Partially complete, current-main | `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md` records proof for missing-artifact fail-closed behavior, model exports, plan-revision service extraction, session-status migration constraint alignment, selection-manifest mismatch, API error envelope, plan-preview DTO boundary proof, source-preview DTO boundary proof, material-preview DTO boundary proof, package-hash canonicalization, source-boundary guard proof, same-origin signed-reference lifecycle/concurrent single-use proof, and PR #535 merged-main verification. | Authentication/security is explicitly deferred. Broad capability activation remains blocked. |
| Canonical state/action contract | Implemented and tested, current-main | `backend/app/services/layer3_state_action_contract.py`; `backend/app/services/layer3_workbench.py`; `backend/tests/test_layer3_workbench.py`; `backend/tests/test_layer3_api.py`; `python -m pytest <backend/tests/test_layer3*.py> -q` passed; post-merge `main` workflow passed. | Does not admit deferred capabilities as action ids. |
| Frontend session recovery | Implemented and tested, current-main | `backend/app/review_ui/static/layer3.js`; `backend/tests/test_layer3_page.py`; `e2e/layer3-workbench.spec.js`; headed and headless `layer3-workbench.spec.js` passed; post-merge `main` workflow passed. | Browser recovery is server-revalidated cache/restore behavior only, not frontend-only durable state. |
| Service extraction to reduce workbench risk | Implemented narrowly, current-main | `backend/app/services/layer3_plan_revision_state.py`; `backend/tests/test_layer3_plan_revision_state.py`; `backend/app/services/layer3_gate_b_state.py`; `backend/tests/test_layer3_gate_b_state.py`; `backend/app/services/layer3_source_boundary.py`; `backend/tests/test_layer3_source_boundary.py`. | Does not complete a broad `layer3_workbench.py` split, does not widen source classes, and does not change behavior outside extracted owner surfaces. |
| Connector/destination dispatch | Internal record-only implementation is live and tested; broad dispatch remains blocked | `112_CONNECTOR_DISPATCH_FREEZE.md`; `113_CONNECTOR_DISPATCH_CONTRACT.md`; `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md`; `backend/app/services/layer3_connector_dispatch_entry.py`; `backend/app/api/layer3.py`; `backend/tests/test_layer3_api.py`; `tools/l3-progress-check.py`; `backend/app/services/layer3_state_action_contract.py` keeps broad `connector_destination_dispatch` unadmitted while admitting exact `internal_dispatch_record_only`. | Only `internal_dispatch_record_only` is admitted. External connector invocation, destination writes, generic downstream dispatch, provider/public URLs, package mutation/reconstruction, source widening, qualitative/hybrid/RAG execution, rendered controls, and full mockup activation remain blocked. |
| Package mutation/reconstruction | Read-only supersession preview implementation is live and tested on current main; broad package mutation/reconstruction commit remains blocked | `105_deferred-gates.md`; `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`; `122_PACKAGE_MUTATION_FREEZE.md`; `backend/app/services/layer3_package_mutation_entry.py`; `backend/app/api/layer3.py`; `backend/tests/test_layer3_api.py`; `backend/app/services/layer3_state_action_contract.py` keeps `package_mutation_reconstruction` unadmitted while admitting exact `package_supersession_preview_only`. | Only `package_supersession_preview_only` is admitted. Existing bounded package construction/submit is not package mutation, reconstruction, amendment, supersession, or payload rewrite. Package row mutation, payload rewrite, supersession commit, provider/public URLs, connector/destination dispatch, source widening, qualitative/hybrid/RAG execution, rendered controls, full mockup activation, and authentication/security work remain blocked. |
| Broad source/upload expansion | Not implemented; blocked | `123_SOURCE_EXPANSION_FREEZE.md`; `backend/app/services/layer3_source_boundary.py` keeps `SUPPORTED_SOURCE_CLASSES == ("dataset_version", "aps_content_document")` and `UNSUPPORTED_SOURCE_CLASSES == ("rag_vector_index", "arbitrary_local_directory", "broad_file_upload", "web_connector", "unbounded_runtime_db")`; `source_boundary_contract()` exposes `supported_source_classes_only` with source upload, local directory, broad file upload, web connector, RAG/vector, and unbounded runtime DB flags false; `backend/tests/test_layer3_source_boundary.py` proves the extracted boundary rejects deferred source families and does not widen source classes. | Requires a later source/runtime widening freeze before local upload, directory source, RAG/vector source, or web connector source work. |
| Qualitative/hybrid/RAG execution | Single APS-document qualitative execution is implemented and tested on current-main; broad qualitative, hybrid, and RAG/vector execution remain blocked | `114_QUAL_APS_EXEC_FREEZE.md`; `115_QUAL_APS_EXEC_CONTRACT.md`; `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md`; `124_QUAL_HYBRID_RAG_FREEZE.md`; `backend/app/services/layer3_qual_aps_execution.py`; `qualitative_hybrid_rag_boundary_contract()` exposes `single_aps_doc_qualitative_pass_only` with broad qualitative/hybrid/RAG flags false; `backend/app/services/layer3_pass_entry.py`; `backend/app/services/layer3_workbench.py`; `backend/tests/test_layer3_qual_aps_execution.py`; `test_qualitative_hybrid_rag_boundary_contract_keeps_broad_execution_fail_closed`; `python -m pytest .\backend\tests\test_layer3_qual_aps_execution.py -q` passed; focused and full Layer 3 suites passed; post-merge `main` workflow passed. | Only `single_aps_doc_qualitative_pass` is admitted. Broad qualitative execution, qualitative cohort execution, comparative execution, cross-document synthesis, hybrid execution, RAG/vector execution, qualitative package/handoff/export, hidden LLM planning, source widening, connector/destination dispatch, and package mutation/reconstruction remain no-go lanes. |
| Full mockup activation | Not implemented; blocked with explicit truth-state contract | `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md` states mockups are target-state design/spec artifacts and cannot admit broad features; `125_MOCKUP_TRUTH_STATE_FREEZE.md`; `backend/app/services/layer3_mockup_boundary.py`; `mockup_truth_state_contract()` exposes `mockups_target_state_only`; `backend/app/services/layer3_state_action_contract.py` keeps `full_mockup_activation` admitted false with reason `mockups_target_state_only`; `backend/tests/test_layer3_mockup_boundary.py`; `e2e/layer3-workbench.spec.js` proves bounded rendered behavior only. | Full mockup activation would require separate freezes per capability plus live source owner, route/API contract, server authority contract, negative invariant proof, headed browser proof, and headless browser proof; current UI slices are not full mockup behavior. |
| Authority-boundary preservation | Preserved on current main | `single_aps_doc_qualitative_execution`, `internal_dispatch_record_only`, and `package_supersession_preview_only` are current-main exact admitted capabilities. Broad/deferred capabilities remain `admitted: false`; same-origin signed-reference state is guarded by `backend/app/services/layer3_signed_reference_state.py` and `backend/tests/test_layer3_signed_reference_state.py`; `0012_layer3_session_entry.py` and `test_layer3_session_entry_migration_defines_status_check_constraint` guard the `L3Session.status` migration constraint; plan/source/material DTO boundary tests guard request boundaries; internal connector dispatch record remains exact `internal_dispatch_record_only`; package mutation/reconstruction is admitted only as read-only `package_supersession_preview_only`. | Any future lane must re-run this audit against fresh source before broadening scope. |

## Completion Decision

The active goal is not complete.

Implemented, tested, audited, and merged current-main items include the canonical state/action contract, session-status migration constraint alignment, frontend session recovery, narrow service extraction, source-boundary extraction, Gate B/session/status/idempotency hardening, DTO/error-boundary proof including plan-preview, source-preview, and material-preview DTO boundary hardening, package-hash proof, same-origin signed-reference lifecycle/concurrent single-use proof, single APS-document qualitative execution, qualitative/hybrid/RAG boundary proof, mockup truth-state boundary proof, and several fail-closed downstream checks.

The following named goal items remain intentionally unavailable because current authority blocks implementation rather than merely lacking code:

- generic connector/destination dispatch beyond the live `internal_dispatch_record_only` internal record lane;
- package mutation/reconstruction beyond read-only `package_supersession_preview_only`;
- broad source/upload expansion;
- broad qualitative execution beyond the single APS-document qualitative pass, hybrid execution, and RAG/vector execution;
- full mockup activation;
- authentication/security hardening.

Treating bounded APS owner-service dispatch, package construction/submit, same-origin delivery, same-origin signed references, `internal_dispatch_record_only`, or read-only `package_supersession_preview_only` as completion of broad connector/destination dispatch or package mutation/reconstruction commit would be an overclaim.

## Next Admissible Work

The next broad runtime implementation is blocked unless a later freeze selects exactly one currently deferred lane with concrete authority evidence.

Supported next actions are:

- a post-merge docs/proof sync when current-main wording drifts from merged authority;
- a future implementation-entry freeze for broad qualitative, hybrid, or RAG/vector execution if live evidence justifies one narrow lane;
- a docs/proof-only implementation-entry freeze for another deferred lane if live evidence justifies it;
- additional narrow proof/state/refactor hardening if fresh source inspection finds a concrete uncovered edge.

Unsupported next actions are:

- broad connector/destination dispatch, including external connector invocation or destination writes;
- package rewrite/reconstruction;
- broad upload/local-directory/RAG/vector source expansion;
- broad qualitative execution outside the `single_aps_doc_qualitative_pass` freeze, hybrid execution, or any RAG execution;
- full mockup activation;
- authentication/security work while it remains deferred.
