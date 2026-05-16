# 602 - Local Receipt Lifecycle Hardening Freeze

## Status

Status: planning/control freeze for `freeze_layer3_local_receipt_lifecycle_hardening_after_real_target_missing_decision_sync`.

Doc: `602_LOCAL_RECEIPT_LIFECYCLE_HARDENING_FREEZE.md`.

Current-main checkpoint: `f2515593d7fcd911b2e9ae20dceb826969d54526`.

Prior sync doc: `601_REAL_TARGET_MISSING_DECISION_CURRENT_MAIN_SYNC.md`.

Branch: `codex/l3-local-receipt-lifecycle-plan`.

## Current Authority

Current main already contains the internal fake/local connector destination receipt runtime. The canonical live authority is:

- service: `backend/app/services/layer3_connector_local_destination_receipt.py`;
- API route: `POST /api/v1/layer3/handoff/connector/local-destination/receipt` in `backend/app/api/layer3.py`;
- durable row: `L3ConnectorLocalDestinationReceipt` in `backend/app/models/models.py`;
- session projection: `State.sessionSummary.connector_local_destination_receipt`;
- rendered status panel: `backend/app/review_ui/static/layer3.js`; and
- focused smoke proof: `recordRenderedConnectorLocalReceiptSmoke`.

Current main proves `connector_local_destination_receipt_recorded`, `durable_connector_local_destination_receipt_row`, same-`client_request_id` same-basis replay as `already_recorded`, same-basis new-request conflict as `connector_local_destination_receipt_already_recorded`, stale delivery authority rejection before first record, forbidden real connector/destination/provider/package/source/RAG fields, and read-only operator-visible status projection.

This freeze selects the next local receipt lifecycle-hardening lane because the real connector/destination target remains unnamed after doc `601`.

## Selected Lane

Selected exact milestone: `implement_layer3_local_receipt_lifecycle_hardening_after_real_target_missing_decision_sync`.

Selected runtime family: `connector_local_destination_receipt_runtime`.

Selected runtime mode: `internal_fake_local_destination_receipt_lifecycle_hardening`.

Entry decision: `implementation_entry_prepared`.

Runtime status before implementation: `partially_implemented_existing_local_receipt_runtime`.

Implementation-entry allowed next: true.

## Immediate Milestone

Implement the narrow local receipt lifecycle-hardening pass over the existing fake/local runtime:

1. Add a read-only receipt lifecycle/history/listing projection for the current session and reconciliation authority.
2. Project explicit status and failure states for unavailable, ready, recorded, stale-authority, wrong-session, wrong-artifact, wrong-basis, duplicate-client-request, replay, and same-basis conflict cases.
3. Keep retry semantics status-only: same `client_request_id` plus same authority basis returns the existing row, while same `client_request_id` plus different authority basis fails closed.
4. Preserve the existing single durable receipt row per client request and per authority basis unless the implementation pass separately proves that a lightweight read-only event projection can be derived without creating a new write model.
5. Prove the lifecycle through focused backend/API tests and a rendered headed/headless E2E path over `/review/layer3`.

## Mid-Term Milestones

After the immediate hardening pass lands and is current-main synced, proceed in this order:

1. Add focused guardrail coverage for wrong artifact/session/basis, duplicate `client_request_id`, same-key/same-payload replay, same-key/different-payload conflict, same-basis/new-key conflict, and stale delivery authority.
2. Harden operator-visible history copy so it names the durable authority row, redacted artifact reference, connector dispatch ref, external export/download ref, and disabled downstream lanes without creating write controls.
3. Add lifecycle proof metadata to the progress/proof manifests and keep `tools/l3-progress-check.py` guarding the exact admitted lane.
4. Reconcile the lifecycle surface after merge with a current-main sync doc before selecting any real connector/destination target.
5. Only after a concrete real target is named, write a separate real connector/destination implementation-entry freeze.

## Long-Term Milestones

The remaining whole-project path after local lifecycle hardening is:

1. Real connector/destination implementation-entry freeze after one concrete connector or destination target is named.
2. Provider-public delivery/use only after an exposure/security/public-access decision.
3. Package mutation/reconstruction only after a named operator package action.
4. Source expansion only as one named source family.
5. RAG/vector only after source/index authority is defined.
6. Auth/security hardening tied to whichever external or operator-facing surface becomes real.

## Required Future Proof

The implementation pass must prove:

- no `ConnectorRun` rows are created;
- no real external connector is invoked;
- no destination write, network write, provider-public delivery/use, credential use, package mutation, source expansion, RAG/vector behavior, full mockup activation, auth/security behavior change, or frontend-only durable authority is admitted;
- replay and conflict behavior remains fail-closed and operator-visible;
- listing/history surfaces are read-only projections from server authority; and
- headed and headless browser proof exercise the same lifecycle status/history path.

## Non-Admission Boundary

This freeze admits no real connector invocation, destination write, connector-run creation, credential handling, provider-public delivery/use, package mutation/reconstruction, source expansion, RAG/vector behavior, auth/security behavior change, full mockup activation, frontend-durable authority, backend route outside the local receipt lifecycle boundary, package/source/provider/connector model expansion, or broad no-runtime audit.

## Next Posture

The next whole-project posture is `await_layer3_local_receipt_lifecycle_hardening_implementation_after_freeze`.
