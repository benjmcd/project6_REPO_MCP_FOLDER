# Connector Destination Reentry Decision Freeze

Status: current-main reentry decision freeze for `connector_destination_reentry_decision`.

This document follows `253_SOURCE_RENDERED_CONTROL_DECISION_FREEZE.md`. It records the connector/destination reentry decision after the goal-stack and source rendered-control audits: the existing `internal_dispatch_record_only` path is live and bounded; no external connector invocation, destination write, connector-run creation, generic downstream dispatch, provider/public URL runtime, rendered connector/destination control, package mutation, source expansion, broad qualitative/hybrid/RAG behavior, full mockup activation, auth/security behavior, hidden LLM planning, or frontend-only durable authority is admitted.

## Decision

```yaml
selected_planning_mode: connector_destination_reentry_decision
entry_decision: internal_record_only_live_external_dispatch_blocked
base_branch: main
implementation_branch: codex/l3-connector-destination-reentry-freeze
live_behavior_change: false
current_connector_destination_runtime: internal_dispatch_record_only
external_connector_invocation: blocked
destination_write: blocked
connector_run_creation: blocked
generic_downstream_dispatch: blocked
rendered_connector_destination_controls: blocked
provider_public_url_runtime: blocked
implementation_entry_allowed_next: false
next_required_boundary: single_named_connector_or_destination_freeze_before_runtime
```

The decision is deliberately not an external dispatch implementation. Current main can record an internal server-authority receipt over already prepared same-origin artifacts. That receipt is not a connector run, destination write, provider object operation, public URL, retryable dispatch lifecycle, or external delivery proof.

## Current Live Boundary

The live connector/destination boundary is:

- endpoint: `/api/v1/layer3/handoff/connector/record`;
- owner service: `backend/app/services/layer3_connector_dispatch_entry.py`;
- mode: `internal_dispatch_record_only`;
- state: `connector_dispatch_recorded`;
- prerequisite authority: existing session, plan, pass, result review, package review/submit, package construction, handoff/export prepare, APS handoff dispatch, and external export/download prepare state;
- output: an internal control-plane receipt and reconciliation-state entry;
- side effects: no external connector invocation, no destination write, no connector-run creation, no provider/public URL generation, no package mutation, no source expansion.

## Runtime Still Blocked

The following remain blocked:

- external connector invocation;
- destination writes;
- connector-run creation from Layer 3 downstream reentry;
- generic downstream dispatch;
- browser-supplied connector keys, destination ids, connector credentials, destination credentials, raw targets, URLs, buckets, object keys, ACLs, or policy documents;
- retry, rerun, cancel, recovery, timeout, or queue behavior;
- rendered connector/destination controls;
- provider/public URL runtime as a side effect;
- package mutation or package payload rewrite;
- source expansion, upload, directory ingestion, web retrieval, or RAG/vector retrieval;
- broad qualitative/hybrid/RAG execution;
- full mockup activation;
- auth/security behavior changes.

## Reentry Requirements

A later connector/destination implementation may proceed only if it selects exactly one mode:

- `single_named_connector_dispatch`;
- `single_named_destination_dispatch`;
- `internal_dispatch_record_only_extension`.

The selected mode must define:

- named downstream use case;
- selected artifact family;
- connector or destination family;
- server-side allowlist/config authority;
- credential and access authority;
- lifecycle states;
- retry, cancel, timeout, duplicate, and idempotency behavior;
- stale-authority failure behavior;
- receipt and audit contract;
- fake connector/destination test architecture by default;
- leak-control policy for logs, error bodies, traces, screenshots, and response payloads;
- rendered UI state/theme/headed/headless proof if controls are admitted.

## Validation Evidence

This freeze relies on already-landed implementation/audit evidence:

- PR `#809` recorded the goal-stack implementation audit and proved the current bounded implementation state.
- PR `#810` recorded the source rendered-control decision and preserved source/rendered non-admission.
- Current `internal_dispatch_record_only` behavior remains governed by `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md`, `189_CONNECTOR_DESTINATION_ENTRY_FREEZE.md`, and `190_CONNECTOR_DESTINATION_ENTRY_CONTRACT.md`.
- `python .\tools\l3-progress-check.py` must pass after this freeze is wired.

This validation does not prove any real connector credentials, destination access, external network behavior, retry/cancel behavior, destination receipt, provider object operation, or rendered connector/destination UI.

## Negative Invariants

- no external connector invocation;
- no destination write;
- no connector-run creation;
- no generic downstream dispatch;
- no provider/public URL runtime;
- no provider object write, copy, ACL change, or public-access operation;
- no rendered connector/destination controls;
- no browser-owned connector/destination authority;
- no client-supplied connector credentials, destination credentials, raw targets, URLs, buckets, object keys, ACLs, or policy documents;
- no package mutation/reconstruction;
- no package payload rewrite;
- no source expansion;
- no local upload;
- no local-directory ingestion;
- no arbitrary local path input;
- no web connector retrieval;
- no RAG/vector retrieval;
- no broad qualitative/hybrid/RAG runtime;
- no full mockup activation;
- no hidden LLM planning;
- no auth/security behavior change;
- no route/API/DTO/model/migration/service behavior change;
- no executable test behavior change;
- no CI workflow or Playwright configuration change;
- no frontend-only durable authority.

## Stop Condition

Stop before code if the next connector/destination proposal lacks one named connector or destination mode, treats internal record-only as external dispatch, accepts credentials or raw targets from the browser, lacks credential/access authority, lacks lifecycle and stale-authority contracts, lacks fake connector/destination test architecture, emits connector/destination fields from existing same-origin/provider/package/source responses without a compatibility freeze, or changes package/source/RAG/mockup/auth behavior as a side effect.
