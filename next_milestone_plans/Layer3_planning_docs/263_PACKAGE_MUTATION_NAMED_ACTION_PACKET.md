# Package Mutation Named Action Packet

Status: current-main package mutation named-action packet for `package_mutation_named_action_packet`.

## Decision YAML

```yaml
selected_planning_mode: package_mutation_named_action_packet
entry_decision: no_runtime_now_named_rendered_package_action_absent
base_branch: main
implementation_branch: codex/l3-package-action-packet
live_behavior_change: false
upstream_reentry_doc: 255_PACKAGE_MUTATION_REENTRY_DECISION_FREEZE.md
current_package_lifecycle_runtime: backend_api_bounded_lifecycle
named_operator_package_revision_use_case: null
selected_rendered_package_lifecycle_mode: null
package_payload_source_selected: false
downstream_invalidation_policy_selected: false
re_delivery_policy_selected: false
receipt_audit_contract_selected: false
headed_headless_theme_proof_plan_selected: false
implementation_entry_allowed_next: false
next_required_boundary: named_rendered_package_lifecycle_action_before_runtime
rendered_package_mutation_runtime_status: blocked
```

## Purpose

Doc `255_PACKAGE_MUTATION_REENTRY_DECISION_FREEZE.md` requires a single named rendered package lifecycle freeze before rendered package mutation or broader package reconstruction. This packet answers that gate from current repo evidence.

The result is no runtime now. Current main proves bounded backend/API package lifecycle authority. It does not prove a rendered operator package-revision use case, browser-safe mutation control, package payload source, downstream invalidation policy, re-delivery compatibility, or headed/headless/theme proof plan.

## Repo-confirmed package truth

Current package authority remains:

- Backend/API lifecycle runtimes are live for package supersession preview, replacement package-set authority, supersession commit lineage, replacement artifact manifest metadata, and replacement namespace rows.
- Source `L3OutputPackage` rows remain immutable source package authority.
- Source package payload refs and hashes remain authority metadata, not browser-editable payloads.
- Existing rendered controls cover package review preview, package construction commit, and package review submit where already admitted.
- Rendered package mutation/reconstruction controls remain blocked.
- Package payload rewrite, replacement package payload generation, source package row mutation, downstream invalidation runtime, and re-delivery runtime remain blocked.

## Named-action gate result

```yaml
named_package_action_gate:
  named_operator_package_revision_use_case:
    status: not_found_in_current_authority
    consequence: runtime_blocked
  selected_rendered_package_lifecycle_mode:
    status: null
    consequence: runtime_blocked
  package_payload_source:
    status: not_selected
    consequence: runtime_blocked
  immutable_package_rule:
    status: current_source_packages_immutable
    consequence: sufficient_for_existing_backend_lifecycle_only
  downstream_invalidation_policy:
    status: not_selected
    consequence: runtime_blocked
  re_delivery_compatibility_rule:
    status: not_selected
    consequence: runtime_blocked
  receipt_audit_contract:
    status: not_selected
    consequence: runtime_blocked
  stale_authority_failure_plan:
    status: not_selected
    consequence: runtime_blocked
  idempotency_replay_recovery_policy:
    status: not_selected_for_rendered_action
    consequence: runtime_blocked
  headed_headless_theme_proof_plan:
    status: not_selected
    consequence: rendered_controls_blocked
```

## Why no rendered package mutation runtime is selected

A rendered package mutation runtime would need a real operator action and a safe authority model. Current authority does not answer:

- which package lifecycle action the operator needs in the browser;
- whether the first action should be supersession preview, supersession commit, namespace review, or a read-only lifecycle dashboard;
- whether package bytes are never changed, generated server-side, copied from existing immutable artifacts, or eventually editable through a separate generation freeze;
- how stale package authority, downstream invalidation, re-delivery, duplicate action, and recovery behave;
- which receipt and audit fields are response-safe;
- how to prevent package payload bytes, diffs, local paths, refs, hashes, provider URLs, connector targets, destination targets, and tokens from leaking in logs, responses, traces, screenshots, or errors;
- how headed and headless browser proof covers light, dark, and workbench themes if controls are admitted.

Selecting a rendered mutation action without those facts would turn backend lifecycle metadata into browser mutation authority, which the current docs explicitly forbid.

## Required future package-action packet contents

A future rendered package lifecycle runtime entry may proceed only after a packet names:

- one concrete operator package-revision use case;
- one selected rendered package lifecycle mode;
- exact server-authority source package and replacement package ownership;
- package payload source and immutable package rule;
- downstream invalidation policy;
- re-delivery compatibility rule;
- stale-authority failure behavior;
- idempotency, replay, duplicate-action, and recovery behavior;
- receipt/audit contract;
- leak-control policy;
- rendered UI state plan;
- headed/headless/theme proof plan;
- explicit no-go list for source expansion, connector/destination dispatch, provider/public URL runtime, broad qualitative/RAG behavior, full mockup activation, and auth/security behavior.

## Non-admission

This packet admits no runtime behavior, route/API/DTO/model/migration/service behavior, executable test behavior, rendered UI behavior, rendered package mutation controls, rendered package supersession controls, rendered replacement namespace review controls, rendered package lifecycle dashboard, package payload rewrite, package payload generation, source `L3OutputPackage` row mutation, browser-supplied package diffs, browser-supplied package bytes, downstream invalidation runtime, re-delivery runtime, provider/public URL runtime, external connector invocation, destination writes, source expansion, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, broad qualitative/hybrid/RAG execution, full mockup activation, auth/security behavior, hidden LLM planning, CI workflow change, Playwright configuration change, or frontend-only durable authority.

## Stop condition

Stop before implementation if the next package proposal cannot name one rendered package lifecycle action and resolve package authority, payload source, immutable package rule, downstream invalidation, re-delivery, stale-authority, idempotency, receipt/audit, leak-control, browser proof, and no-go boundaries from explicit evidence rather than inference.
