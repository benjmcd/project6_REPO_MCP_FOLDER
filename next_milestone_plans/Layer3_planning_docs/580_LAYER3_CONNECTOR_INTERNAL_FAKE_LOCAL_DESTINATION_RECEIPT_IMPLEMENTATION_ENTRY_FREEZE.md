# 580 - Layer 3 Connector Internal Fake Local Destination Receipt Implementation Entry Freeze

## Status

Status: implementation-entry freeze for `layer3_connector_internal_fake_local_destination_receipt_implementation_entry_freeze`.

Doc: `580_LAYER3_CONNECTOR_INTERNAL_FAKE_LOCAL_DESTINATION_RECEIPT_IMPLEMENTATION_ENTRY_FREEZE.md`.

Current-main checkpoint: `a9dfe56a22966e7e0bb845126b244ea552a2bc95`.

Prior terminal roadmap: `579_LAYER3_TERMINAL_NO_RUNTIME_ROADMAP_AFTER_CURRENT_SYNC_CHECKPOINT.md`.

Working-tree note: `.codesight/` remains untracked and is not part of this freeze.

## Objective Restatement

This pass converts the prior terminal no-runtime posture into one exact implementation-entry freeze because the current session supplies the missing product direction for the highest-priority candidate: connector/destination dispatch should advance first, and the first runtime slice should be internal/fake/local with durable receipt semantics before any real external connector, credential, network write, or destination integration.

This is an implementation-entry freeze only. It does not implement runtime behavior.

## Current Authority

Canonical current-main authority:

- `356_CONNECTOR_DESTINATION_NAMED_TARGET_REVALIDATION_PACKET.md`
- `357_CONNECTOR_DESTINATION_NAMED_TARGET_REVALIDATION_CURRENT_MAIN_SYNC.md`
- `551_LAYER3_CONNECTOR_DESTINATION_DISPATCH_BOUNDARY_AUTHORITY_AUDIT_AFTER_HANDOFF_EXPORT_AUDIT_PACKAGE_LIFECYCLE_SOURCE_INTAKE_PROVIDER_PRIVATE_E2E_CONNECTOR_REQUIREMENT_FREEZE_SYNC.md`
- `552_LAYER3_CONNECTOR_DESTINATION_DISPATCH_BOUNDARY_AUTHORITY_AUDIT_AFTER_HANDOFF_EXPORT_AUDIT_PACKAGE_LIFECYCLE_SOURCE_INTAKE_PROVIDER_PRIVATE_E2E_CONNECTOR_REQUIREMENT_CURRENT_MAIN_SYNC.md`
- `579_LAYER3_TERMINAL_NO_RUNTIME_ROADMAP_AFTER_CURRENT_SYNC_CHECKPOINT.md`
- `backend/app/services/layer3_connector_dispatch_entry.py`
- `backend/app/api/layer3.py`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_workbench.py`

Current main already admits `internal_dispatch_record_only` through `/api/v1/layer3/handoff/connector/record`. That service records a bounded connector dispatch control event against existing Layer 3 reconciliation authority and keeps external connector invocation, destination writes, connector-run creation, provider-public URL use, package mutation, source expansion, RAG/vector behavior, retry/rerun/cancel, and hidden LLM planning disabled.

The prior terminal roadmap found connector/destination runtime inadmissible because no downstream use case, destination target, dispatch mode, lifecycle contract, receipt/audit contract, fake-target test architecture, or auth/security posture had been named. The current session supplies a bounded answer for the first implementation-entry step.

## Selected Runtime Slice

Selected candidate: `connector_destination_dispatch`.

Selected exact runtime slice: `layer3_connector_internal_fake_local_destination_receipt`.

Selected target: `layer3_internal_fake_local_destination_receipt`.

Selected dispatch mode: `internal_fake_local_destination_receipt_only`.

Selected downstream use case: an operator records a server-owned durable local receipt proving that an already prepared same-origin external export/download artifact was accepted by an internal fake/local destination, without external connector invocation or destination write.

Entry decision: `implementation_entry_freeze_only`.

Runtime status: `not_implemented`.

Implementation action admitted next: `implement_layer3_connector_internal_fake_local_destination_receipt_runtime`.

Next whole-project posture after this freeze sync: `await_implementation_of_layer3_connector_internal_fake_local_destination_receipt_runtime`.

## Future Runtime Contract

The next implementation pass may implement only `implement_layer3_connector_internal_fake_local_destination_receipt_runtime`.

The runtime must:

- consume only existing Layer 3 authority such as `session_id`, `pass_run_id`, `reconciliation_record_id`, `connector_dispatch_record_ref`, and an existing external export/download record reference;
- require the existing `connector_dispatch_recorded` state from the `internal_dispatch_record_only` lane;
- require an existing same-origin external export/download prepare/delivery authority before writing a receipt;
- write one durable server-owned internal fake/local destination receipt;
- make the receipt idempotent by a client request id and an authority-basis hash;
- reject stale, missing, mismatched, duplicate-conflicting, or forbidden-field requests fail closed;
- expose response fields that prove receipt identity, basis, mode, state, and redacted accepted artifact reference without leaking provider/public/signed/download URLs, destination URLs, credentials, local paths, object-store keys, package payloads, or source bytes;
- use fake/local semantics only, with no network write, credential lookup, real connector call, real destination write, generic downstream dispatch, or connector-run creation; and
- preserve existing `internal_dispatch_record_only` behavior.

Expected implementation surfaces, if current-main audit confirms them in the implementation pass:

- owner service: `backend/app/services/layer3_connector_local_destination_receipt.py`;
- API route: `POST /api/v1/layer3/handoff/connector/local-destination/receipt`;
- durable state model/table: `L3ConnectorLocalDestinationReceipt` / `l3_connector_local_destination_receipt`;
- migration under `backend/alembic/versions/`;
- response/request contract in `backend/app/schemas/layer3.py`;
- focused tests in `backend/tests/test_layer3_connector_local_destination_receipt.py`; and
- API contract coverage near existing connector tests if the route is added.

These surfaces are admitted only for the next exact implementation pass. This freeze does not create them.

## Non-Admission Boundary

This freeze admits no runtime behavior change, backend route behavior change, service runtime behavior change, response-model shape change, schema/model/migration change, rendered UI implementation, external connector invocation, destination write, real connector run, connector-run creation, generic downstream dispatch, provider-public delivery/use, raw public URL display/use, public proxy runtime, provider network/object-store write, package mutation, package reconstruction, package payload rewrite, replacement artifact generation, source expansion, RAG/vector behavior, broad qualitative behavior, auth/security behavior change, full mockup activation, frontend-only durable authority, credential handling, network write, or real destination integration.

No closed or blocked lane is reopened by implication.
