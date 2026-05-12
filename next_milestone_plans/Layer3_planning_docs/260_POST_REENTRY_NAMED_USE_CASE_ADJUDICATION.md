# Post Reentry Named Use Case Adjudication

Status: current-main adjudication freeze for `post_reentry_named_use_case_adjudication`.

## Decision YAML

```yaml
selected_planning_mode: post_reentry_named_use_case_adjudication
entry_decision: source_breadth_named_use_case_packet_selected_as_next_planning_step
base_branch: main
implementation_branch: codex/l3-post-reentry-use-case-adjudication
live_behavior_change: false
upstream_selection_sync_doc: 259_POST_REENTRY_RUNTIME_SELECTION_SYNC.md
selected_runtime_family: null
selected_runtime_mode: null
named_use_case_selected: false
selected_next_planning_lane: source_breadth_named_use_case_packet
runtime_implementation_allowed_next: false
next_required_artifact: source_breadth_named_use_case_packet_or_explicit_no_runtime_closeout
implementation_entry_allowed_next: false
```

## Purpose

Doc `259_POST_REENTRY_RUNTIME_SELECTION_SYNC.md` prevents direct runtime implementation until one exact named runtime use case is selected. This adjudication answers the next planning question: which candidate family should be forced to produce that use-case packet first.

The answer is source breadth, but only as a planning packet. This document does not select a source family, adapter, route, rendered control, connector, package mutation behavior, RAG/vector behavior, mockup activation, or auth/security behavior. It selects the next decision artifact that must either name the source use case and authority chain or close source breadth again as no-runtime.

## Adjudication result

```yaml
candidate_adjudication:
  source_breadth_runtime:
    rank: 1
    next_step: source_breadth_named_use_case_packet
    reason: upstream_input_provenance_is_foundational_for_later_analysis_package_connector_and_rag_work
    runtime_status: blocked_until_named_source_use_case_packet
  external_connector_destination_runtime:
    rank: 2
    next_step: keep_blocked_until_source_or_delivery_use_case_is_named
    reason: connector_or_destination_writes_depend_on_artifact_authority_and_named_target
    runtime_status: blocked
  package_mutation_rendered_runtime:
    rank: 3
    next_step: keep_blocked_until_named_operator_package_revision_use_case
    reason: rendered_mutation_controls_need_server_authority_and_downstream_invalidation_rules
    runtime_status: blocked
  broad_qual_hybrid_rag_runtime:
    rank: 4
    next_step: keep_blocked_until_source_set_and_analysis_mode_are_named
    reason: broad_analysis_or_rag_without_source_contract_would_blur_provenance_and_leakage_controls
    runtime_status: blocked
  browser_full_mockup_runtime:
    rank: 5
    next_step: keep_blocked_until_one_mockup_control_maps_to_server_authority
    reason: target_state_design_inputs_are_not_runtime_authority
    runtime_status: blocked
  auth_security_runtime:
    rank: conditional
    next_step: escalate_first_only_if_selected_source_use_case_requires_new_identity_permission_or_secret_policy
    reason: security_must_gate_nonlocal_or_sensitive_surfaces_but_should_not_be_overbuilt_without_a_selected_surface
    runtime_status: blocked
```

## Why source breadth is the next planning lane

Source breadth remains the correct next planning lane for three reasons:

- It is upstream of broad qualitative, hybrid/RAG, package lifecycle expansion, and connector/destination delivery because those downstream surfaces need stable source identity, bytes, metadata, freshness, and provenance.
- Current repo truth already has bounded source behavior for `dataset_version` and `aps_content_document`, so the next source question can be asked precisely: what concrete operator need cannot be satisfied by those current classes and current raw-mixed materialization paths?
- A source-use-case packet can fail closed. If it cannot name a source family, adapter/input mode, storage/security model, provenance contract, downstream semantics, rendered-control obligation, and auth/security posture, the correct result is no-runtime closeout rather than speculative code.

## Why this does not select runtime

This pass does not select runtime because the product/operator use case is still absent. It would be an assumption to choose local upload, local directory ingestion, web connector retrieval, RAG/vector retrieval, broad file upload, or another source family from repo structure alone.

The next artifact must provide all of:

- one concrete source use case;
- proof that current `dataset_version` and `aps_content_document` behavior is insufficient;
- one selected source family or explicit `none_selected_runtime_blocked` outcome;
- one adapter/input mode;
- source-of-truth ownership for identity, bytes, metadata, freshness, and provenance;
- storage/security model and leakage posture;
- network retrieval policy;
- downstream semantics for material preview, Gate B/Gate C, execution, package, handoff/export, and qualitative/RAG lanes;
- rendered-control plan if any UI change is needed;
- auth/security escalation rule if identity, credential, permission, or nonlocal exposure is required.

## Non-fragility and scalability constraints

The next source packet must preserve these constraints:

- No browser-local source authority.
- No local path as durable truth.
- No provider, connector, prompt/model, vector, or generated id as authority without a selected freeze.
- No multi-family source registry as the first implementation.
- No hidden coupling between source selection and package mutation, connector dispatch, RAG, or mockup activation.
- No rendered controls without server authority and headed/headless/theme proof.
- No auth/security overbuild unless the selected source surface makes it necessary.
- Tests must prove admitted behavior and blocked adjacent behaviors; happy-path proof alone is insufficient.

## Non-admission

This adjudication admits no runtime behavior, route/API/DTO/model/migration/service behavior, executable test behavior, rendered UI behavior, source adapter registry behavior, local upload, local-directory ingestion, web connector retrieval, broad file upload, RAG/vector retrieval, vector index creation, external connector invocation, destination writes, package mutation/reconstruction, broad qualitative/hybrid/RAG execution, full mockup activation, auth/security behavior, hidden LLM planning, provider/public URL behavior, CI workflow change, Playwright configuration change, or frontend-only durable authority.

## Stop condition

Stop before implementation unless the next source-breadth packet names one concrete source use case and resolves every required source authority dimension. If it cannot do that from repo-confirmed evidence and product intent, the packet must close as `no_runtime_now`.
