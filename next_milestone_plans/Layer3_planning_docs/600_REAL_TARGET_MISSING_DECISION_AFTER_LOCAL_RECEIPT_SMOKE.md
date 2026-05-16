# 600 - Real Target Missing Decision After Local Receipt Smoke

## Status

Status: missing-decision packet for `confirm_or_refresh_connector_destination_missing_decision_packet_for_real_target`.

Doc: `600_REAL_TARGET_MISSING_DECISION_AFTER_LOCAL_RECEIPT_SMOKE.md`.

Current-main checkpoint: `d73fe78c372f1237196ce7124e217f9366922e8c`.

Prior sync doc: `599_LOCAL_RECEIPT_E2E_SMOKE_CURRENT_MAIN_SYNC.md`.

Branch: `codex/l3-real-target-missing-decision`.

## Current Authority

Current main now includes the read-only operator-visible connector-local receipt status surface and the focused E2E smoke path from existing handoff/export readiness through `recordRenderedConnectorLocalReceiptSmoke`.

Current main proves only:

- internal connector dispatch record authority through `POST /api/v1/layer3/handoff/connector/record`;
- internal fake/local destination receipt authority through `POST /api/v1/layer3/handoff/connector/local-destination/receipt`;
- `connector_local_destination_receipt_recorded`;
- `durable_connector_local_destination_receipt_row`; and
- read-only operator status projection through `State.sessionSummary.connector_local_destination_receipt`.

Current main still does not name or admit a real connector target, real destination target, external connector invocation, destination write, connector-run creation, credential use, network write, real destination integration, generic downstream dispatch, provider-public delivery/use, rendered connector/destination controls, or frontend-only durable authority.

## Missing Decisions

No implementation-entry freeze can be written for real connector/destination runtime until a product/operator authority names all of the following:

- exactly one real connector or destination target;
- selected dispatch mode;
- credential/access model;
- lifecycle semantics, including retry, timeout, cancel, replay, and idempotency behavior;
- receipt/audit contract;
- fake-target or fake-connector test architecture;
- leak controls and response redaction requirements;
- rendered-control obligations, if any rendered controls are admitted; and
- auth/security posture tied to the admitted external surface.

## Decision Result

Decision result: `no_runtime_now_connector_destination_real_target_authority_absent_after_local_receipt_smoke_sync`.

Implementation-entry freeze written: false.

Runtime status: `not_implemented`.

Selected implementation action: `none`.

Required next action after merge: `current_main_sync_layer3_real_target_missing_decision_after_local_receipt_smoke_merge`.

## Non-Admission Boundary

This packet admits no runtime behavior, backend route behavior, service behavior, response-model shape change, schema/model/migration change, rendered UI implementation, executable test behavior, connector/provider/destination dispatch behavior, package mutation/reconstruction, source expansion, RAG/vector behavior, broad qualitative behavior, auth/security behavior change, full mockup activation, credential handling, network write, real destination integration, provider-public delivery/use, or frontend-only durable authority.

## Next Posture

The next whole-project posture is `await_local_receipt_lifecycle_hardening_after_real_target_missing_decision`.
