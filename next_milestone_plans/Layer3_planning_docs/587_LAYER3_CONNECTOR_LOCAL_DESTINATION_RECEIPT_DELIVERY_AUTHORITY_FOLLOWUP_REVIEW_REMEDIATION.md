# 587 - Layer 3 Connector Local Destination Receipt Delivery-Authority Follow-Up Review Remediation

## Status

Status: follow-up review-remediation implementation for `remediate_layer3_connector_local_destination_receipt_delivery_authority_followup_review_threads`.

Doc: `587_LAYER3_CONNECTOR_LOCAL_DESTINATION_RECEIPT_DELIVERY_AUTHORITY_FOLLOWUP_REVIEW_REMEDIATION.md`.

Current-main preflight commit: `8949e854ce78a68e0dea60c4b0ac097e4911ea3d`.

Branch: `codex/l3-local-receipt-delivery-authority-followup-remediation`.

Source review threads:

- PR `#1181`, `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1181#discussion_r3249031415`.
- PR `#1181`, `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1181#discussion_r3249031420`.

## Review Assessment

Both follow-up findings are valid against the PR `#1181` remediation intent.

The first finding notes that `layer3_workbench.external_export_download_deliver` can call `db.rollback()` before returning. Calling it on the local receipt transaction can therefore abort the transaction that protects the receipt idempotency checks and later summary JSON update.

The second finding notes that stale delivery authority was revalidated before the existing receipt checks. That made an idempotent replay capable of returning a stale-authority `409` even though no new `L3ConnectorLocalDestinationReceipt` would be written.

## Remediation

The changed service remains `backend/app/services/layer3_connector_local_destination_receipt.py`.

The delivery-authority validator now runs through an isolated SQLAlchemy session created with `validation_db = Session(bind=db.get_bind())`, so any rollback inside `layer3_workbench.external_export_download_deliver` is kept out of the local receipt write transaction.

The receipt flow now computes the authority basis and checks `existing_by_client` and `existing_by_basis` before calling `_validate_existing_delivery_authority`. Same-client idempotent replay returns `already_recorded` before stale delivery-authority revalidation, while same-basis duplicate requests still fail with `connector_local_destination_receipt_already_recorded` before any new receipt write.

The changed test remains `backend/tests/test_layer3_api.py`.

`test_layer3_api_connector_local_destination_receipt_records_durable_fake_local_receipt` now mutates the recorded external export/download descriptor to `artifact://stale-local-receipt-replay-authority` after the first successful receipt and proves that same-client replay still returns `already_recorded`.

## Validation

Focused validation passed:

- `python -m py_compile .\backend\app\services\layer3_connector_local_destination_receipt.py`;
- `python -m pytest .\backend\tests\test_layer3_api.py -k "connector_local_destination_receipt"` with `3 passed, 149 deselected`.

## Non-Admission Boundary

This follow-up remediation changes only the local receipt delivery-authority guard and idempotent replay ordering inside the already-admitted internal fake/local destination receipt slice.

It admits no real connector target, real destination target, external connector invocation, destination write, connector-run creation, credential use, network write, real destination integration, generic downstream dispatch, provider-public delivery/use, rendered connector/destination controls, schema/model/migration changes, package mutation/reconstruction, source expansion, RAG/vector behavior, broad qualitative behavior, auth/security behavior, full mockup activation, or frontend-only durable authority.

## Next Posture

After this follow-up remediation merges, the required next action is `current_main_sync_layer3_connector_local_destination_receipt_delivery_authority_followup_review_remediation_merge`.

After that sync, the next whole-project posture remains `await_real_connector_or_destination_target_authority_after_internal_fake_local_receipt_sync`.
