# 597 - Local Receipt Status Surface

## Status

Status: implemented/read-only status surface for `implement_connector_local_receipt_read_only_status_surface`.

Doc: `597_LOCAL_RECEIPT_STATUS_SURFACE.md`.

Current-main checkpoint: `b6de6a8bd8210536d80a3c679fc1d04ac8f6a4b7`.

Prior control doc: `596_LOCAL_RECEIPT_PLAN.md`.

Branch: `codex/l3-local-receipt-status`.

## Canonical Authority

The canonical runtime remains server-owned:

- route: `POST /api/v1/layer3/handoff/connector/local-destination/receipt`;
- service: `backend/app/services/layer3_connector_local_destination_receipt.py`;
- state/table: `L3ConnectorLocalDestinationReceipt` / `l3_connector_local_destination_receipt`;
- admitted target: `layer3_internal_fake_local_destination_receipt`;
- admitted mode: `internal_fake_local_destination_receipt_only`;
- admitted operator decision: `record_internal_fake_local_destination_receipt`; and
- redacted artifact ref: `artifact://layer3-internal-fake-local-destination-redacted`.

This pass does not create frontend durable authority. The read-only status response authority is `State.sessionSummary.connector_local_destination_receipt`, populated by the server session summary from the durable receipt row, reconciliation summary state, or existing handoff/export readiness chain.

## Implemented Surface

The exact product/use-case behavior is `operator_reviews_connector_local_destination_receipt_status_without_real_connector_invocation_or_destination_write`.

Implemented changes:

- `backend/app/services/layer3_workbench.py` exposes `_connector_local_destination_receipt_summary` through `session_summary`;
- `backend/app/api/layer3.py` includes `connector_local_destination_receipt` in `Layer3SessionSummaryResponse`;
- `backend/app/review_ui/static/layer3.html` adds `connector-local-destination-receipt-panel`;
- `backend/app/review_ui/static/layer3.js` renders `renderConnectorLocalDestinationReceiptStatusPanel` from `State.sessionSummary.connector_local_destination_receipt`;
- `backend/tests/test_layer3_api.py` proves the OpenAPI/session-summary contract and durable local receipt projection; and
- `backend/tests/test_layer3_page.py` proves the static read-only panel wiring and that the review UI does not call `/handoff/connector/local-destination/receipt`.

The rendered status surface mode is `rendered_connector_local_destination_receipt_read_only_status_surface`. The server projection mode is `read_only_server_session_summary_projection`.

## Validation

Focused validation passed:

`python -m pytest .\backend\tests\test_layer3_page.py .\backend\tests\test_layer3_api.py::test_layer3_external_export_download_openapi_contracts .\backend\tests\test_layer3_api.py::test_layer3_api_connector_local_destination_receipt_records_durable_fake_local_receipt`

Result: `5 passed, 3 warnings`.

## Blocked Lanes

The following remain blocked unless a later exact named freeze separately admits them:

- real connector invocation;
- destination writes;
- connector-run creation;
- credentials or credential exchange;
- provider-public delivery/use;
- package mutation or reconstruction;
- source expansion;
- RAG/vector behavior;
- auth/security changes not tied to an admitted external surface;
- full mockup activation; and
- frontend-only durable authority.

## Goal Ladder

Immediate goal: `connector_local_receipt_from_handoff_export_readiness_e2e_smoke_path`.

Mid-term goals:

- `confirm_or_refresh_connector_destination_missing_decision_packet_for_real_target`;
- `harden_connector_local_receipt_lifecycle`; and
- `write_real_connector_destination_implementation_entry_freeze_after_target_named`.

Long-term gated goals:

- `provider_public_delivery_use_after_exposure_security_decision`;
- `package_mutation_reconstruction_after_named_operator_action`;
- `source_expansion_as_one_named_source_family`;
- `rag_vector_after_source_index_authority_defined`; and
- `auth_security_hardening_tied_to_admitted_external_surface`.

## Next Posture

Next whole-project posture: `await_connector_local_receipt_from_handoff_export_readiness_e2e_smoke_path`.
