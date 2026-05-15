# 569 - Layer 3 Provider-Public Authority Audit After Source Intake Provider-Private Authority Sync

## Status

Status: branch-local planning/control audit for `conduct_layer3_provider_public_delivery_use_no_runtime_boundary_authority_audit_after_source_intake_provider_private_signed_reference_audit_after_end_to_end_governance_lifecycle_behavior_audit_after_connector_destination_audit_after_handoff_export_audit_after_package_lifecycle_audit_after_provider_public_audit_after_source_intake_provider_private_e2e_connector_requirement_selection_sync`.

Doc: `569_LAYER3_PROVIDER_PUBLIC_AUTHORITY_AUDIT_AFTER_SOURCE_INTAKE_PROVIDER_PRIVATE_AUTHORITY_SYNC.md`.

Current-main preflight commit: `8f9bc3b60510e0fab432f368cd2949c01df09756`.

This audit follows current-main sync doc `568_LAYER3_PROVIDER_PUBLIC_BEHAVIOR_FREEZE_AFTER_SOURCE_INTAKE_PROVIDER_PRIVATE_AUTHORITY_CURRENT_MAIN_SYNC.md`.

## Audited Behavior

Exact named product/use-case behavior: `operator_reviews_layer3_provider_public_delivery_use_no_runtime_boundary_after_source_intake_provider_private_signed_reference_audit_after_end_to_end_governance_lifecycle_behavior_audit_after_connector_destination_audit_after_handoff_export_audit_after_package_lifecycle_audit_after_provider_public_audit_after_source_intake_provider_private_e2e_connector_requirement_selection_without_raw_public_url_exposure_or_dispatch`.

Audit result: `layer3_provider_public_delivery_use_no_runtime_boundary_authority_current_main_satisfied_no_runtime_after_source_intake_provider_private_signed_reference_audit_after_end_to_end_governance_lifecycle_behavior_audit_after_connector_destination_audit_after_handoff_export_audit_after_package_lifecycle_audit_after_provider_public_audit_source_intake_provider_private_e2e_connector_requirement`.

Entry decision: `read_only_current_main_control_surface_only`.

Runtime status: `not_implemented`.

Selected implementation action: `none`.

## Current-Main Evidence

Current main already contains the selected provider-public delivery/use no-runtime boundary as repo-owned server authority and rendered control state:

- `backend/app/services/layer3_provider_public_url.py` restricts prepare to `client_request_id`, `provider_private_signed_url_receipt_id`, `recipient_scope`, `requested_ttl_seconds`, `delivery_mode`, `operator_decision`, and notes fields; rejects raw provider/public URL, public proxy, signed/download/provider URL, provider credentials/object controls, connector dispatch, and destination write fields; requires prepared non-expired provider-private signed URL receipt authority; records durable provider-public URL receipt/audit state; returns `provider_public_url_redacted`, `raw_public_url_exposed: False`, `public_url_enabled: False`, `provider_network_enabled: False`, `provider_object_write_enabled: False`, `connector_dispatch_enabled: False`, and `destination_write_enabled: False`.
- `backend/app/api/layer3.py` exposes bounded provider-public prepare/status/revoke routes and response models with redacted provider-public URL fields, explicit `raw_public_url_exposed` and `public_url_enabled` booleans, and no provider-public use/deliver route.
- `backend/app/review_ui/static/layer3.js` gates provider-public prepare on an existing provider-private signed URL receipt, sends only `provider_private_signed_url_receipt_id` plus bounded metadata, renders redacted receipt-only state, and keeps provider-public delivery/use and raw URL exposure closed.
- `backend/tests/test_layer3_provider_public_url_state.py` proves durable provider-public state is redacted, idempotent, TTL-bounded, revocable, and never exposes a raw public URL through the fake provider.
- `backend/tests/test_layer3_api.py::test_layer3_api_provider_public_url_openapi_prepare_status_schema`, `test_layer3_api_provider_public_url_prepare_status_idempotent_and_fail_closed`, and `test_layer3_api_provider_public_url_revoke_success_idempotency_and_fail_closed` prove bounded OpenAPI/API contracts, prepare/status/revoke idempotency, fail-closed forbidden-field handling, redaction, and no raw public URL leak.
- `backend/tests/test_layer3_page.py::test_layer3_page_route_serves_workbench_shell` proves rendered provider-public controls and copy preserve the closed provider-public delivery/use and raw URL exposure boundary.

## Validation

- `python -m pytest .\backend\tests\test_layer3_provider_public_url_state.py -q`: `PASS` (`6 passed`).
- `python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_provider_public_url_openapi_prepare_status_schema .\backend\tests\test_layer3_api.py::test_layer3_api_provider_public_url_prepare_status_idempotent_and_fail_closed .\backend\tests\test_layer3_api.py::test_layer3_api_provider_public_url_revoke_success_idempotency_and_fail_closed -q`: `PASS` (`3 passed, 3 warnings`).
- `python -m pytest .\backend\tests\test_layer3_page.py::test_layer3_page_route_serves_workbench_shell -q`: `PASS` (`1 passed, 3 warnings`).

## Audit Decision

No implementation is selected by this audit. The selected read-only provider-public delivery/use no-runtime boundary is already represented as current-main control and server-authoritative runtime surface without admitting raw public URL display/use, provider-public delivery/use, public proxy runtime, provider network/object-store writes, external connector invocation, destination writes, connector-run creation, package mutation, source expansion, RAG/vector behavior, auth/security behavior, or frontend-only durable authority.

No implementation begins in this audit.

The required next action after merge is `current_main_sync_layer3_provider_public_delivery_use_no_runtime_boundary_authority_audit_after_source_intake_provider_private_signed_reference_audit_after_end_to_end_governance_lifecycle_behavior_audit_after_connector_destination_audit_after_handoff_export_audit_after_package_lifecycle_audit_after_provider_public_audit_after_source_intake_provider_private_e2e_connector_requirement_selection_merge`.

After that sync, the next whole-project posture is `await_new_exact_named_layer3_product_use_case_requirement_after_provider_public_delivery_use_no_runtime_boundary_audit_after_source_intake_provider_private_signed_reference_audit_after_end_to_end_governance_lifecycle_behavior_audit_after_connector_destination_audit_after_handoff_export_audit_after_package_lifecycle_audit_after_provider_public_audit_after_source_intake_provider_private_e2e_connector_requirement_sync`.

## Non-Admission Boundary

No runtime behavior, backend route behavior, service runtime behavior, response-model shape change, schema/model/migration change, rendered UI implementation, external connector invocation, destination write, connector-run creation, generic downstream dispatch, rendered connector action control, provider-public delivery/use, raw public URL display/use, public proxy runtime, provider network/object-store write, package mutation, package reconstruction, package payload rewrite, replacement artifact generation, source expansion, RAG/vector behavior, full mockup activation, auth/security behavior change, or frontend-only durable authority is admitted by this audit.

No closed or blocked lane is reopened by implication.
