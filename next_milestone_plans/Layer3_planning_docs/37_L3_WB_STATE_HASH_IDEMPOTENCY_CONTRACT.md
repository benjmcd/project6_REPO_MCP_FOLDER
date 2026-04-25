# Layer 3 Workbench State, Hash, And Idempotency Contract

Status: branch-local planning-only companion for `36_L3_WB_EXECUTION_READINESS_FREEZE.md`.

This document defines the state, preview identity, idempotency, and concurrency decisions that must be settled before any Layer 3 workbench execution slice can be selected.

It is not a live implementation claim and does not change current `/review/layer3` or `/api/v1/layer3/...` behavior.

## Authority Model

The authority order is:

1. durable Layer 3 session state
2. committed Gate B and Gate C decisions
3. server-side owner-service preview computation
4. persisted approval or revision-control state
5. browser state as display/cache only

Browser state must never be the authority for approving, revising, or executing a plan.

## Canonical Workbench States

The readiness packet recognizes these workbench states:

| State | Current live status | Allowed next actions before execution |
| --- | --- | --- |
| `intent_preflight_ready` | live bounded | source preview |
| `source_preview_ready` | live bounded | material preview |
| `material_preview_ready` | live bounded | Gate B decision |
| `gate_b_committed` | live bounded | Gate C typing preview/commit |
| `gate_c_typing_previewed` | live bounded, non-authoritative in UI | Gate C commit through API owner-service path |
| `gate_c_typing_committed` | live bounded | read-only plan preview |
| `plan_preview_ready` | live bounded | approve, reject, or request revision |
| `plan_approved` | live bounded approval-only | no execution until later freeze |
| `plan_rejected` | live bounded revision-control | no execution; new preview path requires later explicit rule |
| `plan_revision_requested` | live bounded revision-control | no execution; return-to-preview path requires this contract |
| `execution_readiness_blocked` | planning-only | resolve readiness gates |

Any future state must declare:

- authority source
- allowed next actions
- forbidden downstream actions
- required proof
- stale/retry behavior

## Preview Hash Basis

Before execution, a later implementation freeze must either adopt or revise this canonical hash basis:

`layer3.plan_preview_hash.v1`

The hash basis must include only server-authoritative semantic inputs:

- session id
- committed Gate B accepted material ids and source candidate ids
- committed Gate C typing record ids and analysis unit/group/set ids
- owner-service plan schema id/version
- plan objective and analysis-set summary
- admissible source/material references
- deterministic warning/exclusion codes that affect admissibility

The hash basis must exclude:

- browser render order
- local UI labels
- timestamps that do not affect plan meaning
- collapsed/expanded UI state
- non-authoritative explanatory text
- generated alternatives not persisted by the server

The required mismatch rule is fail-closed:

- stale `preview_id` or `preview_hash` blocks approval, revision, and future execution
- the response must identify `preview_mismatch`
- the response must not write execution, result, package, handoff, or artifact state

## Idempotency Contract

Every endpoint that can write state must declare its idempotency rule before execution is selected.

Minimum rule set:

| Endpoint class | Required idempotency behavior |
| --- | --- |
| preflight/source/material previews | may recompute read-only previews; no durable duplicate side effects |
| Gate B decision | duplicate `client_request_id` must not create conflicting material decisions |
| Gate C commit | duplicate commit must not create duplicate typing records |
| plan preview | read-only recomputation; no plan/pass row materialization |
| plan approval | duplicate approval must return existing approved-plan conflict or equivalent deterministic state |
| plan revision | duplicate revision request must return existing revision-control conflict or equivalent deterministic state |
| future execution | must be separately frozen before any run creation is allowed |

If current persistence cannot prove idempotency for a future write path, the implementation must stop before execution.

## Concurrency Contract

Before execution is selected, concurrent operator actions must have a single authority rule:

- approval and revision decisions for the same preview are mutually exclusive
- future execution must be impossible while a revision/rejection decision is being recorded
- future execution must be impossible for a stale preview id/hash
- a row lock or equivalent serialized owner-service transaction is required for any state transition that could create durable runtime side effects
- browser in-flight locking is only a UX guard; it is not the authority

## Revision Recovery Contract

The current `plan_revision_requested` state is intentionally non-executing. Before execution, a later freeze must choose one return path:

| Option | Decision | Tradeoff |
| --- | --- | --- |
| A | return to Gate C typing review and require a new server-backed plan preview | safest because it reuses current committed typing authority |
| B | allow a narrow preview refresh if committed Gate B/Gate C state is unchanged | efficient but requires hash-basis proof |
| C | create a new session or revision lineage | most auditable but wider persistence scope |

No current implementation may infer automatic plan regeneration from `plan_revision_requested`.

## Approved-Plan Correction Contract

Approved plans remain terminal in the current live slice. Before execution, a later freeze must decide whether to admit:

- pre-execution cancellation
- approved-plan supersession
- approved-plan replacement
- new approval lineage
- execution lock once any pass run exists

Until that freeze exists:

- approved plans must not be reopened
- approved plans must not be overwritten in place
- execution must not rely on hidden approved-plan mutation

## Output Taxonomy Readiness

Before result or package UI exists, a later freeze must define or explicitly defer these terms:

- datum
- fact
- finding
- insight
- caveat
- contradiction
- generated narrative
- result package
- handoff payload

The workbench must not infer this taxonomy from the mockup labels alone.

## Source Breadth Readiness

The mockups imply broader source breadth than current live workbench scope. Before execution, a later freeze must explicitly decide:

- whether RAG/vector/semantic retrieval is in scope
- whether local upload or local directory selection is in scope
- whether qualitative or hybrid execution is in scope
- whether external connector authentication/configuration is in scope

Until then, these remain unavailable in the live workbench.

## Proof Expectations

Any future execution freeze must cite a proof/readiness manifest that shows:

- exact files governing state/hash/idempotency
- exact tests run
- exact headed/headless browser proof when UI behavior changes
- exact no-go scan for execution overclaims
- exact status of deferred source breadth and output taxonomy questions

If proof is not machine-checkable, the execution freeze is not ready.
