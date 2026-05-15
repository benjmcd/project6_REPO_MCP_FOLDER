# 585 - Layer 3 Connector Local Destination Receipt Delivery-Authority Review Remediation

## Status

Status: review-remediation implementation for `remediate_layer3_connector_local_destination_receipt_delivery_authority_review_thread`.

Doc: `585_LAYER3_CONNECTOR_LOCAL_DESTINATION_RECEIPT_DELIVERY_AUTHORITY_REVIEW_REMEDIATION.md`.

Current-main preflight commit: `9f197c4ce4ffda0def8ff58f8d3925204d941e14`.

Source review thread: PR `#1177`, `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1177#discussion_r3248772902`.

Branch: `codex/l3-local-receipt-delivery-authority-remediation`.

## Review Finding

The unresolved PR `#1177` review thread identified that the local destination receipt endpoint could record a durable fake/local receipt after `/handoff/connector/record` while checking only `external_export_download_prepared`. That left the receipt write insufficiently tied to the existing same-origin external export/download delivery validator required by doc `580`.

The finding is valid against the freeze text. Doc `580` requires an existing same-origin external export/download prepare/delivery authority before writing a receipt.

## Remediation

`backend/app/services/layer3_connector_local_destination_receipt.py` now revalidates same-origin external export/download delivery authority before it writes `L3ConnectorLocalDestinationReceipt`.

The remediation:

- reads the recorded `external_export_download_prepare` authority from the reconciliation state;
- builds the existing delivery-validator payload from the connector dispatch record plus the recorded readiness state;
- calls `layer3_workbench.external_export_download_deliver` before receipt persistence;
- requires `X-Layer3-Delivery-State: external_export_download_delivered`; and
- fails closed before receipt insertion when the recorded readiness/descriptor/artifact authority is stale or mismatched.

## Proof

Focused validation passed:

- `python -m pytest .\backend\tests\test_layer3_api.py -k "connector_local_destination_receipt"` -> `3 passed, 149 deselected`.

New regression coverage:

- `test_layer3_api_connector_local_destination_receipt_revalidates_delivery_authority`

The regression mutates recorded external export/download descriptor authority after the connector dispatch record and proves the local destination receipt endpoint returns `409` with `external_export_download_delivery_source_artifact_mismatch` and writes no `L3ConnectorLocalDestinationReceipt`.

## Non-Admission Boundary

This remediation changes only the already-admitted internal fake/local destination receipt guard. It does not add a real connector target, real destination target, external connector invocation, destination write, connector-run creation, credential use, network write, real destination integration, generic downstream dispatch, provider-public delivery/use, rendered connector/destination controls, schema/model/migration changes, package mutation/reconstruction, source expansion, RAG/vector behavior, broad qualitative behavior, auth/security behavior, full mockup activation, or frontend-only durable authority.

## Next Posture

Required next action after merge: `current_main_sync_layer3_connector_local_destination_receipt_delivery_authority_review_remediation_merge`.

Next whole-project posture after sync remains `await_real_connector_or_destination_target_authority_after_internal_fake_local_receipt_sync`.
