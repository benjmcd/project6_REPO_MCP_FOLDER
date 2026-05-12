# Layer 3 Runtime Freeze Intake Checklist

Status: current-branch runtime-freeze intake checklist after mockup pixel-proof closeout.

```yaml
selected_planning_mode: runtime_freeze_intake_checklist
entry_proof: 284_MOCKUP_PIXEL_PROOF_CLOSEOUT.md
base_branch: main
implementation_branch: codex/l3-runtime-freeze-intake
live_behavior_change: false
runtime_behavior_change: false
rendered_ui_behavior_change: false
next_required_boundary: exact_named_server_authoritative_runtime_use_case_freeze
hard_stop: no_runtime_implementation_without_named_use_case
```

## Purpose

This checklist converts the post-mockup pixel-proof boundary into the concrete intake gate for the next non-visual Layer 3 implementation. The current repo has completed bounded visual proof for `layer3_mockup_workbench_theme`; it has not selected the next runtime use case.

No runtime implementation may proceed from this checklist alone. A future implementation must first produce one freeze that names exactly one server-authoritative runtime family, one mode, and one operator/product use case.

## Eligible runtime families

A future freeze may select exactly one of these families:

| Runtime family | Current status | Required before implementation |
| --- | --- | --- |
| `source_breadth_runtime` | blocked | One named source use case, selected source family/input mode, server-owned source-of-truth, provenance, storage/security, downstream semantics, rendered-control plan if needed. |
| `external_connector_destination_runtime` | blocked | One named connector or destination target, selected dispatch mode, allowlist/config authority, credential model, lifecycle/idempotency, receipt/audit, fake-target tests. |
| `rendered_package_mutation_runtime` | blocked | One named rendered package lifecycle action, package authority, payload rule, invalidation/re-delivery policy, stale-authority behavior, rendered proof if controls change. |
| `broad_qual_hybrid_rag_runtime` | blocked | One named analysis mode, source scope, retrieval/vector/model/provider authority if any, output taxonomy, leakage controls, rendered proof if controls change. |
| `full_mockup_durable_activation` | blocked | One named mockup or rendered-control journey mapped to server authority, route/API contract, durable state owner, browser-storage policy, mockup-to-live mapping, headed/headless/theme proof. |
| `auth_security_runtime` | blocked | One named operator/security mode, identity authority, tenant/session ownership, permission matrix, route dependency contract, audit/security-event contract, secret policy. |

## Minimum freeze contents

A valid next freeze must include all of the following:

- One runtime family and one runtime mode, not a bundle.
- One named operator/product use case.
- Why current admitted behavior is insufficient for that use case.
- Canonical server authority object, row family, or persisted contract.
- Request/response contract, including forbidden fields.
- Stale-authority, idempotency, replay, duplicate, rollback, and failure behavior where applicable.
- Negative tests proving blocked adjacent modes remain blocked.
- Leakage/security controls for identifiers, paths, tokens, prompts, provider data, connector data, package bytes, logs, traces, screenshots, and errors where applicable.
- Headed/headless/theme proof plan if rendered UI behavior changes.
- Explicit no-go list for every Layer 3 family not selected in that slice.
- Commit, PR, review-thread, check, and post-merge verification plan.

## Invalid freeze patterns

The next freeze is invalid if it:

- Selects more than one runtime family.
- Treats mockup text, screenshots, browser storage, local paths, generated IDs, provider URLs, connector IDs, prompts, vectors, or package bytes as authority without server ownership.
- Adds runtime code directly without a freeze.
- Uses green tests or existing manifests as a substitute for naming the use case.
- Widens backend API/model/migration/service behavior without a selected authority object and negative tests.
- Enables source upload, local directory, connector dispatch, package mutation, RAG/vector, full mockup activation, or auth/security behavior as a side effect of another slice.

## Stop condition

If no exact named use case is supplied, the correct next posture is stop-at-planning. Do not implement a runtime slice, do not infer a product use case from repo structure, and do not continue visual churn unless a new explicit mockup frame target or threshold gap is named.
