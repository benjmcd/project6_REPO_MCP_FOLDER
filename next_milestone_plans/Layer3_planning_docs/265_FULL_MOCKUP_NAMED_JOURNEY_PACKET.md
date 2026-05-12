# Full Mockup Named Journey Packet

Status: current-main full mockup named-journey packet for `full_mockup_named_journey_packet`.

## Decision YAML

```yaml
selected_planning_mode: full_mockup_named_journey_packet
entry_decision: no_runtime_now_named_mockup_journey_absent
base_branch: main
implementation_branch: codex/l3-mockup-journey-packet
live_behavior_change: false
upstream_reentry_doc: 257_FULL_MOCKUP_ACTIVATION_REENTRY_DECISION_FREEZE.md
current_mockup_truth_state: mockups_target_state_only
named_operator_journey: null
selected_activation_mode: null
mockup_source_owner_selected: false
route_api_contract_selected: false
server_authority_contract_selected: false
durable_state_owner_selected: false
browser_storage_policy_selected: false
mockup_to_live_state_mapping_selected: false
theme_accessibility_headed_headless_plan_selected: false
implementation_entry_allowed_next: false
next_required_boundary: named_mockup_or_rendered_control_journey_before_activation
full_mockup_activation_status: blocked
```

## Purpose

Doc `257_FULL_MOCKUP_ACTIVATION_REENTRY_DECISION_FREEZE.md` requires a single named mockup or rendered-control mode before activation. This packet answers that gate from current repo evidence.

The result is no runtime now. Current main proves mockups are target-state design/specification inputs and that `/review/layer3` is live only for existing server-authoritative controls. It does not prove a full mockup source owner, named operator journey, route/API contract, server authority contract, durable state owner, browser storage authority policy, mockup-to-live mapping, or theme/accessibility/headed/headless proof plan.

## Repo-confirmed mockup truth

Current mockup/browser authority remains:

- Mockup files are target-state design/specification inputs only.
- Existing `/review/layer3` controls remain live only where server-backed routes and tests already prove them.
- Browser local/session state is convenience state only, not durable workflow authority.
- Existing headed/headless proof applies to admitted rendered paths only.
- Full mockup activation, frontend-only durable state, browser-local persistence as authority, and new rendered mockup controls remain blocked.

## Named-journey gate result

```yaml
named_mockup_journey_gate:
  named_operator_journey:
    status: not_found_in_current_authority
    consequence: runtime_blocked
  selected_activation_mode:
    status: null
    consequence: runtime_blocked
  mockup_source_owner:
    status: not_selected
    consequence: runtime_blocked
  route_api_contract:
    status: not_selected
    consequence: runtime_blocked
  server_authority_contract:
    status: not_selected
    consequence: runtime_blocked
  durable_state_owner:
    status: not_selected
    consequence: runtime_blocked
  browser_storage_policy:
    status: convenience_only_not_authority
    consequence: insufficient_for_activation
  mockup_to_live_state_mapping:
    status: not_selected
    consequence: runtime_blocked
  theme_accessibility_headed_headless_plan:
    status: not_selected
    consequence: rendered_activation_blocked
  auth_security_posture:
    status: not_selected_for_mockup_activation
    consequence: runtime_blocked
```

## Why no mockup activation is selected

Full mockup activation would need a real operator journey and a server-authoritative mapping. Current authority does not answer:

- which mockup screen or existing rendered control should activate first;
- who owns the mockup source and when it supersedes design-only status;
- which route/API contract backs the screen;
- which server state is durable authority;
- what browser storage may cache versus what it may never own;
- how mockup fields map to live state, package, source, handoff, delivery, or downstream operations;
- how stale state, idempotency, recovery, and disabled states behave;
- how theme, accessibility, responsive layout, focus, headed Chrome, and headless Chrome proof would be run.

Selecting activation from mockup text, screenshots, browser storage, or manually clicked flows would overclaim design artifacts as runtime authority.

## Required future mockup-journey packet contents

A future mockup or rendered-control activation may proceed only after a packet names:

- one operator journey;
- one selected mode: `single_existing_rendered_control_extension`, `single_mockup_screen_read_only_projection`, `single_mockup_screen_server_authoritative_activation`, `full_mockup_program_activation`, or `mockup_to_live_mapping_inventory_only`;
- mockup source owner;
- route/API contract;
- server authority contract;
- durable state owner;
- browser storage policy;
- mockup-to-live state mapping;
- idempotency, stale-authority, and recovery behavior;
- negative invariant tests for source, package, provider, connector, RAG, prompt/model, auth, and browser-local authority boundaries;
- leak-control policy;
- theme, accessibility, responsive layout, headed Chromium proof, and headless Chromium proof.

## Non-admission

This packet admits no runtime behavior, full mockup activation, full mockup program activation, single-screen activation, frontend-only durable state, browser-local persistence as authority, browser-only workflow authority, mockup text as server authority, screenshots as server authority, copied browser output as server authority, route/API/DTO/model/migration/service behavior, executable test behavior, rendered UI behavior, new rendered controls, source expansion, local upload, local-directory ingestion, web connector retrieval, package mutation/reconstruction, provider/public URL runtime, external connector invocation, destination writes, broad qualitative/hybrid/RAG execution, RAG/vector retrieval, hidden LLM planning, auth/security behavior, CI workflow change, Playwright configuration change, or frontend-only durable authority.

## Stop condition

Stop before implementation if the next mockup/browser proposal cannot name one operator journey and resolve activation mode, source owner, route/API contract, server authority, durable state, browser storage policy, mockup-to-live mapping, browser proof, leakage, and no-go boundaries from explicit evidence rather than inference.
