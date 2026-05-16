# 596 - Local Receipt Plan

## Status

Status: planning/control sequence for `plan_connector_local_receipt_outward_sequence_after_sync_hash_remediation`.

Doc: `596_LOCAL_RECEIPT_PLAN.md`.

Current-main checkpoint: `3922446a52fc9af901f32a3cc4ef7bd86818ba33`.

Prior sync doc: `595_LAYER3_CONNECTOR_DESTINATION_SYNC_HASH_REMEDIATION_CURRENT_MAIN_SYNC.md`.

Branch: `codex/l3-local-receipt-plan`.

## Canonical Authority

Current main contains the server-owned internal fake/local connector destination receipt runtime:

- route: `POST /api/v1/layer3/handoff/connector/local-destination/receipt`;
- service: `backend/app/services/layer3_connector_local_destination_receipt.py`;
- state/table: `L3ConnectorLocalDestinationReceipt` / `l3_connector_local_destination_receipt`;
- admitted target: `layer3_internal_fake_local_destination_receipt`;
- admitted mode: `internal_fake_local_destination_receipt_only`;
- admitted operator decision: `record_internal_fake_local_destination_receipt`;
- redacted artifact ref: `artifact://layer3-internal-fake-local-destination-redacted`; and
- proof boundary: no external connector invocation, no destination write, no connector-run creation, no credential use, and no network write.

Current main also contains the missing-decision packet for real connector/destination target authority. That packet remains valid and should not be regenerated unless current-main authority changes or a product/user authority names a real connector or destination target.

## Preferred Sequence

The next outward build should use the merged local receipt runtime before reopening real connector dispatch:

1. `conduct_connector_local_receipt_status_surface_authority_audit`.
2. If current-main authority is sufficient, `implement_connector_local_receipt_read_only_status_surface`.
3. `connector_local_receipt_from_handoff_export_readiness_e2e_smoke_path`.
4. `confirm_or_refresh_connector_destination_missing_decision_packet_for_real_target`.
5. `harden_connector_local_receipt_lifecycle`.
6. `write_real_connector_destination_implementation_entry_freeze_after_target_named`.
7. `defer_provider_public_delivery_use_until_exposure_security_decision`.
8. `defer_package_mutation_reconstruction_until_named_operator_action`.
9. `defer_source_expansion_until_one_named_source_family`.
10. `defer_rag_vector_until_source_index_authority_defined`.
11. `tie_auth_security_hardening_to_the_first_real_external_surface`.

## Immediate Milestone

Immediate milestone: `conduct_connector_local_receipt_status_surface_authority_audit`.

Exact product/use-case behavior: `operator_reviews_connector_local_destination_receipt_status_without_real_connector_invocation_or_destination_write`.

Preferred implementation shape for the later implementation pass: a read-only operator-visible status/review surface over the existing local receipt runtime and existing handoff/export readiness chain.

Allowed planning targets for the next pass:

- prove whether the existing route response, reconciliation summary state, and session summary state already expose enough status data;
- if response authority is sufficient, admit only read-only rendered UI and tests;
- if response authority is insufficient, stop at `connector_local_receipt_status_response_authority_freeze` rather than inventing durable frontend authority; and
- keep the focused E2E smoke path limited to already admitted handoff/export readiness, connector record, external export/download readiness, and local receipt recording.

## Anti-Cycle Rule

Each pass must start with one live authority check, then execute exactly the next named step. Do not create another broad no-runtime audit if the existing missing-decision packet remains current and no real target authority has been named. Prefer implementation-facing preparation for the read-only local receipt status surface and E2E smoke path.

This doc is the selection/control artifact for the local receipt status surface. Do not create a separate broad selection freeze before the status-surface authority audit.

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

## Next Posture

Next whole-project posture: `await_connector_local_receipt_read_only_status_surface_authority_audit`.
