from __future__ import annotations

from typing import Any

from fastapi import Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.layer3_workbench_error import Layer3WorkbenchError, workbench_error_response
from app.services import (
    layer3_connector_dispatch_entry,
    layer3_connector_local_destination_receipt,
    layer3_external_local_export,
    layer3_internal_webhook_connector,
    layer3_local_outbox_provider_private_handoff,
    layer3_provider_private_signed_url,
    layer3_provider_public_url,
    layer3_provider_public_url_delivery_use,
    layer3_server_owned_local_outbox_target,
    layer3_server_owned_local_outbox_write,
    layer3_workbench,
)
from app.api.layer3 import router  # the shared APIRouter instance
from app.api.layer3._shared import *  # noqa: F401,F403
from app.api.layer3 import (  # Pydantic models still defined in __init__
    Layer3ApsHandoffDispatchRequest,
    Layer3ApsHandoffDispatchResponse,
    Layer3ConnectorDatasetHandoffRequest,
    Layer3ConnectorDatasetHandoffResponse,
    Layer3ConnectorDispatchRecordRequest,
    Layer3ConnectorDispatchRecordResponse,
    Layer3ConnectorLocalDestinationReceiptRequest,
    Layer3ConnectorLocalDestinationReceiptResponse,
    Layer3ExternalExportDownloadPrepareRequest,
    Layer3ExternalExportDownloadPrepareResponse,
    Layer3ExternalExportDownloadSignedReferenceResponse,
    Layer3ExternalLocalExportResponse,
    Layer3ExternalLocalExportWriteRequest,
    Layer3HandoffExportPrepareRequest,
    Layer3HandoffExportPrepareResponse,
    Layer3InternalWebhookDispatchRequest,
    Layer3InternalWebhookDispatchResponse,
    Layer3LocalOutboxProviderPrivateHandoffPrepareRequest,
    Layer3LocalOutboxProviderPrivateHandoffResponse,
    Layer3MixedSourceExternalExportDownloadReadinessRequest,
    Layer3MixedSourceExternalExportDownloadReadinessResponse,
    Layer3ProviderPrivateSignedUrlPrepareRequest,
    Layer3ProviderPrivateSignedUrlPrepareResponse,
    Layer3ProviderPrivateSignedUrlRevokeRequest,
    Layer3ProviderPrivateSignedUrlRevokeResponse,
    Layer3ProviderPrivateSignedUrlStatusResponse,
    Layer3ProviderPublicUrlDeliveryUseRequest,
    Layer3ProviderPublicUrlDeliveryUseResponse,
    Layer3ProviderPublicUrlPrepareRequest,
    Layer3ProviderPublicUrlPrepareResponse,
    Layer3ProviderPublicUrlRevokeRequest,
    Layer3ProviderPublicUrlRevokeResponse,
    Layer3ProviderPublicUrlStatusResponse,
    Layer3ServerOwnedLocalOutboxFakeTargetRequest,
    Layer3ServerOwnedLocalOutboxFakeTargetResponse,
    Layer3ServerOwnedLocalOutboxWriteRequest,
    Layer3ServerOwnedLocalOutboxWriteResponse,
    Layer3WorkbenchErrorResponse,
    _workbench_error_responses,
)


@router.post(
    "/handoff/export/prepare",
    response_model=Layer3HandoffExportPrepareResponse,
    response_model_exclude_unset=True,
    openapi_extra={"requestBody": _json_request_body(HANDOFF_EXPORT_PREPARE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_handoff_export_prepare(
    request: Request,
    payload: Layer3HandoffExportPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.handoff_export_prepare(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/handoff/aps/dispatch",
    response_model=Layer3ApsHandoffDispatchResponse,
    openapi_extra={"requestBody": _json_request_body(APS_HANDOFF_DISPATCH_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_aps_handoff_dispatch(
    request: Request,
    payload: Layer3ApsHandoffDispatchRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.aps_handoff_dispatch(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/handoff/export/download/readiness",
    response_model=Layer3MixedSourceExternalExportDownloadReadinessResponse,
    openapi_extra={"requestBody": _json_request_body(MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_READINESS_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_mixed_source_external_export_download_readiness(
    request: Request,
    payload: Layer3MixedSourceExternalExportDownloadReadinessRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_workbench.mixed_source_external_export_download_readiness(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/export/download/prepare",
    response_model=Layer3ExternalExportDownloadPrepareResponse,
    openapi_extra={"requestBody": _json_request_body(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_external_export_download_prepare(
    request: Request,
    payload: Layer3ExternalExportDownloadPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_workbench.external_export_download_prepare(db, payload.model_dump(exclude_unset=True))
    )


@router.post(
    "/handoff/connector/dataset",
    response_model=Layer3ConnectorDatasetHandoffResponse,
    response_model_exclude_unset=True,
    openapi_extra={"requestBody": _json_request_body(CONNECTOR_DATASET_HANDOFF_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_connector_dataset_handoff(
    request: Request,
    payload: Layer3ConnectorDatasetHandoffRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_workbench.connector_dataset_handoff(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/connector/record",
    response_model=Layer3ConnectorDispatchRecordResponse,
    openapi_extra={"requestBody": _json_request_body(CONNECTOR_DISPATCH_RECORD_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_connector_dispatch_record(
    request: Request,
    payload: Layer3ConnectorDispatchRecordRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_connector_dispatch_entry.record_internal_connector_dispatch(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/connector/local-destination/receipt",
    response_model=Layer3ConnectorLocalDestinationReceiptResponse,
    openapi_extra={"requestBody": _json_request_body(CONNECTOR_LOCAL_DESTINATION_RECEIPT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_connector_local_destination_receipt(
    request: Request,
    payload: Layer3ConnectorLocalDestinationReceiptRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_connector_local_destination_receipt.record_internal_fake_local_destination_receipt(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/connector/local-outbox/fake-target",
    response_model=Layer3ServerOwnedLocalOutboxFakeTargetResponse,
    openapi_extra={"requestBody": _json_request_body(SERVER_OWNED_LOCAL_OUTBOX_FAKE_TARGET_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_server_owned_local_outbox_fake_target(
    request: Request,
    payload: Layer3ServerOwnedLocalOutboxFakeTargetRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_server_owned_local_outbox_target.record_server_owned_local_outbox_fake_target(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/connector/local-outbox/write",
    response_model=Layer3ServerOwnedLocalOutboxWriteResponse,
    openapi_extra={"requestBody": _json_request_body(SERVER_OWNED_LOCAL_OUTBOX_WRITE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_server_owned_local_outbox_write(
    request: Request,
    payload: Layer3ServerOwnedLocalOutboxWriteRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_server_owned_local_outbox_write.write_server_owned_local_outbox(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/connector/local-outbox/provider-private/prepare",
    response_model=Layer3LocalOutboxProviderPrivateHandoffResponse,
    openapi_extra={"requestBody": _json_request_body(LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_PREPARE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_local_outbox_provider_private_handoff_prepare(
    request: Request,
    payload: Layer3LocalOutboxProviderPrivateHandoffPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_local_outbox_provider_private_handoff.prepare_local_outbox_provider_private_handoff(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.get(
    "/handoff/connector/local-outbox/provider-private/status/{provider_private_handoff_receipt_id}",
    response_model=Layer3LocalOutboxProviderPrivateHandoffResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_local_outbox_provider_private_handoff_status(
    provider_private_handoff_receipt_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_local_outbox_provider_private_handoff.local_outbox_provider_private_handoff_status(
            db,
            provider_private_handoff_receipt_id,
        )
    )


@router.post(
    "/handoff/connector/local-outbox/external-local-export/write",
    response_model=Layer3ExternalLocalExportResponse,
    openapi_extra={"requestBody": _json_request_body(EXTERNAL_LOCAL_EXPORT_WRITE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_external_local_export_write(
    request: Request,
    payload: Layer3ExternalLocalExportWriteRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_external_local_export.write_external_local_export(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.get(
    "/handoff/connector/local-outbox/external-local-export/status/{external_local_export_receipt_id}",
    response_model=Layer3ExternalLocalExportResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_external_local_export_status(
    external_local_export_receipt_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_external_local_export.external_local_export_status(
            db,
            external_local_export_receipt_id,
        )
    )


@router.post(
    "/handoff/export/internal-webhook/dispatch",
    response_model=Layer3InternalWebhookDispatchResponse,
    openapi_extra={"requestBody": _json_request_body(INTERNAL_WEBHOOK_DISPATCH_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_internal_webhook_dispatch(
    request: Request,
    payload: Layer3InternalWebhookDispatchRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_internal_webhook_connector.dispatch_internal_webhook(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.get(
    "/handoff/export/internal-webhook/status/{internal_webhook_dispatch_receipt_id}",
    response_model=Layer3InternalWebhookDispatchResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_internal_webhook_dispatch_status(
    internal_webhook_dispatch_receipt_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_internal_webhook_connector.internal_webhook_status(
            db,
            internal_webhook_dispatch_receipt_id,
        )
    )


@router.post(
    "/handoff/export/download/signed-reference/generate",
    response_model=Layer3ExternalExportDownloadSignedReferenceResponse,
    openapi_extra={"requestBody": _json_request_body(EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_GENERATE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_external_export_download_signed_reference_generate(
    request: Request,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.external_export_download_generate_signed_reference(db, payload))


@router.post(
    "/handoff/export/download/provider-private-signed-url/prepare",
    response_model=Layer3ProviderPrivateSignedUrlPrepareResponse,
    openapi_extra={"requestBody": _json_request_body(PROVIDER_PRIVATE_SIGNED_URL_PREPARE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_provider_private_signed_url_prepare(
    request: Request,
    payload: Layer3ProviderPrivateSignedUrlPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_provider_private_signed_url.provider_private_signed_url_prepare(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.get(
    "/handoff/export/download/provider-private-signed-url/status/{provider_signed_url_receipt_id}",
    response_model=Layer3ProviderPrivateSignedUrlStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_provider_private_signed_url_status(
    provider_signed_url_receipt_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_provider_private_signed_url.provider_private_signed_url_status(
            db,
            provider_signed_url_receipt_id,
        )
    )


@router.post(
    "/handoff/export/download/provider-private-signed-url/revoke",
    response_model=Layer3ProviderPrivateSignedUrlRevokeResponse,
    openapi_extra={"requestBody": _json_request_body(PROVIDER_PRIVATE_SIGNED_URL_REVOKE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_provider_private_signed_url_revoke(
    request: Request,
    payload: Layer3ProviderPrivateSignedUrlRevokeRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_provider_private_signed_url.provider_private_signed_url_revoke(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/export/download/provider-public-url/prepare",
    response_model=Layer3ProviderPublicUrlPrepareResponse,
    openapi_extra={"requestBody": _json_request_body(PROVIDER_PUBLIC_URL_PREPARE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_provider_public_url_prepare(
    request: Request,
    payload: Layer3ProviderPublicUrlPrepareRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_provider_public_url.provider_public_url_prepare(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.get(
    "/handoff/export/download/provider-public-url/status/{provider_public_url_receipt_id}",
    response_model=Layer3ProviderPublicUrlStatusResponse,
    responses=_workbench_error_responses(400, 404, 409),
)
def get_provider_public_url_status(
    provider_public_url_receipt_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_provider_public_url.provider_public_url_status(
            db,
            provider_public_url_receipt_id,
        )
    )


@router.post(
    "/handoff/export/download/provider-public-url/revoke",
    response_model=Layer3ProviderPublicUrlRevokeResponse,
    openapi_extra={"requestBody": _json_request_body(PROVIDER_PUBLIC_URL_REVOKE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_provider_public_url_revoke(
    request: Request,
    payload: Layer3ProviderPublicUrlRevokeRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_provider_public_url.provider_public_url_revoke(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/export/download/provider-public-url/use",
    response_model=Layer3ProviderPublicUrlDeliveryUseResponse,
    openapi_extra={"requestBody": _json_request_body(PROVIDER_PUBLIC_URL_DELIVERY_USE_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_provider_public_url_delivery_use(
    request: Request,
    payload: Layer3ProviderPublicUrlDeliveryUseRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request, access="read")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_provider_public_url_delivery_use.provider_public_url_delivery_use(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/handoff/export/download/deliver",
    response_model=None,
    openapi_extra={"requestBody": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUEST_BODY},
    responses={
        200: {
            "description": "APS evidence bundle artifact attachment.",
            "content": {
                "application/json": {
                    "schema": {"type": "string", "format": "binary"},
                },
            },
            "headers": {
                "Content-Disposition": {"schema": {"type": "string"}},
                "X-Layer3-Schema-Id": {"schema": {"type": "string"}},
                "X-Layer3-Delivery-State": {"schema": {"type": "string"}},
                "X-Layer3-Source-Artifact-Hash": {"schema": {"type": "string"}},
                "X-Layer3-Package-Family": {"schema": {"type": "string"}},
                "X-Layer3-Output-Package-Id": {"schema": {"type": "string"}},
                "X-Layer3-Package-Kind": {"schema": {"type": "string"}},
                "X-Layer3-Package-Payload-Hash": {"schema": {"type": "string"}},
                "X-Layer3-External-Export-Download-Readiness-Record-Ref": {
                    "schema": {"type": "string"}
                },
                "X-Layer3-External-Export-Download-Delivery-Record-Ref": {
                    "schema": {"type": "string"}
                },
            },
        },
        400: {"model": Layer3WorkbenchErrorResponse},
        404: {"model": Layer3WorkbenchErrorResponse},
        409: {"model": Layer3WorkbenchErrorResponse},
    },
)
async def post_external_export_download_deliver(
    request: Request,
    db: Session = Depends(get_db),
) -> FileResponse | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        payload = await _payload_from_request(request)
        delivery = layer3_workbench.external_export_download_deliver(db, payload)
    except Layer3WorkbenchError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=workbench_error_response(exc),
        )
    return FileResponse(
        path=delivery.artifact_path,
        media_type=delivery.media_type,
        filename=delivery.filename,
        content_disposition_type="attachment",
        headers=delivery.headers,
    )


@router.post(
    "/handoff/export/download/signed-reference/use",
    response_model=None,
    openapi_extra={"requestBody": _json_request_body(EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_USE_REQUEST_SCHEMA)},
    responses={
        200: {
            "description": "APS evidence bundle artifact attachment from a server-owned signed delivery reference.",
            "content": {
                "application/json": {
                    "schema": {"type": "string", "format": "binary"},
                },
            },
            "headers": {
                "Content-Disposition": {"schema": {"type": "string"}},
                "X-Layer3-Schema-Id": {"schema": {"type": "string"}},
                "X-Layer3-Delivery-State": {"schema": {"type": "string"}},
                "X-Layer3-Source-Artifact-Hash": {"schema": {"type": "string"}},
                "X-Layer3-Signed-Reference-State": {"schema": {"type": "string"}},
                "X-Layer3-Signed-Reference-Expires-At": {"schema": {"type": "string"}},
                "X-Layer3-Signed-Reference-Token-Id": {"schema": {"type": "string"}},
                "X-Layer3-Signed-Reference-Receipt-Id": {"schema": {"type": "string"}},
                "X-Layer3-Signed-Reference-Replay-Policy": {"schema": {"type": "string"}},
                "X-Layer3-Signed-Reference-Use-Count": {"schema": {"type": "string"}},
            },
        },
        400: {"model": Layer3WorkbenchErrorResponse},
        404: {"model": Layer3WorkbenchErrorResponse},
        409: {"model": Layer3WorkbenchErrorResponse},
    },
)
def post_external_export_download_signed_reference_use(
    request: Request,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
) -> FileResponse | JSONResponse:
    try:
        _route_level_operator_identity(request, access="write")
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    try:
        delivery = layer3_workbench.external_export_download_use_signed_reference(db, payload)
    except Layer3WorkbenchError as exc:
        return JSONResponse(
            status_code=exc.http_status,
            content=workbench_error_response(exc),
        )
    return FileResponse(
        path=delivery.artifact_path,
        media_type=delivery.media_type,
        filename=delivery.filename,
        content_disposition_type="attachment",
        headers=delivery.headers,
    )
