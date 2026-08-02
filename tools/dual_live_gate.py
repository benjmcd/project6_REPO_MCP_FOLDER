import json
import os
import re
import socket
import sqlite3
import sys
import warnings
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Literal, NoReturn
from uuid import UUID


_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
_BACKEND = _ROOT / "backend"
_LOWERCASE_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_FALSE_VALUES = frozenset(("", "0", "false", "no", "off"))
_TRUE_VALUES = frozenset(("1", "true", "yes", "on"))
_AUTHORITY_VARIABLES = (
    "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
    "CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
    "CONNECTOR_SCIENCEBASE_GRANT_PATH",
    "CONNECTOR_SCIENCEBASE_GRANT_SHA256",
    "CONNECTOR_NRC_APS_GRANT_PATH",
    "CONNECTOR_NRC_APS_GRANT_SHA256",
)
_OPTIONS = {
    "--campaign-id": "campaign_id",
    "--campaign-fingerprint": "campaign_fingerprint",
}
GATE_CHECK_ORDER = (
    "G01_GATE_REFUSAL_PRECONDITIONS",
    "G02_GATE_NETWORK_DENIAL",
)
_SAFE_CODE = re.compile(r"[a-z0-9_]+\Z")
_EXPECTED_EVALUATOR_CHECK_ORDER = (
    "A01_INPUT_IDENTITY",
    "A02_INDEX_LINEAR_HEAD",
    "A03_ARCHIVE_EXACT",
    "A04_SLICE_CARDINALITY",
    "A05_SELECTED_UNION",
    "A06_INTRODUCTION_PARITY",
    "A07_MARKER_ONE_USE",
    "A08_ORIGINAL_WINDOWS",
    "A09_CODE_CAMPAIGN_FINGERPRINTS",
    "A10_PROOF_CLASS",
    "R01_CAPTURE_MEMBERSHIP",
    "R02_MANIFEST_FILE_HASHES",
    "R03_SEAL_PARITY",
    "R04_SEAL_EVENT_PARITY",
    "R05_RUNTIME_CHAIN",
    "R06_STARTUP_LOGGER_CENSUS",
    "R07_EXIT_LOGGER_CENSUS",
    "R08_PHASE_A_IDENTITY",
    "R09_PHASE_A_JOB_ZERO",
    "R10_PHASE_A_SOCKET_QUIESCENCE",
    "R11_AUTHORITY_CLEARED",
    "R12_PHASE_B_GUARDS",
    "R13_PHASE_B_JOB_ZERO",
    "R14_RUNTIME_TERMINAL",
    "R15_WRAPPER_NETWORK_INERT",
    "R16_PHASE_A_RAW_ONLY",
    "R17_PHASE_B_STRICT_FLOW",
    "R18_PHASE_A_TERMINAL_ONCE",
    "R19_A_TO_B_ORDER",
    "R20_FOUR_STREAM_CLOSEOUT",
    "R21_EXTANT_RUN_SEAL_EVENTS",
    "R22_CAPTURE_START_CONTRACT",
    "L01_RUN_CARDINALITY",
    "L02_TERMINAL_EVENT",
    "L03_POST_TERMINAL_EXTINCTION",
    "L04_LEDGER_RECONSTRUCTION",
    "L05_COUNTER_BIJECTION",
    "L06_COUNTER_BOOT",
    "L07_BYTE_ALLOWANCE",
    "L08_REQUEST_CADENCE",
    "L09_TRANSPORT_POLICY",
    "L10_FRESH_200_BYTES",
    "L11_NRC_FIRST_BINDING",
    "L12_RESERVATION_RESOLUTION",
    "D01_ORIGIN_RECEIPT",
    "D02_RAW_PROVENANCE_LINKAGE",
    "D03_LAYER3_EXECUTION",
    "D04_REVIEW_RESULT",
    "D05_PACKAGE_SET",
    "D06_PACKAGE_PAYLOAD",
    "D07_SUBMIT_RECEIPT",
    "D08_HANDOFF_RECEIPT",
    "C01_STRICT_NULLS",
    "C02_DB_SCALAR_JSON_SCAN",
    "C03_NON_SOURCE_FILE_SCAN",
    "C04_SERIALIZATION_EVENT_SCAN",
    "C05_RUNTIME_LOG_SCAN",
    "C06_BOUNDED_DECODERS",
    "C07_SOURCE_EXEMPTION",
    "C08_SECRET_SCAN",
    "F01_EVIDENCE_STABILITY",
    "F02_DATABASE_STABILITY",
    "F03_NONCLAIMS_REPORT",
    "F04_READ_ONLY_EVALUATION",
    "F05_PROJECTION_REDERIVATION",
    "F06_NO_EGRESS_DEPENDENCY",
    "F07_PUBLIC_API_CONTRACT",
    "F08_RESULT_AGGREGATION",
    "F09_CONNECTOR_AND_COMBINED_REPORTS",
)
_EXPECTED_EVALUATOR_NONCLAIMS = (
    "offline local-experiment evidence only",
    "no external live acquisition performed by evaluation",
    "no signature or WORM custody claim",
    "no cryptographic nonrepudiation claim",
    "no owning-account compromise resistance claim",
    "no coherent all-domain rewrite detection claim",
    "no visibility into OS, proxy, provider, or machine-global logs",
    "no deployment or production readiness claim",
)
_SAFE_EVIDENCE_KEYS = frozenset(
    {
        "acquisition_only",
        "action_receipt_count",
        "active_process_count",
        "admitted_raw_response_count",
        "alias_count",
        "all_required_absent",
        "archive_count",
        "authority_posture_sha256",
        "bound_review_count",
        "boundary_count",
        "cadence_verified",
        "campaign_fingerprint",
        "canonical",
        "captures",
        "census_count",
        "child_proof_count",
        "closed_stream_count",
        "code_revision",
        "combined_result_count",
        "combined_result",
        "completed_run_count",
        "connector_acquisition_count",
        "connector_count",
        "connector_result_count",
        "connector_results",
        "contradictory_tail_count",
        "counter_count",
        "decoded_form_count",
        "decoded_sink_count",
        "definitions",
        "denied_route_count",
        "delivery_claim_count",
        "domain",
        "downstream_action_count",
        "encoding",
        "exact_source_exemption_count",
        "execution_result_count",
        "extant_run_count",
        "file_count",
        "file_set_hash",
        "first_hit_digest",
        "forbidden_dependency_count",
        "grants",
        "guard_proof_count",
        "half_open",
        "head_revision",
        "hit_count",
        "inspected_module_count",
        "introduction_revision",
        "introduction_sha256",
        "ledger_count",
        "ledger_send_count",
        "linked_raw_blob_count",
        "marker_count",
        "nonclaim_count",
        "package_count",
        "package_kind_count",
        "parent_run_id",
        "parent_terminal_hash",
        "pending_write_count",
        "phase_a_terminal_ordinal",
        "phase_b_network_enable_attempt_count",
        "phase_b_start_ordinal",
        "pre_import_guarded",
        "prepared_internal_handoff_count",
        "process_boot_count",
        "process_boot_id",
        "prohibited_endpoint_count",
        "proof_class",
        "protected_object_count",
        "protected_snapshot_count",
        "proof_stream_phase_order",
        "provenance_count",
        "public_parameter_count",
        "raw_blob_count",
        "record_count",
        "rederived_projection_domain_count",
        "rederived_receipt_count",
        "registered_check_count",
        "rehashed_payload_count",
        "request_rule_count",
        "retained_campaign_count",
        "revision_count",
        "runtime_instance_count",
        "scanned_sink_count",
        "seal_event_count",
        "seal_sha256",
        "selected_captures",
        "selected_definitions",
        "selected_grants",
        "semantic_snapshot_count",
        "shared_stream_count",
        "source_binding_count",
        "stream_count",
        "submit_receipt_count",
        "target_count",
        "terminal_boundary",
        "terminal_event_count",
        "terminal_hashes",
        "terminal_record_sha256",
        "terminal_run_count",
        "terminal_state",
        "terminal_transition_count",
        "unchanged",
        "unresolved_reservation_count",
        "wrapper_send_records",
    }
)
_EXPECTED_CONNECTOR_KEYS = ("nrc_adams_aps", "sciencebase_mcs")
_HASH_EVIDENCE_KEYS = frozenset(
    {
        "authority_posture_sha256",
        "campaign_fingerprint",
        "file_set_hash",
        "first_hit_digest",
        "introduction_sha256",
        "parent_terminal_hash",
        "seal_sha256",
        "terminal_record_sha256",
    }
)
_NONNEGATIVE_INTEGER_EVIDENCE_KEYS = frozenset(
    {
        "action_receipt_count",
        "child_proof_count",
        "connector_acquisition_count",
        "denied_route_count",
        "downstream_action_count",
        "guard_proof_count",
        "inspected_module_count",
        "phase_a_terminal_ordinal",
        "phase_b_network_enable_attempt_count",
        "source_binding_count",
        "terminal_transition_count",
    }
)
_SAFE_EVIDENCE_DOMAINS = frozenset(
    {
        "archive",
        "authority",
        "capture",
        "counter",
        "custody",
        "downstream",
        "execution",
        "handoff",
        "ledger",
        "origin",
        "package_set",
        "review",
        "runtime",
        "stability",
        "submit",
    }
)
_RUNTIME_START_EVIDENCE_KEYS = (
    "record_count",
    "terminal_record_sha256",
    "dependency_set_sha256",
    "phase_a_timeout_ms",
    "phase_b_timeout_ms",
)
_KNOWN_SAFE_EXCEPTION_CODES = frozenset(
    {
        "dual_live_campaign_evidence_invalid",
        "dual_live_campaign_evidence_missing",
        "dual_live_capture_unsealed",
        "dual_live_database_attachment_unsafe",
        "dual_live_database_custody_changed",
        "dual_live_database_custody_cleanup_failed",
        "dual_live_database_custody_closed",
        "dual_live_database_custody_refused",
        "dual_live_database_data_version_changed",
        "dual_live_database_journal_mode_unsafe",
        "dual_live_database_missing",
        "dual_live_database_path_unsafe",
        "dual_live_database_query_only_refused",
        "dual_live_database_sidecar_present",
        "dual_live_database_url_invalid",
        "dual_live_egress_enabled",
        "dual_live_environment_ambiguous",
        "dual_live_environment_invalid",
        "dual_live_evaluation_contract_invalid",
        "dual_live_evaluation_snapshot_changed",
        "dual_live_evaluation_status_invalid",
        "dual_live_evidence_chain_changed",
        "dual_live_evidence_chain_unavailable",
        "dual_live_evidence_index_path_invalid",
        "dual_live_evidence_index_path_missing",
        "dual_live_evidence_index_sha256_invalid",
        "dual_live_evidence_index_sha256_missing",
        "dual_live_evidence_root_invalid",
        "dual_live_evidence_root_missing",
        "dual_live_evidence_root_reparse",
        "dual_live_gate_internal_error",
        "dual_live_gate_stability_indeterminate",
        "dual_live_lock_abandoned",
        "dual_live_lock_access_refused",
        "dual_live_lock_acl_mismatch",
        "dual_live_lock_busy",
        "dual_live_lock_cleanup_failed",
        "dual_live_lock_closed",
        "dual_live_lock_invalid",
        "dual_live_lock_namespace_invalid",
        "dual_live_lock_namespace_squatted",
        "dual_live_lock_release_failed",
        "dual_live_lock_wrong_thread",
        "dual_live_network_guard_lost",
        "dual_live_network_guard_unavailable",
        "dual_live_platform_unsupported",
        "dual_live_scan_key_missing",
        "dual_live_send_authority_environment_present",
        "dual_live_settings_invalid",
        "dual_live_storage_invalid",
        "dual_live_storage_missing",
    }
)
_REQUIRED_ENVIRONMENT = (
    ("DATABASE_URL", "dual_live_database_missing"),
    ("STORAGE_DIR", "dual_live_storage_missing"),
    ("CONNECTOR_CAMPAIGN_EVIDENCE_ROOT", "dual_live_evidence_root_missing"),
    (
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH",
        "dual_live_evidence_index_path_missing",
    ),
    (
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256",
        "dual_live_evidence_index_sha256_missing",
    ),
    ("NRC_ADAMS_APS_SUBSCRIPTION_KEY", "dual_live_scan_key_missing"),
)
_LOW_LEVEL_INSTALLED = False
_REQUESTS_INSTALLED = False
_CONNECTOR_TRANSPORT_INSTALLED = False
_CONNECTOR_TRANSPORT_CLASSES: tuple[Any, Any] | None = None

_GENERIC_READ = 0x80000000
_FILE_READ_ATTRIBUTES = 0x0080
_FILE_SHARE_READ = 0x00000001
_OPEN_EXISTING = 3
_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
    _fields_ = (
        ("dwFileAttributes", wintypes.DWORD),
        ("ftCreationTime", wintypes.FILETIME),
        ("ftLastAccessTime", wintypes.FILETIME),
        ("ftLastWriteTime", wintypes.FILETIME),
        ("dwVolumeSerialNumber", wintypes.DWORD),
        ("nFileSizeHigh", wintypes.DWORD),
        ("nFileSizeLow", wintypes.DWORD),
        ("nNumberOfLinks", wintypes.DWORD),
        ("nFileIndexHigh", wintypes.DWORD),
        ("nFileIndexLow", wintypes.DWORD),
    )


class DualLiveGateError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class GateCheckResult:
    check_id: str
    status: Literal["PASS", "REFUSED"]
    code: str

    def __post_init__(self) -> None:
        if self.check_id not in GATE_CHECK_ORDER:
            raise DualLiveGateError("dual_live_gate_check_id_invalid")
        if self.status not in {"PASS", "REFUSED"}:
            raise DualLiveGateError("dual_live_gate_check_status_invalid")
        if not isinstance(self.code, str) or not _SAFE_CODE.fullmatch(self.code):
            raise DualLiveGateError("dual_live_gate_check_code_invalid")


def _fail(code: str) -> NoReturn:
    raise DualLiveGateError(code)


class DualLiveNetworkDenied(OSError):
    def __init__(self) -> None:
        self.code = "dual_live_network_denied"
        super().__init__(self.code)


def _deny_network(*_args: object, **_kwargs: object) -> None:
    raise DualLiveNetworkDenied


_LOW_LEVEL_HOOKS = (
    (socket.socket, "connect"),
    (socket.socket, "connect_ex"),
    (socket.socket, "bind"),
    (socket.socket, "sendto"),
    (socket, "create_connection"),
    (socket, "getaddrinfo"),
    (socket, "gethostbyname"),
    (socket, "gethostbyname_ex"),
    (socket, "gethostbyaddr"),
    (socket, "getnameinfo"),
    (socket, "getfqdn"),
)


def _install_low_level_guard() -> None:
    global _LOW_LEVEL_INSTALLED

    if _LOW_LEVEL_INSTALLED:
        if not all(getattr(owner, name) is _deny_network for owner, name in _LOW_LEVEL_HOOKS):
            raise RuntimeError("network guard changed")
        return

    for owner, name in _LOW_LEVEL_HOOKS:
        setattr(owner, name, _deny_network)
    if not all(getattr(owner, name) is _deny_network for owner, name in _LOW_LEVEL_HOOKS):
        raise RuntimeError("network guard incomplete")
    _LOW_LEVEL_INSTALLED = True


def _install_network_guard() -> None:
    global _REQUESTS_INSTALLED

    sys.dont_write_bytecode = True
    _install_low_level_guard()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import requests

    request_hooks = (
        (requests.api, "request"),
        (requests, "request"),
        (requests.sessions.Session, "request"),
        (requests.sessions.Session, "send"),
        (requests.adapters.HTTPAdapter, "send"),
    )
    if _REQUESTS_INSTALLED:
        if not all(getattr(owner, name) is _deny_network for owner, name in request_hooks):
            raise RuntimeError("requests guard changed")
        return

    for owner, name in request_hooks:
        setattr(owner, name, _deny_network)
    if not all(getattr(owner, name) is _deny_network for owner, name in request_hooks):
        raise RuntimeError("requests guard incomplete")
    if requests.Session.request is not _deny_network or requests.Session.send is not _deny_network:
        raise RuntimeError("requests aliases unguarded")
    _REQUESTS_INSTALLED = True


def _install_connector_transport_guard() -> None:
    global _CONNECTOR_TRANSPORT_CLASSES, _CONNECTOR_TRANSPORT_INSTALLED

    if not _base_network_guard_intact():
        raise RuntimeError("connector transport guard prerequisite missing")
    from app.services import connector_egress_transport

    classes = (
        connector_egress_transport.CountingHTTPAdapter,
        connector_egress_transport.BoundedConnectorTransport,
    )
    hooks = (
        (classes[0], "send"),
        (classes[1], "send_once"),
    )
    if _CONNECTOR_TRANSPORT_INSTALLED:
        if _CONNECTOR_TRANSPORT_CLASSES != classes or not all(
            getattr(owner, name) is _deny_network for owner, name in hooks
        ):
            raise RuntimeError("connector transport guard changed")
        return
    for owner, name in hooks:
        setattr(owner, name, _deny_network)
    if not all(getattr(owner, name) is _deny_network for owner, name in hooks):
        raise RuntimeError("connector transport guard incomplete")
    _CONNECTOR_TRANSPORT_CLASSES = classes
    _CONNECTOR_TRANSPORT_INSTALLED = True


def _base_network_guard_intact() -> bool:
    if not _LOW_LEVEL_INSTALLED or not all(
        getattr(owner, name) is _deny_network for owner, name in _LOW_LEVEL_HOOKS
    ):
        return False
    try:
        import requests
    except Exception:
        return False
    request_hooks = (
        (requests.api, "request"),
        (requests, "request"),
        (requests.sessions.Session, "request"),
        (requests.sessions.Session, "send"),
        (requests.adapters.HTTPAdapter, "send"),
    )
    return bool(
        _REQUESTS_INSTALLED
        and all(getattr(owner, name) is _deny_network for owner, name in request_hooks)
    )


def _network_guard_intact() -> bool:
    connector_classes = _CONNECTOR_TRANSPORT_CLASSES
    return bool(
        _base_network_guard_intact()
        and _CONNECTOR_TRANSPORT_INSTALLED
        and connector_classes is not None
        and connector_classes[0].send is _deny_network
        and connector_classes[1].send_once is _deny_network
    )


def _unsafe_backend_module_preloaded() -> bool:
    return any(
        name == "app"
        or name.startswith("app.")
        or name == "sqlalchemy"
        or name.startswith("sqlalchemy.")
        for name in sys.modules
    )


def _filetime_value(value: wintypes.FILETIME) -> int:
    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError:
        _fail("dual_live_database_custody_changed")
    return digest.hexdigest()


class _DatabaseFileCustody:
    __slots__ = ("path", "_handle", "_kernel32", "_initial_identity", "_closed")

    def __init__(self, path: Path, handle: int, kernel32: Any) -> None:
        self.path = path
        self._handle = handle
        self._kernel32 = kernel32
        self._closed = False
        self._initial_identity = self.stable_identity()

    @classmethod
    def open(cls, path: Path) -> "_DatabaseFileCustody":
        if os.name != "nt":
            _fail("dual_live_platform_unsupported")
        from app.services.dual_live_windows import (
            DualLiveWindowsError,
            assert_fixed_local_no_reparse_path_before_open,
            assert_open_handle_local_fixed,
        )

        try:
            expected_path = assert_fixed_local_no_reparse_path_before_open(
                path,
                code="dual_live_database_path_unsafe",
            )
        except DualLiveWindowsError as exc:
            raise DualLiveGateError("dual_live_database_path_unsafe") from exc
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        )
        kernel32.CreateFileW.restype = wintypes.HANDLE
        kernel32.GetFileInformationByHandle.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(_BY_HANDLE_FILE_INFORMATION),
        )
        kernel32.GetFileInformationByHandle.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.CreateFileW(
            str(expected_path),
            _GENERIC_READ | _FILE_READ_ATTRIBUTES,
            _FILE_SHARE_READ,
            None,
            _OPEN_EXISTING,
            _FILE_FLAG_OPEN_REPARSE_POINT,
            None,
        )
        if handle in (None, _INVALID_HANDLE_VALUE):
            _fail("dual_live_database_custody_refused")
        try:
            try:
                assert_open_handle_local_fixed(
                    int(handle),
                    expected_path=expected_path,
                    code="dual_live_database_path_unsafe",
                )
            except DualLiveWindowsError as exc:
                raise DualLiveGateError("dual_live_database_path_unsafe") from exc
            return cls(expected_path, int(handle), kernel32)
        except BaseException:
            kernel32.CloseHandle(handle)
            raise

    def __enter__(self) -> "_DatabaseFileCustody":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def stable_identity(self) -> tuple[int, int, int, int, str]:
        if self._closed:
            _fail("dual_live_database_custody_closed")
        information = _BY_HANDLE_FILE_INFORMATION()
        if not self._kernel32.GetFileInformationByHandle(
            self._handle, ctypes.byref(information)
        ):
            _fail("dual_live_database_custody_changed")
        if information.dwFileAttributes & (
            _FILE_ATTRIBUTE_DIRECTORY | _FILE_ATTRIBUTE_REPARSE_POINT
        ):
            _fail("dual_live_database_path_unsafe")
        file_index = (int(information.nFileIndexHigh) << 32) | int(
            information.nFileIndexLow
        )
        file_size = (int(information.nFileSizeHigh) << 32) | int(
            information.nFileSizeLow
        )
        return (
            int(information.dwVolumeSerialNumber),
            file_index,
            file_size,
            _filetime_value(information.ftLastWriteTime),
            _hash_file(self.path),
        )

    def assert_stable(self) -> None:
        if self.stable_identity() != self._initial_identity:
            _fail("dual_live_database_custody_changed")

    def close(self) -> None:
        if self._closed:
            return
        if not self._kernel32.CloseHandle(self._handle):
            _fail("dual_live_database_custody_cleanup_failed")
        self._closed = True


def _sql_text(statement: str) -> Any:
    from sqlalchemy import text

    return text(statement)


_DENIED_SQLITE_ACTION_NAMES = (
    "SQLITE_INSERT",
    "SQLITE_UPDATE",
    "SQLITE_DELETE",
    "SQLITE_CREATE_INDEX",
    "SQLITE_CREATE_TABLE",
    "SQLITE_CREATE_TEMP_INDEX",
    "SQLITE_CREATE_TEMP_TABLE",
    "SQLITE_CREATE_TEMP_TRIGGER",
    "SQLITE_CREATE_TEMP_VIEW",
    "SQLITE_CREATE_TRIGGER",
    "SQLITE_CREATE_VIEW",
    "SQLITE_DROP_INDEX",
    "SQLITE_DROP_TABLE",
    "SQLITE_DROP_TEMP_INDEX",
    "SQLITE_DROP_TEMP_TABLE",
    "SQLITE_DROP_TEMP_TRIGGER",
    "SQLITE_DROP_TEMP_VIEW",
    "SQLITE_DROP_TRIGGER",
    "SQLITE_DROP_VIEW",
    "SQLITE_ALTER_TABLE",
    "SQLITE_REINDEX",
    "SQLITE_ANALYZE",
    "SQLITE_ATTACH",
    "SQLITE_DETACH",
    "SQLITE_CREATE_VTABLE",
    "SQLITE_DROP_VTABLE",
)
_DENIED_SQLITE_ACTIONS = frozenset(
    getattr(sqlite3, name)
    for name in _DENIED_SQLITE_ACTION_NAMES
    if hasattr(sqlite3, name)
)


def _read_only_authorizer(
    action: int,
    argument_one: str | None,
    argument_two: str | None,
    _database: str | None,
    _trigger: str | None,
) -> int:
    if action in _DENIED_SQLITE_ACTIONS:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_PRAGMA:
        pragma = (argument_one or "").casefold()
        if pragma not in {
            "data_version",
            "database_list",
            "foreign_keys",
            "journal_mode",
            "query_only",
            "read_uncommitted",
            "schema_version",
            "table_info",
            "table_xinfo",
        }:
            return sqlite3.SQLITE_DENY
        if pragma in {
            "data_version",
            "database_list",
            "journal_mode",
            "query_only",
            "read_uncommitted",
            "schema_version",
        } and argument_two is not None:
            return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


class _ReadOnlyDatabase:
    __slots__ = ("path", "_custody", "_engine", "_closed")

    def __init__(self, path: Path, custody: _DatabaseFileCustody, engine: Any) -> None:
        self.path = path
        self._custody = custody
        self._engine = engine
        self._closed = False

    @classmethod
    def open(cls, path: Path) -> "_ReadOnlyDatabase":
        from sqlalchemy import create_engine
        from sqlalchemy.pool import NullPool

        if any(Path(f"{path}{suffix}").exists() for suffix in ("-journal", "-wal", "-shm")):
            _fail("dual_live_database_sidecar_present")
        custody = _DatabaseFileCustody.open(path)
        uri = f"file:{path.as_posix()}?mode=ro&cache=private"

        def connect() -> sqlite3.Connection:
            connection = sqlite3.connect(
                uri,
                uri=True,
                check_same_thread=True,
            )
            try:
                connection.execute("PRAGMA query_only=ON")
                if connection.execute("PRAGMA query_only").fetchone() != (1,):
                    _fail("dual_live_database_query_only_refused")
                row = connection.execute("PRAGMA journal_mode").fetchone()
                if row is None or str(row[0]).casefold() != "delete":
                    _fail("dual_live_database_journal_mode_unsafe")
                database_list = tuple(connection.execute("PRAGMA database_list"))
                if len(database_list) != 1 or database_list[0][1] != "main":
                    _fail("dual_live_database_attachment_unsafe")
                connection.set_authorizer(_read_only_authorizer)
                return connection
            except BaseException:
                connection.close()
                raise

        try:
            engine = create_engine(
                f"sqlite+pysqlite:///{path.as_posix()}",
                creator=connect,
                future=True,
                poolclass=NullPool,
            )
            database = cls(path, custody, engine)
            with database.session():
                pass
            return database
        except BaseException:
            custody.close()
            raise

    def __enter__(self) -> "_ReadOnlyDatabase":
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        primary: BaseException | None,
        _traceback: object,
    ) -> None:
        try:
            self.close()
        except BaseException as cleanup_error:
            if primary is None:
                raise
            primary.add_note(
                _safe_exception_code(
                    cleanup_error,
                    "dual_live_database_custody_cleanup_failed",
                )
            )

    @contextmanager
    def session(self) -> Iterator[Any]:
        from sqlalchemy.orm import Session

        if self._closed:
            _fail("dual_live_database_custody_closed")
        connection = self._engine.connect()
        session: Any = None
        primary: BaseException | None = None
        primary_traceback: Any = None
        cleanup_errors: list[BaseException] = []

        def record_error(error: BaseException) -> None:
            nonlocal primary, primary_traceback
            if primary is None:
                primary = error
                primary_traceback = error.__traceback__
            else:
                cleanup_errors.append(error)

        initial_version: int | None = None
        final_version: int | None = None
        database_list: tuple[Any, ...] | None = None
        try:
            initial_version = int(
                connection.exec_driver_sql("PRAGMA data_version").scalar_one()
            )
            connection.rollback()
            session = Session(
                bind=connection,
                autoflush=False,
                expire_on_commit=False,
                future=True,
            )
            try:
                yield session
            except BaseException as error:
                record_error(error)
            if session is not None:
                try:
                    if session.in_transaction():
                        session.rollback()
                except BaseException as error:
                    record_error(error)
                try:
                    session.close()
                except BaseException as error:
                    record_error(error)
            try:
                final_version = int(
                    connection.exec_driver_sql("PRAGMA data_version").scalar_one()
                )
            except BaseException as error:
                record_error(error)
            try:
                database_list = tuple(
                    connection.exec_driver_sql("PRAGMA database_list").all()
                )
            except BaseException as error:
                record_error(error)
            try:
                connection.rollback()
            except BaseException as error:
                record_error(error)
            if (
                initial_version is not None
                and final_version is not None
                and final_version != initial_version
            ):
                record_error(DualLiveGateError("dual_live_database_data_version_changed"))
            if database_list is not None and (
                len(database_list) != 1 or database_list[0][1] != "main"
            ):
                record_error(DualLiveGateError("dual_live_database_attachment_unsafe"))
        except BaseException as error:
            record_error(error)
        finally:
            if session is not None:
                try:
                    if session.in_transaction():
                        session.rollback()
                except BaseException as error:
                    record_error(error)
                try:
                    session.close()
                except BaseException as error:
                    record_error(error)
            try:
                connection.close()
            except BaseException as error:
                record_error(error)
            try:
                self.assert_stable()
            except BaseException as error:
                record_error(error)

        if primary is not None:
            for cleanup_error in cleanup_errors:
                primary.add_note(
                    _safe_exception_code(
                        cleanup_error,
                        "dual_live_database_custody_cleanup_failed",
                    )
                )
            raise primary.with_traceback(primary_traceback)

    def stable_identity(self) -> tuple[int, int, int, int, str]:
        self._assert_no_sidecars()
        return self._custody.stable_identity()

    def assert_stable(self) -> None:
        self._assert_no_sidecars()
        self._custody.assert_stable()

    def _assert_no_sidecars(self) -> None:
        if any(Path(f"{self.path}{suffix}").exists() for suffix in ("-journal", "-wal", "-shm")):
            _fail("dual_live_database_sidecar_present")

    def close(self) -> None:
        if self._closed:
            return
        errors: list[BaseException] = []
        try:
            self._engine.dispose(close=True)
        except BaseException as error:
            errors.append(error)
        try:
            self._custody.close()
        except BaseException as error:
            errors.append(error)
        self._closed = True
        if errors:
            primary = errors[0]
            for cleanup_error in errors[1:]:
                primary.add_note(
                    _safe_exception_code(
                        cleanup_error,
                        "dual_live_database_custody_cleanup_failed",
                    )
                )
            raise primary


def _emit(payload: Mapping[str, Any]) -> None:
    line = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    sys.stdout.write(line + "\n")


def _emit_refusal(code: str) -> int:
    _emit(
        {
            "schema_id": "project6.dual_live_gate_refusal.v1",
            "status": "REFUSED",
            "fresh_live": False,
            "evaluation_complete": False,
            "code": code,
        }
    )
    return 2


def _casefold_environment(environ: Mapping[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for name, value in environ.items():
        if not isinstance(name, str) or not isinstance(value, str):
            _fail("dual_live_environment_invalid")
        key = name.casefold()
        if key in normalized and normalized[key] != value:
            _fail("dual_live_environment_ambiguous")
        normalized[key] = value
    return normalized


def _environment_refusal(environ: Mapping[str, str]) -> str | None:
    try:
        normalized_environment = _casefold_environment(environ)
    except DualLiveGateError as exc:
        return exc.code
    raw_flag = normalized_environment.get("connector_live_egress_enabled", "")
    normalized = raw_flag.casefold()
    if normalized not in _FALSE_VALUES | _TRUE_VALUES:
        return "dual_live_egress_flag_invalid"
    if normalized in _TRUE_VALUES:
        return "dual_live_egress_enabled"
    if any(
        normalized_environment.get(name.casefold(), "") != ""
        for name in _AUTHORITY_VARIABLES
    ):
        return "dual_live_send_authority_environment_present"
    return None


def _valid_campaign_id(value: str) -> bool:
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError):
        return False
    return parsed.version == 4 and str(parsed) == value


def _valid_parent_run_id(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError):
        return False
    return parsed.version == 5 and str(parsed) == value


def _parse_arguments(argv: Sequence[str]) -> tuple[str | None, str | None, str | None]:
    values: dict[str, str | None] = {
        "campaign_id": None,
        "campaign_fingerprint": None,
    }
    seen: set[str] = set()
    structural_error = False
    index = 0

    while index < len(argv):
        token = argv[index]
        field = _OPTIONS.get(token)
        if field is None or field in seen:
            structural_error = True
            index += 1
            continue
        seen.add(field)
        if index + 1 >= len(argv):
            index += 1
            continue
        candidate = argv[index + 1]
        if candidate in _OPTIONS:
            index += 1
            continue
        if candidate.startswith("--"):
            structural_error = True
            index += 2
            continue
        values[field] = candidate
        index += 2

    if structural_error:
        return None, None, "dual_live_arguments_invalid"
    campaign_id = values["campaign_id"]
    campaign_fingerprint = values["campaign_fingerprint"]
    if campaign_id is None:
        return None, None, "dual_live_campaign_id_missing"
    if not _valid_campaign_id(campaign_id):
        return None, None, "dual_live_campaign_id_invalid"
    if campaign_fingerprint is None:
        return None, None, "dual_live_campaign_fingerprint_missing"
    if not _LOWERCASE_SHA256.fullmatch(campaign_fingerprint):
        return None, None, "dual_live_campaign_fingerprint_invalid"
    return campaign_id, campaign_fingerprint, None


def _backend_path() -> None:
    backend = str(_BACKEND)
    if backend not in sys.path:
        sys.path.insert(0, backend)


def _load_settings(environ: Mapping[str, str]) -> Any:
    from app.core.config import Settings

    normalized = _casefold_environment(environ)
    values: dict[str, str] = {}
    for field in Settings.model_fields.values():
        alias = field.alias
        if isinstance(alias, str) and alias.casefold() in normalized:
            value = normalized[alias.casefold()]
            if alias == "CONNECTOR_LIVE_EGRESS_ENABLED" and value == "":
                continue
            values[alias] = value
    try:
        return Settings.model_validate(values)
    except Exception:
        _fail("dual_live_settings_invalid")


def _required_environment_values(environ: Mapping[str, str]) -> dict[str, str]:
    normalized = _casefold_environment(environ)
    required: dict[str, str] = {}
    for name, missing_code in _REQUIRED_ENVIRONMENT:
        value = normalized.get(name.casefold(), "")
        if value == "":
            _fail(missing_code)
        required[name] = value
    return required


def _path_has_reparse_component(path: Path) -> bool:
    if os.name != "nt":
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFileAttributesW.argtypes = (wintypes.LPCWSTR,)
    kernel32.GetFileAttributesW.restype = wintypes.DWORD
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        attributes = int(kernel32.GetFileAttributesW(str(current)))
        if attributes == 0xFFFFFFFF:
            return True
        if attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
            return True
    return False


def _local_absolute_path(raw: str, *, code: str) -> Path:
    from app.services.dual_live_windows import (
        DualLiveWindowsError,
        assert_local_fixed_path_before_touch,
    )

    try:
        return assert_local_fixed_path_before_touch(raw, code=code)
    except DualLiveWindowsError:
        _fail(code)
    raise AssertionError("unreachable")


def _existing_local_path(raw: str, *, kind: Literal["file", "directory"], code: str) -> Path:
    from app.services.dual_live_windows import (
        DualLiveWindowsError,
        assert_fixed_local_no_reparse_path_before_open,
    )

    try:
        candidate = assert_fixed_local_no_reparse_path_before_open(raw, code=code)
    except DualLiveWindowsError:
        _fail(code)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        _fail(code)
    if kind == "file" and not resolved.is_file():
        _fail(code)
    if kind == "directory" and not resolved.is_dir():
        _fail(code)
    return resolved


def _database_path_from_url(raw_url: str) -> Path:
    prefix = "sqlite:///"
    if not raw_url.startswith(prefix) or any(token in raw_url for token in ("?", "#")):
        _fail("dual_live_database_url_invalid")
    raw_path = raw_url[len(prefix) :]
    if not raw_path or raw_path == ":memory:" or raw_path.startswith("file:"):
        _fail("dual_live_database_url_invalid")
    return _local_absolute_path(raw_path, code="dual_live_database_path_unsafe")


def _settings_and_paths(
    environ: Mapping[str, str],
) -> tuple[Any, Path, Path]:
    required = _required_environment_values(environ)
    normalized_environment = _casefold_environment(environ)
    if any(
        normalized_environment.get(name.casefold(), "") != ""
        for name in _AUTHORITY_VARIABLES
    ):
        _fail("dual_live_send_authority_environment_present")
    if not _LOWERCASE_SHA256.fullmatch(
        required["CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256"]
    ):
        _fail("dual_live_evidence_index_sha256_invalid")
    evidence_root = _local_absolute_path(
        required["CONNECTOR_CAMPAIGN_EVIDENCE_ROOT"],
        code="dual_live_evidence_root_invalid",
    )
    evidence_index_path = _local_absolute_path(
        required["CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH"],
        code="dual_live_evidence_index_path_invalid",
    )
    storage_path = _local_absolute_path(
        required["STORAGE_DIR"],
        code="dual_live_storage_invalid",
    )
    database_path = _database_path_from_url(required["DATABASE_URL"])
    from app.services.dual_live_windows import (
        DualLiveWindowsError,
        assert_fixed_local_no_reparse_path_before_open,
    )

    for path, code in (
        (evidence_root, "dual_live_evidence_root_invalid"),
        (evidence_index_path, "dual_live_evidence_index_path_invalid"),
        (storage_path, "dual_live_storage_invalid"),
        (database_path, "dual_live_database_path_unsafe"),
    ):
        try:
            assert_fixed_local_no_reparse_path_before_open(path, code=code)
        except DualLiveWindowsError:
            _fail(code)
    settings = _load_settings(environ)
    if settings.connector_live_egress_enabled:
        _fail("dual_live_egress_enabled")
    return settings, evidence_root, database_path


def _definition_sha256(
    chain: Any,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
) -> str:
    matches = tuple(
        item
        for item in chain.head.campaigns
        if str(item.campaign_id) == campaign_id
        and item.campaign_fingerprint == campaign_fingerprint
    )
    if len(matches) != 1:
        _fail("dual_live_campaign_evidence_missing")
    digest = matches[0].raw_definition_sha256
    if not isinstance(digest, str) or not _LOWERCASE_SHA256.fullmatch(digest):
        _fail("dual_live_campaign_evidence_invalid")
    return digest


def _chain_snapshot(chain: Any) -> tuple[tuple[int, str, bytes], ...]:
    return tuple(
        (item.model.revision, item.raw_sha256, item.raw_bytes)
        for item in chain.revisions
    )


def _g01_pass() -> GateCheckResult:
    return GateCheckResult(
        check_id="G01_GATE_REFUSAL_PRECONDITIONS",
        status="PASS",
        code="g01_gate_preconditions_passed",
    )


def _g02_pass() -> GateCheckResult:
    if not _network_guard_intact():
        _fail("dual_live_network_guard_lost")
    return GateCheckResult(
        check_id="G02_GATE_NETWORK_DENIAL",
        status="PASS",
        code="g02_network_denial_passed",
    )


def _report_is_exact(
    report: object,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
) -> bool:
    if type(report) is not dict:
        return False
    expected_keys = [
        "schema_id",
        "campaign_id",
        "expected_campaign_fingerprint",
        "status",
        "fresh_live",
        "evaluation_complete",
        "code",
        "checks",
        "nonclaims",
    ]
    if list(report) != expected_keys:
        return False
    checks = report.get("checks")
    if type(checks) is not list or len(checks) != len(_EXPECTED_EVALUATOR_CHECK_ORDER):
        return False
    statuses: list[str] = []
    codes: list[str] = []
    for expected_check_id, check in zip(_EXPECTED_EVALUATOR_CHECK_ORDER, checks):
        if type(check) is not dict or list(check) != [
            "check_id",
            "status",
            "code",
            "evidence",
        ]:
            return False
        check_status = check.get("status")
        check_code = check.get("code")
        if (
            check.get("check_id") != expected_check_id
            or check_status not in {"PASS", "FAIL", "INDETERMINATE"}
            or not isinstance(check_code, str)
            or _SAFE_CODE.fullmatch(check_code) is None
            or not _evidence_is_safe(
                check.get("evidence"),
                check_id=expected_check_id,
                check_status=str(check_status),
            )
        ):
            return False
        statuses.append(str(check_status))
        codes.append(check_code)
    if "INDETERMINATE" in statuses:
        aggregate_status = "INDETERMINATE"
        aggregate_code = codes[statuses.index("INDETERMINATE")]
    elif "FAIL" in statuses:
        aggregate_status = "FAIL"
        aggregate_code = codes[statuses.index("FAIL")]
    else:
        aggregate_status = "PASS"
        aggregate_code = "all_checks_pass"
    status = report.get("status")
    return bool(
        report.get("schema_id") == "project6.dual_live_evaluation.v1"
        and report.get("campaign_id") == campaign_id
        and report.get("expected_campaign_fingerprint") == campaign_fingerprint
        and status == aggregate_status
        and report.get("fresh_live") is (status == "PASS")
        and report.get("evaluation_complete") is (status in {"PASS", "FAIL"})
        and report.get("code") == aggregate_code
        and type(report.get("nonclaims")) is list
        and tuple(report["nonclaims"]) == _EXPECTED_EVALUATOR_NONCLAIMS
        and len(json.dumps(report, ensure_ascii=True)) <= 262_144
    )


def _evidence_is_safe(
    value: object,
    *,
    check_id: str,
    check_status: str | None = None,
) -> bool:
    if type(value) is not dict or len(value) > 16:
        return False
    if "reason_code" in value:
        return bool(
            check_status == "INDETERMINATE"
            and list(value) == ["domain", "reason_code"]
            and value.get("domain") in _SAFE_EVIDENCE_DOMAINS
            and isinstance(value.get("reason_code"), str)
            and _SAFE_CODE.fullmatch(value["reason_code"])
        )
    if any(key in value for key in _RUNTIME_START_EVIDENCE_KEYS[2:]):
        return bool(
            check_id == "R05_RUNTIME_CHAIN"
            and check_status == "PASS"
            and tuple(value) == _RUNTIME_START_EVIDENCE_KEYS
            and type(value["record_count"]) is int
            and 0 <= value["record_count"] <= (2**63) - 1
            and isinstance(value["terminal_record_sha256"], str)
            and _LOWERCASE_SHA256.fullmatch(value["terminal_record_sha256"])
            and isinstance(value["dependency_set_sha256"], str)
            and _LOWERCASE_SHA256.fullmatch(value["dependency_set_sha256"])
            and type(value["phase_a_timeout_ms"]) is int
            and 1 <= value["phase_a_timeout_ms"] <= 0xFFFFFFFE
            and type(value["phase_b_timeout_ms"]) is int
            and 1 <= value["phase_b_timeout_ms"] <= 0xFFFFFFFE
        )
    if "connector_results" in value or "combined_result" in value:
        if (
            check_id != "F09_CONNECTOR_AND_COMBINED_REPORTS"
            or list(value) != ["connector_results", "combined_result"]
        ):
            return False
        connector_results = value["connector_results"]
        combined_result = value["combined_result"]
        return bool(
            type(connector_results) is list
            and len(connector_results) == 2
            and tuple(
                item.get("connector_key")
                for item in connector_results
                if type(item) is dict
            )
            == _EXPECTED_CONNECTOR_KEYS
            and all(
                type(item) is dict
                and list(item) == ["connector_key", "projection_sha256"]
                and isinstance(item.get("projection_sha256"), str)
                and _LOWERCASE_SHA256.fullmatch(item["projection_sha256"])
                for item in connector_results
            )
            and type(combined_result) is dict
            and list(combined_result) == ["projection_sha256"]
            and isinstance(combined_result.get("projection_sha256"), str)
            and _LOWERCASE_SHA256.fullmatch(combined_result["projection_sha256"])
        )
    for key, item in value.items():
        if key not in _SAFE_EVIDENCE_KEYS:
            return False
        if key in _HASH_EVIDENCE_KEYS:
            if not isinstance(item, str) or _LOWERCASE_SHA256.fullmatch(item) is None:
                return False
        elif key == "code_revision":
            if not isinstance(item, str) or re.fullmatch(r"[0-9a-f]{7,64}", item) is None:
                return False
        elif key == "process_boot_id":
            if not isinstance(item, str) or _LOWERCASE_SHA256.fullmatch(item) is None:
                return False
        elif key == "parent_run_id":
            if not _valid_parent_run_id(item):
                return False
        elif key == "terminal_hashes":
            if type(item) is not list or len(item) > 16 or not all(
                isinstance(digest, str) and _LOWERCASE_SHA256.fullmatch(digest)
                for digest in item
            ):
                return False
        elif key == "domain":
            if item not in _SAFE_EVIDENCE_DOMAINS:
                return False
        elif key == "proof_class":
            if item != "fresh_live":
                return False
        elif key == "terminal_state":
            if item != "completed":
                return False
        elif key == "encoding":
            if item != "utf-8":
                return False
        elif key == "proof_stream_phase_order":
            if item != "A_then_B":
                return False
        elif key == "terminal_boundary":
            if item != "handoff_prepared":
                return False
        elif key in _NONNEGATIVE_INTEGER_EVIDENCE_KEYS:
            if type(item) is not int or not 0 <= item <= (2**63) - 1:
                return False
        elif type(item) is bool:
            continue
        elif type(item) is not int or not -(2**63) <= item <= (2**63) - 1:
            return False
    return True


def _exit_code_for_status(status: str) -> int:
    if status == "PASS":
        return 0
    if status == "FAIL":
        return 1
    if status == "INDETERMINATE":
        return 2
    _fail("dual_live_evaluation_status_invalid")


def _safe_exception_code(exc: BaseException, fallback: str) -> str:
    code = getattr(exc, "code", None)
    if isinstance(code, str) and code in _KNOWN_SAFE_EXCEPTION_CODES:
        return code
    return fallback


@contextmanager
def _suppress_pymupdf_layout_recommendation() -> Iterator[None]:
    """Keep the gate stdout JSON-only while preserving the caller environment."""

    key = "PYMUPDF_SUGGEST_LAYOUT_ANALYZER"
    prior_present = key in os.environ
    prior_value = os.environ.get(key)
    os.environ[key] = "0"
    try:
        yield
    finally:
        if prior_present:
            assert prior_value is not None
            os.environ[key] = prior_value
        else:
            os.environ.pop(key, None)


def _run_guarded_evaluation(
    *,
    campaign_id: str,
    campaign_fingerprint: str,
    environ: Mapping[str, str],
) -> dict[str, Any]:
    settings, evidence_root, database_path = _settings_and_paths(environ)
    from app.services.connector_campaign_log_capture import (
        verify_connector_campaign_log_capture_read_only,
    )
    from app.services.connector_egress_authorization import (
        load_evidence_index_chain_read_only,
    )
    from app.services.dual_live_windows import acquire_proof_locks_staged

    entered = False
    indeterminate_report_builder: Any = None
    try:
        chain_holder: dict[str, Any] = {}

        def resolve_definition_sha256() -> str:
            chain = load_evidence_index_chain_read_only(settings)
            chain_holder["chain"] = chain
            return _definition_sha256(
                chain,
                campaign_id=campaign_id,
                campaign_fingerprint=campaign_fingerprint,
            )

        with acquire_proof_locks_staged(
            evidence_root,
            campaign_id,
            campaign_fingerprint,
            resolve_definition_sha256,
        ):
            chain = chain_holder.get("chain")
            if chain is None:
                _fail("dual_live_evidence_chain_unavailable")
            _existing_local_path(
                str(settings.storage_dir),
                kind="directory",
                code="dual_live_storage_invalid",
            )
            database_path = _existing_local_path(
                str(database_path),
                kind="file",
                code="dual_live_database_path_unsafe",
            )
            initial_chain = _chain_snapshot(chain)
            with _ReadOnlyDatabase.open(database_path) as database:
                initial_database = database.stable_identity()
                try:
                    with database.session() as session:
                        verify_connector_campaign_log_capture_read_only(
                            session,
                            chain,
                            campaign_id,
                            campaign_fingerprint,
                        )
                except Exception as exc:
                    raise DualLiveGateError("dual_live_capture_unsealed") from exc
                _g01_pass()
                _install_connector_transport_guard()
                _g02_pass()

                from app.services.dual_live_evaluator import (
                    build_indeterminate_dual_live_report as public_indeterminate_builder,
                    evaluate_dual_live_proof,
                )

                indeterminate_report_builder = public_indeterminate_builder
                entered = True
                with database.session() as session:
                    first = evaluate_dual_live_proof(
                        session,
                        campaign_id=campaign_id,
                        expected_campaign_fingerprint=campaign_fingerprint,
                        settings=settings,
                    )
                if not _report_is_exact(
                    first,
                    campaign_id=campaign_id,
                    campaign_fingerprint=campaign_fingerprint,
                ):
                    _fail("dual_live_evaluation_contract_invalid")
                _g02_pass()

                with database.session() as session:
                    second = evaluate_dual_live_proof(
                        session,
                        campaign_id=campaign_id,
                        expected_campaign_fingerprint=campaign_fingerprint,
                        settings=settings,
                    )
                if second != first:
                    _fail("dual_live_evaluation_snapshot_changed")
                final_chain = load_evidence_index_chain_read_only(settings)
                if _chain_snapshot(final_chain) != initial_chain:
                    _fail("dual_live_evidence_chain_changed")
                with database.session() as session:
                    verify_connector_campaign_log_capture_read_only(
                        session,
                        final_chain,
                        campaign_id,
                        campaign_fingerprint,
                    )
                _g02_pass()
                if database.stable_identity() != initial_database:
                    _fail("dual_live_database_custody_changed")
                return first
    except Exception as exc:
        if not entered:
            raise
        code = _safe_exception_code(exc, "dual_live_gate_stability_indeterminate")
        if indeterminate_report_builder is None:
            raise
        return indeterminate_report_builder(
            campaign_id=campaign_id,
            expected_campaign_fingerprint=campaign_fingerprint,
            code=code,
        )


def main(
    argv: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    sys.dont_write_bytecode = True
    arguments = list(sys.argv[1:] if argv is None else argv)
    environment = os.environ if environ is None else environ

    try:
        _install_low_level_guard()
    except Exception:
        return _emit_refusal("dual_live_gate_internal_error")

    environment_error = _environment_refusal(environment)
    if environment_error is not None:
        return _emit_refusal(environment_error)

    campaign_id, campaign_fingerprint, argument_error = _parse_arguments(arguments)
    if argument_error is not None:
        return _emit_refusal(argument_error)
    if campaign_id is None or campaign_fingerprint is None:
        return _emit_refusal("dual_live_gate_internal_error")

    try:
        if not sys.flags.isolated:
            return _emit_refusal("dual_live_isolated_mode_required")
        _install_network_guard()
        if _unsafe_backend_module_preloaded():
            raise DualLiveGateError("dual_live_gate_internal_error")
        _backend_path()
        if not _base_network_guard_intact():
            raise DualLiveGateError("dual_live_network_guard_unavailable")
        with _suppress_pymupdf_layout_recommendation():
            report = _run_guarded_evaluation(
                campaign_id=campaign_id,
                campaign_fingerprint=campaign_fingerprint,
                environ=environment,
            )
        if not _report_is_exact(
            report,
            campaign_id=campaign_id,
            campaign_fingerprint=campaign_fingerprint,
        ):
            raise DualLiveGateError("dual_live_evaluation_contract_invalid")
        _emit(report)
        return _exit_code_for_status(str(report["status"]))
    except Exception as exc:
        return _emit_refusal(_safe_exception_code(exc, "dual_live_gate_internal_error"))


if __name__ == "__main__":
    raise SystemExit(main())
