# Layer 3 Goal Audit

Status: current-main completion audit after PR #535 merged at `project6-origin/main=7d07477a`.

This file is not an implementation freeze and does not admit new runtime behavior. It maps the active goal to current local evidence so future work does not confuse implemented bounded slices with still-blocked broad capabilities.

## Authority Boundary

- Live source, tests, and local command output outrank this note.
- `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md` remains the current post-synthesis overclaim guardrail.
- Authentication/security hardening remains deferred by operator instruction and is not reopened here.
- Mockups, Codesight sidecars, progress prose, and prior PR numbers are not completion proof without live source/test evidence.

## Prompt-To-Artifact Checklist

| Goal item | Current disposition | Evidence | Missing or blocked scope |
| --- | --- | --- | --- |
| Synthesis critical items before broader work | Partially complete, current-main | `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md` records proof for missing-artifact fail-closed behavior, model exports, plan-revision service extraction, session-status migration constraint alignment, selection-manifest mismatch, API error envelope, plan-preview DTO boundary proof, source-preview DTO boundary proof, material-preview DTO boundary proof, package-hash canonicalization, source-boundary guard proof, same-origin signed-reference lifecycle/concurrent single-use proof, and PR #535 merged-main verification. | Authentication/security is explicitly deferred. Broad capability activation remains blocked. |
| Canonical state/action contract | Implemented and tested, current-main | `backend/app/services/layer3_state_action_contract.py`; `backend/app/services/layer3_workbench.py`; `backend/tests/test_layer3_workbench.py`; `backend/tests/test_layer3_api.py`; `python -m pytest <backend/tests/test_layer3*.py> -q` passed; post-merge `main` workflow passed. | Does not admit deferred capabilities as action ids. |
| Frontend session recovery | Implemented and tested, current-main | `backend/app/review_ui/static/layer3.js`; `backend/tests/test_layer3_page.py`; `e2e/layer3-workbench.spec.js`; headed and headless `layer3-workbench.spec.js` passed; post-merge `main` workflow passed. | Browser recovery is server-revalidated cache/restore behavior only, not frontend-only durable state. |
| Service extraction to reduce workbench risk | Implemented narrowly, current-main | `backend/app/services/layer3_plan_revision_state.py`; `backend/tests/test_layer3_plan_revision_state.py`; `backend/app/services/layer3_gate_b_state.py`; `backend/tests/test_layer3_gate_b_state.py`; `backend/app/services/layer3_source_boundary.py`; `backend/tests/test_layer3_source_boundary.py`. | Does not complete a broad `layer3_workbench.py` split, does not widen source classes, and does not change behavior outside extracted owner surfaces. |
| Connector/destination dispatch | Not implemented; implementation-entry freeze selected for the next narrow lane | `112_CONNECTOR_DISPATCH_FREEZE.md`; `113_CONNECTOR_DISPATCH_CONTRACT.md`; `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md`; `105_deferred-gates.md`; `backend/app/services/layer3_state_action_contract.py` keeps broad `connector_destination_dispatch` unadmitted. | Only `internal_dispatch_record_only` is selected for a future code slice. External connector invocation, destination writes, generic downstream dispatch, provider/public URLs, package mutation/reconstruction, source widening, qualitative/hybrid/RAG execution, rendered controls, and full mockup activation remain blocked. |
| Package mutation/reconstruction | Not implemented; blocked | `105_deferred-gates.md`; `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`; `backend/app/services/layer3_state_action_contract.py` keeps `package_mutation_reconstruction` unadmitted. | Existing bounded package construction/submit is not package mutation, reconstruction, amendment, supersession, or payload rewrite. |
| Broad source/upload expansion | Not implemented; blocked | `backend/app/services/layer3_source_boundary.py` keeps `SUPPORTED_SOURCE_CLASSES == ("dataset_version", "aps_content_document")` and `UNSUPPORTED_SOURCE_CLASSES == ("rag_vector_index", "arbitrary_local_directory", "broad_file_upload", "web_connector", "unbounded_runtime_db")`; `backend/tests/test_layer3_source_boundary.py` proves the extracted boundary rejects deferred source families. | Requires a later source/runtime widening freeze before local upload, directory source, RAG/vector source, or web connector source work. |
| Qualitative/hybrid/RAG execution | Single APS-document qualitative execution is implemented and tested on current-main; hybrid and RAG/vector execution remain blocked | `114_QUAL_APS_EXEC_FREEZE.md`; `115_QUAL_APS_EXEC_CONTRACT.md`; `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md`; `backend/app/services/layer3_qual_aps_execution.py`; `backend/app/services/layer3_pass_entry.py`; `backend/app/services/layer3_workbench.py`; `backend/tests/test_layer3_qual_aps_execution.py`; `python -m pytest .\backend\tests\test_layer3_qual_aps_execution.py -q` passed; focused and full Layer 3 suites passed; post-merge `main` workflow passed. | Only `single_aps_doc_qualitative_pass` is admitted. Broad qualitative execution, hybrid execution, RAG/vector execution, qualitative package/handoff/export, and hidden LLM planning remain no-go lanes. |
| Full mockup activation | Not implemented; blocked | `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md` states mockups are target-state design/spec artifacts and cannot admit broad features. `e2e/layer3-workbench.spec.js` proves bounded rendered behavior only. | Full mockup activation would require separate freezes per capability and browser proof; current UI slices are not full mockup behavior. |
| Authority-boundary preservation | Current main preserves it | `single_aps_doc_qualitative_execution` is recorded as an exact admitted capability; broad/deferred capabilities remain `admitted: false`; same-origin signed-reference state is guarded by `backend/app/services/layer3_signed_reference_state.py` and `backend/tests/test_layer3_signed_reference_state.py`; `0012_layer3_session_entry.py` and `test_layer3_session_entry_migration_defines_status_check_constraint` guard the `L3Session.status` migration constraint; `Layer3PlanPreviewRequest` and `test_layer3_api_plan_preview_rejects_extra_fields_before_service_mutation` guard the plan-preview request boundary; `Layer3SourcePreviewRequest` and `test_layer3_api_source_preview_rejects_extra_fields_before_service_execution` guard the source-preview request boundary; `Layer3MaterialPreviewRequest` and `test_layer3_api_material_preview_rejects_extra_fields_before_service_execution` guard the material-preview request boundary; local proof includes `python -m pytest` over the explicit `backend/tests/test_layer3_*.py` file list with `264 passed`, `python .\tools\l3-progress-check.py`, headed/headless browser proof from the frontend recovery slice, PR #535 checks, and post-merge `main` workflow success. | Any future lane must re-run this audit against fresh source before broadening scope. |

## Completion Decision

The active goal is not complete.

Implemented, tested, audited, and merged current-main items include the canonical state/action contract, session-status migration constraint alignment, frontend session recovery, narrow service extraction, source-boundary extraction, Gate B/session/status/idempotency hardening, DTO/error-boundary proof including plan-preview, source-preview, and material-preview DTO boundary hardening, package-hash proof, same-origin signed-reference lifecycle/concurrent single-use proof, single APS-document qualitative execution, and several fail-closed downstream checks.

The following named goal items remain intentionally unavailable because current authority blocks implementation rather than merely lacking code:

- generic connector/destination dispatch; `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md` selects only future `internal_dispatch_record_only` planning authority and does not implement runtime dispatch;
- package mutation/reconstruction;
- broad source/upload expansion;
- broad qualitative execution beyond the single APS-document qualitative pass, hybrid execution, and RAG/vector execution;
- full mockup activation;
- authentication/security hardening.

Treating bounded APS owner-service dispatch, package construction/submit, same-origin delivery, or same-origin signed references as completion of those broader items would be an overclaim.

## Next Admissible Work

The next runtime implementation is blocked unless a later freeze selects exactly one currently deferred lane with concrete authority evidence.

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
