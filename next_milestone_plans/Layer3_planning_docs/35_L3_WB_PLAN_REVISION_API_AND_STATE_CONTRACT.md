# Layer 3 Workbench Plan Revision API And State Contract

Status: planning-only API/state companion for `34_L3_WB_PLAN_REVISION_FREEZE.md`.

This document defines the narrow route, DTO, state, UI, and proof contract for plan rejection and revision-request semantics. It is not a live implementation claim.

## Contract Summary

The fourth workbench slice may add two operator decisions against the current server-backed plan preview:

- reject current preview
- request revision for current preview

Both decisions are preview-control decisions. They do not execute the plan, create pass runs, write artifacts, or alter package/handoff state.

## Canonical Authority

The authority chain remains:

1. durable Layer 3 session state
2. explicit Gate C typing commit
3. owner-service read-only plan preview
4. operator preview-control decision

Browser state is not authoritative. Any rejection or revision request must target the server-recomputed preview id/hash.

## Candidate Endpoint Shape

A later implementation may use one endpoint with an action field:

`POST /api/v1/layer3/plan/revise`

Request shape:

```json
{
  "session_id": "string",
  "preview_id": "string",
  "preview_hash": "string",
  "operator_decision": "reject_current_preview | request_revision",
  "operator_note": "optional string",
  "client_request_id": "optional string"
}
```

The exact endpoint name may change only if the implementation PR updates this contract and all progress/control surfaces consistently. The behavior contract is more important than the route spelling.

## Forbidden Request Fields

The request must fail closed if it includes execution-bearing or downstream fields, including:

- `execute`
- `execution_started`
- `create_pass_runs`
- `pass_run_ids`
- `artifact_manifest`
- `result_review`
- `package_review`
- `handoff`
- `qualitative_plan`
- `hybrid_plan`
- `rag_plan`
- `vector_plan`
- `llm_plan`

## Success Response Shape

Successful rejection/revision responses should include:

```json
{
  "schema_id": "layer3.plan_revision_result.v1",
  "request_id": "string",
  "session_id": "string",
  "next_state": "plan_rejected | plan_revision_requested",
  "revision_control_only": true,
  "execution_started": false,
  "source_preview_id": "string",
  "source_preview_hash": "string",
  "operator_decision": "reject_current_preview | request_revision",
  "operator_note_recorded": true,
  "authority_rail": {},
  "downstream_unavailable": []
}
```

The response must not include pass-run ids, package ids, handoff ids, execution ids, artifact refs, or generated plan alternatives.

## Blocked And Conflict Responses

The implementation must use deterministic error codes.

Required blocked/conflict cases:

| Case | Error code | Required posture |
| --- | --- | --- |
| Missing session id | `session_not_found` | No state writes |
| Gate C typing not committed | `gate_c_not_committed` | No revision decision |
| No current admissible preview | `no_admissible_plan` | No revision decision |
| Preview id/hash mismatch | `preview_mismatch` | Require preview refresh |
| Approved plan already exists | `plan_already_approved` | Do not reopen approved plan |
| Non-approved plan row already exists | `plan_already_materialized` | Do not infer revision lifecycle |
| Pass runs already exist | `pass_runs_already_exist` | Do not alter execution state |
| Forbidden field present | `execution_not_admitted` | Fail closed |
| Unsupported decision | `unsupported_revision_decision` | Fail closed |

## Persistence Contract

Preferred persistence posture:

- record the operator decision in existing session/workbench summary state if it can be represented without ambiguity
- include source preview id/hash, decision type, operator note presence, timestamp, and approval/execution blocked flags
- preserve existing approval-only `L3AnalysisPlan` behavior
- create no `L3PassRun`
- write no artifact manifests
- add no migration

If existing summary state is not adequate, the implementation must stop and produce a follow-up freeze rather than silently widening schema.

## Session Summary Fields

If persisted in session summary, use a narrow object such as:

```json
{
  "plan_revision_control": {
    "schema_id": "layer3.plan_revision_control.v1",
    "state": "plan_rejected | plan_revision_requested",
    "source_preview_id": "string",
    "source_preview_hash": "string",
    "operator_note_recorded": true,
    "approval_available": false,
    "execution_started": false,
    "created_at": "ISO-8601 string"
  }
}
```

The summary must not store generated plan alternatives, execution inputs, pass-run ids, package refs, handoff refs, or artifact refs.

## Approval Interaction

After rejection or revision request for the current preview:

- approval for that preview is blocked
- approval may become available again only after a later explicit preview refresh or earlier-gate state change
- approval of a stale preview id/hash must remain blocked
- already approved plans remain terminal for this slice

This contract does not define approved-plan supersession.

## UI State Contract

The browser may represent:

- `plan_preview_ready`
- `plan_approved`
- `plan_rejected`
- `plan_revision_requested`

The UI must not represent rejection or revision request as execution readiness. It must keep downstream controls unavailable and keep the authority rail visible.

## Test Contract

Required tests for a later implementation:

- API success for `reject_current_preview`
- API success for `request_revision`
- API conflict for stale preview id/hash
- API conflict for already approved plan
- API blocked before Gate C commit
- API fail-closed behavior for forbidden execution fields
- database proof that no `L3PassRun` is created
- database proof that no artifact/package/handoff state is written
- UI proof that approval is blocked after rejection/revision request
- UI proof that downstream execution remains unavailable

## Out Of Scope Until Later Freeze

The following require a separate freeze:

- approved-plan reopen
- approved-plan replacement
- approved-plan supersession
- revision history table
- plan alternative generation
- execution scheduling
- result review
- package review
- handoff
- runtime snapshot DB writes
- schema migration
- qualitative/hybrid/RAG/vector/LLM planning
