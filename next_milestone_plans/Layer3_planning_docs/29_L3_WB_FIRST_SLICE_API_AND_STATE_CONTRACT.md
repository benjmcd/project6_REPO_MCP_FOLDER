# 29 L3 Workbench First Slice API And State Contract

## Status
- planning-only
- not active implementation
- companion contract for `28_L3_WB_FIRST_SLICE_FREEZE.md`
- does not reopen the settled APS packet
- does not change merged milestone counts by itself
- does not activate or make `/review/layer3` or `/api/v1/layer3/...` live
- does not admit schema widening, runtime snapshot DB writes, RAG/vector retrieval, qualitative execution, hybrid execution, package review, or handoff scope

## Purpose
Freeze the endpoint, DTO, state, persistence, and proof contract for the first Layer 3 workbench implementation slice before any code branch builds `/review/layer3` or `/api/v1/layer3/...`.

`28_L3_WB_FIRST_SLICE_FREEZE.md` freezes the first-slice scope. This document freezes the API and state contract under that scope so implementation can proceed without inventing endpoint shapes, browser-only authority, or ad hoc persistence while coding.

## Authority Order
1. Current `project6-origin/main` repo truth.
2. `next_milestone_plans/layer3_progress_manifest.json`.
3. `next_milestone_plans/layer3_progress_board.md`.
4. `24_L3_WB_FREEZE.md`.
5. `26_L3_WB_INPUTS.md`.
6. `28_L3_WB_FIRST_SLICE_FREEZE.md`.
7. This file, for endpoint, DTO, state, and persistence details only.
8. `next_milestone_plans/layer3-mockups/mockup-spec.txt`.
9. `next_milestone_plans/layer3-mockups/assets.md`.

This file is subordinate to the no-go list in `28_L3_WB_FIRST_SLICE_FREEZE.md`. If this file appears to admit a wider scope, the narrower no-go list wins.

## Repo-Confirmed Starting Truth
- Current `main` does not ship `/review/layer3`.
- Current `main` does not ship `/api/v1/layer3/...`.
- Current `main` already ships Layer 3 owner services for session, typing, pass, and package entry.
- Current `main` already has model surfaces for session, selection manifest, descriptor, retrieval event, material snapshot, typing record, analysis unit/group/set, pass run, reconciliation record, and output package.
- Current `main` has JSON-bearing fields that may carry bounded first-slice control state without a migration if the contract is explicit.
- Current `main` does not have a first-class Gate B decision table.
- Current `main` does not have an implemented operator-facing Gate C override workflow.
- Current `layer3_pass_entry.py` is quantitative-first and must not be treated as a generic qualitative/hybrid analysis engine.
- Current package/reconciliation code is real backend capability but package review UI is not first-slice scope.

## First-Slice Contract Boundary
The first implementation slice may implement:
- static `/review/layer3` shell reachability
- `/api/v1/layer3` bootstrap
- intent preflight
- deterministic source preview
- deterministic material preview
- Gate B material decision recording
- Gate C typing preview
- explicit Gate C override unavailability, or a fully proven bounded override path if implemented exactly under this contract
- persistent authority/context rail payload
- visible unavailable downstream placeholders

The first implementation slice must not implement:
- analysis execution
- qualitative or hybrid execution
- RAG/vector indexing or semantic retrieval
- arbitrary local directory ingestion
- broad file upload handling
- package review or handoff initiation
- runtime snapshot DB writes
- new schema or migration
- React/client-router/component-library adoption
- rewrites of existing review/document-trace/Workbench Compare/Candidate B/analyst-insight behavior
- hidden LLM planning or unreviewed natural-language decomposition

## Endpoint List
The only admitted first-slice API family is `/api/v1/layer3/...`.

| Method | Path | Purpose | Write posture |
| --- | --- | --- | --- |
| GET | `/api/v1/layer3/bootstrap` | Return UI configuration, supported source classes, gate labels, disabled downstream states, and authority defaults. | Read-only |
| POST | `/api/v1/layer3/preflight` | Normalize intent and manual constraints, report blockers and warnings, and return a preflight token. | Read-only |
| POST | `/api/v1/layer3/source-preview` | Convert normalized intent into allowlisted source candidates. | Read-only |
| POST | `/api/v1/layer3/material-preview` | Produce deterministic material candidates from the selected source candidates. | Read-only |
| POST | `/api/v1/layer3/gate-b/decision` | Persist explicit Gate B decisions and create a deliberate Layer 3 session for approved material only. | Existing Layer 3 control persistence only |
| POST | `/api/v1/layer3/gate-c/preview` | Preview or materialize Gate C typing/unit/group/set posture through existing owner services. | Read-only unless explicitly committed through owner services |
| POST | `/api/v1/layer3/gate-c/override` | Return explicit unavailable state unless bounded override persistence is fully implemented and tested. | Existing Layer 3 control persistence only if enabled |
| GET | `/api/v1/layer3/session/{session_id}` | Return persisted first-slice session summary and authority rail state. | Read-only |

No route outside this API family is admitted by this document.

## Common DTO Rules
Every response must include:
- `schema_id`
- `schema_version`
- `request_id`
- `server_time`
- `status`

Every state-changing request must include:
- `schema_id`
- `client_request_id`
- `actor`
- `operator_reason` when the request changes durable review state

Allowed response statuses:
- `ok`
- `blocked`
- `invalid`
- `unavailable`
- `conflict`
- `failed`

No response may imply that analysis execution, package review, RAG/vector, qualitative execution, or hybrid execution is active.

## Error DTO
All non-`ok` responses must use this shape:

```json
{
  "schema_id": "layer3.workbench_error.v1",
  "schema_version": 1,
  "request_id": "string",
  "status": "blocked | invalid | unavailable | conflict | failed",
  "error_code": "string",
  "message": "string",
  "recoverable": true,
  "blocked_fields": [],
  "next_allowed_actions": []
}
```

Minimum error codes:
- `empty_intent`
- `conflicting_constraints`
- `unsupported_source_class`
- `unavailable_source`
- `no_source_candidates`
- `no_material_candidates`
- `partial_material_preview`
- `invalid_material_candidate`
- `duplicate_material_candidate`
- `no_approved_material`
- `session_not_found`
- `typing_not_ready`
- `typing_already_materialized`
- `unsupported_typing_shape`
- `override_unavailable`
- `override_invalid_transition`
- `downstream_unavailable`
- `owner_service_error`

## Bootstrap Contract
`GET /api/v1/layer3/bootstrap` returns what the UI may display as active.

Required response:

```json
{
  "schema_id": "layer3.workbench_bootstrap.v1",
  "schema_version": 1,
  "route": "/review/layer3",
  "api_root": "/api/v1/layer3",
  "supported_source_classes": ["dataset_version", "aps_content_document"],
  "preview_only_source_classes": [],
  "unsupported_source_classes": [
    "rag_vector_index",
    "arbitrary_local_directory",
    "broad_file_upload",
    "web_connector",
    "unbounded_runtime_db"
  ],
  "gate_labels": ["intent", "sources", "gate_b", "gate_c", "plan", "execution", "results", "package"],
  "active_gate_labels": ["intent", "sources", "gate_b", "gate_c"],
  "unavailable_gate_labels": ["plan", "execution", "results", "package"],
  "features": {
    "analysis_execution": false,
    "qualitative_execution": false,
    "hybrid_execution": false,
    "rag_vector_retrieval": false,
    "package_review": false,
    "handoff": false,
    "runtime_snapshot_db_writes": false,
    "schema_widening": false,
    "typing_override_enabled": false
  },
  "authority_rail": {
    "session_id": null,
    "preflight_id": null,
    "source_set_id": null,
    "current_gate": "intent",
    "persistence_mode": "not_committed",
    "browser_only_state": ["expanded_rows", "hidden_uncommitted_candidates", "selected_tab"]
  }
}
```

`typing_override_enabled` must remain `false` unless the implementation satisfies the Gate C override section below.

## Preflight Contract
`POST /api/v1/layer3/preflight` normalizes operator intent and constraints without creating a Layer 3 session.

Request:

```json
{
  "schema_id": "layer3.preflight_request.v1",
  "schema_version": 1,
  "client_request_id": "string",
  "natural_language_intent": "string",
  "manual_constraints": {
    "entities": [],
    "topics": [],
    "source_classes": [],
    "date_bounds": null,
    "required_artifacts": []
  },
  "actor": "operator"
}
```

Response:

```json
{
  "schema_id": "layer3.preflight_result.v1",
  "schema_version": 1,
  "preflight_id": "stable_hash_or_uuid",
  "normalized_intent": {
    "intent_text": "string",
    "manual_constraints": {}
  },
  "blockers": [],
  "warnings": [],
  "eligible_for_source_selection": true,
  "authority_rail": {}
}
```

Preflight must fail closed on empty intent, conflicting constraints, unsupported source classes, and unavailable runtime/source authority.

## Source Preview Contract
`POST /api/v1/layer3/source-preview` returns source candidates only from allowlisted deterministic source classes.

Request:

```json
{
  "schema_id": "layer3.source_preview_request.v1",
  "schema_version": 1,
  "client_request_id": "string",
  "preflight_id": "string",
  "selected_source_classes": ["dataset_version"],
  "actor": "operator"
}
```

Response:

```json
{
  "schema_id": "layer3.source_preview_result.v1",
  "schema_version": 1,
  "source_set_id": "stable_hash_or_uuid",
  "source_candidates": [
    {
      "source_candidate_id": "string",
      "source_class": "dataset_version | aps_content_document",
      "source_label": "string",
      "source_ref": "string",
      "source_authority": "repo_supported",
      "eligible_for_material_preview": true,
      "unavailable_reason": null
    }
  ],
  "unsupported_sources": [],
  "authority_rail": {}
}
```

The endpoint must not claim arbitrary connector, web, local-directory, upload, RAG/vector, or runtime-DB source support.

## Material Preview Contract
`POST /api/v1/layer3/material-preview` returns candidate material. Candidate material is not approved material and is not a committed session.

Request:

```json
{
  "schema_id": "layer3.material_preview_request.v1",
  "schema_version": 1,
  "client_request_id": "string",
  "preflight_id": "string",
  "source_set_id": "string",
  "source_candidate_ids": [],
  "query_basis": {
    "terms": [],
    "filters": {}
  },
  "actor": "operator"
}
```

Response:

```json
{
  "schema_id": "layer3.material_preview_result.v1",
  "schema_version": 1,
  "material_preview_id": "stable_hash_or_uuid",
  "material_candidates": [
    {
      "candidate_id": "string",
      "source_label": "string",
      "source_class": "dataset_version | aps_content_document",
      "source_ref": "string",
      "owner_service_source_shape": "dataset_version | aps_content_document",
      "planning_shape_family": "tabular_numeric | document_chunks",
      "query_basis": "string",
      "validation_status": "valid | invalid | partial | unavailable",
      "duplicate_status": "unique | duplicate | possible_duplicate",
      "size_or_unit_count": 1,
      "preview_payload_ref": null,
      "provenance_ref": "string",
      "current_decision_state": "candidate"
    }
  ],
  "partial_retrieval": false,
  "authority_rail": {}
}
```

The implementation must keep `owner_service_source_shape` separate from `planning_shape_family`. Current owner services use shapes such as `dataset_version` and `aps_content_document`; broader planning language such as `tabular_numeric` and `document_chunks` must be exposed as derived planning family until a later owner-service change admits different persisted shape values.

## Gate B Decision Contract
`POST /api/v1/layer3/gate-b/decision` is the first admitted write endpoint. It records explicit operator decisions and creates a deliberate Layer 3 session for approved material only.

Request:

```json
{
  "schema_id": "layer3.gate_b_decision_request.v1",
  "schema_version": 1,
  "client_request_id": "string",
  "preflight_id": "string",
  "source_set_id": "string",
  "material_preview_id": "string",
  "actor": "operator",
  "candidate_decisions": [
    {
      "candidate_id": "string",
      "decision": "approved | denied | isolated | flagged",
      "operator_reason": "string",
      "decision_basis": {
        "source_ref": "string",
        "query_basis": "string",
        "provenance_ref": "string"
      }
    }
  ],
  "commit_reason": "operator_gate_b_decision"
}
```

Response:

```json
{
  "schema_id": "layer3.gate_b_decision_result.v1",
  "schema_version": 1,
  "session_id": "string",
  "selection_manifest_id": "string",
  "gate_b_decision_manifest_id": "stable_hash",
  "approved_candidate_ids": [],
  "denied_candidate_ids": [],
  "isolated_candidate_ids": [],
  "flagged_candidate_ids": [],
  "next_state": "gate_c_preview_ready | blocked_no_approved_material",
  "authority_rail": {}
}
```

Persistence mapping:

| State concept | Required persistence surface | Rule |
| --- | --- | --- |
| Approved candidate | `L3SelectionManifest.manifest_json.items` | Approved candidates become committed selection manifest items. |
| Denied/isolated/flagged decisions | `L3Session.operator_context_json.layer3_gate_b_decision_manifest_v1` | These remain auditable even though they are not normal downstream material. |
| Gate B decision counts | `L3Session.summary_json.gate_b_summary_v1` | Counts must match the decision manifest. |
| Source hints | `L3SelectionManifest.source_plane_hints_json` | Preserve source set and source class context. |
| Material snapshots | Existing `record_retrieval_event` owner path only | Snapshots are created only through existing session owner service behavior. |

Gate B must fail closed if:
- no candidate is approved
- any denied, isolated, or flagged candidate lacks an operator reason
- a candidate ID is unknown to the material preview
- a candidate decision attempts `remove` as durable state
- browser-only hidden state is submitted as durable fact

`remove` may only hide an uncommitted candidate locally in the browser. It is not durable Gate B state.

## Gate C Preview Contract
`POST /api/v1/layer3/gate-c/preview` exposes typing/unit/group/set posture through existing Layer 3 owner services.

Request:

```json
{
  "schema_id": "layer3.gate_c_preview_request.v1",
  "schema_version": 1,
  "client_request_id": "string",
  "session_id": "string",
  "commit_typing": false,
  "actor": "operator"
}
```

Response:

```json
{
  "schema_id": "layer3.gate_c_preview_result.v1",
  "schema_version": 1,
  "session_id": "string",
  "typing_records": [],
  "analysis_units": [],
  "analysis_groups": [],
  "analysis_sets": [],
  "unsupported_material": [],
  "override_allowed": false,
  "next_state": "first_slice_complete | blocked_typing_unavailable",
  "authority_rail": {}
}
```

If `commit_typing` is `true`, the API must call the existing typing owner service and persist through current owner-service paths. It must not materialize typing in route handlers or browser code.

If `commit_typing` is `false`, the implementation may return read-only projection data only if the projection is explicitly marked non-authoritative.

## Gate C Override Contract
Gate C override default: unavailable unless bounded override persistence, recomputation/invalidation, audit payload, and tests are implemented together.

`POST /api/v1/layer3/gate-c/override` is unavailable by default.

The endpoint may return:

```json
{
  "schema_id": "layer3.typing_override_unavailable.v1",
  "schema_version": 1,
  "status": "unavailable",
  "error_code": "override_unavailable",
  "message": "Typing override is not enabled in this first slice.",
  "recoverable": false,
  "next_allowed_actions": ["review_typing", "finish_first_slice"]
}
```

The endpoint may become active only if the same implementation pass proves all of the following:
- prior source shape and modality are recorded
- new source shape and modality are recorded
- actor is recorded
- timestamp is recorded
- reason is recorded
- must-remain-intact change is recorded
- allowed enum transitions are validated
- affected groups/sets are recomputed or explicitly invalidated
- tests prove invalid transitions fail closed
- the persisted record uses existing Layer 3 control surfaces only

If active, the minimum request shape is:

```json
{
  "schema_id": "layer3.typing_override_request.v1",
  "schema_version": 1,
  "client_request_id": "string",
  "session_id": "string",
  "typing_record_id": "string",
  "before": {
    "owner_service_source_shape": "string",
    "planning_shape_family": "string",
    "analysis_modality": "string"
  },
  "after": {
    "owner_service_source_shape": "string",
    "planning_shape_family": "string",
    "analysis_modality": "string"
  },
  "operator_reason": "string",
  "must_remain_intact_changed": false,
  "actor": "operator"
}
```

An active override must not enable arbitrary group/set construction, payload editing, provenance editing, downstream execution, or package review.

## Session Summary Contract
`GET /api/v1/layer3/session/{session_id}` returns the durable first-slice state.

Required response:

```json
{
  "schema_id": "layer3.workbench_session_summary.v1",
  "schema_version": 1,
  "session_id": "string",
  "selection_manifest_id": "string",
  "current_gate": "gate_b | gate_c | complete",
  "gate_b_summary": {
    "approved": 0,
    "denied": 0,
    "isolated": 0,
    "flagged": 0
  },
  "gate_c_summary": {
    "typing_committed": false,
    "typing_record_count": 0,
    "analysis_unit_count": 0,
    "analysis_group_count": 0,
    "analysis_set_count": 0
  },
  "downstream_unavailable": ["plan", "execution", "results", "package"],
  "authority_rail": {}
}
```

## Authority Rail Contract
Every UI state must be able to render this payload:

```json
{
  "schema_id": "layer3.authority_rail.v1",
  "schema_version": 1,
  "session_id": "none | string",
  "preflight_id": "none | string",
  "source_set_id": "none | string",
  "current_gate": "intent | sources | gate_b | gate_c | complete",
  "persistence_mode": "not_committed | preview_only | durable_layer3_control",
  "source_authority": {
    "source_classes": [],
    "runtime_label": null,
    "database_label": null,
    "storage_label": null
  },
  "approved_material_count": 0,
  "denied_material_count": 0,
  "isolated_material_count": 0,
  "flagged_material_count": 0,
  "typing_status": "not_started | previewed | committed | unavailable",
  "downstream_unavailable": ["plan", "execution", "results", "package"],
  "browser_only_state": []
}
```

The UI may keep browser-only state for display preferences only:
- selected tab
- expanded rows
- hidden uncommitted candidates
- drawer open/closed state
- client-side filters

The UI must not keep browser-only state for:
- approved/denied/isolated/flagged decisions after submit
- operator reasons
- committed source set
- session ID
- typing record changes
- downstream eligibility

## Proof Matrix
The first implementation pass must include tests for:
- `/review/layer3` route loads without disturbing existing review pages
- bootstrap returns inactive downstream states
- preflight fails closed on empty and conflicting input
- source preview rejects unsupported source classes
- material preview distinguishes candidate material from committed material
- Gate B requires explicit decisions and reasons where needed
- Gate B persists approved material separately from denied/isolated/flagged decisions
- Gate C preview delegates to existing owner-service behavior or returns explicit unavailable state
- Gate C override is either unavailable with a tested response or fully persisted and tested
- session summary returns authority rail and counts from durable state
- browser-only state is not accepted as durable authority
- no schema migration is added
- no runtime snapshot DB write path is added
- qualitative/hybrid/RAG/package controls are unavailable
- existing `/review/nrc-aps`, Workbench Compare, Candidate B Trace, and analyst-insight tests still pass or remain untouched

When UI is touched, proof must include headed and headless Chrome validation for shell reachability and the first-slice operator path.

## Stop Conditions
Stop and reopen planning before implementation if any of these become necessary:
- new model/table/column or migration
- runtime snapshot DB writes
- broad source picker beyond deterministic allowlisted sources
- arbitrary local file/directory ingestion
- RAG/vector retrieval
- qualitative or hybrid execution
- package review or handoff
- full idempotent de-duplication claims without a tested persistence lookup
- current review/APS/analyst-insight behavior changes
- unreviewed natural-language task decomposition

## Remaining Non-Blocking Decisions
These remain intentionally outside this contract:
- final visual spacing/token system
- final glossary for Gate A and Pre-3A
- source preview expansion beyond `dataset_version` and `aps_content_document`
- exact performance limits for maximum candidates/materials/units
- final accessibility acceptance checklist beyond semantic HTML, keyboard access, contrast, and non-color-only statuses
- qualitative single-item execution activation
- hybrid execution activation
- RAG/vector activation
- package review activation
- RBAC or multi-user collaboration
