# Full Mockup Activation Reentry Decision Freeze

Status: current-main reentry decision freeze for `full_mockup_activation_reentry_decision`.

This document follows `256_QUAL_HYBRID_RAG_REENTRY_DECISION_FREEZE.md`. It records the full mockup activation reentry decision after the goal-stack, source rendered-control, connector/destination, package mutation, and qualitative/hybrid/RAG reentry audits: current main keeps mockups as target-state design/specification inputs and preserves existing server-authoritative rendered controls only where already proven, but no full mockup activation, frontend-only durable workflow authority, browser-local persistence as authority, new rendered mockup controls, route/API behavior change, DTO behavior change, model/migration change, production service behavior change, source expansion, package mutation, provider/public URL runtime, connector/destination dispatch, broad qualitative/hybrid/RAG behavior, hidden LLM planning, auth/security behavior, or CI/Playwright behavior change is admitted.

## Decision

```yaml
selected_planning_mode: full_mockup_activation_reentry_decision
entry_decision: mockups_target_state_only_activation_blocked
base_branch: main
implementation_branch: codex/l3-full-mockup-reentry-freeze
live_behavior_change: false
current_mockup_truth_state: mockups_target_state_only
current_rendered_workbench_status: existing_server_authoritative_controls_only
current_browser_proof_status: bounded_headed_headless_proofs_for_admitted_paths
full_mockup_activation: blocked
frontend_only_durable_state: blocked
browser_local_persistence_as_authority: blocked
new_rendered_mockup_controls: blocked
route_api_behavior_change: blocked
server_authority_contract_for_mockups: missing
mockup_to_live_state_mapping: missing
operator_journey_scope: missing
theme_accessibility_headed_headless_plan: missing
implementation_entry_allowed_next: false
next_required_boundary: single_named_mockup_or_rendered_control_mode_freeze_before_activation
```

The decision is deliberately not an activation implementation. Existing mockup artifacts can inform design and planning, and existing rendered Layer 3 controls remain live only where server-backed routes and tests already prove them. Mockup text, screenshots, local storage, browser session state, manually clicked flows, or target-state planning prose are not durable runtime authority.

## Current Live Boundary

The current mockup/browser boundary is:

- owner service: `backend/app/services/layer3_mockup_boundary.py`;
- mockup truth-state mode: `mockups_target_state_only`;
- mockup files: `next_milestone_plans/layer3-mockups/assets.md` and `next_milestone_plans/layer3-mockups/mockup-spec.txt`;
- rendered route: `/review/layer3` only for existing server-authoritative controls;
- proof posture: existing headed/headless browser tests prove admitted paths only;
- browser state: display, draft, recovery, or theme convenience only, not server or workflow authority.

## Runtime Still Blocked

The following remain blocked:

- full mockup activation;
- full mockup program activation;
- frontend-only durable workflow state;
- browser-local persistence as authority;
- browser-only workflow authority;
- mockup text, screenshots, manually clicked flows, copied output, or local storage as server authority;
- new rendered mockup controls;
- route/API behavior change;
- DTO behavior change;
- model or migration change;
- production service behavior change;
- source expansion, local upload, local-directory ingestion, web retrieval, or unbounded runtime DB source reads;
- package mutation/reconstruction;
- provider/public URL runtime;
- connector/destination dispatch;
- broad qualitative/hybrid/RAG behavior;
- hidden LLM planning;
- auth/security behavior changes;
- Playwright configuration or browser-mode changes.

## Reentry Requirements

A later mockup or browser activation implementation may proceed only if it selects exactly one mode:

- `single_existing_rendered_control_extension`;
- `single_mockup_screen_read_only_projection`;
- `single_mockup_screen_server_authoritative_activation`;
- `full_mockup_program_activation`;
- `mockup_to_live_mapping_inventory_only`.

The selected mode must define:

- named operator journey;
- mockup source owner;
- route/API contract;
- server authority contract;
- durable state owner;
- browser storage policy;
- mockup-to-live state mapping;
- idempotency, stale-authority, and recovery behavior;
- negative invariant tests for source, package, provider, connector, RAG, prompt/model, auth, and browser-local authority boundaries;
- leak-control policy for local paths, provider URLs, connector targets, destination targets, source credentials, auth tokens, prompt text, browser storage secrets, screenshots, logs, error bodies, traces, and responses;
- theme, accessibility, responsive layout, headed Chromium proof, and headless Chromium proof.

## Validation Evidence

This freeze relies on already-landed implementation/audit evidence:

- PR `#809` recorded the goal-stack implementation audit and proved the current bounded implementation state.
- PR `#810` recorded the source rendered-control decision and preserved source/rendered non-admission.
- PR `#811` recorded the connector/destination reentry decision and preserved external dispatch non-admission.
- PR `#812` recorded the package mutation reentry decision and preserved rendered/broad mutation non-admission.
- PR `#813` recorded the qualitative/hybrid/RAG reentry decision and preserved broad analysis/RAG non-admission.
- Current mockup truth state remains governed by `125_MOCKUP_TRUTH_STATE_FREEZE.md`.
- Current full mockup activation non-admission remains governed by `197_BROWSER_FULL_MOCKUP_ACTIVATION_ENTRY_FREEZE.md`, `198_BROWSER_FULL_MOCKUP_ACTIVATION_ENTRY_CONTRACT.md`, and `218_BROWSER_FULL_MOCKUP_AUTHORITY_DISCOVERY_CLOSEOUT.md`.
- `python .\tools\l3-progress-check.py` must pass after this freeze is wired.

This validation does not prove full mockup operator completeness, mockup-to-live route mapping, server authority for mockup screens, browser storage safety, accessibility conformance, new rendered-control usability, or auth/security production readiness.

## Negative Invariants

- no full mockup activation;
- no full mockup program activation;
- no frontend-only durable state;
- no browser-local persistence as authority;
- no browser-only workflow authority;
- no mockup text treated as server authority;
- no screenshot or manually clicked flow treated as server authority;
- no copied browser output treated as server authority;
- no new rendered mockup controls;
- no route/API behavior change;
- no DTO behavior change;
- no model or migration change;
- no production service behavior change;
- no executable test behavior change;
- no Playwright configuration change;
- no browser mode change;
- no source expansion;
- no local upload;
- no local-directory ingestion;
- no arbitrary local path input;
- no web connector retrieval;
- no package mutation/reconstruction;
- no provider/public URL runtime;
- no connector or destination dispatch;
- no broad qualitative/hybrid/RAG runtime;
- no hidden LLM planning;
- no prompt/model/provider runtime;
- no theme-specific durable authority;
- no auth/security behavior change;
- no CI workflow change.

## Stop Condition

Stop before code if the next mockup/browser proposal lacks one named activation mode, treats mockup text/screenshots/browser state as durable authority, lacks a server route/API contract, lacks a durable state owner, lacks browser storage policy, lacks headed/headless/theme/accessibility proof, accepts local paths/storage/screenshots as authority, mutates source/package/provider/connector/RAG state as a side effect, activates hidden LLM behavior, changes auth/security behavior, or widens CI/browser behavior without a dedicated freeze.
