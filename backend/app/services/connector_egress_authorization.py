from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
import hashlib
import ipaddress
from itertools import islice
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any, Literal, NoReturn, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.requests import Request

from app.core.config import BACKEND_ROOT, Settings, settings
from app.schemas.api import (
    SINGLE_SEND_DETECTION_ALLOWANCE_BYTES as SINGLE_SEND_DETECTION_ALLOWANCE_BYTES,
    ConnectorCampaignDefinitionRefV1,
    ConnectorCampaignEvidenceIndexV1,
    ConnectorCampaignLogCaptureRefV1,
    ConnectorEgressGrantV1,
    ConnectorGrantConsumptionMarkerV1,
    ConnectorGrantEvidenceRefV1,
    DualLiveCampaignDefinitionV1,
    expected_grant_rule_payloads,
)
from app.services.layer3_sec_xbrl_in_app_auth_policy import (
    SecXbrlInAppAuthPolicyError,
    route_level_operator_authorization_required,
)

MAX_PROTECTED_JSON_BYTES = 64 * 1024
MAX_EVIDENCE_INDEX_REVISIONS = 128
MAX_EVIDENCE_CAMPAIGN_ARCHIVES = 128
MAX_EVIDENCE_GRANT_ARCHIVES = 256
MAX_EVIDENCE_LOG_CAPTURE_REFS = 128
AUTHORIZATION_RECEIPT_SCHEMA_ID: Literal[
    "project6.connector_egress_authorization_receipt.v1"
] = "project6.connector_egress_authorization_receipt.v1"
_HEX = frozenset("0123456789abcdef")
_INDEX_DIR = "indexes"
_EXPECTED_CONNECTORS = frozenset({"sciencebase_mcs", "nrc_adams_aps"})
_FORWARDED_IDENTITY_HEADERS = frozenset(
    {
        "forwarded",
        "x-forwarded-for",
        "x-forwarded-host",
        "x-forwarded-proto",
        "x-forwarded-port",
        "x-forwarded-user",
        "x-forwarded-email",
        "x-forwarded-groups",
        "x-forwarded-roles",
        "x-real-ip",
    }
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class ConnectorEgressAuthorizationError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
        http_status: int = 403,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})
        self.http_status = http_status


@dataclass(frozen=True, slots=True)
class VerifiedEvidenceIndexRevision:
    model: ConnectorCampaignEvidenceIndexV1
    raw_bytes: bytes
    raw_sha256: str
    path: Path


@dataclass(frozen=True, slots=True)
class VerifiedEvidenceIndexChain:
    evidence_root: Path
    head: ConnectorCampaignEvidenceIndexV1
    head_raw_sha256: str
    head_path: Path
    revisions: tuple[VerifiedEvidenceIndexRevision, ...]


@dataclass(frozen=True, slots=True)
class VerifiedDualLiveCampaignDefinition:
    model: DualLiveCampaignDefinitionV1
    raw_bytes: bytes
    raw_sha256: str
    canonical_bytes: bytes
    canonical_fingerprint: str
    introduction_index_revision: int
    introduction_index_sha256: str
    evidence_root: Path
    definition_archive_path: Path
    index_chain: VerifiedEvidenceIndexChain


@dataclass(frozen=True, slots=True)
class VerifiedConnectorGrant:
    model: ConnectorEgressGrantV1
    raw_bytes: bytes
    raw_sha256: str
    canonical_bytes: bytes
    canonical_fingerprint: str
    verified_campaign: VerifiedDualLiveCampaignDefinition
    grant_archive_path: Path
    consumption_marker_path: Path
    consumption_marker_sha256: str
    consumption_marker_present: bool


@dataclass(frozen=True, slots=True)
class VerifiedHistoricalGrantEvidence:
    definition_model: DualLiveCampaignDefinitionV1
    model: ConnectorEgressGrantV1
    raw_definition_sha256: str
    canonical_campaign_fingerprint: str
    raw_sha256: str
    canonical_fingerprint: str
    introduction_index_revision: int
    introduction_index_sha256: str
    definition_archive_path: Path
    grant_archive_path: Path
    marker_model: ConnectorGrantConsumptionMarkerV1
    consumption_marker_path: Path
    consumption_marker_sha256: str
    index_chain: VerifiedEvidenceIndexChain


class ConnectorEgressAuthorizationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_id: Literal[
        "project6.connector_egress_authorization_receipt.v1"
    ] = AUTHORIZATION_RECEIPT_SCHEMA_ID
    connector_key: Literal["sciencebase_mcs", "nrc_adams_aps"]
    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    grant_sha256: str
    canonical_grant_fingerprint: str
    introduction_index_revision: int
    introduction_index_sha256: str
    operator_ref_hash: str
    workspace_ref_hash: str
    auth_owner_mode: str
    authorization_mode: Literal["identity_presence", "role_enforcing"]
    role: Literal["owner"] | None
    access: Literal["write"]


def _canonical_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _canonical_value(value.model_dump(mode="python"))
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_value(asdict(value))
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("canonical JSON rejects naive datetime values")
        normalized = value.astimezone(UTC)
        return normalized.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("canonical JSON requires string object keys")
            result[key] = _canonical_value(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON rejects non-finite numbers")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"canonical JSON cannot encode {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def strict_json_loads(value: bytes | str) -> Any:
    if isinstance(value, bytes):
        try:
            text = value.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("protected JSON must be strict UTF-8") from exc
    elif isinstance(value, str):
        text = value
    else:
        raise TypeError("strict_json_loads accepts bytes or str")

    def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON member: {key}")
            result[key] = item
        return result

    def _nonfinite(token: str) -> None:
        raise ValueError(f"JSON number must be finite: {token}")

    try:
        return json.loads(
            text,
            object_pairs_hook=_object,
            parse_constant=_nonfinite,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed protected JSON: {exc.msg}") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalized_sha256(value: object, *, label: str) -> str:
    normalized = str(value or "").strip().lower()
    if len(normalized) != 64 or any(char not in _HEX for char in normalized):
        raise ConnectorEgressAuthorizationError(
            "connector_egress_invalid_sha256",
            f"{label} must be a lowercase 64-hex SHA-256.",
            http_status=409,
        )
    return normalized


def _fail(
    code: str,
    message: str,
    *,
    details: Mapping[str, Any] | None = None,
    http_status: int = 409,
) -> NoReturn:
    raise ConnectorEgressAuthorizationError(
        code,
        message,
        details=details,
        http_status=http_status,
    )


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _assert_fixed_local_path_before_touch(path: Path | str, *, label: str) -> Path:
    if os.name != "nt":
        return Path(path)
    from app.services.dual_live_windows import (
        DualLiveWindowsError,
        assert_fixed_local_no_reparse_path_before_open,
    )

    try:
        return assert_fixed_local_no_reparse_path_before_open(
            path,
            code="connector_egress_protected_path_invalid",
        )
    except DualLiveWindowsError as exc:
        _fail(
            "connector_egress_protected_path_invalid",
            f"{label} must be on a fixed local Windows volume.",
        )
        raise AssertionError("unreachable") from exc


def _assert_opened_fixed_local(
    handle: Any,
    *,
    expected_path: Path,
    label: str,
) -> None:
    if os.name != "nt":
        return
    import msvcrt

    from app.services.dual_live_windows import (
        DualLiveWindowsError,
        assert_open_handle_local_fixed,
    )

    try:
        assert_open_handle_local_fixed(
            int(msvcrt.get_osfhandle(handle.fileno())),
            expected_path=expected_path,
            code="connector_egress_protected_path_invalid",
        )
    except (DualLiveWindowsError, OSError) as exc:
        raise ConnectorEgressAuthorizationError(
            "connector_egress_protected_path_invalid",
            f"{label} opened outside its fixed local Windows path.",
            http_status=409,
        ) from exc


def _sqlite_database_path(
    settings_override: Settings | None = None,
) -> Path | None:
    configuration = settings if settings_override is None else settings_override
    raw = str(configuration.database_url or "")
    if not raw.startswith("sqlite:///"):
        return None
    value = raw[len("sqlite:///") :]
    if not value or value == ":memory:" or value.startswith("file:"):
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = BACKEND_ROOT / candidate
    _assert_fixed_local_path_before_touch(candidate, label="database path")
    return candidate.resolve(strict=False)


def _forbidden_path(
    path: Path,
    *,
    settings_override: Settings | None = None,
) -> bool:
    configuration = settings if settings_override is None else settings_override
    _assert_fixed_local_path_before_touch(path, label="protected path")
    storage_path = _assert_fixed_local_path_before_touch(
        configuration.storage_dir,
        label="storage directory",
    )
    resolved = path.resolve(strict=False)
    roots = {
        BACKEND_ROOT.parent.resolve(strict=False),
        storage_path.resolve(strict=False),
        (BACKEND_ROOT / "app" / "review_ui" / "static").resolve(strict=False),
    }
    if any(_is_relative_to(resolved, root) for root in roots):
        return True
    database_path = _sqlite_database_path(configuration)
    return database_path is not None and resolved == database_path


def _has_alternate_data_stream(path: Path) -> bool:
    text = str(path)
    if os.name != "nt":
        return False
    drive, tail = os.path.splitdrive(text)
    return ":" in tail


def _assert_no_reparse_components(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for part in parts:
        current = current / part
        try:
            info = os.lstat(current)
        except OSError:
            _fail(
                "connector_egress_protected_path_unavailable",
                "Protected path is missing or unavailable.",
            )
        attrs = int(getattr(info, "st_file_attributes", 0))
        reparse_flag = int(
            getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        )
        if stat.S_ISLNK(info.st_mode) or attrs & reparse_flag:
            _fail(
                "connector_egress_protected_path_reparse",
                "Protected path cannot contain a symlink or reparse point.",
            )


def _protected_directory(
    path_value: Path | str | None,
    *,
    label: str,
    settings_override: Settings | None = None,
) -> Path:
    if path_value is None:
        _fail(
            "connector_egress_missing_configuration",
            f"{label} is required for live egress.",
        )
    path = _assert_fixed_local_path_before_touch(path_value, label=label)
    if not path.is_absolute() or _has_alternate_data_stream(path):
        _fail(
            "connector_egress_protected_path_invalid",
            f"{label} must be an absolute protected path.",
        )
    _assert_no_reparse_components(path)
    resolved = path.resolve(strict=True)
    if not resolved.is_dir() or _forbidden_path(
        resolved,
        settings_override=settings_override,
    ):
        _fail(
            "connector_egress_protected_path_invalid",
            f"{label} must be a protected directory outside application roots.",
        )
    return resolved


def _read_protected_bytes(
    path_value: Path | str | None,
    *,
    expected_sha256: object,
    label: str,
    settings_override: Settings | None = None,
) -> tuple[Path, bytes, str]:
    expected = _normalized_sha256(expected_sha256, label=f"{label} digest")
    if path_value is None:
        _fail(
            "connector_egress_missing_configuration",
            f"{label} path is required for live egress.",
        )
    path = _assert_fixed_local_path_before_touch(
        path_value,
        label=f"{label} path",
    )
    if not path.is_absolute() or _has_alternate_data_stream(path):
        _fail(
            "connector_egress_protected_path_invalid",
            f"{label} path must be absolute and protected.",
        )
    _assert_no_reparse_components(path)
    resolved = path.resolve(strict=True)
    if _forbidden_path(
        resolved,
        settings_override=settings_override,
    ):
        _fail(
            "connector_egress_protected_path_invalid",
            f"{label} path is inside a forbidden application root.",
        )
    before = os.stat(resolved, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):
        _fail(
            "connector_egress_protected_file_invalid",
            f"{label} must be a regular file.",
        )
    if before.st_size > MAX_PROTECTED_JSON_BYTES:
        _fail(
            "connector_egress_protected_file_oversized",
            f"{label} exceeds the 64 KiB protected-input ceiling.",
        )
    try:
        with resolved.open("rb") as handle:
            _assert_opened_fixed_local(
                handle,
                expected_path=resolved,
                label=label,
            )
            opened = os.fstat(handle.fileno())
            data = handle.read(MAX_PROTECTED_JSON_BYTES + 1)
    except OSError as exc:
        raise ConnectorEgressAuthorizationError(
            "connector_egress_protected_file_unreadable",
            f"{label} could not be read.",
            http_status=409,
        ) from exc
    after = os.stat(resolved, follow_symlinks=False)
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
    if any(
        getattr(before, field, None) != getattr(opened, field, None)
        or getattr(opened, field, None) != getattr(after, field, None)
        for field in stable_fields
    ):
        _fail(
            "connector_egress_protected_file_changed",
            f"{label} changed while it was being verified.",
        )
    if len(data) > MAX_PROTECTED_JSON_BYTES or len(data) != before.st_size:
        _fail(
            "connector_egress_protected_file_oversized",
            f"{label} exceeds or changed across the protected read.",
        )
    actual = _sha256(data)
    if actual != expected:
        _fail(
            "connector_egress_protected_file_digest_mismatch",
            f"{label} raw-byte SHA-256 does not match configuration.",
        )
    return resolved, data, actual


def _parse_model(data: bytes, model_type: type[ModelT], *, label: str) -> ModelT:
    try:
        payload = strict_json_loads(data)
        if not isinstance(payload, dict):
            raise ValueError("protected JSON root must be an object")
        return model_type.model_validate(payload)
    except (ValueError, ValidationError) as exc:
        raise ConnectorEgressAuthorizationError(
            "connector_egress_protected_json_invalid",
            f"{label} is invalid: {exc}",
            http_status=409,
        ) from exc


def _safe_relative_path(value: str, *, label: str) -> str:
    raw = str(value or "")
    normalized = raw.replace("\\", "/")
    if (
        not normalized
        or normalized.startswith("/")
        or normalized.endswith("/")
        or "//" in normalized
        or "\x00" in normalized
        or ":" in normalized
        or any(ord(char) < 32 for char in normalized)
    ):
        _fail(
            "connector_egress_index_path_invalid",
            f"{label} is not a safe relative path.",
        )
    parts = PurePosixPath(normalized).parts
    if any(part in {"", ".", ".."} for part in parts):
        _fail(
            "connector_egress_index_path_invalid",
            f"{label} cannot traverse the evidence root.",
        )
    return "/".join(parts)


def _resolve_evidence_path(
    root: Path,
    relative_path: str,
    *,
    label: str,
    must_exist: bool,
) -> Path:
    normalized = _safe_relative_path(relative_path, label=label)
    candidate = root.joinpath(*PurePosixPath(normalized).parts)
    _assert_fixed_local_path_before_touch(
        candidate if must_exist else candidate.parent,
        label=label,
    )
    resolved = candidate.resolve(strict=must_exist)
    if not _is_relative_to(resolved, root):
        _fail(
            "connector_egress_index_path_escape",
            f"{label} escapes the protected evidence root.",
        )
    if must_exist:
        _assert_no_reparse_components(candidate)
    else:
        _assert_no_reparse_components(candidate.parent)
    return resolved


def validate_exact_rule_matrix(grant: ConnectorEgressGrantV1) -> None:
    expected = expected_grant_rule_payloads(grant.connector_key)
    actual = tuple(rule.model_dump(mode="python") for rule in grant.request_rules)
    if actual != expected:
        _fail(
            f"{grant.connector_key}_egress_rule_matrix_mismatch",
            "Connector grant request rules do not equal the exact admitted matrix.",
        )


def validate_exact_rule(grant: ConnectorEgressGrantV1) -> None:
    validate_exact_rule_matrix(grant)


def _campaign_key(
    value: ConnectorCampaignDefinitionRefV1
    | ConnectorGrantEvidenceRefV1
    | ConnectorCampaignLogCaptureRefV1,
) -> tuple[str, str]:
    return (value.campaign_id, value.campaign_fingerprint)


def _validate_definition_reference_path(
    ref: ConnectorCampaignDefinitionRefV1,
) -> str:
    actual = _safe_relative_path(
        ref.definition_relative_path,
        label="campaign definition archive path",
    )
    expected = f"campaigns/{ref.raw_definition_sha256}.json"
    if actual != expected:
        _fail(
            "connector_egress_definition_archive_path_mismatch",
            "Campaign definition archive path is not content-addressed.",
        )
    return actual


def _validate_grant_reference_paths(
    ref: ConnectorGrantEvidenceRefV1,
) -> tuple[str, str]:
    grant_path = _safe_relative_path(
        ref.grant_relative_path,
        label="connector grant archive path",
    )
    marker_path = _safe_relative_path(
        ref.consumption_marker_relative_path,
        label="connector grant consumption-marker path",
    )
    if grant_path != f"grants/{ref.raw_grant_sha256}.json":
        _fail(
            "connector_egress_grant_archive_path_mismatch",
            "Connector grant archive path is not content-addressed.",
        )
    if marker_path != f"consumed/{ref.raw_grant_sha256}.json":
        _fail(
            "connector_egress_marker_path_mismatch",
            "Connector grant marker path is not keyed by the grant digest.",
        )
    return grant_path, marker_path


def _validate_log_capture_paths(
    ref: ConnectorCampaignLogCaptureRefV1,
) -> tuple[str, str, str]:
    log_dir = _safe_relative_path(
        ref.log_dir_relative_path,
        label="campaign log directory path",
    )
    manifest = _safe_relative_path(
        ref.manifest_relative_path,
        label="campaign log manifest path",
    )
    seal = _safe_relative_path(
        ref.seal_relative_path,
        label="campaign log seal path",
    )
    fingerprint = ref.campaign_fingerprint
    if log_dir != f"logs/{fingerprint}":
        _fail(
            "connector_egress_log_directory_mismatch",
            "Campaign log directory does not equal the indexed fingerprint path.",
        )
    if manifest != f"logs/{fingerprint}/manifest.json":
        _fail(
            "connector_egress_log_manifest_path_mismatch",
            "Campaign log manifest does not equal the indexed fingerprint path.",
        )
    if seal != f"log-seals/{fingerprint}.json":
        _fail(
            "connector_egress_log_seal_path_mismatch",
            "Campaign log seal does not equal the indexed fingerprint path.",
        )
    return log_dir, manifest, seal


def _validate_index_slice_structure(
    index: ConnectorCampaignEvidenceIndexV1,
) -> None:
    if not index.campaigns:
        _fail(
            "connector_egress_index_empty",
            "Campaign evidence index cannot be empty.",
        )
    definition_keys = [_campaign_key(ref) for ref in index.campaigns]
    if len(set(definition_keys)) != len(definition_keys):
        _fail(
            "connector_egress_index_duplicate_definition",
            "Campaign evidence index has a duplicate campaign definition.",
        )
    id_to_fingerprint: dict[str, str] = {}
    fingerprint_to_id: dict[str, str] = {}
    for campaign_id, fingerprint in definition_keys:
        if id_to_fingerprint.setdefault(campaign_id, fingerprint) != fingerprint:
            _fail(
                "connector_egress_index_campaign_alias",
                "One campaign ID cannot map to multiple fingerprints.",
            )
        if fingerprint_to_id.setdefault(fingerprint, campaign_id) != campaign_id:
            _fail(
                "connector_egress_index_fingerprint_alias",
                "One campaign fingerprint cannot map to multiple IDs.",
            )

    entry_keys = [
        (
            ref.campaign_id,
            ref.campaign_fingerprint,
            ref.campaign_definition_sha256,
            ref.connector_key,
            ref.raw_grant_sha256,
            ref.canonical_grant_fingerprint,
        )
        for ref in index.entries
    ]
    if len(set(entry_keys)) != len(entry_keys):
        _fail(
            "connector_egress_index_duplicate_grant",
            "Campaign evidence index has a duplicate connector grant reference.",
        )
    if len({_campaign_key(ref) for ref in index.log_captures}) != len(
        index.log_captures
    ):
        _fail(
            "connector_egress_index_duplicate_log_capture",
            "Campaign evidence index has a duplicate log-capture reference.",
        )

    referenced_paths: list[str] = []
    for definition in index.campaigns:
        referenced_paths.append(_validate_definition_reference_path(definition))
        entries = [
            entry
            for entry in index.entries
            if _campaign_key(entry) == _campaign_key(definition)
        ]
        captures = [
            capture
            for capture in index.log_captures
            if _campaign_key(capture) == _campaign_key(definition)
        ]
        if (
            len(entries) != 2
            or {entry.connector_key for entry in entries} != _EXPECTED_CONNECTORS
            or len(captures) != 1
        ):
            _fail(
                "connector_egress_index_incomplete_slice",
                "Each campaign slice must contain one definition, two connector grants, and one log capture.",
            )
        for entry in entries:
            if (
                entry.campaign_definition_sha256
                != definition.raw_definition_sha256
                or entry.code_revision != definition.code_revision
            ):
                _fail(
                    "connector_egress_index_slice_mismatch",
                    "Grant reference does not match its campaign definition reference.",
                )
            referenced_paths.extend(_validate_grant_reference_paths(entry))
        capture = captures[0]
        if (
            capture.campaign_definition_sha256
            != definition.raw_definition_sha256
            or capture.code_revision != definition.code_revision
        ):
            _fail(
                "connector_egress_index_slice_mismatch",
                "Log-capture reference does not match its campaign definition reference.",
            )
        referenced_paths.extend(_validate_log_capture_paths(capture))

    if any(_campaign_key(ref) not in set(definition_keys) for ref in index.entries):
        _fail(
            "connector_egress_index_orphan_grant",
            "Campaign evidence index contains an orphan grant reference.",
        )
    if any(
        _campaign_key(ref) not in set(definition_keys)
        for ref in index.log_captures
    ):
        _fail(
            "connector_egress_index_orphan_log_capture",
            "Campaign evidence index contains an orphan log-capture reference.",
        )
    casefolded = [path.casefold() for path in referenced_paths]
    if len(casefolded) != len(set(casefolded)):
        _fail(
            "connector_egress_index_case_collision",
            "Campaign evidence paths collide case-insensitively.",
        )


def _validate_successor(
    predecessor: VerifiedEvidenceIndexRevision,
    successor: VerifiedEvidenceIndexRevision,
) -> None:
    previous = predecessor.model
    current = successor.model
    if current.revision != previous.revision + 1:
        _fail(
            "connector_egress_index_revision_gap",
            "Campaign evidence revisions must increment by exactly one.",
        )
    if (
        current.predecessor_index_sha256 != predecessor.raw_sha256
        or _safe_relative_path(
            str(current.predecessor_index_relative_path),
            label="predecessor index path",
        )
        != f"indexes/{predecessor.raw_sha256}.json"
    ):
        _fail(
            "connector_egress_index_predecessor_mismatch",
            "Campaign evidence successor does not bind its exact predecessor.",
        )
    if (
        current.campaigns[:-1] != previous.campaigns
        or current.entries[:-2] != previous.entries
        or current.log_captures[:-1] != previous.log_captures
        or len(current.campaigns) != len(previous.campaigns) + 1
        or len(current.entries) != len(previous.entries) + 2
        or len(current.log_captures) != len(previous.log_captures) + 1
    ):
        _fail(
            "connector_egress_index_not_strict_successor",
            "Each evidence-index successor must preserve all references and append one complete slice.",
        )
    previous_keys = {_campaign_key(ref) for ref in previous.campaigns}
    if _campaign_key(current.campaigns[-1]) in previous_keys:
        _fail(
            "connector_egress_index_slice_not_disjoint",
            "Evidence-index successor campaign slice must be disjoint.",
        )


def _load_evidence_index_chain(
    settings_override: Settings | None = None,
) -> VerifiedEvidenceIndexChain:
    configuration = settings if settings_override is None else settings_override
    root = _protected_directory(
        configuration.connector_campaign_evidence_root,
        label="CONNECTOR_CAMPAIGN_EVIDENCE_ROOT",
        settings_override=configuration,
    )
    expected_head = _normalized_sha256(
        configuration.connector_campaign_evidence_index_sha256,
        label="configured evidence-index head digest",
    )
    configured_path_value = configuration.connector_campaign_evidence_index_path
    if configured_path_value is None:
        _fail(
            "connector_egress_missing_configuration",
            "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH is required for live egress.",
        )
    configured_path = Path(configured_path_value)
    if (
        not configured_path.is_absolute()
        or _has_alternate_data_stream(configured_path)
    ):
        _fail(
            "connector_egress_index_head_path_invalid",
            "Configured evidence-index head path must be absolute.",
        )
    _assert_no_reparse_components(configured_path)
    expected_path = root / _INDEX_DIR / f"{expected_head}.json"
    if configured_path.resolve(strict=True) != expected_path.resolve(strict=True):
        _fail(
            "connector_egress_index_head_path_mismatch",
            "Configured evidence-index head path is not the content-addressed root object.",
        )
    indexes_dir = _resolve_evidence_path(
        root,
        _INDEX_DIR,
        label="evidence-index directory",
        must_exist=True,
    )
    if not indexes_dir.is_dir():
        _fail(
            "connector_egress_index_directory_invalid",
            "Protected evidence indexes path must be a directory.",
        )

    children = tuple(
        islice(indexes_dir.iterdir(), MAX_EVIDENCE_INDEX_REVISIONS + 1)
    )
    if not children:
        _fail(
            "connector_egress_index_directory_empty",
            "Protected evidence indexes directory is empty.",
        )
    if len(children) > MAX_EVIDENCE_INDEX_REVISIONS:
        _fail(
            "connector_egress_index_revision_limit_exceeded",
            "Protected evidence-index revision count exceeds its frozen ceiling.",
        )
    if len({child.name.casefold() for child in children}) != len(children):
        _fail(
            "connector_egress_index_case_collision",
            "Protected evidence index filenames collide case-insensitively.",
        )

    objects: dict[str, VerifiedEvidenceIndexRevision] = {}
    revisions: dict[int, str] = {}
    for child in children:
        name = child.name
        digest = name[:-5] if name.endswith(".json") else ""
        if (
            len(digest) != 64
            or any(char not in _HEX for char in digest)
            or name != f"{digest}.json"
        ):
            _fail(
                "connector_egress_index_filename_invalid",
                "Every protected evidence-index object must use its lowercase raw digest filename.",
            )
        path, raw_bytes, actual = _read_protected_bytes(
            child,
            expected_sha256=digest,
            label="campaign evidence-index object",
            settings_override=configuration,
        )
        model = _parse_model(
            raw_bytes,
            ConnectorCampaignEvidenceIndexV1,
            label="campaign evidence-index object",
        )
        if raw_bytes != canonical_json_bytes(model):
            _fail(
                "connector_egress_index_not_canonical",
                "Campaign evidence-index object bytes are not canonical JSON.",
            )
        _validate_index_slice_structure(model)
        if actual in objects or model.revision in revisions:
            _fail(
                "connector_egress_index_revision_collision",
                "Campaign evidence-index revisions and digests must be unique.",
            )
        item = VerifiedEvidenceIndexRevision(
            model=model,
            raw_bytes=raw_bytes,
            raw_sha256=actual,
            path=path,
        )
        objects[actual] = item
        revisions[model.revision] = actual

    if expected_head not in objects:
        _fail(
            "connector_egress_index_head_missing",
            "Configured evidence-index head object is missing.",
        )
    head = objects[expected_head]
    maximal_revision = max(revisions)
    if head.model.revision != maximal_revision:
        _fail(
            "connector_egress_index_head_rollback",
            "Configured evidence-index object is not the unique maximal revision.",
        )

    descending: list[VerifiedEvidenceIndexRevision] = []
    seen: set[str] = set()
    current = head
    while True:
        if current.raw_sha256 in seen:
            _fail(
                "connector_egress_index_cycle",
                "Campaign evidence-index predecessor chain contains a cycle.",
            )
        descending.append(current)
        seen.add(current.raw_sha256)
        if current.model.revision == 1:
            if (
                current.model.predecessor_index_sha256 is not None
                or current.model.predecessor_index_relative_path is not None
            ):
                _fail(
                    "connector_egress_index_revision_one_predecessor",
                    "Revision 1 must not name a predecessor.",
                )
            break
        predecessor_sha = current.model.predecessor_index_sha256
        if predecessor_sha is None or predecessor_sha not in objects:
            _fail(
                "connector_egress_index_predecessor_missing",
                "Campaign evidence-index predecessor object is missing.",
            )
        current = objects[predecessor_sha]

    if seen != set(objects):
        _fail(
            "connector_egress_index_not_linear",
            "Protected evidence indexes must form one gap-free linear chain with no fork or orphan.",
        )
    ascending = tuple(reversed(descending))
    if tuple(item.model.revision for item in ascending) != tuple(
        range(1, len(ascending) + 1)
    ):
        _fail(
            "connector_egress_index_revision_gap",
            "Campaign evidence-index revisions must be gap-free from revision 1.",
        )
    if len(ascending[0].model.campaigns) != 1 or (
        len(ascending[0].model.entries),
        len(ascending[0].model.log_captures),
    ) != (2, 1):
        _fail(
            "connector_egress_index_revision_one_invalid",
            "Revision 1 must contain exactly one complete campaign slice.",
        )
    for position in range(1, len(ascending)):
        _validate_successor(ascending[position - 1], ascending[position])

    chain = VerifiedEvidenceIndexChain(
        evidence_root=root,
        head=head.model,
        head_raw_sha256=head.raw_sha256,
        head_path=head.path,
        revisions=ascending,
    )
    _assert_evidence_index_chain_unchanged(
        chain,
        settings_override=configuration,
    )
    return chain


def load_evidence_index_chain_read_only(
    settings: Settings,
) -> VerifiedEvidenceIndexChain:
    if not isinstance(settings, Settings):
        _fail(
            "connector_egress_settings_invalid",
            "Read-only evidence resolution requires explicit Settings.",
        )
    return _load_evidence_index_chain(settings)


def _assert_evidence_index_chain_unchanged(
    chain: VerifiedEvidenceIndexChain,
    *,
    settings_override: Settings | None = None,
) -> None:
    indexes_dir = _resolve_evidence_path(
        chain.evidence_root,
        _INDEX_DIR,
        label="evidence-index directory revalidation",
        must_exist=True,
    )
    expected = {
        f"{revision.raw_sha256}.json": revision
        for revision in chain.revisions
    }
    children = tuple(
        islice(indexes_dir.iterdir(), MAX_EVIDENCE_INDEX_REVISIONS + 1)
    )
    if len(children) > MAX_EVIDENCE_INDEX_REVISIONS:
        _fail(
            "connector_egress_index_revision_limit_exceeded",
            "Protected evidence-index revision count exceeds its frozen ceiling.",
        )
    actual_names = tuple(sorted(child.name for child in children))
    expected_names = tuple(sorted(expected))
    if actual_names != expected_names or len(
        {name.casefold() for name in actual_names}
    ) != len(actual_names):
        _fail(
            "connector_egress_index_snapshot_changed",
            "Protected evidence-index membership changed during authority resolution.",
        )
    for name in expected_names:
        revision = expected[name]
        path, raw_bytes, actual_sha256 = _read_protected_bytes(
            indexes_dir / name,
            expected_sha256=revision.raw_sha256,
            label="campaign evidence-index snapshot object",
            settings_override=settings_override,
        )
        if (
            path != revision.path
            or raw_bytes != revision.raw_bytes
            or actual_sha256 != revision.raw_sha256
        ):
            _fail(
                "connector_egress_index_snapshot_changed",
                "Protected evidence-index bytes changed during authority resolution.",
            )
    final_children = tuple(
        islice(indexes_dir.iterdir(), MAX_EVIDENCE_INDEX_REVISIONS + 1)
    )
    if len(final_children) > MAX_EVIDENCE_INDEX_REVISIONS:
        _fail(
            "connector_egress_index_revision_limit_exceeded",
            "Protected evidence-index revision count exceeds its frozen ceiling.",
        )
    final_names = tuple(sorted(child.name for child in final_children))
    if final_names != expected_names:
        _fail(
            "connector_egress_index_snapshot_changed",
            "Protected evidence-index membership changed during final revalidation.",
        )


def _find_campaign_refs(
    chain: VerifiedEvidenceIndexChain,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
) -> tuple[
    ConnectorCampaignDefinitionRefV1,
    tuple[ConnectorGrantEvidenceRefV1, ...],
    ConnectorCampaignLogCaptureRefV1,
]:
    key = (campaign_id, campaign_fingerprint)
    definitions = [
        ref for ref in chain.head.campaigns if _campaign_key(ref) == key
    ]
    entries = [
        ref for ref in chain.head.entries if _campaign_key(ref) == key
    ]
    captures = [
        ref for ref in chain.head.log_captures if _campaign_key(ref) == key
    ]
    if (
        len(definitions) != 1
        or len(entries) != 2
        or {entry.connector_key for entry in entries} != _EXPECTED_CONNECTORS
        or len(captures) != 1
    ):
        _fail(
            "connector_egress_campaign_slice_not_found",
            "Exact complete campaign evidence slice was not found.",
        )
    return definitions[0], tuple(entries), captures[0]


def _introduction_revision(
    chain: VerifiedEvidenceIndexChain,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
) -> VerifiedEvidenceIndexRevision:
    key = (campaign_id, campaign_fingerprint)
    for revision in chain.revisions:
        definitions = [
            ref for ref in revision.model.campaigns if _campaign_key(ref) == key
        ]
        if definitions:
            entries = [
                ref for ref in revision.model.entries if _campaign_key(ref) == key
            ]
            captures = [
                ref
                for ref in revision.model.log_captures
                if _campaign_key(ref) == key
            ]
            if (
                len(definitions) != 1
                or len(entries) != 2
                or {entry.connector_key for entry in entries}
                != _EXPECTED_CONNECTORS
                or len(captures) != 1
            ):
                _fail(
                    "connector_egress_campaign_introduction_partial",
                    "Campaign introduction revision does not contain one complete slice.",
                )
            return revision
    _fail(
        "connector_egress_campaign_introduction_missing",
        "Campaign introduction revision was not found.",
    )


def _read_archived_definition(
    chain: VerifiedEvidenceIndexChain,
    ref: ConnectorCampaignDefinitionRefV1,
    *,
    settings_override: Settings | None = None,
) -> tuple[Path, bytes, DualLiveCampaignDefinitionV1, str]:
    relative_path = _validate_definition_reference_path(ref)
    archive_path = _resolve_evidence_path(
        chain.evidence_root,
        relative_path,
        label="campaign definition archive",
        must_exist=True,
    )
    path, raw_bytes, raw_sha256 = _read_protected_bytes(
        archive_path,
        expected_sha256=ref.raw_definition_sha256,
        label="archived campaign definition",
        settings_override=settings_override,
    )
    model = _parse_model(
        raw_bytes,
        DualLiveCampaignDefinitionV1,
        label="archived campaign definition",
    )
    canonical_fingerprint = _sha256(canonical_json_bytes(model))
    if (
        str(model.campaign_id) != ref.campaign_id
        or canonical_fingerprint != ref.campaign_fingerprint
        or model.code_revision != ref.code_revision
        or raw_sha256 != ref.raw_definition_sha256
    ):
        _fail(
            "connector_egress_archived_definition_mismatch",
            "Archived campaign definition does not match its exact evidence reference.",
        )
    return path, raw_bytes, model, canonical_fingerprint


def _validate_grant_intersection(
    definition: DualLiveCampaignDefinitionV1,
    grant: ConnectorEgressGrantV1,
    *,
    raw_definition_sha256: str,
    canonical_campaign_fingerprint: str,
) -> None:
    validate_exact_rule_matrix(grant)
    campaign_id = str(definition.campaign_id)
    if (
        grant.campaign_id != campaign_id
        or grant.campaign_fingerprint != canonical_campaign_fingerprint
        or grant.campaign_definition_sha256 != raw_definition_sha256
        or grant.code_revision != definition.code_revision
    ):
        _fail(
            f"{grant.connector_key}_egress_campaign_intersection_mismatch",
            "Connector grant does not intersect the exact campaign definition.",
        )
    expected_target = (
        definition.sciencebase_target
        if grant.connector_key == "sciencebase_mcs"
        else definition.nrc_target
    )
    if grant.target != expected_target:
        _fail(
            f"{grant.connector_key}_egress_target_mismatch",
            "Connector grant target does not equal the campaign target.",
        )
    if (
        grant.issued_at < definition.not_before
        or grant.expires_at > definition.expires_at
    ):
        _fail(
            f"{grant.connector_key}_egress_window_not_contained",
            "Connector grant authority window must be wholly inside the campaign window.",
        )


def _read_archived_grant(
    chain: VerifiedEvidenceIndexChain,
    ref: ConnectorGrantEvidenceRefV1,
    *,
    definition: DualLiveCampaignDefinitionV1,
    raw_definition_sha256: str,
    canonical_campaign_fingerprint: str,
    settings_override: Settings | None = None,
) -> tuple[Path, bytes, ConnectorEgressGrantV1, str]:
    grant_relative_path, _ = _validate_grant_reference_paths(ref)
    archive_path = _resolve_evidence_path(
        chain.evidence_root,
        grant_relative_path,
        label="connector grant archive",
        must_exist=True,
    )
    path, raw_bytes, raw_sha256 = _read_protected_bytes(
        archive_path,
        expected_sha256=ref.raw_grant_sha256,
        label=f"archived {ref.connector_key} connector grant",
        settings_override=settings_override,
    )
    model = _parse_model(
        raw_bytes,
        ConnectorEgressGrantV1,
        label=f"archived {ref.connector_key} connector grant",
    )
    canonical_fingerprint = _sha256(canonical_json_bytes(model))
    if (
        model.connector_key != ref.connector_key
        or model.campaign_id != ref.campaign_id
        or model.campaign_fingerprint != ref.campaign_fingerprint
        or model.campaign_definition_sha256 != ref.campaign_definition_sha256
        or model.code_revision != ref.code_revision
        or raw_sha256 != ref.raw_grant_sha256
        or canonical_fingerprint != ref.canonical_grant_fingerprint
    ):
        _fail(
            f"{ref.connector_key}_egress_archived_grant_mismatch",
            "Archived connector grant does not match its exact evidence reference.",
        )
    _validate_grant_intersection(
        definition,
        model,
        raw_definition_sha256=raw_definition_sha256,
        canonical_campaign_fingerprint=canonical_campaign_fingerprint,
    )
    return path, raw_bytes, model, canonical_fingerprint


def _validate_marker_model(
    marker: ConnectorGrantConsumptionMarkerV1,
    *,
    ref: ConnectorGrantEvidenceRefV1,
    grant: ConnectorEgressGrantV1,
) -> None:
    if (
        marker.connector_key != grant.connector_key
        or marker.campaign_id != grant.campaign_id
        or marker.campaign_fingerprint != grant.campaign_fingerprint
        or marker.campaign_definition_sha256
        != grant.campaign_definition_sha256
        or marker.raw_grant_sha256 != ref.raw_grant_sha256
        or marker.canonical_grant_fingerprint
        != ref.canonical_grant_fingerprint
        or marker.arming_nonce != grant.arming_nonce
        or marker.max_armings != 1
    ):
        _fail(
            f"{grant.connector_key}_egress_consumption_marker_mismatch",
            "Connector grant consumption marker does not match indexed authority.",
        )


def _read_marker_if_present(
    chain: VerifiedEvidenceIndexChain,
    ref: ConnectorGrantEvidenceRefV1,
    grant: ConnectorEgressGrantV1,
    *,
    required: bool,
    settings_override: Settings | None = None,
) -> tuple[Path, ConnectorGrantConsumptionMarkerV1 | None]:
    _, marker_relative_path = _validate_grant_reference_paths(ref)
    marker_path = _resolve_evidence_path(
        chain.evidence_root,
        marker_relative_path,
        label="connector grant consumption marker",
        must_exist=False,
    )
    if not marker_path.exists():
        if required:
            _fail(
                f"{grant.connector_key}_egress_consumption_marker_missing",
                "Historical connector grant evidence requires its indexed consumption marker.",
            )
        return marker_path, None
    path, raw_bytes, _ = _read_protected_bytes(
        marker_path,
        expected_sha256=ref.consumption_marker_sha256,
        label=f"{grant.connector_key} connector grant consumption marker",
        settings_override=settings_override,
    )
    marker = _parse_model(
        raw_bytes,
        ConnectorGrantConsumptionMarkerV1,
        label=f"{grant.connector_key} connector grant consumption marker",
    )
    if raw_bytes != canonical_json_bytes(marker):
        _fail(
            f"{grant.connector_key}_egress_consumption_marker_not_canonical",
            "Connector grant consumption marker bytes are not canonical JSON.",
        )
    _validate_marker_model(marker, ref=ref, grant=grant)
    return path, marker


def _validate_chain_archives(
    chain: VerifiedEvidenceIndexChain,
    *,
    settings_override: Settings | None = None,
) -> None:
    definition_refs = tuple(
        islice(
            iter(chain.head.campaigns),
            MAX_EVIDENCE_CAMPAIGN_ARCHIVES + 1,
        )
    )
    entries = tuple(
        islice(
            iter(chain.head.entries),
            MAX_EVIDENCE_GRANT_ARCHIVES + 1,
        )
    )
    capture_refs = tuple(
        islice(
            iter(chain.head.log_captures),
            MAX_EVIDENCE_LOG_CAPTURE_REFS + 1,
        )
    )
    if (
        len(definition_refs) > MAX_EVIDENCE_CAMPAIGN_ARCHIVES
        or len(entries) > MAX_EVIDENCE_GRANT_ARCHIVES
        or len(capture_refs) > MAX_EVIDENCE_LOG_CAPTURE_REFS
    ):
        _fail(
            "connector_egress_archive_limit_exceeded",
            "Protected evidence archive references exceed frozen ceilings.",
        )
    entries_by_campaign: dict[
        tuple[str, str], list[ConnectorGrantEvidenceRefV1]
    ] = {}
    for entry in entries:
        entries_by_campaign.setdefault(_campaign_key(entry), []).append(entry)
    for definition_ref in definition_refs:
        (
            _,
            _,
            definition,
            canonical_fingerprint,
        ) = _read_archived_definition(
            chain,
            definition_ref,
            settings_override=settings_override,
        )
        for entry in entries_by_campaign.get(_campaign_key(definition_ref), []):
            _, _, grant, _ = _read_archived_grant(
                chain,
                entry,
                definition=definition,
                raw_definition_sha256=definition_ref.raw_definition_sha256,
                canonical_campaign_fingerprint=canonical_fingerprint,
                settings_override=settings_override,
            )
            _read_marker_if_present(
                chain,
                entry,
                grant,
                required=False,
                settings_override=settings_override,
            )


def _validated_now(now: datetime) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None:
        _fail(
            "connector_egress_authorization_time_invalid",
            "Authorization time must be timezone-aware.",
        )
    return now.astimezone(UTC)


def _canonical_campaign_id(value: str) -> str:
    try:
        parsed = UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        _fail(
            "connector_egress_campaign_id_invalid",
            "Expected campaign ID must be a canonical UUID4.",
        )
    if parsed.version != 4 or str(parsed) != str(value).lower():
        _fail(
            "connector_egress_campaign_id_invalid",
            "Expected campaign ID must be a canonical UUID4.",
        )
    return str(parsed)


def _current_campaign_integrity(
    verified: VerifiedDualLiveCampaignDefinition,
) -> None:
    if not isinstance(verified, VerifiedDualLiveCampaignDefinition):
        _fail(
            "connector_egress_verified_campaign_type_invalid",
            "Current connector authority requires a verified campaign definition.",
        )
    canonical_bytes = canonical_json_bytes(verified.model)
    chain = verified.index_chain
    if not isinstance(chain, VerifiedEvidenceIndexChain):
        _fail(
            "connector_egress_verified_index_type_invalid",
            "Verified campaign requires an immutable evidence-index binding.",
        )
    chain_consistent = bool(chain.revisions)
    if chain_consistent:
        chain_consistent = (
            chain.head == chain.revisions[-1].model
            and chain.head_raw_sha256 == chain.revisions[-1].raw_sha256
            and chain.head_path == chain.revisions[-1].path
            and all(
                revision.raw_bytes == canonical_json_bytes(revision.model)
                and _sha256(revision.raw_bytes) == revision.raw_sha256
                for revision in chain.revisions
            )
        )
    if (
        canonical_bytes != verified.canonical_bytes
        or _sha256(canonical_bytes) != verified.canonical_fingerprint
        or _sha256(verified.raw_bytes) != verified.raw_sha256
        or not chain_consistent
        or verified.introduction_index_sha256
        != chain.head_raw_sha256
        or verified.introduction_index_revision
        != chain.head.revision
        or verified.evidence_root != chain.evidence_root
        or not _is_relative_to(
            verified.definition_archive_path,
            verified.evidence_root,
        )
    ):
        _fail(
            "connector_egress_verified_campaign_changed",
            "Verified campaign binding is internally inconsistent.",
        )
    _assert_evidence_index_chain_unchanged(chain)


def _current_grant_integrity(verified: VerifiedConnectorGrant) -> None:
    if not isinstance(verified, VerifiedConnectorGrant):
        _fail(
            "connector_egress_verified_grant_type_invalid",
            "Connector owner authorization requires a verified current grant.",
        )
    canonical_bytes = canonical_json_bytes(verified.model)
    if (
        canonical_bytes != verified.canonical_bytes
        or _sha256(canonical_bytes) != verified.canonical_fingerprint
        or _sha256(verified.raw_bytes) != verified.raw_sha256
    ):
        _fail(
            f"{verified.model.connector_key}_egress_verified_grant_changed",
            "Verified connector grant binding is internally inconsistent.",
        )
    _current_campaign_integrity(verified.verified_campaign)


def _normalized_code_revision(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if (
        len(normalized) != 40
        or any(char not in _HEX for char in normalized)
    ):
        _fail(
            "connector_egress_code_revision_invalid",
            "Code revision must be a lowercase 40-hex Git revision.",
        )
    return normalized


def resolve_current_dual_live_campaign_definition(
    *,
    expected_campaign_id: str,
    expected_campaign_fingerprint: str,
    code_revision: str,
    now: datetime,
) -> VerifiedDualLiveCampaignDefinition:
    campaign_id = _canonical_campaign_id(expected_campaign_id)
    expected_fingerprint = _normalized_sha256(
        expected_campaign_fingerprint,
        label="expected campaign fingerprint",
    )
    expected_revision = _normalized_code_revision(code_revision)
    authorization_time = _validated_now(now)
    definition_path, raw_bytes, raw_sha256 = _read_protected_bytes(
        settings.connector_campaign_definition_path,
        expected_sha256=settings.connector_campaign_definition_sha256,
        label="current dual-live campaign definition",
    )
    model = _parse_model(
        raw_bytes,
        DualLiveCampaignDefinitionV1,
        label="current dual-live campaign definition",
    )
    canonical_bytes = canonical_json_bytes(model)
    canonical_fingerprint = _sha256(canonical_bytes)
    if (
        str(model.campaign_id) != campaign_id
        or canonical_fingerprint != expected_fingerprint
        or model.code_revision != expected_revision
    ):
        _fail(
            "connector_egress_campaign_definition_mismatch",
            "Current campaign definition does not match expected ID, fingerprint, or code revision.",
        )
    if not (model.not_before <= authorization_time < model.expires_at):
        _fail(
            "connector_egress_campaign_window_closed",
            "Current campaign definition is outside its half-open authority window.",
        )

    chain = _load_evidence_index_chain()
    _validate_chain_archives(chain)
    definition_ref, _, _ = _find_campaign_refs(
        chain,
        campaign_id=campaign_id,
        campaign_fingerprint=canonical_fingerprint,
    )
    if (
        definition_ref.raw_definition_sha256 != raw_sha256
        or definition_ref.code_revision != expected_revision
    ):
        _fail(
            "connector_egress_campaign_index_mismatch",
            "Current campaign definition does not match its evidence-index reference.",
        )
    (
        definition_archive_path,
        archived_bytes,
        archived_model,
        archived_fingerprint,
    ) = _read_archived_definition(chain, definition_ref)
    if (
        archived_bytes != raw_bytes
        or archived_model != model
        or archived_fingerprint != canonical_fingerprint
    ):
        _fail(
            "connector_egress_campaign_archive_mismatch",
            "Current and archived campaign definition bytes do not match exactly.",
        )
    introduction = _introduction_revision(
        chain,
        campaign_id=campaign_id,
        campaign_fingerprint=canonical_fingerprint,
    )
    if (
        introduction.model.revision != chain.head.revision
        or introduction.raw_sha256 != chain.head_raw_sha256
    ):
        _fail(
            "connector_egress_campaign_historical_only",
            "Selected campaign was introduced before the configured unique-maximal head and is historical-only.",
        )
    if definition_path == definition_archive_path and raw_bytes != archived_bytes:
        _fail(
            "connector_egress_campaign_file_changed",
            "Campaign definition changed across current/archive verification.",
        )
    _assert_evidence_index_chain_unchanged(chain)
    return VerifiedDualLiveCampaignDefinition(
        model=model,
        raw_bytes=raw_bytes,
        raw_sha256=raw_sha256,
        canonical_bytes=canonical_bytes,
        canonical_fingerprint=canonical_fingerprint,
        introduction_index_revision=introduction.model.revision,
        introduction_index_sha256=introduction.raw_sha256,
        evidence_root=chain.evidence_root,
        definition_archive_path=definition_archive_path,
        index_chain=chain,
    )


def _grant_configuration(
    connector_key: str,
) -> tuple[Path | None, str | None]:
    if connector_key == "sciencebase_mcs":
        return (
            settings.connector_sciencebase_grant_path,
            settings.connector_sciencebase_grant_sha256,
        )
    if connector_key == "nrc_adams_aps":
        return (
            settings.connector_nrc_aps_grant_path,
            settings.connector_nrc_aps_grant_sha256,
        )
    _fail(
        "connector_egress_connector_not_admitted",
        "Connector key is not admitted for dual-live egress.",
        http_status=400,
    )


def resolve_current_connector_egress_grant(
    *,
    verified_campaign: VerifiedDualLiveCampaignDefinition,
    connector_key: str,
    expected_grant_sha256: str,
    campaign_id: str,
    campaign_fingerprint: str,
    code_revision: str,
    now: datetime,
) -> VerifiedConnectorGrant:
    if connector_key not in _EXPECTED_CONNECTORS:
        _fail(
            "connector_egress_connector_not_admitted",
            "Connector key is not admitted for dual-live egress.",
            http_status=400,
        )
    _current_campaign_integrity(verified_campaign)
    expected_grant = _normalized_sha256(
        expected_grant_sha256,
        label=f"expected {connector_key} grant digest",
    )
    expected_campaign_id = _canonical_campaign_id(campaign_id)
    expected_campaign_fingerprint = _normalized_sha256(
        campaign_fingerprint,
        label="expected campaign fingerprint",
    )
    expected_revision = _normalized_code_revision(code_revision)
    authorization_time = _validated_now(now)

    reloaded_campaign = resolve_current_dual_live_campaign_definition(
        expected_campaign_id=expected_campaign_id,
        expected_campaign_fingerprint=expected_campaign_fingerprint,
        code_revision=expected_revision,
        now=authorization_time,
    )
    if (
        reloaded_campaign.raw_bytes != verified_campaign.raw_bytes
        or reloaded_campaign.raw_sha256 != verified_campaign.raw_sha256
        or reloaded_campaign.canonical_fingerprint
        != verified_campaign.canonical_fingerprint
        or reloaded_campaign.introduction_index_revision
        != verified_campaign.introduction_index_revision
        or reloaded_campaign.introduction_index_sha256
        != verified_campaign.introduction_index_sha256
        or reloaded_campaign.evidence_root
        != verified_campaign.evidence_root
        or reloaded_campaign.definition_archive_path
        != verified_campaign.definition_archive_path
        or reloaded_campaign.index_chain.head_path
        != verified_campaign.index_chain.head_path
    ):
        _fail(
            f"{connector_key}_egress_campaign_revalidation_mismatch",
            "Verified campaign changed before connector grant resolution.",
        )
    grant_path_setting, grant_digest_setting = _grant_configuration(connector_key)
    configured_grant = _normalized_sha256(
        grant_digest_setting,
        label=f"configured {connector_key} grant digest",
    )
    if configured_grant != expected_grant:
        _fail(
            f"{connector_key}_egress_grant_digest_mismatch",
            "Caller expected grant digest does not equal protected configuration.",
        )
    _, entries, _ = _find_campaign_refs(
        reloaded_campaign.index_chain,
        campaign_id=expected_campaign_id,
        campaign_fingerprint=expected_campaign_fingerprint,
    )
    matching_entries = [
        entry
        for entry in entries
        if entry.connector_key == connector_key
        and entry.raw_grant_sha256 == expected_grant
    ]
    if len(matching_entries) != 1:
        _fail(
            f"{connector_key}_egress_grant_index_mismatch",
            "Exact connector grant evidence reference was not found.",
        )
    entry = matching_entries[0]

    current_path, raw_bytes, raw_sha256 = _read_protected_bytes(
        grant_path_setting,
        expected_sha256=configured_grant,
        label=f"current {connector_key} connector grant",
    )
    model = _parse_model(
        raw_bytes,
        ConnectorEgressGrantV1,
        label=f"current {connector_key} connector grant",
    )
    canonical_bytes = canonical_json_bytes(model)
    canonical_fingerprint = _sha256(canonical_bytes)
    _validate_grant_intersection(
        reloaded_campaign.model,
        model,
        raw_definition_sha256=reloaded_campaign.raw_sha256,
        canonical_campaign_fingerprint=(
            reloaded_campaign.canonical_fingerprint
        ),
    )
    if (
        model.connector_key != connector_key
        or model.campaign_id != expected_campaign_id
        or model.campaign_fingerprint != expected_campaign_fingerprint
        or model.code_revision != expected_revision
        or raw_sha256 != entry.raw_grant_sha256
        or canonical_fingerprint != entry.canonical_grant_fingerprint
    ):
        _fail(
            f"{connector_key}_egress_grant_mismatch",
            "Current connector grant does not match request, campaign, or evidence index.",
        )
    if not (model.issued_at <= authorization_time < model.expires_at):
        _fail(
            f"{connector_key}_egress_grant_window_closed",
            "Current connector grant is outside its half-open authority window.",
        )
    (
        grant_archive_path,
        archived_bytes,
        archived_model,
        archived_fingerprint,
    ) = _read_archived_grant(
        reloaded_campaign.index_chain,
        entry,
        definition=reloaded_campaign.model,
        raw_definition_sha256=reloaded_campaign.raw_sha256,
        canonical_campaign_fingerprint=(
            reloaded_campaign.canonical_fingerprint
        ),
    )
    if (
        archived_bytes != raw_bytes
        or archived_model != model
        or archived_fingerprint != canonical_fingerprint
    ):
        _fail(
            f"{connector_key}_egress_grant_archive_mismatch",
            "Current and archived connector grant bytes do not match exactly.",
        )
    marker_path, marker = _read_marker_if_present(
        reloaded_campaign.index_chain,
        entry,
        model,
        required=False,
    )
    if current_path == grant_archive_path and archived_bytes != raw_bytes:
        _fail(
            f"{connector_key}_egress_grant_file_changed",
            "Connector grant changed across current/archive verification.",
        )
    _assert_evidence_index_chain_unchanged(reloaded_campaign.index_chain)
    return VerifiedConnectorGrant(
        model=model,
        raw_bytes=raw_bytes,
        raw_sha256=raw_sha256,
        canonical_bytes=canonical_bytes,
        canonical_fingerprint=canonical_fingerprint,
        verified_campaign=reloaded_campaign,
        grant_archive_path=grant_archive_path,
        consumption_marker_path=marker_path,
        consumption_marker_sha256=entry.consumption_marker_sha256,
        consumption_marker_present=marker is not None,
    )


def resolve_historical_connector_grant_evidence_read_only(
    settings: Settings,
    *,
    connector_key: str,
    campaign_id: str,
    expected_campaign_fingerprint: str,
    expected_grant_sha256: str,
) -> VerifiedHistoricalGrantEvidence:
    if not isinstance(settings, Settings):
        _fail(
            "connector_egress_settings_invalid",
            "Historical evidence resolution requires explicit Settings.",
        )
    if connector_key not in _EXPECTED_CONNECTORS:
        _fail(
            "connector_egress_connector_not_admitted",
            "Connector key is not admitted for historical evidence resolution.",
            http_status=400,
        )
    expected_campaign_id = _canonical_campaign_id(campaign_id)
    expected_fingerprint = _normalized_sha256(
        expected_campaign_fingerprint,
        label="expected historical campaign fingerprint",
    )
    expected_grant = _normalized_sha256(
        expected_grant_sha256,
        label=f"expected historical {connector_key} grant digest",
    )
    chain = _load_evidence_index_chain(settings)
    _validate_chain_archives(chain, settings_override=settings)
    definition_ref, entries, _ = _find_campaign_refs(
        chain,
        campaign_id=expected_campaign_id,
        campaign_fingerprint=expected_fingerprint,
    )
    matching_entries = [
        entry
        for entry in entries
        if entry.connector_key == connector_key
        and entry.raw_grant_sha256 == expected_grant
    ]
    if len(matching_entries) != 1:
        _fail(
            f"{connector_key}_egress_historical_grant_not_found",
            "Exact historical connector grant reference was not found.",
        )
    entry = matching_entries[0]
    (
        definition_archive_path,
        definition_bytes,
        definition,
        canonical_campaign_fingerprint,
    ) = _read_archived_definition(
        chain,
        definition_ref,
        settings_override=settings,
    )
    (
        grant_archive_path,
        grant_bytes,
        grant,
        canonical_grant_fingerprint,
    ) = _read_archived_grant(
        chain,
        entry,
        definition=definition,
        raw_definition_sha256=definition_ref.raw_definition_sha256,
        canonical_campaign_fingerprint=canonical_campaign_fingerprint,
        settings_override=settings,
    )
    marker_path, marker = _read_marker_if_present(
        chain,
        entry,
        grant,
        required=True,
        settings_override=settings,
    )
    if marker is None:
        _fail(
            f"{connector_key}_egress_historical_marker_missing",
            "Historical connector grant marker is missing.",
        )
    introduction = _introduction_revision(
        chain,
        campaign_id=expected_campaign_id,
        campaign_fingerprint=expected_fingerprint,
    )
    final_definition = _read_archived_definition(
        chain,
        definition_ref,
        settings_override=settings,
    )
    final_grant = _read_archived_grant(
        chain,
        entry,
        definition=final_definition[2],
        raw_definition_sha256=definition_ref.raw_definition_sha256,
        canonical_campaign_fingerprint=final_definition[3],
        settings_override=settings,
    )
    final_marker_path, final_marker = _read_marker_if_present(
        chain,
        entry,
        final_grant[2],
        required=True,
        settings_override=settings,
    )
    if (
        final_definition
        != (
            definition_archive_path,
            definition_bytes,
            definition,
            canonical_campaign_fingerprint,
        )
        or final_grant
        != (
            grant_archive_path,
            grant_bytes,
            grant,
            canonical_grant_fingerprint,
        )
        or final_marker_path != marker_path
        or final_marker != marker
    ):
        _fail(
            "connector_egress_historical_snapshot_changed",
            "Historical definition, grant, or marker changed during verification.",
        )
    _assert_evidence_index_chain_unchanged(
        chain,
        settings_override=settings,
    )
    return VerifiedHistoricalGrantEvidence(
        definition_model=definition,
        model=grant,
        raw_definition_sha256=definition_ref.raw_definition_sha256,
        canonical_campaign_fingerprint=canonical_campaign_fingerprint,
        raw_sha256=entry.raw_grant_sha256,
        canonical_fingerprint=canonical_grant_fingerprint,
        introduction_index_revision=introduction.model.revision,
        introduction_index_sha256=introduction.raw_sha256,
        definition_archive_path=definition_archive_path,
        grant_archive_path=grant_archive_path,
        marker_model=marker,
        consumption_marker_path=marker_path,
        consumption_marker_sha256=entry.consumption_marker_sha256,
        index_chain=chain,
    )


def resolve_historical_connector_grant_evidence(
    *,
    connector_key: str,
    campaign_id: str,
    expected_campaign_fingerprint: str,
    expected_grant_sha256: str,
) -> VerifiedHistoricalGrantEvidence:
    return resolve_historical_connector_grant_evidence_read_only(
        settings,
        connector_key=connector_key,
        campaign_id=campaign_id,
        expected_campaign_fingerprint=expected_campaign_fingerprint,
        expected_grant_sha256=expected_grant_sha256,
    )


def _request_headers(request: Request) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in request.headers.items()}


def _has_forwarded_identity(request: Request) -> bool:
    headers = _request_headers(request)
    configured = {
        str(settings.proxy_identity_header or "").strip().lower(),
        str(settings.proxy_email_header or "").strip().lower(),
        str(settings.proxy_groups_header or "").strip().lower(),
        str(settings.proxy_roles_header or "").strip().lower(),
    }
    forbidden = _FORWARDED_IDENTITY_HEADERS | {
        name for name in configured if name
    }
    return any(name in headers for name in forbidden)


def _direct_loopback_peer(request: Request) -> bool:
    client = request.client
    if client is None:
        return False
    try:
        return ipaddress.ip_address(str(client.host)).is_loopback
    except ValueError:
        return False


def _build_connector_egress_authorization_receipt(
    *,
    verified_grant: VerifiedConnectorGrant,
    operator_ref_hash: str,
    workspace_ref_hash: str,
    auth_owner_mode: str,
    authorization_mode: Literal["identity_presence", "role_enforcing"],
    role: Literal["owner"] | None,
) -> ConnectorEgressAuthorizationReceipt:
    connector_key = verified_grant.model.connector_key
    if (
        len(operator_ref_hash) != 64
        or len(workspace_ref_hash) != 64
        or not auth_owner_mode
    ):
        _fail(
            f"{connector_key}_egress_principal_hash_invalid",
            "Connector caller posture did not return protected principal/workspace hashes.",
        )
    campaign = verified_grant.verified_campaign
    return ConnectorEgressAuthorizationReceipt(
        connector_key=connector_key,
        campaign_id=str(campaign.model.campaign_id),
        campaign_fingerprint=campaign.canonical_fingerprint,
        campaign_definition_sha256=campaign.raw_sha256,
        grant_sha256=verified_grant.raw_sha256,
        canonical_grant_fingerprint=verified_grant.canonical_fingerprint,
        introduction_index_revision=campaign.introduction_index_revision,
        introduction_index_sha256=campaign.introduction_index_sha256,
        operator_ref_hash=operator_ref_hash,
        workspace_ref_hash=workspace_ref_hash,
        auth_owner_mode=auth_owner_mode,
        authorization_mode=authorization_mode,
        role=role,
        access="write",
    )


def _local_runner_principal_hashes(
    *,
    connector_key: str,
) -> tuple[str, str]:
    try:
        from app.services.dual_live_windows import current_user_sid_sha256

        sid_sha256 = current_user_sid_sha256()
        repo_root = BACKEND_ROOT.parent.resolve(strict=True)
    except Exception as exc:
        raise ConnectorEgressAuthorizationError(
            f"{connector_key}_egress_local_runner_identity_invalid",
            "Local-runner OS or workspace identity is unavailable.",
        ) from exc
    if (
        not isinstance(sid_sha256, str)
        or len(sid_sha256) != 64
        or any(char not in _HEX for char in sid_sha256)
    ):
        _fail(
            f"{connector_key}_egress_local_runner_identity_invalid",
            "Local-runner OS identity is not a lowercase SHA-256 digest.",
        )
    canonical_root = os.path.normcase(str(repo_root))
    operator_ref_hash = _sha256(
        canonical_json_bytes(
            {
                "auth_owner": "none",
                "current_user_sid_sha256": sid_sha256,
                "identity_schema_id": (
                    "project6.connector_egress_local_runner_identity.v1"
                ),
            }
        )
    )
    workspace_ref_hash = _sha256(
        canonical_json_bytes(
            {
                "auth_owner": "none",
                "canonical_repo_root": canonical_root,
                "identity_schema_id": (
                    "project6.connector_egress_local_runner_identity.v1"
                ),
            }
        )
    )
    return operator_ref_hash, workspace_ref_hash


def authorize_connector_egress_owner(
    request: Request,
    *,
    verified_grant: VerifiedConnectorGrant,
    access: Literal["write"],
) -> ConnectorEgressAuthorizationReceipt:
    if not isinstance(request, Request):
        _fail(
            "connector_egress_request_context_invalid",
            "Connector owner authorization requires a server request context.",
            http_status=400,
        )
    try:
        posture = route_level_operator_authorization_required(
            request.headers,
            access=access,
        )
    except SecXbrlInAppAuthPolicyError as exc:
        raise ConnectorEgressAuthorizationError(
            "connector_egress_caller_posture_denied",
            "Connector egress caller posture was denied.",
            http_status=exc.http_status,
        ) from exc
    if access != "write" or posture.get("access") != "write":
        _fail(
            "connector_egress_access_class_not_admitted",
            "Connector egress owner authorization admits write access only.",
            http_status=400,
        )
    _current_grant_integrity(verified_grant)
    connector_key = verified_grant.model.connector_key
    if not settings.connector_live_egress_enabled:
        _fail(
            f"{connector_key}_egress_default_off",
            "Connector live egress is disabled.",
        )
    if not settings.connector_live_egress_exclusive_proof_mode:
        _fail(
            f"{connector_key}_egress_exclusive_mode_required",
            "Connector live egress requires exclusive proof mode.",
        )

    role = posture.get("role")
    raw_authorization_mode = str(posture.get("authorization_mode") or "")
    if raw_authorization_mode not in {"identity_presence", "role_enforcing"}:
        _fail(
            f"{connector_key}_egress_authorization_mode_invalid",
            "Connector caller posture returned an unadmitted authorization mode.",
        )
    authorization_mode: Literal["identity_presence", "role_enforcing"] = (
        "identity_presence"
        if raw_authorization_mode == "identity_presence"
        else "role_enforcing"
    )
    if settings.auth_owner == "none":
        if (
            settings.deployment_mode != "local"
            or settings.trusted_proxy_mode
            or not _direct_loopback_peer(request)
            or _has_forwarded_identity(request)
            or verified_grant.model.operator_mode != "local_loopback"
        ):
            _fail(
                f"{connector_key}_egress_local_posture_denied",
                "Local connector egress requires direct loopback, non-proxy, exclusive single-operator posture.",
            )
        if role not in {None, "owner"}:
            _fail(
                f"{connector_key}_egress_owner_role_required",
                "Local connector egress caller posture did not derive owner authority.",
            )
    elif settings.auth_owner == "proxy":
        if (
            not settings.trusted_proxy_mode
            or settings.layer3_route_authorization_mode != "role_enforcing"
            or authorization_mode != "role_enforcing"
            or role != "owner"
            or verified_grant.model.operator_mode != "proxy_owner"
        ):
            _fail(
                f"{connector_key}_egress_proxy_owner_required",
                "Proxy connector egress requires trusted role enforcement and derived owner role.",
            )
    else:
        _fail(
            f"{connector_key}_egress_auth_owner_not_admitted",
            "Connector egress admits only local-none or trusted-proxy owner posture.",
        )

    operator_ref_hash = str(posture.get("operator_ref_hash") or "")
    workspace_ref_hash = str(posture.get("workspace_ref_hash") or "")
    auth_owner_mode = str(posture.get("auth_owner_mode") or "")
    return _build_connector_egress_authorization_receipt(
        verified_grant=verified_grant,
        operator_ref_hash=operator_ref_hash,
        workspace_ref_hash=workspace_ref_hash,
        auth_owner_mode=auth_owner_mode,
        authorization_mode=authorization_mode,
        role=role,
    )


def authorize_connector_egress_local_runner(
    *,
    verified_grant: VerifiedConnectorGrant,
    access: Literal["write"],
) -> ConnectorEgressAuthorizationReceipt:
    if access != "write":
        _fail(
            "connector_egress_access_class_not_admitted",
            "Connector egress owner authorization admits write access only.",
            http_status=400,
        )
    _current_grant_integrity(verified_grant)
    connector_key = verified_grant.model.connector_key
    if not settings.connector_live_egress_enabled:
        _fail(
            f"{connector_key}_egress_default_off",
            "Connector live egress is disabled.",
        )
    if not settings.connector_live_egress_exclusive_proof_mode:
        _fail(
            f"{connector_key}_egress_exclusive_mode_required",
            "Connector live egress requires exclusive proof mode.",
        )
    if (
        settings.deployment_mode != "local"
        or settings.auth_owner != "none"
        or settings.trusted_proxy_mode
        or verified_grant.model.operator_mode != "local_loopback"
    ):
        _fail(
            f"{connector_key}_egress_local_runner_posture_denied",
            "Local-runner connector egress requires local AUTH_OWNER=none, non-proxy, local-loopback authority.",
        )
    operator_ref_hash, workspace_ref_hash = _local_runner_principal_hashes(
        connector_key=connector_key,
    )
    return _build_connector_egress_authorization_receipt(
        verified_grant=verified_grant,
        operator_ref_hash=operator_ref_hash,
        workspace_ref_hash=workspace_ref_hash,
        auth_owner_mode="AUTH_OWNER_none_single_operator_dev_profile",
        authorization_mode="identity_presence",
        role=None,
    )
