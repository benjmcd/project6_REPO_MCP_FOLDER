# 591 - Layer 3 Connector Local Destination Receipt Delivery-Authority Readiness/Artifact Review Remediation

## Status

Status: review-remediation implementation for `remediate_layer3_connector_local_destination_receipt_delivery_authority_readiness_artifact_review_threads`.

Doc: `591_LAYER3_CONNECTOR_LOCAL_DESTINATION_RECEIPT_DELIVERY_AUTHORITY_READINESS_ARTIFACT_REVIEW_REMEDIATION.md`.

Current-main preflight commit: `17344bb9166bc82f2bb62f6ab934af75b41a659f`.

Branch: `codex/l3-local-receipt-delivery-authority-readiness-artifact-remediation`.

Source review threads:

- PR `#1185`, `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1185#discussion_r3249255284`.
- PR `#1185`, `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1185#discussion_r3249255289`.

## Review Assessment

Both findings are valid against the PR `#1185` validator remediation.

The side-effect-free validator preserved delivery request/readiness field comparisons but did not preserve the full same-origin delivery checks that validate the persisted APS bundle artifact hash, size, and bundle id.

The validator also accepted the stored reconciliation readiness snapshot without recomputing external export/download readiness against the current package, handoff, APS dispatch, and result authority rows.

## Remediation

The changed service remains `backend/app/services/layer3_connector_local_destination_receipt.py`.

The validator still avoids a second `Session` and still avoids calling `layer3_workbench.external_export_download_deliver`.

It now reruns `layer3_workbench.external_export_download_prepare` in the existing receipt transaction with `_external_export_download_prepare_payload_for_delivery(..., readiness_state=readiness_state)` and `validate_source_artifact=False`. In the valid recorded-readiness path this returns `already_prepared` before commit, while stale readiness fails before receipt persistence.

It then calls `_external_export_download_delivery_response` to preserve persisted APS bundle artifact validation for source artifact hash, artifact size, and APS bundle id before writing `L3ConnectorLocalDestinationReceipt`.

## Validation

Focused validation passed:

- `python -m py_compile .\backend\app\services\layer3_connector_local_destination_receipt.py`;
- `python -m pytest .\backend\tests\test_layer3_api.py -k "connector_local_destination_receipt"` with `3 passed, 149 deselected`.

## Non-Admission Boundary

This remediation changes only the local receipt delivery-authority validation implementation inside the already-admitted internal fake/local destination receipt slice.

It admits no real connector target, real destination target, external connector invocation, destination write, connector-run creation, credential use, network write, real destination integration, generic downstream dispatch, provider-public delivery/use, rendered connector/destination controls, schema/model/migration changes, package mutation/reconstruction, source expansion, RAG/vector behavior, broad qualitative behavior, auth/security behavior, full mockup activation, or frontend-only durable authority.

## Next Posture

After this remediation merges, the required next action is `current_main_sync_layer3_connector_local_destination_receipt_delivery_authority_readiness_artifact_review_remediation_merge`.

After that sync, the next whole-project posture remains `await_real_connector_or_destination_target_authority_after_internal_fake_local_receipt_sync`.
