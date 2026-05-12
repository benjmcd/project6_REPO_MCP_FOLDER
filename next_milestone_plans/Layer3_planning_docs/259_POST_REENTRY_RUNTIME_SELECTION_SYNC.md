# Post Reentry Runtime Selection Sync

Status: current-main selection sync for `post_reentry_runtime_selection_sync`.

## Decision YAML

```yaml
selected_planning_mode: post_reentry_runtime_selection_sync
entry_decision: no_runtime_selected_after_reentry_closeout
base_branch: main
implementation_branch: codex/l3-post-reentry-runtime-selection-sync
live_behavior_change: false
upstream_closeout_doc: 258_GOAL_STACK_REENTRY_CLOSEOUT_AND_IMPLEMENTATION_GATE.md
selected_runtime_family: null
selected_runtime_mode: null
named_use_case_selected: false
source_breadth_runtime: blocked_until_named_source_use_case
external_connector_destination_runtime: blocked_until_named_connector_or_destination_use_case
package_mutation_rendered_runtime: blocked_until_named_rendered_package_lifecycle_use_case
broad_qual_hybrid_rag_runtime: blocked_until_named_analysis_use_case
browser_full_mockup_runtime: blocked_until_named_mockup_or_rendered_control_use_case
auth_security_runtime: blocked_until_named_security_operator_access_use_case
implementation_entry_allowed_next: false
next_required_boundary: exact_named_runtime_use_case_selection_or_stop_at_planning
```

## Purpose

Doc `258_GOAL_STACK_REENTRY_CLOSEOUT_AND_IMPLEMENTATION_GATE.md` closed the reentry stack and required one named runtime mode before any next code. This sync records the current post-closeout selection state: no runtime family, runtime mode, operator use case, source family, connector target, package lifecycle action, analysis/RAG mode, mockup activation path, or auth/security mode has been selected.

The value of this pass is negative control. It prevents a planning-closeout milestone from being treated as implicit permission to implement the next appealing runtime slice. The repo already has several bounded live surfaces, but the remaining stack is heterogeneous enough that direct implementation without a named mode would blur authority, contracts, test scope, leakage posture, and rendered-control proof obligations.

## Current admitted truth

The current bounded implementation truth remains unchanged:

- Current-class source behavior is live only for the admitted `dataset_version` and `aps_content_document` families and current raw-mixed server-owned materialization paths.
- Existing `/review/layer3` source controls are live only where they drive server-authoritative current-class raw-mixed behavior.
- Connector/destination behavior is live only as internal dispatch record-only authority, not external connector invocation or destination writes.
- Package lifecycle behavior is live only for bounded backend/API package paths already frozen and proven; rendered package mutation and broad reconstruction remain blocked.
- Qualitative behavior is live only for the single APS-document pass and bounded qualitative APS downstream chain; broad qualitative, hybrid, RAG/vector, embeddings, prompt/model/provider runtime, and comparative/cross-document synthesis remain blocked.
- Mockups remain target-state design/specification inputs unless a separate freeze maps one mockup control to live server authority.

## Why no runtime is selected

No implementation can be justified from the current planning state because the next runtime question is under-specified across the exact dimensions that determine safe code shape:

- `source_breadth_runtime` still lacks one named new-source use case, selected source family, adapter/input mode, storage/security model, network retrieval policy if any, and rendered-control obligations.
- `external_connector_destination_runtime` still lacks one named connector or destination, invocation/write semantics, allowlist, idempotency, receipt/audit payload, authorization posture, and failure-state vocabulary.
- `package_mutation_rendered_runtime` still lacks one named rendered package lifecycle action, server authority source, mutation/reconstruction boundary, downstream invalidation posture, and browser proof scope.
- `broad_qual_hybrid_rag_runtime` still lacks one named analysis mode, source set, retrieval/vector/embedding policy if any, prompt/model/provider boundary, citation/provenance contract, and negative leakage tests.
- `browser_full_mockup_runtime` still lacks one selected mockup control, live-state mapping, server authority contract, storage boundary, and headed/headless/theme proof plan.
- `auth_security_runtime` still lacks one selected operator/security mode, identity/tenant model, permission boundary, threat/leakage posture, and route-level enforcement plan.

## Required next boundary before code

Before any runtime implementation branch starts, a new freeze must select exactly one named runtime use case and define the smallest safe implementation shape. That freeze must include:

- One runtime family and one runtime mode, not a bundle.
- The canonical server authority object or row family.
- Request and response contracts, including forbidden fields.
- Idempotency and stale-authority behavior.
- Negative tests for blocked adjacent modes.
- Leakage/security controls appropriate to the selected mode.
- Headed/headless/theme proof only if rendered UI changes are admitted.
- Explicit no-go list for all neighboring families not selected.

## Non-admission

This sync admits no runtime behavior, route/API/DTO/model/migration/service behavior, executable test behavior, rendered UI behavior, source adapter registry behavior, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, external connector invocation, destination writes, package mutation/reconstruction, broad qualitative/hybrid/RAG execution, full mockup activation, auth/security behavior, hidden LLM planning, provider/public URL behavior, CI workflow change, Playwright configuration change, or frontend-only durable authority.

## Validation and proof posture

Validation is limited to planning/control consistency:

- `tools/l3-progress-check.py` must guard this document and its README, board, progress-manifest, and proof-manifest wiring.
- JSON manifests must remain valid.
- The pass must remain docs/control-only and must not touch runtime code.
