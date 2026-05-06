# Layer 3 Plan Revision Recovery Contract

Status: planning/control API and state contract for `132_PLAN_REVISION_RECOVERY_FREEZE.md`. This document is not a live implementation claim.

## Contract Summary

The future `plan_revision_recovery_lifecycle` lane may define one server-authorized recovery action from a pre-approval terminal revision-control state:

- `plan_rejected`
- `plan_revision_requested`

The recovery action may only prepare the session for a fresh server-backed plan preview. It must not approve a plan, reopen an approved plan, supersede an approved plan, execute analysis, or create downstream package/handoff/export state.

## Canonical Authority

The authority chain for any future implementation is:

1. durable `L3Session` state;
2. recorded `plan_revision_control` object in `L3Session.summary_json`;
3. current server validation that no approved plan or pass run exists;
4. current Gate C typing authority;
5. operator recovery request;
6. fresh server-backed plan preview after recovery.

Browser state is display/cache only. It may submit a recovery request, but it cannot be the durable source of the recovery state.

## Candidate Endpoint Shape

A later implementation-entry freeze may choose this endpoint shape:

`POST /api/v1/layer3/plan/revision/recover`

Request shape:

```json
{
  "schema_id": "layer3.plan_revision_recovery_request.v1",
  "session_id": "string",
  "source_revision_state": "plan_rejected | plan_revision_requested",
  "source_preview_id": "string",
  "source_preview_hash": "string",
  "operator_decision": "recover_for_preview_refresh",
  "operator_note": "optional string",
  "client_request_id": "string"
}
```

The exact route may change only if the implementation-entry freeze updates this contract and all progress/control surfaces consistently.

## Forbidden Request Fields

The request must fail closed if it includes execution-bearing, downstream, or authority-widening fields, including:

- `approve_plan`
- `approved_plan_supersession`
- `delete_approved_plan`
- `execute`
- `create_pass_runs`
- `pass_run_ids`
- `analysis_run_id`
- `artifact_manifest`
- `result_review`
- `package_review`
- `package_mutation`
- `handoff`
- `connector_dispatch`
- `provider_public_url`
- `source_expansion`
- `qualitative_plan`
- `hybrid_plan`
- `rag_plan`
- `vector_plan`
- `llm_plan`
- `browser_persisted_state`

## Success Response Shape

Successful recovery responses should include:

```json
{
  "schema_id": "layer3.plan_revision_recovery_result.v1",
  "request_id": "string",
  "session_id": "string",
  "source_revision_state": "plan_rejected | plan_revision_requested",
  "next_state": "gate_c_typing_committed",
  "preview_refresh_required": true,
  "approval_available": false,
  "execution_started": false,
  "recovery_lifecycle_only": true,
  "source_preview_id": "string",
  "source_preview_hash": "string",
  "operator_decision": "recover_for_preview_refresh",
  "authority_rail": {},
  "downstream_unavailable": ["execution", "results", "package", "handoff"]
}
```

The response must not include pass-run ids, analysis-run ids, package ids, handoff ids, export ids, generated plan alternatives, connector ids, provider URLs, file bytes, or artifact refs.

## Blocked And Conflict Responses

Required deterministic error codes:

| Case | Error code | Required posture |
| --- | --- | --- |
| Missing session id | `session_not_found` | No state writes |
| No recorded revision-control state | `plan_revision_recovery_not_available` | No recovery |
| Source revision state mismatch | `plan_revision_state_mismatch` | No recovery |
| Preview id/hash mismatch | `preview_mismatch` | Require fresh inspection |
| Gate C typing not committed | `gate_c_not_committed` | No recovery |
| Approved plan already exists | `plan_already_approved` | Do not reopen or supersede |
| Non-approved plan row exists | `plan_already_materialized` | Do not infer lifecycle |
| Pass runs already exist | `pass_runs_already_exist` | Do not alter execution state |
| Forbidden field present | `execution_not_admitted` | Fail closed |
| Unsupported decision | `unsupported_revision_recovery_decision` | Fail closed |

## Persistence Contract

Preferred persistence posture:

- record recovery only in existing session/workbench summary state if it can be represented without ambiguity;
- preserve the source revision-control object for auditability or mark it superseded by recovery without deleting it;
- record source preview id/hash, source revision state, operator note presence, timestamp, and preview-refresh-required flags;
- create no `L3AnalysisPlan`;
- create no `L3PassRun`;
- create no `AnalysisRun`;
- write no artifact, package, handoff, export, connector, source, or provider state;
- add no migration.

If existing summary state is not adequate, implementation must stop and produce a follow-up freeze instead of silently widening schema.

## UI State Contract

The browser may represent:

- `plan_revision_recovery_available`
- `plan_revision_recovery_blocked`
- `plan_revision_recovery_recorded`
- `plan_preview_refresh_required`

The UI must not represent recovery as approval, execution readiness, package readiness, connector readiness, or generated-plan availability. It must keep downstream controls unavailable and keep server authority visible.

## Test Contract

Required tests for a later implementation:

- API success from `plan_rejected`;
- API success from `plan_revision_requested`;
- API blocked without recorded revision-control state;
- API conflict for source revision state mismatch;
- API conflict for stale preview id/hash;
- API conflict for already approved plan;
- API conflict for existing pass runs;
- API fail-closed behavior for forbidden execution/downstream fields;
- database proof that no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, package, handoff, export, connector, source, provider, or artifact state is created;
- UI proof that recovery requires server authority and downstream controls remain unavailable.

## Out Of Scope Until Later Freeze

The following require a separate freeze:

- approved-plan reopen, cancellation, replacement, deletion, or supersession;
- revision history table;
- plan alternative generation;
- execution scheduling;
- result review changes;
- package review or package mutation;
- handoff/export changes;
- connector/destination dispatch;
- provider/public URL behavior;
- runtime snapshot DB writes;
- schema migration;
- broad qualitative/hybrid/RAG/vector/LLM planning;
- frontend-only durable state;
- full mockup activation;
- authentication/security hardening.
