# Connector Destination Named Target Revalidation Packet

## Status

Status: planning/control connector/destination named-target revalidation packet only; no runtime behavior admitted.

This packet follows current-main doc `355_NEXT_DEFERRED_SERVER_AUTHORITATIVE_RUNTIME_LANE_CURRENT_MAIN_SYNC.md`.

The selected packet is `connector_destination_named_target_revalidation_packet`.

## Decision

No connector/destination runtime is selected.

The revalidation result is `no_runtime_now_named_connector_or_destination_absent`.

The next required action is `current_main_sync_connector_destination_named_target_revalidation_packet_after_merge`.

## Repo-confirmed authority

Current repo authority still admits only `internal_dispatch_record_only`:

- Service owner: `backend/app/services/layer3_connector_dispatch_entry.py`
- Endpoint: `/api/v1/layer3/handoff/connector/record`
- Dispatch mode: `internal_dispatch_record_only`
- Delivery mode: `same_origin_artifact_stream`
- Operator decision: `record_internal_connector_dispatch`
- State: `connector_dispatch_recorded`
- External connector invocation: disabled
- Destination write: disabled
- Connector run creation: disabled
- Provider-public URL side effect: disabled
- Package mutation: disabled
- Source widening: disabled
- Qualitative/hybrid/RAG execution: disabled

The API schema and tests keep connector/destination target fields as known but non-admitted or forbidden request fields, including connector keys, connector run ids, connector secrets, destination ids, destination secrets, destination URLs, connector payloads, destination selectors, generic dispatch fields, provider/public URLs, package payload fields, local paths, local directory inputs, web connector fields, and RAG/vector fields.

## Gate result

```yaml
connector_destination_named_target_revalidation:
  selected_planning_mode: connector_destination_named_target_revalidation_packet
  entry_decision: no_runtime_now_named_connector_or_destination_absent
  current_connector_destination_runtime: internal_dispatch_record_only
  named_downstream_use_case: null
  selected_connector_or_destination_family: null
  selected_dispatch_mode: null
  server_allowlist_config_authority_selected: false
  credential_access_model_selected: false
  lifecycle_contract_selected: false
  receipt_audit_contract_selected: false
  fake_connector_destination_test_architecture_selected: false
  rendered_control_plan_selected: false
  auth_security_posture_selected: false
  external_connector_destination_runtime_status: blocked
```

## Why runtime remains blocked

Current main does not prove:

- one concrete downstream use case
- one connector or destination target
- one selected mode from `single_named_connector_dispatch`, `single_named_destination_dispatch`, or `internal_dispatch_record_only_extension`
- server-side allowlist/config authority
- credential/access authority
- lifecycle states for retry, cancel, timeout, duplicate, or idempotency
- receipt/audit fields for an external connector or destination
- fake connector/destination test architecture for external behavior
- rendered connector/destination control requirements
- auth/security posture for target credentials or destination access

Provider-public prepare/status/revoke and rendered controls do not create any connector target, destination target, credential model, connector-run lifecycle, destination write authority, or generic downstream dispatch authority.

## Explicit non-goals

No external connector invocation is admitted.

No destination write is admitted.

No connector-run creation is admitted.

No generic downstream dispatch is admitted.

No rendered connector/destination control is admitted.

No provider-public delivery/use is admitted.

No provider object write/copy/ACL behavior is admitted.

No package mutation or reconstruction is admitted.

No source expansion is admitted.

No RAG/vector behavior is admitted.

No broad qualitative behavior is admitted.

No full mockup activation is admitted.

No auth/security behavior is admitted.

No frontend-only durable authority is admitted.

## Future reopening condition

A later connector/destination runtime freeze may proceed only if it names:

- one downstream use case
- one connector or destination target
- one selected mode
- server allowlist/config authority
- credential/access authority
- lifecycle and stale-authority semantics
- receipt/audit contract
- fake-target test architecture
- leak controls
- rendered control proof, if UI is admitted
- auth/security posture

Until then, connector/destination remains at the existing internal-record-only boundary.
