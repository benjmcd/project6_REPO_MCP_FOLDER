"""Strict downstream linkage for one admitted NRC APS raw target."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
import json
import math
import os
from pathlib import Path
import re
from typing import Any, Mapping, NoReturn
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.engine import Connection, Engine, RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import Settings, settings
from app.models import (
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunEvent,
    ConnectorRunTarget,
)
from app.services import connector_egress_arming
from app.services import connectors_nrc_adams
from app.services import layer3_origin_continuity
from app.services import nrc_aps_artifact_ingestion
from app.services import nrc_aps_content_index
from app.services import nrc_phase_b_custody
from app.services import nrc_aps_strict_parse
from app.services.raw_storage_handles import (
    StableRawStorageError,
    hash_locked_raw_file,
    locked_raw_file_snapshot,
)


_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_ACCESSION = connectors_nrc_adams.NRC_FRESH_ACCESSION
_ORIGIN_RECEIPT_KEY = (
    layer3_origin_continuity.ORIGIN_RECEIPT_STORAGE_KEY
)
_CUSTODY_KEY = nrc_phase_b_custody.CUSTODY_STORAGE_KEY
_ADMISSION_KEYS = frozenset(
    {
        "schema_id",
        "accession_number",
        "artifact_file_name",
        "detail_response_sha256",
        "artifact_url_sha256",
        "artifact_path_class",
        "raw_content_sha256",
        "raw_content_size_bytes",
        "media_type",
        "blob_storage_layout",
    }
)
_RowSnapshot = tuple[tuple[str, Any], ...]
_EventSnapshot = tuple[_RowSnapshot, ...]
_RowSetSnapshot = tuple[_RowSnapshot, ...]
_NRC_PHASE_B_EVENT_CAP = 7
_NRC_CAMPAIGN_SEAL_EVENT_CAP = 1
_NRC_CAMPAIGN_SEAL_EVENT_TYPE = "campaign_log_capture_sealed"
_ADMISSION_KEY_SETS = frozenset(
    {
        _ADMISSION_KEYS,
        _ADMISSION_KEYS | {_ORIGIN_RECEIPT_KEY},
        _ADMISSION_KEYS | {_CUSTODY_KEY},
        _ADMISSION_KEYS | {_ORIGIN_RECEIPT_KEY, _CUSTODY_KEY},
    }
)


@dataclass(frozen=True, slots=True)
class NrcPhaseBVerifiedState:
    connector_run_id: str
    connector_run_target_id: str
    aps_content_linkage_id: str
    content_id: str
    raw_storage_ref: str
    raw_content_sha256: str
    raw_content_size_bytes: int


@dataclass(frozen=True, slots=True)
class _CoreSnapshotRow:
    values: dict[str, Any]
    snapshot: _RowSnapshot


@dataclass(frozen=True, slots=True)
class _VerifierAuthorityRead:
    runs: tuple[_CoreSnapshotRow, ...]
    targets: tuple[_CoreSnapshotRow, ...]
    run_targets: tuple[_CoreSnapshotRow, ...]
    events: tuple[_CoreSnapshotRow, ...]

    @property
    def fingerprint(self) -> tuple[_RowSetSnapshot, ...]:
        return tuple(
            tuple(row.snapshot for row in rows)
            for rows in (
                self.runs,
                self.targets,
                self.run_targets,
                self.events,
            )
        )


@dataclass(frozen=True, slots=True)
class _VerifierProjectionRead:
    linkages: tuple[_CoreSnapshotRow, ...]
    documents: tuple[_CoreSnapshotRow, ...]
    chunks: tuple[_CoreSnapshotRow, ...]

    @property
    def fingerprint(self) -> tuple[_RowSetSnapshot, ...]:
        return tuple(
            tuple(row.snapshot for row in rows)
            for rows in (self.linkages, self.documents, self.chunks)
        )


class NrcPhaseBLinkageError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> NoReturn:
    raise NrcPhaseBLinkageError(code, message)


def _text(value: object) -> str:
    return str(value or "").strip()


def _sha256(value: object, *, field: str) -> str:
    digest = _text(value)
    if not _SHA256_RE.fullmatch(digest):
        _fail(
            "nrc_phase_b_admission_invalid",
            f"{field} is not a lowercase SHA-256.",
        )
    return digest


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _same_lexical_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.normpath(str(left))) == os.path.normcase(
        os.path.normpath(str(right))
    )


def _contains_url(value: object) -> bool:
    if isinstance(value, str):
        normalized = value.strip().lower()
        return (
            normalized.startswith("http://")
            or normalized.startswith("https://")
            or normalized.startswith("//")
        )
    if isinstance(value, Mapping):
        return any(_contains_url(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_url(item) for item in value)
    return False


def _canonical_snapshot_value(value: object) -> tuple[str, Any]:
    if value is None:
        return ("none", None)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, float):
        if not math.isfinite(value):
            _fail(
                "nrc_phase_b_snapshot_invalid",
                "Authority snapshot contains a non-finite float.",
            )
        return ("float", value.hex())
    if isinstance(value, str):
        return ("str", value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return ("bytes", bytes(value).hex())
    if isinstance(value, datetime):
        normalized = value
        if value.tzinfo is not None:
            normalized = value.astimezone(timezone.utc).replace(tzinfo=None)
        return ("datetime", normalized.isoformat(timespec="microseconds"))
    if isinstance(value, date):
        return ("date", value.isoformat())
    if isinstance(value, time):
        return ("time", value.isoformat(timespec="microseconds"))
    if isinstance(value, Decimal):
        return ("decimal", str(value.normalize()))
    if isinstance(value, UUID):
        return ("uuid", str(value))
    if isinstance(value, (Mapping, list, tuple)):
        try:
            canonical_json = json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise NrcPhaseBLinkageError(
                "nrc_phase_b_snapshot_invalid",
                "Authority JSON cannot be canonicalized.",
            ) from exc
        return ("json", canonical_json)
    _fail(
        "nrc_phase_b_snapshot_invalid",
        f"Unsupported authority value type: {type(value).__name__}.",
    )


def _mapped_snapshot(row: object) -> _RowSnapshot:
    table = getattr(row, "__table__", None)
    if table is None:
        _fail(
            "nrc_phase_b_snapshot_invalid",
            "Authority row has no mapped table.",
        )
    return tuple(
        (
            column.key,
            _canonical_snapshot_value(getattr(row, column.key)),
        )
        for column in sorted(table.columns, key=lambda item: item.key)
    )


def _core_snapshot_row(
    table: Any,
    row: RowMapping,
) -> _CoreSnapshotRow:
    values = {
        column.key: deepcopy(row[column.key])
        for column in table.columns
    }
    return _CoreSnapshotRow(
        values=values,
        snapshot=tuple(
            (
                column.key,
                _canonical_snapshot_value(values[column.key]),
            )
            for column in sorted(
                table.columns,
                key=lambda item: item.key,
            )
        ),
    )


def _read_bounded_core_rows(
    connection: Connection,
    table: Any,
    *,
    criterion: Any,
    max_rows: int,
) -> tuple[_CoreSnapshotRow, ...]:
    statement = (
        select(table)
        .where(criterion)
        .order_by(*tuple(table.primary_key.columns))
        .limit(max_rows + 1)
    )
    return tuple(
        _core_snapshot_row(table, row)
        for row in connection.execute(statement).mappings().all()
    )


def _materialize_core_row(
    row: _CoreSnapshotRow,
    model: type[Any],
) -> Any:
    return model(**deepcopy(row.values))


def _read_verifier_authority(
    connection: Connection,
    *,
    target_id: str,
    expected_run_id: str | None = None,
) -> _VerifierAuthorityRead:
    target_table = ConnectorRunTarget.__table__
    run_table = ConnectorRun.__table__
    event_table = ConnectorRunEvent.__table__
    targets = _read_bounded_core_rows(
        connection,
        target_table,
        criterion=(
            target_table.c.connector_run_target_id == target_id
        ),
        max_rows=1,
    )
    run_id = expected_run_id
    if targets and run_id is None:
        candidate = targets[0].values.get("connector_run_id")
        if isinstance(candidate, str):
            run_id = candidate
    bounded_run_id = run_id or ""
    runs = _read_bounded_core_rows(
        connection,
        run_table,
        criterion=run_table.c.connector_run_id == bounded_run_id,
        max_rows=1,
    )
    run_targets = _read_bounded_core_rows(
        connection,
        target_table,
        criterion=target_table.c.connector_run_id == bounded_run_id,
        max_rows=1,
    )
    phase_events = _read_bounded_core_rows(
        connection,
        event_table,
        criterion=(
            (event_table.c.connector_run_id == bounded_run_id)
            & or_(
                event_table.c.event_type
                != _NRC_CAMPAIGN_SEAL_EVENT_TYPE,
                event_table.c.event_type.is_(None),
            )
        ),
        max_rows=_NRC_PHASE_B_EVENT_CAP,
    )
    seal_events = _read_bounded_core_rows(
        connection,
        event_table,
        criterion=(
            (event_table.c.connector_run_id == bounded_run_id)
            & (
                event_table.c.event_type
                == _NRC_CAMPAIGN_SEAL_EVENT_TYPE
            )
        ),
        max_rows=_NRC_CAMPAIGN_SEAL_EVENT_CAP,
    )
    events = tuple(
        sorted(
            (*phase_events, *seal_events),
            key=lambda row: str(
                row.values.get("connector_run_event_id", "")
            ),
        )
    )
    return _VerifierAuthorityRead(
        runs=runs,
        targets=targets,
        run_targets=run_targets,
        events=events,
    )


def _read_verifier_projection(
    connection: Connection,
    *,
    payload: Mapping[str, Any],
) -> _VerifierProjectionRead:
    chunk_count = payload.get("chunk_count")
    chunks = payload.get("chunks")
    if (
        isinstance(chunk_count, bool)
        or not isinstance(chunk_count, int)
        or chunk_count < 0
        or not isinstance(chunks, list)
        or len(chunks) != chunk_count
    ):
        _fail(
            "nrc_phase_b_parse_projection_invalid",
            "Strict projection has no bounded complete chunk set.",
        )
    linkage_table = ApsContentLinkage.__table__
    document_table = ApsContentDocument.__table__
    chunk_table = ApsContentChunk.__table__
    return _VerifierProjectionRead(
        linkages=_read_bounded_core_rows(
            connection,
            linkage_table,
            criterion=(
                linkage_table.c.target_id == payload["target_id"]
            ),
            max_rows=1,
        ),
        documents=_read_bounded_core_rows(
            connection,
            document_table,
            criterion=(
                document_table.c.content_id == payload["content_id"]
            ),
            max_rows=1,
        ),
        chunks=_read_bounded_core_rows(
            connection,
            chunk_table,
            criterion=chunk_table.c.content_id == payload["content_id"],
            max_rows=chunk_count,
        ),
    )


def _reject_phase_b_identity_map_state(db: Session) -> None:
    authority_types = (
        ConnectorRun,
        ConnectorRunTarget,
        ConnectorRunEvent,
        ApsContentDocument,
        ApsContentChunk,
        ApsContentLinkage,
    )
    if any(
        isinstance(item, authority_types)
        for collection in (db.new, db.deleted)
        for item in collection
    ) or any(
        isinstance(item, authority_types)
        and db.is_modified(item, include_collections=True)
        for item in db.dirty
    ):
        _fail(
            "nrc_phase_b_identity_map_dirty",
            "Phase B authority has pending identity-map changes.",
        )


def _committed_visibility_unavailable(
    cause: Exception | None = None,
) -> NoReturn:
    error = NrcPhaseBLinkageError(
        "nrc_phase_b_committed_visibility_unavailable",
        "Independent committed Phase B visibility is unavailable.",
    )
    if cause is not None:
        raise error from cause
    raise error


def _independent_committed_engine(db: Session) -> Engine:
    try:
        bind = db.get_bind()
    except SQLAlchemyError as exc:
        _committed_visibility_unavailable(exc)
    engine = bind.engine if isinstance(bind, Connection) else bind
    if not isinstance(engine, Engine) or not isinstance(
        engine.pool,
        (QueuePool, NullPool),
    ):
        _committed_visibility_unavailable()
    if engine.dialect.name == "sqlite":
        database = _text(engine.url.database).lower()
        mode = _text(engine.url.query.get("mode")).lower()
        if not database or ":memory:" in database or mode == "memory":
            _committed_visibility_unavailable()
    return engine


def _require_owned_clean_transaction(db: Session) -> None:
    if (
        db.in_transaction()
        or db.in_nested_transaction()
        or db.new
        or db.dirty
        or db.deleted
    ):
        _fail(
            "nrc_phase_b_transaction_not_owned",
            "Phase B requires a clean Session with no active transaction.",
        )


def _event_snapshot(
    events: list[ConnectorRunEvent],
) -> _EventSnapshot:
    return tuple(
        _mapped_snapshot(event)
        for event in sorted(
            events,
            key=lambda item: item.connector_run_event_id,
        )
    )


def _validate_run_shape(run: ConnectorRun) -> None:
    if (
        run.connector_key != "nrc_adams_aps"
        or run.source_system != "nrc_adams"
        or run.source_mode != "strict_live_egress"
        or run.status != "completed"
        or not connector_egress_arming.is_strict_egress_run(run)
        or run.discovered_count != 1
        or run.selected_count != 1
        or run.downloaded_count != 1
        or run.ingested_count != 0
        or run.failed_count != 0
        or run.terminal_target_count != 1
        or run.nonterminal_target_count != 0
        or run.consumed_bytes <= 0
    ):
        _fail(
            "nrc_phase_b_run_invalid",
            "Target parent is not one completed strict NRC raw-only run.",
        )


def _validate_run_events(
    run: ConnectorRun,
    events: list[ConnectorRunEvent],
) -> None:
    try:
        connector_egress_arming._assert_nrc_terminal_transition(
            run,
            events=events,
            now=datetime.now(timezone.utc),
        )
    except connector_egress_arming.ConnectorEgressArmingError as exc:
        raise NrcPhaseBLinkageError(
            "nrc_phase_b_run_invalid",
            "Strict NRC terminal transition is not structurally valid.",
        ) from exc


def _validate_run(
    db: Session,
    run: ConnectorRun,
    *,
    expected_event_snapshot: _EventSnapshot | None = None,
    lock_events: bool = False,
) -> _EventSnapshot:
    _validate_run_shape(run)
    event_query = db.query(ConnectorRunEvent).filter(
        ConnectorRunEvent.connector_run_id == run.connector_run_id
    ).populate_existing()
    if lock_events:
        event_query = event_query.with_for_update()
    events = event_query.all()
    current_event_snapshot = _event_snapshot(events)
    if (
        expected_event_snapshot is not None
        and current_event_snapshot != expected_event_snapshot
    ):
        _fail(
            "nrc_phase_b_row_drift",
            "Run event authority changed during strict parsing.",
        )
    _validate_run_events(run, events)
    return current_event_snapshot


def _validate_target(
    target: ConnectorRunTarget,
    *,
    run: ConnectorRun,
) -> tuple[str, int]:
    if (
        target.connector_run_id != run.connector_run_id
        or target.ordinal != 1
        or target.stable_release_key != _ACCESSION
        or target.stable_release_identifier
        != f"adams_accession:{_ACCESSION}"
        or target.identifiers_json
        != [{"type": "AccessionNumber", "value": _ACCESSION}]
        or target.sciencebase_item_id is not None
        or target.sciencebase_file_name
        != connectors_nrc_adams.NRC_FRESH_FILENAME
        or target.artifact_surface != "files"
        or target.selection_source != "strict_exact_accession"
        or target.selection_scope != "dual_live_proof_v1"
        or target.selection_match_basis != "exact_accession"
        or target.artifact_locator_type
        != connectors_nrc_adams.NRC_FRESH_ARTIFACT_PATH_CLASS
        or target.source_artifact_key
        != f"nrc_adams_aps::{_ACCESSION}"
        or target.canonical_artifact_key
        != f"nrc_adams_aps::{_ACCESSION}"
        or target.fetch_policy_mode != "strict_live_egress"
        or target.redirect_count != 0
        or target.aliases_json != []
        or target.permission_snapshot_json
        != {"direct_public_200": True}
        or target.access_level_summary != "public_direct_200"
        or target.public_read_confirmed is not True
        or target.status != "downloaded"
        or target.retry_eligible is not False
        or target.attempt_count != 1
        or target.ingested_at is not None
        or target.profiled_at is not None
        or target.recommended_at is not None
    ):
        _fail(
            "nrc_phase_b_target_invalid",
            "Run target is not the canonical ordinal-1 NRC raw target.",
        )
    if (
        target.sciencebase_item_url is not None
        or target.sciencebase_download_uri is not None
        or _contains_url(target.aliases_json)
    ):
        _fail(
            "nrc_phase_b_url_authority_refused",
            "URL-bearing target authority is forbidden in Phase B.",
        )

    admission = target.source_reference_json
    if (
        not isinstance(admission, Mapping)
        or frozenset(admission) not in _ADMISSION_KEY_SETS
        or admission.get("schema_id")
        != "project6.nrc_raw_admission.v1"
        or admission.get("accession_number") != _ACCESSION
        or admission.get("artifact_file_name")
        != connectors_nrc_adams.NRC_FRESH_FILENAME
        or admission.get("artifact_path_class")
        != connectors_nrc_adams.NRC_FRESH_ARTIFACT_PATH_CLASS
        or admission.get("media_type")
        not in connectors_nrc_adams.NRC_FRESH_MEDIA_TYPES
        or admission.get("blob_storage_layout")
        != "nrc_aps_blob_sha256_v1"
        or _contains_url(admission)
    ):
        _fail(
            "nrc_phase_b_admission_invalid",
            "Target lacks exact URL-free NRC raw admission metadata.",
        )
    receipt = admission.get(_ORIGIN_RECEIPT_KEY)
    if _ORIGIN_RECEIPT_KEY in admission:
        if (
            not isinstance(receipt, Mapping)
            or receipt.get("schema_id")
            != layer3_origin_continuity.ORIGIN_RECEIPT_SCHEMA_ID
            or receipt.get("connector_key") != run.connector_key
            or receipt.get("connector_run_id")
            != run.connector_run_id
            or receipt.get("connector_run_target_id")
            != target.connector_run_target_id
        ):
            _fail(
                "nrc_phase_b_admission_invalid",
                "Optional connector-origin receipt envelope is invalid.",
            )
        _sha256(
            receipt.get("receipt_hash"),
            field="connector_origin_receipt_v1.receipt_hash",
        )
    _sha256(
        admission.get("detail_response_sha256"),
        field="detail_response_sha256",
    )
    _sha256(
        admission.get("artifact_url_sha256"),
        field="artifact_url_sha256",
    )
    raw_sha256 = _sha256(
        admission.get("raw_content_sha256"),
        field="raw_content_sha256",
    )
    target_sha256 = _sha256(
        target.downloaded_sha256,
        field="ConnectorRunTarget.downloaded_sha256",
    )
    raw_size = admission.get("raw_content_size_bytes")
    if (
        isinstance(raw_size, bool)
        or not isinstance(raw_size, int)
        or raw_size <= 0
        or raw_size > connectors_nrc_adams.NRC_FRESH_MAX_PDF_BYTES
        or raw_size != run.consumed_bytes
        or raw_sha256 != target_sha256
        or not _text(target.raw_storage_ref)
    ):
        _fail(
            "nrc_phase_b_admission_invalid",
            "Raw admission size, hash, or storage binding is invalid.",
        )
    return raw_sha256, raw_size


def _safe_rehash(
    target: ConnectorRunTarget,
    *,
    expected_sha256: str,
    expected_size: int,
    drift_phase: bool,
    raw_root: Path | None = None,
) -> Path:
    raw_root = _lexical_absolute(
        Path(settings.connector_raw_dir) if raw_root is None else raw_root
    )
    expected_path = _lexical_absolute(
        raw_root
        / nrc_aps_artifact_ingestion.blob_relative_path(
            sha256=expected_sha256
        )
    )
    raw_ref = target.raw_storage_ref
    if (
        not isinstance(raw_ref, str)
        or not raw_ref
        or raw_ref != raw_ref.strip()
    ):
        _fail(
            "nrc_phase_b_raw_path_invalid",
            "Raw storage ref is not one canonical absolute string.",
        )
    target_path = _lexical_absolute(Path(raw_ref))
    if not _same_lexical_path(target_path, expected_path):
        _fail(
            "nrc_phase_b_raw_path_invalid",
            "Raw storage ref is not the exact content-addressed path.",
        )
    try:
        size, digest, resolved_ref = hash_locked_raw_file(
            raw_root,
            expected_path,
        )
    except StableRawStorageError as exc:
        code = (
            "nrc_phase_b_raw_drift"
            if drift_phase
            else "nrc_phase_b_raw_storage_unsafe"
        )
        raise NrcPhaseBLinkageError(
            code,
            "Handle-safe raw storage validation failed closed.",
        ) from exc
    resolved_path = _lexical_absolute(Path(resolved_ref))
    if (
        not _same_lexical_path(resolved_path, expected_path)
        or raw_ref != resolved_ref
        or size != expected_size
        or digest != expected_sha256
    ):
        if raw_ref != resolved_ref:
            _fail(
                "nrc_phase_b_raw_path_invalid",
                "Raw storage ref is not the canonical locked reference.",
            )
        code = (
            "nrc_phase_b_raw_drift"
            if drift_phase
            else "nrc_phase_b_raw_binding_mismatch"
        )
        _fail(code, "Rehashed raw bytes contradict admission authority.")
    return resolved_path


def _run_snapshot(run: ConnectorRun) -> _RowSnapshot:
    return _mapped_snapshot(run)


def _target_snapshot(target: ConnectorRunTarget) -> _RowSnapshot:
    return _mapped_snapshot(target)


def _visual_refs(raw: str | None) -> list[dict[str, Any]] | None:
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, list) or any(
        not isinstance(item, dict) for item in parsed
    ):
        return None
    return [dict(item) for item in parsed]


def _document_matches(
    document: ApsContentDocument,
    payload: Mapping[str, Any],
) -> bool:
    return bool(
        document.content_id == payload["content_id"]
        and document.content_contract_id
        == payload["content_contract_id"]
        and document.chunking_contract_id
        == payload["chunking_contract_id"]
        and document.normalization_contract_id
        == payload["normalization_contract_id"]
        and document.normalized_text_sha256
        == payload["normalized_text_sha256"]
        and document.normalized_char_count
        == payload["normalized_char_count"]
        and document.chunk_count == payload["chunk_count"]
        and document.content_status == payload["content_status"]
        and document.media_type == payload["effective_content_type"]
        and document.document_class == payload["document_class"]
        and document.quality_status == payload["quality_status"]
        and document.page_count == payload["page_count"]
        and document.diagnostics_ref is None
        and _visual_refs(document.visual_page_refs_json) == []
    )


def _chunks_match(
    rows: list[ApsContentChunk],
    payload: Mapping[str, Any],
) -> bool:
    expected_rows = payload.get("chunks")
    if not isinstance(expected_rows, list) or len(rows) != len(expected_rows):
        return False
    by_id = {row.chunk_id: row for row in rows}
    if len(by_id) != len(rows):
        return False
    for raw_expected in expected_rows:
        if not isinstance(raw_expected, Mapping):
            return False
        expected = dict(raw_expected)
        chunk_id = expected.get("chunk_id")
        if not isinstance(chunk_id, str):
            return False
        row = by_id.get(chunk_id)
        if row is None or not (
            row.content_id == payload["content_id"]
            and row.content_contract_id
            == payload["content_contract_id"]
            and row.chunking_contract_id
            == payload["chunking_contract_id"]
            and row.chunk_ordinal == expected.get("chunk_ordinal")
            and row.start_char == expected.get("start_char")
            and row.end_char == expected.get("end_char")
            and row.chunk_text == expected.get("chunk_text")
            and row.chunk_text_sha256
            == expected.get("chunk_text_sha256")
            and row.page_start == expected.get("page_start")
            and row.page_end == expected.get("page_end")
            and row.unit_kind == expected.get("unit_kind")
            and row.quality_status == payload["quality_status"]
        ):
            return False
    return True


def _linkage_matches(
    linkage: ApsContentLinkage,
    payload: Mapping[str, Any],
) -> bool:
    return bool(
        linkage.content_id == payload["content_id"]
        and linkage.run_id == payload["run_id"]
        and linkage.target_id == payload["target_id"]
        and linkage.accession_number == payload["accession_number"]
        and linkage.content_contract_id
        == payload["content_contract_id"]
        and linkage.chunking_contract_id
        == payload["chunking_contract_id"]
        and linkage.content_units_ref is None
        and linkage.normalized_text_ref is None
        and linkage.normalized_text_sha256
        == payload["normalized_text_sha256"]
        and linkage.blob_ref == payload["blob_ref"]
        and linkage.blob_sha256 == payload["blob_sha256"]
        and linkage.download_exchange_ref is None
        and linkage.discovery_ref is None
        and linkage.selection_ref is None
        and linkage.diagnostics_ref is None
    )


def _content_projection(
    db: Session,
    payload: Mapping[str, Any],
) -> tuple[list[ApsContentDocument], list[ApsContentChunk]]:
    documents = (
        db.query(ApsContentDocument)
        .filter(
            ApsContentDocument.content_id == payload["content_id"]
        )
        .populate_existing()
        .with_for_update()
        .all()
    )
    chunks = (
        db.query(ApsContentChunk)
        .filter(ApsContentChunk.content_id == payload["content_id"])
        .populate_existing()
        .with_for_update()
        .all()
    )
    return documents, chunks


def _preflight(
    db: Session,
    *,
    payload: Mapping[str, Any],
) -> tuple[str, ApsContentLinkage | None]:
    linkages = (
        db.query(ApsContentLinkage)
        .filter(
            ApsContentLinkage.run_id == payload["run_id"],
            ApsContentLinkage.target_id == payload["target_id"],
        )
        .populate_existing()
        .with_for_update()
        .all()
    )
    if len(linkages) > 1:
        _fail(
            "nrc_phase_b_linkage_cardinality",
            "Run-target pair already has more than one linkage.",
        )
    documents, chunks = _content_projection(db, payload)
    if len(linkages) == 1:
        linkage = linkages[0]
        if not _linkage_matches(linkage, payload):
            _fail(
                "nrc_phase_b_linkage_mismatch",
                "Existing run-target linkage is not exact.",
            )
        if (
            len(documents) != 1
            or not _document_matches(documents[0], payload)
            or not _chunks_match(chunks, payload)
        ):
            _fail(
                "nrc_phase_b_linkage_mismatch",
                "Existing linkage document/chunk projection is not exact.",
            )
        return "existing", linkage

    if not documents and not chunks:
        return "immutable_insert", None
    if (
        len(documents) == 1
        and _document_matches(documents[0], payload)
        and _chunks_match(chunks, payload)
    ):
        return "linkage_only", None
    _fail(
        "nrc_phase_b_shared_content_mismatch",
        "Shared content state is not the exact strict projection.",
    )


def _require_exact_persisted(
    db: Session,
    *,
    payload: Mapping[str, Any],
) -> ApsContentLinkage:
    linkages = (
        db.query(ApsContentLinkage)
        .filter(
            ApsContentLinkage.run_id == payload["run_id"],
            ApsContentLinkage.target_id == payload["target_id"],
        )
        .populate_existing()
        .with_for_update()
        .all()
    )
    documents, chunks = _content_projection(db, payload)
    if (
        len(linkages) != 1
        or not _linkage_matches(linkages[0], payload)
        or len(documents) != 1
        or not _document_matches(documents[0], payload)
        or not _chunks_match(chunks, payload)
    ):
        _fail(
            "nrc_phase_b_persistence_conflict",
            "Committed or concurrent persistence is not exact.",
        )
    return linkages[0]


def _reload_authority(
    db: Session,
    *,
    run_id: str,
    target_id: str,
    run_snapshot: _RowSnapshot,
    target_snapshot: _RowSnapshot,
    event_snapshot: _EventSnapshot,
) -> tuple[ConnectorRun, ConnectorRunTarget]:
    run = (
        db.query(ConnectorRun)
        .filter(ConnectorRun.connector_run_id == run_id)
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    target = (
        db.query(ConnectorRunTarget)
        .filter(
            ConnectorRunTarget.connector_run_target_id == target_id
        )
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    if (
        run is None
        or target is None
        or _run_snapshot(run) != run_snapshot
        or _target_snapshot(target) != target_snapshot
    ):
        _fail(
            "nrc_phase_b_row_drift",
            "Run or target authority changed during strict parsing.",
        )
    targets = (
        db.query(ConnectorRunTarget)
        .filter(ConnectorRunTarget.connector_run_id == run_id)
        .populate_existing()
        .with_for_update()
        .all()
    )
    if (
        len(targets) != 1
        or targets[0].connector_run_target_id != target_id
    ):
        _fail(
            "nrc_phase_b_row_drift",
            "Run target cardinality changed during strict parsing.",
        )
    _validate_run(
        db,
        run,
        expected_event_snapshot=event_snapshot,
        lock_events=True,
    )
    _validate_target(target, run=run)
    return run, target


def _recovery_target_snapshot(
    db: Session,
    *,
    target_id: str,
    target_snapshot: _RowSnapshot,
    initial_source_reference: Mapping[str, Any],
) -> _RowSnapshot:
    target = (
        db.query(ConnectorRunTarget)
        .filter(
            ConnectorRunTarget.connector_run_target_id == target_id
        )
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    source_reference = (
        target.source_reference_json if target is not None else None
    )
    if (
        target is None
        or not isinstance(source_reference, dict)
        or _CUSTODY_KEY in initial_source_reference
        or _CUSTODY_KEY not in source_reference
    ):
        _fail(
            "nrc_phase_b_row_drift",
            "Concurrent exact-conflict authority is not one custody delta.",
        )
    without_custody = deepcopy(source_reference)
    without_custody.pop(_CUSTODY_KEY)
    if without_custody != initial_source_reference:
        _fail(
            "nrc_phase_b_row_drift",
            "Concurrent exact-conflict authority changed outside custody.",
        )
    replacement = _canonical_snapshot_value(source_reference)
    replaced = False
    recovered_snapshot: list[tuple[str, Any]] = []
    for key, value in target_snapshot:
        if key == "source_reference_json":
            if replaced:
                _fail(
                    "nrc_phase_b_snapshot_invalid",
                    "Target snapshot has duplicate source-reference columns.",
                )
            recovered_snapshot.append((key, replacement))
            replaced = True
        else:
            recovered_snapshot.append((key, value))
    if not replaced:
        _fail(
            "nrc_phase_b_snapshot_invalid",
            "Target snapshot omits source-reference authority.",
        )
    return tuple(recovered_snapshot)


def _begin_authoritative_transaction(db: Session) -> None:
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")


def _cleanup_owned_session(db: Session) -> bool:
    try:
        if not db.in_transaction():
            return True
        db.rollback()
        return True
    except BaseException:
        try:
            db.invalidate()
        except BaseException:
            pass
        return False


def _detach_then_rollback(
    db: Session,
    linkage: ApsContentLinkage,
) -> ApsContentLinkage:
    db.expunge(linkage)
    db.rollback()
    return linkage


def _detach_then_commit(
    db: Session,
    linkage: ApsContentLinkage,
) -> ApsContentLinkage:
    db.expunge(linkage)
    db.commit()
    return linkage


def _custody_ineligible(
    *,
    cause: Exception | None = None,
) -> NoReturn:
    error = NrcPhaseBLinkageError(
        "nrc_phase_b_custody_ineligible",
        "Target custody marker is absent, pending, malformed, or contradictory.",
    )
    if cause is None:
        raise error
    raise error from cause


def _initial_custody_gate(source_reference: Mapping[str, Any]) -> None:
    if _CUSTODY_KEY not in source_reference:
        return
    try:
        marker = nrc_phase_b_custody.parse_custody_marker(
            source_reference[_CUSTODY_KEY]
        )
    except nrc_phase_b_custody.NrcPhaseBCustodyMarkerError as exc:
        _custody_ineligible(cause=exc)
    if marker["status"] != nrc_phase_b_custody.VERIFIED:
        _custody_ineligible()


def _require_exact_custody(
    value: object,
    *,
    status: str,
    linkage: ApsContentLinkage,
    raw_size: int,
    attempt_id: str | None = None,
) -> dict[str, Any]:
    try:
        return nrc_phase_b_custody.require_exact_custody_marker(
            value,
            status=status,
            connector_run_id=linkage.run_id,
            connector_run_target_id=linkage.target_id,
            aps_content_linkage_id=linkage.aps_content_linkage_id,
            content_id=linkage.content_id,
            blob_ref=str(linkage.blob_ref or ""),
            blob_sha256=str(linkage.blob_sha256 or ""),
            blob_size_bytes=raw_size,
            attempt_id=attempt_id,
        )
    except nrc_phase_b_custody.NrcPhaseBCustodyMarkerError as exc:
        _custody_ineligible(cause=exc)


def _phase_one_state(
    *,
    target: ConnectorRunTarget,
    action: str,
    existing: ApsContentLinkage | None,
    raw_size: int,
) -> tuple[str, dict[str, Any] | None]:
    source_reference = target.source_reference_json
    assert isinstance(source_reference, Mapping)
    receipt_present = _ORIGIN_RECEIPT_KEY in source_reference
    if receipt_present and action != "existing":
        _fail(
            "nrc_phase_b_receipt_without_linkage",
            "A canonical origin receipt requires exact existing content linkage.",
        )

    marker_present = _CUSTODY_KEY in source_reference
    if not marker_present:
        if action == "existing":
            _custody_ineligible()
        return "first_bind", None

    try:
        marker = nrc_phase_b_custody.parse_custody_marker(
            source_reference[_CUSTODY_KEY]
        )
    except nrc_phase_b_custody.NrcPhaseBCustodyMarkerError as exc:
        _custody_ineligible(cause=exc)
    if (
        marker["status"] != nrc_phase_b_custody.VERIFIED
        or action != "existing"
        or existing is None
    ):
        _custody_ineligible()
    verified = _require_exact_custody(
        marker,
        status=nrc_phase_b_custody.VERIFIED,
        linkage=existing,
        raw_size=raw_size,
    )
    return "verified_replay", verified


def _recover_exact_conflict(
    db: Session,
    *,
    payload: Mapping[str, Any],
    run_snapshot: _RowSnapshot,
    target_snapshot: _RowSnapshot,
    event_snapshot: _EventSnapshot,
    initial_source_reference: Mapping[str, Any],
    raw_size: int,
) -> ApsContentLinkage:
    try:
        _begin_authoritative_transaction(db)
        recovered_target_snapshot = _recovery_target_snapshot(
            db,
            target_id=str(payload["target_id"]),
            target_snapshot=target_snapshot,
            initial_source_reference=initial_source_reference,
        )
        _, target = _reload_authority(
            db,
            run_id=str(payload["run_id"]),
            target_id=str(payload["target_id"]),
            run_snapshot=run_snapshot,
            target_snapshot=recovered_target_snapshot,
            event_snapshot=event_snapshot,
        )
        action, existing = _preflight(db, payload=payload)
        if action != "existing" or existing is None:
            _fail(
                "nrc_phase_b_persistence_conflict",
                "Concurrent persistence did not produce one exact linkage.",
            )
        phase_state, _ = _phase_one_state(
            target=target,
            action=action,
            existing=existing,
            raw_size=raw_size,
        )
        if phase_state != "verified_replay":
            _custody_ineligible()
        return _detach_then_rollback(db, existing)
    except SQLAlchemyError as exc:
        _cleanup_owned_session(db)
        raise NrcPhaseBLinkageError(
            "nrc_phase_b_persistence_conflict",
            "Exact-conflict recovery could not revalidate durable authority.",
        ) from exc


def _durably_verified_after_commit_error(
    db: Session,
    *,
    run_id: str,
    target_id: str,
    expected_linkage_id: str,
    processed: Mapping[str, Any],
    raw_sha256: str,
    raw_ref: str,
    raw_size: int,
    attempt_id: str,
    run_snapshot: _RowSnapshot,
    verified_target_snapshot: _RowSnapshot,
    event_snapshot: _EventSnapshot,
) -> bool:
    if not _cleanup_owned_session(db):
        return False
    try:
        _begin_authoritative_transaction(db)
        run, target = _reload_authority(
            db,
            run_id=run_id,
            target_id=target_id,
            run_snapshot=run_snapshot,
            target_snapshot=verified_target_snapshot,
            event_snapshot=event_snapshot,
        )
        payload = _strict_payload(
            run=run,
            target=target,
            raw_sha256=raw_sha256,
            blob_ref=raw_ref,
            processed=processed,
        )
        exact = _require_exact_persisted(db, payload=payload)
        if exact.aps_content_linkage_id != expected_linkage_id:
            _fail(
                "nrc_phase_b_persistence_conflict",
                "Durable commit acknowledgement changed linkage identity.",
            )
        source_reference = target.source_reference_json
        if not isinstance(source_reference, Mapping):
            _custody_ineligible()
        _require_exact_custody(
            source_reference.get(_CUSTODY_KEY),
            status=nrc_phase_b_custody.VERIFIED,
            linkage=exact,
            raw_size=raw_size,
            attempt_id=attempt_id,
        )
        return True
    except Exception:
        return False
    finally:
        _cleanup_owned_session(db)


def _finalize_pending_custody(
    db: Session,
    *,
    linkage: ApsContentLinkage,
    processed: Mapping[str, Any],
    raw_sha256: str,
    raw_ref: str,
    raw_size: int,
    run_snapshot: _RowSnapshot,
    pending_target_snapshot: _RowSnapshot,
    event_snapshot: _EventSnapshot,
    pending_marker: Mapping[str, Any],
) -> None:
    _begin_authoritative_transaction(db)
    run, target = _reload_authority(
        db,
        run_id=linkage.run_id,
        target_id=linkage.target_id,
        run_snapshot=run_snapshot,
        target_snapshot=pending_target_snapshot,
        event_snapshot=event_snapshot,
    )
    payload = _strict_payload(
        run=run,
        target=target,
        raw_sha256=raw_sha256,
        blob_ref=raw_ref,
        processed=processed,
    )
    exact = _require_exact_persisted(db, payload=payload)
    if exact.aps_content_linkage_id != linkage.aps_content_linkage_id:
        _fail(
            "nrc_phase_b_persistence_conflict",
            "Phase-two exact projection changed linkage identity.",
        )
    attempt_id = str(pending_marker["attempt_id"])
    source_reference = deepcopy(target.source_reference_json)
    current = _require_exact_custody(
        source_reference.get(_CUSTODY_KEY),
        status=nrc_phase_b_custody.PENDING_SNAPSHOT_EXIT,
        linkage=exact,
        raw_size=raw_size,
        attempt_id=attempt_id,
    )
    source_reference[_CUSTODY_KEY] = (
        nrc_phase_b_custody.verified_custody_marker(current)
    )
    target.source_reference_json = source_reference
    db.flush()
    verified_target_snapshot = _target_snapshot(target)
    try:
        db.commit()
    except Exception:
        if _durably_verified_after_commit_error(
            db,
            run_id=linkage.run_id,
            target_id=linkage.target_id,
            expected_linkage_id=linkage.aps_content_linkage_id,
            processed=processed,
            raw_sha256=raw_sha256,
            raw_ref=raw_ref,
            raw_size=raw_size,
            attempt_id=attempt_id,
            run_snapshot=run_snapshot,
            verified_target_snapshot=verified_target_snapshot,
            event_snapshot=event_snapshot,
        ):
            return
        raise


def _strict_payload(
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    raw_sha256: str,
    blob_ref: str,
    processed: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        return (
            nrc_aps_content_index
            .build_strict_content_units_payload_from_processed_output(
                run_id=run.connector_run_id,
                target_id=target.connector_run_target_id,
                accession_number=_ACCESSION,
                blob_ref=blob_ref,
                blob_sha256=raw_sha256,
                processed_output=processed,
            )
        )
    except (TypeError, ValueError) as exc:
        raise NrcPhaseBLinkageError(
            "nrc_phase_b_parse_projection_invalid",
            "Strict parser result cannot form canonical content units.",
        ) from exc


def _validate_verifier_authority(
    authority: _VerifierAuthorityRead,
    *,
    target_id: str,
) -> tuple[ConnectorRun, ConnectorRunTarget, str, int]:
    if len(authority.targets) != 1:
        _fail(
            "nrc_phase_b_target_not_found",
            "Connector run target does not exist.",
        )
    if len(authority.runs) != 1:
        _fail(
            "nrc_phase_b_run_not_found",
            "Connector run does not exist.",
        )
    run = _materialize_core_row(authority.runs[0], ConnectorRun)
    target = _materialize_core_row(
        authority.targets[0],
        ConnectorRunTarget,
    )
    _validate_run_shape(run)
    events = [
        _materialize_core_row(row, ConnectorRunEvent)
        for row in authority.events
    ]
    phase_event_count = sum(
        event.event_type != _NRC_CAMPAIGN_SEAL_EVENT_TYPE
        for event in events
    )
    seal_event_count = len(events) - phase_event_count
    if (
        phase_event_count > _NRC_PHASE_B_EVENT_CAP
        or seal_event_count > _NRC_CAMPAIGN_SEAL_EVENT_CAP
    ):
        _fail(
            "nrc_phase_b_run_invalid",
            "Strict NRC run exceeds its bounded event authority.",
        )
    _validate_run_events(run, events)
    if (
        len(authority.run_targets) != 1
        or authority.run_targets[0].values.get(
            "connector_run_target_id"
        )
        != target_id
    ):
        _fail(
            "nrc_phase_b_target_cardinality",
            "Strict NRC run must have exactly one ordinal-1 target.",
        )
    raw_sha256, raw_size = _validate_target(target, run=run)
    return run, target, raw_sha256, raw_size


def _validate_verifier_projection(
    projection: _VerifierProjectionRead,
    *,
    payload: Mapping[str, Any],
    target: ConnectorRunTarget,
    raw_size: int,
) -> ApsContentLinkage:
    if len(projection.linkages) != 1:
        _fail(
            "nrc_phase_b_linkage_cardinality",
            "Target must have exactly one durable content linkage.",
        )
    linkage = _materialize_core_row(
        projection.linkages[0],
        ApsContentLinkage,
    )
    if not _linkage_matches(linkage, payload):
        _fail(
            "nrc_phase_b_linkage_mismatch",
            "Existing run-target linkage is not exact.",
        )
    documents = [
        _materialize_core_row(row, ApsContentDocument)
        for row in projection.documents
    ]
    chunks = [
        _materialize_core_row(row, ApsContentChunk)
        for row in projection.chunks
    ]
    if (
        len(documents) != 1
        or not _document_matches(documents[0], payload)
        or not _chunks_match(chunks, payload)
    ):
        _fail(
            "nrc_phase_b_linkage_mismatch",
            "Existing linkage document/chunk projection is not exact.",
        )
    source_reference = target.source_reference_json
    if not isinstance(source_reference, Mapping):
        _custody_ineligible()
    _require_exact_custody(
        source_reference.get(_CUSTODY_KEY),
        status=nrc_phase_b_custody.VERIFIED,
        linkage=linkage,
        raw_size=raw_size,
    )
    return linkage


def _verify_strict_nrc_phase_b_linkage_on_connection(
    db: Session,
    connection: Connection,
    *,
    target_id: str,
    raw_root: Path,
) -> NrcPhaseBVerifiedState:
    """Verify two visible snapshots without an ABA or serializability claim."""

    with db.no_autoflush:
        initial_authority = _read_verifier_authority(
            connection,
            target_id=target_id,
        )
        run, target, raw_sha256, raw_size = (
            _validate_verifier_authority(
                initial_authority,
                target_id=target_id,
            )
        )
        linkage_table = ApsContentLinkage.__table__
        initial_linkages = _read_bounded_core_rows(
            connection,
            linkage_table,
            criterion=linkage_table.c.target_id == target_id,
            max_rows=1,
        )
        initial_linkage_snapshot = tuple(
            row.snapshot for row in initial_linkages
        )
        raw_path = _safe_rehash(
            target,
            expected_sha256=raw_sha256,
            expected_size=raw_size,
            drift_phase=False,
            raw_root=raw_root,
        )
        expected_raw_ref = str(target.raw_storage_ref)
        try:
            processed = nrc_aps_strict_parse.parse_admitted_blob_strict(
                blob_path=raw_path,
                expected_sha256=raw_sha256,
            )
        except (
            nrc_aps_strict_parse.StrictParseViolation,
            OSError,
            ValueError,
        ) as exc:
            raise NrcPhaseBLinkageError(
                "nrc_phase_b_parse_failed",
                "Frozen strict parser refused admitted bytes.",
            ) from exc
        payload = _strict_payload(
            run=run,
            target=target,
            raw_sha256=raw_sha256,
            blob_ref=str(raw_path),
            processed=processed,
        )
        snapshot_a_authority = _read_verifier_authority(
            connection,
            target_id=target_id,
            expected_run_id=run.connector_run_id,
        )
        if (
            snapshot_a_authority.fingerprint
            != initial_authority.fingerprint
        ):
            _fail(
                "nrc_phase_b_row_drift",
                "Run, target, or event authority changed during parsing.",
            )
        snapshot_a_projection = _read_verifier_projection(
            connection,
            payload=payload,
        )
        if tuple(
            row.snapshot for row in snapshot_a_projection.linkages
        ) != initial_linkage_snapshot:
            _fail(
                "nrc_phase_b_row_drift",
                "Target linkage authority changed during parsing.",
            )
        linkage = _validate_verifier_projection(
            snapshot_a_projection,
            payload=payload,
            target=target,
            raw_size=raw_size,
        )
        snapshot_a = (
            snapshot_a_authority.fingerprint,
            snapshot_a_projection.fingerprint,
        )
        verified_values: tuple[str, str, str, str, str, str, int] | None = (
            None
        )
        try:
            with locked_raw_file_snapshot(
                raw_root,
                raw_path,
            ) as raw_snapshot:
                if (
                    raw_snapshot.canonical_ref != expected_raw_ref
                    or raw_snapshot.sha256 != raw_sha256
                    or raw_snapshot.size != raw_size
                ):
                    _fail(
                        "nrc_phase_b_raw_drift",
                        "Final locked raw snapshot contradicts authority.",
                    )
                snapshot_b_authority = _read_verifier_authority(
                    connection,
                    target_id=target_id,
                    expected_run_id=run.connector_run_id,
                )
                snapshot_b_projection = _read_verifier_projection(
                    connection,
                    payload=payload,
                )
                snapshot_b = (
                    snapshot_b_authority.fingerprint,
                    snapshot_b_projection.fingerprint,
                )
                if snapshot_b != snapshot_a:
                    _fail(
                        "nrc_phase_b_row_drift",
                        "Phase B authority changed between visible snapshots.",
                    )
                _reject_phase_b_identity_map_state(db)
                verified_values = (
                    run.connector_run_id,
                    target.connector_run_target_id,
                    linkage.aps_content_linkage_id,
                    linkage.content_id,
                    raw_snapshot.canonical_ref,
                    raw_sha256,
                    raw_size,
                )
        except StableRawStorageError as exc:
            raise NrcPhaseBLinkageError(
                "nrc_phase_b_raw_drift",
                "Final locked raw snapshot changed during verification.",
            ) from exc
        assert verified_values is not None
        return NrcPhaseBVerifiedState(*verified_values)


def _verify_strict_nrc_phase_b_linkage_with_raw_root(
    db: Session,
    *,
    connector_run_target_id: str,
    raw_root: Path,
) -> NrcPhaseBVerifiedState:
    """Verify committed state against one explicit raw root."""

    with db.no_autoflush:
        if not db.in_transaction():
            _fail(
                "nrc_phase_b_caller_transaction_required",
                "Phase B verification requires an active caller transaction.",
            )
        _reject_phase_b_identity_map_state(db)
        target_id = _text(connector_run_target_id)
        canonical_raw_root = _lexical_absolute(raw_root)
        engine = _independent_committed_engine(db)
        try:
            with engine.connect() as connection:
                isolation_level = re.sub(
                    r"[-\s_]+",
                    " ",
                    connection.get_isolation_level().strip().upper(),
                )
                if isolation_level == "READ UNCOMMITTED":
                    _committed_visibility_unavailable()
                return _verify_strict_nrc_phase_b_linkage_on_connection(
                    db,
                    connection,
                    target_id=target_id,
                    raw_root=canonical_raw_root,
                )
        except NrcPhaseBLinkageError:
            raise
        except Exception as exc:
            _committed_visibility_unavailable(exc)


def verify_strict_nrc_phase_b_linkage_read_only(
    db: Session,
    connector_run_target_id: str,
    settings: Settings,
) -> NrcPhaseBVerifiedState:
    """Verify committed Phase-B authority from explicit read settings."""

    if not isinstance(settings, Settings):
        _fail(
            "nrc_phase_b_settings_invalid",
            "Read-only Phase B verification requires explicit Settings.",
        )
    return _verify_strict_nrc_phase_b_linkage_with_raw_root(
        db,
        connector_run_target_id=connector_run_target_id,
        raw_root=Path(settings.connector_raw_dir),
    )


def verify_strict_nrc_phase_b_linkage(
    db: Session,
    *,
    connector_run_target_id: str,
) -> NrcPhaseBVerifiedState:
    """Verify committed state without an ABA or serializability claim."""

    return _verify_strict_nrc_phase_b_linkage_with_raw_root(
        db,
        connector_run_target_id=connector_run_target_id,
        raw_root=Path(settings.connector_raw_dir),
    )


def _bind_strict_nrc_phase_b_linkage_owned(
    db: Session,
    *,
    connector_run_target_id: str,
) -> ApsContentLinkage:
    """Bind one strict NRC Phase-B parse to server-owned raw authority."""

    target_id = _text(connector_run_target_id)
    target = (
        db.query(ConnectorRunTarget)
        .filter(
            ConnectorRunTarget.connector_run_target_id == target_id
        )
        .populate_existing()
        .one_or_none()
    )
    if target is None:
        _fail(
            "nrc_phase_b_target_not_found",
            "Connector run target does not exist.",
        )
    run = (
        db.query(ConnectorRun)
        .filter(ConnectorRun.connector_run_id == target.connector_run_id)
        .populate_existing()
        .one_or_none()
    )
    if run is None:
        _fail(
            "nrc_phase_b_run_not_found",
            "Connector run does not exist.",
        )
    event_authority = _validate_run(db, run)
    targets = (
        db.query(ConnectorRunTarget)
        .filter(
            ConnectorRunTarget.connector_run_id
            == run.connector_run_id
        )
        .populate_existing()
        .all()
    )
    if (
        len(targets) != 1
        or targets[0].connector_run_target_id != target_id
    ):
        _fail(
            "nrc_phase_b_target_cardinality",
            "Strict NRC run must have exactly one ordinal-1 target.",
        )
    raw_sha256, raw_size = _validate_target(target, run=run)
    assert isinstance(target.source_reference_json, Mapping)
    initial_source_reference = deepcopy(target.source_reference_json)
    _initial_custody_gate(initial_source_reference)
    raw_path = _safe_rehash(
        target,
        expected_sha256=raw_sha256,
        expected_size=raw_size,
        drift_phase=False,
    )
    run_authority = _run_snapshot(run)
    target_authority = _target_snapshot(target)
    run_id = run.connector_run_id
    expected_raw_ref = str(target.raw_storage_ref)

    try:
        processed = nrc_aps_strict_parse.parse_admitted_blob_strict(
            blob_path=raw_path,
            expected_sha256=raw_sha256,
        )
    except (
        nrc_aps_strict_parse.StrictParseViolation,
        OSError,
        ValueError,
    ) as exc:
        raise NrcPhaseBLinkageError(
            "nrc_phase_b_parse_failed",
            "Frozen strict parser refused admitted bytes.",
        ) from exc
    _strict_payload(
        run=run,
        target=target,
        raw_sha256=raw_sha256,
        blob_ref=str(raw_path),
        processed=processed,
    )
    db.rollback()

    phase_one_committed = False
    detached_linkage: ApsContentLinkage | None = None
    pending_marker: dict[str, Any] | None = None
    pending_target_authority: _RowSnapshot | None = None
    raw_ref: str | None = None
    try:
        with locked_raw_file_snapshot(
            Path(settings.connector_raw_dir),
            raw_path,
        ) as raw_snapshot:
            if (
                raw_snapshot.canonical_ref
                != expected_raw_ref
                or raw_snapshot.size != raw_size
                or raw_snapshot.sha256 != raw_sha256
            ):
                _fail(
                    "nrc_phase_b_raw_drift",
                    "Final locked raw snapshot contradicts admission authority.",
                )
            raw_ref = raw_snapshot.canonical_ref
            _begin_authoritative_transaction(db)
            run, target = _reload_authority(
                db,
                run_id=run_id,
                target_id=target_id,
                run_snapshot=run_authority,
                target_snapshot=target_authority,
                event_snapshot=event_authority,
            )
            payload = _strict_payload(
                run=run,
                target=target,
                raw_sha256=raw_sha256,
                blob_ref=raw_ref,
                processed=processed,
            )
            action, existing = _preflight(
                db,
                payload=payload,
            )
            phase_state, _ = _phase_one_state(
                target=target,
                action=action,
                existing=existing,
                raw_size=raw_size,
            )
            if phase_state == "verified_replay":
                assert existing is not None
                return _detach_then_rollback(db, existing)
            try:
                if action == "linkage_only":
                    inserted = (
                        nrc_aps_content_index
                        .insert_content_linkage_immutable(
                            db,
                            payload=payload,
                        )
                    )
                elif action == "immutable_insert":
                    inserted = (
                        nrc_aps_content_index
                        .insert_content_units_payload_immutable(
                            db,
                            payload=payload,
                        )
                    )
                else:
                    _fail(
                        "nrc_phase_b_persistence_conflict",
                        "Unknown strict persistence action.",
                    )
            except (
                nrc_aps_content_index.ImmutableContentInsertConflict
            ):
                db.rollback()
                return _recover_exact_conflict(
                    db,
                    payload=payload,
                    run_snapshot=run_authority,
                    target_snapshot=target_authority,
                    event_snapshot=event_authority,
                    initial_source_reference=initial_source_reference,
                    raw_size=raw_size,
                )

            exact = _require_exact_persisted(db, payload=payload)
            if (
                exact.aps_content_linkage_id
                != inserted.aps_content_linkage_id
            ):
                _fail(
                    "nrc_phase_b_persistence_conflict",
                    "Precommit exact-one requery changed linkage identity.",
                )
            pending_marker = (
                nrc_phase_b_custody.build_pending_custody_marker(
                    connector_run_id=exact.run_id,
                    connector_run_target_id=exact.target_id,
                    aps_content_linkage_id=exact.aps_content_linkage_id,
                    content_id=exact.content_id,
                    blob_ref=str(exact.blob_ref or ""),
                    blob_sha256=str(exact.blob_sha256 or ""),
                    blob_size_bytes=raw_size,
                )
            )
            source_reference = deepcopy(target.source_reference_json)
            source_reference[_CUSTODY_KEY] = pending_marker
            target.source_reference_json = source_reference
            db.flush()
            pending_target_authority = _target_snapshot(target)
            detached_linkage = _detach_then_commit(db, exact)
            phase_one_committed = True
    except StableRawStorageError as exc:
        if phase_one_committed:
            raise NrcPhaseBLinkageError(
                "nrc_phase_b_postcommit_raw_drift",
                "Postcommit raw drift preserves exact rows but grants no "
                "receipt, retry, or repair authority.",
            ) from exc
        raise NrcPhaseBLinkageError(
            "nrc_phase_b_raw_drift",
            "Final locked raw snapshot changed during persistence.",
        ) from exc

    assert detached_linkage is not None
    assert pending_marker is not None
    assert pending_target_authority is not None
    assert raw_ref is not None
    _finalize_pending_custody(
        db,
        linkage=detached_linkage,
        processed=processed,
        raw_sha256=raw_sha256,
        raw_ref=raw_ref,
        raw_size=raw_size,
        run_snapshot=run_authority,
        pending_target_snapshot=pending_target_authority,
        event_snapshot=event_authority,
        pending_marker=pending_marker,
    )
    return detached_linkage


def bind_strict_nrc_phase_b_linkage(
    db: Session,
    *,
    connector_run_target_id: str,
) -> ApsContentLinkage:
    """Own one clean transaction for strict NRC Phase-B linkage."""

    _require_owned_clean_transaction(db)
    try:
        linkage = _bind_strict_nrc_phase_b_linkage_owned(
            db,
            connector_run_target_id=connector_run_target_id,
        )
        if db.in_transaction():
            _fail(
                "nrc_phase_b_transaction_leak",
                "Owned Phase-B transaction remained active on return.",
            )
        return linkage
    except BaseException:
        _cleanup_owned_session(db)
        raise
