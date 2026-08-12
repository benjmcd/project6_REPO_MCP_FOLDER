"""Durable reservation and bounded transport for B0 connector effects."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import urlsplit
from uuid import UUID

from app.services.connector_egress_contract import EffectResult, PhysicalRequestPlan


@dataclass(frozen=True)
class CommittedReservation:
    disposition: str
    event_id: str
    plan_digest: str


@dataclass(frozen=True)
class ReservationHold:
    disposition: str
    reason_code: str
    event_id: str | None
    plan_digest: str | None


@dataclass(frozen=True)
class ExactEventResult:
    disposition: str
    event_id: str
    reason_code: str


class EgressHold(RuntimeError):
    def __init__(self, disposition: str, reason_code: str) -> None:
        self.disposition = disposition
        self.reason_code = reason_code
        super().__init__(f"{disposition}:{reason_code}")


@dataclass(frozen=True)
class ReservationVolumeIdentity:
    identity: str
    fixed: bool
    local: bool


@dataclass(frozen=True)
class ReservationFileIdentity:
    volume_identity: str
    file_identity: str
    link_count: int
    reparse: bool
    directory: bool


class ReservationIdentityProbe(Protocol):
    def canonicalize(self, path: Path) -> Path: ...
    def pin(self, path: Path, *, directory: bool) -> None: ...
    def volume(self, path: Path) -> ReservationVolumeIdentity: ...
    def identity(self, path: Path, *, directory: bool) -> ReservationFileIdentity: ...
    def close(self) -> None: ...


class _FileInfo(ctypes.Structure):
    _fields_ = [
        ("attributes", wintypes.DWORD),
        ("creation_low", wintypes.DWORD),
        ("creation_high", wintypes.DWORD),
        ("access_low", wintypes.DWORD),
        ("access_high", wintypes.DWORD),
        ("write_low", wintypes.DWORD),
        ("write_high", wintypes.DWORD),
        ("volume_serial", wintypes.DWORD),
        ("size_high", wintypes.DWORD),
        ("size_low", wintypes.DWORD),
        ("link_count", wintypes.DWORD),
        ("file_index_high", wintypes.DWORD),
        ("file_index_low", wintypes.DWORD),
    ]


class _WindowsReservationIdentityProbe:
    def __init__(self) -> None:
        if os.name != "nt":
            raise EgressHold("HOLD", "reservation_windows_identity_required")
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        self._kernel.CreateFileW.restype = wintypes.HANDLE
        self._kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel.GetFileInformationByHandle.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_FileInfo),
        ]
        self._kernel.GetVolumePathNameW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPWSTR,
            wintypes.DWORD,
        ]
        self._kernel.GetVolumeInformationW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.LPWSTR,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.LPWSTR,
            wintypes.DWORD,
        ]
        self._kernel.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
        self._handles: list[int] = []

    @staticmethod
    def _check(ok: object) -> None:
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())

    def canonicalize(self, path: Path) -> Path:
        return path.resolve(strict=True)

    def _open(self, path: Path, *, directory: bool) -> int:
        flags = 0x00200000 | (0x02000000 if directory else 0)
        handle = self._kernel.CreateFileW(
            str(path), 0x00000080, 0x00000001 | 0x00000002, None, 3, flags, None
        )
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        return int(handle)

    def pin(self, path: Path, *, directory: bool) -> None:
        self._handles.append(self._open(path, directory=directory))

    def volume(self, path: Path) -> ReservationVolumeIdentity:
        volume_root = ctypes.create_unicode_buffer(32768)
        self._check(
            self._kernel.GetVolumePathNameW(str(path), volume_root, len(volume_root))
        )
        serial = wintypes.DWORD()
        self._check(
            self._kernel.GetVolumeInformationW(
                volume_root.value, None, 0, ctypes.byref(serial), None, None, None, 0
            )
        )
        drive_type = int(self._kernel.GetDriveTypeW(volume_root.value))
        return ReservationVolumeIdentity(
            f"serial:{serial.value:08x}", drive_type == 3, drive_type != 4
        )

    def identity(self, path: Path, *, directory: bool) -> ReservationFileIdentity:
        handle = self._open(path, directory=directory)
        try:
            info = _FileInfo()
            self._check(
                self._kernel.GetFileInformationByHandle(handle, ctypes.byref(info))
            )
        finally:
            self._kernel.CloseHandle(handle)
        file_id = (int(info.file_index_high) << 32) | int(info.file_index_low)
        return ReservationFileIdentity(
            f"serial:{int(info.volume_serial):08x}",
            f"file:{file_id:016x}",
            int(info.link_count),
            bool(info.attributes & 0x400),
            bool(info.attributes & 0x10),
        )

    def close(self) -> None:
        while self._handles:
            self._kernel.CloseHandle(self._handles.pop())


class ConnectorEgressTransport:
    def __init__(
        self,
        reservation_store: "ReservationStore",
        *,
        session_factory: Callable[[], Any],
        request_headers: Mapping[str, str] | None = None,
    ) -> None:
        self.reservation_store = reservation_store
        self.session_factory = session_factory
        self.request_headers = dict(request_headers or {})

    def _validated_headers(self, plan: PhysicalRequestPlan) -> dict[str, str]:
        names = tuple(sorted(self.request_headers))
        valid_shape = names == plan.header_names and all(
            isinstance(value, str)
            and len(value) <= 4096
            and "\r" not in value
            and "\n" not in value
            for value in self.request_headers.values()
        )
        commitments = (
            tuple(
                "sha256:"
                + hashlib.sha256(self.request_headers[name].encode("utf-8")).hexdigest()
                for name in names
            )
            if valid_shape
            else ()
        )
        if not valid_shape or commitments != plan.header_value_sha256s:
            raise EgressHold("HOLD", "request_header_commitment_mismatch")
        return dict(self.request_headers)

    def execute(self, plan: PhysicalRequestPlan) -> EffectResult:
        reservation = self.reservation_store.reserve(plan)
        if not isinstance(reservation, CommittedReservation):
            raise EgressHold(reservation.disposition, reservation.reason_code)
        session: Any = None
        response: Any = None
        try:
            headers = self._validated_headers(plan)
            session = self.session_factory()
            response = session.request(
                plan.method,
                plan.canonical_destination,
                allow_redirects=False,
                headers=headers,
                stream=True,
                timeout=plan.limits.timeout_seconds,
            )
            body = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not isinstance(chunk, bytes):
                    raise EgressHold("HOLD", "transport_response_chunk_invalid")
                body.extend(chunk)
                if len(body) > plan.limits.max_response_bytes:
                    raise EgressHold("HOLD", "transport_response_too_large")
            status_code = response.status_code
            if (
                isinstance(status_code, bool)
                or not isinstance(status_code, int)
                or not 100 <= status_code <= 599
            ):
                raise EgressHold("HOLD", "transport_status_code_invalid")
            raw_header_names = tuple(response.headers)
            if not all(isinstance(name, str) for name in raw_header_names):
                raise EgressHold("HOLD", "transport_response_headers_invalid")
            header_names = tuple(sorted({name.lower() for name in raw_header_names}))
            if len(header_names) != len(raw_header_names):
                raise EgressHold("HOLD", "transport_response_headers_invalid")
            redirect_location = None
            if status_code in {301, 302, 303, 307, 308}:
                redirect_location = response.headers.get("Location")
                if not isinstance(redirect_location, str):
                    raise EgressHold("HOLD", "transport_redirect_invalid")
                redirect = urlsplit(redirect_location)
                relative = (
                    not redirect.scheme
                    and not redirect.netloc
                    and redirect.path.startswith("/")
                    and not redirect.fragment
                )
                absolute = (
                    redirect.scheme == "https"
                    and bool(redirect.hostname)
                    and redirect.hostname == redirect.hostname.lower()
                    and redirect.username is None
                    and redirect.password is None
                    and not redirect.fragment
                )
                if not (relative or absolute):
                    raise EgressHold("HOLD", "transport_redirect_invalid")
            return EffectResult(
                reservation_event_id=reservation.event_id,
                plan_digest=reservation.plan_digest,
                status_code=status_code,
                body=bytes(body),
                response_header_names=header_names,
                redirect_location=redirect_location,
            )
        except EgressHold:
            raise
        except Exception:
            raise EgressHold("HOLD", "transport_failed") from None
        finally:
            cleanup_failed = False
            if response is not None:
                try:
                    response.close()
                except Exception:
                    cleanup_failed = True
            if session is not None:
                try:
                    session.close()
                except Exception:
                    cleanup_failed = True
            if cleanup_failed:
                raise EgressHold("HOLD", "transport_cleanup_failed") from None


class ReservationStore:
    DATABASE_BASENAME = "reservation.db"
    _LIVE_EVENT_TYPES = frozenset(
        {
            "sciencebase_live_go_consumed",
            "sciencebase_acquisition_terminal",
            "sciencebase_closeout_verified",
        }
    )

    def __init__(
        self,
        canonical_root: Path,
        database_path: Path | None = None,
        *,
        identity_probe: ReservationIdentityProbe | None = None,
    ) -> None:
        self._probe = identity_probe or _WindowsReservationIdentityProbe()
        try:
            root_candidate = Path(canonical_root)
            canonical = self._probe.canonicalize(root_candidate)
            if (
                root_candidate != canonical
                or not canonical.is_dir()
                or str(canonical).startswith("\\\\")
            ):
                raise EgressHold("HOLD", "reservation_root_identity_invalid")
            derived_database = canonical / self.DATABASE_BASENAME
            if database_path is not None and Path(database_path) != derived_database:
                raise EgressHold("HOLD", "reservation_database_path_mismatch")
            if self._probe.canonicalize(derived_database) != derived_database:
                raise EgressHold("HOLD", "reservation_database_identity_invalid")
            self.canonical_root = canonical
            self.database_path = derived_database
            self._probe.pin(self.canonical_root, directory=True)
            self._probe.pin(self.database_path, directory=False)
            self._volume_identity = self._probe.volume(self.canonical_root)
            self._root_identity = self._probe.identity(
                self.canonical_root, directory=True
            )
            self._database_identity = self._probe.identity(
                self.database_path, directory=False
            )
            self._revalidate_identity()
        except EgressHold:
            self._probe.close()
            raise
        except (OSError, TypeError, ValueError):
            self._probe.close()
            raise EgressHold("HOLD", "reservation_database_identity_invalid") from None

    def close(self) -> None:
        self._probe.close()

    def verify_identity(self) -> None:
        self._revalidate_identity()

    def __del__(self) -> None:
        probe = getattr(self, "_probe", None)
        if probe is not None:
            probe.close()

    def _revalidate_identity(self) -> None:
        try:
            volume = self._probe.volume(self.canonical_root)
            root = self._probe.identity(self.canonical_root, directory=True)
            database = self._probe.identity(self.database_path, directory=False)
            valid = (
                self._probe.canonicalize(self.canonical_root) == self.canonical_root
                and self._probe.canonicalize(self.database_path) == self.database_path
                and volume == self._volume_identity
                and volume.fixed
                and volume.local
                and bool(volume.identity)
                and root == self._root_identity
                and root.directory
                and not root.reparse
                and bool(root.file_identity)
                and root.volume_identity == volume.identity
                and database == self._database_identity
                and not database.directory
                and not database.reparse
                and not isinstance(database.link_count, bool)
                and database.link_count == 1
                and bool(database.file_identity)
                and database.volume_identity == volume.identity
            )
        except (OSError, TypeError, ValueError):
            valid = False
        if not valid:
            raise EgressHold("HOLD", "reservation_database_identity_drift") from None

    def _open(self) -> sqlite3.Connection:
        self._revalidate_identity()
        connection = sqlite3.connect(
            self.database_path.as_uri() + "?mode=rw",
            uri=True,
            isolation_level=None,
            timeout=5.0,
        )
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = FULL")
        database_file = Path(
            connection.execute("PRAGMA database_list").fetchone()[2]
        ).resolve()
        if database_file != self.database_path:
            connection.close()
            raise sqlite3.DatabaseError("reservation_store_path_ambiguous")
        self._revalidate_identity()
        return connection

    @staticmethod
    def _metrics(plan: PhysicalRequestPlan) -> dict[str, object]:
        return {
            "schema": "project6.physical_request_reservation.v1",
            "plan_digest": plan.plan_digest,
            "envelope_digest": plan.envelope_digest,
            "authorization_digest": plan.authorization_digest,
            "grant_digest": plan.grant_digest,
            "request_ordinal": plan.request_ordinal,
            "target_id": plan.target_id,
            "stage": plan.stage,
        }

    def reserve(
        self, plan: PhysicalRequestPlan
    ) -> CommittedReservation | ReservationHold:
        if plan.canonical_root != str(self.canonical_root):
            return ReservationHold(
                "HOLD",
                "reservation_root_binding_mismatch",
                plan.slot_uuid,
                plan.plan_digest,
            )
        metrics_json = json.dumps(
            self._metrics(plan), sort_keys=True, separators=(",", ":")
        )
        try:
            with self._open() as connection:
                self._revalidate_identity()
                connection.execute("BEGIN IMMEDIATE")
                self._revalidate_identity()
                existing = connection.execute(
                    """
                    SELECT connector_run_id, phase, stage, event_type, status_after,
                           reason_code, metrics_json
                    FROM connector_run_event WHERE connector_run_event_id = ?
                    """,
                    (plan.slot_uuid,),
                ).fetchone()
                if existing is not None:
                    connection.rollback()
                    expected = (
                        plan.connector_run_id,
                        "physical_request",
                        plan.stage,
                        "physical_request_reserved",
                        "reserved",
                        "physical_request_reserved",
                        metrics_json,
                    )
                    if existing == expected:
                        return ReservationHold(
                            "SPENT",
                            "reservation_already_spent",
                            plan.slot_uuid,
                            plan.plan_digest,
                        )
                    return ReservationHold(
                        "HOLD", "reservation_slot_conflict", plan.slot_uuid, None
                    )
                connection.execute(
                    """
                    INSERT INTO connector_run_event (
                        connector_run_event_id, connector_run_id, connector_run_target_id,
                        phase, stage, event_type, status_before, status_after,
                        reason_code, error_class, message, metrics_json, created_at
                    ) VALUES (?, ?, NULL, ?, ?, ?, NULL, ?, ?, NULL, NULL, ?, ?)
                    """,
                    (
                        plan.slot_uuid,
                        plan.connector_run_id,
                        "physical_request",
                        plan.stage,
                        "physical_request_reserved",
                        "reserved",
                        "physical_request_reserved",
                        metrics_json,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                self._revalidate_identity()
                connection.commit()
                self._revalidate_identity()
        except EgressHold as exc:
            return ReservationHold(
                "HOLD", exc.reason_code, plan.slot_uuid, plan.plan_digest
            )
        except sqlite3.Error:
            return ReservationHold(
                "HOLD", "reservation_write_failed", plan.slot_uuid, plan.plan_digest
            )
        try:
            with self._open() as independent:
                self._revalidate_identity()
                observed = independent.execute(
                    "SELECT event_type, reason_code, metrics_json FROM connector_run_event WHERE connector_run_event_id = ?",
                    (plan.slot_uuid,),
                ).fetchone()
                self._revalidate_identity()
        except EgressHold as exc:
            return ReservationHold(
                "HOLD", exc.reason_code, plan.slot_uuid, plan.plan_digest
            )
        except sqlite3.Error:
            return ReservationHold(
                "HOLD",
                "reservation_observation_indeterminate",
                plan.slot_uuid,
                plan.plan_digest,
            )
        if observed != (
            "physical_request_reserved",
            "physical_request_reserved",
            metrics_json,
        ):
            return ReservationHold(
                "HOLD",
                "reservation_observation_mismatch",
                plan.slot_uuid,
                plan.plan_digest,
            )
        return CommittedReservation("RESERVED", plan.slot_uuid, plan.plan_digest)

    def assert_no_reservations(self, connector_run_id: str) -> ReservationHold | None:
        try:
            with self._open() as independent:
                self._revalidate_identity()
                run_count = independent.execute(
                    "SELECT COUNT(*) FROM connector_run WHERE connector_run_id = ?",
                    (connector_run_id,),
                ).fetchone()[0]
                rows = independent.execute(
                    """
                    SELECT connector_run_event_id, phase, stage, event_type,
                           status_after, reason_code, metrics_json
                    FROM connector_run_event
                    WHERE connector_run_id = ?
                      AND (phase = 'physical_request' OR event_type = 'physical_request_reserved')
                    """,
                    (connector_run_id,),
                ).fetchall()
                self._revalidate_identity()
        except EgressHold as exc:
            return ReservationHold("HOLD", exc.reason_code, None, None)
        except sqlite3.Error:
            return ReservationHold(
                "HOLD", "reservation_probe_indeterminate", None, None
            )
        if run_count != 1:
            return ReservationHold(
                "HOLD", "connector_run_identity_ambiguous", None, None
            )
        if not rows:
            return None
        for (
            event_id,
            phase,
            stage,
            event_type,
            status_after,
            reason_code,
            raw_metrics,
        ) in rows:
            try:
                metrics = json.loads(raw_metrics)
                valid_uuid = str(UUID(event_id)) == event_id
            except (TypeError, ValueError, json.JSONDecodeError, AttributeError):
                return ReservationHold(
                    "HOLD", "reservation_history_malformed", event_id, None
                )
            valid = (
                valid_uuid
                and phase == "physical_request"
                and isinstance(stage, str)
                and bool(stage)
                and event_type == "physical_request_reserved"
                and status_after == "reserved"
                and reason_code == "physical_request_reserved"
                and isinstance(metrics, dict)
                and metrics.get("schema") == "project6.physical_request_reservation.v1"
                and isinstance(metrics.get("plan_digest"), str)
                and metrics["plan_digest"].startswith("sha256:")
            )
            if not valid:
                return ReservationHold(
                    "HOLD", "reservation_history_malformed", event_id, None
                )
        return ReservationHold(
            "SPENT", "connector_run_has_reservation", rows[0][0], None
        )

    def write_sciencebase_live_event(
        self,
        *,
        event_id: str,
        connector_run_id: str,
        phase: str,
        stage: str,
        event_type: str,
        status_after: str,
        reason_code: str,
        metrics: dict[str, object],
    ) -> ExactEventResult | ReservationHold:
        try:
            valid = (
                str(UUID(event_id)) == event_id
                and str(UUID(connector_run_id)) == connector_run_id
                and event_type in self._LIVE_EVENT_TYPES
                and all(
                    isinstance(value, str) and 0 < len(value) <= limit
                    for value, limit in (
                        (phase, 100),
                        (stage, 100),
                        (status_after, 50),
                        (reason_code, 255),
                    )
                )
                and isinstance(metrics, dict)
            )
            metrics_json = json.dumps(
                metrics, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
        except (TypeError, ValueError, AttributeError):
            valid = False
            metrics_json = ""
        if not valid or len(metrics_json.encode("utf-8")) > 32 * 1024:
            return ReservationHold("HOLD", "live_event_invalid", event_id, None)
        expected = (
            connector_run_id,
            phase,
            stage,
            event_type,
            status_after,
            reason_code,
            metrics_json,
        )
        try:
            with self._open() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._revalidate_identity()
                existing = connection.execute(
                    """
                    SELECT connector_run_id, phase, stage, event_type,
                           status_after, reason_code, metrics_json
                    FROM connector_run_event WHERE connector_run_event_id = ?
                    """,
                    (event_id,),
                ).fetchone()
                if existing is not None:
                    connection.rollback()
                    if existing == expected:
                        return ExactEventResult("EXISTS", event_id, reason_code)
                    return ReservationHold(
                        "HOLD", "live_event_identity_conflict", event_id, None
                    )
                connection.execute(
                    """
                    INSERT INTO connector_run_event (
                        connector_run_event_id, connector_run_id, connector_run_target_id,
                        phase, stage, event_type, status_before, status_after,
                        reason_code, error_class, message, metrics_json, created_at
                    ) VALUES (?, ?, NULL, ?, ?, ?, NULL, ?, ?, NULL, NULL, ?, ?)
                    """,
                    (
                        event_id,
                        connector_run_id,
                        phase,
                        stage,
                        event_type,
                        status_after,
                        reason_code,
                        metrics_json,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                self._revalidate_identity()
                connection.commit()
                self._revalidate_identity()
        except EgressHold as exc:
            return ReservationHold("HOLD", exc.reason_code, event_id, None)
        except sqlite3.Error:
            return ReservationHold("HOLD", "live_event_write_failed", event_id, None)
        try:
            with self._open() as independent:
                observed = independent.execute(
                    """
                    SELECT connector_run_id, phase, stage, event_type,
                           status_after, reason_code, metrics_json
                    FROM connector_run_event WHERE connector_run_event_id = ?
                    """,
                    (event_id,),
                ).fetchone()
                self._revalidate_identity()
        except (EgressHold, sqlite3.Error):
            return ReservationHold(
                "HOLD", "live_event_observation_indeterminate", event_id, None
            )
        if observed != expected:
            return ReservationHold(
                "HOLD", "live_event_observation_mismatch", event_id, None
            )
        return ExactEventResult("RECORDED", event_id, reason_code)

    def read_sciencebase_run_events(
        self, connector_run_id: str
    ) -> tuple[dict[str, object], ...] | ReservationHold:
        try:
            if str(UUID(connector_run_id)) != connector_run_id:
                raise ValueError
            with self._open() as connection:
                rows = connection.execute(
                    """
                    SELECT connector_run_event_id, phase, stage, event_type,
                           status_after, reason_code, metrics_json
                    FROM connector_run_event
                    WHERE connector_run_id = ?
                      AND (event_type = 'physical_request_reserved'
                           OR event_type LIKE 'sciencebase_%')
                    ORDER BY created_at, connector_run_event_id
                    """,
                    (connector_run_id,),
                ).fetchall()
                self._revalidate_identity()
        except (EgressHold, sqlite3.Error, TypeError, ValueError, AttributeError):
            return ReservationHold("HOLD", "live_event_read_failed", None, None)
        result: list[dict[str, object]] = []
        for event_id, phase, stage, event_type, status_after, reason_code, raw in rows:
            try:
                metrics = json.loads(raw)
                if str(UUID(event_id)) != event_id or not isinstance(metrics, dict):
                    raise ValueError
            except (TypeError, ValueError, json.JSONDecodeError, AttributeError):
                return ReservationHold("HOLD", "live_event_history_malformed", event_id, None)
            result.append(
                {
                    "event_id": event_id,
                    "phase": phase,
                    "stage": stage,
                    "event_type": event_type,
                    "status_after": status_after,
                    "reason_code": reason_code,
                    "metrics": metrics,
                }
            )
        return tuple(result)
