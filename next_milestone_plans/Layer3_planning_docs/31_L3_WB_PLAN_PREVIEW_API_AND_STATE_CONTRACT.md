# Layer 3 Workbench Plan Preview API And State Contract

## Status

- planning-only API/state companion for `30_L3_WB_PLAN_PREVIEW_FREEZE.md`, merged by PR `#191`
- not active implementation by itself
- subordinate to the first-slice no-go list unless this contract explicitly narrows a later implementation pass

This document freezes the API, DTO, browser-state, persistence, and proof contract for the plan-preview slice. It does not activate execution, results, package review, handoff, schema widening, runtime DB writes, qualitative/hybrid/RAG/vector execution, or hidden natural-language/LLM planning.

## Endpoint List

The later implementation may add the following endpoint under the existing Layer 3 router:

| Method | Path | Purpose | Persistence |
| --- | --- | --- | --- |
| POST | `/api/v1/layer3/plan/preview` | Return a read-only preview of the bounded owner-service plan that could be formed from a committed Gate C session. | Read-only |

Existing endpoints may be updated only to expose plan-preview availability:

| Method | Path | Allowed change |
| --- | --- | --- |
| GET | `/api/v1/layer3/bootstrap` | May include `plan_preview` feature metadata while keeping `analysis_execution`, `package_review`, and handoff features false. |
| GET | `/api/v1/layer3/session/{session_id}` | May include plan-preview readiness metadata, but must not report an executed or packaged state. |

## Common Response Fields

All plan-preview responses must include:

- `schema_id`
- `schema_version`
- `request_id`
- `server_time`
- `status`

Allowed statuses for this slice:

- `ok`
- `blocked`
- `invalid`
- `unavailable`
- `conflict`
- `failed`

## Request DTO

`POST /api/v1/layer3/plan/preview`

```json
{
  "schema_id": "layer3.plan_preview_request.v1",
  "schema_version": 1,
  "client_request_id": "string",
  "session_id": "string",
  "include_exclusions": true,
  "preview_scope": "owner_service_default"
}
```

Rules:

- `session_id` is required.
- `preview_scope` must default to `owner_service_default`.
- The implementation must reject arbitrary plan scopes unless a later freeze admits them.
- The request must not accept natural-language plan instructions.
- The request must not accept execution flags.
- The request must not accept package or handoff flags.

## Success DTO

```json
{
  "schema_id": "layer3.plan_preview_result.v1",
  "schema_version": 1,
  "request_id": "string",
  "server_time": "ISO-8601 timestamp",
  "status": "ok",
  "session_id": "string",
  "next_state": "plan_preview_ready",
  "preview_id": "stable hash or deterministic preview id",
  "preview_only": true,
  "authority_rail": {
    "schema_id": "layer3.authority_rail.v1",
    "current_gate": "plan",
    "persistence_mode": "preview_only",
    "typing_status": "committed",
    "execution_enabled": false,
    "package_review_enabled": false,
    "downstream_unavailable": ["execution", "results", "package"]
  },
  "plan_preview": {
    "schema_id": "layer3.plan_preview_payload.v1",
    "plan_version": "owner_service_default",
    "would_create_analysis_plan": false,
    "would_create_pass_runs": false,
    "would_execute_passes": false,
    "admitted_sets": [],
    "excluded_sets": [],
    "planned_passes": [],
    "warnings": [],
    "owner_service_basis": {
      "service": "backend/app/services/layer3_pass_entry.py",
      "mode": "read_only_preview",
      "source_gate": "plan_preview"
    }
  }
}
```

The DTO may include additional stable display fields only if they are derived from existing Layer 3 session, material, typing, analysis-unit, analysis-set, or pass-entry owner-service state.

## Plan Preview Payload

Minimum admitted-set item:

```json
{
  "analysis_set_id": "string",
  "analysis_unit_ids": ["string"],
  "material_snapshot_ids": ["string"],
  "analysis_modality": "quantitative",
  "pass_type": "single_item | associated_cohort",
  "pass_scope": "string",
  "readiness": "admitted",
  "source_summary": {
    "source_classes": ["dataset_version"],
    "source_material_count": 1
  }
}
```

Minimum excluded-set item:

```json
{
  "analysis_set_id": "string",
  "reason_code": "string",
  "analysis_modality": "string",
  "source_summary": {
    "source_classes": ["string"],
    "source_material_count": 0
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
  "preview_only": true
}
```

## Error DTO

Use the common `layer3.workbench_error.v1` shape from `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`.

Minimum error codes:

- `session_not_found`
- `gate_c_not_committed`
- `no_analysis_sets`
- `no_admissible_plan`
- `plan_already_materialized`
- `plan_preview_unavailable`
- `unsupported_preview_scope`
- `owner_service_error`

Blocked or unavailable plan preview must not include `analysis_plan_id`, `pass_run_ids`, package ids, handoff ids, or execution ids.

## Persistence Contract

This slice is read-only.

The implementation must not create or mutate:

- `L3AnalysisPlan`
- `L3PassRun`
- analysis run rows
- package rows
- handoff rows
- runtime snapshot DB records
- migration state
- persisted artifact manifests

Browser state may store the most recent preview for display, but it is non-authoritative and must be recomputed from server state after refresh.

## Owner-Service Contract

If `layer3_pass_entry.py` needs a new public helper, it should be a read-only helper that returns plain DTO-ready data or a typed result object.

Allowed helper behavior:

- load the session
- confirm the session is finalized enough for pass-entry inspection
- load analysis sets, units, and material snapshots
- classify admissible and excluded sets using owner-service logic
- compute the same plan payload basis that pass-entry would use
- return preview data

Forbidden helper behavior:

- create `L3AnalysisPlan`
- create `L3PassRun`
- execute analysis
- persist manifests
- commit transactions
- change session status
- loosen pass-entry admissibility rules

## UI State Contract

The UI may:

- enable the `plan` step after Gate C committed state is available
- display a preview-only plan review panel
- list admitted and excluded sets
- show warnings and owner-service basis
- keep execution/results/package visibly disabled

The UI must not:

- expose a working execute/run button
- expose package review controls
- show handoff controls
- display LLM-generated plan text as authoritative
- hide exclusions or warnings
- treat browser-only preview state as durable server truth

## Proof Contract

The later implementation must include:

- unit/service proof for any new owner-service preview helper
- API proof for success and blocked/error states
- page proof that the plan panel is visible only when eligible
- browser proof that the operator path reaches plan preview while execution/results/package remain disabled
- regression proof that first-slice Gate B/Gate C behavior still passes

Required negative assertions:

- no `L3AnalysisPlan` exists after preview
- no `L3PassRun` exists after preview
- no execution artifact is written
- `analysis_execution` remains false
- `package_review` remains false

## Stop Conditions

Stop before implementation if this contract cannot be satisfied without:

- calling `materialize_pass_entry(...)`
- adding new schema
- adding migrations
- enabling execution
- creating plans or pass runs
- broadening source classes
- changing package or APS handoff contracts
- using hidden natural-language or LLM planning
