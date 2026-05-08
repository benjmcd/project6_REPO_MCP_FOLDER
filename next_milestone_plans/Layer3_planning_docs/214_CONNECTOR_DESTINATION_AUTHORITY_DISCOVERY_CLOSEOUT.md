# Connector/Destination Authority Discovery Closeout

Status: current-main planning/control closeout for `connector_destination_authority_discovery_closeout`.

This document is a post-PR #769 authority-discovery closeout over docs `189_CONNECTOR_DESTINATION_ENTRY_FREEZE.md`, `190_CONNECTOR_DESTINATION_ENTRY_CONTRACT.md`, `203_POST_756_GOVERNANCE_CLOSEOUT.md`, `212_CI_OBSERVABILITY_NO_RUNTIME_CLOSEOUT.md`, and `213_PROVIDER_PUBLIC_URL_AUTHORITY_DISCOVERY_CLOSEOUT.md`. It does not replace those docs and does not implement new connector/destination runtime, external connector invocation, destination writes, generic downstream dispatch, connector-run creation, provider/public URLs, provider object writes, provider object copies, provider ACL changes, package mutation, source expansion, RAG/vector retrieval, full mockup activation, hidden LLM planning, auth/security behavior, route, DTO, model, migration, service behavior, test behavior, or rendered UI controls.

## Decision

The selected authority-discovery decision is:

```yaml
selected_planning_mode: connector_destination_authority_discovery_closeout
entry_decision: no_runtime_now
selected_mode: null
runtime_status: not_implemented
live_internal_record_only_status: already_admitted_by_doc_121
authority_discovery_result: insufficient_authority_for_external_connector_destination_runtime
implementation_entry_required_before_runtime: true
next_product_boundary_required: true
```

No new connector/destination runtime is admitted by this pass.

The already-live `internal_dispatch_record_only` path remains governed by `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md`, `/api/v1/layer3/handoff/connector/record`, and `backend/app/services/layer3_connector_dispatch_entry.py`. This closeout does not expand that runtime into external connector invocation, destination writes, connector-run creation, generic downstream dispatch, queue/retry/cancel behavior, or rendered controls.

Docs `189` and `190` already freeze the connector/destination entry posture as deferred. This pass records the current-main discovery result after provider/public URL authority discovery was closed out: the repo still has no concrete external connector authority, destination authority, named downstream use case, selected connector/destination family, credential/access model, lifecycle/retry/cancel/timeout contract, receipt/audit contract, fake connector/destination test architecture, or leak-control proof sufficient to select a runtime mode.

The only future candidate modes remain:

- `single_named_connector_dispatch`;
- `single_named_destination_dispatch`;
- `internal_dispatch_record_only_extension`.

Do not choose a runtime mode unless a later implementation-entry freeze proves why same-origin delivery, same-origin signed references, provider/public URL non-admission, and the existing internal record-only runtime are insufficient for a named downstream use case.

## Current-Main Authority Evidence

```yaml
authority_evidence:
  live_main_anchor:
    status: verified
    evidence:
      - project6-origin/main at d84e5238a2fbd35c40d38278fe01395ee1622afd during this pass
      - python .\tools\l3-progress-check.py
      - git diff --check
  internal_dispatch_record_only:
    status: verified
    evidence:
      - next_milestone_plans/Layer3_planning_docs/121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md
      - backend/app/services/layer3_connector_dispatch_entry.py
      - backend/app/api/layer3.py
      - backend/tests/test_layer3_api.py
      - tools/l3-progress-check.py
  provider_public_url_authority_discovery_closeout:
    status: verified
    evidence:
      - next_milestone_plans/Layer3_planning_docs/213_PROVIDER_PUBLIC_URL_AUTHORITY_DISCOVERY_CLOSEOUT.md
  external_connector_authority:
    status: unverified
    evidence: []
  destination_authority:
    status: unverified
    evidence: []
  named_downstream_use_case:
    status: unverified
    evidence: []
  selected_connector_or_destination_family:
    status: unverified
    evidence: []
  credential_and_access_model:
    status: unverified
    evidence: []
  lifecycle_retry_cancel_timeout_contract:
    status: unverified
    evidence: []
  receipt_and_audit_contract:
    status: unverified
    evidence: []
  fake_connector_destination_test_architecture:
    status: unverified
    evidence: []
```

The repo-confirmed connector/destination references in current source and tests prove bounded internal record-only behavior plus broad-dispatch non-admission. They are not authority for external invocation or destination writes.

## Source/Test Discovery Result

Current source/test inspection confirms this posture:

- `backend/app/services/layer3_connector_dispatch_entry.py` owns `internal_dispatch_record_only`, requires exact internal-record fields, blocks connector/destination/provider/source/package/RAG/retry/cancel/hidden-LLM fields, and returns `external_connector_invocation_enabled: False`, `destination_write_enabled: False`, `connector_run_created: False`, and `provider_public_url_enabled: False`.
- `backend/app/api/layer3.py` exposes connector/destination terms only through the existing internal record-only endpoint, known-but-non-admitted request fields, disabled flags, or schema guards.
- `backend/app/services/layer3_preflight_request_contract.py`, `backend/app/services/layer3_package_mutation_entry.py`, `backend/app/services/layer3_package_supersession_commit.py`, `backend/app/services/layer3_replacement_package_*`, `backend/app/services/layer3_mockup_boundary.py`, and `backend/app/services/layer3_state_action_contract.py` keep broad `connector_destination_dispatch` blocked or disabled.
- `backend/tests/test_layer3_api.py`, `backend/tests/test_layer3_bounded_e2e.py`, `backend/tests/test_layer3_mockup_boundary.py`, `backend/tests/test_layer3_preflight_request_contract.py`, and related focused tests assert broad connector/destination dispatch remains forbidden, disabled, absent from side effects, or deferred.

This evidence proves non-admission for external dispatch and preserves the bounded internal record-only path. It does not prove external connector/destination readiness or runtime suitability.

## Authority Discovery Ledger

```yaml
authority_discovery_ledger:
  external_connector_authority:
    result: not_found
    consequence: runtime_blocked
  destination_authority:
    result: not_found
    consequence: runtime_blocked
  named_downstream_use_case:
    result: not_found
    consequence: runtime_blocked
  selected_mode:
    result: null
    consequence: runtime_blocked
  selected_connector_or_destination_family:
    result: null
    consequence: runtime_blocked
  artifact_family:
    result: null
    consequence: runtime_blocked
  credential_and_access_model:
    result: not_defined
    consequence: runtime_blocked
  lifecycle_retry_cancel_timeout_contract:
    result: not_defined
    consequence: runtime_blocked
  receipt_and_audit_contract:
    result: not_defined
    consequence: runtime_blocked
  fake_connector_destination_test_architecture:
    result: not_defined
    consequence: runtime_blocked
```

## Runtime Non-Admission

```yaml
runtime_admission:
  new_connector_destination_runtime: false
  external_connector_invocation: false
  destination_write: false
  connector_run_creation: false
  generic_downstream_dispatch: false
  internal_dispatch_record_only_expansion: false
  provider_public_url_runtime: false
  provider_object_write_or_copy: false
  provider_object_acl_change: false
  package_mutation_reconstruction: false
  source_expansion: false
  rag_vector_retrieval: false
  hidden_llm_planning: false
  full_mockup_activation: false
  auth_security_behavior_change: false
  rendered_ui_control_change: false
  test_behavior_change: false
```

## Theme And UI Posture

This pass adds no rendered UI controls. If a later freeze admits rendered connector/destination controls, it must preserve the current theme split:

- `light` remains the inspection/status/preview/review theme surface;
- `dark` remains the execution/package-construction theme surface;
- `workbench` remains the package submit, handoff/export, APS handoff, external export/download, signed-reference, provider/public URL governance, and downstream operation-dock theme surface.

A later rendered implementation must prove headed and headless Chromium consistency before merge and must not treat browser state or mockups as durable authority.

## Negative Invariants

- no new connector/destination runtime;
- no external connector invocation;
- no destination write;
- no connector-run creation;
- no generic downstream dispatch;
- no internal_dispatch_record_only behavior expansion;
- no provider/public URL runtime;
- no provider object write, copy, mutation, materialization, ACL change, or lifecycle management;
- no connector, destination, or provider credentials in browser, request payloads, responses, logs, traces, screenshots, or error bodies;
- no connector/destination secrets, targets, URLs, tokens, or receipts leaking in logs, traces, screenshots, error bodies, proof manifests, or response fields;
- no package payload rewrite, package mutation, package reconstruction, replacement payload generation, or supersession behavior change;
- no source expansion, local upload, local-directory ingestion, arbitrary local path input, web connector retrieval, or source adapter registry behavior;
- no RAG/vector retrieval, embedding generation, broad qualitative execution, hybrid execution, prompt/model/provider runtime, or hidden LLM planning;
- no full mockup activation, frontend-only durable authority, browser-local durable authority, or new rendered UI controls;
- no auth/security behavior change, route-level auth dependency change, tenant/session ownership runtime, permission runtime, or storage exposure expansion;
- no CI workflow change, Playwright configuration change, executable test behavior change, dependency change, artifact retention change, headed-browser CI matrix, sharding/parallelism change, or observability runtime;
- no same-origin attachment delivery, same-origin signed-reference, provider/public URL governance, package review, handoff/export, APS handoff, external export/download, artifact hash/size, or internal dispatch record semantics change;
- no route, DTO, model, migration, production service behavior, or test behavior change.

## Next Boundary

External connector/destination runtime should not be implemented next unless a concrete named downstream use case emerges and a later implementation-entry freeze proves the missing authority listed above.

The next implementation-eligible boundary should move to one of:

1. `source_breadth_authority_discovery_freeze_or_entry_freeze_update`, if source expansion is the blocker;
2. `package_mutation_rendered_authority_discovery_freeze_or_entry_freeze_update`, if operator package revision is the blocker;
3. `qual_hybrid_rag_authority_discovery_freeze_or_entry_freeze_update`, if broader analysis execution is the blocker;
4. `connector_destination_runtime_entry_freeze_update` only if a named downstream destination requires direct dispatch and the required authority is proven.

## Stop Condition

Stop before implementation if any proposed change needs external connector authority, destination authority, connector/destination mode selection, credential/access model, lifecycle/retry/cancel/timeout behavior, receipt/audit behavior, access authority, leak controls, stale-authority tests, fake connector/destination architecture, rendered connector/destination controls, or auth/security posture that this closeout has not verified.
