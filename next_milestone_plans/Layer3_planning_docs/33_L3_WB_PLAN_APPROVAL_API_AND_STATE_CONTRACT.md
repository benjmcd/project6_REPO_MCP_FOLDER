# Layer 3 Workbench Plan Approval API And State Contract

## Status

- planning-only API/state companion for `32_L3_WB_PLAN_APPROVAL_FREEZE.md`
- not active implementation by itself
- subordinate to the plan-preview contract unless this document explicitly narrows a later implementation pass
- implementation binding: PR `#199` implements this contract through `/api/v1/layer3/plan/approve` and the existing `/review/layer3` plan panel

This document freezes the API, DTO, browser-state, persistence, and proof contract for a plan-approval slice. It does not activate execution, results, package review, handoff, schema widening, runtime DB writes, qualitative/hybrid/RAG/vector execution, or hidden natural-language/LLM planning.

## Endpoint List

The later implementation may add the following endpoint under the existing Layer 3 router:

| Method | Path | Purpose | Persistence |
| --- | --- | --- | --- |
| POST | `/api/v1/layer3/plan/approve` | Persist operator approval of the deterministic owner-service plan that is already available through read-only preview. | Creates one approved `L3AnalysisPlan`; no pass runs or execution |

Existing endpoints may be updated only to expose plan-approval availability:

| Method | Path | Allowed change |
| --- | --- | --- |
| GET | `/api/v1/layer3/bootstrap` | May include `plan_approval` feature metadata while keeping `analysis_execution`, `package_review`, and handoff features false. |
| GET | `/api/v1/layer3/session/{session_id}` | May include plan-preview and plan-approval readiness metadata, but must not report executed, resulted, packaged, or handed-off state. |
| POST | `/api/v1/layer3/plan/preview` | May include approval-readiness metadata derived from the recomputed preview. |

## Common Response Fields

All plan-approval responses must include:

- `schema_id`
- `schema_version`
- `request_id`
- `server_time`
- `status`

Allowed statuses for this slice:

- `ok`
- `blocked`
- `invalid`
- `conflict`
- `failed`

## Request DTO

`POST /api/v1/layer3/plan/approve`

```json
{
  "schema_id": "layer3.plan_approval_request.v1",
  "schema_version": 1,
  "client_request_id": "string",
  "session_id": "string",
  "preview_id": "string",
  "preview_hash": "string",
  "operator_confirmation": true,
  "approval_scope": "owner_service_default"
}
```

Rules:

- `session_id` is required.
- `operator_confirmation` must be explicitly true.
- `approval_scope` must default to `owner_service_default`.
- `preview_id` and/or `preview_hash` must match server-side recomputation unless a later freeze admits approval without preview hash checking.
- The request must not accept arbitrary plan scopes.
- The request must not accept plan edits.
- The request must not accept natural-language plan instructions.
- The request must not accept execution flags.
- The request must not accept package or handoff flags.

## Success DTO

```json
{
  "schema_id": "layer3.plan_approval_result.v1",
  "schema_version": 1,
  "request_id": "string",
  "server_time": "ISO-8601 timestamp",
  "status": "ok",
  "session_id": "string",
  "next_state": "plan_approved",
  "approval_only": true,
  "execution_started": false,
  "analysis_plan_id": "string",
  "plan_status": "approved",
  "approved_by_operator": true,
  "approved_at": "ISO-8601 timestamp",
  "authority_rail": {
    "schema_id": "layer3.authority_rail.v1",
    "current_gate": "plan",
    "persistence_mode": "approved_plan",
    "typing_status": "committed",
    "execution_enabled": false,
    "package_review_enabled": false,
    "downstream_unavailable": ["execution", "results", "package"]
  },
  "approved_plan": {
    "schema_id": "layer3.approved_plan_payload.v1",
    "plan_version": "owner_service_default",
    "source_preview_id": "string",
    "source_preview_hash": "string",
    "would_create_pass_runs": false,
    "would_execute_passes": false,
    "approved_sets": [],
    "excluded_sets": [],
    "planned_passes": [],
    "warnings": [],
    "owner_service_basis": {
      "service": "backend/app/services/layer3_pass_entry.py",
      "mode": "operator_approved_plan_only",
      "source_gate": "plan_approval"
    }
  }
}
```

The DTO may include additional stable display fields only if they are derived from existing Layer 3 session, material, typing, analysis-unit, analysis-set, plan-preview, or pass-entry owner-service state.

## Approved Plan Payload

Minimum approved-set item:

```json
{
  "analysis_set_id": "string",
  "analysis_unit_ids": ["string"],
  "material_snapshot_ids": ["string"],
  "analysis_modality": "quantitative",
  "pass_type": "single_item | associated_cohort",
  "pass_scope": "string",
  "readiness": "approved",
  "source_summary": {
    "source_classes": ["dataset_version"],
    "source_material_count": 1
  }
}
```

Minimum planned-pass item:

```json
{
  "pass_type": "single_item | associated_cohort",
  "pass_scope": "string",
  "analysis_set_id": "string",
  "method_family": "repo_supported_quantitative",
  "execution_status": "not_started",
  "approval_only": true
}
```

## Error DTO

Use the common `layer3.workbench_error.v1` shape from `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`.

Minimum error codes:

- `session_not_found`
- `gate_c_not_committed`
- `no_admissible_plan`
- `preview_mismatch`
- `plan_already_approved`
- `pass_runs_already_exist`
- `unsupported_approval_scope`
- `operator_confirmation_required`
- `execution_not_admitted`
- `package_handoff_not_admitted`
- `owner_service_error`

Blocked or failed plan approval must not include `pass_run_ids`, package ids, handoff ids, execution ids, or artifact refs.

## Persistence Contract

This slice is approval-only.

The implementation may create or mutate:

- one `L3AnalysisPlan` for the session
- the plan's `status`
- the plan's `approved_by_operator`
- the plan's `approved_at`
- the plan's `plan_json`
- the session summary and planning state fields needed to point to the approved plan

The implementation must not create or mutate:

- `L3PassRun`
- analysis run rows
- package rows
- handoff rows
- runtime snapshot DB records
- migration state
- persisted input manifests
- persisted output manifests
- derived datasets for execution

Browser state may store the approved plan summary for display, but it is non-authoritative and must be recomputed from server state after refresh.

## Owner-Service Contract

The implementation must add or reuse a pass-entry owner-service helper that approves the plan without executing it.

Allowed helper behavior:

- load the session
- confirm the session is eligible for plan approval
- recompute the preview from current durable state
- compare the recomputed preview against the submitted preview id/hash
- create one `L3AnalysisPlan`
- preserve approved, excluded, warning, preview, and owner-service basis in `plan_json`
- set operator approval metadata
- flush or commit through the same transaction discipline used by the surrounding service

Forbidden helper behavior:

- call `materialize_pass_entry(...)`
- call `_execute_passes(...)`
- create `L3PassRun`
- call `run_analysis`
- persist manifests
- change package or handoff state
- loosen pass-entry admissibility rules

## UI State Contract

The UI may:

- enable a plan-approval action after a successful server-backed plan preview
- show approved-plan summary after approval
- keep admitted/excluded/warning context visible
- keep execution/results/package visibly disabled

The UI must not:

- expose a working execute/run button
- expose result review controls
- expose package review controls
- show handoff controls
- display LLM-generated plan text as authoritative
- hide exclusions or warnings
- treat browser-only approval state as durable server truth

## Proof Contract

The later implementation must include:

- unit/service proof for the owner-service approval helper
- API proof for success and blocked/error states
- page proof that approval controls are visible only when eligible
- browser proof that the operator path reaches approved plan state while execution/results/package remain disabled
- regression proof that first-slice Gate B/Gate C and read-only preview behavior still pass

Required negative assertions:

- exactly one `L3AnalysisPlan` exists after approval
- no `L3PassRun` exists after approval
- no analysis run exists after approval
- no execution artifact is written
- `analysis_execution` remains false
- `package_review` remains false
- handoff remains false

## Stop Conditions

Stop before implementation if this contract cannot be satisfied without:

- calling `materialize_pass_entry(...)`
- creating pass runs
- running analysis
- adding new schema
- adding migrations
- enabling execution
- enabling results review
- changing package or APS handoff contracts
- using hidden natural-language or LLM planning
