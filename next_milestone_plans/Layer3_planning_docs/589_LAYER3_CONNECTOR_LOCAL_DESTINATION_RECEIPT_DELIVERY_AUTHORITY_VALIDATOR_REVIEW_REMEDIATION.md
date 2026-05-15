# 589 - Layer 3 Connector Local Destination Receipt Delivery-Authority Validator Review Remediation

## Status

Status: review-remediation implementation for `remediate_layer3_connector_local_destination_receipt_delivery_authority_validator_review_thread`.

Doc: `589_LAYER3_CONNECTOR_LOCAL_DESTINATION_RECEIPT_DELIVERY_AUTHORITY_VALIDATOR_REVIEW_REMEDIATION.md`.

Current-main preflight commit: `570c9fd0019e8e94bde65485ae03dbe8cb4dee94`.

Branch: `codex/l3-local-receipt-delivery-authority-validator-remediation`.

Source review thread: PR `#1183`, `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1183#discussion_r3249158973`.

## Review Assessment

The finding is valid against the PR `#1183` follow-up remediation.

The previous fix isolated `layer3_workbench.external_export_download_deliver` in `validation_db = Session(bind=db.get_bind())` to avoid rolling back the receipt write transaction. On databases that honor `SELECT ... FOR UPDATE`, that separate session can attempt to lock the same reconciliation row already locked by the outer receipt transaction, while the outer transaction waits synchronously for validation to return. SQLite-based tests do not expose this lock cycle.

## Remediation

The changed service remains `backend/app/services/layer3_connector_local_destination_receipt.py`.

`_validate_existing_delivery_authority` no longer creates a second `Session` and no longer calls `layer3_workbench.external_export_download_deliver`.

The validator now checks the delivery authority side-effect-free against the locked reconciliation readiness state already loaded by `record_internal_fake_local_destination_receipt`. It uses the existing workbench contract helpers `external_export_download_delivery_request_fields`, `external_export_download_delivery_blocked_fields`, and `external_export_download_delivery_readiness_mismatches`, then validates descriptor identity and source artifact identity without a second transaction, no extra `with_for_update`, and no rollback.

The replay ordering from doc `587` remains intact: same-client idempotent replay and same-basis conflict checks happen before stale delivery-authority revalidation.

## Validation

Focused validation passed:

- `python -m py_compile .\backend\app\services\layer3_connector_local_destination_receipt.py`;
- `python -m pytest .\backend\tests\test_layer3_api.py -k "connector_local_destination_receipt"` with `3 passed, 149 deselected`.

## Non-Admission Boundary

This remediation changes only the local receipt delivery-authority validation implementation inside the already-admitted internal fake/local destination receipt slice.

It admits no real connector target, real destination target, external connector invocation, destination write, connector-run creation, credential use, network write, real destination integration, generic downstream dispatch, provider-public delivery/use, rendered connector/destination controls, schema/model/migration changes, package mutation/reconstruction, source expansion, RAG/vector behavior, broad qualitative behavior, auth/security behavior, full mockup activation, or frontend-only durable authority.

## Next Posture

After this remediation merges, the required next action is `current_main_sync_layer3_connector_local_destination_receipt_delivery_authority_validator_review_remediation_merge`.

After that sync, the next whole-project posture remains `await_real_connector_or_destination_target_authority_after_internal_fake_local_receipt_sync`.
