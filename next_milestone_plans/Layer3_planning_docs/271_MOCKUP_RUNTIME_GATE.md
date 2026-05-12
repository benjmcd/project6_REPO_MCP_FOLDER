# Layer 3 Mockup Runtime Gate

Status: current-branch planning/control gate after mockup frame-map proof.

```yaml
selected_planning_mode: post_mockup_runtime_gate
entry_decision: no_runtime_selected_after_mockup_visual_proof
base_branch: main
implementation_branch: codex/l3-post-mockup-runtime-gate
live_behavior_change: false
upstream_mockup_proof_docs:
  - 268_MOCKUP_THEME_FREEZE.md
  - 269_MOCKUP_THEME_ENTRY_FREEZE.md
  - 270_MOCKUP_THEME_SHELL_PROOF.md
mockup_visual_proof_status: static_theme_frame_projection_proven
runtime_implementation_allowed_next: false
next_required_boundary: exact_named_server_authoritative_runtime_use_case_freeze
```

## Decision

The landed mockup workbench theme proof establishes only that selected repo-local mockup frames now have a static rendered projection in the dedicated `layer3_mockup_workbench_theme` surface. It does not select a new server-authoritative runtime use case, source family, connector target, package lifecycle action, broad analysis mode, auth/security mode, or full durable mockup workflow.

This gate authorizes static rendered theme proof only. It does not authorize backend/runtime expansion.

## Runtime gate matrix

| Runtime family | Gate status | Required before implementation |
| --- | --- | --- |
| Source breadth runtime | `source_breadth_runtime: blocked_until_named_source_use_case` | One named source use case with selected source family, input mode, source of truth, storage/security model, provenance, downstream semantics, rendered-control plan, and auth/security posture. |
| External connector/destination runtime | `external_connector_destination_runtime: blocked_until_named_connector_or_destination_target` | One named connector or destination target with credential/access model, lifecycle contract, receipt/audit contract, fake-target proof, rendered-control plan, and auth/security posture. |
| Rendered package mutation runtime | `rendered_package_mutation_runtime: blocked_until_named_package_lifecycle_action` | One named package lifecycle action with package authority, invalidation/redelivery rules, stale-authority/idempotency behavior, negative tests, and rendered theme proof. |
| Broad qualitative/hybrid/RAG runtime | `broad_qual_hybrid_rag_runtime: blocked_until_named_analysis_mode` | One named analysis mode with source scope, retrieval corpus, vector storage policy if any, model/prompt/provider authority, output taxonomy, leakage controls, and rendered-control proof. |
| Full mockup durable activation | `full_mockup_durable_activation: blocked_until_one_mockup_control_maps_to_server_authority` | One mockup control or journey mapped to a server authority object, route/API contract, durable state owner, browser-storage policy, stale-authority behavior, and headed/headless/theme proof. |
| Auth/security runtime | `auth_security_runtime: blocked_until_named_operator_access_security_mode` | One named operator access mode with identity authority, tenant/session ownership, permission matrix, route dependency contract, audit events, provider/connector secret policy, and rendered identity-control plan. |

## What the mockup proof does authorize

- Dedicated theme selection and deterministic fixture projection for `layer3_mockup_workbench_theme`.
- Static rendered projection of selected mockup/user-flow regions into visible UI selectors.
- Headed/headless and responsive proof for the static theme surface already admitted by docs `268` through `270`.
- Continued use of mockups as visual/user-flow acceptance authority for future bounded slices.

## What remains blocked without a later freeze

- backend API/model/migration/service changes
- source runtime
- connector/destination dispatch
- package mutation
- broad qualitative/hybrid/RAG runtime
- full durable mockup activation
- auth/security runtime
- frontend-only durable authority

## Required contents of the next runtime freeze

A later implementation-entry freeze must name exactly one server-authoritative runtime use case before code. The freeze must include:

- selected runtime family, mode, and product/operator use case
- canonical server authority object, row, or persisted contract
- request/response contract and route/UI exposure if any
- explicitly forbidden fields and no-go surfaces
- stale-authority, idempotency, and replay behavior
- negative tests and fail-closed empty-runtime behavior
- leakage/security controls for identifiers, paths, tokens, prompts, and provider or connector data
- headed/headless/theme proof if rendered UI behavior changes
- explicit no-go list for every adjacent Layer 3 family not selected in that slice

## Stop condition

If no exact named server-authoritative runtime use case is selected, work must stop at planning/control. The correct next posture is not a partial runtime implementation, not a browser-owned durable mockup workflow, and not a speculative backend/API expansion.
