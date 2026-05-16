# 598 - Local Receipt E2E Smoke

## Status

Status: branch-local focused E2E smoke path for `connector_local_receipt_from_handoff_export_readiness_e2e_smoke_path`.

Doc: `598_LOCAL_RECEIPT_E2E_SMOKE.md`.

Current-main checkpoint: `0ba2cc98132569e1d98049854f03959c62e23777`.

Prior status-surface doc: `597_LOCAL_RECEIPT_STATUS_SURFACE.md`.

Branch: `codex/l3-local-receipt-smoke`.

## Canonical Authority

The canonical runtime remains server-owned:

- connector dispatch record route: `POST /api/v1/layer3/handoff/connector/record`;
- local destination receipt route: `POST /api/v1/layer3/handoff/connector/local-destination/receipt`;
- read-only review authority: `State.sessionSummary.connector_local_destination_receipt`;
- rendered panel: `connector-local-destination-receipt-panel`;
- rendered mode: `rendered_connector_local_destination_receipt_read_only_status_surface`;
- admitted dispatch mode: `internal_dispatch_record_only`;
- admitted receipt mode: `internal_fake_local_destination_receipt_only`; and
- admitted receipt operator decision: `record_internal_fake_local_destination_receipt`.

The smoke path uses the existing handoff/export readiness chain and the existing connector-local receipt runtime. It does not create a new connector target, destination target, connector run, credential exchange, provider-public delivery mode, package mutation path, source family, RAG/vector index, auth/security surface, or frontend durable authority.

## Implemented Smoke Path

The focused E2E test is `e2e/layer3-workbench.spec.js`, in `Layer 3 workbench drives raw mixed rendered external export download delivery`, using the `recordRenderedConnectorLocalReceiptSmoke` helper after existing external export/download prepare authority and before same-origin delivery.

The smoke path proves:

- existing handoff/export readiness reaches `external_export_download_prepared`;
- the read-only review UI exposes `State.sessionSummary.connector_local_destination_receipt` through `connector-local-destination-receipt-panel`;
- the local receipt panel has no write controls;
- `/api/v1/layer3/handoff/connector/record` records only `internal_dispatch_record_only`;
- `/api/v1/layer3/handoff/connector/local-destination/receipt` records only `internal_fake_local_destination_receipt_only`;
- the refreshed summary and panel show `connector_local_destination_receipt_recorded`;
- the response authority is `durable_connector_local_destination_receipt_row`; and
- same-origin external export/download delivery still proceeds after the receipt smoke.

The request payload assertions explicitly reject connector keys, connector-run IDs, destination IDs/URLs, provider/public/signed/download URLs, package payloads, rewrites, uploads, local directories/paths, RAG/vector fields, credentials, network-write fields, external connector invocation fields, and destination-write fields.

## Validation

Required branch-local validation:

- `Get-Content .\e2e\layer3-workbench.spec.js | node --input-type=module --check`;
- `npx playwright test layer3-workbench.spec.js --grep "Layer 3 workbench drives raw mixed rendered external export download delivery" --project=chromium`;
- `npx playwright test layer3-workbench.spec.js --grep "Layer 3 workbench drives raw mixed rendered external export download delivery" --project=chromium --headed`;
- `python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_connector_local_destination_receipt_records_durable_fake_local_receipt`;
- JSON validation for `next_milestone_plans/layer3_progress_manifest.json` and `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `python -m py_compile .\tools\l3-progress-check.py`; and
- `python .\tools\l3-progress-check.py`.

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

## Future Step Ladder

Immediate next goal after this smoke: `confirm_or_refresh_connector_destination_missing_decision_packet_for_real_target`.

The missing-decision packet must name exactly one real connector or destination target, selected dispatch mode, credential/access model, lifecycle semantics, receipt/audit contract, leak controls, rendered-control obligations, and auth/security posture before any real connector/destination implementation-entry freeze can be written.

Mid-term goals:

- `harden_connector_local_receipt_lifecycle`;
- `write_real_connector_destination_implementation_entry_freeze_after_target_named`; and
- `implement_exact_real_connector_destination_runtime_only_after_target_named`.

Long-term gated goals:

- `provider_public_delivery_use_after_exposure_security_decision`;
- `package_mutation_reconstruction_after_named_operator_action`;
- `source_expansion_as_one_named_source_family`;
- `rag_vector_after_source_index_authority_defined`; and
- `auth_security_hardening_tied_to_admitted_external_surface`.

## Next Posture

Next whole-project posture: `await_connector_destination_missing_decision_packet_for_real_target_after_local_receipt_smoke`.
