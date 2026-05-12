# Connector Destination Named Target Packet

Status: current-main connector/destination named-target packet for `connector_destination_named_target_packet`.

## Decision YAML

```yaml
selected_planning_mode: connector_destination_named_target_packet
entry_decision: no_runtime_now_named_connector_or_destination_absent
base_branch: main
implementation_branch: codex/l3-connector-target-packet
live_behavior_change: false
upstream_reentry_doc: 254_CONNECTOR_DESTINATION_REENTRY_DECISION_FREEZE.md
current_connector_destination_runtime: internal_dispatch_record_only
named_downstream_use_case: null
selected_connector_or_destination_family: null
selected_dispatch_mode: null
credential_access_model_selected: false
lifecycle_contract_selected: false
receipt_audit_contract_selected: false
fake_connector_destination_test_architecture_selected: false
implementation_entry_allowed_next: false
next_required_boundary: named_connector_or_destination_target_before_runtime
external_connector_destination_runtime_status: blocked
```

## Purpose

Doc `254_CONNECTOR_DESTINATION_REENTRY_DECISION_FREEZE.md` requires a single named connector or destination freeze before external connector/destination runtime. This packet answers that gate from current repo evidence.

The result is no runtime now. Current main proves a bounded internal dispatch record, not an external connector invocation, destination write, connector-run lifecycle, retry/cancel system, credential model, or rendered connector/destination control.

## Repo-confirmed connector truth

Current connector/destination authority remains:

- `backend/app/services/layer3_connector_dispatch_entry.py` owns `internal_dispatch_record_only`.
- The live endpoint is `/api/v1/layer3/handoff/connector/record`.
- The live state is `connector_dispatch_recorded`.
- The live delivery mode is `same_origin_artifact_stream`.
- `external_connector_invocation_enabled` is false.
- `destination_write_enabled` is false.
- `connector_run_created` is false.
- `provider_public_url_enabled` is false.
- `package_mutation_enabled` is false.
- `source_widening_enabled` is false.
- `qualitative_hybrid_rag_execution_enabled` is false.
- The owner service rejects connector keys, connector run ids, connector secrets, destination ids, destination secrets, destination URLs, provider/public/signed/download URLs, buckets, object keys, local paths, package payloads, source upload fields, local directory fields, RAG/vector fields, retry/rerun/cancel fields, hybrid/RAG execution fields, and hidden LLM planning fields.

This evidence proves the bounded internal control-plane receipt path. It does not prove readiness for external connector/destination runtime.

## Named-target gate result

```yaml
named_connector_destination_gate:
  named_downstream_use_case:
    status: not_found_in_current_authority
    consequence: runtime_blocked
  selected_connector_or_destination_family:
    status: not_selected
    consequence: runtime_blocked
  selected_dispatch_mode:
    status: null
    consequence: runtime_blocked
  artifact_family:
    status: current_aps_evidence_bundle_authority_only
    consequence: insufficient_for_external_target_without_named_destination
  credential_access_model:
    status: not_selected
    consequence: runtime_blocked
  lifecycle_retry_cancel_timeout_contract:
    status: not_selected
    consequence: runtime_blocked
  receipt_audit_contract:
    status: not_selected
    consequence: runtime_blocked
  fake_connector_destination_test_architecture:
    status: not_selected
    consequence: runtime_blocked
  rendered_control_plan:
    status: not_selected
    consequence: rendered_connector_destination_controls_blocked
  auth_security_posture:
    status: not_selected_for_external_dispatch
    consequence: runtime_blocked
```

## Why no external connector/destination runtime is selected

External dispatch cannot be selected safely without a real target model. Current authority does not answer:

- which downstream operator/product need requires external dispatch rather than same-origin delivery, signed references, APS handoff artifacts, or internal dispatch records;
- whether the first target should be a connector invocation or a destination write;
- which connector key or destination id is server-allowlisted;
- where credentials live and how missing credentials fail closed;
- which artifact family is sent or written;
- what lifecycle states, retry, cancel, timeout, duplicate, and idempotency behavior apply;
- which receipt and audit fields are response-safe;
- how logs, traces, screenshots, error bodies, and manifests avoid leaking secrets, local paths, object keys, URLs, package bytes, or destination internals;
- whether rendered controls are needed and how headed/headless/theme proof would be run.

Selecting any external target without these facts would couple Layer 3 to an inferred destination and create fragile, unsafe authority boundaries.

## Required future connector/destination packet contents

A future connector/destination runtime entry may proceed only after a packet names:

- one concrete downstream use case;
- why internal record-only, same-origin delivery, same-origin signed reference, and APS handoff artifacts are insufficient;
- one selected mode: `single_named_connector_dispatch`, `single_named_destination_dispatch`, or a bounded `internal_dispatch_record_only_extension`;
- one connector family or destination family;
- server-side allowlist/config authority;
- credential/access model and fail-closed behavior;
- artifact family, artifact hash/size binding, and stale-authority behavior;
- lifecycle states, terminal states, retry, cancel, timeout, duplicate, and idempotency behavior;
- receipt/audit contract and leak-control policy;
- fake connector/destination test architecture by default;
- rendered-control and headed/headless/theme proof obligations if UI changes are required;
- auth/security escalation rule if identity, permission, credential, or nonlocal exposure risk is introduced.

## Non-admission

This packet admits no runtime behavior, external connector invocation, destination write, connector-run creation, generic downstream dispatch, provider/public URL runtime, provider object write/copy/ACL behavior, route/API/DTO/model/migration/service behavior, executable test behavior, rendered UI behavior, rendered connector/destination controls, package mutation/reconstruction, package payload rewrite, source expansion, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, broad qualitative/hybrid/RAG execution, full mockup activation, auth/security behavior, hidden LLM planning, CI workflow change, Playwright configuration change, or frontend-only durable authority.

## Stop condition

Stop before implementation if the next connector/destination proposal cannot name one downstream use case, one connector or destination target, one selected mode, credential/access authority, lifecycle semantics, receipt/audit contract, fake-target tests, leak controls, and auth/security posture from explicit evidence rather than inference.
