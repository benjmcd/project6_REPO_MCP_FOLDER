# Layer 3 SEC XBRL operator-review open API

## Scope

This pass adds the first runtime API boundary for opening a redacted SEC XBRL
operator-review workflow. The route is disabled by default and is limited to
server-owned evidence authority handles.

## Route

- `POST /api/v1/layer3/sec-xbrl/operator-review/workflow/open`

The route admits:

- `client_request_id`
- `open_mode = sec_xbrl_operator_review_workflow_open_v1`
- `operator_decision = open_sec_xbrl_operator_review_workflow_from_authority`
- `operator_review_authority_handle`
- `proof_source_report_hash`
- `period_limit`

The route rejects undeclared fields before execution. This prevents caller
submission of raw filings, local storage paths, URLs, accession identifiers,
`companyfacts`, or extracted XBRL/iXBRL payloads through the operator-review
open surface.

## Transaction boundary

The route calls the offline evidence orchestrator with:

- `single_transaction = true`
- `commit = false`

The API layer then records the route authorization binding and commits both the
workflow materialization and auth-binding receipt together. If authorization
binding fails, the transaction rolls back and no projection set, statement
packet, operator workflow, or auth-binding receipt is persisted.

## Defaults and non-claims

The route is gated by
`LAYER3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_OPEN_ENABLED`, defaulting to `false`.

Even when enabled for a controlled runtime, this pass does not claim:

- rendered UI availability
- value reveal execution
- live SEC acquisition
- Arelle invocation
- monitoring activation
- production readiness
- production admission

## Remaining work

The server-owned authority resolver now has a default-empty process-local
registry. API callers cannot populate it. Empty registries, unknown handles, raw
handle shapes, and source-hash mismatches fail closed before workflow
materialization.

The resolver still requires production wiring before admission: the registered
evidence must be backed by real multi-filing evidence authority, route-level
operator authorization policy, UI controls, rollback/monitoring, runbooks,
targeted validation, and explicit admission gating.
