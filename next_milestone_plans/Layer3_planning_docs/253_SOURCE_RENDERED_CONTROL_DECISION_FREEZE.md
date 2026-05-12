# Source Rendered Control Decision Freeze

Status: current-main rendered-control decision freeze for `source_rendered_control_decision`.

This document follows `252_GOAL_STACK_IMPLEMENTATION_AUDIT_FREEZE.md`. It records the rendered source-control decision after the goal-stack audit: existing `/review/layer3` raw-mixed current-class controls are live and bounded; no new rendered source-family control is admitted. It does not add source classes, a source adapter registry, local upload, local-directory ingestion, broad file upload, web connector retrieval, RAG/vector retrieval, vector index creation, arbitrary local path input, route behavior, DTO behavior, service behavior, model or migration behavior, executable test behavior, CI workflow behavior, Playwright configuration behavior, connector/destination dispatch, package mutation/reconstruction, broad qualitative/hybrid/RAG execution, full mockup activation, auth/security behavior, hidden LLM planning, or frontend-only durable authority.

## Decision

```yaml
selected_planning_mode: source_rendered_control_decision
entry_decision: current_raw_mixed_controls_live_no_new_source_controls
base_branch: main
implementation_branch: codex/l3-source-rendered-control-freeze
live_behavior_change: false
current_rendered_source_controls: raw_mixed_current_classes_only
new_source_family_rendered_controls: blocked
browser_source_authority: blocked
local_upload_control: blocked
local_directory_control: blocked
web_connector_control: blocked
rag_vector_control: blocked
implementation_entry_allowed_next: false
next_required_boundary: named_source_family_or_rendered_control_freeze_before_expansion
```

The decision is deliberately narrow. Current raw-mixed controls can help an operator use server-backed `dataset_version` and `aps_content_document` materialization authority. They are not proof that source breadth, local upload, web retrieval, arbitrary files, RAG/vector retrieval, or new source-family controls are available.

## Current Live Control Boundary

The current live rendered source controls are bounded to:

- source preview over admitted source classes;
- raw-mixed current-class seed/materialization setup;
- server-owned manifest/hash authority;
- materialized source ID selection for existing supported source classes;
- normal downstream Layer 3 flow through existing server APIs.

The browser may display state, request allowed current-class actions, and recover convenience form state. It does not own durable source identity, bytes, provenance, storage refs, source freshness, source-family admission, or workflow truth.

## Non-Admitted Rendered Controls

The following controls remain blocked:

- local upload source control;
- local-directory ingestion control;
- arbitrary local path picker;
- broad file upload control;
- web connector retrieval control;
- external URL fetch control;
- RAG/vector retrieval control;
- vector index creation control;
- source adapter registry control;
- new source-family selector beyond current admitted source-family metadata;
- connector/destination source dispatch control;
- package mutation control coupled to source selection;
- full mockup source control activation.

## Validation Evidence

This decision relies on the validation already recorded in `252_GOAL_STACK_IMPLEMENTATION_AUDIT_FREEZE.md`:

- focused source, raw-mixed, source-family, qualitative, and mockup tests passed;
- focused package lifecycle tests passed;
- focused APS downstream/package tests passed;
- targeted Layer 3 API integration tests passed;
- `python .\tools\l3-progress-check.py` passed before and after the audit wiring;
- PR `#809` CI passed and merged to current `main`.

This freeze adds no rendered behavior and therefore does not require a new headed/headless browser proof. A later rendered source-control implementation must provide headed and headless proof across the admitted theme surface before merge.

## Reentry Rules

A later rendered source-control implementation must select exactly one mode:

- `current_raw_mixed_control_extension`;
- `single_named_source_family_selector`;
- `single_server_owned_adapter_control`;
- `source_read_only_inventory_control`.

The selected mode must define the server authority contract, request/response fields, storage/security model, provenance/audit fields, idempotency and stale-authority behavior, leakage controls, disabled/ready/error UI states, theme surface, headed/headless proof plan, and negative invariant tests.

## Negative Invariants

- no new rendered source-family control;
- no browser-local source authority;
- no local upload;
- no local-directory ingestion;
- no arbitrary local path input;
- no web connector retrieval;
- no external URL fetch;
- no RAG/vector retrieval;
- no vector index creation;
- no source adapter registry;
- no source-class expansion beyond current admitted classes;
- no raw mixed seed behavior change;
- no raw mixed materialization behavior change;
- no Layer 3 flow start inside source setup;
- no package mutation/reconstruction;
- no provider/public URL runtime;
- no connector/destination dispatch;
- no broad qualitative/hybrid/RAG runtime;
- no full mockup activation;
- no hidden LLM planning;
- no auth/security behavior change;
- no route/API/DTO/model/migration/service behavior change;
- no executable test behavior change;
- no CI workflow or Playwright configuration change;
- no frontend-only durable authority.

## Stop Condition

Stop before code if the next source rendered-control proposal depends on browser state as durable authority, introduces any new source family without a selected source-family freeze, accepts local paths/files/directories or external URLs, fetches web connector content, builds vectors, changes package/provider/connector/destination behavior as a side effect, or lacks focused backend/API tests plus headed/headless rendered proof for the selected mode.
