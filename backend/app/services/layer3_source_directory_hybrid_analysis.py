from __future__ import annotations

import hashlib
import time
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    L3MaterialSnapshot,
    L3OutputPackage,
    L3ProviderPrivateSignedUrlAuditEvent,
    L3ProviderPrivateSignedUrlObjectAuthority,
    L3ProviderPrivateSignedUrlReceipt,
    L3ReconciliationRecord,
    L3Session,
)
from app.services.layer3_external_export_contract import ExternalExportDownloadDelivery
from app.services.layer3_provider_private_signed_url import (
    PROVIDER_PRIVATE_SIGNED_URL_DELIVERY_MODE,
    PROVIDER_PRIVATE_SIGNED_URL_REDACTED_MARKER,
)
from app.services.layer3_provider_private_signed_url_fake_provider import (
    PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
    ProviderArtifactAuthority,
    ProviderPrivateSignedUrlError,
    ProviderPrivateSignedUrlFakeProvider,
    ProviderPrivateSignedUrlPrepareRequest,
)
from app.services.layer3_provider_private_signed_url_state import (
    INTERNAL_ARTIFACT_REF_PLACEHOLDER,
    PROVIDER_PRIVATE_SIGNED_URL_MAX_TTL_SECONDS,
    ProviderPrivateSignedUrlStateError,
    record_prepared_provider_private_signed_url_receipt,
    record_server_owned_provider_private_signed_url_receipt_use,
    revoke_provider_private_signed_url_receipt,
)
from app.services.layer3_source_directory_hybrid_context import (
    CONTRACT_ID as HYBRID_CONTEXT_CONTRACT_ID,
    HYBRID_MODE as HYBRID_CONTEXT_MODE,
    SCHEMA_ID as HYBRID_CONTEXT_SCHEMA_ID,
    source_directory_material_hybrid_retrieval_context_packet,
)
from app.services.layer3_package_entry import (
    FINALIZED_PACKAGE_SESSION_STATUSES,
    Layer3PackageEntryError,
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
    SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
    materialize_source_directory_hybrid_context_qualitative_analysis_package_commit,
)
from app.services.layer3_source_directory_ingestion import _stable_hash
from app.services.layer3_utils import json_clone as _json_clone, stable_id as _stable_id
from app.services.nrc_aps_content_index import normalize_query_tokens

SCHEMA_ID = "layer3.source_directory_hybrid_context_packet_qualitative_analysis.v1"
MODE = "source_directory_hybrid_context_packet_qualitative_analysis_authority"
ANALYSIS_CONTRACT_ID = "source_directory_hybrid_context_packet_qualitative_analysis_authority"
ANALYSIS_MODE = "hybrid_context_packet_grounded_qualitative_analysis"
SOURCE_GATE = "824_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_RUNTIME_ENTRY_FREEZE"
ANALYSIS_STATUS_SCHEMA_ID = (
    "layer3.source_directory_hybrid_context_packet_qualitative_analysis_status.v1"
)
ANALYSIS_STATUS_MODE = (
    "source_directory_hybrid_context_packet_qualitative_analysis_status_authority"
)
ANALYSIS_STATUS_SOURCE_GATE = (
    "834_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_STATUS_RUNTIME_ENTRY_FREEZE"
)
ANALYSIS_STATUS_DEFAULT_CLIENT_REQUEST_ID = (
    "source-directory-hybrid-context-qualitative-analysis-status-read"
)
PACKAGE_REVIEW_PREVIEW_SCHEMA_ID = (
    "layer3.source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview.v1"
)
PACKAGE_REVIEW_PREVIEW_MODE = (
    "read_only_source_directory_hybrid_context_packet_qualitative_analysis_package_review_preview"
)
PACKAGE_REVIEW_PREVIEW_SOURCE_GATE = (
    "826_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_PREVIEW_RUNTIME_ENTRY_FREEZE"
)
PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)
PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID = (
    "layer3.source_directory_hybrid_context_packet_qualitative_analysis_package_commit.v1"
)
PACKAGE_CONSTRUCTION_COMMIT_MODE = (
    "source_directory_hybrid_context_packet_qualitative_analysis_package_commit_authority"
)
PACKAGE_CONSTRUCTION_OPERATOR_DECISION = (
    "commit_source_directory_hybrid_context_packet_qualitative_analysis_package"
)
PACKAGE_REVIEW_SUBMIT_SCHEMA_ID = (
    "layer3.source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit.v1"
)
PACKAGE_REVIEW_SUBMIT_MODE = (
    "source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_authority"
)
PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID = "layer3.package_review_submit_state.v1"
PACKAGE_REVIEW_SUBMIT_SOURCE_GATE = (
    "830_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_PACKAGE_REVIEW_SUBMIT_RUNTIME_ENTRY_FREEZE"
)
PACKAGE_REVIEW_APPROVED_STATE = "package_review_approved"
PACKAGE_REVIEW_SUBMIT_DECISIONS = frozenset({"approved", "changes_requested", "rejected", "blocked"})
PACKAGE_REVIEW_SUBMIT_STATE_BY_DECISION = {
    "approved": PACKAGE_REVIEW_APPROVED_STATE,
    "changes_requested": "package_review_changes_requested",
    "rejected": "package_review_rejected",
    "blocked": "package_review_blocked",
}
PACKAGE_REVIEW_SUBMIT_NOTE_REQUIRED_DECISIONS = frozenset({"changes_requested", "rejected", "blocked"})
PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE = (
    "handoff",
    "export",
    "external_export_download",
    "connector_dispatch",
    "provider_delivery",
)
HANDOFF_EXPORT_PREPARE_SCHEMA_ID = (
    "layer3.source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare.v1"
)
HANDOFF_EXPORT_PREPARE_MODE = (
    "source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_authority"
)
HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID = "layer3.handoff_export_prepare_state.v1"
HANDOFF_EXPORT_PREPARE_SOURCE_GATE = (
    "832_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_HANDOFF_EXPORT_PREPARE_RUNTIME_ENTRY_FREEZE"
)
HANDOFF_EXPORT_PREPARED_STATE = "handoff_export_prepared"
HANDOFF_EXPORT_HELD_STATE = "handoff_export_held"
HANDOFF_EXPORT_DECLINED_STATE = "handoff_export_declined"
HANDOFF_EXPORT_BLOCKED_STATE = "handoff_export_blocked"
HANDOFF_EXPORT_PREPARE_DECISIONS = frozenset({"authorize_prepare", "hold", "decline", "blocked"})
HANDOFF_EXPORT_PREPARE_STATE_BY_DECISION = {
    "authorize_prepare": HANDOFF_EXPORT_PREPARED_STATE,
    "hold": HANDOFF_EXPORT_HELD_STATE,
    "decline": HANDOFF_EXPORT_DECLINED_STATE,
    "blocked": HANDOFF_EXPORT_BLOCKED_STATE,
}
HANDOFF_EXPORT_PREPARE_STATUS_BY_DECISION = {
    "authorize_prepare": "prepared",
    "hold": "held",
    "decline": "declined",
    "blocked": "blocked",
}
HANDOFF_EXPORT_PREPARE_NOTE_REQUIRED_DECISIONS = frozenset({"hold", "decline", "blocked"})
HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE = (
    "external_export_download",
    "connector_dispatch",
    "provider_public_delivery",
    "provider_private_signed_url",
    "network_egress",
)
EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = (
    "layer3.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare.v1"
)
EXTERNAL_EXPORT_DOWNLOAD_PREPARE_MODE = (
    "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare_authority"
)
EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID = "layer3.external_export_download_prepare_state.v1"
EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_GATE = (
    "836_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_RUNTIME_ENTRY_FREEZE"
)
EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION = (
    "prepare_source_directory_hybrid_external_export_download"
)
EXTERNAL_EXPORT_DOWNLOAD_TARGET = (
    "source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference"
)
EXTERNAL_EXPORT_DOWNLOAD_MODE = "reference_only_prepare"
EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE = "external_export_download_prepared"
EXTERNAL_EXPORT_DOWNLOAD_PREPARE_DOWNSTREAM_UNAVAILABLE = (
    "same_origin_delivery",
    "browser_download",
    "connector_dispatch",
    "provider_public_delivery",
    "provider_private_signed_url",
    "network_egress",
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = (
    "layer3.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery.v1"
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_SCHEMA_ID = (
    "layer3.source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status.v1"
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE = (
    "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_authority"
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_MODE = (
    "source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status_authority"
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SOURCE_GATE = (
    "838_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RUNTIME_ENTRY_FREEZE"
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_SOURCE_GATE = EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SOURCE_GATE
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION = (
    "deliver_source_directory_hybrid_external_export_download"
)
EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE_VALUE = "same_origin_artifact_stream"
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_PREPARE_SCHEMA_ID = (
    "layer3.source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url.prepare.v1"
)
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_PREPARE_MODE = (
    "source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_prepare_authority"
)
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_OPERATOR_DECISION = (
    "prepare_source_directory_hybrid_provider_private_signed_url"
)
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_SCHEMA_ID = (
    "layer3.source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url.use.v1"
)
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_MODE = (
    "source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_use_authority"
)
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_OPERATOR_DECISION = (
    "use_source_directory_hybrid_provider_private_signed_url"
)
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_STATUS_SCHEMA_ID = (
    "layer3.source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url.status.v1"
)
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_STATUS_MODE = (
    "source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_status_authority"
)
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_STATUS_OPERATOR_DECISION = (
    "inspect_source_directory_hybrid_provider_private_signed_url_status"
)
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_SCHEMA_ID = (
    "layer3.source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url.revoke.v1"
)
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_MODE = (
    "source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_revoke_authority"
)
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_OPERATOR_DECISION = (
    "revoke_source_directory_hybrid_provider_private_signed_url"
)
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_DEFAULT_TTL_SECONDS = 300
SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_FIXED_FAKE_PROVIDER_EPOCH = 0
EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE = "external_export_download_delivered"

_REQUIRED_FIELDS = {
    "client_request_id",
    "analysis_question",
    "analysis_focus",
    "material_snapshot_id",
    "source_ingestion_batch_id",
    "source_ingestion_file_id",
    "content_sha256",
    "file_identity_hash",
    "authority_basis_hash",
    "payload_hash",
    "index_authority_hash",
    "embedding_index_authority_hash",
    "query_text",
}

_OPTIONAL_FIELDS = {"limit", "offset", "top_k"}

_PACKAGE_COMMIT_REQUIRED_FIELDS = _REQUIRED_FIELDS | {
    "qualitative_analysis_hash",
    "source_directory_hybrid_package_review_preview_hash",
    "operator_decision",
}

_PACKAGE_REVIEW_SUBMIT_REQUIRED_FIELDS = _REQUIRED_FIELDS | {
    "qualitative_analysis_hash",
    "source_directory_hybrid_package_review_preview_hash",
    "construction_basis_hash",
    "reconciliation_record_id",
    "output_package_ids",
    "package_kinds",
    "payload_hashes",
    "operator_decision",
}

_HANDOFF_EXPORT_PREPARE_REQUIRED_FIELDS = _PACKAGE_REVIEW_SUBMIT_REQUIRED_FIELDS | {
    "package_review_submit_record_ref",
    "package_review_state",
    "handoff_target",
    "export_mode",
}

_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUIRED_FIELDS = _HANDOFF_EXPORT_PREPARE_REQUIRED_FIELDS | {
    "prepare_record_ref",
    "handoff_export_state",
    "handoff_export_envelope_ref",
    "external_export_download_target",
    "download_mode",
}
_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUIRED_FIELDS = (
    _EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUIRED_FIELDS
    | {
        "external_export_download_record_ref",
        "export_download_descriptor_ref",
        "external_export_download_state",
        "delivery_mode",
        "output_package_id",
        "package_kind",
        "package_payload_hash",
    }
)
_SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REQUIRED_FIELDS = (
    _EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUIRED_FIELDS | {"recipient_scope"}
)
_SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_ALLOWED_FIELDS = (
    _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REQUIRED_FIELDS
    | _OPTIONAL_FIELDS
    | {"decision_notes", "requested_ttl_seconds"}
)
_SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_REQUIRED_FIELDS = (
    _EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUIRED_FIELDS
    | {"provider_signed_url_receipt_id"}
)
_SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_ALLOWED_FIELDS = (
    _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_REQUIRED_FIELDS
    | _OPTIONAL_FIELDS
    | {"decision_notes"}
)
_SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_STATUS_REQUIRED_FIELDS = (
    _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_REQUIRED_FIELDS
)
_SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_STATUS_ALLOWED_FIELDS = (
    _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_STATUS_REQUIRED_FIELDS
    | _OPTIONAL_FIELDS
    | {"decision_notes"}
)
_SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_REQUIRED_FIELDS = (
    _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_REQUIRED_FIELDS
    | {"idempotency_key", "revoked_by", "revocation_reason"}
)
_SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_ALLOWED_FIELDS = (
    _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_REQUIRED_FIELDS
    | _OPTIONAL_FIELDS
    | {"decision_notes"}
)

_HYBRID_CONTEXT_FIELDS = (
    _REQUIRED_FIELDS
    - {
        "analysis_question",
        "analysis_focus",
    }
) | _OPTIONAL_FIELDS

_FORBIDDEN_FIELDS = {
    "absolute_path",
    "analysis_run_id",
    "connector_target",
    "destination",
    "durable_write",
    "embedding",
    "embedding_model",
    "embedding_options",
    "file_bytes",
    "frontend_state",
    "glob",
    "local_path",
    "model",
    "output_package_id",
    "package_payload",
    "pass_run_id",
    "path",
    "prompt",
    "provider_model",
    "provider_url",
    "public_url",
    "rag_execution",
    "rag_index",
    "rag_plan",
    "rag_prompt",
    "recursive",
    "rewrite_output",
    "runtime_db_write",
    "semantic_score",
    "url",
    "vector",
    "vector_index",
    "web_connector",
}

_HANDOFF_EXPORT_PREPARE_FORBIDDEN_FIELDS = _FORBIDDEN_FIELDS | {
    "aps_handoff",
    "connector_dispatch",
    "connector_payload",
    "delivery",
    "download",
    "download_url",
    "external_export",
    "provider_private_signed_url",
    "provider_public_url",
    "send",
    "signed_url",
}

_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS = _FORBIDDEN_FIELDS | {
    "aps_handoff",
    "browser_download",
    "connector_dispatch",
    "connector_payload",
    "delivery",
    "download",
    "download_token",
    "download_url",
    "payload_path",
    "provider_private_signed_url",
    "provider_public_url",
    "raw_payload_path",
    "send",
    "signed_url",
}
_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS = (
    _EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS - {"output_package_id"}
) | {
    "bucket",
    "connector_run_id",
    "connector_secret",
    "destination_id",
    "local_file_path",
    "object_key",
    "provider_credentials",
    "raw_provider_url",
    "write_destination",
}
_SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_FORBIDDEN_FIELDS = (
    _EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS
    | {
        "provider_private_signed_url_token",
        "raw_provider_private_signed_url_token",
        "provider_public_url",
        "raw_public_url",
        "provider_secret",
    }
)


class SourceDirectoryHybridAnalysisError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-hybrid-context-qualitative-analysis-error",
            "server_time": _server_time(),
            "mode": MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryHybridPackageCommitError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-hybrid-package-commit-error",
            "server_time": _server_time(),
            "mode": PACKAGE_CONSTRUCTION_COMMIT_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryHybridPackageReviewSubmitError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-hybrid-package-review-submit-error",
            "server_time": _server_time(),
            "mode": PACKAGE_REVIEW_SUBMIT_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryHybridHandoffExportPrepareError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": HANDOFF_EXPORT_PREPARE_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-hybrid-handoff-export-prepare-error",
            "server_time": _server_time(),
            "mode": HANDOFF_EXPORT_PREPARE_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryHybridExternalExportDownloadPrepareError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-hybrid-external-export-download-prepare-error",
            "server_time": _server_time(),
            "mode": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryHybridExternalExportDownloadDeliveryError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-hybrid-external-export-download-delivery-error",
            "server_time": _server_time(),
            "mode": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_PREPARE_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-hybrid-provider-private-signed-url-prepare-error",
            "server_time": _server_time(),
            "mode": SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_PREPARE_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryHybridProviderPrivateSignedUrlUseError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-hybrid-provider-private-signed-url-use-error",
            "server_time": _server_time(),
            "mode": SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryHybridProviderPrivateSignedUrlStatusError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_STATUS_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-hybrid-provider-private-signed-url-status-error",
            "server_time": _server_time(),
            "mode": SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_STATUS_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class SourceDirectoryHybridProviderPrivateSignedUrlRevokeError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-hybrid-provider-private-signed-url-revoke-error",
            "server_time": _server_time(),
            "mode": SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def source_directory_hybrid_context_packet_qualitative_analysis(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    analysis_question = _required(fields, "analysis_question")
    analysis_focus = _required(fields, "analysis_focus")

    hybrid_context = source_directory_material_hybrid_retrieval_context_packet(
        db,
        _hybrid_context_payload(fields),
    )
    _assert_hybrid_context_authority(hybrid_context)

    items = list(hybrid_context.get("items") or [])
    supporting_segments = _supporting_segments(items)
    salient_terms = _salient_terms(hybrid_context.get("query_tokens") or [], items)
    evidence_summary = _evidence_summary(
        hybrid_context=hybrid_context,
        supporting_segments=supporting_segments,
        analysis_question=analysis_question,
    )
    coverage_notes = _coverage_notes(
        hybrid_context=hybrid_context,
        supporting_segments=supporting_segments,
    )
    analysis_limits = _analysis_limits()
    row_write_flags = _row_write_flags()
    negative_invariants = _negative_invariants()
    qualitative_analysis_hash = _qualitative_analysis_hash(
        fields=fields,
        hybrid_context=hybrid_context,
        evidence_summary=evidence_summary,
        salient_terms=salient_terms,
        supporting_segments=supporting_segments,
        coverage_notes=coverage_notes,
        analysis_limits=analysis_limits,
        row_write_flags=row_write_flags,
        negative_invariants=negative_invariants,
    )
    package_review_preview = _package_review_preview(
        request_id=request_id,
        fields=fields,
        hybrid_context=hybrid_context,
        qualitative_analysis_hash=qualitative_analysis_hash,
    )

    return {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": MODE,
        "status": "available",
        "analysis_contract_id": ANALYSIS_CONTRACT_ID,
        "analysis_mode": ANALYSIS_MODE,
        "source_gate": SOURCE_GATE,
        "qualitative_analysis_hash": qualitative_analysis_hash,
        "analysis_question": analysis_question,
        "analysis_focus": analysis_focus,
        "hybrid_context_packet_hash": hybrid_context["hybrid_context_packet_hash"],
        "hybrid_context_contract_id": hybrid_context["hybrid_context_contract_id"],
        "hybrid_context_mode": hybrid_context["hybrid_context_mode"],
        "validated_hybrid_context_schema_id": hybrid_context["schema_id"],
        "validated_hybrid_context_mode": hybrid_context["mode"],
        "lexical_context_packet_hash": hybrid_context["lexical_context_packet_hash"],
        "lexical_context_packet_contract_id": hybrid_context["lexical_context_packet_contract_id"],
        "lexical_context_packet_mode": hybrid_context["lexical_context_packet_mode"],
        "vector_retrieval_contract_id": hybrid_context["vector_retrieval_contract_id"],
        "vector_retrieval_mode": hybrid_context["vector_retrieval_mode"],
        "embedding_contract_id": hybrid_context["embedding_contract_id"],
        "embedding_mode": hybrid_context["embedding_mode"],
        "vector_index_mode": hybrid_context["vector_index_mode"],
        "feature_hash_version": hybrid_context["feature_hash_version"],
        "vector_dimensions": hybrid_context["vector_dimensions"],
        "query_tokens": list(hybrid_context.get("query_tokens") or []),
        "evidence_summary": evidence_summary,
        "salient_terms": salient_terms,
        "supporting_segments": supporting_segments,
        "coverage_notes": coverage_notes,
        "analysis_limits": analysis_limits,
        "lexical_total": int(hybrid_context["lexical_total"]),
        "lexical_limit": int(hybrid_context["lexical_limit"]),
        "lexical_offset": int(hybrid_context["lexical_offset"]),
        "vector_total": int(hybrid_context["vector_total"]),
        "vector_top_k": int(hybrid_context["vector_top_k"]),
        "hybrid_total": int(hybrid_context["hybrid_total"]),
        "index_authority_hash": hybrid_context["index_authority_hash"],
        "embedding_index_authority_hash": hybrid_context["embedding_index_authority_hash"],
        "source_ingestion_batch_id": hybrid_context["source_ingestion_batch_id"],
        "source_ingestion_file_id": hybrid_context["source_ingestion_file_id"],
        "material_snapshot_id": hybrid_context["material_snapshot_id"],
        "source_shape": hybrid_context.get("source_shape"),
        "content_sha256": hybrid_context["content_sha256"],
        "file_identity_hash": hybrid_context["file_identity_hash"],
        "authority_basis_hash": hybrid_context["authority_basis_hash"],
        "payload_hash": hybrid_context["payload_hash"],
        "source_directory_package_review_preview_enabled": True,
        "source_directory_hybrid_package_review_preview_hash": package_review_preview[
            "package_review_preview_hash"
        ],
        "source_directory_hybrid_package_review_preview": package_review_preview,
        "candidate_package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS),
        "package_commit_enabled": False,
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "external_export_download_enabled": False,
        **row_write_flags,
        "negative_invariants": negative_invariants,
        "next_allowed_actions": [],
    }


def source_directory_hybrid_context_packet_qualitative_analysis_status(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    analysis = source_directory_hybrid_context_packet_qualitative_analysis(
        db,
        _status_analysis_payload(payload),
    )
    status_state = _hybrid_qualitative_analysis_status_state(db, analysis=analysis)
    negative_invariants = {
        **dict(analysis["negative_invariants"]),
        "package_payload_rewrite_enabled": False,
        "source_package_row_mutation_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "raw_local_path_exposed": False,
        "raw_vector_exposed": False,
    }
    return {
        "schema_id": ANALYSIS_STATUS_SCHEMA_ID,
        "schema_version": 1,
        "request_id": analysis["request_id"],
        "server_time": _server_time(),
        "mode": ANALYSIS_STATUS_MODE,
        "status": "available",
        "analysis_status": (
            "source_directory_hybrid_context_packet_qualitative_analysis_available"
        ),
        "source_gate": ANALYSIS_STATUS_SOURCE_GATE,
        "validated_analysis_schema_id": analysis["schema_id"],
        "validated_analysis_mode": analysis["mode"],
        "analysis_contract_id": analysis["analysis_contract_id"],
        "analysis_mode": analysis["analysis_mode"],
        "qualitative_analysis_hash": analysis["qualitative_analysis_hash"],
        "hybrid_context_packet_hash": analysis["hybrid_context_packet_hash"],
        "hybrid_context_contract_id": analysis["hybrid_context_contract_id"],
        "hybrid_context_mode": analysis["hybrid_context_mode"],
        "validated_hybrid_context_schema_id": analysis["validated_hybrid_context_schema_id"],
        "validated_hybrid_context_mode": analysis["validated_hybrid_context_mode"],
        "lexical_context_packet_hash": analysis["lexical_context_packet_hash"],
        "lexical_context_packet_contract_id": analysis["lexical_context_packet_contract_id"],
        "lexical_context_packet_mode": analysis["lexical_context_packet_mode"],
        "vector_retrieval_contract_id": analysis["vector_retrieval_contract_id"],
        "vector_retrieval_mode": analysis["vector_retrieval_mode"],
        "embedding_contract_id": analysis["embedding_contract_id"],
        "embedding_mode": analysis["embedding_mode"],
        "vector_index_mode": analysis["vector_index_mode"],
        "feature_hash_version": analysis["feature_hash_version"],
        "vector_dimensions": int(analysis["vector_dimensions"]),
        "query_tokens": list(analysis["query_tokens"]),
        "coverage_label": str(analysis["evidence_summary"].get("coverage_label") or ""),
        "supporting_segment_count": len(analysis["supporting_segments"]),
        "salient_term_count": len(analysis["salient_terms"]),
        "coverage_note_count": len(analysis["coverage_notes"]),
        "analysis_limit_count": len(analysis["analysis_limits"]),
        "lexical_total": int(analysis["lexical_total"]),
        "lexical_limit": int(analysis["lexical_limit"]),
        "lexical_offset": int(analysis["lexical_offset"]),
        "vector_total": int(analysis["vector_total"]),
        "vector_top_k": int(analysis["vector_top_k"]),
        "hybrid_total": int(analysis["hybrid_total"]),
        "index_authority_hash": analysis["index_authority_hash"],
        "embedding_index_authority_hash": analysis["embedding_index_authority_hash"],
        "source_ingestion_batch_id": analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": analysis["source_ingestion_file_id"],
        "material_snapshot_id": analysis["material_snapshot_id"],
        "source_shape": analysis.get("source_shape"),
        "content_sha256": analysis["content_sha256"],
        "file_identity_hash": analysis["file_identity_hash"],
        "authority_basis_hash": analysis["authority_basis_hash"],
        "payload_hash": analysis["payload_hash"],
        "source_directory_package_review_preview_available": True,
        "source_directory_hybrid_package_review_preview_hash": analysis[
            "source_directory_hybrid_package_review_preview_hash"
        ],
        "source_directory_hybrid_package_review_preview_payload_redacted": True,
        "supporting_segments_redacted": True,
        "analysis_result_redacted": True,
        "source_index_rows_written": bool(analysis["source_index_rows_written"]),
        "embedding_vector_rows_written": bool(analysis["embedding_vector_rows_written"]),
        "vector_index_rows_written": bool(analysis["vector_index_rows_written"]),
        "retrieval_rows_written": bool(analysis["retrieval_rows_written"]),
        "context_packet_rows_written": bool(analysis["context_packet_rows_written"]),
        "qualitative_analysis_rows_written": bool(analysis["qualitative_analysis_rows_written"]),
        "qualitative_generation_rows_written": bool(
            analysis["qualitative_generation_rows_written"]
        ),
        "analysis_run_rows_written": bool(analysis["analysis_run_rows_written"]),
        "package_rows_written": False,
        "connector_rows_written": False,
        "negative_invariants": negative_invariants,
        **status_state,
    }


def source_directory_hybrid_context_packet_qualitative_analysis_package_commit(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_package_commit_payload(payload)
    request_id = _require_commit_field(fields, "client_request_id")
    if str(fields.get("operator_decision") or "") != PACKAGE_CONSTRUCTION_OPERATOR_DECISION:
        raise SourceDirectoryHybridPackageCommitError(
            "source_directory_hybrid_package_commit_operator_decision_not_admitted",
            "The source-directory hybrid package commit requires the admitted package-construction operator decision.",
            http_status=409,
            details={
                "field": "operator_decision",
                "expected": PACKAGE_CONSTRUCTION_OPERATOR_DECISION,
            },
        )

    qualitative_analysis = source_directory_hybrid_context_packet_qualitative_analysis(
        db,
        _qualitative_analysis_payload(fields),
    )
    expected_analysis_hash = str(qualitative_analysis["qualitative_analysis_hash"])
    if str(fields.get("qualitative_analysis_hash") or "") != expected_analysis_hash:
        raise SourceDirectoryHybridPackageCommitError(
            "source_directory_hybrid_package_commit_qualitative_analysis_hash_mismatch",
            "Package construction commit must reference the current server-recomputed hybrid qualitative-analysis hash.",
            http_status=409,
            details={"blocked_fields": ["qualitative_analysis_hash"]},
        )
    preview = qualitative_analysis["source_directory_hybrid_package_review_preview"]
    expected_preview_hash = str(preview["package_review_preview_hash"])
    if str(fields.get("source_directory_hybrid_package_review_preview_hash") or "") != expected_preview_hash:
        raise SourceDirectoryHybridPackageCommitError(
            "source_directory_hybrid_package_commit_preview_hash_mismatch",
            "Package construction commit must reference the current server-recomputed hybrid package-review preview hash.",
            http_status=409,
            details={"blocked_fields": ["source_directory_hybrid_package_review_preview_hash"]},
        )

    material_snapshot = _load_material_snapshot_for_commit(
        db,
        material_snapshot_id=str(qualitative_analysis["material_snapshot_id"]),
        source_authority=preview["source_authority"],
    )
    session = _load_package_commit_session(db, material_snapshot=material_snapshot)
    try:
        result = materialize_source_directory_hybrid_context_qualitative_analysis_package_commit(
            db,
            session=session,
            material_snapshot=material_snapshot,
            client_request_id=request_id,
            package_review_preview_hash=expected_preview_hash,
            qualitative_analysis=qualitative_analysis,
            source_authority=preview["source_authority"],
        )
    except Layer3PackageEntryError as exc:
        raise SourceDirectoryHybridPackageCommitError(
            "source_directory_hybrid_package_commit_existing_package_state",
            str(exc),
            http_status=409,
            details={"next_allowed_actions": ["inspect_existing_package_state"]},
        ) from exc
    db.commit()

    reconciliation_summary = result.reconciliation_record.summary_json or {}
    commit_summary = reconciliation_summary.get("source_directory_hybrid_context_qualitative_package_commit")
    if not isinstance(commit_summary, dict):
        commit_summary = {}
    packages = list(result.output_packages)
    construction_basis_hash = (
        commit_summary.get("construction_basis_hash")
        or next(
            (
                str((package.summary_json or {}).get("construction_basis_hash") or "")
                for package in packages
                if str((package.summary_json or {}).get("construction_basis_hash") or "")
            ),
            None,
        )
        or commit_summary.get("authority_basis_hash")
    )
    return {
        "schema_id": PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": PACKAGE_CONSTRUCTION_COMMIT_MODE,
        "status": "committed",
        "operator_decision": PACKAGE_CONSTRUCTION_OPERATOR_DECISION,
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "embedding_index_authority_hash": qualitative_analysis["embedding_index_authority_hash"],
        "lexical_context_packet_hash": qualitative_analysis["lexical_context_packet_hash"],
        "hybrid_context_packet_hash": qualitative_analysis["hybrid_context_packet_hash"],
        "qualitative_analysis_hash": expected_analysis_hash,
        "source_directory_hybrid_package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": construction_basis_hash,
        "reconciliation_record_id": result.reconciliation_record.reconciliation_record_id,
        "output_packages": [
            {
                "output_package_id": package.output_package_id,
                "package_kind": package.package_kind,
                "status": package.status,
                "payload_hash": package.payload_hash,
                "payload_ref_redacted": True,
            }
            for package in packages
        ],
        "output_package_ids": [package.output_package_id for package in packages],
        "package_kinds": [package.package_kind for package in packages],
        "payload_hashes": [package.payload_hash for package in packages],
        "payload_refs_redacted": True,
        "package_rows_written": True,
        "package_payloads_written": True,
        "source_package_row_mutation_enabled": False,
        "package_payload_rewrite_enabled": False,
        "package_review_submit_enabled": True,
        "handoff_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "package_construction_source_gate": SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "next_state": "source_directory_hybrid_context_qualitative_analysis_package_constructed",
        "next_allowed_actions": ["submit_package_review"],
        "negative_invariants": {
            "source_package_row_mutation_enabled": False,
            "package_payload_rewrite_enabled": False,
            "package_review_submit_enabled": True,
            "handoff_export_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_public_delivery_enabled": False,
            "network_egress_enabled": False,
            "frontend_durable_authority_enabled": False,
            "prompt_model_provider_runtime_enabled": False,
        },
    }


def source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_package_review_submit_payload(payload)
    request_id = _require_submit_field(fields, "client_request_id")
    operator_decision = str(fields.get("operator_decision") or "").strip()
    decision_notes = str(fields.get("decision_notes") or "").strip()
    if operator_decision not in PACKAGE_REVIEW_SUBMIT_DECISIONS:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_decision_not_admitted",
            "operator_decision must be approved, changes_requested, rejected, or blocked.",
            http_status=409,
            details={"field": "operator_decision"},
        )
    if operator_decision in PACKAGE_REVIEW_SUBMIT_NOTE_REQUIRED_DECISIONS and not decision_notes:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_decision_notes_required",
            "decision_notes are required for changes_requested, rejected, or blocked package-review decisions.",
            details={"field": "decision_notes"},
        )

    qualitative_analysis = source_directory_hybrid_context_packet_qualitative_analysis(
        db,
        _qualitative_analysis_payload(fields),
    )
    expected_analysis_hash = str(qualitative_analysis["qualitative_analysis_hash"])
    if str(fields.get("qualitative_analysis_hash") or "") != expected_analysis_hash:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_qualitative_analysis_hash_mismatch",
            "Package-review submit must reference the current server-recomputed hybrid qualitative-analysis hash.",
            http_status=409,
            details={"blocked_fields": ["qualitative_analysis_hash"]},
        )
    preview = qualitative_analysis["source_directory_hybrid_package_review_preview"]
    expected_preview_hash = str(preview["package_review_preview_hash"])
    if str(fields.get("source_directory_hybrid_package_review_preview_hash") or "") != expected_preview_hash:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_preview_hash_mismatch",
            "Package-review submit must reference the current server-recomputed hybrid package-review preview hash.",
            http_status=409,
            details={"blocked_fields": ["source_directory_hybrid_package_review_preview_hash"]},
        )

    material_snapshot = _load_material_snapshot_for_submit(
        db,
        material_snapshot_id=str(qualitative_analysis["material_snapshot_id"]),
        source_authority=preview["source_authority"],
    )
    session = _load_package_review_submit_session(db, material_snapshot=material_snapshot)
    reconciliation_record_id = _require_submit_field(fields, "reconciliation_record_id")
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session.session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if reconciliation is None:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_reconciliation_not_found",
            "No source-directory hybrid package reconciliation record exists for the supplied authority.",
            http_status=404,
            details={"reconciliation_record_id": reconciliation_record_id},
        )

    reconciliation_summary = _json_clone(reconciliation.summary_json or {})
    commit_summary = reconciliation_summary.get("source_directory_hybrid_context_qualitative_package_commit")
    if not isinstance(commit_summary, dict):
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_requires_package_commit",
            "Package-review submit requires source-directory hybrid qualitative package-commit authority.",
            http_status=409,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    if str(reconciliation_summary.get("source_gate") or "") != SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_source_gate_mismatch",
            "Package-review submit requires the source-directory hybrid package-construction source gate.",
            http_status=409,
            details={"blocked_fields": ["reconciliation_record_id"]},
        )

    packages = _source_directory_hybrid_review_packages(
        db,
        session_id=session.session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    supplied_construction_basis_hash = _require_submit_field(fields, "construction_basis_hash")
    expected_construction_basis_hash = str(
        commit_summary.get("construction_basis_hash")
        or next(
            (
                str((package.summary_json or {}).get("construction_basis_hash") or "")
                for package in packages
                if str((package.summary_json or {}).get("construction_basis_hash") or "")
            ),
            "",
        )
        or commit_summary.get("authority_basis_hash")
        or ""
    )
    commit_authority_basis = commit_summary.get("authority_basis")
    if not isinstance(commit_authority_basis, dict):
        commit_authority_basis = {}
    commit_mismatches = [
        field
        for field, expected in {
            "package_review_preview_hash": expected_preview_hash,
            "qualitative_analysis_hash": expected_analysis_hash,
            "hybrid_context_packet_hash": qualitative_analysis["hybrid_context_packet_hash"],
            "embedding_index_authority_hash": qualitative_analysis["embedding_index_authority_hash"],
        }.items()
        if str(commit_summary.get(field) or commit_authority_basis.get(field) or "") != str(expected)
    ]
    if commit_mismatches or supplied_construction_basis_hash != expected_construction_basis_hash:
        blocked_fields = sorted(
            set(
                commit_mismatches
                + (
                    ["construction_basis_hash"]
                    if supplied_construction_basis_hash != expected_construction_basis_hash
                    else []
                )
            )
        )
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_construction_mismatch",
            "Stored package-construction provenance does not match the supplied package-review submit authority.",
            http_status=409,
            details={"blocked_fields": blocked_fields},
        )

    supplied_package_ids = _submit_string_list(fields.get("output_package_ids"), field="output_package_ids")
    supplied_package_kinds = _submit_string_list(fields.get("package_kinds"), field="package_kinds")
    supplied_payload_hashes = _submit_string_list(fields.get("payload_hashes"), field="payload_hashes")
    expected_package_ids = [package.output_package_id for package in packages]
    expected_package_kinds = [package.package_kind for package in packages]
    expected_payload_hashes = [package.payload_hash for package in packages]
    if supplied_package_ids != expected_package_ids:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_package_ids_mismatch",
            "Supplied output_package_ids do not match the constructed source-directory hybrid package set.",
            http_status=409,
            details={"blocked_fields": ["output_package_ids"]},
        )
    if supplied_package_kinds != expected_package_kinds:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_package_kinds_mismatch",
            "Supplied package_kinds must match canonical_internal, user_facing, and review_facing in review order.",
            http_status=409,
            details={"blocked_fields": ["package_kinds"]},
        )
    if supplied_payload_hashes != expected_payload_hashes:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_payload_hashes_mismatch",
            "Supplied payload_hashes do not match the constructed source-directory hybrid package payload hashes.",
            http_status=409,
            details={"blocked_fields": ["payload_hashes"]},
        )

    package_review_state = PACKAGE_REVIEW_SUBMIT_STATE_BY_DECISION[operator_decision]
    submit_basis = {
        "schema_id": "layer3.source_directory_hybrid_context_packet_qualitative_analysis_package_review_submit_authority_basis.v1",
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "embedding_index_authority_hash": qualitative_analysis["embedding_index_authority_hash"],
        "lexical_context_packet_hash": qualitative_analysis["lexical_context_packet_hash"],
        "hybrid_context_packet_hash": qualitative_analysis["hybrid_context_packet_hash"],
        "qualitative_analysis_hash": expected_analysis_hash,
        "package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": expected_construction_basis_hash,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "operator_decision": operator_decision,
        "decision_notes": decision_notes or None,
        "package_review_state": package_review_state,
        "package_construction_source_gate": SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "source_shape": material_snapshot.source_shape,
    }
    submit_record_ref = _stable_id("l3-source-directory-hybrid-package-review-submit", submit_basis)
    existing_submit = reconciliation_summary.get("package_review_submit")
    if isinstance(existing_submit, dict):
        if str(existing_submit.get("submit_record_ref") or "") == submit_record_ref:
            return _package_review_submit_response(
                request_id=request_id,
                status="already_submitted",
                session=session,
                material_snapshot=material_snapshot,
                qualitative_analysis=qualitative_analysis,
                reconciliation=reconciliation,
                packages=packages,
                submit_state=existing_submit,
            )
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_already_recorded",
            "This source-directory hybrid package set already has a package-review submit decision.",
            http_status=409,
            details={"blocked_fields": ["operator_decision", "decision_notes"]},
        )

    handoff_prepare_enabled = package_review_state == PACKAGE_REVIEW_APPROVED_STATE
    submit_downstream_unavailable = (
        [item for item in PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE if item not in {"handoff", "export"}]
        if handoff_prepare_enabled
        else list(PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE)
    )
    submit_state = {
        "schema_id": PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
        "package_review_submit_schema_id": PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
        "client_request_id": request_id,
        "submit_record_ref": submit_record_ref,
        "authority_basis": submit_basis,
        "state": package_review_state,
        "package_review_state": package_review_state,
        "operator_decision": operator_decision,
        "decision_notes": decision_notes or None,
        "package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": expected_construction_basis_hash,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "payload_refs": None,
        "payload_refs_redacted": True,
        "package_construction_source_gate": SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "source_shape": material_snapshot.source_shape,
        "recorded_at": _server_time(),
        "package_review_submit_enabled": False,
        "handoff_enabled": handoff_prepare_enabled,
        "export_enabled": handoff_prepare_enabled,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "downstream_unavailable": submit_downstream_unavailable,
    }
    reconciliation.summary_json = {
        **reconciliation_summary,
        "source_directory_hybrid_context_qualitative_package_commit": {
            **commit_summary,
            "package_review_submit_enabled": False,
        },
        "package_review_submit": submit_state,
    }
    session.summary_json = {
        **_json_clone(session.summary_json or {}),
        "package_review_submit": {
            "schema_id": PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
            "package_review_submit_schema_id": PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
            "submit_record_ref": submit_record_ref,
            "state": package_review_state,
            "package_review_state": package_review_state,
            "operator_decision": operator_decision,
            "reconciliation_record_id": reconciliation_record_id,
            "output_package_ids": expected_package_ids,
            "package_kinds": expected_package_kinds,
            "payload_hashes": expected_payload_hashes,
            "payload_refs": None,
            "payload_refs_redacted": True,
            "package_construction_source_gate": SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
            "source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
            "source_shape": material_snapshot.source_shape,
            "package_review_submit_enabled": False,
            "handoff_enabled": handoff_prepare_enabled,
            "export_enabled": handoff_prepare_enabled,
            "downstream_unavailable": submit_downstream_unavailable,
        },
    }
    db.commit()

    return _package_review_submit_response(
        request_id=request_id,
        status="submitted",
        session=session,
        material_snapshot=material_snapshot,
        qualitative_analysis=qualitative_analysis,
        reconciliation=reconciliation,
        packages=packages,
        submit_state=submit_state,
    )


def source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_handoff_export_prepare_payload(payload)
    request_id = _require_handoff_field(fields, "client_request_id")
    operator_decision = str(fields.get("operator_decision") or "").strip()
    decision_notes = str(fields.get("decision_notes") or "").strip()
    if operator_decision not in HANDOFF_EXPORT_PREPARE_DECISIONS:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_decision_not_admitted",
            "operator_decision must be authorize_prepare, hold, decline, or blocked.",
            http_status=409,
            details={"field": "operator_decision"},
        )
    if operator_decision in HANDOFF_EXPORT_PREPARE_NOTE_REQUIRED_DECISIONS and not decision_notes:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_decision_notes_required",
            "decision_notes are required for hold, decline, or blocked handoff/export decisions.",
            details={"field": "decision_notes"},
        )
    if str(fields.get("handoff_target") or "").strip() != "internal_export_envelope":
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_target_not_admitted",
            "handoff_target must be internal_export_envelope for this tranche.",
            http_status=409,
            details={"blocked_fields": ["handoff_target"]},
        )
    if str(fields.get("export_mode") or "").strip() != "prepare_only":
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_mode_not_admitted",
            "export_mode must be prepare_only for this tranche.",
            http_status=409,
            details={"blocked_fields": ["export_mode"]},
        )
    if str(fields.get("package_review_state") or "").strip() != PACKAGE_REVIEW_APPROVED_STATE:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_requires_approved_package_review",
            "Handoff/export preparation requires package_review_state to be package_review_approved.",
            http_status=409,
            details={"blocked_fields": ["package_review_state"]},
        )

    qualitative_analysis = source_directory_hybrid_context_packet_qualitative_analysis(
        db,
        _qualitative_analysis_payload(fields),
    )
    expected_analysis_hash = str(qualitative_analysis["qualitative_analysis_hash"])
    if str(fields.get("qualitative_analysis_hash") or "") != expected_analysis_hash:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_qualitative_analysis_hash_mismatch",
            "Handoff/export prepare must reference the current server-recomputed hybrid qualitative-analysis hash.",
            http_status=409,
            details={"blocked_fields": ["qualitative_analysis_hash"]},
        )
    preview = qualitative_analysis["source_directory_hybrid_package_review_preview"]
    expected_preview_hash = str(preview["package_review_preview_hash"])
    if str(fields.get("source_directory_hybrid_package_review_preview_hash") or "") != expected_preview_hash:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_preview_hash_mismatch",
            "Handoff/export prepare must reference the current server-recomputed hybrid package-review preview hash.",
            http_status=409,
            details={"blocked_fields": ["source_directory_hybrid_package_review_preview_hash"]},
        )

    material_snapshot = _load_material_snapshot_for_handoff_export_prepare(
        db,
        material_snapshot_id=str(qualitative_analysis["material_snapshot_id"]),
        source_authority=preview["source_authority"],
    )
    session = _load_handoff_export_prepare_session(db, material_snapshot=material_snapshot)
    reconciliation_record_id = _require_handoff_field(fields, "reconciliation_record_id")
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session.session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if reconciliation is None:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_reconciliation_not_found",
            "No source-directory hybrid package reconciliation record exists for the supplied authority.",
            http_status=404,
            details={"reconciliation_record_id": reconciliation_record_id},
        )

    reconciliation_summary = _json_clone(reconciliation.summary_json or {})
    commit_summary = reconciliation_summary.get("source_directory_hybrid_context_qualitative_package_commit")
    if not isinstance(commit_summary, dict):
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_requires_package_commit",
            "Handoff/export prepare requires source-directory hybrid qualitative package-commit authority.",
            http_status=409,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    if str(reconciliation_summary.get("source_gate") or "") != SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_source_gate_mismatch",
            "Handoff/export prepare requires the source-directory hybrid package-construction source gate.",
            http_status=409,
            details={"blocked_fields": ["reconciliation_record_id"]},
        )
    submit_state = reconciliation_summary.get("package_review_submit")
    if not isinstance(submit_state, dict):
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_requires_package_review_submit",
            "Handoff/export prepare requires existing package-review submit authority.",
            http_status=409,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    supplied_submit_ref = _require_handoff_field(fields, "package_review_submit_record_ref")
    if str(submit_state.get("schema_id") or "") != PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_submit_schema_mismatch",
            "Stored package-review submit state does not match the admitted state schema.",
            http_status=409,
            details={"blocked_fields": ["package_review_submit_record_ref"]},
        )
    if str(submit_state.get("package_review_submit_schema_id") or "") != PACKAGE_REVIEW_SUBMIT_SCHEMA_ID:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_submit_contract_mismatch",
            "Stored package-review submit state does not match the source-directory hybrid submit contract.",
            http_status=409,
            details={"blocked_fields": ["package_review_submit_record_ref"]},
        )
    if str(submit_state.get("submit_record_ref") or "") != supplied_submit_ref:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_submit_ref_mismatch",
            "Supplied package_review_submit_record_ref does not match stored package-review submit authority.",
            http_status=409,
            details={"blocked_fields": ["package_review_submit_record_ref"]},
        )
    if str(submit_state.get("package_review_state") or "") != PACKAGE_REVIEW_APPROVED_STATE:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_submit_not_approved",
            "Handoff/export prepare requires stored package-review submit state to be approved.",
            http_status=409,
            details={"blocked_fields": ["package_review_submit_record_ref"]},
        )

    packages = _source_directory_hybrid_review_packages_for_handoff_export_prepare(
        db,
        session_id=session.session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    supplied_construction_basis_hash = _require_handoff_field(fields, "construction_basis_hash")
    expected_construction_basis_hash = str(
        commit_summary.get("construction_basis_hash")
        or next(
            (
                str((package.summary_json or {}).get("construction_basis_hash") or "")
                for package in packages
                if str((package.summary_json or {}).get("construction_basis_hash") or "")
            ),
            "",
        )
        or commit_summary.get("authority_basis_hash")
        or ""
    )
    submit_authority_basis = submit_state.get("authority_basis")
    if not isinstance(submit_authority_basis, dict):
        submit_authority_basis = {}
    mismatches = [
        field
        for field, expected in {
            "package_review_preview_hash": expected_preview_hash,
            "qualitative_analysis_hash": expected_analysis_hash,
            "hybrid_context_packet_hash": qualitative_analysis["hybrid_context_packet_hash"],
            "embedding_index_authority_hash": qualitative_analysis["embedding_index_authority_hash"],
            "construction_basis_hash": expected_construction_basis_hash,
        }.items()
        if str(submit_state.get(field) or submit_authority_basis.get(field) or "") != str(expected)
    ]
    if supplied_construction_basis_hash != expected_construction_basis_hash:
        mismatches.append("construction_basis_hash")
    if mismatches:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_authority_mismatch",
            "Stored package-review submit provenance does not match the supplied handoff/export prepare authority.",
            http_status=409,
            details={"blocked_fields": sorted(set(mismatches))},
        )

    supplied_package_ids = _handoff_string_list(fields.get("output_package_ids"), field="output_package_ids")
    supplied_package_kinds = _handoff_string_list(fields.get("package_kinds"), field="package_kinds")
    supplied_payload_hashes = _handoff_string_list(fields.get("payload_hashes"), field="payload_hashes")
    expected_package_ids = [package.output_package_id for package in packages]
    expected_package_kinds = [package.package_kind for package in packages]
    expected_payload_hashes = [package.payload_hash for package in packages]
    if supplied_package_ids != expected_package_ids:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_package_ids_mismatch",
            "Supplied output_package_ids do not match the constructed source-directory hybrid package set.",
            http_status=409,
            details={"blocked_fields": ["output_package_ids"]},
        )
    if supplied_package_kinds != expected_package_kinds:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_package_kinds_mismatch",
            "Supplied package_kinds must match canonical_internal, user_facing, and review_facing in review order.",
            http_status=409,
            details={"blocked_fields": ["package_kinds"]},
        )
    if supplied_payload_hashes != expected_payload_hashes:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_payload_hashes_mismatch",
            "Supplied payload_hashes do not match the constructed source-directory hybrid package payload hashes.",
            http_status=409,
            details={"blocked_fields": ["payload_hashes"]},
        )

    handoff_export_state = HANDOFF_EXPORT_PREPARE_STATE_BY_DECISION[operator_decision]
    prepare_basis = {
        "schema_id": "layer3.source_directory_hybrid_context_packet_qualitative_analysis_handoff_export_prepare_authority_basis.v1",
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "embedding_index_authority_hash": qualitative_analysis["embedding_index_authority_hash"],
        "lexical_context_packet_hash": qualitative_analysis["lexical_context_packet_hash"],
        "hybrid_context_packet_hash": qualitative_analysis["hybrid_context_packet_hash"],
        "qualitative_analysis_hash": expected_analysis_hash,
        "package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": expected_construction_basis_hash,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "package_review_submit_record_ref": supplied_submit_ref,
        "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "operator_decision": operator_decision,
        "decision_notes": decision_notes or None,
        "handoff_export_state": handoff_export_state,
        "package_review_submit_source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "package_construction_source_gate": SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": HANDOFF_EXPORT_PREPARE_SOURCE_GATE,
        "source_shape": material_snapshot.source_shape,
    }
    prepare_record_ref = _stable_id("l3-source-directory-hybrid-handoff-export-prepare", prepare_basis)
    envelope = {
        "schema_id": "layer3.source_directory_hybrid_context_packet_internal_export_envelope.v1",
        "envelope_ref": _stable_id(
            "l3-source-directory-hybrid-internal-export-envelope",
            {
                "prepare_record_ref": prepare_record_ref,
                "package_review_submit_record_ref": supplied_submit_ref,
                "output_package_ids": expected_package_ids,
                "payload_hashes": expected_payload_hashes,
                "hybrid_context_packet_hash": qualitative_analysis["hybrid_context_packet_hash"],
                "embedding_index_authority_hash": qualitative_analysis["embedding_index_authority_hash"],
            },
        ),
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "payload_refs": None,
        "payload_refs_redacted": True,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
    }
    existing_prepare = reconciliation_summary.get("handoff_export_prepare")
    if isinstance(existing_prepare, dict):
        if str(existing_prepare.get("prepare_record_ref") or "") == prepare_record_ref:
            return _handoff_export_prepare_response(
                request_id=request_id,
                status="already_prepared",
                session=session,
                material_snapshot=material_snapshot,
                qualitative_analysis=qualitative_analysis,
                reconciliation=reconciliation,
                packages=packages,
                prepare_state=existing_prepare,
            )
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_already_recorded",
            "This source-directory hybrid package set already has a handoff/export prepare decision.",
            http_status=409,
            details={"blocked_fields": ["operator_decision", "decision_notes"]},
        )

    prepare_state = {
        "schema_id": HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
        "handoff_export_prepare_schema_id": HANDOFF_EXPORT_PREPARE_SCHEMA_ID,
        "client_request_id": request_id,
        "prepare_record_ref": prepare_record_ref,
        "authority_basis": prepare_basis,
        "state": handoff_export_state,
        "handoff_export_state": handoff_export_state,
        "operator_decision": operator_decision,
        "decision_notes": decision_notes or None,
        "package_review_submit_record_ref": supplied_submit_ref,
        "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
        "package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": expected_construction_basis_hash,
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "payload_refs": None,
        "payload_refs_redacted": True,
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "handoff_export_envelope": envelope,
        "package_review_submit_source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "package_construction_source_gate": SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": HANDOFF_EXPORT_PREPARE_SOURCE_GATE,
        "source_shape": material_snapshot.source_shape,
        "recorded_at": _server_time(),
        "handoff_enabled": False,
        "export_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
    }
    reconciliation.summary_json = {
        **reconciliation_summary,
        "handoff_export_prepare": prepare_state,
    }
    session.summary_json = {
        **_json_clone(session.summary_json or {}),
        "handoff_export_prepare": {
            "schema_id": HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
            "handoff_export_prepare_schema_id": HANDOFF_EXPORT_PREPARE_SCHEMA_ID,
            "prepare_record_ref": prepare_record_ref,
            "state": handoff_export_state,
            "handoff_export_state": handoff_export_state,
            "operator_decision": operator_decision,
            "reconciliation_record_id": reconciliation_record_id,
            "package_review_submit_record_ref": supplied_submit_ref,
            "output_package_ids": expected_package_ids,
            "package_kinds": expected_package_kinds,
            "payload_hashes": expected_payload_hashes,
            "payload_refs": None,
            "payload_refs_redacted": True,
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "package_review_submit_source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
            "package_construction_source_gate": SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
            "source_gate": HANDOFF_EXPORT_PREPARE_SOURCE_GATE,
            "source_shape": material_snapshot.source_shape,
            "handoff_enabled": False,
            "export_enabled": False,
            "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        },
    }
    db.commit()

    return _handoff_export_prepare_response(
        request_id=request_id,
        status=HANDOFF_EXPORT_PREPARE_STATUS_BY_DECISION[operator_decision],
        session=session,
        material_snapshot=material_snapshot,
        qualitative_analysis=qualitative_analysis,
        reconciliation=reconciliation,
        packages=packages,
        prepare_state=prepare_state,
    )


def source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_external_export_download_prepare_payload(payload)
    request_id = _require_external_export_download_prepare_field(fields, "client_request_id")
    if str(fields.get("operator_decision") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_decision_not_admitted",
            "operator_decision must be prepare_source_directory_hybrid_external_export_download.",
            http_status=409,
            details={"field": "operator_decision"},
        )
    if str(fields.get("external_export_download_target") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_TARGET:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_target_not_admitted",
            "external_export_download_target must be source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference.",
            http_status=409,
            details={"blocked_fields": ["external_export_download_target"]},
        )
    if str(fields.get("download_mode") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_MODE:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_mode_not_admitted",
            "download_mode must be reference_only_prepare for this tranche.",
            http_status=409,
            details={"blocked_fields": ["download_mode"]},
        )
    if str(fields.get("handoff_export_state") or "").strip() != HANDOFF_EXPORT_PREPARED_STATE:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_requires_prepared_handoff",
            "External export/download readiness requires handoff_export_state to be handoff_export_prepared.",
            http_status=409,
            details={"blocked_fields": ["handoff_export_state"]},
        )

    qualitative_analysis = source_directory_hybrid_context_packet_qualitative_analysis(
        db,
        _qualitative_analysis_payload(fields),
    )
    expected_analysis_hash = str(qualitative_analysis["qualitative_analysis_hash"])
    if str(fields.get("qualitative_analysis_hash") or "") != expected_analysis_hash:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_qualitative_analysis_hash_mismatch",
            "External export/download prepare must reference the current server-recomputed hybrid qualitative-analysis hash.",
            http_status=409,
            details={"blocked_fields": ["qualitative_analysis_hash"]},
        )
    preview = qualitative_analysis["source_directory_hybrid_package_review_preview"]
    expected_preview_hash = str(preview["package_review_preview_hash"])
    if str(fields.get("source_directory_hybrid_package_review_preview_hash") or "") != expected_preview_hash:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_preview_hash_mismatch",
            "External export/download prepare must reference the current server-recomputed hybrid package-review preview hash.",
            http_status=409,
            details={"blocked_fields": ["source_directory_hybrid_package_review_preview_hash"]},
        )

    material_snapshot = _load_material_snapshot_for_external_export_download_prepare(
        db,
        material_snapshot_id=str(qualitative_analysis["material_snapshot_id"]),
        source_authority=preview["source_authority"],
    )
    session = _load_external_export_download_prepare_session(db, material_snapshot=material_snapshot)
    reconciliation_record_id = _require_external_export_download_prepare_field(
        fields,
        "reconciliation_record_id",
    )
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session.session_id,
        )
        .with_for_update()
        .one_or_none()
    )
    if reconciliation is None:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_reconciliation_not_found",
            "No source-directory hybrid package reconciliation record exists for the supplied authority.",
            http_status=404,
            details={"reconciliation_record_id": reconciliation_record_id},
        )

    reconciliation_summary = _json_clone(reconciliation.summary_json or {})
    prepare_state = reconciliation_summary.get("handoff_export_prepare")
    if not isinstance(prepare_state, dict):
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_requires_handoff_prepare",
            "External export/download readiness requires existing source-directory hybrid handoff/export prepare authority.",
            http_status=409,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    supplied_prepare_ref = _require_external_export_download_prepare_field(fields, "prepare_record_ref")
    supplied_envelope_ref = _require_external_export_download_prepare_field(
        fields,
        "handoff_export_envelope_ref",
    )
    if str(prepare_state.get("schema_id") or "") != HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_state_schema_mismatch",
            "Stored handoff/export prepare state does not match the admitted state schema.",
            http_status=409,
            details={"blocked_fields": ["prepare_record_ref"]},
        )
    if str(prepare_state.get("handoff_export_prepare_schema_id") or "") != HANDOFF_EXPORT_PREPARE_SCHEMA_ID:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_contract_mismatch",
            "Stored handoff/export prepare state does not match the source-directory hybrid prepare contract.",
            http_status=409,
            details={"blocked_fields": ["prepare_record_ref"]},
        )
    envelope = prepare_state.get("handoff_export_envelope")
    if not isinstance(envelope, dict):
        envelope = {}
    prepare_authority_basis = prepare_state.get("authority_basis")
    if not isinstance(prepare_authority_basis, dict):
        prepare_authority_basis = {}
    mismatches = [
        field
        for field, expected in {
            "prepare_record_ref": supplied_prepare_ref,
            "package_review_submit_record_ref": str(fields.get("package_review_submit_record_ref") or ""),
            "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
            "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "package_review_preview_hash": expected_preview_hash,
            "construction_basis_hash": str(fields.get("construction_basis_hash") or ""),
            "hybrid_context_packet_hash": qualitative_analysis["hybrid_context_packet_hash"],
            "embedding_index_authority_hash": qualitative_analysis["embedding_index_authority_hash"],
        }.items()
        if str(prepare_state.get(field) or prepare_authority_basis.get(field) or "") != str(expected)
    ]
    if str(envelope.get("envelope_ref") or "") != supplied_envelope_ref:
        mismatches.append("handoff_export_envelope_ref")
    if mismatches:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_authority_mismatch",
            "Stored source-directory hybrid handoff/export prepare authority does not match the supplied readiness basis.",
            http_status=409,
            details={"blocked_fields": sorted(set(mismatches))},
        )

    packages = _source_directory_hybrid_review_packages_for_external_export_download_prepare(
        db,
        session_id=session.session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    supplied_package_ids = _external_export_download_prepare_string_list(
        fields.get("output_package_ids"),
        field="output_package_ids",
    )
    supplied_package_kinds = _external_export_download_prepare_string_list(
        fields.get("package_kinds"),
        field="package_kinds",
    )
    supplied_payload_hashes = _external_export_download_prepare_string_list(
        fields.get("payload_hashes"),
        field="payload_hashes",
    )
    expected_package_ids = [package.output_package_id for package in packages]
    expected_package_kinds = [package.package_kind for package in packages]
    expected_payload_hashes = [package.payload_hash for package in packages]
    list_mismatches = []
    if supplied_package_ids != expected_package_ids:
        list_mismatches.append("output_package_ids")
    if supplied_package_kinds != expected_package_kinds:
        list_mismatches.append("package_kinds")
    if supplied_payload_hashes != expected_payload_hashes:
        list_mismatches.append("payload_hashes")
    if list_mismatches:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_package_authority_mismatch",
            "Supplied package identity does not match the constructed source-directory hybrid package set.",
            http_status=409,
            details={"blocked_fields": list_mismatches},
        )

    readiness_basis = {
        "schema_id": "layer3.source_directory_hybrid_context_packet_external_export_download_prepare_authority_basis.v1",
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "embedding_index_authority_hash": qualitative_analysis["embedding_index_authority_hash"],
        "lexical_context_packet_hash": qualitative_analysis["lexical_context_packet_hash"],
        "hybrid_context_packet_hash": qualitative_analysis["hybrid_context_packet_hash"],
        "qualitative_analysis_hash": expected_analysis_hash,
        "package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": str(fields.get("construction_basis_hash") or ""),
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "package_review_submit_record_ref": str(fields.get("package_review_submit_record_ref") or ""),
        "prepare_record_ref": supplied_prepare_ref,
        "handoff_export_envelope_ref": supplied_envelope_ref,
        "external_export_download_target": EXTERNAL_EXPORT_DOWNLOAD_TARGET,
        "download_mode": EXTERNAL_EXPORT_DOWNLOAD_MODE,
        "operator_decision": EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION,
        "source_gate": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_GATE,
    }
    record_ref = _stable_id("l3-source-directory-hybrid-external-export-download-prepare", readiness_basis)
    existing_readiness = reconciliation_summary.get("external_export_download_prepare")
    if isinstance(existing_readiness, dict):
        if str(existing_readiness.get("external_export_download_record_ref") or "") == record_ref:
            return _external_export_download_prepare_response(
                request_id=request_id,
                status="already_prepared",
                session=session,
                material_snapshot=material_snapshot,
                qualitative_analysis=qualitative_analysis,
                reconciliation=reconciliation,
                packages=packages,
                readiness_state=existing_readiness,
            )
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_already_recorded",
            "This source-directory hybrid package set already has external export/download readiness.",
            http_status=409,
            details={"blocked_fields": ["external_export_download_record_ref"]},
        )

    descriptor_ref = _stable_id(
        "l3-source-directory-hybrid-external-export-download-descriptor",
        {
            **readiness_basis,
            "schema_id": "layer3.source_directory_hybrid_external_export_download_descriptor_authority.v1",
        },
    )
    descriptor = {
        "schema_id": "layer3.source_directory_hybrid_external_export_download_descriptor.v1",
        "descriptor_ref": descriptor_ref,
        "session_id": session.session_id,
        "reconciliation_record_id": reconciliation_record_id,
        "prepare_record_ref": supplied_prepare_ref,
        "handoff_export_envelope_ref": supplied_envelope_ref,
        "external_export_download_target": EXTERNAL_EXPORT_DOWNLOAD_TARGET,
        "download_mode": EXTERNAL_EXPORT_DOWNLOAD_MODE,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "payload_refs": None,
        "payload_refs_redacted": True,
        "browser_download_enabled": False,
        "same_origin_delivery_enabled": False,
        "provider_public_url_enabled": False,
        "connector_dispatch_enabled": False,
        "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_DOWNSTREAM_UNAVAILABLE),
    }
    readiness_state = {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
        "external_export_download_prepare_schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
        "client_request_id": request_id,
        "external_export_download_record_ref": record_ref,
        "export_download_descriptor_ref": descriptor_ref,
        "external_export_download_descriptor": descriptor,
        "authority_basis": readiness_basis,
        "external_export_download_state": EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE,
        "external_export_download_target": EXTERNAL_EXPORT_DOWNLOAD_TARGET,
        "download_mode": EXTERNAL_EXPORT_DOWNLOAD_MODE,
        "operator_decision": EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION,
        "decision_notes": str(fields.get("decision_notes") or "").strip() or None,
        "reconciliation_record_id": reconciliation_record_id,
        "package_review_submit_record_ref": str(fields.get("package_review_submit_record_ref") or ""),
        "package_review_state": PACKAGE_REVIEW_APPROVED_STATE,
        "package_review_preview_hash": expected_preview_hash,
        "construction_basis_hash": str(fields.get("construction_basis_hash") or ""),
        "prepare_record_ref": supplied_prepare_ref,
        "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
        "handoff_export_envelope_ref": supplied_envelope_ref,
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_hashes": expected_payload_hashes,
        "payload_refs": None,
        "payload_refs_redacted": True,
        "source_gate": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_GATE,
        "package_review_submit_source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "package_construction_source_gate": SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_shape": material_snapshot.source_shape,
        "recorded_at": _server_time(),
        "same_origin_delivery_enabled": False,
        "browser_download_enabled": False,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "connector_dispatch_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_DOWNSTREAM_UNAVAILABLE),
    }
    reconciliation.summary_json = {
        **reconciliation_summary,
        "external_export_download_prepare": readiness_state,
    }
    session.summary_json = {
        **_json_clone(session.summary_json or {}),
        "external_export_download_prepare": {
            "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
            "external_export_download_prepare_schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
            "external_export_download_record_ref": record_ref,
            "export_download_descriptor_ref": descriptor_ref,
            "external_export_download_state": EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE,
            "reconciliation_record_id": reconciliation_record_id,
            "prepare_record_ref": supplied_prepare_ref,
            "payload_refs": None,
            "payload_refs_redacted": True,
            "source_gate": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_GATE,
            "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_DOWNSTREAM_UNAVAILABLE),
        },
    }
    db.commit()

    return _external_export_download_prepare_response(
        request_id=request_id,
        status="prepared",
        session=session,
        material_snapshot=material_snapshot,
        qualitative_analysis=qualitative_analysis,
        reconciliation=reconciliation,
        packages=packages,
        readiness_state=readiness_state,
    )


def source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver(
    db: Session,
    payload: Mapping[str, Any],
) -> ExternalExportDownloadDelivery:
    fields = _normalise_external_export_download_delivery_payload(payload)
    request_id = _require_external_export_download_delivery_field(fields, "client_request_id")
    if str(fields.get("operator_decision") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_decision_not_admitted",
            "operator_decision must be deliver_source_directory_hybrid_external_export_download.",
            http_status=409,
            details={"field": "operator_decision"},
        )
    if str(fields.get("external_export_download_target") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_TARGET:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_target_not_admitted",
            "external_export_download_target must be source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference.",
            http_status=409,
            details={"blocked_fields": ["external_export_download_target"]},
        )
    if str(fields.get("download_mode") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_MODE:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_download_mode_not_admitted",
            "download_mode must be reference_only_prepare for this tranche.",
            http_status=409,
            details={"blocked_fields": ["download_mode"]},
        )
    if str(fields.get("delivery_mode") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE_VALUE:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_mode_not_admitted",
            "delivery_mode must be same_origin_artifact_stream.",
            http_status=409,
            details={"blocked_fields": ["delivery_mode"]},
        )
    if str(fields.get("external_export_download_state") or "").strip() != EXTERNAL_EXPORT_DOWNLOAD_PREPARED_STATE:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_requires_prepared_state",
            "Source-directory hybrid external export/download delivery requires external_export_download_prepared state.",
            http_status=409,
            details={"blocked_fields": ["external_export_download_state"]},
        )

    reconciliation_record_id = _require_external_export_download_delivery_field(
        fields,
        "reconciliation_record_id",
    )
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_reconciliation_not_found",
            "No source-directory hybrid package reconciliation record exists for the supplied delivery authority.",
            http_status=404,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    existing_readiness = _json_clone(reconciliation.summary_json or {}).get(
        "external_export_download_prepare"
    )
    if not isinstance(existing_readiness, dict):
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_requires_prepare",
            "Delivery requires existing source-directory hybrid external export/download prepare authority.",
            http_status=409,
            details={"reconciliation_record_id": reconciliation_record_id},
        )

    prepare_fields = {
        field: fields[field]
        for field in sorted(_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUIRED_FIELDS | _OPTIONAL_FIELDS)
        if field in fields
    }
    if "decision_notes" in fields:
        prepare_fields["decision_notes"] = fields["decision_notes"]
    prepare_fields["operator_decision"] = EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION
    try:
        prepare_response = (
            source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_prepare(
                db,
                prepare_fields,
            )
        )
    except SourceDirectoryHybridExternalExportDownloadPrepareError as exc:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            exc.code.replace("prepare", "delivery"),
            exc.message.replace("prepare", "delivery"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc

    authority_mismatches = [
        field
        for field in (
            "external_export_download_record_ref",
            "export_download_descriptor_ref",
            "external_export_download_state",
        )
        if str(fields.get(field) or "") != str(prepare_response.get(field) or "")
    ]
    if authority_mismatches:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_authority_mismatch",
            "Prepared source-directory hybrid external export/download authority does not match the delivery basis.",
            http_status=409,
            details={"blocked_fields": authority_mismatches},
        )

    packages = _source_directory_hybrid_review_packages_for_external_export_download_delivery(
        db,
        session_id=str(prepare_response["session_id"]),
        reconciliation_record_id=reconciliation_record_id,
    )
    selected_package_id = _require_external_export_download_delivery_field(fields, "output_package_id")
    selected_package = next(
        (package for package in packages if package.output_package_id == selected_package_id),
        None,
    )
    if selected_package is None:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_package_not_found",
            "Requested source-directory hybrid package is not part of the prepared package set.",
            http_status=404,
            details={"blocked_fields": ["output_package_id"]},
        )
    if selected_package.package_kind != str(fields.get("package_kind") or ""):
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_package_kind_mismatch",
            "Requested source-directory hybrid package kind does not match the selected package row.",
            http_status=409,
            details={"blocked_fields": ["package_kind"]},
        )
    if selected_package.payload_hash != str(fields.get("package_payload_hash") or ""):
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_payload_hash_mismatch",
            "Requested source-directory hybrid package payload hash does not match the selected package row.",
            http_status=409,
            details={"blocked_fields": ["package_payload_hash"]},
        )

    artifact_path = _source_directory_hybrid_package_payload_path(selected_package)
    artifact_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if artifact_hash != selected_package.payload_hash:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_artifact_hash_mismatch",
            "Stored source-directory hybrid package artifact hash does not match the selected package row.",
            http_status=409,
            details={"blocked_fields": ["output_package_id", "package_payload_hash"]},
        )

    authority = {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "mode": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE,
        "delivery_state": EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE,
        "source_gate": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SOURCE_GATE,
        "session_id": str(prepare_response["session_id"]),
        "selection_manifest_id": str(prepare_response["selection_manifest_id"]),
        "material_snapshot_id": str(prepare_response["material_snapshot_id"]),
        "reconciliation_record_id": reconciliation_record_id,
        "external_export_download_record_ref": str(prepare_response["external_export_download_record_ref"]),
        "export_download_descriptor_ref": str(prepare_response["export_download_descriptor_ref"]),
        "output_package_id": selected_package.output_package_id,
        "package_kind": selected_package.package_kind,
        "package_payload_hash": selected_package.payload_hash,
        "payload_ref_redacted": True,
        "same_origin_delivery_enabled": True,
        "browser_managed_same_origin_attachment_enabled": True,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "connector_dispatch_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "package_payload_rewrite_enabled": False,
        "source_package_row_mutation_enabled": False,
    }
    db.rollback()
    return ExternalExportDownloadDelivery(
        artifact_path=artifact_path,
        media_type="application/json",
        filename=_source_directory_hybrid_delivery_filename(
            session_id=str(prepare_response["session_id"]),
            package_kind=selected_package.package_kind,
        ),
        headers={
            "X-Layer3-Schema-Id": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID,
            "X-Layer3-Delivery-State": EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE,
            "X-Layer3-Source-Artifact-Hash": artifact_hash,
            "X-Layer3-External-Export-Download-Record-Ref": str(
                prepare_response["external_export_download_record_ref"]
            ),
            "X-Layer3-Source-Directory-Hybrid-Package-Kind": selected_package.package_kind,
        },
        authority=authority,
    )


def source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivery_status(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    delivery = source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver(
        db,
        payload,
    )
    authority = _json_clone(delivery.authority)
    request_id = str(authority.get("request_id") or "")
    return {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_MODE,
        "status": "ready",
        "delivery_status": "source_directory_hybrid_external_export_download_delivery_ready",
        "delivery_available": True,
        "delivery_streaming_performed": False,
        "delivery_state": authority.get("delivery_state"),
        "source_gate": EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_SOURCE_GATE,
        "validated_delivery_source_gate": authority.get("source_gate"),
        "external_export_download_record_ref": authority.get("external_export_download_record_ref"),
        "export_download_descriptor_ref": authority.get("export_download_descriptor_ref"),
        "output_package_id": authority.get("output_package_id"),
        "package_kind": authority.get("package_kind"),
        "package_payload_hash": authority.get("package_payload_hash"),
        "payload_ref_redacted": True,
        "raw_local_path_exposed": False,
        "same_origin_delivery_enabled": True,
        "browser_managed_same_origin_attachment_enabled": True,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "connector_dispatch_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "package_payload_rewrite_enabled": False,
        "source_package_row_mutation_enabled": False,
        "delivery_headers": dict(delivery.headers),
        "delivery_authority": authority,
        "next_allowed_actions": [EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION],
    }


def source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_prepare(
    db: Session,
    payload: Mapping[str, Any],
    *,
    fake_provider: ProviderPrivateSignedUrlFakeProvider | None = None,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    fields = _normalise_source_directory_provider_private_signed_url_payload(payload)
    request_id = _source_directory_provider_private_field(fields, "client_request_id")
    if (
        str(fields.get("operator_decision") or "").strip()
        != SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_OPERATOR_DECISION
    ):
        raise SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
            "source_directory_hybrid_provider_private_signed_url_decision_not_admitted",
            "operator_decision must be prepare_source_directory_hybrid_provider_private_signed_url.",
            http_status=409,
            details={"blocked_fields": ["operator_decision"]},
        )
    if str(fields.get("delivery_mode") or "").strip() != PROVIDER_PRIVATE_SIGNED_URL_DELIVERY_MODE:
        raise SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
            "source_directory_hybrid_provider_private_signed_url_delivery_mode_not_admitted",
            "delivery_mode must be provider_private_signed_url.",
            http_status=409,
            details={"blocked_fields": ["delivery_mode"]},
        )

    ttl_seconds = _source_directory_provider_private_ttl_seconds(fields)
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    delivery_payload = _source_directory_provider_private_delivery_payload(db, fields)
    try:
        delivery = source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver(
            db,
            delivery_payload,
        )
    except SourceDirectoryHybridExternalExportDownloadDeliveryError as exc:
        raise SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
            exc.code,
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc

    authority = _json_clone(delivery.authority)
    artifact_path = Path(delivery.artifact_path)
    source_artifact_hash = str(authority.get("package_payload_hash") or "").strip().lower()
    source_artifact_size_bytes = artifact_path.stat().st_size
    authority_basis = {
        "session_id": str(authority.get("session_id") or "").strip(),
        "reconciliation_record_id": str(authority.get("reconciliation_record_id") or "").strip(),
        "source_artifact_ref": str(artifact_path),
        "source_artifact_hash": source_artifact_hash,
        "source_artifact_size_bytes": source_artifact_size_bytes,
        "external_export_download_record_ref": str(
            authority.get("external_export_download_record_ref") or ""
        ).strip(),
        "export_download_descriptor_ref": str(authority.get("export_download_descriptor_ref") or "").strip(),
    }
    provider = fake_provider or ProviderPrivateSignedUrlFakeProvider()
    try:
        fake_receipt = provider.prepare(
            ProviderPrivateSignedUrlPrepareRequest(
                client_request_id=request_id,
                authority=ProviderArtifactAuthority(
                    source_artifact_ref=authority_basis["source_artifact_ref"],
                    source_artifact_hash=authority_basis["source_artifact_hash"],
                    source_artifact_size_bytes=authority_basis["source_artifact_size_bytes"],
                    external_export_download_record_ref=authority_basis[
                        "external_export_download_record_ref"
                    ],
                    export_download_descriptor_ref=authority_basis["export_download_descriptor_ref"],
                ),
                recipient_scope=_source_directory_provider_private_field(fields, "recipient_scope"),
                requested_ttl_seconds=ttl_seconds,
                now_epoch=SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_FIXED_FAKE_PROVIDER_EPOCH,
            )
        )
    except ProviderPrivateSignedUrlError as exc:
        raise _source_directory_provider_private_fake_provider_error(exc) from exc

    try:
        durable_state = record_prepared_provider_private_signed_url_receipt(
            db,
            request_id=request_id,
            client_request_id=request_id,
            authority_basis=authority_basis,
            recipient_scope=_source_directory_provider_private_field(fields, "recipient_scope"),
            requested_ttl_seconds=ttl_seconds,
            now_epoch=effective_now,
            provider_private_signed_url_token=fake_receipt.token_for_test,
        )
    except ProviderPrivateSignedUrlStateError as exc:
        raise _source_directory_provider_private_state_error(exc) from exc

    receipt = db.get(
        L3ProviderPrivateSignedUrlReceipt,
        durable_state.provider_private_signed_url_receipt_id,
    )
    if receipt is None:
        raise SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
            "source_directory_hybrid_provider_private_signed_url_receipt_missing_after_prepare",
            "Provider-private signed URL durable receipt was not readable after source-directory prepare.",
            http_status=409,
            details={"blocked_fields": ["provider_signed_url_receipt_id"]},
        )
    provider_authority = db.get(
        L3ProviderPrivateSignedUrlObjectAuthority,
        receipt.provider_private_signed_url_object_authority_id,
    )
    audit = db.get(
        L3ProviderPrivateSignedUrlAuditEvent,
        durable_state.provider_private_signed_url_audit_event_id,
    )
    if provider_authority is None:
        raise SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
            "source_directory_hybrid_provider_private_signed_url_authority_missing_after_prepare",
            "Provider-private signed URL durable authority was not readable after source-directory prepare.",
            http_status=409,
            details={"blocked_fields": ["provider_private_signed_url_object_authority_id"]},
        )

    expires_at_epoch = _source_directory_provider_private_datetime_epoch(
        receipt.provider_private_signed_url_expires_at
    )
    state = _source_directory_provider_private_state(receipt, now_epoch=effective_now)
    return {
        "schema_id": SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_PREPARE_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "prepared",
        "mode": SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_PREPARE_MODE,
        "session_id": provider_authority.session_id,
        "reconciliation_record_id": provider_authority.reconciliation_record_id,
        "external_export_download_record_ref": provider_authority.external_export_download_record_ref,
        "export_download_descriptor_ref": provider_authority.export_download_descriptor_ref,
        "output_package_id": authority.get("output_package_id"),
        "package_kind": authority.get("package_kind"),
        "package_payload_hash": authority.get("package_payload_hash"),
        "provider_signed_url_receipt_id": receipt.provider_private_signed_url_receipt_id,
        "provider_private_signed_url_object_authority_id": (
            receipt.provider_private_signed_url_object_authority_id
        ),
        "provider_signed_url_state": state,
        "delivery_mode": PROVIDER_PRIVATE_SIGNED_URL_DELIVERY_MODE,
        "provider_url_redacted": PROVIDER_PRIVATE_SIGNED_URL_REDACTED_MARKER,
        "provider_url_expires_at": _source_directory_provider_private_epoch_iso(expires_at_epoch),
        "provider_url_expires_in_seconds": max(0, expires_at_epoch - effective_now),
        "provider_url_replay_policy": receipt.provider_private_signed_url_replay_policy,
        "provider_url_revocation_supported": True,
        "provider_url_use_count": receipt.provider_private_signed_url_use_count,
        "provider_url_max_use_count": receipt.provider_private_signed_url_max_use_count,
        "provider_url_revoked": (
            receipt.provider_private_signed_url_state == "provider_private_signed_url_revoked"
        ),
        "source_artifact_ref": INTERNAL_ARTIFACT_REF_PLACEHOLDER,
        "source_artifact_hash": provider_authority.source_artifact_hash,
        "source_artifact_size_bytes": provider_authority.source_artifact_size_bytes,
        "source_directory_delivery_authority": authority,
        "audit_receipt": _source_directory_provider_private_audit_receipt(
            receipt=receipt,
            authority=provider_authority,
            audit=audit,
        ),
        "authority_rail": {
            "provider_authority": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
            "artifact_authority": "source_directory_hybrid_external_export_download_delivery_authority",
            "durable_state_authority": True,
            "provider_url_secret_redacted": True,
            "provider_network_enabled": False,
            "provider_object_write_enabled": False,
            "connector_dispatch_enabled": False,
            "destination_write_enabled": False,
            "public_url_enabled": False,
            "same_origin_delivery_changed": False,
        },
        "source_directory_provider_private_signed_url_enabled": True,
        "provider_private_signed_url_enabled": True,
        "provider_public_url_prepare_enabled": True,
        "same_origin_delivery_changed": False,
        "raw_local_path_exposed": False,
        "raw_provider_url_exposed": False,
        "raw_provider_private_signed_url_token_exposed": False,
        "provider_network_enabled": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_write_enabled": False,
        "package_mutation_enabled": False,
        "source_expansion_enabled": False,
        "frontend_durable_authority_enabled": False,
        "next_allowed_actions": [
            "prepare_provider_public_url",
            "inspect_provider_private_signed_url_status",
            "revoke_provider_private_signed_url",
        ],
        "next_state": state,
    }


def source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_use(
    db: Session,
    payload: Mapping[str, Any],
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    fields = _normalise_source_directory_provider_private_signed_url_use_payload(payload)
    request_id = _source_directory_provider_private_use_field(fields, "client_request_id")
    if (
        str(fields.get("operator_decision") or "").strip()
        != SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_OPERATOR_DECISION
    ):
        raise SourceDirectoryHybridProviderPrivateSignedUrlUseError(
            "source_directory_hybrid_provider_private_signed_url_use_decision_not_admitted",
            "operator_decision must be use_source_directory_hybrid_provider_private_signed_url.",
            http_status=409,
            details={"blocked_fields": ["operator_decision"]},
        )
    if str(fields.get("delivery_mode") or "").strip() != PROVIDER_PRIVATE_SIGNED_URL_DELIVERY_MODE:
        raise SourceDirectoryHybridProviderPrivateSignedUrlUseError(
            "source_directory_hybrid_provider_private_signed_url_use_delivery_mode_not_admitted",
            "delivery_mode must be provider_private_signed_url.",
            http_status=409,
            details={"blocked_fields": ["delivery_mode"]},
        )

    effective_now = int(time.time() if now_epoch is None else now_epoch)
    delivery_payload = _source_directory_provider_private_use_delivery_payload(db, fields)
    try:
        delivery = source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver(
            db,
            delivery_payload,
        )
    except SourceDirectoryHybridExternalExportDownloadDeliveryError as exc:
        raise SourceDirectoryHybridProviderPrivateSignedUrlUseError(
            exc.code,
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc

    authority = _json_clone(delivery.authority)
    artifact_path = Path(delivery.artifact_path)
    authority_basis = {
        "session_id": str(authority.get("session_id") or "").strip(),
        "reconciliation_record_id": str(authority.get("reconciliation_record_id") or "").strip(),
        "source_artifact_ref": str(artifact_path),
        "source_artifact_hash": str(authority.get("package_payload_hash") or "").strip().lower(),
        "source_artifact_size_bytes": artifact_path.stat().st_size,
        "external_export_download_record_ref": str(
            authority.get("external_export_download_record_ref") or ""
        ).strip(),
        "export_download_descriptor_ref": str(authority.get("export_download_descriptor_ref") or "").strip(),
    }
    receipt_id = _source_directory_provider_private_use_field(fields, "provider_signed_url_receipt_id")
    try:
        durable_state = record_server_owned_provider_private_signed_url_receipt_use(
            db,
            provider_private_signed_url_receipt_id=receipt_id,
            authority_basis=authority_basis,
            now_epoch=effective_now,
            request_id=request_id,
        )
    except ProviderPrivateSignedUrlStateError as exc:
        raise _source_directory_provider_private_use_state_error(exc) from exc

    receipt = db.get(
        L3ProviderPrivateSignedUrlReceipt,
        durable_state.provider_private_signed_url_receipt_id,
    )
    if receipt is None:
        raise SourceDirectoryHybridProviderPrivateSignedUrlUseError(
            "source_directory_hybrid_provider_private_signed_url_receipt_missing_after_use",
            "Provider-private signed URL durable receipt was not readable after source-directory use.",
            http_status=409,
            details={"blocked_fields": ["provider_signed_url_receipt_id"]},
        )
    provider_authority = db.get(
        L3ProviderPrivateSignedUrlObjectAuthority,
        receipt.provider_private_signed_url_object_authority_id,
    )
    audit = db.get(
        L3ProviderPrivateSignedUrlAuditEvent,
        durable_state.provider_private_signed_url_audit_event_id,
    )
    if provider_authority is None:
        raise SourceDirectoryHybridProviderPrivateSignedUrlUseError(
            "source_directory_hybrid_provider_private_signed_url_authority_missing_after_use",
            "Provider-private signed URL durable authority was not readable after source-directory use.",
            http_status=409,
            details={"blocked_fields": ["provider_private_signed_url_object_authority_id"]},
        )

    expires_at_epoch = _source_directory_provider_private_datetime_epoch(
        receipt.provider_private_signed_url_expires_at
    )
    state = _source_directory_provider_private_state(receipt, now_epoch=effective_now)
    return {
        "schema_id": SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "used",
        "mode": SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_MODE,
        "session_id": provider_authority.session_id,
        "reconciliation_record_id": provider_authority.reconciliation_record_id,
        "external_export_download_record_ref": provider_authority.external_export_download_record_ref,
        "export_download_descriptor_ref": provider_authority.export_download_descriptor_ref,
        "output_package_id": authority.get("output_package_id"),
        "package_kind": authority.get("package_kind"),
        "package_payload_hash": authority.get("package_payload_hash"),
        "provider_signed_url_receipt_id": receipt.provider_private_signed_url_receipt_id,
        "provider_private_signed_url_object_authority_id": (
            receipt.provider_private_signed_url_object_authority_id
        ),
        "provider_signed_url_state": state,
        "delivery_mode": PROVIDER_PRIVATE_SIGNED_URL_DELIVERY_MODE,
        "delivery_use_decision": "allowed",
        "delivery_use_mode": "server_owned_redacted_provider_private_use",
        "provider_url_redacted": PROVIDER_PRIVATE_SIGNED_URL_REDACTED_MARKER,
        "provider_url_expires_at": _source_directory_provider_private_epoch_iso(expires_at_epoch),
        "provider_url_expires_in_seconds": max(0, expires_at_epoch - effective_now),
        "provider_url_replay_policy": receipt.provider_private_signed_url_replay_policy,
        "provider_url_revocation_supported": True,
        "provider_url_use_count": receipt.provider_private_signed_url_use_count,
        "provider_url_max_use_count": receipt.provider_private_signed_url_max_use_count,
        "provider_url_revoked": (
            receipt.provider_private_signed_url_state == "provider_private_signed_url_revoked"
        ),
        "source_artifact_ref": INTERNAL_ARTIFACT_REF_PLACEHOLDER,
        "source_artifact_hash": provider_authority.source_artifact_hash,
        "source_artifact_size_bytes": provider_authority.source_artifact_size_bytes,
        "source_directory_delivery_authority": authority,
        "audit_receipt": _source_directory_provider_private_audit_receipt(
            receipt=receipt,
            authority=provider_authority,
            audit=audit,
        ),
        "authority_rail": {
            "provider_authority": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
            "artifact_authority": "source_directory_hybrid_external_export_download_delivery_authority",
            "durable_state_authority": True,
            "provider_url_secret_redacted": True,
            "server_owned_use_authority": True,
            "provider_network_enabled": False,
            "provider_object_write_enabled": False,
            "connector_dispatch_enabled": False,
            "destination_write_enabled": False,
            "public_url_enabled": False,
            "same_origin_delivery_changed": False,
        },
        "source_directory_provider_private_signed_url_enabled": True,
        "provider_private_signed_url_enabled": True,
        "provider_public_url_prepare_enabled": False,
        "same_origin_delivery_changed": False,
        "raw_local_path_exposed": False,
        "raw_provider_url_exposed": False,
        "raw_provider_private_signed_url_token_exposed": False,
        "provider_network_enabled": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_write_enabled": False,
        "package_mutation_enabled": False,
        "source_expansion_enabled": False,
        "frontend_durable_authority_enabled": False,
        "next_allowed_actions": ["inspect_provider_private_signed_url_status"],
        "next_state": state,
    }


def source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_status(
    db: Session,
    payload: Mapping[str, Any],
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    fields = _normalise_source_directory_provider_private_signed_url_status_payload(payload)
    request_id = _source_directory_provider_private_status_field(fields, "client_request_id")
    if (
        str(fields.get("operator_decision") or "").strip()
        != SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_STATUS_OPERATOR_DECISION
    ):
        raise SourceDirectoryHybridProviderPrivateSignedUrlStatusError(
            "source_directory_hybrid_provider_private_signed_url_status_decision_not_admitted",
            "operator_decision must be inspect_source_directory_hybrid_provider_private_signed_url_status.",
            http_status=409,
            details={"blocked_fields": ["operator_decision"]},
        )
    if str(fields.get("delivery_mode") or "").strip() != PROVIDER_PRIVATE_SIGNED_URL_DELIVERY_MODE:
        raise SourceDirectoryHybridProviderPrivateSignedUrlStatusError(
            "source_directory_hybrid_provider_private_signed_url_status_delivery_mode_not_admitted",
            "delivery_mode must be provider_private_signed_url.",
            http_status=409,
            details={"blocked_fields": ["delivery_mode"]},
        )

    effective_now = int(time.time() if now_epoch is None else now_epoch)
    authority, authority_basis = _source_directory_provider_private_current_authority_for_status(
        db,
        fields,
    )
    receipt_id = _source_directory_provider_private_status_field(fields, "provider_signed_url_receipt_id")
    receipt = db.get(L3ProviderPrivateSignedUrlReceipt, receipt_id)
    if receipt is None:
        raise SourceDirectoryHybridProviderPrivateSignedUrlStatusError(
            "provider_private_signed_url_receipt_not_found",
            "Provider-private signed URL receipt was not found.",
            http_status=404,
            details={
                "blocked_fields": ["provider_signed_url_receipt_id"],
                "next_allowed_actions": ["prepare_provider_private_signed_url"],
            },
        )
    provider_authority = db.get(
        L3ProviderPrivateSignedUrlObjectAuthority,
        receipt.provider_private_signed_url_object_authority_id,
    )
    if provider_authority is None:
        raise SourceDirectoryHybridProviderPrivateSignedUrlStatusError(
            "provider_private_signed_url_authority_missing",
            "Provider-private signed URL receipt is missing durable object authority.",
            http_status=409,
            details={"blocked_fields": ["provider_signed_url_receipt_id"]},
        )
    _assert_source_directory_provider_private_current_authority(
        provider_authority,
        authority_basis,
        SourceDirectoryHybridProviderPrivateSignedUrlStatusError,
    )
    audit = (
        db.query(L3ProviderPrivateSignedUrlAuditEvent)
        .filter(
            L3ProviderPrivateSignedUrlAuditEvent.provider_private_signed_url_receipt_id
            == receipt.provider_private_signed_url_receipt_id
        )
        .order_by(L3ProviderPrivateSignedUrlAuditEvent.created_at.desc())
        .first()
    )
    return _source_directory_provider_private_response(
        schema_id=SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_STATUS_SCHEMA_ID,
        mode=SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_STATUS_MODE,
        request_id=request_id,
        status="ok",
        receipt=receipt,
        provider_authority=provider_authority,
        audit=audit,
        source_directory_delivery_authority=authority,
        effective_now=effective_now,
    )


def source_directory_hybrid_context_packet_qualitative_analysis_provider_private_signed_url_revoke(
    db: Session,
    payload: Mapping[str, Any],
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    fields = _normalise_source_directory_provider_private_signed_url_revoke_payload(payload)
    request_id = _source_directory_provider_private_revoke_field(fields, "client_request_id")
    if (
        str(fields.get("operator_decision") or "").strip()
        != SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_OPERATOR_DECISION
    ):
        raise SourceDirectoryHybridProviderPrivateSignedUrlRevokeError(
            "source_directory_hybrid_provider_private_signed_url_revoke_decision_not_admitted",
            "operator_decision must be revoke_source_directory_hybrid_provider_private_signed_url.",
            http_status=409,
            details={"blocked_fields": ["operator_decision"]},
        )
    if str(fields.get("delivery_mode") or "").strip() != PROVIDER_PRIVATE_SIGNED_URL_DELIVERY_MODE:
        raise SourceDirectoryHybridProviderPrivateSignedUrlRevokeError(
            "source_directory_hybrid_provider_private_signed_url_revoke_delivery_mode_not_admitted",
            "delivery_mode must be provider_private_signed_url.",
            http_status=409,
            details={"blocked_fields": ["delivery_mode"]},
        )

    effective_now = int(time.time() if now_epoch is None else now_epoch)
    authority, authority_basis = _source_directory_provider_private_current_authority_for_revoke(
        db,
        fields,
    )
    receipt_id = _source_directory_provider_private_revoke_field(fields, "provider_signed_url_receipt_id")
    receipt = db.get(L3ProviderPrivateSignedUrlReceipt, receipt_id)
    if receipt is not None:
        provider_authority = db.get(
            L3ProviderPrivateSignedUrlObjectAuthority,
            receipt.provider_private_signed_url_object_authority_id,
        )
        if provider_authority is not None:
            _assert_source_directory_provider_private_current_authority(
                provider_authority,
                authority_basis,
                SourceDirectoryHybridProviderPrivateSignedUrlRevokeError,
            )
    try:
        durable_state = revoke_provider_private_signed_url_receipt(
            db,
            provider_private_signed_url_receipt_id=receipt_id,
            idempotency_key=_source_directory_provider_private_revoke_field(fields, "idempotency_key"),
            revoked_by=_source_directory_provider_private_revoke_field(fields, "revoked_by"),
            revocation_reason=_source_directory_provider_private_revoke_field(fields, "revocation_reason"),
            authority_basis=authority_basis,
            now_epoch=effective_now,
            request_id=request_id,
        )
    except ProviderPrivateSignedUrlStateError as exc:
        raise _source_directory_provider_private_revoke_state_error(exc) from exc

    receipt = db.get(
        L3ProviderPrivateSignedUrlReceipt,
        durable_state.provider_private_signed_url_receipt_id,
    )
    if receipt is None:
        raise SourceDirectoryHybridProviderPrivateSignedUrlRevokeError(
            "source_directory_hybrid_provider_private_signed_url_receipt_missing_after_revoke",
            "Provider-private signed URL durable receipt was not readable after source-directory revoke.",
            http_status=409,
            details={"blocked_fields": ["provider_signed_url_receipt_id"]},
        )
    provider_authority = db.get(
        L3ProviderPrivateSignedUrlObjectAuthority,
        receipt.provider_private_signed_url_object_authority_id,
    )
    audit = db.get(
        L3ProviderPrivateSignedUrlAuditEvent,
        durable_state.provider_private_signed_url_audit_event_id,
    )
    if provider_authority is None:
        raise SourceDirectoryHybridProviderPrivateSignedUrlRevokeError(
            "source_directory_hybrid_provider_private_signed_url_authority_missing_after_revoke",
            "Provider-private signed URL durable authority was not readable after source-directory revoke.",
            http_status=409,
            details={"blocked_fields": ["provider_private_signed_url_object_authority_id"]},
        )
    return _source_directory_provider_private_response(
        schema_id=SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_SCHEMA_ID,
        mode=SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_MODE,
        request_id=request_id,
        status="revoked",
        receipt=receipt,
        provider_authority=provider_authority,
        audit=audit,
        source_directory_delivery_authority=authority,
        effective_now=effective_now,
        extra={
            "revocation_recorded": True,
            "revocation_idempotency_key": _source_directory_provider_private_revoke_field(
                fields,
                "idempotency_key",
            ),
        },
    )


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHybridAnalysisError(
            "source_directory_hybrid_context_qualitative_analysis_forbidden_field_not_admitted",
            "The source-directory hybrid-context qualitative-analysis request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _REQUIRED_FIELDS - _OPTIONAL_FIELDS)
    if unknown:
        raise SourceDirectoryHybridAnalysisError(
            "source_directory_hybrid_context_qualitative_analysis_unknown_field",
            "The source-directory hybrid-context qualitative-analysis request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_REQUIRED_FIELDS):
        _required(fields, field)
    return fields


def _status_analysis_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    if not str(fields.get("client_request_id") or "").strip():
        fields["client_request_id"] = ANALYSIS_STATUS_DEFAULT_CLIENT_REQUEST_ID
    return fields


def _normalise_package_commit_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHybridPackageCommitError(
            "source_directory_hybrid_package_commit_forbidden_field_not_admitted",
            "The source-directory hybrid package commit request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _PACKAGE_COMMIT_REQUIRED_FIELDS - _OPTIONAL_FIELDS)
    if unknown:
        raise SourceDirectoryHybridPackageCommitError(
            "source_directory_hybrid_package_commit_unknown_field",
            "The source-directory hybrid package commit request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_PACKAGE_COMMIT_REQUIRED_FIELDS):
        _require_commit_field(fields, field)
    return fields


def _normalise_package_review_submit_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_forbidden_field_not_admitted",
            "The source-directory hybrid package-review submit request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(
        set(fields)
        - _PACKAGE_REVIEW_SUBMIT_REQUIRED_FIELDS
        - _OPTIONAL_FIELDS
        - {"decision_notes"}
    )
    if unknown:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_unknown_field",
            "The source-directory hybrid package-review submit request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_PACKAGE_REVIEW_SUBMIT_REQUIRED_FIELDS):
        _require_submit_field(fields, field)
    return fields


def _normalise_handoff_export_prepare_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _HANDOFF_EXPORT_PREPARE_FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_forbidden_field_not_admitted",
            "The source-directory hybrid handoff/export prepare request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(
        set(fields)
        - _HANDOFF_EXPORT_PREPARE_REQUIRED_FIELDS
        - _OPTIONAL_FIELDS
        - {"decision_notes"}
    )
    if unknown:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_unknown_field",
            "The source-directory hybrid handoff/export prepare request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_HANDOFF_EXPORT_PREPARE_REQUIRED_FIELDS):
        _require_handoff_field(fields, field)
    return fields


def _normalise_external_export_download_prepare_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_forbidden_field_not_admitted",
            "The source-directory hybrid external export/download prepare request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(
        set(fields)
        - _EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUIRED_FIELDS
        - _OPTIONAL_FIELDS
        - {"decision_notes"}
    )
    if unknown:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_unknown_field",
            "The source-directory hybrid external export/download prepare request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_REQUIRED_FIELDS):
        _require_external_export_download_prepare_field(fields, field)
    return fields


def _normalise_external_export_download_delivery_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_forbidden_field_not_admitted",
            "The source-directory hybrid external export/download delivery request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(
        set(fields)
        - _EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUIRED_FIELDS
        - _OPTIONAL_FIELDS
        - {"decision_notes"}
    )
    if unknown:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_unknown_field",
            "The source-directory hybrid external export/download delivery request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUIRED_FIELDS):
        _require_external_export_download_delivery_field(fields, field)
    return fields


def _normalise_source_directory_provider_private_signed_url_payload(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
            "source_directory_hybrid_provider_private_signed_url_forbidden_field_not_admitted",
            "The source-directory hybrid provider-private signed URL request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_ALLOWED_FIELDS)
    if unknown:
        raise SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
            "source_directory_hybrid_provider_private_signed_url_unknown_field",
            "The source-directory hybrid provider-private signed URL request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REQUIRED_FIELDS):
        _source_directory_provider_private_field(fields, field)
    return fields


def _normalise_source_directory_provider_private_signed_url_use_payload(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHybridProviderPrivateSignedUrlUseError(
            "source_directory_hybrid_provider_private_signed_url_use_forbidden_field_not_admitted",
            "The source-directory hybrid provider-private signed URL use request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_ALLOWED_FIELDS)
    if unknown:
        raise SourceDirectoryHybridProviderPrivateSignedUrlUseError(
            "source_directory_hybrid_provider_private_signed_url_use_unknown_field",
            "The source-directory hybrid provider-private signed URL use request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_USE_REQUIRED_FIELDS):
        _source_directory_provider_private_use_field(fields, field)
    return fields


def _normalise_source_directory_provider_private_signed_url_status_payload(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHybridProviderPrivateSignedUrlStatusError(
            "source_directory_hybrid_provider_private_signed_url_status_forbidden_field_not_admitted",
            "The source-directory hybrid provider-private signed URL status request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_STATUS_ALLOWED_FIELDS)
    if unknown:
        raise SourceDirectoryHybridProviderPrivateSignedUrlStatusError(
            "source_directory_hybrid_provider_private_signed_url_status_unknown_field",
            "The source-directory hybrid provider-private signed URL status request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_STATUS_REQUIRED_FIELDS):
        _source_directory_provider_private_status_field(fields, field)
    return fields


def _normalise_source_directory_provider_private_signed_url_revoke_payload(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_FORBIDDEN_FIELDS)
    if forbidden:
        raise SourceDirectoryHybridProviderPrivateSignedUrlRevokeError(
            "source_directory_hybrid_provider_private_signed_url_revoke_forbidden_field_not_admitted",
            "The source-directory hybrid provider-private signed URL revoke request includes deferred or forbidden fields.",
            details={"forbidden_fields": forbidden},
        )
    unknown = sorted(set(fields) - _SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_ALLOWED_FIELDS)
    if unknown:
        raise SourceDirectoryHybridProviderPrivateSignedUrlRevokeError(
            "source_directory_hybrid_provider_private_signed_url_revoke_unknown_field",
            "The source-directory hybrid provider-private signed URL revoke request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    for field in sorted(_SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_REQUIRED_FIELDS):
        _source_directory_provider_private_revoke_field(fields, field)
    return fields


def _source_directory_provider_private_field(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
            "source_directory_hybrid_provider_private_signed_url_required_field_missing",
            "A required source-directory hybrid provider-private signed URL field is missing or empty.",
            details={"field": key},
        )
    return value


def _source_directory_provider_private_use_field(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryHybridProviderPrivateSignedUrlUseError(
            "source_directory_hybrid_provider_private_signed_url_use_required_field_missing",
            "A required source-directory hybrid provider-private signed URL use field is missing or empty.",
            details={"field": key},
        )
    return value


def _source_directory_provider_private_status_field(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryHybridProviderPrivateSignedUrlStatusError(
            "source_directory_hybrid_provider_private_signed_url_status_required_field_missing",
            "A required source-directory hybrid provider-private signed URL status field is missing or empty.",
            details={"field": key},
        )
    return value


def _source_directory_provider_private_revoke_field(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryHybridProviderPrivateSignedUrlRevokeError(
            "source_directory_hybrid_provider_private_signed_url_revoke_required_field_missing",
            "A required source-directory hybrid provider-private signed URL revoke field is missing or empty.",
            details={"field": key},
        )
    return value


def _source_directory_provider_private_ttl_seconds(fields: Mapping[str, Any]) -> int:
    raw_value = fields.get(
        "requested_ttl_seconds",
        SOURCE_DIRECTORY_PROVIDER_PRIVATE_SIGNED_URL_DEFAULT_TTL_SECONDS,
    )
    try:
        ttl = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
            "source_directory_hybrid_provider_private_signed_url_ttl_invalid",
            "requested_ttl_seconds must be an integer.",
            details={"blocked_fields": ["requested_ttl_seconds"]},
        ) from exc
    if ttl <= 0 or ttl > PROVIDER_PRIVATE_SIGNED_URL_MAX_TTL_SECONDS:
        raise SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
            "source_directory_hybrid_provider_private_signed_url_ttl_not_admitted",
            "requested_ttl_seconds must be positive and within the admitted provider-private TTL bound.",
            details={"blocked_fields": ["requested_ttl_seconds"]},
        )
    return ttl


def _source_directory_provider_private_delivery_payload(
    db: Session,
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    reconciliation_record_id = _source_directory_provider_private_field(fields, "reconciliation_record_id")
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None:
        raise SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
            "source_directory_hybrid_provider_private_signed_url_reconciliation_not_found",
            "No source-directory hybrid reconciliation record exists for the supplied provider-private authority.",
            http_status=404,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    readiness = _json_clone(reconciliation.summary_json or {}).get("external_export_download_prepare")
    if not isinstance(readiness, dict):
        raise SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
            "source_directory_hybrid_provider_private_signed_url_requires_prepare",
            "Provider-private signed URL prepare requires source-directory external export/download prepare authority.",
            http_status=409,
            details={"blocked_fields": ["external_export_download_state"]},
        )
    delivery_payload = {
        field: fields[field]
        for field in sorted(_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUIRED_FIELDS | _OPTIONAL_FIELDS)
        if field in fields
    }
    delivery_payload["client_request_id"] = str(
        readiness.get("client_request_id") or fields.get("client_request_id") or ""
    ).strip()
    delivery_payload["operator_decision"] = EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION
    delivery_payload["delivery_mode"] = EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE_VALUE
    return delivery_payload


def _source_directory_provider_private_use_delivery_payload(
    db: Session,
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    reconciliation_record_id = _source_directory_provider_private_use_field(fields, "reconciliation_record_id")
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None:
        raise SourceDirectoryHybridProviderPrivateSignedUrlUseError(
            "source_directory_hybrid_provider_private_signed_url_use_reconciliation_not_found",
            "No source-directory hybrid reconciliation record exists for the supplied provider-private use authority.",
            http_status=404,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    readiness = _json_clone(reconciliation.summary_json or {}).get("external_export_download_prepare")
    if not isinstance(readiness, dict):
        raise SourceDirectoryHybridProviderPrivateSignedUrlUseError(
            "source_directory_hybrid_provider_private_signed_url_use_requires_prepare",
            "Provider-private signed URL use requires source-directory external export/download prepare authority.",
            http_status=409,
            details={"blocked_fields": ["external_export_download_state"]},
        )
    delivery_payload = {
        field: fields[field]
        for field in sorted(_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUIRED_FIELDS | _OPTIONAL_FIELDS)
        if field in fields
    }
    delivery_payload["client_request_id"] = str(
        readiness.get("client_request_id") or fields.get("client_request_id") or ""
    ).strip()
    delivery_payload["operator_decision"] = EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION
    delivery_payload["delivery_mode"] = EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE_VALUE
    return delivery_payload


def _source_directory_provider_private_current_authority_for_status(
    db: Session,
    fields: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    delivery_payload = _source_directory_provider_private_status_delivery_payload(db, fields)
    try:
        delivery = source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver(
            db,
            delivery_payload,
        )
    except SourceDirectoryHybridExternalExportDownloadDeliveryError as exc:
        raise SourceDirectoryHybridProviderPrivateSignedUrlStatusError(
            exc.code,
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    return _source_directory_provider_private_authority_basis_from_delivery(delivery)


def _source_directory_provider_private_current_authority_for_revoke(
    db: Session,
    fields: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    delivery_payload = _source_directory_provider_private_revoke_delivery_payload(db, fields)
    try:
        delivery = source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_deliver(
            db,
            delivery_payload,
        )
    except SourceDirectoryHybridExternalExportDownloadDeliveryError as exc:
        raise SourceDirectoryHybridProviderPrivateSignedUrlRevokeError(
            exc.code,
            exc.message,
            http_status=exc.http_status,
            details=exc.details,
        ) from exc
    return _source_directory_provider_private_authority_basis_from_delivery(delivery)


def _source_directory_provider_private_status_delivery_payload(
    db: Session,
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    return _source_directory_provider_private_delivery_payload_for_lifecycle(
        db,
        fields,
        _source_directory_provider_private_status_field,
        SourceDirectoryHybridProviderPrivateSignedUrlStatusError,
        "status",
    )


def _source_directory_provider_private_revoke_delivery_payload(
    db: Session,
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    return _source_directory_provider_private_delivery_payload_for_lifecycle(
        db,
        fields,
        _source_directory_provider_private_revoke_field,
        SourceDirectoryHybridProviderPrivateSignedUrlRevokeError,
        "revoke",
    )


def _source_directory_provider_private_delivery_payload_for_lifecycle(
    db: Session,
    fields: Mapping[str, Any],
    field_reader: Any,
    error_type: Any,
    operation: str,
) -> dict[str, Any]:
    reconciliation_record_id = field_reader(fields, "reconciliation_record_id")
    reconciliation = db.get(L3ReconciliationRecord, reconciliation_record_id)
    if reconciliation is None:
        raise error_type(
            f"source_directory_hybrid_provider_private_signed_url_{operation}_reconciliation_not_found",
            f"No source-directory hybrid reconciliation record exists for the supplied provider-private {operation} authority.",
            http_status=404,
            details={"reconciliation_record_id": reconciliation_record_id},
        )
    readiness = _json_clone(reconciliation.summary_json or {}).get("external_export_download_prepare")
    if not isinstance(readiness, dict):
        raise error_type(
            f"source_directory_hybrid_provider_private_signed_url_{operation}_requires_prepare",
            f"Provider-private signed URL {operation} requires source-directory external export/download prepare authority.",
            http_status=409,
            details={"blocked_fields": ["external_export_download_state"]},
        )
    delivery_payload = {
        field: fields[field]
        for field in sorted(_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_REQUIRED_FIELDS | _OPTIONAL_FIELDS)
        if field in fields
    }
    delivery_payload["client_request_id"] = str(
        readiness.get("client_request_id") or fields.get("client_request_id") or ""
    ).strip()
    delivery_payload["operator_decision"] = EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION
    delivery_payload["delivery_mode"] = EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE_VALUE
    return delivery_payload


def _source_directory_provider_private_authority_basis_from_delivery(
    delivery: ExternalExportDownloadDelivery,
) -> tuple[dict[str, Any], dict[str, Any]]:
    authority = _json_clone(delivery.authority)
    artifact_path = Path(delivery.artifact_path)
    authority_basis = {
        "session_id": str(authority.get("session_id") or "").strip(),
        "reconciliation_record_id": str(authority.get("reconciliation_record_id") or "").strip(),
        "source_artifact_ref": str(artifact_path),
        "source_artifact_hash": str(authority.get("package_payload_hash") or "").strip().lower(),
        "source_artifact_size_bytes": artifact_path.stat().st_size,
        "external_export_download_record_ref": str(
            authority.get("external_export_download_record_ref") or ""
        ).strip(),
        "export_download_descriptor_ref": str(authority.get("export_download_descriptor_ref") or "").strip(),
    }
    return authority, authority_basis


def _assert_source_directory_provider_private_current_authority(
    provider_authority: L3ProviderPrivateSignedUrlObjectAuthority,
    authority_basis: Mapping[str, Any],
    error_type: Any,
) -> None:
    mismatched = [
        field
        for field in (
            "session_id",
            "reconciliation_record_id",
            "external_export_download_record_ref",
            "export_download_descriptor_ref",
            "source_artifact_hash",
            "source_artifact_size_bytes",
        )
        if str(getattr(provider_authority, field)) != str(authority_basis[field])
    ]
    if mismatched:
        raise error_type(
            "provider_private_signed_url_state_authority_mismatch",
            "Current source-directory artifact authority no longer matches the provider-private signed URL durable receipt.",
            http_status=409,
            details={
                "blocked_fields": mismatched,
                "next_allowed_actions": ["prepare_new_provider_private_signed_url"],
            },
        )


def _source_directory_provider_private_response(
    *,
    schema_id: str,
    mode: str,
    request_id: str,
    status: str,
    receipt: L3ProviderPrivateSignedUrlReceipt,
    provider_authority: L3ProviderPrivateSignedUrlObjectAuthority,
    audit: L3ProviderPrivateSignedUrlAuditEvent | None,
    source_directory_delivery_authority: Mapping[str, Any],
    effective_now: int,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    expires_at_epoch = _source_directory_provider_private_datetime_epoch(
        receipt.provider_private_signed_url_expires_at
    )
    state = _source_directory_provider_private_state(receipt, now_epoch=effective_now)
    return {
        "schema_id": schema_id,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": status,
        "mode": mode,
        "session_id": provider_authority.session_id,
        "reconciliation_record_id": provider_authority.reconciliation_record_id,
        "external_export_download_record_ref": provider_authority.external_export_download_record_ref,
        "export_download_descriptor_ref": provider_authority.export_download_descriptor_ref,
        "output_package_id": source_directory_delivery_authority.get("output_package_id"),
        "package_kind": source_directory_delivery_authority.get("package_kind"),
        "package_payload_hash": source_directory_delivery_authority.get("package_payload_hash"),
        "provider_signed_url_receipt_id": receipt.provider_private_signed_url_receipt_id,
        "provider_private_signed_url_object_authority_id": (
            receipt.provider_private_signed_url_object_authority_id
        ),
        "provider_signed_url_state": state,
        "delivery_mode": PROVIDER_PRIVATE_SIGNED_URL_DELIVERY_MODE,
        "provider_url_redacted": PROVIDER_PRIVATE_SIGNED_URL_REDACTED_MARKER,
        "provider_url_expires_at": _source_directory_provider_private_epoch_iso(expires_at_epoch),
        "provider_url_expires_in_seconds": max(0, expires_at_epoch - effective_now),
        "provider_url_replay_policy": receipt.provider_private_signed_url_replay_policy,
        "provider_url_revocation_supported": True,
        "provider_url_use_count": receipt.provider_private_signed_url_use_count,
        "provider_url_max_use_count": receipt.provider_private_signed_url_max_use_count,
        "provider_url_revoked": (
            receipt.provider_private_signed_url_state == "provider_private_signed_url_revoked"
        ),
        "source_artifact_ref": INTERNAL_ARTIFACT_REF_PLACEHOLDER,
        "source_artifact_hash": provider_authority.source_artifact_hash,
        "source_artifact_size_bytes": provider_authority.source_artifact_size_bytes,
        "source_directory_delivery_authority": dict(source_directory_delivery_authority),
        "audit_receipt": _source_directory_provider_private_audit_receipt(
            receipt=receipt,
            authority=provider_authority,
            audit=audit,
        ),
        "authority_rail": {
            "provider_authority": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
            "artifact_authority": "source_directory_hybrid_external_export_download_delivery_authority",
            "durable_state_authority": True,
            "provider_url_secret_redacted": True,
            "server_owned_use_authority": True,
            "provider_network_enabled": False,
            "provider_object_write_enabled": False,
            "connector_dispatch_enabled": False,
            "destination_write_enabled": False,
            "public_url_enabled": False,
            "same_origin_delivery_changed": False,
        },
        "source_directory_provider_private_signed_url_enabled": True,
        "provider_private_signed_url_enabled": True,
        "provider_public_url_prepare_enabled": False,
        "same_origin_delivery_changed": False,
        "raw_local_path_exposed": False,
        "raw_provider_url_exposed": False,
        "raw_provider_private_signed_url_token_exposed": False,
        "provider_network_enabled": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_write_enabled": False,
        "package_mutation_enabled": False,
        "source_expansion_enabled": False,
        "frontend_durable_authority_enabled": False,
        "next_allowed_actions": ["inspect_provider_private_signed_url_status"],
        "next_state": state,
        **dict(extra or {}),
    }


def _source_directory_provider_private_state_error(
    exc: ProviderPrivateSignedUrlStateError,
) -> SourceDirectoryHybridProviderPrivateSignedUrlPrepareError:
    http_status = 404 if exc.status == "not_found" else 409 if exc.status in {"blocked", "conflict"} else 400
    return SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
        exc.error_code,
        exc.message,
        http_status=http_status,
        details={
            "blocked_fields": list(exc.blocked_fields),
            "next_allowed_actions": list(exc.next_allowed_actions),
        },
    )


def _source_directory_provider_private_use_state_error(
    exc: ProviderPrivateSignedUrlStateError,
) -> SourceDirectoryHybridProviderPrivateSignedUrlUseError:
    http_status = 404 if exc.status == "not_found" else 409 if exc.status in {"blocked", "conflict"} else 400
    return SourceDirectoryHybridProviderPrivateSignedUrlUseError(
        exc.error_code,
        exc.message,
        http_status=http_status,
        details={
            "blocked_fields": list(exc.blocked_fields),
            "next_allowed_actions": list(exc.next_allowed_actions),
        },
    )


def _source_directory_provider_private_revoke_state_error(
    exc: ProviderPrivateSignedUrlStateError,
) -> SourceDirectoryHybridProviderPrivateSignedUrlRevokeError:
    http_status = 404 if exc.status == "not_found" else 409 if exc.status in {"blocked", "conflict"} else 400
    return SourceDirectoryHybridProviderPrivateSignedUrlRevokeError(
        exc.error_code,
        exc.message,
        http_status=http_status,
        details={
            "blocked_fields": list(exc.blocked_fields),
            "next_allowed_actions": list(exc.next_allowed_actions),
        },
    )


def _source_directory_provider_private_fake_provider_error(
    exc: ProviderPrivateSignedUrlError,
) -> SourceDirectoryHybridProviderPrivateSignedUrlPrepareError:
    http_status = 409 if "blocked" in exc.status or "conflict" in exc.status else 400
    return SourceDirectoryHybridProviderPrivateSignedUrlPrepareError(
        exc.error_code,
        "Provider-private signed URL fake-provider prepare failed without exposing provider secrets.",
        http_status=http_status,
        details={
            "blocked_fields": list(exc.blocked_fields),
            "next_allowed_actions": list(exc.next_allowed_actions),
        },
    )


def _source_directory_provider_private_datetime_epoch(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.astimezone(timezone.utc).timestamp())


def _source_directory_provider_private_epoch_iso(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def _source_directory_provider_private_state(
    receipt: L3ProviderPrivateSignedUrlReceipt,
    *,
    now_epoch: int,
) -> str:
    if (
        receipt.provider_private_signed_url_state == "provider_private_signed_url_prepared"
        and now_epoch >= _source_directory_provider_private_datetime_epoch(
            receipt.provider_private_signed_url_expires_at
        )
    ):
        return "provider_private_signed_url_expired"
    return receipt.provider_private_signed_url_state


def _source_directory_provider_private_audit_receipt(
    *,
    receipt: L3ProviderPrivateSignedUrlReceipt,
    authority: L3ProviderPrivateSignedUrlObjectAuthority,
    audit: L3ProviderPrivateSignedUrlAuditEvent | None,
) -> dict[str, Any]:
    return {
        "provider_private_signed_url_receipt_id": receipt.provider_private_signed_url_receipt_id,
        "provider_private_signed_url_object_authority_id": (
            receipt.provider_private_signed_url_object_authority_id
        ),
        "provider_private_signed_url_token_prefix": receipt.provider_private_signed_url_token_prefix,
        "provider_private_signed_url_audit_event_id": (
            audit.provider_private_signed_url_audit_event_id if audit is not None else None
        ),
        "provider_authority": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
        "authority_hash": authority.authority_hash,
        "provider_object_identity_hash": authority.provider_object_identity_hash,
        "source_artifact_ref": INTERNAL_ARTIFACT_REF_PLACEHOLDER,
        "source_directory_delivery_authority": (
            "source_directory_hybrid_external_export_download_delivery_authority"
        ),
        "provider_url_secret_redacted": True,
        "provider_network_enabled": False,
        "provider_object_write_enabled": False,
    }


def _hybrid_context_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {field: fields[field] for field in sorted(_HYBRID_CONTEXT_FIELDS) if field in fields}


def _qualitative_analysis_payload(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {field: fields[field] for field in sorted(_REQUIRED_FIELDS | _OPTIONAL_FIELDS) if field in fields}


def _assert_hybrid_context_authority(context: Mapping[str, Any]) -> None:
    mismatches = []
    expected = {
        "schema_id": HYBRID_CONTEXT_SCHEMA_ID,
        "hybrid_context_contract_id": HYBRID_CONTEXT_CONTRACT_ID,
        "hybrid_context_mode": HYBRID_CONTEXT_MODE,
    }
    for field, value in expected.items():
        if str(context.get(field) or "") != value:
            mismatches.append(field)
    if str(context.get("mode") or "") != "source_directory_hybrid_retrieval_context_packet_authority":
        mismatches.append("mode")
    if mismatches:
        raise SourceDirectoryHybridAnalysisError(
            "source_directory_hybrid_context_qualitative_analysis_authority_mismatch",
            "The qualitative-analysis reader requires admitted source-directory hybrid context-packet authority.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )


def _package_review_preview(
    *,
    request_id: str,
    fields: Mapping[str, Any],
    hybrid_context: Mapping[str, Any],
    qualitative_analysis_hash: str,
) -> dict[str, Any]:
    source_authority = {
        "source_ingestion_batch_id": hybrid_context["source_ingestion_batch_id"],
        "source_ingestion_file_id": hybrid_context["source_ingestion_file_id"],
        "material_snapshot_id": hybrid_context["material_snapshot_id"],
        "content_sha256": hybrid_context["content_sha256"],
        "file_identity_hash": hybrid_context["file_identity_hash"],
        "authority_basis_hash": hybrid_context["authority_basis_hash"],
        "payload_hash": hybrid_context["payload_hash"],
        "index_authority_hash": hybrid_context["index_authority_hash"],
        "embedding_index_authority_hash": hybrid_context["embedding_index_authority_hash"],
        "lexical_context_packet_hash": hybrid_context["lexical_context_packet_hash"],
        "hybrid_context_packet_hash": hybrid_context["hybrid_context_packet_hash"],
        "qualitative_analysis_hash": qualitative_analysis_hash,
    }
    candidate_packages = [
        {
            "package_kind": package_kind,
            "preview_only": True,
            "package_commit_enabled": False,
            "package_review_submit_enabled": False,
            "handoff_enabled": False,
            "external_export_download_enabled": False,
            "readiness_reason": (
                "source-directory hybrid qualitative-analysis package construction is not admitted in this boundary"
            ),
        }
        for package_kind in PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS
    ]
    negative_invariants = {
        "read_only_preview": True,
        "package_rows_written": False,
        "package_payload_written": False,
        "package_construction_enabled": False,
        "package_mutation_enabled": False,
        "source_package_row_mutation_enabled": False,
        "handoff_export_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
    }
    package_review_preview_hash = _stable_hash(
        {
            "schema_id": PACKAGE_REVIEW_PREVIEW_SCHEMA_ID,
            "schema_version": 1,
            "mode": PACKAGE_REVIEW_PREVIEW_MODE,
            "source_gate": PACKAGE_REVIEW_PREVIEW_SOURCE_GATE,
            "analysis_question": str(fields.get("analysis_question") or ""),
            "analysis_focus": str(fields.get("analysis_focus") or ""),
            "query_text": str(fields.get("query_text") or ""),
            "source_authority": source_authority,
            "candidate_package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS),
            "negative_invariants": negative_invariants,
        }
    )
    return {
        "schema_id": PACKAGE_REVIEW_PREVIEW_SCHEMA_ID,
        "schema_version": 1,
        "mode": PACKAGE_REVIEW_PREVIEW_MODE,
        "source_gate": PACKAGE_REVIEW_PREVIEW_SOURCE_GATE,
        "status": "available",
        "package_review_preview_hash": package_review_preview_hash,
        "source_authority": source_authority,
        "candidate_package_kinds": list(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS),
        "candidate_packages": candidate_packages,
        "package_review_preview_enabled": True,
        "package_commit_enabled": False,
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "external_export_download_enabled": False,
        "next_state": "source_directory_hybrid_package_review_preview_available",
        "next_allowed_actions": [],
        "negative_invariants": negative_invariants,
    }


def _supporting_segments(items: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for item in items:
        segments.append(
            {
                "segment_id": str(item["segment_id"]),
                "rank_position": int(item["hybrid_rank"]),
                "hybrid_rank": int(item["hybrid_rank"]),
                "lexical_rank": item.get("lexical_rank"),
                "vector_rank": item.get("vector_rank"),
                "hybrid_score": str(item["hybrid_score"]),
                "vector_score": str(item["vector_score"]),
                "included_by_lexical": bool(item["included_by_lexical"]),
                "included_by_vector": bool(item["included_by_vector"]),
                "segment_sequence": int(item["segment_sequence"]),
                "line_range": {
                    "start": int(item["line_start"]),
                    "end": int(item["line_end"]),
                },
                "segment_hash": str(item["segment_hash"]),
                "quote_excerpt": str(item.get("text_excerpt") or ""),
                "matched_unique_query_terms": max(
                    int(item.get("lexical_matched_unique_query_terms") or 0),
                    int(item.get("vector_matched_unique_query_terms") or 0),
                ),
                "summed_term_frequency": (
                    int(item.get("lexical_summed_term_frequency") or 0)
                    + int(item.get("vector_summed_query_term_frequency") or 0)
                ),
                "support_label": (
                    "primary_hybrid_context_segment"
                    if int(item["hybrid_rank"]) == 1
                    else "supporting_hybrid_context_segment"
                ),
            }
        )
    return segments


def _salient_terms(query_tokens: list[Any], items: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    terms: list[dict[str, Any]] = []
    for token in [str(value) for value in query_tokens]:
        matched_segments = 0
        summed_frequency = 0
        for item in items:
            counts = Counter(normalize_query_tokens(str(item.get("text_excerpt") or "")))
            frequency = int(counts.get(token, 0))
            if frequency > 0:
                matched_segments += 1
                summed_frequency += frequency
        terms.append(
            {
                "term": token,
                "matched_segments": matched_segments,
                "summed_term_frequency": summed_frequency,
            }
        )
    return terms


def _evidence_summary(
    *,
    hybrid_context: Mapping[str, Any],
    supporting_segments: list[Mapping[str, Any]],
    analysis_question: str,
) -> dict[str, Any]:
    hybrid_total = int(hybrid_context["hybrid_total"])
    considered = len(supporting_segments)
    if hybrid_total == 0:
        coverage_label = "no_hybrid_context_matches"
    elif considered < hybrid_total:
        coverage_label = "paged_hybrid_context_matches"
    else:
        coverage_label = "complete_hybrid_context_matches"
    return {
        "summary_kind": "deterministic_hybrid_context_packet_evidence_summary",
        "analysis_question_token_count": len(normalize_query_tokens(analysis_question)),
        "hybrid_context_total_matches": hybrid_total,
        "lexical_total_matches": int(hybrid_context["lexical_total"]),
        "vector_total_matches": int(hybrid_context["vector_total"]),
        "context_segments_considered": considered,
        "top_rank_position": int(supporting_segments[0]["rank_position"]) if supporting_segments else 0,
        "matched_query_tokens": list(hybrid_context.get("query_tokens") or []),
        "coverage_label": coverage_label,
    }


def _coverage_notes(
    *,
    hybrid_context: Mapping[str, Any],
    supporting_segments: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    lexical_inclusions = sum(1 for item in supporting_segments if item["included_by_lexical"])
    vector_inclusions = sum(1 for item in supporting_segments if item["included_by_vector"])
    notes = [
        {
            "code": "hybrid_context_packet_authority_validated",
            "message": "Hybrid context-packet authority fields were validated before qualitative analysis assembly.",
        },
        {
            "code": "hybrid_context_packet_sources_redacted",
            "message": "The qualitative analysis uses redacted text excerpts and does not expose raw vectors or local paths.",
        },
        {
            "code": "hybrid_context_packet_fusion_observed",
            "message": "Lexical and vector inclusion counts are reported from the validated hybrid context packet.",
            "lexical_inclusion_count": lexical_inclusions,
            "vector_inclusion_count": vector_inclusions,
        },
    ]
    if int(hybrid_context["hybrid_total"]) == 0:
        notes.append(
            {
                "code": "no_hybrid_context_matches",
                "message": "The validated hybrid context packet produced no matching segments.",
            }
        )
    return notes


def _analysis_limits() -> list[dict[str, Any]]:
    return [
        {
            "code": "deterministic_reader_only",
            "message": "This analysis is assembled deterministically from the admitted hybrid context packet.",
        },
        {
            "code": "no_prompt_model_provider_runtime",
            "message": "No prompt, model, provider, RAG execution, network, or qualitative generation runtime is used.",
        },
        {
            "code": "no_package_or_delivery_authority",
            "message": "Package construction, package review, handoff/export, provider delivery, and connector dispatch remain blocked.",
        },
    ]


def _qualitative_analysis_hash(
    *,
    fields: Mapping[str, Any],
    hybrid_context: Mapping[str, Any],
    evidence_summary: Mapping[str, Any],
    salient_terms: list[Mapping[str, Any]],
    supporting_segments: list[Mapping[str, Any]],
    coverage_notes: list[Mapping[str, Any]],
    analysis_limits: list[Mapping[str, Any]],
    row_write_flags: Mapping[str, bool],
    negative_invariants: Mapping[str, bool],
) -> str:
    return _stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": 1,
            "analysis_contract_id": ANALYSIS_CONTRACT_ID,
            "analysis_mode": ANALYSIS_MODE,
            "source_gate": SOURCE_GATE,
            "request_contract": {
                field: str(fields.get(field) or "")
                for field in sorted(_REQUIRED_FIELDS - {"client_request_id"})
            },
            "hybrid_context_packet_hash": hybrid_context["hybrid_context_packet_hash"],
            "hybrid_context_contract_id": hybrid_context["hybrid_context_contract_id"],
            "hybrid_context_mode": hybrid_context["hybrid_context_mode"],
            "lexical_context_packet_hash": hybrid_context["lexical_context_packet_hash"],
            "vector_retrieval_contract_id": hybrid_context["vector_retrieval_contract_id"],
            "vector_retrieval_mode": hybrid_context["vector_retrieval_mode"],
            "embedding_index_authority_hash": hybrid_context["embedding_index_authority_hash"],
            "index_authority_hash": hybrid_context["index_authority_hash"],
            "evidence_refs": [
                {
                    "segment_id": item["segment_id"],
                    "rank_position": item["rank_position"],
                    "hybrid_rank": item["hybrid_rank"],
                    "lexical_rank": item["lexical_rank"],
                    "vector_rank": item["vector_rank"],
                    "hybrid_score": item["hybrid_score"],
                    "segment_sequence": item["segment_sequence"],
                    "line_range": item["line_range"],
                    "segment_hash": item["segment_hash"],
                    "matched_unique_query_terms": item["matched_unique_query_terms"],
                    "summed_term_frequency": item["summed_term_frequency"],
                    "included_by_lexical": item["included_by_lexical"],
                    "included_by_vector": item["included_by_vector"],
                }
                for item in supporting_segments
            ],
            "analysis_sections": {
                "evidence_summary": evidence_summary,
                "salient_terms": salient_terms,
                "supporting_segments": supporting_segments,
                "coverage_notes": coverage_notes,
                "analysis_limits": analysis_limits,
            },
            "row_write_flags": row_write_flags,
            "negative_invariants": negative_invariants,
        }
    )


def _row_write_flags() -> dict[str, bool]:
    return {
        "source_index_rows_written": False,
        "embedding_vector_rows_written": False,
        "vector_index_rows_written": False,
        "retrieval_rows_written": False,
        "context_packet_rows_written": False,
        "qualitative_analysis_rows_written": False,
        "qualitative_generation_rows_written": False,
        "analysis_run_rows_written": False,
        "package_rows_written": False,
        "connector_rows_written": False,
    }


def _negative_invariants() -> dict[str, bool]:
    return {
        "source_index_rows_written": False,
        "embedding_vector_rows_written": False,
        "vector_index_rows_written": False,
        "retrieval_rows_written": False,
        "context_packet_rows_written": False,
        "qualitative_analysis_rows_written": False,
        "qualitative_generation_rows_written": False,
        "analysis_run_rows_written": False,
        "package_rows_written": False,
        "connector_rows_written": False,
        "persistent_vector_store_enabled": False,
        "durable_embedding_rows_enabled": False,
        "durable_retrieval_rows_enabled": False,
        "rag_execution_enabled": False,
        "embedding_model_provider_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "qualitative_generation_runtime_enabled": False,
        "package_construction_enabled": False,
        "package_review_submit_enabled": False,
        "package_mutation_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "frontend_durable_authority_enabled": False,
        "network_egress_enabled": False,
        "raw_local_path_exposed": False,
        "raw_vector_exposed": False,
    }


def _hybrid_qualitative_analysis_status_state(
    db: Session,
    *,
    analysis: Mapping[str, Any],
) -> dict[str, Any]:
    base = {
        "source_directory_hybrid_package_commit_available": False,
        "source_directory_hybrid_package_review_submit_available": False,
        "source_directory_hybrid_handoff_export_prepare_available": False,
        "source_directory_hybrid_external_export_download_prepare_available": False,
        "reconciliation_record_id": None,
        "construction_basis_hash": None,
        "output_packages": [],
        "output_package_ids": [],
        "package_kinds": [],
        "payload_hashes": [],
        "payload_refs_redacted": True,
        "package_review_state": None,
        "package_review_submit_record_ref": None,
        "handoff_export_state": None,
        "handoff_export_prepare_record_ref": None,
        "handoff_target": None,
        "export_mode": None,
        "external_export_download_record_ref": None,
        "external_export_download_state": None,
        "external_export_download_target": None,
        "export_download_descriptor_ref": None,
        "download_mode": None,
        "package_review_submit_enabled": False,
        "handoff_enabled": False,
        "export_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        "status_defects": [],
        "next_allowed_actions": [
            "commit_source_directory_hybrid_context_packet_qualitative_analysis_package"
        ],
    }
    snapshot = db.get(L3MaterialSnapshot, str(analysis["material_snapshot_id"]))
    if snapshot is None:
        return {
            **base,
            "next_allowed_actions": [],
            "status_defects": ["material_snapshot_not_found"],
        }
    session = db.get(L3Session, snapshot.session_id)
    if session is None:
        return {
            **base,
            "next_allowed_actions": [],
            "status_defects": ["session_not_found"],
        }
    reconciliation = _matching_hybrid_package_reconciliation(
        db,
        session_id=session.session_id,
        analysis=analysis,
    )
    if reconciliation is None:
        return base

    summary = reconciliation.summary_json or {}
    if not isinstance(summary, dict):
        return {
            **base,
            "next_allowed_actions": [],
            "status_defects": ["reconciliation_summary_invalid"],
        }
    commit_summary = summary.get("source_directory_hybrid_context_qualitative_package_commit")
    if not isinstance(commit_summary, dict):
        return base

    packages = _hybrid_status_packages(
        db,
        session_id=session.session_id,
        reconciliation_record_id=reconciliation.reconciliation_record_id,
    )
    complete_package_set = (
        len(packages) == len(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
        and {package.package_kind for package in packages}
        == set(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
    )
    if not complete_package_set:
        return {
            **base,
            "reconciliation_record_id": reconciliation.reconciliation_record_id,
            "next_allowed_actions": [],
            "status_defects": ["source_directory_hybrid_package_set_incomplete"],
        }

    construction_basis_hash = str(
        commit_summary.get("construction_basis_hash")
        or next(
            (
                str((package.summary_json or {}).get("construction_basis_hash") or "")
                for package in packages
                if str((package.summary_json or {}).get("construction_basis_hash") or "")
            ),
            "",
        )
        or commit_summary.get("authority_basis_hash")
        or ""
    )
    package_state = {
        **base,
        "source_directory_hybrid_package_commit_available": True,
        "reconciliation_record_id": reconciliation.reconciliation_record_id,
        "construction_basis_hash": construction_basis_hash,
        "output_packages": [
            {
                "output_package_id": package.output_package_id,
                "package_kind": package.package_kind,
                "status": package.status,
                "payload_hash": package.payload_hash,
                "payload_ref_redacted": True,
            }
            for package in packages
        ],
        "output_package_ids": [package.output_package_id for package in packages],
        "package_kinds": [package.package_kind for package in packages],
        "payload_hashes": [package.payload_hash for package in packages],
        "package_review_submit_enabled": True,
        "downstream_unavailable": list(PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE),
        "next_allowed_actions": ["submit_package_review"],
    }
    submit_state = summary.get("package_review_submit")
    if not isinstance(submit_state, dict):
        return package_state

    package_review_state = str(submit_state.get("package_review_state") or "")
    submit_available = (
        str(submit_state.get("schema_id") or "") == PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID
        and str(submit_state.get("package_review_submit_schema_id") or "")
        == PACKAGE_REVIEW_SUBMIT_SCHEMA_ID
    )
    if not submit_available:
        return {
            **package_state,
            "package_review_submit_enabled": False,
            "next_allowed_actions": [],
            "status_defects": ["package_review_submit_state_invalid"],
        }

    handoff_allowed = package_review_state == PACKAGE_REVIEW_APPROVED_STATE
    review_state = {
        **package_state,
        "source_directory_hybrid_package_review_submit_available": True,
        "package_review_state": package_review_state,
        "package_review_submit_record_ref": submit_state.get("submit_record_ref"),
        "package_review_submit_enabled": False,
        "handoff_enabled": handoff_allowed,
        "export_enabled": handoff_allowed,
        "downstream_unavailable": (
            [
                item
                for item in PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE
                if item not in {"handoff", "export"}
            ]
            if handoff_allowed
            else list(PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE)
        ),
        "next_allowed_actions": ["prepare_handoff_export"] if handoff_allowed else [],
    }
    prepare_state = summary.get("handoff_export_prepare")
    if not isinstance(prepare_state, dict):
        return review_state

    prepare_available = (
        str(prepare_state.get("schema_id") or "") == HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID
        and str(prepare_state.get("handoff_export_prepare_schema_id") or "")
        == HANDOFF_EXPORT_PREPARE_SCHEMA_ID
    )
    if not prepare_available:
        return {
            **review_state,
            "handoff_enabled": False,
            "export_enabled": False,
            "next_allowed_actions": [],
            "status_defects": ["handoff_export_prepare_state_invalid"],
        }
    handoff_state = {
        **review_state,
        "source_directory_hybrid_handoff_export_prepare_available": True,
        "handoff_export_state": prepare_state.get("handoff_export_state"),
        "handoff_export_prepare_record_ref": prepare_state.get("prepare_record_ref"),
        "handoff_target": prepare_state.get("handoff_target"),
        "export_mode": prepare_state.get("export_mode"),
        "handoff_enabled": False,
        "export_enabled": False,
        "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        "next_allowed_actions": [],
    }
    readiness_state = summary.get("external_export_download_prepare")
    if not isinstance(readiness_state, dict):
        return handoff_state

    readiness_available = (
        str(readiness_state.get("schema_id") or "") == EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID
        and str(readiness_state.get("external_export_download_prepare_schema_id") or "")
        == EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID
    )
    if not readiness_available:
        return {
            **handoff_state,
            "next_allowed_actions": [],
            "status_defects": ["external_export_download_prepare_state_invalid"],
        }
    return {
        **handoff_state,
        "source_directory_hybrid_external_export_download_prepare_available": True,
        "external_export_download_record_ref": readiness_state.get("external_export_download_record_ref"),
        "external_export_download_state": readiness_state.get("external_export_download_state"),
        "external_export_download_target": readiness_state.get("external_export_download_target"),
        "export_download_descriptor_ref": readiness_state.get("export_download_descriptor_ref"),
        "download_mode": readiness_state.get("download_mode"),
        "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_DOWNSTREAM_UNAVAILABLE),
        "next_allowed_actions": [],
    }


def _matching_hybrid_package_reconciliation(
    db: Session,
    *,
    session_id: str,
    analysis: Mapping[str, Any],
) -> L3ReconciliationRecord | None:
    records = (
        db.query(L3ReconciliationRecord)
        .filter(L3ReconciliationRecord.session_id == session_id)
        .all()
    )
    for record in records:
        summary = record.summary_json or {}
        if not isinstance(summary, dict):
            continue
        if (
            str(summary.get("source_gate") or "")
            != SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE
        ):
            continue
        commit_summary = summary.get("source_directory_hybrid_context_qualitative_package_commit")
        if not isinstance(commit_summary, dict):
            continue
        authority_basis = commit_summary.get("authority_basis")
        if not isinstance(authority_basis, dict):
            authority_basis = {}
        source_authority = authority_basis.get("source_authority")
        if not isinstance(source_authority, dict):
            source_authority = {}
        expected = {
            "hybrid_context_packet_hash": analysis["hybrid_context_packet_hash"],
            "lexical_context_packet_hash": analysis["lexical_context_packet_hash"],
            "index_authority_hash": analysis["index_authority_hash"],
            "embedding_index_authority_hash": analysis["embedding_index_authority_hash"],
            "source_ingestion_batch_id": analysis["source_ingestion_batch_id"],
            "source_ingestion_file_id": analysis["source_ingestion_file_id"],
            "material_snapshot_id": analysis["material_snapshot_id"],
            "content_sha256": analysis["content_sha256"],
            "file_identity_hash": analysis["file_identity_hash"],
            "payload_hash": analysis["payload_hash"],
        }
        actual_fields = {
            field: str(
                commit_summary.get(field)
                or authority_basis.get(field)
                or source_authority.get(field)
                or ""
            )
            for field in expected
        }
        matched_fields = {
            field for field, value in expected.items() if actual_fields[field] == str(value)
        }
        mismatched_fields = {
            field
            for field, value in expected.items()
            if actual_fields[field] and actual_fields[field] != str(value)
        }
        required_matches = {"hybrid_context_packet_hash", "embedding_index_authority_hash"}
        if not mismatched_fields and required_matches <= matched_fields:
            return record
    return None


def _hybrid_status_packages(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
) -> list[L3OutputPackage]:
    packages = (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation_record_id,
        )
        .all()
    )
    review_order = {kind: index for index, kind in enumerate(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)}
    return sorted(
        packages,
        key=lambda package: review_order.get(package.package_kind, len(review_order)),
    )


def _load_material_snapshot_for_commit(
    db: Session,
    *,
    material_snapshot_id: str,
    source_authority: Mapping[str, Any],
) -> L3MaterialSnapshot:
    snapshot = db.get(L3MaterialSnapshot, material_snapshot_id)
    if snapshot is None:
        raise SourceDirectoryHybridPackageCommitError(
            "source_directory_hybrid_package_commit_material_snapshot_not_found",
            "No material snapshot exists for the source-directory hybrid package commit.",
            http_status=404,
            details={"material_snapshot_id": material_snapshot_id},
        )
    mismatches = [
        field
        for field, expected in {
            "material_snapshot_id": snapshot.material_snapshot_id,
            "payload_hash": snapshot.payload_hash,
        }.items()
        if str(source_authority.get(field) or "") != str(expected)
    ]
    if mismatches:
        raise SourceDirectoryHybridPackageCommitError(
            "source_directory_hybrid_package_commit_material_authority_mismatch",
            "The source-directory hybrid package commit source authority does not match the material snapshot.",
            http_status=409,
            details={"blocked_fields": mismatches},
        )
    return snapshot


def _load_package_commit_session(db: Session, *, material_snapshot: L3MaterialSnapshot) -> L3Session:
    session = db.get(L3Session, material_snapshot.session_id)
    if session is None:
        raise SourceDirectoryHybridPackageCommitError(
            "source_directory_hybrid_package_commit_session_not_found",
            "No Layer 3 session owns the source-directory material snapshot.",
            http_status=404,
            details={"session_id": material_snapshot.session_id},
        )
    if session.status not in FINALIZED_PACKAGE_SESSION_STATUSES or session.completed_at is None:
        raise SourceDirectoryHybridPackageCommitError(
            "source_directory_hybrid_package_commit_session_not_terminal",
            "Source-directory hybrid package construction requires a finalized Layer 3 material session.",
            http_status=409,
            details={"session_id": session.session_id, "status": session.status},
        )
    return session


def _load_material_snapshot_for_submit(
    db: Session,
    *,
    material_snapshot_id: str,
    source_authority: Mapping[str, Any],
) -> L3MaterialSnapshot:
    try:
        return _load_material_snapshot_for_commit(
            db,
            material_snapshot_id=material_snapshot_id,
            source_authority=source_authority,
        )
    except SourceDirectoryHybridPackageCommitError as exc:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            exc.code.replace("package_commit", "package_review_submit"),
            exc.message.replace("package commit", "package-review submit"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_package_review_submit_session(db: Session, *, material_snapshot: L3MaterialSnapshot) -> L3Session:
    try:
        return _load_package_commit_session(db, material_snapshot=material_snapshot)
    except SourceDirectoryHybridPackageCommitError as exc:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            exc.code.replace("package_commit", "package_review_submit"),
            exc.message.replace("package construction", "package-review submit"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_material_snapshot_for_handoff_export_prepare(
    db: Session,
    *,
    material_snapshot_id: str,
    source_authority: Mapping[str, Any],
) -> L3MaterialSnapshot:
    try:
        return _load_material_snapshot_for_commit(
            db,
            material_snapshot_id=material_snapshot_id,
            source_authority=source_authority,
        )
    except SourceDirectoryHybridPackageCommitError as exc:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            exc.code.replace("package_commit", "handoff_export_prepare"),
            exc.message.replace("package commit", "handoff/export prepare"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_material_snapshot_for_external_export_download_prepare(
    db: Session,
    *,
    material_snapshot_id: str,
    source_authority: Mapping[str, Any],
) -> L3MaterialSnapshot:
    try:
        return _load_material_snapshot_for_commit(
            db,
            material_snapshot_id=material_snapshot_id,
            source_authority=source_authority,
        )
    except SourceDirectoryHybridPackageCommitError as exc:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            exc.code.replace("package_commit", "external_export_download_prepare"),
            exc.message.replace("package commit", "external export/download prepare"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_handoff_export_prepare_session(db: Session, *, material_snapshot: L3MaterialSnapshot) -> L3Session:
    try:
        return _load_package_commit_session(db, material_snapshot=material_snapshot)
    except SourceDirectoryHybridPackageCommitError as exc:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            exc.code.replace("package_commit", "handoff_export_prepare"),
            exc.message.replace("package construction", "handoff/export prepare"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _load_external_export_download_prepare_session(
    db: Session,
    *,
    material_snapshot: L3MaterialSnapshot,
) -> L3Session:
    try:
        return _load_package_commit_session(db, material_snapshot=material_snapshot)
    except SourceDirectoryHybridPackageCommitError as exc:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            exc.code.replace("package_commit", "external_export_download_prepare"),
            exc.message.replace("package construction", "external export/download prepare"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _source_directory_hybrid_review_packages(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
) -> list[L3OutputPackage]:
    packages = (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation_record_id,
        )
        .with_for_update()
        .all()
    )
    if (
        len(packages) != len(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
        or {package.package_kind for package in packages} != set(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)
    ):
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_requires_complete_package_set",
            "Package-review submit requires exactly the constructed canonical_internal, user_facing, and review_facing packages.",
            http_status=409,
            details={"blocked_fields": ["output_package_ids"]},
        )
    review_order = {kind: index for index, kind in enumerate(PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS)}
    return sorted(packages, key=lambda package: review_order[package.package_kind])


def _source_directory_hybrid_review_packages_for_handoff_export_prepare(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
) -> list[L3OutputPackage]:
    try:
        return _source_directory_hybrid_review_packages(
            db,
            session_id=session_id,
            reconciliation_record_id=reconciliation_record_id,
        )
    except SourceDirectoryHybridPackageReviewSubmitError as exc:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            exc.code.replace("package_review_submit", "handoff_export_prepare"),
            exc.message.replace("Package-review submit", "Handoff/export prepare"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _source_directory_hybrid_review_packages_for_external_export_download_prepare(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
) -> list[L3OutputPackage]:
    try:
        return _source_directory_hybrid_review_packages(
            db,
            session_id=session_id,
            reconciliation_record_id=reconciliation_record_id,
        )
    except SourceDirectoryHybridPackageReviewSubmitError as exc:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            exc.code.replace("package_review_submit", "external_export_download_prepare"),
            exc.message.replace("Package-review submit", "External export/download prepare"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _source_directory_hybrid_review_packages_for_external_export_download_delivery(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
) -> list[L3OutputPackage]:
    try:
        return _source_directory_hybrid_review_packages(
            db,
            session_id=session_id,
            reconciliation_record_id=reconciliation_record_id,
        )
    except SourceDirectoryHybridPackageReviewSubmitError as exc:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            exc.code.replace("package_review_submit", "external_export_download_delivery"),
            exc.message.replace("Package-review submit", "External export/download delivery"),
            http_status=exc.http_status,
            details=exc.details,
        ) from exc


def _submit_string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list):
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_list_field_invalid",
            "Package-review submit list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    normalized = [str(item or "").strip() for item in value]
    if not normalized or any(not item for item in normalized):
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_list_field_invalid",
            "Package-review submit list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    return normalized


def _handoff_string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list):
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_list_field_invalid",
            "Handoff/export prepare list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    normalized = [str(item or "").strip() for item in value]
    if not normalized or any(not item for item in normalized):
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_list_field_invalid",
            "Handoff/export prepare list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    return normalized


def _external_export_download_prepare_string_list(value: Any, *, field: str) -> list[str]:
    if not isinstance(value, list):
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_list_field_invalid",
            "External export/download prepare list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    normalized = [str(item or "").strip() for item in value]
    if not normalized or any(not item for item in normalized):
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_list_field_invalid",
            "External export/download prepare list fields must be supplied as non-empty string lists.",
            details={"field": field},
        )
    return normalized


def _package_review_submit_response(
    *,
    request_id: str,
    status: str,
    session: L3Session,
    material_snapshot: L3MaterialSnapshot,
    qualitative_analysis: Mapping[str, Any],
    reconciliation: L3ReconciliationRecord,
    packages: list[L3OutputPackage],
    submit_state: Mapping[str, Any],
) -> dict[str, Any]:
    handoff_prepare_enabled = submit_state["package_review_state"] == PACKAGE_REVIEW_APPROVED_STATE
    downstream_unavailable = (
        [item for item in PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE if item not in {"handoff", "export"}]
        if handoff_prepare_enabled
        else list(PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE)
    )
    return {
        "schema_id": PACKAGE_REVIEW_SUBMIT_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": PACKAGE_REVIEW_SUBMIT_MODE,
        "status": status,
        "operator_decision": submit_state["operator_decision"],
        "decision_notes": submit_state.get("decision_notes"),
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "embedding_index_authority_hash": qualitative_analysis["embedding_index_authority_hash"],
        "lexical_context_packet_hash": qualitative_analysis["lexical_context_packet_hash"],
        "hybrid_context_packet_hash": qualitative_analysis["hybrid_context_packet_hash"],
        "qualitative_analysis_hash": qualitative_analysis["qualitative_analysis_hash"],
        "source_directory_hybrid_package_review_preview_hash": submit_state["package_review_preview_hash"],
        "construction_basis_hash": submit_state["construction_basis_hash"],
        "reconciliation_record_id": reconciliation.reconciliation_record_id,
        "output_packages": [
            {
                "output_package_id": package.output_package_id,
                "package_kind": package.package_kind,
                "status": package.status,
                "payload_hash": package.payload_hash,
                "payload_ref_redacted": True,
            }
            for package in packages
        ],
        "output_package_ids": [package.output_package_id for package in packages],
        "package_kinds": [package.package_kind for package in packages],
        "payload_hashes": [package.payload_hash for package in packages],
        "payload_refs_redacted": True,
        "package_review_state": submit_state["package_review_state"],
        "submit_record_ref": submit_state["submit_record_ref"],
        "package_review_submit_enabled": False,
        "handoff_enabled": handoff_prepare_enabled,
        "export_enabled": handoff_prepare_enabled,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "package_construction_source_gate": SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "downstream_unavailable": downstream_unavailable,
        "next_state": submit_state["package_review_state"],
        "next_allowed_actions": ["prepare_handoff_export"] if handoff_prepare_enabled else [],
        "negative_invariants": {
            "package_payload_rewrite_enabled": False,
            "handoff_export_enabled": handoff_prepare_enabled,
            "external_export_download_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_public_delivery_enabled": False,
            "network_egress_enabled": False,
            "frontend_durable_authority_enabled": False,
            "prompt_model_provider_runtime_enabled": False,
        },
    }


def _handoff_export_prepare_response(
    *,
    request_id: str,
    status: str,
    session: L3Session,
    material_snapshot: L3MaterialSnapshot,
    qualitative_analysis: Mapping[str, Any],
    reconciliation: L3ReconciliationRecord,
    packages: list[L3OutputPackage],
    prepare_state: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_id": HANDOFF_EXPORT_PREPARE_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": HANDOFF_EXPORT_PREPARE_MODE,
        "status": status,
        "operator_decision": prepare_state["operator_decision"],
        "decision_notes": prepare_state.get("decision_notes"),
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "embedding_index_authority_hash": qualitative_analysis["embedding_index_authority_hash"],
        "lexical_context_packet_hash": qualitative_analysis["lexical_context_packet_hash"],
        "hybrid_context_packet_hash": qualitative_analysis["hybrid_context_packet_hash"],
        "qualitative_analysis_hash": qualitative_analysis["qualitative_analysis_hash"],
        "source_directory_hybrid_package_review_preview_hash": prepare_state["package_review_preview_hash"],
        "construction_basis_hash": prepare_state["construction_basis_hash"],
        "reconciliation_record_id": reconciliation.reconciliation_record_id,
        "output_packages": [
            {
                "output_package_id": package.output_package_id,
                "package_kind": package.package_kind,
                "status": package.status,
                "payload_hash": package.payload_hash,
                "payload_ref_redacted": True,
            }
            for package in packages
        ],
        "output_package_ids": [package.output_package_id for package in packages],
        "package_kinds": [package.package_kind for package in packages],
        "payload_hashes": [package.payload_hash for package in packages],
        "payload_refs_redacted": True,
        "package_review_state": prepare_state["package_review_state"],
        "package_review_submit_record_ref": prepare_state["package_review_submit_record_ref"],
        "handoff_export_state": prepare_state["handoff_export_state"],
        "prepare_record_ref": prepare_state["prepare_record_ref"],
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "handoff_export_envelope": _json_clone(prepare_state["handoff_export_envelope"]),
        "handoff_enabled": False,
        "export_enabled": False,
        "external_export_download_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "package_review_submit_source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "package_construction_source_gate": SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": HANDOFF_EXPORT_PREPARE_SOURCE_GATE,
        "downstream_unavailable": list(HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE),
        "next_state": prepare_state["handoff_export_state"],
        "next_allowed_actions": [],
        "negative_invariants": {
            "external_export_download_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_public_delivery_enabled": False,
            "provider_private_signed_url_enabled": False,
            "network_egress_enabled": False,
            "frontend_durable_authority_enabled": False,
            "prompt_model_provider_runtime_enabled": False,
        },
    }


def _external_export_download_prepare_response(
    *,
    request_id: str,
    status: str,
    session: L3Session,
    material_snapshot: L3MaterialSnapshot,
    qualitative_analysis: Mapping[str, Any],
    reconciliation: L3ReconciliationRecord,
    packages: list[L3OutputPackage],
    readiness_state: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_id": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id,
        "server_time": _server_time(),
        "mode": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_MODE,
        "status": status,
        "operator_decision": readiness_state["operator_decision"],
        "decision_notes": readiness_state.get("decision_notes"),
        "session_id": session.session_id,
        "selection_manifest_id": session.selection_manifest_id,
        "material_snapshot_id": material_snapshot.material_snapshot_id,
        "source_ingestion_batch_id": qualitative_analysis["source_ingestion_batch_id"],
        "source_ingestion_file_id": qualitative_analysis["source_ingestion_file_id"],
        "content_sha256": qualitative_analysis["content_sha256"],
        "file_identity_hash": qualitative_analysis["file_identity_hash"],
        "authority_basis_hash": qualitative_analysis["authority_basis_hash"],
        "payload_hash": qualitative_analysis["payload_hash"],
        "index_authority_hash": qualitative_analysis["index_authority_hash"],
        "embedding_index_authority_hash": qualitative_analysis["embedding_index_authority_hash"],
        "lexical_context_packet_hash": qualitative_analysis["lexical_context_packet_hash"],
        "hybrid_context_packet_hash": qualitative_analysis["hybrid_context_packet_hash"],
        "qualitative_analysis_hash": qualitative_analysis["qualitative_analysis_hash"],
        "source_directory_hybrid_package_review_preview_hash": readiness_state["package_review_preview_hash"],
        "construction_basis_hash": readiness_state["construction_basis_hash"],
        "reconciliation_record_id": reconciliation.reconciliation_record_id,
        "output_packages": [
            {
                "output_package_id": package.output_package_id,
                "package_kind": package.package_kind,
                "status": package.status,
                "payload_hash": package.payload_hash,
                "payload_ref_redacted": True,
            }
            for package in packages
        ],
        "output_package_ids": [package.output_package_id for package in packages],
        "package_kinds": [package.package_kind for package in packages],
        "payload_hashes": [package.payload_hash for package in packages],
        "payload_refs_redacted": True,
        "package_review_state": readiness_state["package_review_state"],
        "package_review_submit_record_ref": readiness_state["package_review_submit_record_ref"],
        "handoff_export_state": readiness_state["handoff_export_state"],
        "prepare_record_ref": readiness_state["prepare_record_ref"],
        "handoff_export_envelope_ref": readiness_state["handoff_export_envelope_ref"],
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "external_export_download_state": readiness_state["external_export_download_state"],
        "external_export_download_record_ref": readiness_state["external_export_download_record_ref"],
        "export_download_descriptor_ref": readiness_state["export_download_descriptor_ref"],
        "external_export_download_target": EXTERNAL_EXPORT_DOWNLOAD_TARGET,
        "download_mode": EXTERNAL_EXPORT_DOWNLOAD_MODE,
        "external_export_download_descriptor": _json_clone(
            readiness_state["external_export_download_descriptor"]
        ),
        "same_origin_delivery_enabled": False,
        "browser_download_enabled": False,
        "provider_public_delivery_enabled": False,
        "provider_private_signed_url_enabled": False,
        "connector_dispatch_enabled": False,
        "network_egress_enabled": False,
        "frontend_durable_authority_enabled": False,
        "prompt_model_provider_runtime_enabled": False,
        "package_review_submit_source_gate": PACKAGE_REVIEW_SUBMIT_SOURCE_GATE,
        "package_construction_source_gate": SOURCE_DIRECTORY_HYBRID_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        "source_gate": EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SOURCE_GATE,
        "downstream_unavailable": list(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_DOWNSTREAM_UNAVAILABLE),
        "next_state": readiness_state["external_export_download_state"],
        "next_allowed_actions": [],
        "negative_invariants": {
            "same_origin_delivery_enabled": False,
            "browser_download_enabled": False,
            "provider_public_delivery_enabled": False,
            "provider_private_signed_url_enabled": False,
            "connector_dispatch_enabled": False,
            "network_egress_enabled": False,
            "frontend_durable_authority_enabled": False,
            "prompt_model_provider_runtime_enabled": False,
            "package_payload_rewrite_enabled": False,
            "source_package_row_mutation_enabled": False,
        },
    }


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryHybridAnalysisError(
            "source_directory_hybrid_context_qualitative_analysis_required_field_missing",
            "A required source-directory hybrid-context qualitative-analysis field is missing or empty.",
            details={"field": key},
        )
    return value


def _require_commit_field(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryHybridPackageCommitError(
            "source_directory_hybrid_package_commit_required_field_missing",
            "A required source-directory hybrid package commit field is missing or empty.",
            details={"field": key},
        )
    return value


def _require_submit_field(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryHybridPackageReviewSubmitError(
            "source_directory_hybrid_package_review_submit_required_field_missing",
            "A required source-directory hybrid package-review submit field is missing or empty.",
            details={"field": key},
        )
    return value


def _require_handoff_field(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryHybridHandoffExportPrepareError(
            "source_directory_hybrid_handoff_export_prepare_required_field_missing",
            "A required source-directory hybrid handoff/export prepare field is missing or empty.",
            details={"field": key},
        )
    return value


def _require_external_export_download_prepare_field(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryHybridExternalExportDownloadPrepareError(
            "source_directory_hybrid_external_export_download_prepare_required_field_missing",
            "A required source-directory hybrid external export/download prepare field is missing or empty.",
            details={"field": key},
        )
    return value


def _require_external_export_download_delivery_field(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_required_field_missing",
            "A required source-directory hybrid external export/download delivery field is missing or empty.",
            details={"field": key},
        )
    return value


def _source_directory_hybrid_package_payload_path(package: L3OutputPackage) -> Path:
    payload_ref = str(package.payload_ref or "").strip()
    if not payload_ref:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_payload_ref_missing",
            "Selected source-directory hybrid package row is missing its server-owned payload reference.",
            http_status=409,
            details={"blocked_fields": ["output_package_id"]},
        )
    artifact_root = Path(settings.artifact_storage_dir).resolve(strict=False)
    payload_path = Path(payload_ref).resolve(strict=False)
    try:
        payload_path.relative_to(artifact_root)
    except ValueError as exc:
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_payload_ref_not_server_owned",
            "Selected source-directory hybrid package payload is not under the server-owned artifact storage root.",
            http_status=409,
            details={"blocked_fields": ["output_package_id"]},
        ) from exc
    if not payload_path.is_file():
        raise SourceDirectoryHybridExternalExportDownloadDeliveryError(
            "source_directory_hybrid_external_export_download_delivery_payload_ref_not_found",
            "Selected source-directory hybrid package payload artifact was not found.",
            http_status=404,
            details={"blocked_fields": ["output_package_id"]},
        )
    return payload_path


def _source_directory_hybrid_delivery_filename(*, session_id: str, package_kind: str) -> str:
    session_token = _safe_delivery_token(session_id, fallback="session")
    kind_token = _safe_delivery_token(package_kind, fallback="package")
    return f"layer3-source-directory-hybrid-{session_token}-{kind_token}.json"


def _safe_delivery_token(value: str, *, fallback: str) -> str:
    token = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in str(value or "").strip())
    token = token.strip(".-")
    return (token or fallback)[:96]


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
