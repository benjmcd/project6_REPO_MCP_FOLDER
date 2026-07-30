from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat
from typing import TYPE_CHECKING, Any, NoReturn, TypeVar
from typing import cast as type_cast
from uuid import UUID

from sqlalchemy import JSON, Table, cast, false, literal, or_, select, update
from sqlalchemy.engine import RowMapping
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    ApsContentLinkage,
    ConnectorPolicySnapshot,
    ConnectorRun,
    ConnectorRunEvent,
    ConnectorRunTarget,
    DatasetSourceProvenance,
    DatasetVersion,
    L3ConnectorSourceIntakeRecord,
)
from app.services import nrc_phase_b_custody
from app.services.connector_egress_authorization import (
    VerifiedHistoricalGrantEvidence,
    resolve_historical_connector_grant_evidence,
    strict_json_loads,
)
from app.services.connector_egress_arming import (
    canonical_arming_payload,
    compute_arming_fingerprint,
)

if TYPE_CHECKING:
    from app.services.connector_egress_transport import (
        VerifiedTerminalRequestLedger,
    )

_ModelT = TypeVar("_ModelT")


ORIGIN_RECEIPT_SCHEMA_ID = "layer3.connector_origin_continuity.v1"
ORIGIN_RECEIPT_STORAGE_KEY = "connector_origin_receipt_v1"
STRICT_ARMING_SCHEMA_ID = "project6.connector_egress_arming.v1"
TERMINAL_LEDGER_SCHEMA_ID = "project6.connector_egress_terminal_ledger.v1"
FRESH_LIVE_PROOF_CLASS = "fresh_live"
OFFLINE_FIXTURE_PROOF_CLASS = "offline_fixture"
_SQLITE_ROOT_MARKER = "layer3_origin_sqlite_root_materialized"

_ALLOWED_CONNECTORS = frozenset({"sciencebase_mcs", "nrc_adams_aps"})
_ORIGIN_EVENT_CAPS: Mapping[str, int] = {
    "nrc_adams_aps": 8,
    "sciencebase_mcs": 12,
}
_ORIGIN_POLICY_CAPS: Mapping[str, int] = {
    "nrc_adams_aps": 2,
    "sciencebase_mcs": 3,
}
_GLOBAL_ORIGIN_EVENT_CAP = 12
_GLOBAL_ORIGIN_POLICY_CAP = 3
_SINGLE_ORIGIN_ROW_CAP = 1
_ORIGIN_HISTORY_ROW_CAP = 10_000
_ORIGIN_CLAIM_DEPTH_CAP = 64
_ORIGIN_CLAIM_NODE_CAP = 10_000
_HEX = frozenset("0123456789abcdef")
_FIXTURE_ID = "ml17123a319"
_FIXTURE_FILE_NAME = "ML17123A319.pdf"
_FIXTURE_ACCESSION = "ML17123A319"
_FIXTURE_MANIFEST_REF = "tests/fixtures/nrc_aps_docs/v1/manifest.json"


class Layer3OriginContinuityError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})


def _fail(
    code: str,
    message: str,
    *,
    details: Mapping[str, Any] | None = None,
) -> NoReturn:
    raise Layer3OriginContinuityError(code, message, details=details)


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_noncanonical_value",
            "Connector-origin evidence is not canonical JSON.",
        ) from exc


def _stable_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _normalized_sha256(value: object, *, field: str) -> str:
    normalized = str(value or "").strip().lower()
    if len(normalized) != 64 or any(char not in _HEX for char in normalized):
        _fail(
            "layer3_origin_invalid_sha256",
            f"{field} must be a lowercase SHA-256.",
            details={"field": field},
        )
    return normalized


def _required_text(value: object, *, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        _fail(
            "layer3_origin_binding_missing",
            f"{field} is required for connector-origin continuity.",
            details={"field": field},
        )
    return normalized


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        _fail(
            "layer3_origin_binding_invalid",
            f"{field} must be a positive integer.",
            details={"field": field},
        )
    return value


def _value(source: object, field: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(field)
    return getattr(source, field, None)


def _as_utc(value: object, *, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise Layer3OriginContinuityError(
                "layer3_origin_timestamp_invalid",
                f"{field} is not a valid UTC timestamp.",
                details={"field": field},
            ) from exc
    else:
        _fail(
            "layer3_origin_timestamp_invalid",
            f"{field} is not a valid UTC timestamp.",
            details={"field": field},
        )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(
            "layer3_origin_timestamp_invalid",
            f"{field} must be timezone-aware.",
            details={"field": field},
        )
    return parsed.astimezone(timezone.utc)


def _one(rows: list[Any], *, code: str, label: str) -> Any:
    if len(rows) != 1:
        _fail(
            code,
            f"Exactly one {label} must bind the connector target.",
            details={"count": len(rows)},
        )
    return rows[0]


def _model_table(model: type[Any]) -> Table:
    table = getattr(model, "__table__", None)
    if not isinstance(table, Table):
        _fail(
            "layer3_origin_anchor_invalid",
            "Origin authority model lacks a mapped table.",
        )
    return table


def _freeze_anchor_value(
    value: object,
    *,
    preserve_mapping_order: bool = False,
) -> tuple[str, Any]:
    if value is None:
        return ("none", None)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, float):
        if not math.isfinite(value):
            _fail(
                "layer3_origin_anchor_invalid",
                "Origin authority contains a non-finite float.",
            )
        return ("float", value.hex())
    if isinstance(value, str):
        return ("str", value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return ("bytes", bytes(value).hex())
    if isinstance(value, datetime):
        normalized = value
        if value.tzinfo is not None:
            normalized = value.astimezone(timezone.utc)
        return ("datetime", normalized.isoformat(timespec="microseconds"))
    if isinstance(value, date):
        return ("date", value.isoformat())
    if isinstance(value, time):
        return ("time", value.isoformat(timespec="microseconds"))
    if isinstance(value, Decimal):
        return ("decimal", str(value.normalize()))
    if isinstance(value, UUID):
        return ("uuid", str(value))
    if isinstance(value, Mapping):
        items: list[tuple[str, tuple[str, Any]]] = []
        for key, item in value.items():
            if not isinstance(key, str):
                _fail(
                    "layer3_origin_anchor_invalid",
                    "Origin authority mapping keys must be strings.",
                )
            items.append(
                (
                    key,
                    _freeze_anchor_value(
                        item,
                        preserve_mapping_order=preserve_mapping_order,
                    ),
                )
            )
        if not preserve_mapping_order:
            items.sort()
        return ("mapping", tuple(items))
    if isinstance(value, list):
        return (
            "list",
            tuple(
                _freeze_anchor_value(
                    item,
                    preserve_mapping_order=preserve_mapping_order,
                )
                for item in value
            ),
        )
    if isinstance(value, tuple):
        return (
            "tuple",
            tuple(
                _freeze_anchor_value(
                    item,
                    preserve_mapping_order=preserve_mapping_order,
                )
                for item in value
            ),
        )
    _fail(
        "layer3_origin_anchor_invalid",
        f"Unsupported origin authority type: {type(value).__name__}.",
    )


def _thaw_anchor_value(value: tuple[str, Any]) -> Any:
    kind, payload = value
    if kind == "none":
        return None
    if kind in {"bool", "int", "str"}:
        return payload
    if kind == "float":
        return float.fromhex(payload)
    if kind == "bytes":
        return bytes.fromhex(payload)
    if kind == "datetime":
        return datetime.fromisoformat(payload)
    if kind == "date":
        return date.fromisoformat(payload)
    if kind == "time":
        return time.fromisoformat(payload)
    if kind == "decimal":
        return Decimal(payload)
    if kind == "uuid":
        return UUID(payload)
    if kind == "mapping":
        return {
            key: _thaw_anchor_value(item)
            for key, item in payload
        }
    if kind == "list":
        return [_thaw_anchor_value(item) for item in payload]
    if kind == "tuple":
        return tuple(_thaw_anchor_value(item) for item in payload)
    _fail(
        "layer3_origin_anchor_invalid",
        f"Unknown frozen origin authority type: {kind}.",
    )


@dataclass(frozen=True)
class _AnchorRow:
    table_name: str
    values: tuple[tuple[str, tuple[str, Any]], ...]
    cas_values: tuple[tuple[str, tuple[str, Any]], ...]

    def materialize(self, model: type[_ModelT]) -> _ModelT:
        table = getattr(model, "__table__", None)
        if getattr(table, "name", None) != self.table_name:
            _fail(
                "layer3_origin_anchor_invalid",
                "Origin authority materialization used the wrong model.",
            )
        return model(
            **{
                key: _thaw_anchor_value(value)
                for key, value in self.values
            }
        )


@dataclass(frozen=True)
class _OriginAnchor:
    target: _AnchorRow
    run: _AnchorRow
    events: tuple[_AnchorRow, ...]
    policy_snapshots: tuple[_AnchorRow, ...]
    linkages: tuple[_AnchorRow, ...]
    dataset_versions: tuple[_AnchorRow, ...]
    provenances: tuple[_AnchorRow, ...]
    intakes: tuple[_AnchorRow, ...]


def _index_anchor_authority(
    rows: Sequence[_AnchorRow],
    *,
    model: type[_ModelT],
    identity_field: str,
) -> dict[str, _ModelT]:
    indexed: dict[str, _ModelT] = {}
    for row in rows:
        materialized = row.materialize(model)
        identity = getattr(materialized, identity_field, None)
        if (
            not isinstance(identity, str)
            or not identity
            or identity in indexed
        ):
            _fail(
                "layer3_origin_anchor_invalid",
                "Frozen terminal-ledger authority has invalid cardinality.",
            )
        indexed[identity] = materialized
    return indexed


def _ledger_event_order(
    event: ConnectorRunEvent,
) -> tuple[str, str]:
    created_at = event.created_at
    if not isinstance(created_at, datetime):
        _fail(
            "layer3_origin_anchor_invalid",
            "Frozen terminal-ledger event lacks a datetime.",
        )
    normalized = (
        created_at.replace(tzinfo=timezone.utc)
        if created_at.tzinfo is None
        else created_at.astimezone(timezone.utc)
    )
    event_id = event.connector_run_event_id
    if not isinstance(event_id, str) or not event_id:
        _fail(
            "layer3_origin_anchor_invalid",
            "Frozen terminal-ledger event lacks an identity.",
        )
    return normalized.isoformat(timespec="microseconds"), event_id


@dataclass(frozen=True)
class _FrozenLedgerQuery:
    rows: tuple[ConnectorRunEvent, ...]

    def filter(self, *criteria: object) -> _FrozenLedgerQuery:
        return self

    def order_by(self, *criteria: object) -> _FrozenLedgerQuery:
        return self

    def all(self) -> list[ConnectorRunEvent]:
        return list(self.rows)


@dataclass(frozen=True)
class _FrozenLedgerAuthority:
    run: ConnectorRun
    events_by_id: Mapping[str, ConnectorRunEvent]
    policies_by_id: Mapping[str, ConnectorPolicySnapshot]
    terminal_events: tuple[ConnectorRunEvent, ...]

    @classmethod
    def from_anchor(
        cls,
        anchor: _OriginAnchor,
    ) -> _FrozenLedgerAuthority:
        run = anchor.run.materialize(ConnectorRun)
        events = _index_anchor_authority(
            anchor.events,
            model=ConnectorRunEvent,
            identity_field="connector_run_event_id",
        )
        policies = _index_anchor_authority(
            anchor.policy_snapshots,
            model=ConnectorPolicySnapshot,
            identity_field="connector_policy_snapshot_id",
        )
        run_id = run.connector_run_id
        if any(
            event.connector_run_id != run_id
            for event in events.values()
        ) or any(
            policy.connector_run_id != run_id
            for policy in policies.values()
        ):
            _fail(
                "layer3_origin_anchor_invalid",
                "Frozen terminal-ledger authority crosses run identity.",
            )
        terminal_events = tuple(
            sorted(
                (
                    event
                    for event in events.values()
                    if event.event_type
                    in {"egress_reserved", "egress_completed"}
                ),
                key=_ledger_event_order,
            )
        )
        return cls(
            run=run,
            events_by_id=events,
            policies_by_id=policies,
            terminal_events=terminal_events,
        )

    def get(
        self,
        model: type[Any],
        identity: str,
    ) -> Any | None:
        if model is ConnectorRun:
            return (
                self.run
                if identity == self.run.connector_run_id
                else None
            )
        if model is ConnectorRunEvent:
            return self.events_by_id.get(identity)
        if model is ConnectorPolicySnapshot:
            return self.policies_by_id.get(identity)
        _fail(
            "layer3_origin_anchor_invalid",
            "Terminal-ledger derivation requested unanchored authority.",
        )

    def query(self, model: type[Any]) -> _FrozenLedgerQuery:
        if model is not ConnectorRunEvent:
            _fail(
                "layer3_origin_anchor_invalid",
                "Terminal-ledger derivation queried unanchored authority.",
            )
        return _FrozenLedgerQuery(self.terminal_events)


def _anchor_columns(
    table: Table,
    prefix: str,
) -> list[Any]:
    return [
        column.label(f"{prefix}__{column.key}")
        for column in sorted(table.columns, key=lambda item: item.key)
    ]


def _anchor_row(
    row: RowMapping,
    *,
    table: Table,
    prefix: str,
) -> _AnchorRow | None:
    primary_values = [
        row[f"{prefix}__{column.key}"]
        for column in table.primary_key
    ]
    if all(value is None for value in primary_values):
        return None
    if any(value is None for value in primary_values):
        _fail(
            "layer3_origin_anchor_invalid",
            "Origin authority has a partial primary key.",
        )
    table_name = getattr(table, "name", None)
    if not isinstance(table_name, str) or not table_name:
        _fail(
            "layer3_origin_anchor_invalid",
            "Origin authority table lacks an identity.",
        )
    return _AnchorRow(
        table_name=table_name,
        values=tuple(
            (
                column.key,
                _freeze_anchor_value(row[f"{prefix}__{column.key}"]),
            )
            for column in sorted(table.columns, key=lambda item: item.key)
        ),
        cas_values=tuple(
            (
                column.key,
                _freeze_anchor_value(
                    row[f"{prefix}__{column.key}"],
                    preserve_mapping_order=True,
                ),
            )
            for column in sorted(table.columns, key=lambda item: item.key)
        ),
    )


def _anchor_rows(
    rows: Sequence[RowMapping],
    *,
    table: Table,
    prefix: str,
) -> tuple[_AnchorRow, ...]:
    unique: set[_AnchorRow] = set()
    for row in rows:
        anchor_row = _anchor_row(row, table=table, prefix=prefix)
        if anchor_row is not None:
            unique.add(anchor_row)
    return tuple(sorted(unique, key=lambda item: repr(item.values)))


def _bounded_anchor_rows(
    db: Session,
    *,
    table: Table,
    prefix: str,
    criteria: Sequence[Any],
    max_rows: int,
) -> tuple[_AnchorRow, ...]:
    statement = (
        select(*_anchor_columns(table, prefix))
        .select_from(table)
        .where(*criteria)
        .limit(max_rows + 1)
    )
    rows = list(db.execute(statement).mappings().all())
    if len(rows) > max_rows:
        table_name = getattr(table, "name", None)
        if not isinstance(table_name, str) or not table_name:
            _fail(
                "layer3_origin_anchor_invalid",
                "Origin authority table lacks an identity.",
            )
        _fail(
            "layer3_origin_anchor_cardinality_exceeded",
            "Origin authority exceeds its frozen row maximum.",
            details={
                "table": table_name,
                "max_rows": max_rows,
                "observed_at_least": max_rows + 1,
            },
        )
    return _anchor_rows(rows, table=table, prefix=prefix)


def _read_origin_anchor(
    db: Session,
    *,
    target_id: str,
) -> _OriginAnchor:
    target_table = _model_table(ConnectorRunTarget)
    run_table = _model_table(ConnectorRun)
    event_table = _model_table(ConnectorRunEvent)
    policy_table = _model_table(ConnectorPolicySnapshot)
    linkage_table = _model_table(ApsContentLinkage)
    version_table = _model_table(DatasetVersion)
    provenance_table = _model_table(DatasetSourceProvenance)
    intake_table = _model_table(L3ConnectorSourceIntakeRecord)
    base_tables: tuple[tuple[Table, str], ...] = (
        (target_table, "target"),
        (run_table, "run"),
        (version_table, "version"),
    )
    from_clause = (
        target_table.outerjoin(
            run_table,
            run_table.c.connector_run_id
            == target_table.c.connector_run_id,
        )
        .outerjoin(
            version_table,
            version_table.c.dataset_version_id
            == target_table.c.dataset_version_id,
        )
    )
    columns = [
        column
        for table, prefix in base_tables
        for column in _anchor_columns(table, prefix)
    ]
    statement = (
        select(*columns)
        .select_from(from_clause)
        .where(
            target_table.c.connector_run_target_id == target_id
        )
    )
    rows = list(db.execute(statement).mappings().all())
    targets = list(
        _anchor_rows(rows, table=target_table, prefix="target")
    )
    if not targets:
        _fail(
            "layer3_origin_target_not_found",
            "The connector run target does not exist.",
        )
    target = _one(
        targets,
        code="layer3_origin_target_cardinality",
        label="connector run-target row",
    )
    run = _one(
        list(_anchor_rows(rows, table=run_table, prefix="run")),
        code="layer3_origin_run_not_found",
        label="connector run row",
    )
    dataset_versions = _anchor_rows(
        rows,
        table=version_table,
        prefix="version",
    )
    anchored_target = target.materialize(ConnectorRunTarget)
    anchored_run = run.materialize(ConnectorRun)
    run_id = anchored_run.connector_run_id
    anchored_target_id = anchored_target.connector_run_target_id
    connector_key = anchored_run.connector_key
    event_cap = _ORIGIN_EVENT_CAPS.get(
        connector_key,
        _GLOBAL_ORIGIN_EVENT_CAP,
    )
    policy_cap = _ORIGIN_POLICY_CAPS.get(
        connector_key,
        _GLOBAL_ORIGIN_POLICY_CAP,
    )
    version_id = (
        dataset_versions[0]
        .materialize(DatasetVersion)
        .dataset_version_id
        if dataset_versions
        else None
    )

    events = _bounded_anchor_rows(
        db,
        table=event_table,
        prefix="event",
        criteria=(event_table.c.connector_run_id == run_id,),
        max_rows=event_cap,
    )
    policy_snapshots = _bounded_anchor_rows(
        db,
        table=policy_table,
        prefix="policy",
        criteria=(policy_table.c.connector_run_id == run_id,),
        max_rows=policy_cap,
    )
    linkages = _bounded_anchor_rows(
        db,
        table=linkage_table,
        prefix="linkage",
        criteria=(
            linkage_table.c.run_id == run_id,
            linkage_table.c.target_id == anchored_target_id,
        ),
        max_rows=_SINGLE_ORIGIN_ROW_CAP,
    )
    provenances = _bounded_anchor_rows(
        db,
        table=provenance_table,
        prefix="provenance",
        criteria=(
            provenance_table.c.connector_run_id == run_id,
            (
                provenance_table.c.dataset_version_id == version_id
                if version_id is not None
                else false()
            ),
        ),
        max_rows=_SINGLE_ORIGIN_ROW_CAP,
    )
    intakes = _bounded_anchor_rows(
        db,
        table=intake_table,
        prefix="intake",
        criteria=(
            intake_table.c.connector_run_id == run_id,
            intake_table.c.connector_run_target_id
            == anchored_target_id,
        ),
        max_rows=_SINGLE_ORIGIN_ROW_CAP,
    )
    if (
        sum(
            row.materialize(ConnectorRunEvent).event_type
            == "campaign_log_capture_sealed"
            for row in events
        )
        > 1
    ):
        _fail(
            "layer3_origin_seal_event_cardinality",
            "Origin authority permits at most one campaign log-capture seal event.",
        )
    return _OriginAnchor(
        target=target,
        run=run,
        events=events,
        policy_snapshots=policy_snapshots,
        linkages=linkages,
        dataset_versions=dataset_versions,
        provenances=provenances,
        intakes=intakes,
    )


def _require_anchor_unchanged(
    db: Session,
    *,
    target_id: str,
    expected: _OriginAnchor,
) -> None:
    # Additive reads plus this full recollect detect sustained drift only;
    # they are not a one-statement snapshot and do not detect ABA changes.
    try:
        current = _read_origin_anchor(db, target_id=target_id)
    except Layer3OriginContinuityError as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_authority_drift",
            "Origin authority changed before verification completed.",
        ) from exc
    if current != expected:
        _fail(
            "layer3_origin_authority_drift",
            "Origin authority changed before verification completed.",
        )


def _same_storage_reference(left: object, right: object) -> bool:
    left_text = str(left or "").strip()
    right_text = str(right or "").strip()
    if not left_text or not right_text:
        return False
    try:
        return Path(left_text).resolve() == Path(right_text).resolve()
    except OSError:
        return left_text == right_text


def _fixture_root() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "tests"
        / "fixtures"
        / "nrc_aps_docs"
        / "v1"
    ).resolve()


def _raw_storage_path(
    storage_ref: object,
    *,
    allow_fixed_fixture: bool = False,
) -> Path:
    raw_ref = _required_text(storage_ref, field="raw_storage_ref")
    raw_root = Path(settings.connector_raw_dir).resolve()
    candidate = Path(raw_ref)
    if not candidate.is_absolute():
        candidate = raw_root / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_raw_blob_missing",
            "The connector-origin raw blob does not exist.",
        ) from exc
    admitted_fixture = (
        allow_fixed_fixture
        and resolved.parent == _fixture_root()
        and resolved.name == _FIXTURE_FILE_NAME
    )
    if (
        resolved != raw_root
        and raw_root not in resolved.parents
        and not admitted_fixture
    ):
        _fail(
            "layer3_origin_storage_ref_not_admitted",
            "The raw storage reference escapes connector raw storage.",
        )
    if not resolved.is_file():
        _fail(
            "layer3_origin_raw_blob_missing",
            "The connector-origin raw blob is not a regular file.",
        )
    return resolved


def _hash_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        path_before = path.stat()
        with path.open("rb") as handle:
            opened_before = os.fstat(handle.fileno())
            if (
                opened_before.st_dev != path_before.st_dev
                or opened_before.st_ino != path_before.st_ino
            ):
                _fail(
                    "layer3_origin_raw_blob_changed",
                    "The raw blob changed while it was being opened.",
                )
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
            opened_after = os.fstat(handle.fileno())
        path_after = path.stat()
    except OSError as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_raw_blob_changed",
            "The raw blob changed while it was being hashed.",
        ) from exc
    stable_identity = (
        opened_before.st_dev,
        opened_before.st_ino,
        opened_before.st_size,
        opened_before.st_mtime_ns,
    )
    if stable_identity != (
        opened_after.st_dev,
        opened_after.st_ino,
        opened_after.st_size,
        opened_after.st_mtime_ns,
    ) or stable_identity != (
        path_after.st_dev,
        path_after.st_ino,
        path_after.st_size,
        path_after.st_mtime_ns,
    ):
        _fail(
            "layer3_origin_raw_blob_changed",
            "The raw blob changed while it was being hashed.",
        )
    if size != opened_after.st_size:
        _fail(
            "layer3_origin_raw_blob_changed",
            "The raw blob byte count changed while it was being hashed.",
        )
    if size <= 0:
        _fail(
            "layer3_origin_raw_blob_empty",
            "Connector-origin continuity rejects an empty raw blob.",
        )
    return size, digest.hexdigest()


def _compute_arming_fingerprint(envelope: Mapping[str, Any]) -> str:
    return str(compute_arming_fingerprint(envelope))


def _resolve_historical_evidence(
    **kwargs: str,
) -> VerifiedHistoricalGrantEvidence:
    return resolve_historical_connector_grant_evidence(**kwargs)


def _derive_terminal_ledger(
    authority: Any,
    connector_run_id: str,
    *,
    counter_path: Path,
) -> VerifiedTerminalRequestLedger:
    from app.services.connector_egress_transport import (
        derive_terminal_request_ledger,
    )

    return derive_terminal_request_ledger(
        authority,
        connector_run_id=connector_run_id,
        counter_path=counter_path,
    )


def _assert_counter_path_no_reparse(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for part in parts:
        current = current / part
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise Layer3OriginContinuityError(
                "layer3_origin_counter_path_unavailable",
                "The protected HTTP counter path is unavailable.",
            ) from exc
        attrs = int(getattr(info, "st_file_attributes", 0))
        reparse_flag = int(
            getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        )
        if stat.S_ISLNK(info.st_mode) or attrs & reparse_flag:
            _fail(
                "layer3_origin_counter_path_reparse",
                "The protected HTTP counter path cannot contain a reparse point.",
            )


def _resolve_historical_counter_path(
    evidence: VerifiedHistoricalGrantEvidence,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
) -> Path:
    chain = _value(evidence, "index_chain")
    evidence_root = _value(chain, "evidence_root")
    head = _value(chain, "head")
    captures = _value(head, "log_captures")
    if (
        not isinstance(evidence_root, Path)
        or not evidence_root.is_absolute()
        or not isinstance(captures, Sequence)
        or isinstance(captures, (str, bytes))
    ):
        _fail(
            "layer3_origin_counter_authority_mismatch",
            "Historical evidence lacks one protected log-capture authority.",
        )
    matching = [
        capture
        for capture in captures
        if str(_value(capture, "campaign_id")) == campaign_id
        and _value(capture, "campaign_fingerprint")
        == campaign_fingerprint
    ]
    if len(matching) != 1:
        _fail(
            "layer3_origin_counter_authority_mismatch",
            "Historical evidence does not select one exact log capture.",
            details={"count": len(matching)},
        )
    capture = matching[0]
    expected_log_dir = f"logs/{campaign_fingerprint}"
    expected_manifest = f"{expected_log_dir}/manifest.json"
    expected_seal = f"log-seals/{campaign_fingerprint}.json"
    expected_streams = (
        "app.jsonl",
        "http.jsonl",
        "stdout.log",
        "stderr.log",
    )
    definition = _value(evidence, "definition_model")
    if (
        _value(capture, "campaign_definition_sha256")
        != _value(evidence, "raw_definition_sha256")
        or str(_value(capture, "code_revision"))
        != str(_value(definition, "code_revision"))
        or _value(capture, "log_dir_relative_path") != expected_log_dir
        or _value(capture, "manifest_relative_path") != expected_manifest
        or _value(capture, "seal_relative_path") != expected_seal
        or tuple(_value(capture, "expected_stream_files") or ())
        != expected_streams
    ):
        _fail(
            "layer3_origin_counter_authority_mismatch",
            "The historical log capture contradicts its campaign authority.",
        )

    root = evidence_root.absolute()
    candidate = root.joinpath(
        *PurePosixPath(expected_log_dir).parts,
        "http.jsonl",
    )
    _assert_counter_path_no_reparse(candidate)
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
        file_stat = os.stat(resolved, follow_symlinks=False)
    except OSError as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_counter_path_unavailable",
            "The protected HTTP counter path is unavailable.",
        ) from exc
    if (
        not resolved_root.is_dir()
        or resolved.parent != resolved_root / "logs" / campaign_fingerprint
        or not stat.S_ISREG(file_stat.st_mode)
    ):
        _fail(
            "layer3_origin_counter_path_mismatch",
            "The HTTP counter path does not equal the protected capture path.",
        )
    return resolved


def _load_sciencebase_bindings_from_anchor(
    *,
    anchor: _OriginAnchor,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    raw_sha256: str,
    raw_size: int,
) -> dict[str, str | None]:
    version_id = _required_text(
        target.dataset_version_id,
        field="dataset_version_id",
    )
    version = _one(
        [
            row.materialize(DatasetVersion)
            for row in anchor.dataset_versions
        ],
        code="layer3_origin_dataset_version_cardinality",
        label="dataset-version row",
    )
    if (
        version.dataset_version_id != version_id
        or version.dataset_id != target.dataset_id
    ):
        _fail(
            "layer3_origin_dataset_version_mismatch",
            "The target dataset version relationship is missing or contradictory.",
        )
    if _normalized_sha256(
        version.content_hash,
        field="DatasetVersion.content_hash",
    ) != raw_sha256:
        _fail(
            "layer3_origin_dataset_version_hash_mismatch",
            "DatasetVersion.content_hash does not equal the raw-byte hash.",
        )
    provenance = _one(
        [
            row.materialize(DatasetSourceProvenance)
            for row in anchor.provenances
        ],
        code="layer3_origin_provenance_cardinality",
        label="dataset source-provenance row",
    )
    if (
        _normalized_sha256(
            provenance.downloaded_sha256,
            field="DatasetSourceProvenance.downloaded_sha256",
        )
        != raw_sha256
        or provenance.source_artifact_key != target.source_artifact_key
        or provenance.sciencebase_item_id != target.sciencebase_item_id
        or provenance.sciencebase_file_name != target.sciencebase_file_name
        or not _same_storage_reference(
            provenance.raw_storage_ref,
            target.raw_storage_ref,
        )
    ):
        _fail(
            "layer3_origin_provenance_mismatch",
            "Dataset source provenance contradicts the connector target.",
        )

    intake = _one(
        [
            row.materialize(L3ConnectorSourceIntakeRecord)
            for row in anchor.intakes
        ],
        code="layer3_origin_source_intake_cardinality",
        label="connector source-intake row",
    )
    if (
        intake.connector_key != run.connector_key
        or intake.content_sha256 != raw_sha256
        or intake.content_size_bytes != raw_size
        or intake.original_filename != target.sciencebase_file_name
        or not _same_storage_reference(intake.storage_ref, target.raw_storage_ref)
    ):
        _fail(
            "layer3_origin_source_intake_mismatch",
            "Connector source intake contradicts the connector target bytes.",
        )
    return {
        "dataset_id": str(version.dataset_id),
        "dataset_version_id": str(version.dataset_version_id),
        "dataset_source_provenance_id": str(
            provenance.dataset_source_provenance_id
        ),
        "connector_source_intake_record_id": str(
            intake.connector_source_intake_record_id
        ),
        "aps_content_linkage_id": None,
        "content_id": None,
    }


def _load_sciencebase_bindings(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    raw_sha256: str,
    raw_size: int,
) -> dict[str, str | None]:
    """Compatibility boundary backed by one caller-connection Core anchor."""
    with db.no_autoflush:
        target_id = _required_text(
            target.connector_run_target_id,
            field="connector_run_target_id",
        )
        anchor = _read_origin_anchor(db, target_id=target_id)
        anchored_run = anchor.run.materialize(ConnectorRun)
        anchored_target = anchor.target.materialize(ConnectorRunTarget)
        if (
            anchored_run.connector_run_id != run.connector_run_id
            or anchored_target.connector_run_target_id != target_id
        ):
            _fail(
                "layer3_origin_anchor_mismatch",
                "Caller bindings do not identify the captured origin anchor.",
            )
        bindings = _load_sciencebase_bindings_from_anchor(
            anchor=anchor,
            run=anchored_run,
            target=anchored_target,
            raw_sha256=raw_sha256,
            raw_size=raw_size,
        )
        _require_anchor_unchanged(
            db,
            target_id=target_id,
            expected=anchor,
        )
        return bindings


def _load_nrc_bindings(
    *,
    anchor: _OriginAnchor,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    raw_sha256: str,
    raw_size: int,
    require_custody: bool,
) -> dict[str, str | None]:
    linkage = _one(
        [
            row.materialize(ApsContentLinkage)
            for row in anchor.linkages
        ],
        code="layer3_origin_aps_linkage_cardinality",
        label="APS content-linkage row",
    )
    accession = _required_text(
        linkage.accession_number,
        field="ApsContentLinkage.accession_number",
    )
    if (
        accession != _FIXTURE_ACCESSION
        or target.stable_release_key != accession
        or _normalized_sha256(
            linkage.blob_sha256,
            field="ApsContentLinkage.blob_sha256",
        )
        != raw_sha256
        or not _same_storage_reference(
            linkage.blob_ref,
            target.raw_storage_ref,
        )
    ):
        _fail(
            "layer3_origin_aps_linkage_mismatch",
            "APS content linkage contradicts the connector target bytes.",
        )
    if require_custody:
        source_reference = target.source_reference_json
        marker = (
            source_reference.get(
                nrc_phase_b_custody.CUSTODY_STORAGE_KEY
            )
            if isinstance(source_reference, Mapping)
            else None
        )
        try:
            nrc_phase_b_custody.require_exact_custody_marker(
                marker,
                status=nrc_phase_b_custody.VERIFIED,
                connector_run_id=run.connector_run_id,
                connector_run_target_id=target.connector_run_target_id,
                aps_content_linkage_id=linkage.aps_content_linkage_id,
                content_id=linkage.content_id,
                blob_ref=str(linkage.blob_ref or ""),
                blob_sha256=str(linkage.blob_sha256 or ""),
                blob_size_bytes=raw_size,
            )
        except nrc_phase_b_custody.NrcPhaseBCustodyMarkerError as exc:
            raise Layer3OriginContinuityError(
                "layer3_origin_nrc_custody_ineligible",
                "NRC origin requires one exact verified Phase-B custody marker.",
            ) from exc
    return {
        "dataset_id": None,
        "dataset_version_id": None,
        "dataset_source_provenance_id": None,
        "connector_source_intake_record_id": None,
        "aps_content_linkage_id": str(linkage.aps_content_linkage_id),
        "content_id": _required_text(
            linkage.content_id,
            field="ApsContentLinkage.content_id",
        ),
    }


def _verify_committed_nrc_phase_b(
    db: Session,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    bindings: Mapping[str, str | None],
    raw_path: Path,
    raw_sha256: str,
    raw_size: int,
) -> None:
    from app.services import nrc_aps_phase_b_linkage

    try:
        verified = (
            nrc_aps_phase_b_linkage
            .verify_strict_nrc_phase_b_linkage(
                db,
                connector_run_target_id=(
                    target.connector_run_target_id
                ),
            )
        )
    except nrc_aps_phase_b_linkage.NrcPhaseBLinkageError as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_nrc_phase_b_invalid",
            "NRC origin requires independently verified committed Phase-B authority.",
        ) from exc
    if (
        verified.connector_run_id != run.connector_run_id
        or verified.connector_run_target_id
        != target.connector_run_target_id
        or verified.aps_content_linkage_id
        != bindings["aps_content_linkage_id"]
        or verified.content_id != bindings["content_id"]
        or not _same_storage_reference(
            verified.raw_storage_ref,
            raw_path,
        )
        or verified.raw_content_sha256 != raw_sha256
        or verified.raw_content_size_bytes != raw_size
    ):
        _fail(
            "layer3_origin_nrc_phase_b_mismatch",
            "Committed Phase-B verification contradicts caller-current origin authority.",
        )


def _strict_json_object(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        parsed = strict_json_loads(raw)
    except (TypeError, ValueError) as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_fixture_manifest_invalid",
            f"{label} is not strict canonical evidence.",
        ) from exc
    if not isinstance(parsed, dict):
        _fail(
            "layer3_origin_fixture_manifest_invalid",
            f"{label} root must be an object.",
        )
    return parsed


def _derive_offline_fixture_bindings(
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    raw_path: Path,
    raw_sha256: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    if (
        run.connector_key != "nrc_adams_aps"
        or run.source_mode != OFFLINE_FIXTURE_PROOF_CLASS
        or raw_path.resolve() != (_fixture_root() / _FIXTURE_FILE_NAME)
        or target.stable_release_key != _FIXTURE_ACCESSION
    ):
        _fail(
            "layer3_origin_fixture_source_not_admitted",
            "offline_fixture requires the one fixed manifest-bound NRC source.",
        )
    config = run.request_config_json
    if isinstance(config, Mapping) and config.get("connector_egress_arming") is not None:
        _fail(
            "layer3_origin_fixture_has_strict_arming",
            "A fixed offline fixture cannot carry a strict live arming.",
        )
    manifest_path = _fixture_root() / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
    except OSError as exc:
        raise Layer3OriginContinuityError(
            "layer3_origin_fixture_manifest_missing",
            "The fixed fixture manifest is unavailable.",
        ) from exc
    manifest = _strict_json_object(
        manifest_bytes,
        label="NRC fixture manifest",
    )
    entries = manifest.get("entries")
    if (
        manifest.get("schema_id") != "aps.document_corpus_manifest.v2"
        or not isinstance(entries, list)
    ):
        _fail(
            "layer3_origin_fixture_manifest_invalid",
            "The fixed fixture manifest schema is not admitted.",
        )
    matches = [
        entry
        for entry in entries
        if isinstance(entry, Mapping)
        and entry.get("fixture_id") == _FIXTURE_ID
        and entry.get("path") == _FIXTURE_FILE_NAME
        and entry.get("declared_content_type") == "application/pdf"
    ]
    if len(matches) != 1:
        _fail(
            "layer3_origin_fixture_manifest_invalid",
            "The fixed fixture must have exactly one manifest entry.",
            details={"count": len(matches)},
        )
    return (
        {
            "campaign_id": None,
            "campaign_fingerprint": None,
            "campaign_definition_sha256": None,
            "campaign_introduction_index_revision": None,
            "campaign_introduction_index_sha256": None,
            "arming_fingerprint": None,
            "grant_sha256": None,
            "canonical_grant_fingerprint": None,
            "grant_consumption_marker_sha256": None,
            "ledger_terminal_hash": None,
            "fixture_id": _FIXTURE_ID,
            "fixture_manifest_ref": _FIXTURE_MANIFEST_REF,
            "fixture_manifest_sha256": hashlib.sha256(
                manifest_bytes
            ).hexdigest(),
            "fixture_source_sha256": raw_sha256,
        },
        {"accession_number": _FIXTURE_ACCESSION},
    )


def _canonical_authority_fields(
    evidence: VerifiedHistoricalGrantEvidence,
) -> dict[str, Any]:
    grant = _value(evidence, "model")
    definition = _value(evidence, "definition_model")
    return canonical_arming_payload(
        {
            "schema_id": STRICT_ARMING_SCHEMA_ID,
            "connector_key": _value(grant, "connector_key"),
            "campaign_id": str(_value(grant, "campaign_id")),
            "campaign_definition_sha256": _value(
                evidence,
                "raw_definition_sha256",
            ),
            "campaign_fingerprint": _value(
                evidence,
                "canonical_campaign_fingerprint",
            ),
            "grant_sha256": _value(evidence, "raw_sha256"),
            "canonical_grant_fingerprint": _value(
                evidence,
                "canonical_fingerprint",
            ),
            "campaign_introduction_index_revision": _value(
                evidence,
                "introduction_index_revision",
            ),
            "campaign_introduction_index_sha256": _value(
                evidence,
                "introduction_index_sha256",
            ),
            "code_revision": _value(grant, "code_revision"),
            "grant_id": _value(grant, "grant_id"),
            "arming_nonce": _value(grant, "arming_nonce"),
            "max_armings": _value(grant, "max_armings"),
            "supersedes_grant_sha256": _value(
                grant,
                "supersedes_grant_sha256",
            ),
            "operator_mode": _value(grant, "operator_mode"),
            "non_authorities": _value(grant, "non_authorities"),
            "max_physical_requests": _value(
                grant,
                "max_physical_requests",
            ),
            "max_run_bytes": _value(grant, "max_run_bytes"),
            "max_single_send_detection_allowance_bytes": _value(
                grant,
                "max_single_send_detection_allowance_bytes",
            ),
            "request_timeout_seconds": _value(
                grant,
                "request_timeout_seconds",
            ),
            "min_request_interval_ms": _value(
                grant,
                "min_request_interval_ms",
            ),
            "target": _value(grant, "target"),
            "request_rules": _value(grant, "request_rules"),
            "grant_issued_at": _value(grant, "issued_at"),
            "grant_expires_at": _value(grant, "expires_at"),
            "campaign_not_before": _value(definition, "not_before"),
            "campaign_expires_at": _value(definition, "expires_at"),
        }
    )


def _validate_authorization_receipt_binding(
    envelope: Mapping[str, Any],
    *,
    expected: Mapping[str, Any],
) -> None:
    receipt = envelope.get("authorization_receipt")
    if not isinstance(receipt, Mapping):
        _fail(
            "layer3_origin_authority_binding_mismatch",
            "The strict arming lacks its server-derived authorization receipt.",
            details={"field": "authorization_receipt"},
        )
    binding_values = {
        "schema_id": "project6.connector_egress_authorization_receipt.v1",
        "connector_key": expected["connector_key"],
        "campaign_id": expected["campaign_id"],
        "campaign_fingerprint": expected["campaign_fingerprint"],
        "campaign_definition_sha256": expected[
            "campaign_definition_sha256"
        ],
        "grant_sha256": expected["grant_sha256"],
        "canonical_grant_fingerprint": expected[
            "canonical_grant_fingerprint"
        ],
        "introduction_index_revision": expected[
            "campaign_introduction_index_revision"
        ],
        "introduction_index_sha256": expected[
            "campaign_introduction_index_sha256"
        ],
        "access": "write",
    }
    variable_fields = {
        "operator_ref_hash",
        "workspace_ref_hash",
        "auth_owner_mode",
        "authorization_mode",
        "role",
    }
    if set(receipt) != set(binding_values) | variable_fields:
        _fail(
            "layer3_origin_authority_binding_mismatch",
            "The authorization receipt has missing or undeclared fields.",
            details={"field": "authorization_receipt"},
        )
    for field, expected_value in binding_values.items():
        if receipt.get(field) != expected_value:
            _fail(
                "layer3_origin_authority_binding_mismatch",
                "The authorization receipt contradicts protected authority.",
                details={"field": f"authorization_receipt.{field}"},
            )
    for field in ("operator_ref_hash", "workspace_ref_hash"):
        normalized = _normalized_sha256(
            receipt.get(field),
            field=f"authorization_receipt.{field}",
        )
        if receipt.get(field) != normalized:
            _fail(
                "layer3_origin_authority_binding_mismatch",
                "The authorization receipt hash is not canonical.",
                details={"field": f"authorization_receipt.{field}"},
            )
    _required_text(
        receipt.get("auth_owner_mode"),
        field="authorization_receipt.auth_owner_mode",
    )
    authorization_mode = receipt.get("authorization_mode")
    role = receipt.get("role")
    if (
        authorization_mode == "identity_presence"
        and role is not None
    ) or (
        authorization_mode == "role_enforcing"
        and role != "owner"
    ) or authorization_mode not in {"identity_presence", "role_enforcing"}:
        _fail(
            "layer3_origin_authority_binding_mismatch",
            "The authorization receipt owner posture is contradictory.",
            details={"field": "authorization_receipt.authorization_mode"},
        )


def _validate_full_authority_binding(
    *,
    connector_key: str,
    envelope: Mapping[str, Any],
    evidence: VerifiedHistoricalGrantEvidence,
) -> dict[str, str]:
    expected = _canonical_authority_fields(evidence)
    for field, expected_value in expected.items():
        if envelope.get(field) != expected_value:
            _fail(
                "layer3_origin_authority_binding_mismatch",
                "Protected authority does not equal the immutable arming.",
                details={"field": field},
            )
    _validate_authorization_receipt_binding(
        envelope,
        expected=expected,
    )
    allowed_fields = set(expected) | {
        "arming_fingerprint",
        "authorization_receipt",
    }
    predecessor_bindings: dict[str, str] = {}
    predecessor_fields = {
        "predecessor_nrc_connector_run_id",
        "predecessor_nrc_ledger_terminal_hash",
    }
    if connector_key == "sciencebase_mcs":
        predecessor_bindings = {
            "predecessor_nrc_connector_run_id": _required_text(
                envelope.get("predecessor_nrc_connector_run_id"),
                field="predecessor_nrc_connector_run_id",
            ),
            "predecessor_nrc_ledger_terminal_hash": _normalized_sha256(
                envelope.get("predecessor_nrc_ledger_terminal_hash"),
                field="predecessor_nrc_ledger_terminal_hash",
            ),
        }
        allowed_fields |= predecessor_fields
    elif predecessor_fields & set(envelope):
        _fail(
            "layer3_origin_authority_binding_mismatch",
            "NRC arming cannot claim an NRC predecessor.",
            details={"field": "predecessor_nrc_connector_run_id"},
        )
    if set(envelope) != allowed_fields:
        _fail(
            "layer3_origin_authority_binding_mismatch",
            "The strict arming has missing or undeclared fields.",
            details={"field": "connector_egress_arming"},
        )
    return predecessor_bindings


_PATH_CLASS_BY_RULE = {
    "sciencebase_item_exact_v1": "sciencebase_item_exact",
    "sciencebase_file_exact_v1": "sciencebase_file_exact",
    "nrc_get_document_exact_v1": "nrc_accession_exact",
    "nrc_public_pdf_exact_v1": "nrc_public_pdf_exact",
}
_QUERY_CLASS_BY_RULE = {
    "format_json_exact_v1": "format_json_exact",
    "sciencebase_exact_file_selector_v1": (
        "exact_single_f_expected_filename"
    ),
    "none_v1": "none",
}


def _validate_terminal_request_identities(
    entries: Sequence[Mapping[str, Any]],
    *,
    grant: object,
) -> None:
    canonical = canonical_arming_payload(
        {"request_rules": _value(grant, "request_rules")}
    )
    rules = canonical.get("request_rules")
    if not isinstance(rules, list):
        _fail(
            "layer3_origin_terminal_request_identity_mismatch",
            "Protected grant request rules are not canonical.",
        )
    for entry in entries:
        ordinal = entry.get("ordinal")
        stage = entry.get("stage")
        matches = [
            rule
            for rule in rules
            if isinstance(rule, Mapping)
            and rule.get("ordinal") == ordinal
            and rule.get("stage") == stage
        ]
        if len(matches) != 1:
            _fail(
                "layer3_origin_terminal_request_identity_mismatch",
                "A terminal request does not select one protected grant rule.",
                details={"ordinal": ordinal, "stage": stage},
            )
        rule = matches[0]
        allowed_hosts = rule.get("allowed_hosts")
        expected_identity = {
            "method": rule.get("method"),
            "path_class": _PATH_CLASS_BY_RULE.get(
                str(rule.get("path_rule_id"))
            ),
            "query_class": _QUERY_CLASS_BY_RULE.get(
                str(rule.get("query_rule_id"))
            ),
            "credential_audience": rule.get("credential_audience"),
        }
        if (
            not isinstance(allowed_hosts, list)
            or entry.get("host") not in allowed_hosts
            or any(
                entry.get(field) != expected_value
                for field, expected_value in expected_identity.items()
            )
        ):
            _fail(
                "layer3_origin_terminal_request_identity_mismatch",
                "A terminal request identity contradicts its protected grant rule.",
                details={"ordinal": ordinal, "stage": stage},
            )
        fingerprint = _normalized_sha256(
            entry.get("request_fingerprint"),
            field=f"ledger.request_fingerprint.{ordinal}",
        )
        if entry.get("request_fingerprint") != fingerprint:
            _fail(
                "layer3_origin_terminal_request_identity_mismatch",
                "A terminal request fingerprint is not canonical.",
                details={"ordinal": ordinal, "stage": stage},
            )
        byte_count = entry.get("byte_count")
        max_response_bytes = _positive_int(
            rule.get("max_response_bytes"),
            field=f"request_rule.max_response_bytes.{ordinal}",
        )
        if (
            isinstance(byte_count, bool)
            or not isinstance(byte_count, int)
            or byte_count < 0
            or byte_count > max_response_bytes
        ):
            _fail(
                "layer3_origin_terminal_request_identity_mismatch",
                "A terminal response exceeds or contradicts its protected rule.",
                details={"ordinal": ordinal, "stage": stage},
            )


def _validate_target_against_grant(
    *,
    connector_key: str,
    target: ConnectorRunTarget,
    grant_target: object,
) -> dict[str, str]:
    if connector_key == "sciencebase_mcs":
        item_id = _required_text(
            target.sciencebase_item_id,
            field="sciencebase_item_id",
        )
        file_name = _required_text(
            target.sciencebase_file_name,
            field="sciencebase_file_name",
        )
        if (
            _value(grant_target, "connector_key") != connector_key
            or _value(grant_target, "item_id") != item_id
            or _value(grant_target, "exact_file_name") != file_name
        ):
            _fail(
                "layer3_origin_target_identity_mismatch",
                "The ScienceBase target does not equal the protected grant target.",
            )
        return {"item_id": item_id, "exact_file_name": file_name}
    if connector_key == "nrc_adams_aps":
        accession = _required_text(
            target.stable_release_key,
            field="target accession_number",
        )
        if (
            _value(grant_target, "connector_key") != connector_key
            or _value(grant_target, "accession_number") != accession
        ):
            _fail(
                "layer3_origin_target_identity_mismatch",
                "The NRC target does not equal the protected grant target.",
            )
        return {"accession_number": accession}
    _fail(
        "layer3_origin_connector_not_implemented",
        "This connector-origin branch is not implemented.",
    )


def _validate_fresh_live_evidence(
    ledger_authority: _FrozenLedgerAuthority,
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    envelope: Mapping[str, Any],
    raw_sha256: str,
    raw_size: int,
) -> tuple[dict[str, Any], dict[str, str]]:
    if envelope.get("schema_id") != STRICT_ARMING_SCHEMA_ID:
        _fail(
            "layer3_origin_strict_arming_missing",
            "fresh_live requires the strict connector-egress arming schema.",
        )
    if envelope.get("connector_key") != run.connector_key:
        _fail(
            "layer3_origin_arming_connector_mismatch",
            "The strict arming connector does not match the run.",
        )
    stored_arming_hash = _normalized_sha256(
        envelope.get("arming_fingerprint"),
        field="arming_fingerprint",
    )
    if _compute_arming_fingerprint(envelope) != stored_arming_hash:
        _fail(
            "layer3_origin_arming_fingerprint_mismatch",
            "The strict arming fingerprint does not rederive.",
        )
    run_fingerprint = _normalized_sha256(
        run.request_fingerprint,
        field="ConnectorRun.request_fingerprint",
    )
    if run_fingerprint != stored_arming_hash:
        _fail(
            "layer3_origin_arming_fingerprint_mismatch",
            "The connector run fingerprint contradicts its strict arming.",
        )

    campaign_id = _required_text(
        envelope.get("campaign_id"),
        field="campaign_id",
    )
    campaign_fingerprint = _normalized_sha256(
        envelope.get("campaign_fingerprint"),
        field="campaign_fingerprint",
    )
    grant_sha256 = _normalized_sha256(
        envelope.get("grant_sha256"),
        field="grant_sha256",
    )
    evidence = _resolve_historical_evidence(
        connector_key=run.connector_key,
        campaign_id=campaign_id,
        expected_campaign_fingerprint=campaign_fingerprint,
        expected_grant_sha256=grant_sha256,
    )
    definition = _value(evidence, "definition_model")
    grant = _value(evidence, "model")
    marker = _value(evidence, "marker_model")
    predecessor_bindings = _validate_full_authority_binding(
        connector_key=run.connector_key,
        envelope=envelope,
        evidence=evidence,
    )
    expected_pairs = (
        ("campaign_definition_sha256", "raw_definition_sha256"),
        ("campaign_fingerprint", "canonical_campaign_fingerprint"),
        ("grant_sha256", "raw_sha256"),
        ("canonical_grant_fingerprint", "canonical_fingerprint"),
        (
            "campaign_introduction_index_revision",
            "introduction_index_revision",
        ),
        (
            "campaign_introduction_index_sha256",
            "introduction_index_sha256",
        ),
    )
    for envelope_field, evidence_field in expected_pairs:
        if str(envelope.get(envelope_field)) != str(
            _value(evidence, evidence_field)
        ):
            _fail(
                "layer3_origin_authority_binding_mismatch",
                "Protected evidence does not equal the immutable arming binding.",
                details={"field": envelope_field},
            )
    if (
        str(_value(definition, "campaign_id")) != campaign_id
        or str(_value(grant, "campaign_id")) != campaign_id
        or _value(grant, "connector_key") != run.connector_key
        or str(_value(grant, "code_revision"))
        != str(envelope.get("code_revision"))
        or str(_value(definition, "code_revision"))
        != str(envelope.get("code_revision"))
    ):
        _fail(
            "layer3_origin_authority_document_mismatch",
            "Definition or grant identity contradicts the arming.",
        )
    if (
        str(_value(marker, "connector_run_id")) != run.connector_run_id
        or _value(marker, "connector_key") != run.connector_key
        or str(_value(marker, "campaign_id")) != campaign_id
        or str(_value(marker, "raw_grant_sha256")) != grant_sha256
    ):
        _fail(
            "layer3_origin_consumption_marker_mismatch",
            "The indexed one-use consumption marker contradicts the run.",
        )
    target_identity = _validate_target_against_grant(
        connector_key=run.connector_key,
        target=target,
        grant_target=_value(grant, "target"),
    )

    counter_path = _resolve_historical_counter_path(
        evidence,
        campaign_id=campaign_id,
        campaign_fingerprint=campaign_fingerprint,
    )
    ledger = _derive_terminal_ledger(
        ledger_authority,
        run.connector_run_id,
        counter_path=counter_path,
    )
    if _value(ledger, "eligible") is not True:
        _fail(
            "layer3_origin_terminal_ledger_ineligible",
            "fresh_live requires a complete eligible terminal request ledger.",
        )
    projection = _value(ledger, "canonical_projection")
    if not isinstance(projection, Mapping):
        _fail(
            "layer3_origin_terminal_ledger_invalid",
            "The terminal ledger lacks a canonical projection.",
        )
    projection_dict = dict(projection)
    ledger_hash = _normalized_sha256(
        _value(ledger, "ledger_terminal_hash"),
        field="ledger_terminal_hash",
    )
    if _stable_hash(projection_dict) != ledger_hash:
        _fail(
            "layer3_origin_terminal_ledger_hash_mismatch",
            "The terminal-ledger hash does not rederive.",
        )
    for field, expected in (
        ("schema_id", TERMINAL_LEDGER_SCHEMA_ID),
        ("connector_run_id", run.connector_run_id),
        ("connector_key", run.connector_key),
        ("campaign_fingerprint", campaign_fingerprint),
        ("arming_fingerprint", stored_arming_hash),
        ("grant_sha256", grant_sha256),
        (
            "campaign_introduction_index_revision",
            envelope.get("campaign_introduction_index_revision"),
        ),
        (
            "campaign_introduction_index_sha256",
            envelope.get("campaign_introduction_index_sha256"),
        ),
        (
            "frozen_max_physical_requests",
            envelope.get("max_physical_requests"),
        ),
    ):
        if projection_dict.get(field) != expected:
            _fail(
                "layer3_origin_terminal_ledger_binding_mismatch",
                "The terminal ledger contradicts the strict arming.",
                details={"field": field},
            )
    entries = projection_dict.get("entries")
    if not isinstance(entries, list) or entries != list(
        _value(ledger, "entries") or ()
    ):
        _fail(
            "layer3_origin_terminal_ledger_invalid",
            "The terminal ledger entries are not canonical.",
        )
    if not all(isinstance(item, Mapping) for item in entries):
        _fail(
            "layer3_origin_terminal_ledger_invalid",
            "The terminal ledger contains a non-object entry.",
        )
    typed_entries = [dict(item) for item in entries]
    actual_sequence = [
        (item.get("ordinal"), item.get("stage"))
        for item in typed_entries
    ]
    admitted_sequences = (
        (
            ((1, "item_hydration"), (2, "artifact")),
            (
                (1, "item_hydration"),
                (2, "artifact"),
                (3, "artifact_redirect"),
            ),
        )
        if run.connector_key == "sciencebase_mcs"
        else (((1, "exact_accession_api"), (2, "artifact")),)
    )
    if tuple(actual_sequence) not in admitted_sequences:
        _fail(
            "layer3_origin_request_sequence_mismatch",
            "The terminal ledger has the wrong physical-send sequence.",
        )
    _validate_terminal_request_identities(
        typed_entries,
        grant=grant,
    )
    if (
        run.connector_key == "sciencebase_mcs"
        and len(typed_entries) == 3
        and typed_entries[1].get("response_status")
        not in {301, 302, 303, 307, 308}
    ):
        _fail(
            "layer3_origin_redirect_sequence_mismatch",
            "A ScienceBase redirect send requires an admitted redirect response.",
        )
    artifact = typed_entries[-1]
    if (
        artifact.get("outcome_class") != "completed"
        or artifact.get("response_status") != 200
        or artifact.get("byte_count") != raw_size
        or artifact.get("body_sha256") != raw_sha256
    ):
        _fail(
            "layer3_origin_artifact_completion_mismatch",
            "The terminal artifact completion does not equal admitted raw bytes.",
        )
    campaign_start = _as_utc(
        _value(definition, "not_before"),
        field="campaign.not_before",
    )
    campaign_end = _as_utc(
        _value(definition, "expires_at"),
        field="campaign.expires_at",
    )
    grant_start = _as_utc(_value(grant, "issued_at"), field="grant.issued_at")
    grant_end = _as_utc(_value(grant, "expires_at"), field="grant.expires_at")
    for entry in typed_entries:
        for field in ("reserved_at", "send_started_at"):
            timestamp = _as_utc(entry.get(field), field=f"ledger.{field}")
            if not (
                campaign_start <= timestamp < campaign_end
                and grant_start <= timestamp < grant_end
            ):
                _fail(
                    "layer3_origin_send_outside_authority_window",
                    "A physical-send timestamp is outside an original half-open window.",
                    details={"ordinal": entry.get("ordinal"), "field": field},
                )
    return (
        {
            "campaign_id": campaign_id,
            "campaign_fingerprint": campaign_fingerprint,
            "campaign_definition_sha256": str(
                envelope.get("campaign_definition_sha256")
            ),
            "campaign_introduction_index_revision": _positive_int(
                envelope.get("campaign_introduction_index_revision"),
                field="campaign_introduction_index_revision",
            ),
            "campaign_introduction_index_sha256": str(
                envelope.get("campaign_introduction_index_sha256")
            ),
            "arming_fingerprint": stored_arming_hash,
            "grant_sha256": grant_sha256,
            "canonical_grant_fingerprint": str(
                envelope.get("canonical_grant_fingerprint")
            ),
            "grant_consumption_marker_sha256": _normalized_sha256(
                _value(evidence, "consumption_marker_sha256"),
                field="grant_consumption_marker_sha256",
            ),
            "ledger_terminal_hash": ledger_hash,
            **predecessor_bindings,
        },
        target_identity,
    )


def _derive_connector_origin_receipt_from_anchor(
    db: Session,
    *,
    anchor: _OriginAnchor,
) -> dict[str, Any]:
    target = anchor.target.materialize(ConnectorRunTarget)
    run = anchor.run.materialize(ConnectorRun)
    if run.connector_key not in _ALLOWED_CONNECTORS:
        _fail(
            "layer3_origin_connector_not_admitted",
            "The connector is outside the dual-live origin contract.",
        )
    if run.status != "completed":
        _fail(
            "layer3_origin_run_not_completed",
            "fresh_live origin requires a completed strict connector run.",
            details={"status": run.status},
        )

    is_offline_fixture = (
        run.connector_key == "nrc_adams_aps"
        and run.source_mode == OFFLINE_FIXTURE_PROOF_CLASS
    )
    raw_path = _raw_storage_path(
        target.raw_storage_ref,
        allow_fixed_fixture=is_offline_fixture,
    )
    raw_size, raw_sha256 = _hash_file(raw_path)
    if (
        _normalized_sha256(
            target.downloaded_sha256,
            field="ConnectorRunTarget.downloaded_sha256",
        )
        != raw_sha256
    ):
        _fail(
            "layer3_origin_raw_hash_mismatch",
            "The raw bytes do not equal ConnectorRunTarget.downloaded_sha256.",
        )

    if run.connector_key == "sciencebase_mcs":
        content_bindings = _load_sciencebase_bindings_from_anchor(
            anchor=anchor,
            run=run,
            target=target,
            raw_sha256=raw_sha256,
            raw_size=raw_size,
        )
    else:
        content_bindings = _load_nrc_bindings(
            anchor=anchor,
            run=run,
            target=target,
            raw_sha256=raw_sha256,
            raw_size=raw_size,
            require_custody=not is_offline_fixture,
        )
        if not is_offline_fixture:
            _verify_committed_nrc_phase_b(
                db,
                run=run,
                target=target,
                bindings=content_bindings,
                raw_path=raw_path,
                raw_sha256=raw_sha256,
                raw_size=raw_size,
            )

    if not isinstance(run.request_config_json, Mapping):
        _fail(
            "layer3_origin_request_config_invalid",
            "Connector origin requires an object request configuration.",
        )
    request_config = run.request_config_json
    envelope = request_config.get("connector_egress_arming")
    if is_offline_fixture:
        authority_bindings, target_identity = (
            _derive_offline_fixture_bindings(
                run=run,
                target=target,
                raw_path=raw_path,
                raw_sha256=raw_sha256,
            )
        )
        proof_class = OFFLINE_FIXTURE_PROOF_CLASS
    else:
        if not isinstance(envelope, Mapping):
            _fail(
                "layer3_origin_strict_arming_missing",
                "The run lacks a strict server-derived arming envelope.",
            )
        authority_bindings, target_identity = _validate_fresh_live_evidence(
            _FrozenLedgerAuthority.from_anchor(anchor),
            run=run,
            target=target,
            envelope=envelope,
            raw_sha256=raw_sha256,
            raw_size=raw_size,
        )
        proof_class = FRESH_LIVE_PROOF_CLASS

    receipt: dict[str, Any] = {
        "schema_id": ORIGIN_RECEIPT_SCHEMA_ID,
        "proof_class": proof_class,
        "connector_key": run.connector_key,
        "connector_run_id": run.connector_run_id,
        "connector_run_target_id": target.connector_run_target_id,
        "target_identity": target_identity,
        "source_artifact_key": _required_text(
            target.source_artifact_key,
            field="source_artifact_key",
        ),
        "raw_storage_ref": str(target.raw_storage_ref),
        "raw_content_sha256": raw_sha256,
        "raw_content_size_bytes": raw_size,
        **content_bindings,
        **authority_bindings,
    }
    receipt["receipt_hash"] = _stable_hash(receipt)
    return receipt


def _require_caller_transaction(db: Session) -> None:
    transaction = db.get_transaction()
    if transaction is None or not transaction.is_active:
        _fail(
            "layer3_origin_caller_transaction_required",
            "Origin receipt operations require an active caller transaction.",
        )


def _prepare_caller_root_transaction(db: Session) -> None:
    bind = db.get_bind()
    if bind is None:
        _fail(
            "layer3_origin_caller_transaction_required",
            "Origin receipt operations require a bound caller transaction.",
        )
    if bind.dialect.name != "sqlite":
        return
    root = db.get_transaction()
    if root is None:
        _fail(
            "layer3_origin_caller_transaction_required",
            "Origin receipt operations require an active caller transaction.",
        )
    connection = root.connection(type_cast(Any, bind))
    nested_is_materialized = (
        db.in_nested_transaction()
        and connection.in_nested_transaction()
    )
    driver_connection = connection.connection.driver_connection
    if driver_connection is None:
        _fail(
            "layer3_origin_sqlite_nested_root_unverified",
            "SQLite origin verification requires a physical driver connection.",
        )
    if nested_is_materialized:
        if (
            connection.info.get(_SQLITE_ROOT_MARKER) is not root
            or not driver_connection.in_transaction
        ):
            _fail(
                "layer3_origin_sqlite_nested_root_unverified",
                "SQLite mint refuses an already-materialized nested transaction whose physical root cannot be proven.",
            )
        return
    if not driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN")
    connection.info[_SQLITE_ROOT_MARKER] = root


def _anchor_rows_by_model(
    anchor: _OriginAnchor,
) -> Mapping[type[Any], tuple[_AnchorRow, ...]]:
    return {
        ConnectorRunTarget: (anchor.target,),
        ConnectorRun: (anchor.run,),
        ConnectorRunEvent: anchor.events,
        ConnectorPolicySnapshot: anchor.policy_snapshots,
        ApsContentLinkage: anchor.linkages,
        DatasetVersion: anchor.dataset_versions,
        DatasetSourceProvenance: anchor.provenances,
        L3ConnectorSourceIntakeRecord: anchor.intakes,
    }


def _row_primary_identity(
    row: _AnchorRow,
    model: type[Any],
) -> tuple[Any, ...]:
    values = dict(row.values)
    return tuple(
        _thaw_anchor_value(values[column.key])
        for column in _model_table(model).primary_key
    )


def _instance_affects_anchor(
    instance: object,
    *,
    anchor: _OriginAnchor,
) -> bool:
    rows_by_model = _anchor_rows_by_model(anchor)
    model = type(instance)
    rows = rows_by_model.get(model)
    if rows is None:
        return False
    identity = tuple(
        getattr(instance, column.key, None)
        for column in _model_table(model).primary_key
    )
    if identity in {
        _row_primary_identity(row, model)
        for row in rows
    }:
        return True
    run = anchor.run.materialize(ConnectorRun)
    target = anchor.target.materialize(ConnectorRunTarget)
    run_id = run.connector_run_id
    target_id = target.connector_run_target_id
    version_ids = {
        row.materialize(DatasetVersion).dataset_version_id
        for row in anchor.dataset_versions
    }
    if isinstance(instance, ConnectorRun):
        return instance.connector_run_id == run_id
    if isinstance(
        instance,
        (ConnectorRunEvent, ConnectorPolicySnapshot),
    ):
        return instance.connector_run_id == run_id
    if isinstance(instance, ConnectorRunTarget):
        return (
            instance.connector_run_target_id == target_id
            or instance.connector_run_id == run_id
        )
    if isinstance(instance, ApsContentLinkage):
        return (
            instance.target_id == target_id
            or instance.run_id == run_id
        )
    if isinstance(instance, DatasetVersion):
        return instance.dataset_version_id in version_ids
    if isinstance(instance, DatasetSourceProvenance):
        return (
            instance.connector_run_id == run_id
            or instance.dataset_version_id in version_ids
        )
    if isinstance(instance, L3ConnectorSourceIntakeRecord):
        return (
            instance.connector_run_id == run_id
            or instance.connector_run_target_id == target_id
        )
    return False


def _reject_relevant_identity_map_state(
    db: Session,
    *,
    anchor: _OriginAnchor,
) -> None:
    for instance in tuple(db.new) + tuple(db.deleted):
        if _instance_affects_anchor(instance, anchor=anchor):
            _fail(
                "layer3_origin_identity_map_dirty",
                "Pending caller state affects connector-origin authority.",
            )
    for instance in tuple(db.dirty):
        if (
            db.is_modified(instance, include_collections=True)
            and _instance_affects_anchor(instance, anchor=anchor)
        ):
            _fail(
                "layer3_origin_identity_map_dirty",
                "Pending caller state affects connector-origin authority.",
            )


def _stored_origin_receipt(
    target: ConnectorRunTarget,
) -> dict[str, Any] | None:
    source_reference = target.source_reference_json
    if not isinstance(source_reference, Mapping):
        _fail(
            "layer3_origin_source_reference_invalid",
            "Connector target source_reference_json must be an object.",
        )
    for key, value in source_reference.items():
        if (
            key != ORIGIN_RECEIPT_STORAGE_KEY
            and isinstance(value, Mapping)
            and value.get("schema_id") == ORIGIN_RECEIPT_SCHEMA_ID
        ):
            _fail(
                "layer3_origin_duplicate_canonical_receipt",
                "The target carries more than one canonical origin receipt.",
            )
    hidden_source_reference = {
        key: value
        for key, value in source_reference.items()
        if key != ORIGIN_RECEIPT_STORAGE_KEY
    }
    if _origin_claims(hidden_source_reference):
        _fail(
            "layer3_origin_history_claim_malformed",
            "The current target carries a hidden origin claim.",
        )
    if ORIGIN_RECEIPT_STORAGE_KEY not in source_reference:
        return None
    stored = source_reference[ORIGIN_RECEIPT_STORAGE_KEY]
    if not isinstance(stored, Mapping):
        _fail(
            "layer3_origin_stored_receipt_invalid",
            "The canonical origin receipt slot is malformed.",
        )
    stored_dict = dict(stored)
    stored_hash = _normalized_sha256(
        stored_dict.get("receipt_hash"),
        field="stored receipt_hash",
    )
    preimage = {
        key: value
        for key, value in stored_dict.items()
        if key != "receipt_hash"
    }
    if _stable_hash(preimage) != stored_hash:
        _fail(
            "layer3_origin_stored_receipt_hash_mismatch",
            "The stored connector-origin receipt hash does not rederive.",
        )
    return stored_dict


def _origin_projection(
    receipt: Mapping[str, Any],
) -> dict[str, str]:
    return {
        "connector_run_target_id": _required_text(
            receipt.get("connector_run_target_id"),
            field="connector_run_target_id",
        ),
        "connector_origin_receipt_hash": _normalized_sha256(
            receipt.get("receipt_hash"),
            field="receipt_hash",
        ),
    }


def _sciencebase_phase_a_source_reference(
    *,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    raw_sha256: str,
) -> dict[str, str]:
    target_id = _required_text(
        target.connector_run_target_id,
        field="connector_run_target_id",
    )
    return {
        "schema_id": "project6.sciencebase_phase_a_provenance.v1",
        "connector_key": "sciencebase_mcs",
        "connector_run_target_id": target_id,
        "item_id": _required_text(
            target.sciencebase_item_id,
            field="sciencebase_item_id",
        ),
        "exact_file_name": _required_text(
            target.sciencebase_file_name,
            field="sciencebase_file_name",
        ),
        "artifact_surface": _required_text(
            target.artifact_surface,
            field="artifact_surface",
        ),
        "source_mode": _required_text(
            run.source_mode,
            field="source_mode",
        ),
        "raw_sha256": raw_sha256,
        "storage_class": "connector_raw_sha256",
    }


def _sciencebase_projection_rows(
    anchor: _OriginAnchor,
    *,
    receipt_hash: str,
    projection_present: bool,
) -> tuple[
    _AnchorRow,
    _AnchorRow,
    dict[str, Any],
]:
    from app.services import layer3_connector_source_intake

    run = anchor.run.materialize(ConnectorRun)
    target = anchor.target.materialize(ConnectorRunTarget)
    provenance_row = _one(
        list(anchor.provenances),
        code="layer3_origin_provenance_cardinality",
        label="dataset source-provenance row",
    )
    intake_row = _one(
        list(anchor.intakes),
        code="layer3_origin_source_intake_cardinality",
        label="connector source-intake row",
    )
    provenance = provenance_row.materialize(
        DatasetSourceProvenance
    )
    intake = intake_row.materialize(
        L3ConnectorSourceIntakeRecord
    )
    source_reference = provenance.source_reference_json
    if not isinstance(source_reference, Mapping):
        _fail(
            "layer3_origin_provenance_projection_invalid",
            "ScienceBase provenance projection must be an object.",
        )
    hidden_source_reference = {
        key: value
        for key, value in source_reference.items()
        if key != "connector_origin_receipt_hash"
    }
    if _origin_claims(hidden_source_reference):
        _fail(
            "layer3_origin_history_claim_malformed",
            "Current ScienceBase provenance carries a hidden origin claim.",
        )
    expected_source_reference = _sciencebase_phase_a_source_reference(
        run=run,
        target=target,
        raw_sha256=_normalized_sha256(
            provenance.downloaded_sha256,
            field="DatasetSourceProvenance.downloaded_sha256",
        ),
    )
    expected_projected_reference = dict(expected_source_reference)
    projected_hash = source_reference.get(
        "connector_origin_receipt_hash"
    )
    if projection_present:
        expected_projected_reference[
            "connector_origin_receipt_hash"
        ] = receipt_hash
    elif projected_hash is not None:
        _fail(
            "layer3_origin_candidate_already_consumed",
            "ScienceBase origin projection was consumed before canonical mint.",
        )
    if dict(source_reference) != expected_projected_reference:
        _fail(
            "layer3_origin_provenance_projection_mismatch",
            "ScienceBase provenance does not equal its exact Phase-A projection.",
        )
    if projection_present:
        if projected_hash != receipt_hash:
            _fail(
                "layer3_origin_provenance_projection_mismatch",
                "ScienceBase provenance does not carry the exact origin hash.",
            )
    expected_intake = (
        layer3_connector_source_intake
        ._strict_sciencebase_intake_values(
            connector_key=run.connector_key,
            connector_run_id=run.connector_run_id,
            connector_run_target_id=(
                target.connector_run_target_id
            ),
            raw_storage_ref=str(intake.storage_ref),
            freshness_timestamp=intake.freshness_timestamp,
            content_size_bytes=int(intake.content_size_bytes),
            content_sha256=str(intake.content_sha256),
            connector_origin_receipt_hash=(
                receipt_hash if projection_present else None
            ),
        )
    )
    if any(
        getattr(intake, field) != expected
        for field, expected in expected_intake.items()
    ):
        _fail(
            "layer3_origin_source_intake_projection_mismatch",
            "Strict ScienceBase intake projection is incomplete or contradictory.",
        )
    return provenance_row, intake_row, expected_intake


def _origin_claims(
    value: object,
) -> list[Mapping[str, Any] | None]:
    claims: list[Mapping[str, Any] | None] = []
    pending: list[tuple[object, int]] = [(value, 0)]
    visited = 0
    while pending:
        current, depth = pending.pop()
        visited += 1
        if (
            depth > _ORIGIN_CLAIM_DEPTH_CAP
            or visited > _ORIGIN_CLAIM_NODE_CAP
        ):
            _fail(
                "layer3_origin_history_claim_bounds_exceeded",
                "Origin-claim traversal exceeds its bounded history contract.",
                details={
                    "max_depth": _ORIGIN_CLAIM_DEPTH_CAP,
                    "max_nodes": _ORIGIN_CLAIM_NODE_CAP,
                },
            )
        if isinstance(current, Mapping):
            canonical = current.get(ORIGIN_RECEIPT_STORAGE_KEY)
            if ORIGIN_RECEIPT_STORAGE_KEY in current:
                claims.append(
                    canonical
                    if isinstance(canonical, Mapping)
                    else None
                )
            if (
                current.get("schema_id") == ORIGIN_RECEIPT_SCHEMA_ID
                or "connector_origin_receipt_hash" in current
            ):
                claims.append(current)
            nested_values = [
                nested
                for key, nested in current.items()
                if key != ORIGIN_RECEIPT_STORAGE_KEY
            ]
            pending.extend(
                (nested, depth + 1)
                for nested in reversed(nested_values)
            )
        elif isinstance(current, Sequence) and not isinstance(
            current,
            (str, bytes, bytearray),
        ):
            pending.extend(
                (nested, depth + 1)
                for nested in reversed(current)
            )
    return claims


def _claim_hash(
    claim: Mapping[str, Any] | None,
) -> str | None:
    if claim is None:
        return None
    if claim.get("schema_id") == ORIGIN_RECEIPT_SCHEMA_ID:
        raw_hash = claim.get("receipt_hash")
        if (
            not isinstance(raw_hash, str)
            or len(raw_hash) != 64
            or any(char not in _HEX for char in raw_hash)
        ):
            return None
        preimage = {
            key: value
            for key, value in claim.items()
            if key != "receipt_hash"
        }
        return (
            raw_hash
            if _stable_hash(preimage) == raw_hash
            else None
        )
    raw_hash = claim.get("connector_origin_receipt_hash")
    if (
        not isinstance(raw_hash, str)
        or len(raw_hash) != 64
        or any(char not in _HEX for char in raw_hash)
    ):
        return None
    return raw_hash


def _check_historical_claims(
    value: object,
    *,
    row_target_id: str | None,
    current_target_id: str,
    receipt_hash: str,
) -> None:
    for claim in _origin_claims(value):
        raw_target = (
            claim.get("connector_run_target_id")
            if isinstance(claim, Mapping)
            else None
        )
        explicit_target = (
            raw_target.strip()
            if isinstance(raw_target, str)
            and raw_target.strip()
            else None
        )
        if (
            explicit_target is not None
            and row_target_id is not None
            and explicit_target != row_target_id
        ):
            if current_target_id in {
                explicit_target,
                row_target_id,
            }:
                _fail(
                    "layer3_origin_history_claim_malformed",
                    "Historical origin claim contradicts target attribution.",
                )
            continue
        attributed_target = explicit_target or row_target_id
        if (
            attributed_target is not None
            and attributed_target != current_target_id
        ):
            continue
        if attributed_target is None:
            _fail(
                "layer3_origin_history_claim_malformed",
                "Historical origin claim is not attributable to a target.",
            )
        claimed_hash = _claim_hash(claim)
        if claimed_hash is None:
            _fail(
                "layer3_origin_history_claim_malformed",
                "Historical origin claim is malformed.",
            )
        if claimed_hash == receipt_hash:
            _fail(
                "layer3_origin_candidate_already_consumed",
                "The exact origin candidate was already consumed elsewhere.",
            )
        _fail(
            "layer3_origin_history_claim_malformed",
            "Historical origin claim conflicts with current target authority.",
        )


def _bounded_history_rows(
    db: Session,
    statement: Any,
    *,
    table_name: str,
) -> list[RowMapping]:
    rows = list(
        db.execute(
            statement.limit(_ORIGIN_HISTORY_ROW_CAP + 1)
        ).mappings().all()
    )
    if len(rows) > _ORIGIN_HISTORY_ROW_CAP:
        _fail(
            "layer3_origin_history_cardinality_exceeded",
            "Origin history exceeds its bounded row contract.",
            details={
                "table": table_name,
                "max_rows": _ORIGIN_HISTORY_ROW_CAP,
                "observed_at_least": _ORIGIN_HISTORY_ROW_CAP + 1,
            },
        )
    return rows


def _require_unconsumed_origin_history(
    db: Session,
    *,
    anchor: _OriginAnchor,
    receipt_hash: str,
) -> None:
    """Reject conflicting claims visible now, without phantom/serializability claims."""

    current_target = anchor.target.materialize(
        ConnectorRunTarget
    )
    current_target_id = current_target.connector_run_target_id
    own_provenance_ids = {
        row.materialize(
            DatasetSourceProvenance
        ).dataset_source_provenance_id
        for row in anchor.provenances
    }
    own_intake_ids = {
        row.materialize(
            L3ConnectorSourceIntakeRecord
        ).connector_source_intake_record_id
        for row in anchor.intakes
    }
    target_table = _model_table(ConnectorRunTarget)
    target_rows = _bounded_history_rows(
        db,
        select(
            target_table.c.connector_run_target_id,
            target_table.c.connector_run_id,
            target_table.c.dataset_version_id,
            target_table.c.source_reference_json,
        ),
        table_name=str(target_table.name),
    )
    provenance_targets: dict[
        tuple[str | None, str | None],
        set[str],
    ] = {}
    for row in target_rows:
        target_id = str(row["connector_run_target_id"])
        provenance_targets.setdefault(
            (
                row["connector_run_id"],
                row["dataset_version_id"],
            ),
            set(),
        ).add(target_id)
        if target_id != current_target_id:
            _check_historical_claims(
                row["source_reference_json"],
                row_target_id=target_id,
                current_target_id=current_target_id,
                receipt_hash=receipt_hash,
            )

    provenance_table = _model_table(DatasetSourceProvenance)
    provenance_rows = _bounded_history_rows(
        db,
        select(
            provenance_table.c.dataset_source_provenance_id,
            provenance_table.c.connector_run_id,
            provenance_table.c.dataset_version_id,
            provenance_table.c.source_reference_json,
        ),
        table_name=str(provenance_table.name),
    )
    for row in provenance_rows:
        provenance_id = str(
            row["dataset_source_provenance_id"]
        )
        if provenance_id in own_provenance_ids:
            continue
        candidates = provenance_targets.get(
            (
                row["connector_run_id"],
                row["dataset_version_id"],
            ),
            set(),
        )
        row_target_id = (
            next(iter(candidates))
            if len(candidates) == 1
            else None
        )
        _check_historical_claims(
            row["source_reference_json"],
            row_target_id=row_target_id,
            current_target_id=current_target_id,
            receipt_hash=receipt_hash,
        )

    intake_table = _model_table(L3ConnectorSourceIntakeRecord)
    intake_rows = _bounded_history_rows(
        db,
        select(
            intake_table.c.connector_source_intake_record_id,
            intake_table.c.connector_run_target_id,
            intake_table.c.provenance_json,
            intake_table.c.summary_json,
        ),
        table_name=str(intake_table.name),
    )
    for row in intake_rows:
        intake_id = str(
            row["connector_source_intake_record_id"]
        )
        if intake_id in own_intake_ids:
            continue
        raw_target_id = row["connector_run_target_id"]
        row_target_id = (
            str(raw_target_id)
            if raw_target_id is not None
            else None
        )
        for value in (
            row["provenance_json"],
            row["summary_json"],
        ):
            _check_historical_claims(
                value,
                row_target_id=row_target_id,
                current_target_id=current_target_id,
                receipt_hash=receipt_hash,
            )


def _cas_update_anchor_row(
    db: Session,
    *,
    row: _AnchorRow,
    model: type[Any],
    values: Mapping[str, Any],
) -> None:
    table = _model_table(model)
    if row.table_name != table.name:
        _fail(
            "layer3_origin_anchor_invalid",
            "Origin CAS used the wrong authority table.",
        )
    conditions = []
    for key, frozen in row.cas_values:
        column = table.c[key]
        expected = _thaw_anchor_value(frozen)
        if isinstance(column.type, JSON):
            conditions.append(
                _json_cas_condition(
                    column,
                    expected=expected,
                    dialect_name=db.get_bind().dialect.name,
                )
            )
        elif expected is None:
            conditions.append(column.is_(None))
        else:
            conditions.append(column == expected)
    result = db.execute(
        update(table).where(*conditions).values(**dict(values))
    )
    if getattr(result, "rowcount", None) != 1:
        _fail(
            "layer3_origin_cas_conflict",
            "Connector-origin authority changed during receipt minting.",
            details={"table": table.name},
        )


def _json_cas_condition(
    column: Any,
    *,
    expected: object,
    dialect_name: str,
) -> Any:
    if dialect_name == "sqlite":
        if expected is None:
            return or_(column.is_(None), column == JSON.NULL)
        return column == expected
    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import JSONB

        comparison = cast(column, JSONB) == literal(
            expected,
            type_=JSONB,
        )
        return (
            or_(column.is_(None), comparison)
            if expected is None
            else comparison
        )
    _fail(
        "layer3_origin_cas_dialect_unsupported",
        "Origin JSON CAS is not defined for this database dialect.",
        details={"dialect": dialect_name},
    )


def _expire_minted_rows(
    db: Session,
    *,
    rows: Sequence[tuple[type[Any], _AnchorRow]],
) -> None:
    identities = {
        (model, _row_primary_identity(row, model))
        for model, row in rows
    }
    for instance in tuple(db.identity_map.values()):
        model = type(instance)
        identity = tuple(
            getattr(instance, column.key, None)
            for column in _model_table(model).primary_key
        )
        if (model, identity) in identities:
            db.expire(instance)


def mint_connector_origin_receipt(
    db: Session,
    *,
    connector_run_target_id: str,
) -> dict[str, str]:
    """Mint one canonical receipt inside a caller-owned transaction.

    Unrelated pending work is flushed before the receipt savepoint. A failure
    in that caller-work flush follows normal Session failure semantics and can
    invalidate the caller transaction; receipt rollback containment begins
    only after that flush succeeds and the child savepoint opens.
    A lazy SQLite caller savepoint is made safe before its first SQL. An
    already-materialized SQLite savepoint is refused unless its current
    physical root was previously verified by this service.
    """

    _require_caller_transaction(db)
    _prepare_caller_root_transaction(db)
    target_id = _required_text(
        connector_run_target_id,
        field="connector_run_target_id",
    )
    with db.no_autoflush:
        initial_anchor = _read_origin_anchor(
            db,
            target_id=target_id,
        )
        _reject_relevant_identity_map_state(
            db,
            anchor=initial_anchor,
        )
    db.flush()

    touched_rows: list[tuple[type[Any], _AnchorRow]] = []
    with db.begin_nested():
        with db.no_autoflush:
            anchor = _read_origin_anchor(db, target_id=target_id)
            _reject_relevant_identity_map_state(
                db,
                anchor=anchor,
            )
            receipt = _derive_connector_origin_receipt_from_anchor(
                db,
                anchor=anchor,
            )
            _require_anchor_unchanged(
                db,
                target_id=target_id,
                expected=anchor,
            )
            target = anchor.target.materialize(
                ConnectorRunTarget
            )
            run = anchor.run.materialize(ConnectorRun)
            stored = _stored_origin_receipt(target)
            projection = _origin_projection(receipt)
            receipt_hash = projection[
                "connector_origin_receipt_hash"
            ]
            if stored is not None:
                if stored != receipt:
                    _fail(
                        "layer3_origin_stored_receipt_mismatch",
                        "Stored origin receipt contradicts fresh reconstruction.",
                    )
                if run.connector_key == "sciencebase_mcs":
                    _sciencebase_projection_rows(
                        anchor,
                        receipt_hash=receipt_hash,
                        projection_present=True,
                    )
                _require_anchor_unchanged(
                    db,
                    target_id=target_id,
                    expected=anchor,
                )
                return projection

            _require_unconsumed_origin_history(
                db,
                anchor=anchor,
                receipt_hash=receipt_hash,
            )
            provenance_row: _AnchorRow | None = None
            intake_row: _AnchorRow | None = None
            post_intake: dict[str, Any] | None = None
            if run.connector_key == "sciencebase_mcs":
                (
                    provenance_row,
                    intake_row,
                    _,
                ) = _sciencebase_projection_rows(
                    anchor,
                    receipt_hash=receipt_hash,
                    projection_present=False,
                )
                intake = intake_row.materialize(
                    L3ConnectorSourceIntakeRecord
                )
                from app.services import (
                    layer3_connector_source_intake,
                )

                post_intake = (
                    layer3_connector_source_intake
                    ._strict_sciencebase_intake_values(
                        connector_key=run.connector_key,
                        connector_run_id=run.connector_run_id,
                        connector_run_target_id=target_id,
                        raw_storage_ref=str(intake.storage_ref),
                        freshness_timestamp=(
                            intake.freshness_timestamp
                        ),
                        content_size_bytes=int(
                            intake.content_size_bytes
                        ),
                        content_sha256=str(
                            intake.content_sha256
                        ),
                        connector_origin_receipt_hash=receipt_hash,
                    )
                )

            target_source_reference = dict(
                target.source_reference_json
            )
            target_source_reference[
                ORIGIN_RECEIPT_STORAGE_KEY
            ] = dict(receipt)
            _cas_update_anchor_row(
                db,
                row=anchor.target,
                model=ConnectorRunTarget,
                values={
                    "source_reference_json": (
                        target_source_reference
                    ),
                },
            )
            touched_rows.append(
                (ConnectorRunTarget, anchor.target)
            )
            if (
                provenance_row is not None
                and intake_row is not None
                and post_intake is not None
            ):
                provenance = provenance_row.materialize(
                    DatasetSourceProvenance
                )
                provenance_source_reference = dict(
                    provenance.source_reference_json
                )
                provenance_source_reference[
                    "connector_origin_receipt_hash"
                ] = receipt_hash
                _cas_update_anchor_row(
                    db,
                    row=provenance_row,
                    model=DatasetSourceProvenance,
                    values={
                        "source_reference_json": (
                            provenance_source_reference
                        ),
                    },
                )
                _cas_update_anchor_row(
                    db,
                    row=intake_row,
                    model=L3ConnectorSourceIntakeRecord,
                    values={
                        key: post_intake[key]
                        for key in (
                            "metadata_hash",
                            "authority_basis_hash",
                            "provenance_json",
                            "summary_json",
                        )
                    },
                )
                touched_rows.extend(
                    (
                        (
                            DatasetSourceProvenance,
                            provenance_row,
                        ),
                        (
                            L3ConnectorSourceIntakeRecord,
                            intake_row,
                        ),
                    )
                )

            post_anchor = _read_origin_anchor(
                db,
                target_id=target_id,
            )
            post_receipt = (
                _derive_connector_origin_receipt_from_anchor(
                    db,
                    anchor=post_anchor,
                )
            )
            _require_anchor_unchanged(
                db,
                target_id=target_id,
                expected=post_anchor,
            )
            post_target = post_anchor.target.materialize(
                ConnectorRunTarget
            )
            if (
                post_receipt != receipt
                or _stored_origin_receipt(post_target)
                != receipt
            ):
                _fail(
                    "layer3_origin_post_mint_mismatch",
                    "Minted receipt does not equal fresh origin authority.",
                )
            if run.connector_key == "sciencebase_mcs":
                _sciencebase_projection_rows(
                    post_anchor,
                    receipt_hash=receipt_hash,
                    projection_present=True,
                )

    _expire_minted_rows(db, rows=touched_rows)
    return projection


def _verified_connector_origin_state(
    db: Session,
    *,
    target_id: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    anchor = _read_origin_anchor(db, target_id=target_id)
    _reject_relevant_identity_map_state(db, anchor=anchor)
    receipt = _derive_connector_origin_receipt_from_anchor(
        db,
        anchor=anchor,
    )
    target = anchor.target.materialize(ConnectorRunTarget)
    stored = _stored_origin_receipt(target)
    if stored is None:
        _fail(
            "layer3_origin_stored_receipt_missing",
            "The target lacks its authoritative connector-origin receipt.",
        )
    if stored != receipt:
        _fail(
            "layer3_origin_stored_receipt_mismatch",
            "Stored origin receipt contradicts fresh reconstruction.",
        )
    projection = _origin_projection(receipt)
    run = anchor.run.materialize(ConnectorRun)
    if run.connector_key == "sciencebase_mcs":
        _sciencebase_projection_rows(
            anchor,
            receipt_hash=projection[
                "connector_origin_receipt_hash"
            ],
            projection_present=True,
        )
    _require_anchor_unchanged(
        db,
        target_id=target_id,
        expected=anchor,
    )
    return receipt, projection


def verified_connector_origin_projection(
    db: Session,
    *,
    connector_run_target_id: str,
) -> dict[str, str]:
    """Return the exact stored target/hash pair without mutation."""

    _require_caller_transaction(db)
    target_id = _required_text(
        connector_run_target_id,
        field="connector_run_target_id",
    )
    with db.no_autoflush:
        _, projection = _verified_connector_origin_state(
            db,
            target_id=target_id,
        )
        return projection


def derive_connector_origin_receipt(
    db: Session,
    *,
    connector_run_target_id: str,
) -> dict[str, Any]:
    """Reconstruct one connector target's origin receipt from server-owned state."""
    target_id = _required_text(
        connector_run_target_id,
        field="connector_run_target_id",
    )
    with db.no_autoflush:
        anchor = _read_origin_anchor(db, target_id=target_id)
        receipt = _derive_connector_origin_receipt_from_anchor(
            db,
            anchor=anchor,
        )
        _require_anchor_unchanged(
            db,
            target_id=target_id,
            expected=anchor,
        )
        return receipt


def assert_connector_origin_continuity(
    db: Session,
    *,
    connector_run_target_id: str,
    expected_receipt_hash: str,
    expected_bindings: Mapping[str, str],
) -> None:
    """Fail unless the stored target receipt equals a fresh reconstruction."""
    target_id = _required_text(
        connector_run_target_id,
        field="connector_run_target_id",
    )
    expected_hash = _normalized_sha256(
        expected_receipt_hash,
        field="expected_receipt_hash",
    )
    if not isinstance(expected_bindings, Mapping):
        _fail(
            "layer3_origin_expected_bindings_invalid",
            "expected_bindings must be a mapping of scalar receipt fields.",
        )
    with db.no_autoflush:
        derived, projection = _verified_connector_origin_state(
            db,
            target_id=target_id,
        )
        if projection["connector_origin_receipt_hash"] != expected_hash:
            _fail(
                "layer3_origin_stored_receipt_mismatch",
                "The stored receipt does not equal reconstructed origin evidence.",
            )
        for field, expected in expected_bindings.items():
            if not isinstance(field, str) or not isinstance(expected, str):
                _fail(
                    "layer3_origin_expected_bindings_invalid",
                    "Expected origin bindings must use string keys and values.",
                )
            actual = derived.get(field)
            if (
                actual is None
                or isinstance(actual, (Mapping, list))
                or str(actual) != expected
            ):
                _fail(
                    "layer3_origin_expected_binding_mismatch",
                    "A downstream origin binding does not equal the canonical receipt.",
                    details={"field": field},
                )
