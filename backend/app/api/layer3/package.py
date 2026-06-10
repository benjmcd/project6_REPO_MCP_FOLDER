from __future__ import annotations

from typing import Any

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import (
    layer3_corrected_package_artifact_set,
    layer3_package_mutation_entry,
    layer3_package_replacement_activation,
    layer3_package_supersession_commit,
    layer3_replacement_package_artifact_manifest,
    layer3_replacement_package_materialization,
    layer3_replacement_package_namespace,
    layer3_replacement_package_set_authority,
    layer3_workbench,
)
from app.api.layer3 import router
from app.api.layer3._shared import *  # noqa: F401,F403
from app.api.layer3 import (  # Pydantic models still defined in __init__
    Layer3CorrectedPackageArtifactSetRequest,
    Layer3CorrectedPackageArtifactSetResponse,
    Layer3PackageConstructionCommitRequest,
    Layer3PackageConstructionCommitResponse,
    Layer3PackageReplacementActivationCommitRequest,
    Layer3PackageReplacementActivationCommitResponse,
    Layer3PackageReviewPreviewRequest,
    Layer3PackageReviewPreviewResponse,
    Layer3PackageReviewSubmitRequest,
    Layer3PackageReviewSubmitResponse,
    Layer3PackageSupersessionCommitFromCorrectedArtifactSetRequest,
    Layer3PackageSupersessionCommitRequest,
    Layer3PackageSupersessionCommitResponse,
    Layer3PackageSupersessionPreviewRequest,
    Layer3PackageSupersessionPreviewResponse,
    Layer3ReplacementPackageArtifactManifestFromAuthorityRequest,
    Layer3ReplacementPackageArtifactManifestFromCorrectedArtifactSetRequest,
    Layer3ReplacementPackageArtifactManifestRequest,
    Layer3ReplacementPackageArtifactManifestResponse,
    Layer3ReplacementPackageArtifactMaterializationRequest,
    Layer3ReplacementPackageArtifactMaterializationResponse,
    Layer3ReplacementPackageNamespaceFromCorrectedManifestRequest,
    Layer3ReplacementPackageNamespaceRecordRequest,
    Layer3ReplacementPackageNamespaceRecordResponse,
    Layer3ReplacementPackageNamespaceSetResponse,
    Layer3ReplacementPackageSetAuthorityFromCorrectedArtifactSetRequest,
    Layer3ReplacementPackageSetAuthorityRequest,
    Layer3ReplacementPackageSetAuthorityResponse,
    Layer3WorkbenchErrorResponse,
    _workbench_error_responses,
)


@router.post(
    "/package/review/preview",
    response_model=Layer3PackageReviewPreviewResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_REVIEW_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_review_preview(
    request: Request,
    payload: Layer3PackageReviewPreviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.package_review_preview(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/package/review/commit",
    response_model=Layer3PackageConstructionCommitResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_CONSTRUCTION_COMMIT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_review_commit(
    request: Request,
    payload: Layer3PackageConstructionCommitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.package_construction_commit(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/package/review/submit",
    response_model=Layer3PackageReviewSubmitResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_REVIEW_SUBMIT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_review_submit(
    request: Request,
    payload: Layer3PackageReviewSubmitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(lambda: layer3_workbench.package_review_submit(db, payload.model_dump(exclude_unset=True)))


@router.post(
    "/package/mutation/preview",
    response_model=Layer3PackageSupersessionPreviewResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_SUPERSESSION_PREVIEW_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_mutation_preview(
    request: Request,
    payload: Layer3PackageSupersessionPreviewRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_package_mutation_entry.preview_package_supersession(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-artifact/materialize",
    response_model=Layer3ReplacementPackageArtifactMaterializationResponse,
    openapi_extra={"requestBody": _json_request_body(REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_artifact_materialize(
    request: Request,
    payload: Layer3ReplacementPackageArtifactMaterializationRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_replacement_package_materialization.materialize_replacement_package_artifacts(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-set/record",
    response_model=Layer3ReplacementPackageSetAuthorityResponse,
    openapi_extra={"requestBody": _json_request_body(REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_set_record(
    request: Request,
    payload: Layer3ReplacementPackageSetAuthorityRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_replacement_package_set_authority.record_replacement_package_set_authority(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-set/record-from-corrected-artifact-set",
    response_model=Layer3ReplacementPackageSetAuthorityResponse,
    openapi_extra={
        "requestBody": _json_request_body(
            REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_REQUEST_SCHEMA
        )
    },
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_set_record_from_corrected_artifact_set(
    request: Request,
    payload: Layer3ReplacementPackageSetAuthorityFromCorrectedArtifactSetRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_replacement_package_set_authority.record_replacement_package_set_authority_from_corrected_artifact_set(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/supersession/commit",
    response_model=Layer3PackageSupersessionCommitResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_SUPERSESSION_COMMIT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_supersession_commit(
    request: Request,
    payload: Layer3PackageSupersessionCommitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_package_supersession_commit.commit_package_supersession(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/supersession/commit-from-corrected-artifact-set-authority",
    response_model=Layer3PackageSupersessionCommitResponse,
    openapi_extra={
        "requestBody": _json_request_body(PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_REQUEST_SCHEMA)
    },
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_supersession_commit_from_corrected_artifact_set_authority(
    request: Request,
    payload: Layer3PackageSupersessionCommitFromCorrectedArtifactSetRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_package_supersession_commit.commit_package_supersession_from_corrected_artifact_set_authority(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-artifact/manifest/record",
    response_model=Layer3ReplacementPackageArtifactManifestResponse,
    openapi_extra={"requestBody": _json_request_body(REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_artifact_manifest_record(
    request: Request,
    payload: Layer3ReplacementPackageArtifactManifestRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_replacement_package_artifact_manifest.record_replacement_package_artifact_manifest(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-artifact/manifest/record-from-authority",
    response_model=Layer3ReplacementPackageArtifactManifestResponse,
    openapi_extra={
        "requestBody": _json_request_body(REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_REQUEST_SCHEMA)
    },
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_artifact_manifest_record_from_authority(
    request: Request,
    payload: Layer3ReplacementPackageArtifactManifestFromAuthorityRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_replacement_package_artifact_manifest.record_replacement_package_artifact_manifest_from_authority(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-artifact/manifest/record-from-corrected-artifact-set-authority",
    response_model=Layer3ReplacementPackageArtifactManifestResponse,
    openapi_extra={
        "requestBody": _json_request_body(
            REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_REQUEST_SCHEMA
        )
    },
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_artifact_manifest_record_from_corrected_artifact_set_authority(
    request: Request,
    payload: Layer3ReplacementPackageArtifactManifestFromCorrectedArtifactSetRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_replacement_package_artifact_manifest.record_replacement_package_artifact_manifest_from_corrected_artifact_set_authority(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/corrected-artifact-set/record",
    response_model=Layer3CorrectedPackageArtifactSetResponse,
    openapi_extra={"requestBody": _json_request_body(CORRECTED_PACKAGE_ARTIFACT_SET_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_corrected_artifact_set_record(
    request: Request,
    payload: Layer3CorrectedPackageArtifactSetRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_corrected_package_artifact_set.record_corrected_package_artifact_set(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-namespace/record",
    response_model=Layer3ReplacementPackageNamespaceRecordResponse,
    openapi_extra={"requestBody": _json_request_body(REPLACEMENT_PACKAGE_NAMESPACE_RECORD_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_namespace_record(
    request: Request,
    payload: Layer3ReplacementPackageNamespaceRecordRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_replacement_package_namespace.record_replacement_package_namespace(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-namespace/record-from-corrected-artifact-manifest-authority",
    response_model=Layer3ReplacementPackageNamespaceSetResponse,
    openapi_extra={
        "requestBody": _json_request_body(
            REPLACEMENT_PACKAGE_NAMESPACE_FROM_CORRECTED_MANIFEST_REQUEST_SCHEMA
        )
    },
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_namespace_record_from_corrected_artifact_manifest_authority(
    request: Request,
    payload: Layer3ReplacementPackageNamespaceFromCorrectedManifestRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_replacement_package_namespace.record_replacement_package_namespace_from_corrected_artifact_manifest_authority(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )


@router.post(
    "/package/replacement-activation/commit",
    response_model=Layer3PackageReplacementActivationCommitResponse,
    openapi_extra={"requestBody": _json_request_body(PACKAGE_REPLACEMENT_ACTIVATION_COMMIT_REQUEST_SCHEMA)},
    responses=_workbench_error_responses(400, 404, 409),
)
def post_package_replacement_activation_commit(
    request: Request,
    payload: Layer3PackageReplacementActivationCommitRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any] | JSONResponse:
    try:
        _route_level_operator_identity(request)
    except SecXbrlInAppAuthPolicyError as exc:
        return _sec_xbrl_auth_policy_error_response(exc)
    return _json_or_error(
        lambda: layer3_package_replacement_activation.commit_package_replacement_activation(
            db,
            payload.model_dump(exclude_unset=True),
        )
    )
