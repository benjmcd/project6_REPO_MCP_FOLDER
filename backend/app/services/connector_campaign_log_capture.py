from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
import hashlib
from itertools import islice
import os
from pathlib import Path, PurePosixPath
import re
import stat
import threading
from types import MappingProxyType
from typing import Any, Literal, NoReturn
from uuid import NAMESPACE_URL, UUID, uuid5
import weakref

from sqlalchemy import and_, or_, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.models import ConnectorRun, ConnectorRunEvent
from app.schemas.api import (
    ConnectorCampaignLogFileV1,
    ConnectorCampaignLogManifestV1,
    ConnectorCampaignLogSealV1,
    ConnectorEgressGrantV1,
    DualLiveCampaignDefinitionV1,
)
from app.services.connector_egress_arming import (
    ConnectorEgressArmingError,
    _assert_envelope_fingerprint,
    canonical_arming_payload,
    compute_parent_arming_id,
    is_strict_egress_run,
)
from app.services.connector_egress_authorization import (
    MAX_EVIDENCE_GRANT_ARCHIVES,
    MAX_EVIDENCE_INDEX_REVISIONS,
    ConnectorEgressAuthorizationError,
    ConnectorEgressAuthorizationReceipt,
    VerifiedEvidenceIndexChain,
    _assert_no_reparse_components,
    _canonical_campaign_id,
    _find_campaign_refs,
    _forbidden_path,
    _introduction_revision,
    _load_evidence_index_chain,
    _normalized_sha256,
    _resolve_evidence_path,
    _validate_grant_intersection,
    _validate_index_slice_structure,
    _validate_log_capture_paths,
    _validate_successor,
    canonical_json_bytes,
    resolve_current_connector_egress_grant,
    resolve_current_dual_live_campaign_definition,
    resolve_historical_connector_grant_evidence,
    strict_json_loads,
)
from app.services.raw_storage_handles import (
    LockedRawFileSnapshot,
    OwnedLockedRawFileWriter,
    StableRawFileIdentity,
    StableRawStorageError,
    locked_raw_file_snapshot,
    open_new_locked_raw_file_writer,
    publish_atomic_strict_new_locked_raw_file,
)


MAX_STREAM_BYTES = 16 * 1024 * 1024
MAX_AGGREGATE_BYTES = 32 * 1024 * 1024
MAX_PROTECTED_JSON_BYTES = 64 * 1024
# Grants/markers are separate directories and form the largest protected set.
MAX_PROTECTED_DIRECTORY_CHILDREN = MAX_EVIDENCE_GRANT_ARCHIVES
_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})
_STREAMS: tuple[tuple[str, Literal["app", "http", "stdout", "stderr"]], ...] = (
    ("app.jsonl", "app"),
    ("http.jsonl", "http"),
    ("stdout.log", "stdout"),
    ("stderr.log", "stderr"),
)
_CONNECTORS = ("nrc_adams_aps", "sciencebase_mcs")
_EVENT_CAPS = {"nrc_adams_aps": 8, "sciencebase_mcs": 12}
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


class ConnectorCampaignLogCaptureError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ConnectorCampaignLogCaptureCommitAmbiguous(
    ConnectorCampaignLogCaptureError
):
    pass


def _fail(code: str, message: str) -> NoReturn:
    raise ConnectorCampaignLogCaptureError(code, message)


def _as_utc(value: datetime | None, *, label: str) -> datetime:
    candidate = datetime.now(UTC) if value is None else value
    if candidate.tzinfo is None or candidate.utcoffset() is None:
        _fail(
            "connector_campaign_log_time_invalid",
            f"{label} must be timezone-aware.",
        )
    return candidate.astimezone(UTC)


def _db_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass(frozen=True, slots=True)
class _ExpectedRunBinding:
    connector_key: str
    connector_run_id: str
    source_system: str
    grant_sha256: str
    canonical_grant_fingerprint: str
    envelope_core_bytes: bytes


@dataclass(frozen=True, slots=True)
class _CaptureAuthority:
    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    code_revision: str
    runtime_started_at: datetime
    introduction_index_revision: int
    introduction_index_sha256: str
    evidence_root: Path
    log_dir_relative_path: str
    manifest_relative_path: str
    seal_relative_path: str
    run_bindings: tuple[_ExpectedRunBinding, ...]


class ConnectorCampaignLogWriter:
    __slots__ = (
        "_raw",
        "_stream_class",
        "_flushed_state",
        "_closed_clean",
    )

    def __init__(
        self,
        raw: OwnedLockedRawFileWriter,
        stream_class: Literal["app", "http", "stdout", "stderr"],
    ) -> None:
        self._raw = raw
        self._stream_class = stream_class
        self._flushed_state: tuple[int, int, int, int, int] | None = None
        self._closed_clean = False

    @property
    def stream_class(
        self,
    ) -> Literal["app", "http", "stdout", "stderr"]:
        return self._stream_class

    @property
    def closed(self) -> bool:
        return self._raw.closed

    def write(self, content: bytes | bytearray | memoryview) -> int:
        if self.closed:
            raise ValueError("write to closed campaign log writer")
        written = self._raw.write(content)
        self._flushed_state = None
        self._closed_clean = False
        return written

    def flush(self) -> None:
        if self.closed:
            raise ValueError("flush of closed campaign log writer")
        self._raw.flush()
        os.fsync(self._raw.fileno())
        file_stat = os.fstat(self._raw.fileno())
        self._flushed_state = (
            int(file_stat.st_dev),
            int(file_stat.st_ino),
            int(file_stat.st_size),
            int(file_stat.st_mtime_ns),
            int(file_stat.st_nlink),
        )

    def fileno(self) -> int:
        return self._raw.fileno()

    def close(self) -> None:
        if self.closed:
            return
        try:
            file_stat = os.fstat(self._raw.fileno())
            state = (
                int(file_stat.st_dev),
                int(file_stat.st_ino),
                int(file_stat.st_size),
                int(file_stat.st_mtime_ns),
                int(file_stat.st_nlink),
            )
            self._closed_clean = (
                self._flushed_state is not None
                and state == self._flushed_state
            )
        finally:
            self._raw.close()


@dataclass(frozen=True, slots=True, weakref_slot=True)
class ConnectorCampaignLogCaptureSession:
    campaign_id: str
    campaign_fingerprint: str
    campaign_definition_sha256: str
    code_revision: str
    runtime_started_at: datetime
    writers: tuple[
        ConnectorCampaignLogWriter,
        ConnectorCampaignLogWriter,
        ConnectorCampaignLogWriter,
        ConnectorCampaignLogWriter,
    ]
    _binding_token: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class _CaptureBinding:
    session_ref: weakref.ReferenceType[ConnectorCampaignLogCaptureSession]
    authority: _CaptureAuthority
    stream_identities: tuple[
        StableRawFileIdentity,
        StableRawFileIdentity,
        StableRawFileIdentity,
        StableRawFileIdentity,
    ]
    parent_identity: StableRawFileIdentity
    writers: tuple[
        ConnectorCampaignLogWriter,
        ConnectorCampaignLogWriter,
        ConnectorCampaignLogWriter,
        ConnectorCampaignLogWriter,
    ]
    raw_writers: tuple[
        OwnedLockedRawFileWriter,
        OwnedLockedRawFileWriter,
        OwnedLockedRawFileWriter,
        OwnedLockedRawFileWriter,
    ]


_CAPTURE_BINDINGS: dict[object, _CaptureBinding] = {}
_CAPTURE_BINDINGS_LOCK = threading.RLock()


def _register_capture_binding(
    capture: ConnectorCampaignLogCaptureSession,
    *,
    authority: _CaptureAuthority,
    stream_identities: tuple[
        StableRawFileIdentity,
        StableRawFileIdentity,
        StableRawFileIdentity,
        StableRawFileIdentity,
    ],
    parent_identity: StableRawFileIdentity,
    writers: tuple[
        ConnectorCampaignLogWriter,
        ConnectorCampaignLogWriter,
        ConnectorCampaignLogWriter,
        ConnectorCampaignLogWriter,
    ],
    raw_writers: tuple[
        OwnedLockedRawFileWriter,
        OwnedLockedRawFileWriter,
        OwnedLockedRawFileWriter,
        OwnedLockedRawFileWriter,
    ],
) -> None:
    token = capture._binding_token

    def retire_abandoned(
        session_ref: weakref.ReferenceType[
            ConnectorCampaignLogCaptureSession
        ],
    ) -> None:
        with _CAPTURE_BINDINGS_LOCK:
            current = _CAPTURE_BINDINGS.get(token)
            if current is not None and current.session_ref is session_ref:
                _CAPTURE_BINDINGS.pop(token, None)

    session_ref = weakref.ref(capture, retire_abandoned)
    binding = _CaptureBinding(
        session_ref=session_ref,
        authority=authority,
        stream_identities=stream_identities,
        parent_identity=parent_identity,
        writers=writers,
        raw_writers=raw_writers,
    )
    with _CAPTURE_BINDINGS_LOCK:
        if token in _CAPTURE_BINDINGS:
            _fail(
                "connector_campaign_log_session_binding_mismatch",
                "Capture binding token is not exclusive.",
            )
        _CAPTURE_BINDINGS[token] = binding


def _writer_binding_matches(
    capture: ConnectorCampaignLogCaptureSession,
    binding: _CaptureBinding,
) -> bool:
    try:
        return (
            len(capture.writers) == len(_STREAMS)
            and all(
                writer is bound
                for writer, bound in zip(
                    capture.writers,
                    binding.writers,
                    strict=True,
                )
            )
            and all(
                writer._raw is bound_raw
                for writer, bound_raw in zip(
                    capture.writers,
                    binding.raw_writers,
                    strict=True,
                )
            )
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _require_capture_binding(
    capture: ConnectorCampaignLogCaptureSession,
) -> _CaptureBinding:
    try:
        with _CAPTURE_BINDINGS_LOCK:
            binding = _CAPTURE_BINDINGS.get(capture._binding_token)
    except TypeError:
        binding = None
    if binding is None:
        _fail(
            "connector_campaign_log_session_binding_mismatch",
            "Capture has no live server-owned binding.",
        )
    if not _writer_binding_matches(capture, binding):
        _fail(
            "connector_campaign_log_writer_binding_invalid",
            "Campaign log writers differ from the server-bound writers.",
        )
    if binding.session_ref() is not capture:
        _fail(
            "connector_campaign_log_session_binding_mismatch",
            "Capture is not the exact server-owned session.",
        )
    return binding


def _retire_capture_binding(
    capture: ConnectorCampaignLogCaptureSession,
    binding: _CaptureBinding,
) -> None:
    try:
        with _CAPTURE_BINDINGS_LOCK:
            current = _CAPTURE_BINDINGS.get(capture._binding_token)
            if current is binding:
                _CAPTURE_BINDINGS.pop(capture._binding_token, None)
    except TypeError:
        pass


@dataclass(frozen=True, slots=True)
class ConnectorCampaignLogCaptureResult:
    manifest: ConnectorCampaignLogManifestV1
    manifest_sha256: str
    file_set_hash: str
    seal: ConnectorCampaignLogSealV1
    seal_sha256: str
    event_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VerifiedCampaignLogCapture:
    """Transitively immutable verified evidence; no mutable model escapes."""

    manifest_bytes: bytes
    manifest_sha256: str
    file_set_hash: str
    seal_bytes: bytes
    seal_sha256: str
    stream_bytes: Mapping[str, bytes]
    seal_event_ids: tuple[str, ...]
    stable_snapshot: tuple[tuple[str, int, str], ...]


def _expected_envelope_core(
    *,
    campaign: Any,
    grant: Any,
    raw_grant_sha256: str,
    canonical_grant_fingerprint: str,
    introduction_index_revision: int,
    introduction_index_sha256: str,
) -> bytes:
    model = grant
    if hasattr(campaign, "definition_model"):
        definition_model = campaign.definition_model
        campaign_definition_sha256 = campaign.raw_definition_sha256
        campaign_fingerprint = campaign.canonical_campaign_fingerprint
    else:
        definition_model = campaign.model
        campaign_definition_sha256 = campaign.raw_sha256
        campaign_fingerprint = campaign.canonical_fingerprint
    payload = {
        "schema_id": "project6.connector_egress_arming.v1",
        "connector_key": model.connector_key,
        "campaign_id": str(model.campaign_id),
        "campaign_definition_sha256": campaign_definition_sha256,
        "campaign_fingerprint": campaign_fingerprint,
        "grant_sha256": raw_grant_sha256,
        "canonical_grant_fingerprint": canonical_grant_fingerprint,
        "campaign_introduction_index_revision": (
            introduction_index_revision
        ),
        "campaign_introduction_index_sha256": (
            introduction_index_sha256
        ),
        "code_revision": model.code_revision,
        "grant_id": model.grant_id,
        "arming_nonce": model.arming_nonce,
        "max_armings": model.max_armings,
        "supersedes_grant_sha256": model.supersedes_grant_sha256,
        "operator_mode": model.operator_mode,
        "non_authorities": model.non_authorities,
        "target": model.target,
        "request_rules": model.request_rules,
        "max_physical_requests": model.max_physical_requests,
        "max_run_bytes": model.max_run_bytes,
        "max_single_send_detection_allowance_bytes": (
            model.max_single_send_detection_allowance_bytes
        ),
        "request_timeout_seconds": model.request_timeout_seconds,
        "min_request_interval_ms": model.min_request_interval_ms,
        "grant_issued_at": model.issued_at,
        "grant_expires_at": model.expires_at,
        "campaign_not_before": definition_model.not_before,
        "campaign_expires_at": definition_model.expires_at,
    }
    return canonical_json_bytes(canonical_arming_payload(payload))


def _current_authority(
    *,
    campaign_id: UUID,
    expected_campaign_fingerprint: str,
    expected_code_revision: str,
    started_at: datetime,
) -> _CaptureAuthority:
    verified = resolve_current_dual_live_campaign_definition(
        expected_campaign_id=str(campaign_id),
        expected_campaign_fingerprint=expected_campaign_fingerprint,
        code_revision=expected_code_revision,
        now=started_at,
    )
    _, entries, capture_ref = _find_campaign_refs(
        verified.index_chain,
        campaign_id=str(campaign_id),
        campaign_fingerprint=verified.canonical_fingerprint,
    )
    log_dir, manifest_path, seal_path = _validate_log_capture_paths(
        capture_ref
    )
    if (
        capture_ref.campaign_definition_sha256 != verified.raw_sha256
        or capture_ref.code_revision != verified.model.code_revision
    ):
        _fail(
            "connector_campaign_log_authority_mismatch",
            "Campaign log reference does not match current campaign authority.",
        )
    bindings: list[_ExpectedRunBinding] = []
    for entry in sorted(entries, key=lambda item: item.connector_key):
        current_grant = resolve_current_connector_egress_grant(
            verified_campaign=verified,
            connector_key=entry.connector_key,
            expected_grant_sha256=entry.raw_grant_sha256,
            campaign_id=str(campaign_id),
            campaign_fingerprint=verified.canonical_fingerprint,
            code_revision=verified.model.code_revision,
            now=started_at,
        )
        grant = current_grant.model
        run_id = compute_parent_arming_id(
            connector_key=grant.connector_key,
            campaign_id=str(grant.campaign_id),
            grant_sha256=current_grant.raw_sha256,
            arming_nonce=grant.arming_nonce,
        )
        bindings.append(
            _ExpectedRunBinding(
                connector_key=grant.connector_key,
                connector_run_id=run_id,
                source_system=(
                    "nrc_adams"
                    if grant.connector_key == "nrc_adams_aps"
                    else "sciencebase"
                ),
                grant_sha256=current_grant.raw_sha256,
                canonical_grant_fingerprint=(
                    current_grant.canonical_fingerprint
                ),
                envelope_core_bytes=_expected_envelope_core(
                    campaign=verified,
                    grant=grant,
                    raw_grant_sha256=current_grant.raw_sha256,
                    canonical_grant_fingerprint=(
                        current_grant.canonical_fingerprint
                    ),
                    introduction_index_revision=(
                        verified.introduction_index_revision
                    ),
                    introduction_index_sha256=(
                        verified.introduction_index_sha256
                    ),
                ),
            )
        )
    return _CaptureAuthority(
        campaign_id=str(campaign_id),
        campaign_fingerprint=verified.canonical_fingerprint,
        campaign_definition_sha256=verified.raw_sha256,
        code_revision=verified.model.code_revision,
        runtime_started_at=started_at,
        introduction_index_revision=verified.introduction_index_revision,
        introduction_index_sha256=verified.introduction_index_sha256,
        evidence_root=Path(verified.evidence_root),
        log_dir_relative_path=log_dir,
        manifest_relative_path=manifest_path,
        seal_relative_path=seal_path,
        run_bindings=tuple(bindings),
    )


def _historical_authority(
    capture: ConnectorCampaignLogCaptureSession,
    *,
    bound: _CaptureAuthority,
) -> _CaptureAuthority:
    chain = _load_evidence_index_chain()
    _, entries, capture_ref = _find_campaign_refs(
        chain,
        campaign_id=bound.campaign_id,
        campaign_fingerprint=bound.campaign_fingerprint,
    )
    log_dir, manifest_path, seal_path = _validate_log_capture_paths(
        capture_ref
    )
    if (
        capture_ref.campaign_definition_sha256
        != bound.campaign_definition_sha256
        or capture_ref.code_revision != bound.code_revision
        or log_dir != bound.log_dir_relative_path
        or manifest_path != bound.manifest_relative_path
        or seal_path != bound.seal_relative_path
        or Path(chain.evidence_root) != bound.evidence_root
    ):
        _fail(
            "connector_campaign_log_authority_changed",
            "Historical campaign log authority differs from capture start.",
        )
    bindings: list[_ExpectedRunBinding] = []
    for entry in sorted(entries, key=lambda item: item.connector_key):
        history = resolve_historical_connector_grant_evidence(
            connector_key=entry.connector_key,
            campaign_id=bound.campaign_id,
            expected_campaign_fingerprint=bound.campaign_fingerprint,
            expected_grant_sha256=entry.raw_grant_sha256,
        )
        grant = history.model
        if (
            history.raw_definition_sha256
            != bound.campaign_definition_sha256
            or history.canonical_campaign_fingerprint
            != bound.campaign_fingerprint
            or grant.code_revision != bound.code_revision
            or history.introduction_index_revision
            != bound.introduction_index_revision
            or history.introduction_index_sha256
            != bound.introduction_index_sha256
            or Path(history.index_chain.evidence_root)
            != bound.evidence_root
        ):
            _fail(
                "connector_campaign_log_historical_authority_mismatch",
                "Historical connector grant differs from capture authority.",
            )
        if not (
            _db_utc(history.definition_model.not_before)
            <= capture.runtime_started_at
            < _db_utc(history.definition_model.expires_at)
            and _db_utc(grant.issued_at)
            <= capture.runtime_started_at
            < _db_utc(grant.expires_at)
        ):
            _fail(
                "connector_campaign_log_start_outside_authority",
                "Capture start is outside the historical authority window.",
            )
        run_id = compute_parent_arming_id(
            connector_key=grant.connector_key,
            campaign_id=str(grant.campaign_id),
            grant_sha256=history.raw_sha256,
            arming_nonce=grant.arming_nonce,
        )
        if history.marker_model.connector_run_id != run_id:
            _fail(
                "connector_campaign_log_marker_run_mismatch",
                "Grant marker does not bind the deterministic connector run.",
            )
        bindings.append(
            _ExpectedRunBinding(
                connector_key=grant.connector_key,
                connector_run_id=run_id,
                source_system=(
                    "nrc_adams"
                    if grant.connector_key == "nrc_adams_aps"
                    else "sciencebase"
                ),
                grant_sha256=history.raw_sha256,
                canonical_grant_fingerprint=history.canonical_fingerprint,
                envelope_core_bytes=_expected_envelope_core(
                    campaign=history,
                    grant=grant,
                    raw_grant_sha256=history.raw_sha256,
                    canonical_grant_fingerprint=(
                        history.canonical_fingerprint
                    ),
                    introduction_index_revision=(
                        history.introduction_index_revision
                    ),
                    introduction_index_sha256=(
                        history.introduction_index_sha256
                    ),
                ),
            )
        )
    refreshed = _CaptureAuthority(
        campaign_id=bound.campaign_id,
        campaign_fingerprint=bound.campaign_fingerprint,
        campaign_definition_sha256=bound.campaign_definition_sha256,
        code_revision=bound.code_revision,
        runtime_started_at=bound.runtime_started_at,
        introduction_index_revision=bound.introduction_index_revision,
        introduction_index_sha256=bound.introduction_index_sha256,
        evidence_root=bound.evidence_root,
        log_dir_relative_path=log_dir,
        manifest_relative_path=manifest_path,
        seal_relative_path=seal_path,
        run_bindings=tuple(bindings),
    )
    if refreshed != bound:
        _fail(
            "connector_campaign_log_authority_changed",
            "Historical connector identity differs from capture start.",
        )
    return refreshed


def _exact_child(
    parent: Path,
    name: str,
    *,
    must_exist: bool,
    directory: bool,
) -> Path:
    children = tuple(
        islice(parent.iterdir(), MAX_PROTECTED_DIRECTORY_CHILDREN + 1)
    )
    if len(children) > MAX_PROTECTED_DIRECTORY_CHILDREN:
        _fail(
            "connector_campaign_log_directory_limit_exceeded",
            "Protected directory exceeds its frozen membership ceiling.",
        )
    matches = [
        child
        for child in children
        if child.name.casefold() == name.casefold()
    ]
    exact = [child for child in matches if child.name == name]
    if not must_exist:
        if matches:
            _fail(
                "connector_campaign_log_path_conflict",
                f"Protected path already exists or has a case alias: {name}.",
            )
        return parent / name
    if len(matches) != 1 or len(exact) != 1:
        _fail(
            "connector_campaign_log_parent_invalid",
            f"Protected parent is absent or case-aliased: {name}.",
        )
    child = exact[0]
    try:
        file_stat = os.lstat(child)
    except OSError as exc:
        raise ConnectorCampaignLogCaptureError(
            "connector_campaign_log_parent_invalid",
            f"Protected parent is unavailable: {name}.",
        ) from exc
    attributes = int(getattr(file_stat, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if (
        stat.S_ISLNK(file_stat.st_mode)
        or attributes & reparse
        or directory != stat.S_ISDIR(file_stat.st_mode)
    ):
        _fail(
            "connector_campaign_log_parent_unsafe",
            f"Protected path has an unsafe type: {name}.",
        )
    return child


def _managed_paths(
    authority: _CaptureAuthority,
) -> tuple[Path, Path, Path, Path, Path]:
    root = authority.evidence_root
    raw = str(root)
    if (
        "\x00" in raw
        or not root.is_absolute()
        or raw.startswith(("\\\\", "//", "\\\\?\\", "\\\\.\\"))
    ):
        _fail(
            "connector_campaign_log_root_invalid",
            "Evidence root must be an absolute local managed directory.",
        )
    try:
        _assert_no_reparse_components(root)
        resolved_root = root.resolve(strict=True)
    except (OSError, ConnectorEgressAuthorizationError) as exc:
        raise ConnectorCampaignLogCaptureError(
            "connector_campaign_log_root_invalid",
            "Evidence root is missing, reparse-backed, or unavailable.",
        ) from exc
    if not resolved_root.is_dir() or _forbidden_path(resolved_root):
        _fail(
            "connector_campaign_log_root_forbidden",
            "Evidence root overlaps an application, storage, or database root.",
        )
    logs = _exact_child(
        resolved_root,
        "logs",
        must_exist=True,
        directory=True,
    )
    seals = _exact_child(
        resolved_root,
        "log-seals",
        must_exist=True,
        directory=True,
    )
    _assert_no_reparse_components(logs)
    _assert_no_reparse_components(seals)
    campaign_dir = logs / authority.campaign_fingerprint
    manifest = campaign_dir / "manifest.json"
    seal = seals / f"{authority.campaign_fingerprint}.json"
    return resolved_root, logs, campaign_dir, manifest, seal


def begin_connector_campaign_log_capture(
    *,
    campaign_id: UUID,
    expected_campaign_fingerprint: str,
    expected_code_revision: str,
    now: datetime | None = None,
) -> ConnectorCampaignLogCaptureSession:
    started_at = _as_utc(now, label="capture start")
    writers: list[ConnectorCampaignLogWriter] = []
    raw_writers: list[OwnedLockedRawFileWriter] = []
    try:
        authority = _current_authority(
            campaign_id=campaign_id,
            expected_campaign_fingerprint=expected_campaign_fingerprint,
            expected_code_revision=expected_code_revision,
            started_at=started_at,
        )
        root, _, campaign_dir, manifest_path, seal_path = _managed_paths(
            authority
        )
        seal_stage = seal_path.with_name(f".{seal_path.name}.stage")
        for candidate in (seal_path, seal_stage):
            _exact_child(
                candidate.parent,
                candidate.name,
                must_exist=False,
                directory=False,
            )
        _exact_child(
            campaign_dir.parent,
            campaign_dir.name,
            must_exist=False,
            directory=True,
        )
        identities: list[StableRawFileIdentity] = []
        parent_identity: StableRawFileIdentity | None = None
        for index, (file_name, stream_class) in enumerate(_STREAMS):
            raw_writer = open_new_locked_raw_file_writer(
                root,
                campaign_dir / file_name,
                create_immediate_parent_exclusive=index == 0,
                expected_parent_identity=parent_identity,
            )
            if index == 0:
                parent_identity = raw_writer.parent_identity
            elif raw_writer.parent_identity != parent_identity:
                raw_writer.close()
                _fail(
                    "connector_campaign_log_parent_changed",
                    "Campaign log directory identity changed during begin.",
                )
            if raw_writer.link_count != 1:
                raw_writer.close()
                _fail(
                    "connector_campaign_log_link_count_invalid",
                    "Campaign log stream must have exactly one link.",
                )
            if raw_writer.identity in identities:
                raw_writer.close()
                _fail(
                    "connector_campaign_log_identity_duplicate",
                    "Campaign log streams must have distinct identities.",
                )
            identities.append(raw_writer.identity)
            raw_writers.append(raw_writer)
            writers.append(
                ConnectorCampaignLogWriter(raw_writer, stream_class)
            )
        _exact_stream_membership(
            campaign_dir,
            manifest_present=False,
        )
        for candidate in (seal_path, seal_stage):
            _exact_child(
                candidate.parent,
                candidate.name,
                must_exist=False,
                directory=False,
            )
        if parent_identity is None:  # pragma: no cover - fixed nonempty set
            _fail(
                "connector_campaign_log_begin_failed",
                "Campaign log directory identity was not established.",
            )
        writer_tuple = (
            writers[0],
            writers[1],
            writers[2],
            writers[3],
        )
        raw_writer_tuple = (
            raw_writers[0],
            raw_writers[1],
            raw_writers[2],
            raw_writers[3],
        )
        identity_tuple = (
            identities[0],
            identities[1],
            identities[2],
            identities[3],
        )
        capture = ConnectorCampaignLogCaptureSession(
            campaign_id=authority.campaign_id,
            campaign_fingerprint=authority.campaign_fingerprint,
            campaign_definition_sha256=(
                authority.campaign_definition_sha256
            ),
            code_revision=authority.code_revision,
            runtime_started_at=started_at,
            writers=writer_tuple,
            _binding_token=object(),
        )
        _register_capture_binding(
            capture,
            authority=authority,
            stream_identities=identity_tuple,
            parent_identity=parent_identity,
            writers=writer_tuple,
            raw_writers=raw_writer_tuple,
        )
        return capture
    except (
        ConnectorCampaignLogCaptureError,
        ConnectorEgressAuthorizationError,
        ConnectorEgressArmingError,
        StableRawStorageError,
        OSError,
    ) as exc:
        for writer in writers:
            try:
                writer.close()
            except BaseException:
                pass
        if isinstance(exc, ConnectorCampaignLogCaptureError):
            raise
        raise ConnectorCampaignLogCaptureError(
            "connector_campaign_log_begin_failed",
            "Campaign log capture could not be started safely.",
        ) from exc
    except BaseException:
        for writer in writers:
            try:
                writer.close()
            except BaseException:
                pass
        raise


@dataclass(frozen=True, slots=True)
class _RunDatabaseSnapshot:
    connector_run_id: str
    connector_key: str
    source_system: str
    source_mode: str
    status: str
    request_config_bytes: bytes
    request_fingerprint: str | None
    submission_idempotency_key: str | None
    submitted_at: str
    started_at: str | None
    completed_at: str
    execution_lease_owner: str | None
    execution_lease_token: str | None
    row_bytes: bytes
    events: tuple[bytes, ...]


@dataclass(frozen=True, slots=True)
class _DatabaseSnapshot:
    runs: tuple[_RunDatabaseSnapshot, ...]

    @property
    def run_ids(self) -> tuple[str, ...]:
        return tuple(run.connector_run_id for run in self.runs)


def _event_id(run_id: str, kind: str) -> str:
    return str(
        uuid5(
            NAMESPACE_URL,
            f"project6:connector-egress:{run_id}:{kind}:0",
        )
    )


def _assert_run_envelope(
    run: ConnectorRun,
    binding: _ExpectedRunBinding,
    authority: _CaptureAuthority,
) -> Mapping[str, Any]:
    if not is_strict_egress_run(run):
        _fail(
            "connector_campaign_log_run_identity_invalid",
            "Campaign run does not carry strict egress provenance.",
        )
    raw_envelope = run.request_config_json.get("connector_egress_arming")
    if not isinstance(raw_envelope, dict):
        _fail(
            "connector_campaign_log_run_envelope_invalid",
            "Campaign run arming envelope is missing.",
        )
    envelope = dict(raw_envelope)
    try:
        _assert_envelope_fingerprint(run, envelope)
    except ConnectorEgressArmingError as exc:
        raise ConnectorCampaignLogCaptureError(
            "connector_campaign_log_run_envelope_invalid",
            "Campaign run arming fingerprint does not rederive.",
        ) from exc
    expected_core = strict_json_loads(binding.envelope_core_bytes)
    if not isinstance(expected_core, dict):
        _fail(
            "connector_campaign_log_internal_contract_invalid",
            "Expected arming envelope core is invalid.",
        )
    expected_keys = set(expected_core) | {
        "authorization_receipt",
        "arming_fingerprint",
    }
    if binding.connector_key == "sciencebase_mcs":
        expected_keys |= {
            "predecessor_nrc_connector_run_id",
            "predecessor_nrc_ledger_terminal_hash",
        }
    if set(envelope) != expected_keys:
        _fail(
            "connector_campaign_log_run_envelope_mismatch",
            "Campaign run arming envelope has missing or extra fields.",
        )
    actual_core = {key: envelope[key] for key in expected_core}
    if canonical_json_bytes(actual_core) != binding.envelope_core_bytes:
        _fail(
            "connector_campaign_log_run_envelope_mismatch",
            "Campaign run arming authority differs from protected evidence.",
        )
    try:
        receipt = ConnectorEgressAuthorizationReceipt.model_validate(
            envelope["authorization_receipt"]
        )
    except Exception as exc:
        raise ConnectorCampaignLogCaptureError(
            "connector_campaign_log_run_receipt_invalid",
            "Campaign run authorization receipt is invalid.",
        ) from exc
    receipt_expected = {
        "connector_key": binding.connector_key,
        "campaign_id": authority.campaign_id,
        "campaign_fingerprint": authority.campaign_fingerprint,
        "campaign_definition_sha256": (
            authority.campaign_definition_sha256
        ),
        "grant_sha256": binding.grant_sha256,
        "canonical_grant_fingerprint": (
            binding.canonical_grant_fingerprint
        ),
        "introduction_index_revision": (
            authority.introduction_index_revision
        ),
        "introduction_index_sha256": (
            authority.introduction_index_sha256
        ),
        "access": "write",
    }
    if any(
        getattr(receipt, key) != value
        for key, value in receipt_expected.items()
    ):
        _fail(
            "connector_campaign_log_run_receipt_mismatch",
            "Campaign run receipt differs from protected evidence.",
        )
    if (
        not _HEX_64.fullmatch(receipt.operator_ref_hash)
        or not _HEX_64.fullmatch(receipt.workspace_ref_hash)
        or not receipt.auth_owner_mode
    ):
        _fail(
            "connector_campaign_log_run_receipt_invalid",
            "Campaign run receipt principal bindings are malformed.",
        )
    if binding.connector_key == "sciencebase_mcs":
        nrc_id = next(
            item.connector_run_id
            for item in authority.run_bindings
            if item.connector_key == "nrc_adams_aps"
        )
        if (
            envelope["predecessor_nrc_connector_run_id"] != nrc_id
            or not isinstance(
                envelope["predecessor_nrc_ledger_terminal_hash"],
                str,
            )
            or not _HEX_64.fullmatch(
                envelope["predecessor_nrc_ledger_terminal_hash"]
            )
        ):
            _fail(
                "connector_campaign_log_predecessor_mismatch",
                "ScienceBase predecessor binding is malformed or mismatched.",
            )
    if (
        run.connector_run_id != binding.connector_run_id
        or run.connector_key != binding.connector_key
        or run.source_system != binding.source_system
        or run.source_mode != "strict_live_egress"
        or not isinstance(run.submission_idempotency_key, str)
        or not run.submission_idempotency_key.startswith("egress-arm:")
    ):
        _fail(
            "connector_campaign_log_run_identity_mismatch",
            "Campaign run identity differs from deterministic authority.",
        )
    return envelope


def _event_snapshot(event: ConnectorRunEvent) -> bytes:
    return canonical_json_bytes(
        {
            "connector_run_event_id": event.connector_run_event_id,
            "connector_run_id": event.connector_run_id,
            "connector_run_target_id": event.connector_run_target_id,
            "phase": event.phase,
            "stage": event.stage,
            "event_type": event.event_type,
            "status_before": event.status_before,
            "status_after": event.status_after,
            "reason_code": event.reason_code,
            "error_class": event.error_class,
            "message": event.message,
            "metrics_json": event.metrics_json,
            "created_at": _db_utc(event.created_at),
        }
    )


def _run_row_snapshot(run: ConnectorRun) -> bytes:
    row: dict[str, Any] = {}
    for column in ConnectorRun.__table__.columns:
        value = getattr(run, column.key)
        if isinstance(value, datetime):
            normalized = _db_utc(value)
            if normalized is None:  # pragma: no cover - type narrowing
                row[column.key] = None
            else:
                row[column.key] = _timestamp(normalized)
        else:
            row[column.key] = value
    return canonical_json_bytes(row)


def _validate_database_snapshot(
    db: Session,
    *,
    authority: _CaptureAuthority,
    runtime_started_at: datetime,
    runtime_stopped_at: datetime,
    lock_rows: bool,
) -> _DatabaseSnapshot:
    expected_by_id = {
        binding.connector_run_id: binding
        for binding in authority.run_bindings
    }
    expected_ids = tuple(sorted(expected_by_id))
    arming = ConnectorRun.request_config_json["connector_egress_arming"]
    run_query = (
        select(ConnectorRun)
        .where(
            or_(
                ConnectorRun.connector_run_id.in_(expected_ids),
                and_(
                    ConnectorRun.source_mode == "strict_live_egress",
                    arming["campaign_id"].as_string()
                    == authority.campaign_id,
                    arming["campaign_fingerprint"].as_string()
                    == authority.campaign_fingerprint,
                ),
            )
        )
        .order_by(ConnectorRun.connector_run_id)
        .limit(len(expected_ids) + 1)
        .execution_options(populate_existing=True)
    )
    if lock_rows and db.get_bind().dialect.name != "sqlite":
        run_query = run_query.with_for_update()
    candidates = list(db.scalars(run_query).all())
    campaign_runs: list[ConnectorRun] = []
    for run in candidates:
        raw_config = run.request_config_json
        raw_envelope = (
            raw_config.get("connector_egress_arming")
            if isinstance(raw_config, dict)
            else None
        )
        binds_campaign = bool(
            isinstance(raw_envelope, dict)
            and raw_envelope.get("campaign_id") == authority.campaign_id
            and raw_envelope.get("campaign_fingerprint")
            == authority.campaign_fingerprint
        )
        if run.connector_run_id in expected_by_id or binds_campaign:
            campaign_runs.append(run)
    actual_ids = tuple(
        sorted(run.connector_run_id for run in campaign_runs)
    )
    nrc_id = next(
        binding.connector_run_id
        for binding in authority.run_bindings
        if binding.connector_key == "nrc_adams_aps"
    )
    sciencebase_id = next(
        binding.connector_run_id
        for binding in authority.run_bindings
        if binding.connector_key == "sciencebase_mcs"
    )
    allowed = {(nrc_id,), tuple(sorted((nrc_id, sciencebase_id)))}
    if actual_ids not in allowed:
        _fail(
            "connector_campaign_log_run_cardinality_invalid",
            "Extant campaign runs must be NRC-only or exact NRC+ScienceBase.",
        )
    seal_ids = tuple(
        _event_id(run_id, "campaign_log_capture_sealed")
        for run_id in actual_ids
    )
    if db.scalar(
        select(ConnectorRunEvent.connector_run_event_id)
        .where(ConnectorRunEvent.connector_run_event_id.in_(seal_ids))
        .limit(1)
    ) is not None:
        _fail(
            "connector_campaign_log_event_conflict",
            "A deterministic campaign seal event already exists.",
        )
    event_query = (
        select(ConnectorRunEvent)
        .where(ConnectorRunEvent.connector_run_id.in_(actual_ids))
        .order_by(
            ConnectorRunEvent.connector_run_id,
            ConnectorRunEvent.created_at,
            ConnectorRunEvent.connector_run_event_id,
        )
        .execution_options(populate_existing=True)
    )
    if lock_rows and db.get_bind().dialect.name != "sqlite":
        event_query = event_query.with_for_update()
    all_events = list(db.scalars(event_query).all())
    events_by_run: dict[str, list[ConnectorRunEvent]] = {
        run_id: [] for run_id in actual_ids
    }
    for event in all_events:
        events_by_run[event.connector_run_id].append(event)
    snapshots: list[_RunDatabaseSnapshot] = []
    for run in sorted(campaign_runs, key=lambda item: item.connector_run_id):
        binding = expected_by_id.get(run.connector_run_id)
        if binding is None:
            _fail(
                "connector_campaign_log_extra_run",
                "An extra strict run binds the exact campaign.",
            )
        envelope = _assert_run_envelope(run, binding, authority)
        submitted_at = _db_utc(run.submitted_at)
        started_at = _db_utc(run.started_at)
        completed_at = _db_utc(run.completed_at)
        if (
            run.status not in _TERMINAL_STATUSES
            or run.execution_lease_owner is not None
            or run.execution_lease_token is not None
            or submitted_at is None
            or completed_at is None
            or not (
                runtime_started_at
                <= submitted_at
                <= completed_at
                <= runtime_stopped_at
            )
            or (
                started_at is not None
                and not submitted_at <= started_at <= completed_at
            )
        ):
            _fail(
                "connector_campaign_log_run_not_terminal",
                "Campaign run is nonterminal, leased, or chronologically invalid.",
            )
        events = events_by_run[run.connector_run_id]
        terminal_id = _event_id(
            run.connector_run_id,
            "egress_run_terminal",
        )
        terminals = [
            event
            for event in events
            if event.event_type == "egress_run_terminal"
            or event.connector_run_event_id == terminal_id
        ]
        if len(terminals) != 1:
            _fail(
                "connector_campaign_log_terminal_event_invalid",
                "Campaign run must have one deterministic terminal event.",
            )
        terminal = terminals[0]
        metrics = (
            terminal.metrics_json
            if isinstance(terminal.metrics_json, dict)
            else {}
        )
        expected_metric_keys = {
            "outcome_class",
            "arming_fingerprint",
            "campaign_introduction_index_revision",
            "campaign_introduction_index_sha256",
        }
        if (
            terminal.connector_run_event_id != terminal_id
            or terminal.connector_run_target_id is not None
            or terminal.phase != "execution"
            or terminal.stage != "terminal"
            or terminal.event_type != "egress_run_terminal"
            or terminal.status_before != "running"
            or terminal.status_after != run.status
            or terminal.error_class is not None
            or terminal.message is not None
            or set(metrics) != expected_metric_keys
            or terminal.reason_code != metrics.get("outcome_class")
            or metrics.get("arming_fingerprint")
            != envelope.get("arming_fingerprint")
            or metrics.get("campaign_introduction_index_revision")
            != authority.introduction_index_revision
            or metrics.get("campaign_introduction_index_sha256")
            != authority.introduction_index_sha256
            or _db_utc(terminal.created_at) != completed_at
        ):
            _fail(
                "connector_campaign_log_terminal_event_mismatch",
                "Campaign terminal event differs from run authority.",
            )
        seal_id = _event_id(
            run.connector_run_id,
            "campaign_log_capture_sealed",
        )
        if any(
            event.event_type == "campaign_log_capture_sealed"
            or event.connector_run_event_id == seal_id
            for event in events
        ):
            _fail(
                "connector_campaign_log_event_conflict",
                "Campaign seal event already exists.",
            )
        if len(events) + 1 > _EVENT_CAPS[run.connector_key]:
            _fail(
                "connector_campaign_log_event_cap_exhausted",
                "Campaign run event cap cannot admit the seal event.",
            )
        for event in events:
            created_at = _db_utc(event.created_at)
            if (
                created_at is None
                or not (
                    runtime_started_at
                    <= submitted_at
                    <= created_at
                    <= completed_at
                    <= runtime_stopped_at
                )
            ):
                _fail(
                    "connector_campaign_log_event_chronology_invalid",
                    "Pre-seal event chronology is outside the capture interval.",
                )
        snapshots.append(
            _RunDatabaseSnapshot(
                connector_run_id=run.connector_run_id,
                connector_key=run.connector_key,
                source_system=run.source_system,
                source_mode=run.source_mode,
                status=run.status,
                request_config_bytes=canonical_json_bytes(
                    run.request_config_json
                ),
                request_fingerprint=run.request_fingerprint,
                submission_idempotency_key=run.submission_idempotency_key,
                submitted_at=_timestamp(submitted_at),
                started_at=(
                    _timestamp(started_at)
                    if started_at is not None
                    else None
                ),
                completed_at=_timestamp(completed_at),
                execution_lease_owner=run.execution_lease_owner,
                execution_lease_token=run.execution_lease_token,
                row_bytes=_run_row_snapshot(run),
                events=tuple(_event_snapshot(event) for event in events),
            )
        )
    return _DatabaseSnapshot(runs=tuple(snapshots))


def _exact_stream_membership(
    campaign_dir: Path,
    *,
    manifest_present: bool,
) -> None:
    expected = [name for name, _ in _STREAMS]
    if manifest_present:
        expected.append("manifest.json")
    actual = [
        child.name
        for child in islice(campaign_dir.iterdir(), len(expected) + 1)
    ]
    if (
        len(actual) != len(expected)
        or sorted(actual) != sorted(expected)
        or len({name.casefold() for name in actual}) != len(actual)
    ):
        _fail(
            "connector_campaign_log_stream_membership_invalid",
            "Campaign log directory does not contain the exact stream set.",
        )
    for name in expected:
        path = campaign_dir / name
        file_stat = os.lstat(path)
        attributes = int(getattr(file_stat, "st_file_attributes", 0))
        reparse = int(
            getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        )
        if (
            stat.S_ISLNK(file_stat.st_mode)
            or attributes & reparse
            or not stat.S_ISREG(file_stat.st_mode)
        ):
            _fail(
                "connector_campaign_log_stream_unsafe",
                "Campaign log member is not a regular non-reparse file.",
            )


def _snapshot_streams(
    capture: ConnectorCampaignLogCaptureSession,
    *,
    binding: _CaptureBinding,
    manifest_present: bool,
) -> tuple[
    tuple[
        ConnectorCampaignLogFileV1,
        ConnectorCampaignLogFileV1,
        ConnectorCampaignLogFileV1,
        ConnectorCampaignLogFileV1,
    ],
    tuple[
        LockedRawFileSnapshot,
        LockedRawFileSnapshot,
        LockedRawFileSnapshot,
        LockedRawFileSnapshot,
    ],
]:
    if not _writer_binding_matches(capture, binding):
        _fail(
            "connector_campaign_log_writer_binding_invalid",
            "Campaign log writers differ from the server-bound writers.",
        )
    authority = binding.authority
    _, _, campaign_dir, _, _ = _managed_paths(authority)
    _exact_stream_membership(
        campaign_dir,
        manifest_present=manifest_present,
    )
    if tuple(writer.stream_class for writer in capture.writers) != tuple(
        stream_class for _, stream_class in _STREAMS
    ):
        _fail(
            "connector_campaign_log_writer_order_invalid",
            "Campaign log writers do not retain fixed stream order.",
        )
    if any(
        not writer.closed or not writer._closed_clean
        for writer in capture.writers
    ):
        _fail(
            "connector_campaign_log_writer_not_final",
            "Every session-owned writer must be explicitly flushed and closed.",
        )
    snapshots: list[LockedRawFileSnapshot] = []
    files: list[ConnectorCampaignLogFileV1] = []
    aggregate = 0
    for index, (file_name, stream_class) in enumerate(_STREAMS):
        remaining = MAX_AGGREGATE_BYTES - aggregate
        if remaining < 0:
            _fail(
                "connector_campaign_log_aggregate_oversized",
                "Campaign log aggregate exceeds 32 MiB.",
            )
        try:
            with locked_raw_file_snapshot(
                authority.evidence_root,
                campaign_dir / file_name,
                max_bytes=min(MAX_STREAM_BYTES, remaining),
                expected_identity=binding.stream_identities[index],
                expected_parent_identity=binding.parent_identity,
                required_link_count=1,
            ) as snapshot:
                snapshots.append(snapshot)
        except StableRawStorageError as exc:
            raise ConnectorCampaignLogCaptureError(
                "connector_campaign_log_stream_invalid",
                "Campaign log stream changed, aliased, or exceeded a bound.",
            ) from exc
        aggregate += snapshot.size
        files.append(
            ConnectorCampaignLogFileV1(
                relative_path=(
                    f"{authority.log_dir_relative_path}/{file_name}"
                ),
                stream_class=stream_class,
                byte_count=snapshot.size,
                sha256=snapshot.sha256,
            )
        )
    identities = tuple(snapshot.identity for snapshot in snapshots)
    if (
        any(identity is None for identity in identities)
        or len(set(identities)) != len(identities)
        or aggregate > MAX_AGGREGATE_BYTES
    ):
        _fail(
            "connector_campaign_log_stream_identity_invalid",
            "Campaign log streams are aliased or exceed the aggregate bound.",
        )
    return (
        (files[0], files[1], files[2], files[3]),
        (snapshots[0], snapshots[1], snapshots[2], snapshots[3]),
    )


def _require_clean_session(db: Session) -> None:
    if not isinstance(db, Session):
        _fail(
            "connector_campaign_log_session_invalid",
            "Seal requires a SQLAlchemy Session.",
        )
    if (
        db.in_transaction()
        or bool(db.new)
        or bool(db.dirty)
        or bool(db.deleted)
    ):
        _fail(
            "connector_campaign_log_session_not_clean",
            "Seal Session must be clean and transaction-free.",
        )
    bind = db.get_bind()
    bind_in_transaction = getattr(bind, "in_transaction", None)
    if callable(bind_in_transaction) and bind_in_transaction():
        _fail(
            "connector_campaign_log_connection_not_clean",
            "Seal connection already owns an external transaction.",
        )


def _preflight_database(
    db: Session,
    *,
    authority: _CaptureAuthority,
    runtime_started_at: datetime,
    runtime_stopped_at: datetime,
) -> _DatabaseSnapshot:
    bind = db.get_bind()
    with Session(
        bind=bind,
        autoflush=False,
        expire_on_commit=False,
    ) as isolated:
        try:
            return _validate_database_snapshot(
                isolated,
                authority=authority,
                runtime_started_at=runtime_started_at,
                runtime_stopped_at=runtime_stopped_at,
                lock_rows=False,
            )
        finally:
            if isolated.in_transaction():
                isolated.rollback()


def _seal_event_metrics(
    *,
    authority: _CaptureAuthority,
    seal: ConnectorCampaignLogSealV1,
    seal_relative_path: str,
    seal_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_id": (
            "project6.connector_campaign_log_seal_event_metrics.v1"
        ),
        "campaign_id": authority.campaign_id,
        "campaign_fingerprint": authority.campaign_fingerprint,
        "campaign_definition_sha256": (
            authority.campaign_definition_sha256
        ),
        "code_revision": authority.code_revision,
        "campaign_introduction_index_revision": (
            authority.introduction_index_revision
        ),
        "campaign_introduction_index_sha256": (
            authority.introduction_index_sha256
        ),
        "manifest_relative_path": seal.manifest_relative_path,
        "manifest_sha256": seal.manifest_sha256,
        "file_set_hash": seal.file_set_hash,
        "seal_relative_path": seal_relative_path,
        "seal_sha256": seal_sha256,
        "connector_run_ids": list(seal.connector_run_ids),
        "sealed_at": _timestamp(seal.sealed_at),
    }


def _persist_seal_events(
    db: Session,
    *,
    authority: _CaptureAuthority,
    preflight: _DatabaseSnapshot,
    runtime_started_at: datetime,
    runtime_stopped_at: datetime,
    seal: ConnectorCampaignLogSealV1,
    seal_sha256: str,
) -> tuple[str, ...]:
    _require_clean_session(db)
    event_ids = tuple(
        sorted(
            _event_id(run_id, "campaign_log_capture_sealed")
            for run_id in preflight.run_ids
        )
    )
    dialect = db.get_bind().dialect.name
    try:
        if dialect == "sqlite":
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        elif dialect == "postgresql":
            db.execute(
                text("LOCK TABLE connector_run IN EXCLUSIVE MODE")
            )
            db.execute(
                text("LOCK TABLE connector_run_event IN EXCLUSIVE MODE")
            )
        else:
            _fail(
                "connector_campaign_log_dialect_unsupported",
                "Campaign log sealing requires SQLite or PostgreSQL.",
            )
        current = _validate_database_snapshot(
            db,
            authority=authority,
            runtime_started_at=runtime_started_at,
            runtime_stopped_at=runtime_stopped_at,
            lock_rows=True,
        )
        if current != preflight:
            _fail(
                "connector_campaign_log_database_changed",
                "Campaign run/event state changed after preflight.",
            )
        metrics = _seal_event_metrics(
            authority=authority,
            seal=seal,
            seal_relative_path=authority.seal_relative_path,
            seal_sha256=seal_sha256,
        )
        events: list[ConnectorRunEvent] = []
        for run in current.runs:
            events.append(
                ConnectorRunEvent(
                    connector_run_event_id=_event_id(
                        run.connector_run_id,
                        "campaign_log_capture_sealed",
                    ),
                    connector_run_id=run.connector_run_id,
                    connector_run_target_id=None,
                    phase="evidence",
                    stage="campaign_log_capture",
                    event_type="campaign_log_capture_sealed",
                    status_before=run.status,
                    status_after=run.status,
                    reason_code="protected_log_capture_sealed",
                    error_class=None,
                    message=None,
                    metrics_json=metrics,
                    created_at=seal.sealed_at,
                )
            )
        db.add_all(events)
        db.flush()
        persisted_events = list(
            db.scalars(
                select(ConnectorRunEvent)
                .where(
                    ConnectorRunEvent.connector_run_id.in_(
                        current.run_ids
                    )
                )
                .order_by(
                    ConnectorRunEvent.connector_run_id,
                    ConnectorRunEvent.created_at,
                    ConnectorRunEvent.connector_run_event_id,
                )
                .execution_options(populate_existing=True)
            ).all()
        )
        persisted_by_run: dict[str, list[ConnectorRunEvent]] = {
            run_id: [] for run_id in current.run_ids
        }
        for event in persisted_events:
            persisted_by_run[event.connector_run_id].append(event)
        new_by_run = {
            event.connector_run_id: event for event in events
        }
        for prior in current.runs:
            actual = persisted_by_run[prior.connector_run_id]
            expected_rows = tuple(
                sorted(
                    (
                        *prior.events,
                        _event_snapshot(
                            new_by_run[prior.connector_run_id]
                        ),
                    )
                )
            )
            actual_rows = tuple(
                sorted(_event_snapshot(event) for event in actual)
            )
            if (
                len(actual) != len(prior.events) + 1
                or len(actual) > _EVENT_CAPS[prior.connector_key]
                or actual_rows != expected_rows
            ):
                _fail(
                    "connector_campaign_log_postflush_invalid",
                    "Post-flush events differ from the exact sealed set.",
                )
    except BaseException as exc:
        try:
            db.rollback()
        except BaseException as rollback_exc:
            try:
                db.invalidate()
            except BaseException:
                pass
            raise ConnectorCampaignLogCaptureError(
                "precommit_cleanup_unconfirmed",
                "Pre-commit failure occurred and rollback was not confirmed.",
            ) from rollback_exc
        if isinstance(exc, ConnectorCampaignLogCaptureError):
            raise
        raise ConnectorCampaignLogCaptureError(
            "connector_campaign_log_database_write_failed",
            "Seal event transaction failed before commit.",
        ) from exc
    try:
        db.commit()
    except BaseException as exc:
        try:
            db.invalidate()
        except BaseException:
            pass
        raise ConnectorCampaignLogCaptureCommitAmbiguous(
            "commit_outcome_ambiguous",
            "Seal event commit acknowledgement failed; outcome is ambiguous.",
        ) from exc
    return event_ids


def seal_connector_campaign_log_capture(
    db: Session,
    *,
    capture: ConnectorCampaignLogCaptureSession,
    runtime_stopped_at: datetime,
    now: datetime | None = None,
) -> ConnectorCampaignLogCaptureResult:
    if not isinstance(capture, ConnectorCampaignLogCaptureSession):
        _fail(
            "connector_campaign_log_session_invalid",
            "Seal requires the server-owned capture session.",
        )
    binding = _require_capture_binding(capture)
    bound = binding.authority
    if (
        capture.campaign_id != bound.campaign_id
        or capture.campaign_fingerprint != bound.campaign_fingerprint
        or capture.campaign_definition_sha256
        != bound.campaign_definition_sha256
        or capture.code_revision != bound.code_revision
        or capture.runtime_started_at != bound.runtime_started_at
    ):
        _fail(
            "connector_campaign_log_session_binding_mismatch",
            "Capture projections differ from server-bound authority.",
        )
    stopped_at = _as_utc(
        runtime_stopped_at,
        label="runtime stop",
    )
    sealed_at = _as_utc(now, label="seal time")
    if (
        stopped_at < capture.runtime_started_at
        or sealed_at < stopped_at
    ):
        _fail(
            "connector_campaign_log_time_inversion",
            "Runtime stop and seal time must preserve capture chronology.",
        )
    _require_clean_session(db)
    authority = _historical_authority(capture, bound=bound)
    root, _, _, manifest_path, seal_path = _managed_paths(authority)
    seal_stage_path = seal_path.with_name(f".{seal_path.name}.stage")
    for candidate in (seal_path, seal_stage_path):
        _exact_child(
            candidate.parent,
            candidate.name,
            must_exist=False,
            directory=False,
        )
    files, first_snapshots = _snapshot_streams(
        capture,
        binding=binding,
        manifest_present=False,
    )
    manifest = ConnectorCampaignLogManifestV1(
        schema_id="project6.connector_campaign_log_manifest.v1",
        campaign_id=authority.campaign_id,
        campaign_fingerprint=authority.campaign_fingerprint,
        campaign_definition_sha256=(
            authority.campaign_definition_sha256
        ),
        code_revision=authority.code_revision,
        runtime_started_at=capture.runtime_started_at,
        runtime_stopped_at=stopped_at,
        files=files,
    )
    file_set_preimage = {
        "schema_id": "project6.connector_campaign_log_file_set.v1",
        "files": [
            file.model_dump(mode="python")
            for file in manifest.files
        ],
    }
    file_set_hash = hashlib.sha256(
        canonical_json_bytes(file_set_preimage)
    ).hexdigest()
    manifest_bytes = canonical_json_bytes(manifest)
    if len(manifest_bytes) > MAX_PROTECTED_JSON_BYTES:
        _fail(
            "connector_campaign_log_manifest_oversized",
            "Canonical campaign log manifest exceeds 64 KiB.",
        )
    preflight = _preflight_database(
        db,
        authority=authority,
        runtime_started_at=capture.runtime_started_at,
        runtime_stopped_at=stopped_at,
    )
    _require_clean_session(db)
    try:
        try:
            manifest_snapshot = publish_atomic_strict_new_locked_raw_file(
                root,
                manifest_path,
                manifest_bytes,
                max_bytes=MAX_PROTECTED_JSON_BYTES,
                expected_parent_identity=binding.parent_identity,
            )
        except StableRawStorageError as exc:
            raise ConnectorCampaignLogCaptureError(
                "connector_campaign_log_manifest_publish_failed",
                "Campaign log manifest publication failed closed.",
            ) from exc
        _, second_snapshots = _snapshot_streams(
            capture,
            binding=binding,
            manifest_present=True,
        )
        if tuple(
            (item.identity, item.size, item.sha256)
            for item in second_snapshots
        ) != tuple(
            (item.identity, item.size, item.sha256)
            for item in first_snapshots
        ):
            _fail(
                "connector_campaign_log_stream_changed",
                "Campaign log streams changed after manifest publication.",
            )
        manifest_sha256 = manifest_snapshot.sha256
        seal = ConnectorCampaignLogSealV1(
            schema_id="project6.connector_campaign_log_seal.v1",
            campaign_id=authority.campaign_id,
            campaign_fingerprint=authority.campaign_fingerprint,
            campaign_definition_sha256=(
                authority.campaign_definition_sha256
            ),
            campaign_introduction_index_revision=(
                authority.introduction_index_revision
            ),
            campaign_introduction_index_sha256=(
                authority.introduction_index_sha256
            ),
            code_revision=authority.code_revision,
            manifest_relative_path=authority.manifest_relative_path,
            manifest_sha256=manifest_sha256,
            file_set_hash=file_set_hash,
            connector_run_ids=preflight.run_ids,
            sealed_at=sealed_at,
        )
        seal_bytes = canonical_json_bytes(seal)
        if len(seal_bytes) > MAX_PROTECTED_JSON_BYTES:
            _fail(
                "connector_campaign_log_seal_oversized",
                "Canonical campaign log seal exceeds 64 KiB.",
            )
        try:
            seal_snapshot = publish_atomic_strict_new_locked_raw_file(
                root,
                seal_path,
                seal_bytes,
                max_bytes=MAX_PROTECTED_JSON_BYTES,
            )
        except StableRawStorageError as exc:
            raise ConnectorCampaignLogCaptureError(
                "connector_campaign_log_seal_publish_failed",
                "Campaign log seal publication failed closed.",
            ) from exc
        event_ids = tuple(
            sorted(
                _event_id(run_id, "campaign_log_capture_sealed")
                for run_id in preflight.run_ids
            )
        )
        result = ConnectorCampaignLogCaptureResult(
            manifest=manifest,
            manifest_sha256=manifest_sha256,
            file_set_hash=file_set_hash,
            seal=seal,
            seal_sha256=seal_snapshot.sha256,
            event_ids=event_ids,
        )
    finally:
        _retire_capture_binding(capture, binding)
    _require_clean_session(db)
    _persist_seal_events(
        db,
        authority=authority,
        preflight=preflight,
        runtime_started_at=capture.runtime_started_at,
        runtime_stopped_at=stopped_at,
        seal=seal,
        seal_sha256=seal_snapshot.sha256,
    )
    return result


@dataclass(frozen=True, slots=True)
class _ReadOnlyFileSnapshot:
    relative_path: str
    data: bytes
    size: int
    sha256: str
    identity: tuple[int, int, int, int, int]


@dataclass(frozen=True, slots=True)
class _ReadOnlyDatabaseSnapshot:
    run_rows: tuple[bytes, ...]
    event_rows: tuple[bytes, ...]
    event_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ReadOnlyCampaignProjection:
    model: DualLiveCampaignDefinitionV1
    raw_sha256: str
    canonical_fingerprint: str


def _read_stable_capture_bytes(
    root: Path,
    relative_path: str,
    *,
    max_bytes: int,
) -> _ReadOnlyFileSnapshot:
    try:
        path = _resolve_evidence_path(
            root,
            relative_path,
            label="campaign log capture object",
            must_exist=True,
        )
        before = os.lstat(path)
    except (OSError, ConnectorEgressAuthorizationError) as exc:
        raise ConnectorCampaignLogCaptureError(
            "connector_campaign_log_read_object_invalid",
            "Campaign log capture object is missing or unsafe.",
        ) from exc
    attributes = int(getattr(before, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if (
        stat.S_ISLNK(before.st_mode)
        or attributes & reparse
        or not stat.S_ISREG(before.st_mode)
        or int(before.st_nlink) != 1
        or int(before.st_size) > max_bytes
    ):
        _fail(
            "connector_campaign_log_read_object_invalid",
            "Campaign log capture object is unsafe or exceeds its bound.",
        )
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            data = handle.read(max_bytes + 1)
        after = os.lstat(path)
    except OSError as exc:
        raise ConnectorCampaignLogCaptureError(
            "connector_campaign_log_read_object_invalid",
            "Campaign log capture object could not be read.",
        ) from exc
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_nlink")
    if any(
        getattr(before, field, None) != getattr(opened, field, None)
        or getattr(opened, field, None) != getattr(after, field, None)
        for field in stable_fields
    ) or len(data) != int(before.st_size):
        _fail(
            "connector_campaign_log_read_object_changed",
            "Campaign log capture object changed during verification.",
        )
    if len(data) > max_bytes:
        _fail(
            "connector_campaign_log_read_object_oversized",
            "Campaign log capture object exceeds its verification bound.",
        )
    normalized = PurePosixPath(relative_path).as_posix()
    if path.relative_to(root).as_posix() != normalized:
        _fail(
            "connector_campaign_log_read_object_path_mismatch",
            "Campaign log capture object path changed during verification.",
        )
    return _ReadOnlyFileSnapshot(
        relative_path=normalized,
        data=data,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        identity=(
            int(opened.st_dev),
            int(opened.st_ino),
            int(opened.st_size),
            int(opened.st_mtime_ns),
            int(opened.st_nlink),
        ),
    )


def _verify_index_chain_snapshot(
    chain: VerifiedEvidenceIndexChain,
) -> Path:
    if not isinstance(chain, VerifiedEvidenceIndexChain) or not chain.revisions:
        _fail(
            "connector_campaign_log_index_chain_invalid",
            "Capture verification requires a verified evidence-index chain.",
        )
    root = Path(chain.evidence_root)
    raw_root = str(root)
    if (
        not root.is_absolute()
        or raw_root.startswith(("\\\\", "//", "\\\\?\\", "\\\\.\\"))
    ):
        _fail(
            "connector_campaign_log_index_chain_invalid",
            "Evidence-index root must be an absolute local path.",
        )
    try:
        _assert_no_reparse_components(root)
        root = root.resolve(strict=True)
        indexes = _exact_child(
            root,
            "indexes",
            must_exist=True,
            directory=True,
        )
    except (OSError, ConnectorEgressAuthorizationError) as exc:
        raise ConnectorCampaignLogCaptureError(
            "connector_campaign_log_index_chain_invalid",
            "Evidence-index root is missing or unsafe.",
        ) from exc
    revisions = chain.revisions
    if (
        chain.evidence_root != root
        or chain.head != revisions[-1].model
        or chain.head_raw_sha256 != revisions[-1].raw_sha256
        or chain.head_path != revisions[-1].path
        or tuple(item.model.revision for item in revisions)
        != tuple(range(1, len(revisions) + 1))
        or len(revisions) > MAX_EVIDENCE_INDEX_REVISIONS
        or (len(revisions[0].model.campaigns),
            len(revisions[0].model.entries),
            len(revisions[0].model.log_captures))
        != (1, 2, 1)
    ):
        _fail(
            "connector_campaign_log_index_chain_invalid",
            "Evidence-index chain projection is internally inconsistent.",
        )
    expected_names = tuple(
        sorted(f"{item.raw_sha256}.json" for item in revisions)
    )
    actual_children = tuple(
        islice(indexes.iterdir(), MAX_EVIDENCE_INDEX_REVISIONS + 1)
    )
    if len(actual_children) > MAX_EVIDENCE_INDEX_REVISIONS:
        _fail(
            "connector_campaign_log_index_membership_invalid",
            "Evidence-index revision count exceeds its frozen ceiling.",
        )
    actual_names = tuple(sorted(child.name for child in actual_children))
    if (
        actual_names != expected_names
        or len({name.casefold() for name in actual_names}) != len(actual_names)
    ):
        _fail(
            "connector_campaign_log_index_membership_invalid",
            "Evidence-index directory contains undeclared objects.",
        )
    try:
        for position, revision in enumerate(revisions):
            _validate_index_slice_structure(revision.model)
            if position:
                _validate_successor(revisions[position - 1], revision)
            snapshot = _read_stable_capture_bytes(
                root,
                f"indexes/{revision.raw_sha256}.json",
                max_bytes=MAX_PROTECTED_JSON_BYTES,
            )
            if (
                snapshot.data != revision.raw_bytes
                or snapshot.sha256 != revision.raw_sha256
                or snapshot.data != canonical_json_bytes(revision.model)
                or revision.path != indexes / f"{revision.raw_sha256}.json"
            ):
                _fail(
                    "connector_campaign_log_index_snapshot_changed",
                    "Evidence-index bytes differ from the verified chain.",
                )
    except ConnectorEgressAuthorizationError as exc:
        raise ConnectorCampaignLogCaptureError(
            "connector_campaign_log_index_chain_invalid",
            "Evidence-index chain structure is invalid.",
        ) from exc
    return root


def _parse_canonical_capture_model(
    snapshot: _ReadOnlyFileSnapshot,
    model_type: Any,
    *,
    label: str,
) -> Any:
    try:
        payload = strict_json_loads(snapshot.data)
        if not isinstance(payload, dict):
            raise ValueError("protected JSON root must be an object")
        model = model_type.model_validate(payload)
    except (ValueError, TypeError) as exc:
        raise ConnectorCampaignLogCaptureError(
            "connector_campaign_log_read_json_invalid",
            f"{label} is invalid.",
        ) from exc
    if snapshot.data != canonical_json_bytes(model):
        _fail(
            "connector_campaign_log_read_json_not_canonical",
            f"{label} is not canonical JSON.",
        )
    return model


def _parse_protected_capture_model(
    snapshot: _ReadOnlyFileSnapshot,
    model_type: Any,
    *,
    label: str,
) -> Any:
    try:
        payload = strict_json_loads(snapshot.data)
        if not isinstance(payload, dict):
            raise ValueError("protected JSON root must be an object")
        return model_type.model_validate(payload)
    except (ValueError, TypeError) as exc:
        raise ConnectorCampaignLogCaptureError(
            "connector_campaign_log_read_json_invalid",
            f"{label} is invalid.",
        ) from exc


def _read_only_capture_paths(
    root: Path,
    *,
    campaign_fingerprint: str,
) -> tuple[Path, Path, Path]:
    logs = _exact_child(root, "logs", must_exist=True, directory=True)
    seals = _exact_child(root, "log-seals", must_exist=True, directory=True)
    campaign_dir = _exact_child(
        logs,
        campaign_fingerprint,
        must_exist=True,
        directory=True,
    )
    _exact_stream_membership(campaign_dir, manifest_present=True)
    manifest = campaign_dir / "manifest.json"
    seal = _exact_child(
        seals,
        f"{campaign_fingerprint}.json",
        must_exist=True,
        directory=False,
    )
    _exact_child(
        seals,
        f".{campaign_fingerprint}.json.stage",
        must_exist=False,
        directory=False,
    )
    return campaign_dir, manifest, seal


def _read_capture_file_set(
    root: Path,
    manifest: ConnectorCampaignLogManifestV1,
    *,
    manifest_relative_path: str,
    seal_relative_path: str,
) -> tuple[
    tuple[_ReadOnlyFileSnapshot, ...],
    Mapping[str, bytes],
]:
    snapshots: list[_ReadOnlyFileSnapshot] = []
    stream_bytes: dict[str, bytes] = {}
    aggregate = 0
    for item in manifest.files:
        snapshot = _read_stable_capture_bytes(
            root,
            item.relative_path,
            max_bytes=MAX_STREAM_BYTES,
        )
        aggregate += snapshot.size
        if aggregate > MAX_AGGREGATE_BYTES:
            _fail(
                "connector_campaign_log_read_aggregate_oversized",
                "Campaign log streams exceed the aggregate bound.",
            )
        if snapshot.size != item.byte_count or snapshot.sha256 != item.sha256:
            _fail(
                "connector_campaign_log_stream_digest_mismatch",
                "Campaign log stream differs from its manifest entry.",
            )
        snapshots.append(snapshot)
        stream_bytes[item.relative_path] = snapshot.data
    snapshots.append(
        _read_stable_capture_bytes(
            root,
            manifest_relative_path,
            max_bytes=MAX_PROTECTED_JSON_BYTES,
        )
    )
    snapshots.append(
        _read_stable_capture_bytes(
            root,
            seal_relative_path,
            max_bytes=MAX_PROTECTED_JSON_BYTES,
        )
    )
    return tuple(snapshots), MappingProxyType(stream_bytes)


def _derive_expected_run_ids(
    root: Path,
    definition_ref: Any,
    entries: tuple[Any, ...],
    *,
    authority: _CaptureAuthority,
) -> tuple[
    Mapping[str, _ExpectedRunBinding],
    tuple[_ReadOnlyFileSnapshot, ...],
]:
    definition_snapshot = _read_stable_capture_bytes(
        root,
        definition_ref.definition_relative_path,
        max_bytes=MAX_PROTECTED_JSON_BYTES,
    )
    definition = _parse_protected_capture_model(
        definition_snapshot,
        DualLiveCampaignDefinitionV1,
        label="archived campaign definition",
    )
    campaign_fingerprint = hashlib.sha256(
        canonical_json_bytes(definition)
    ).hexdigest()
    if (
        definition_ref.definition_relative_path
        != f"campaigns/{definition_ref.raw_definition_sha256}.json"
        or definition_snapshot.sha256 != definition_ref.raw_definition_sha256
        or str(definition.campaign_id) != authority.campaign_id
        or definition.code_revision != authority.code_revision
        or campaign_fingerprint != authority.campaign_fingerprint
    ):
        _fail(
            "connector_campaign_log_read_definition_mismatch",
            "Indexed campaign definition differs from capture authority.",
        )
    campaign = _ReadOnlyCampaignProjection(
        model=definition,
        raw_sha256=definition_snapshot.sha256,
        canonical_fingerprint=campaign_fingerprint,
    )
    run_ids: dict[str, str] = {}
    bindings: dict[str, _ExpectedRunBinding] = {}
    snapshots = [definition_snapshot]
    for entry in sorted(entries, key=lambda item: item.connector_key):
        snapshot = _read_stable_capture_bytes(
            root,
            entry.grant_relative_path,
            max_bytes=MAX_PROTECTED_JSON_BYTES,
        )
        grant = _parse_protected_capture_model(
            snapshot,
            ConnectorEgressGrantV1,
            label="archived connector grant",
        )
        canonical_fingerprint = hashlib.sha256(
            canonical_json_bytes(grant)
        ).hexdigest()
        if (
            snapshot.sha256 != entry.raw_grant_sha256
            or entry.grant_relative_path
            != f"grants/{entry.raw_grant_sha256}.json"
            or canonical_fingerprint != entry.canonical_grant_fingerprint
            or grant.connector_key != entry.connector_key
            or grant.campaign_id != authority.campaign_id
            or grant.campaign_fingerprint != authority.campaign_fingerprint
            or grant.campaign_definition_sha256
            != authority.campaign_definition_sha256
            or grant.code_revision != authority.code_revision
        ):
            _fail(
                "connector_campaign_log_read_grant_mismatch",
                "Indexed connector grant differs from campaign authority.",
            )
        try:
            _validate_grant_intersection(
                definition,
                grant,
                raw_definition_sha256=definition_snapshot.sha256,
                canonical_campaign_fingerprint=campaign_fingerprint,
            )
        except ConnectorEgressAuthorizationError as exc:
            raise ConnectorCampaignLogCaptureError(
                "connector_campaign_log_read_grant_mismatch",
                "Indexed connector grant does not intersect campaign authority.",
            ) from exc
        run_id = compute_parent_arming_id(
            connector_key=entry.connector_key,
            campaign_id=authority.campaign_id,
            grant_sha256=entry.raw_grant_sha256,
            arming_nonce=grant.arming_nonce,
        )
        run_ids[entry.connector_key] = run_id
        bindings[entry.connector_key] = _ExpectedRunBinding(
            connector_key=entry.connector_key,
            connector_run_id=run_id,
            source_system=(
                "nrc_adams"
                if entry.connector_key == "nrc_adams_aps"
                else "sciencebase"
            ),
            grant_sha256=entry.raw_grant_sha256,
            canonical_grant_fingerprint=canonical_fingerprint,
            envelope_core_bytes=_expected_envelope_core(
                campaign=campaign,
                grant=grant,
                raw_grant_sha256=entry.raw_grant_sha256,
                canonical_grant_fingerprint=canonical_fingerprint,
                introduction_index_revision=(
                    authority.introduction_index_revision
                ),
                introduction_index_sha256=authority.introduction_index_sha256,
            ),
        )
        snapshots.append(snapshot)
    if tuple(sorted(run_ids)) != ("nrc_adams_aps", "sciencebase_mcs") or len(
        set(run_ids.values())
    ) != 2:
        _fail(
            "connector_campaign_log_read_grant_set_invalid",
            "Campaign grants do not derive two distinct connector runs.",
        )
    return MappingProxyType(bindings), tuple(snapshots)


def _read_seal_database_snapshot(
    db: Session,
    *,
    authority: _CaptureAuthority,
    seal: ConnectorCampaignLogSealV1,
    seal_sha256: str,
    expected_bindings: Mapping[str, _ExpectedRunBinding],
) -> _ReadOnlyDatabaseSnapshot:
    if db.new or db.dirty or db.deleted:
        _fail(
            "connector_campaign_log_read_session_dirty",
            "Read-only capture verification requires a clean session.",
    )
    expected_ids = seal.connector_run_ids
    arming = ConnectorRun.request_config_json["connector_egress_arming"]
    with db.no_autoflush:
        candidates = list(
            db.scalars(
                select(ConnectorRun)
                .where(
                    ConnectorRun.source_mode == "strict_live_egress",
                    arming["campaign_id"].as_string()
                    == authority.campaign_id,
                    arming["campaign_fingerprint"].as_string()
                    == authority.campaign_fingerprint,
                )
                .order_by(ConnectorRun.connector_run_id)
                .limit(len(expected_ids) + 1)
                .execution_options(populate_existing=True)
            ).all()
        )
    campaign_runs = candidates
    actual_ids = tuple(
        sorted(run.connector_run_id for run in campaign_runs)
    )
    connector_keys = tuple(
        sorted(run.connector_key for run in campaign_runs)
    )
    if actual_ids != expected_ids or connector_keys not in {
        ("nrc_adams_aps",),
        ("nrc_adams_aps", "sciencebase_mcs"),
    }:
        _fail(
            "connector_campaign_log_read_run_set_invalid",
            "Extant campaign runs differ from the exact NRC-only or two-run set.",
        )
    runs_by_id = {run.connector_run_id: run for run in campaign_runs}
    run_rows: list[bytes] = []
    for run in campaign_runs:
        envelope = run.request_config_json.get("connector_egress_arming")
        binding = expected_bindings.get(run.connector_key)
        if (
            binding is None
            or not isinstance(envelope, dict)
            or run.connector_run_id != binding.connector_run_id
            or run.source_mode != "strict_live_egress"
            or run.source_system != binding.source_system
            or run.status not in _TERMINAL_STATUSES
            or run.execution_lease_owner is not None
            or run.execution_lease_token is not None
            or envelope.get("campaign_id") != authority.campaign_id
            or envelope.get("campaign_fingerprint")
            != authority.campaign_fingerprint
            or envelope.get("campaign_definition_sha256")
            != authority.campaign_definition_sha256
            or envelope.get("code_revision") != authority.code_revision
            or envelope.get("campaign_introduction_index_revision")
            != authority.introduction_index_revision
            or envelope.get("campaign_introduction_index_sha256")
            != authority.introduction_index_sha256
        ):
            _fail(
                "connector_campaign_log_read_run_identity_mismatch",
                "Campaign run identity differs from the sealed authority.",
            )
        try:
            _assert_run_envelope(run, binding, authority)
        except (ConnectorEgressArmingError, ConnectorCampaignLogCaptureError) as exc:
            raise ConnectorCampaignLogCaptureError(
                "connector_campaign_log_read_run_identity_mismatch",
                "Campaign run arming does not match indexed grant authority.",
            ) from exc
        run_rows.append(_run_row_snapshot(run))
    expected_event_ids = tuple(
        sorted(
            _event_id(run_id, "campaign_log_capture_sealed")
            for run_id in expected_ids
        )
    )
    with db.no_autoflush:
        candidates_events = list(
            db.scalars(
                select(ConnectorRunEvent)
                .where(
                    ConnectorRunEvent.event_type
                    == "campaign_log_capture_sealed",
                    ConnectorRunEvent.connector_run_id.in_(expected_ids),
                )
                .order_by(
                    ConnectorRunEvent.connector_run_id,
                    ConnectorRunEvent.created_at,
                    ConnectorRunEvent.connector_run_event_id,
                )
                .limit(len(expected_ids) + 1)
                .execution_options(populate_existing=True)
            ).all()
        )
    events = candidates_events
    metrics = _seal_event_metrics(
        authority=authority,
        seal=seal,
        seal_relative_path=authority.seal_relative_path,
        seal_sha256=seal_sha256,
    )
    event_rows: list[bytes] = []
    for event in events:
        event_run = runs_by_id.get(event.connector_run_id)
        if (
            event_run is None
            or event.connector_run_event_id
            != _event_id(
                event_run.connector_run_id,
                "campaign_log_capture_sealed",
            )
            or event.connector_run_target_id is not None
            or event.phase != "evidence"
            or event.stage != "campaign_log_capture"
            or event.event_type != "campaign_log_capture_sealed"
            or event.status_before != event_run.status
            or event.status_after != event_run.status
            or event.reason_code != "protected_log_capture_sealed"
            or event.error_class is not None
            or event.message is not None
            or event.metrics_json != metrics
            or _db_utc(event.created_at) != seal.sealed_at
        ):
            _fail(
                "connector_campaign_log_read_seal_event_mismatch",
                "Campaign seal event differs from the sealed filesystem evidence.",
            )
        event_rows.append(_event_snapshot(event))
    actual_event_ids = tuple(
        sorted(event.connector_run_event_id for event in events)
    )
    if actual_event_ids != expected_event_ids:
        _fail(
            "connector_campaign_log_read_seal_event_set_invalid",
            "Campaign seal events are missing, duplicated, or unexpected.",
        )
    if db.new or db.dirty or db.deleted:
        _fail(
            "connector_campaign_log_read_session_dirty",
            "Read-only capture verification changed the supplied session.",
        )
    return _ReadOnlyDatabaseSnapshot(
        run_rows=tuple(run_rows),
        event_rows=tuple(event_rows),
        event_ids=actual_event_ids,
    )


def _verify_connector_campaign_log_capture_in_owned_transaction(
    db: Session,
    chain: VerifiedEvidenceIndexChain,
    campaign_id: str,
    expected_campaign_fingerprint: str,
) -> VerifiedCampaignLogCapture:
    root = _verify_index_chain_snapshot(chain)
    try:
        normalized_campaign_id = _canonical_campaign_id(campaign_id)
        campaign_fingerprint = _normalized_sha256(
            expected_campaign_fingerprint,
            label="expected campaign fingerprint",
        )
        definition_ref, entries, capture_ref = _find_campaign_refs(
            chain,
            campaign_id=normalized_campaign_id,
            campaign_fingerprint=campaign_fingerprint,
        )
        introduction = _introduction_revision(
            chain,
            campaign_id=normalized_campaign_id,
            campaign_fingerprint=campaign_fingerprint,
        )
        log_dir_relative_path, manifest_relative_path, seal_relative_path = (
            _validate_log_capture_paths(capture_ref)
        )
    except ConnectorEgressAuthorizationError as exc:
        raise ConnectorCampaignLogCaptureError(
            "connector_campaign_log_read_authority_invalid",
            "Campaign log capture authority is invalid.",
        ) from exc
    if (
        capture_ref.campaign_definition_sha256
        != definition_ref.raw_definition_sha256
        or capture_ref.code_revision != definition_ref.code_revision
    ):
        _fail(
            "connector_campaign_log_read_authority_mismatch",
            "Campaign log reference differs from its definition reference.",
        )
    campaign_dir, manifest_path, seal_path = _read_only_capture_paths(
        root,
        campaign_fingerprint=campaign_fingerprint,
    )
    if (
        campaign_dir.relative_to(root).as_posix() != log_dir_relative_path
        or manifest_path.relative_to(root).as_posix()
        != manifest_relative_path
        or seal_path.relative_to(root).as_posix() != seal_relative_path
    ):
        _fail(
            "connector_campaign_log_read_path_mismatch",
            "Campaign log paths differ from the evidence index.",
        )
    manifest_object = _read_stable_capture_bytes(
        root,
        manifest_relative_path,
        max_bytes=MAX_PROTECTED_JSON_BYTES,
    )
    seal_object = _read_stable_capture_bytes(
        root,
        seal_relative_path,
        max_bytes=MAX_PROTECTED_JSON_BYTES,
    )
    manifest = _parse_canonical_capture_model(
        manifest_object,
        ConnectorCampaignLogManifestV1,
        label="campaign log manifest",
    )
    seal = _parse_canonical_capture_model(
        seal_object,
        ConnectorCampaignLogSealV1,
        label="campaign log seal",
    )
    identity = (
        normalized_campaign_id,
        campaign_fingerprint,
        definition_ref.raw_definition_sha256,
        definition_ref.code_revision,
    )
    if (
        (
            manifest.campaign_id,
            manifest.campaign_fingerprint,
            manifest.campaign_definition_sha256,
            manifest.code_revision,
        )
        != identity
        or (
            seal.campaign_id,
            seal.campaign_fingerprint,
            seal.campaign_definition_sha256,
            seal.code_revision,
        )
        != identity
        or seal.campaign_introduction_index_revision
        != introduction.model.revision
        or seal.campaign_introduction_index_sha256
        != introduction.raw_sha256
        or seal.manifest_relative_path != manifest_relative_path
        or seal.sealed_at < manifest.runtime_stopped_at
    ):
        _fail(
            "connector_campaign_log_read_identity_mismatch",
            "Manifest, seal, and evidence-index identity do not match.",
        )
    manifest_sha256 = manifest_object.sha256
    seal_sha256 = seal_object.sha256
    file_set_hash = hashlib.sha256(
        canonical_json_bytes(
            {
                "schema_id": "project6.connector_campaign_log_file_set.v1",
                "files": [
                    item.model_dump(mode="python")
                    for item in manifest.files
                ],
            }
        )
    ).hexdigest()
    if (
        seal.manifest_sha256 != manifest_sha256
        or seal.file_set_hash != file_set_hash
    ):
        _fail(
            "connector_campaign_log_read_seal_mismatch",
            "Campaign log seal does not bind the rederived manifest and file set.",
        )
    first_files, stream_bytes = _read_capture_file_set(
        root,
        manifest,
        manifest_relative_path=manifest_relative_path,
        seal_relative_path=seal_relative_path,
    )
    if first_files[-2] != manifest_object or first_files[-1] != seal_object:
        _fail(
            "connector_campaign_log_read_snapshot_changed",
            "Manifest or seal changed during capture verification.",
        )
    authority = _CaptureAuthority(
        campaign_id=normalized_campaign_id,
        campaign_fingerprint=campaign_fingerprint,
        campaign_definition_sha256=definition_ref.raw_definition_sha256,
        code_revision=definition_ref.code_revision,
        runtime_started_at=manifest.runtime_started_at,
        introduction_index_revision=introduction.model.revision,
        introduction_index_sha256=introduction.raw_sha256,
        evidence_root=root,
        log_dir_relative_path=log_dir_relative_path,
        manifest_relative_path=manifest_relative_path,
        seal_relative_path=seal_relative_path,
        run_bindings=(),
    )
    expected_bindings, first_grants = _derive_expected_run_ids(
        root,
        definition_ref,
        entries,
        authority=authority,
    )
    authority = replace(
        authority,
        run_bindings=tuple(
            expected_bindings[key] for key in sorted(expected_bindings)
        ),
    )
    first_database = _read_seal_database_snapshot(
        db,
        authority=authority,
        seal=seal,
        seal_sha256=seal_sha256,
        expected_bindings=expected_bindings,
    )
    _read_only_capture_paths(
        root,
        campaign_fingerprint=campaign_fingerprint,
    )
    second_files, _ = _read_capture_file_set(
        root,
        manifest,
        manifest_relative_path=manifest_relative_path,
        seal_relative_path=seal_relative_path,
    )
    second_bindings, second_grants = _derive_expected_run_ids(
        root,
        definition_ref,
        entries,
        authority=authority,
    )
    second_database = _read_seal_database_snapshot(
        db,
        authority=authority,
        seal=seal,
        seal_sha256=seal_sha256,
        expected_bindings=second_bindings,
    )
    final_root = _verify_index_chain_snapshot(chain)
    final_campaign_dir, final_manifest_path, final_seal_path = (
        _read_only_capture_paths(
            root,
            campaign_fingerprint=campaign_fingerprint,
        )
    )
    if (
        second_files != first_files
        or second_grants != first_grants
        or dict(second_bindings) != dict(expected_bindings)
        or second_database != first_database
        or final_root != root
        or final_campaign_dir != campaign_dir
        or final_manifest_path != manifest_path
        or final_seal_path != seal_path
    ):
        _fail(
            "connector_campaign_log_read_snapshot_changed",
            "Campaign log filesystem or database evidence changed during verification.",
        )
    stable_snapshot = tuple(
        (item.relative_path, item.size, item.sha256)
        for item in first_files
    )
    return VerifiedCampaignLogCapture(
        manifest_bytes=manifest_object.data,
        manifest_sha256=manifest_sha256,
        file_set_hash=file_set_hash,
        seal_bytes=seal_object.data,
        seal_sha256=seal_sha256,
        stream_bytes=stream_bytes,
        seal_event_ids=first_database.event_ids,
        stable_snapshot=stable_snapshot,
    )


def verify_connector_campaign_log_capture_read_only(
    db: Session,
    chain: VerifiedEvidenceIndexChain,
    campaign_id: str,
    expected_campaign_fingerprint: str,
) -> VerifiedCampaignLogCapture:
    """Verify under caller-held campaign ProofLocks mutex.

    This adapter does not provide terminal/preseal continuity or cross-store
    atomicity; the outer evaluator/gate owns those controls through emission.
    """
    if not isinstance(db, Session):
        _fail(
            "connector_campaign_log_read_session_invalid",
            "Capture verification requires an explicit database session.",
        )
    if db.in_transaction():
        _fail(
            "connector_campaign_log_read_transaction_active",
            "Capture verification refuses a caller-active transaction.",
        )
    if db.new or db.dirty or db.deleted:
        _fail(
            "connector_campaign_log_read_session_dirty",
            "Capture verification refuses a dirty caller session.",
        )
    bind = db.get_bind()
    if isinstance(bind, Connection) and bind.in_transaction():
        _fail(
            "connector_campaign_log_read_transaction_active",
            "Capture verification refuses an externally active bind transaction.",
        )
    verification_db = Session(
        bind=bind,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    try:
        transaction = verification_db.begin()
        try:
            return _verify_connector_campaign_log_capture_in_owned_transaction(
                verification_db,
                chain,
                campaign_id,
                expected_campaign_fingerprint,
            )
        finally:
            if transaction.is_active:
                transaction.rollback()
    finally:
        verification_db.close()
