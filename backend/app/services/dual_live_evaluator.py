from __future__ import annotations

import ast
import hashlib
import html
import inspect
import json
import os
import re
import stat
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path, PureWindowsPath
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal, NoReturn
from urllib.parse import unquote_to_bytes
from uuid import NAMESPACE_URL, UUID, uuid5

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.core.config import Settings


EvaluationStatus = Literal["PASS", "FAIL", "INDETERMINATE"]

_LOWERCASE_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LOWERCASE_CODE_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_PERCENT_ESCAPE = re.compile(r"%[0-9A-Fa-f]{2}")
_EXPECTED_CONNECTORS = ("nrc_adams_aps", "sciencebase_mcs")
_EXPECTED_STREAM_FILES = (
    "app.jsonl",
    "http.jsonl",
    "stdout.log",
    "stderr.log",
)
_PACKAGE_KINDS = ("canonical_internal", "user_facing", "review_facing")
_PACKAGE_SCHEMA_IDS = {
    "canonical_internal": "layer3.canonical_internal_package.v1",
    "user_facing": "layer3.user_facing_package.v1",
    "review_facing": "layer3.review_facing_package.v1",
}
_RUNTIME_START_PAYLOAD_KEYS = (
    "code_revision",
    "wrapper_image_sha256",
    "interpreter_image_sha256",
    "dependency_set_sha256",
    "phase_timeout_contract",
    "mutex_identity_sha256",
)
_PHASE_TIMEOUT_CONTRACT_KEYS = frozenset(
    (
        "schema_id",
        "phase_a_timeout_ms",
        "phase_b_timeout_ms",
        "fixed_non_egress_overhead_ms",
        "counter_ack_timeout_ms",
        "connector_grants",
    )
)
_PHASE_TIMEOUT_GRANT_KEYS = frozenset(
    (
        "connector_key",
        "max_physical_requests",
        "request_timeout_seconds",
        "min_request_interval_ms",
    )
)
_PHASE_TIMEOUT_SCHEMA_ID = "project6.dual_live_phase_timeout.v1"
_PHASE_A_TIMEOUT_MILLISECONDS = 205_750
_PHASE_B_TIMEOUT_MILLISECONDS = 30_000
_FIXED_NON_EGRESS_OVERHEAD_MILLISECONDS = 30_000
_COUNTER_ACK_TIMEOUT_MILLISECONDS = 5_000
_EXPECTED_PHASE_TIMEOUT_GRANTS = (
    ("nrc_adams_aps", 2, 30, 250),
    ("sciencebase_mcs", 3, 30, 250),
)
_WINDOWS_MIB_TCP_STATES = (
    "MIB_TCP_STATE_CLOSED",
    "MIB_TCP_STATE_LISTEN",
    "MIB_TCP_STATE_SYN_SENT",
    "MIB_TCP_STATE_SYN_RCVD",
    "MIB_TCP_STATE_ESTAB",
    "MIB_TCP_STATE_FIN_WAIT1",
    "MIB_TCP_STATE_FIN_WAIT2",
    "MIB_TCP_STATE_CLOSE_WAIT",
    "MIB_TCP_STATE_CLOSING",
    "MIB_TCP_STATE_LAST_ACK",
    "MIB_TCP_STATE_TIME_WAIT",
    "MIB_TCP_STATE_DELETE_TCB",
)

MAX_DB_ROWS = 100_000
MAX_DB_VALUE_BYTES = 64 * 1024
MAX_DB_JSON_TOKENS = 1_000_000
MAX_SCAN_FILES = 4_096
MAX_SCAN_NODES = 8_192
MAX_SCAN_FILE_BYTES = 16 * 1024 * 1024
MAX_SCAN_TOTAL_BYTES = 512 * 1024 * 1024
MAX_SOURCE_BYTES = 64 * 1024 * 1024

_DRIVE_FIXED = 3
_WINDOWS_RESERVED_COMPONENTS = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)
_AUTHORITY_CLEARED_POSTURE_SHA256 = (
    "59629217f25b985366b9b16a9f6bd7b9a45d5544375dc04f847f1b7bc1e07cd2"
)
_CHILD_BOOT_SCHEMA_ID = "project6.dual_live_owned_boot.v1"
_CHILD_CONTROL_SCHEMA_ID = "project6.dual_live_child_control.v1"
_CHILD_STATUS_SCHEMA_ID = "project6.dual_live_child_status.v1"
_CHILD_PROOF_SCHEMA_ID = "project6.dual_live_child_proof.v1"
_CHILD_PROOF_TOP_KEYS = (
    "event",
    "ordinal",
    "payload",
    "phase",
    "previous_record_sha256",
    "process_boot_id",
    "record_sha256",
    "schema_id",
    "status_nonce_sha256",
)
_CHILD_PROOF_SEQUENCE = (
    ("A", 1, "acquisition_boundary"),
    ("B", 1, "guard"),
    ("B", 2, "downstream_chain"),
    ("B", 3, "guard"),
)
_CHILD_PROOF_DENIED_ROUTES = (
    "dns",
    "http",
    "socket",
    "subprocess",
    "connector_transport",
)
_PHASE_B_NRC_ACTIONS = (
    "nrc_preflight",
    "nrc_source_preview",
    "nrc_material_preview",
    "nrc_gate_b_decision",
    "nrc_gate_c_typing",
    "nrc_plan_preview",
    "nrc_plan_approval",
    "nrc_execution_selection",
    "nrc_analysis_execution_start",
    "nrc_execution_result_review",
    "nrc_package_review_preview",
    "nrc_package_construction_commit",
    "nrc_package_review_submit",
    "nrc_handoff_export_prepare",
)
_PHASE_B_SCIENCEBASE_ACTIONS = (
    "sciencebase_material_preview",
    "sciencebase_gate_b_decision",
    "sciencebase_gate_c_typing",
    "sciencebase_plan_preview",
    "sciencebase_plan_approval",
    "sciencebase_execution_selection",
    "sciencebase_analysis_execution_start",
    "sciencebase_execution_result_review",
    "sciencebase_package_review_preview",
    "sciencebase_package_construction_commit",
    "sciencebase_package_review_submit",
    "sciencebase_handoff_export_prepare",
)
_PHASE_B_DOWNSTREAM_ACTIONS = (
    "nrc_strict_parse",
    "nrc_origin_receipt",
    "sciencebase_origin_receipt",
    *_PHASE_B_NRC_ACTIONS,
    *_PHASE_B_SCIENCEBASE_ACTIONS,
)
_PHASE_B_SOURCE_SHAPES = MappingProxyType(
    {
        "nrc_adams_aps": "aps_content_document",
        "sciencebase_mcs": "strict_sciencebase_connector_single_source",
    }
)
_PHASE_B_PACKAGE_PREVIEW_PREFIXES = MappingProxyType(
    {
        "nrc_adams_aps": "l3-qual-aps-package-preview-",
        "sciencebase_mcs": "l3-source-intake-package-preview-",
    }
)
_PHASE_B_SOURCE_BINDING_KEYS = frozenset(
    {
        "analysis_plan_id",
        "analysis_run_id",
        "candidate_id",
        "connector_key",
        "connector_origin_receipt_hash",
        "connector_run_id",
        "connector_run_target_id",
        "construction_basis_hash",
        "handoff_export_envelope_ref",
        "output_package_ids",
        "package_kinds",
        "package_review_preview_hash",
        "package_review_submit_record_ref",
        "pass_run_id",
        "payload_hashes",
        "prepare_record_ref",
        "reconciliation_record_id",
        "result_review_record_ref",
        "session_id",
        "source_shape",
        "source_record_id",
    }
)

_CHECK_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "A",
        (
            "INPUT_IDENTITY",
            "INDEX_LINEAR_HEAD",
            "ARCHIVE_EXACT",
            "SLICE_CARDINALITY",
            "SELECTED_UNION",
            "INTRODUCTION_PARITY",
            "MARKER_ONE_USE",
            "ORIGINAL_WINDOWS",
            "CODE_CAMPAIGN_FINGERPRINTS",
            "PROOF_CLASS",
        ),
    ),
    (
        "R",
        (
            "CAPTURE_MEMBERSHIP",
            "MANIFEST_FILE_HASHES",
            "SEAL_PARITY",
            "SEAL_EVENT_PARITY",
            "RUNTIME_CHAIN",
            "STARTUP_LOGGER_CENSUS",
            "EXIT_LOGGER_CENSUS",
            "PHASE_A_IDENTITY",
            "PHASE_A_JOB_ZERO",
            "PHASE_A_SOCKET_QUIESCENCE",
            "AUTHORITY_CLEARED",
            "PHASE_B_GUARDS",
            "PHASE_B_JOB_ZERO",
            "RUNTIME_TERMINAL",
            "WRAPPER_NETWORK_INERT",
            "PHASE_A_RAW_ONLY",
            "PHASE_B_STRICT_FLOW",
            "PHASE_A_TERMINAL_ONCE",
            "A_TO_B_ORDER",
            "FOUR_STREAM_CLOSEOUT",
            "EXTANT_RUN_SEAL_EVENTS",
            "CAPTURE_START_CONTRACT",
        ),
    ),
    (
        "L",
        (
            "RUN_CARDINALITY",
            "TERMINAL_EVENT",
            "POST_TERMINAL_EXTINCTION",
            "LEDGER_RECONSTRUCTION",
            "COUNTER_BIJECTION",
            "COUNTER_BOOT",
            "BYTE_ALLOWANCE",
            "REQUEST_CADENCE",
            "TRANSPORT_POLICY",
            "FRESH_200_BYTES",
            "NRC_FIRST_BINDING",
            "RESERVATION_RESOLUTION",
        ),
    ),
    (
        "D",
        (
            "ORIGIN_RECEIPT",
            "RAW_PROVENANCE_LINKAGE",
            "LAYER3_EXECUTION",
            "REVIEW_RESULT",
            "PACKAGE_SET",
            "PACKAGE_PAYLOAD",
            "SUBMIT_RECEIPT",
            "HANDOFF_RECEIPT",
        ),
    ),
    (
        "C",
        (
            "STRICT_NULLS",
            "DB_SCALAR_JSON_SCAN",
            "NON_SOURCE_FILE_SCAN",
            "SERIALIZATION_EVENT_SCAN",
            "RUNTIME_LOG_SCAN",
            "BOUNDED_DECODERS",
            "SOURCE_EXEMPTION",
            "SECRET_SCAN",
        ),
    ),
    (
        "F",
        (
            "EVIDENCE_STABILITY",
            "DATABASE_STABILITY",
            "NONCLAIMS_REPORT",
            "READ_ONLY_EVALUATION",
            "PROJECTION_REDERIVATION",
            "NO_EGRESS_DEPENDENCY",
            "PUBLIC_API_CONTRACT",
            "RESULT_AGGREGATION",
            "CONNECTOR_AND_COMBINED_REPORTS",
        ),
    ),
)

EVALUATOR_CHECK_ORDER = tuple(
    f"{prefix}{ordinal:02d}_{name}"
    for prefix, names in _CHECK_GROUPS
    for ordinal, name in enumerate(names, start=1)
)

EVALUATOR_NONCLAIMS: tuple[str, ...] = (
    "offline local-experiment evidence only",
    "no external live acquisition performed by evaluation",
    "no signature or WORM custody claim",
    "no cryptographic nonrepudiation claim",
    "no owning-account compromise resistance claim",
    "no coherent all-domain rewrite detection claim",
    "no visibility into OS, proxy, provider, or machine-global logs",
    "no deployment or production readiness claim",
)


class DualLiveEvaluationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _freeze_evidence_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_evidence(value)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_evidence_value(item) for item in value)
    if isinstance(value, (str, int, bool, type(None))):
        return value
    raise DualLiveEvaluationError("dual_live_check_evidence_invalid")


def _freeze_evidence(value: Mapping[str, Any]) -> Mapping[str, Any]:
    frozen: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or key.startswith("_"):
            raise DualLiveEvaluationError("dual_live_check_evidence_invalid")
        frozen[key] = _freeze_evidence_value(item)
    return MappingProxyType(frozen)


@dataclass(frozen=True, slots=True)
class CheckResult:
    check_id: str
    status: EvaluationStatus
    code: str
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.check_id not in EVALUATOR_CHECK_ORDER:
            raise DualLiveEvaluationError("dual_live_check_id_invalid")
        if self.status not in {"PASS", "FAIL", "INDETERMINATE"}:
            raise DualLiveEvaluationError("dual_live_check_status_invalid")
        if not isinstance(self.code, str) or not re.fullmatch(r"[a-z0-9_]+", self.code):
            raise DualLiveEvaluationError("dual_live_check_code_invalid")
        object.__setattr__(self, "evidence", _freeze_evidence(self.evidence))

    def as_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "status": self.status,
            "code": self.code,
            "evidence": _thaw(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class _CaptureRunProjection:
    connector_run_id: str
    status: str


@dataclass(frozen=True, slots=True)
class _CaptureSealEventProjection:
    connector_run_event_id: str
    connector_run_id: str
    connector_run_target_id: str | None
    phase: str
    stage: str
    event_type: str
    status_before: str | None
    status_after: str | None
    reason_code: str | None
    error_class: str | None
    message: str | None
    metrics_bytes: bytes
    created_at: Any


@dataclass(frozen=True, slots=True)
class _IndependentCaptureEvidence:
    manifest: Any = None
    manifest_bytes: bytes = b""
    manifest_sha256: str = ""
    file_set_hash: str = ""
    seal: Any = None
    seal_bytes: bytes = b""
    seal_sha256: str = ""
    stream_bytes: Mapping[str, bytes] = field(default_factory=dict)
    runs: tuple[_CaptureRunProjection, ...] = ()
    seal_events: tuple[_CaptureSealEventProjection, ...] = ()
    errors: Mapping[str, str] = field(default_factory=dict)


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class _EvidenceContext:
    campaign_id: str
    campaign_fingerprint: str
    settings: Any
    db: Any
    chain: Any = None
    campaign_ref: Any = None
    entry_refs: tuple[Any, ...] = ()
    capture_ref: Any = None
    historical: Mapping[str, Any] = field(default_factory=dict)
    capture: Any = None
    independent_capture: _IndependentCaptureEvidence | None = None
    manifest: Any = None
    seal: Any = None
    runtime_records: tuple[Mapping[str, Any], ...] = ()
    child_proofs: tuple[Mapping[str, Any], ...] = ()
    counter_records: tuple[Mapping[str, Any], ...] = ()
    runs: tuple[Any, ...] = ()
    run_by_connector: Mapping[str, Any] = field(default_factory=dict)
    envelopes: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    targets: Mapping[str, Any] = field(default_factory=dict)
    ledgers: Mapping[str, Any] = field(default_factory=dict)
    origins: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    downstream: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    source_record_ids: Mapping[str, str] = field(default_factory=dict)
    downstream_sessions: Mapping[str, Any] = field(default_factory=dict)
    pass_runs: Mapping[str, Any] = field(default_factory=dict)
    output_integrity: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict
    )
    review_states: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    reconciliations: Mapping[str, Any] = field(default_factory=dict)
    package_commits: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    submit_states: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    handoff_states: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    packages: Mapping[str, tuple[Any, ...]] = field(default_factory=dict)
    package_payloads: Mapping[str, tuple[Mapping[str, Any], ...]] = field(
        default_factory=dict
    )
    db_values: tuple[tuple[str, Any], ...] = ()
    non_source_files: tuple[tuple[str, bytes], ...] = ()
    source_exemptions: tuple[tuple[str, str], ...] = ()
    initial_snapshot_sha256: str = ""
    final_snapshot_sha256: str = ""
    initial_database_snapshot_sha256: str = ""
    final_database_snapshot_sha256: str = ""
    domain_errors: Mapping[str, str] = field(default_factory=dict)


def _require_campaign_id(campaign_id: str) -> None:
    if not isinstance(campaign_id, str):
        raise DualLiveEvaluationError("dual_live_campaign_id_invalid")
    try:
        parsed = UUID(campaign_id)
    except (ValueError, AttributeError):
        raise DualLiveEvaluationError("dual_live_campaign_id_invalid") from None
    if parsed.version != 4 or str(parsed) != campaign_id:
        raise DualLiveEvaluationError("dual_live_campaign_id_invalid")


def _require_campaign_fingerprint(expected_campaign_fingerprint: str) -> None:
    if (
        not isinstance(expected_campaign_fingerprint, str)
        or not _LOWERCASE_SHA256.fullmatch(expected_campaign_fingerprint)
    ):
        raise DualLiveEvaluationError("dual_live_campaign_fingerprint_invalid")


def _pass(check_id: str, **evidence: Any) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        status="PASS",
        code=f"{check_id.lower()}_pass",
        evidence=evidence,
    )


def _fail_result(check_id: str, code: str, **evidence: Any) -> CheckResult:
    return CheckResult(check_id=check_id, status="FAIL", code=code, evidence=evidence)


def _indeterminate(check_id: str, code: str, **evidence: Any) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        status="INDETERMINATE",
        code=code,
        evidence=evidence,
    )


def _domain_error(context: _EvidenceContext, check_id: str, domain: str) -> CheckResult | None:
    code = context.domain_errors.get(domain)
    if code is None:
        return None
    return _indeterminate(
        check_id,
        f"{check_id.lower()}_evidence_unavailable",
        domain=domain,
        reason_code=code,
    )


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _thaw(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def _child_proof_invalid() -> None:
    raise DualLiveEvaluationError("dual_live_child_proof_invalid")


def _require_child_proof_sha256(value: Any) -> str:
    if type(value) is not str or _LOWERCASE_SHA256.fullmatch(value) is None:
        _child_proof_invalid()
    return value


def _require_child_proof_identifier(value: Any) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > 255
        or any(character.isspace() for character in value)
    ):
        _child_proof_invalid()
    return value


def _validate_child_proof_hashes(
    payload: Mapping[str, Any],
    names: Sequence[str],
) -> None:
    for name in names:
        _require_child_proof_sha256(payload.get(name))


def _validate_child_guard_payload(
    payload: Any,
    *,
    ordinal: int,
) -> None:
    point = "pre_go" if ordinal == 1 else "exit" if ordinal == 3 else None
    keys = {
        "boot_frame_sha256",
        "control_nonce_sha256",
        "denied_routes",
        "network_enable_attempt_count",
        "original_implementation_call_count",
        "pre_activity_status_frame_sha256",
        "proof_point",
        "proof_scope",
    }
    hashes = [
        "boot_frame_sha256",
        "control_nonce_sha256",
        "pre_activity_status_frame_sha256",
    ]
    if point == "exit":
        keys.update(("control_frame_sha256", "exit_status_frame_sha256"))
        hashes.extend(("control_frame_sha256", "exit_status_frame_sha256"))
    if (
        type(payload) is not dict
        or set(payload) != keys
        or payload.get("proof_scope") != "production"
        or payload.get("proof_point") != point
        or type(payload.get("denied_routes")) is not list
        or tuple(payload["denied_routes"]) != _CHILD_PROOF_DENIED_ROUTES
        or type(payload.get("network_enable_attempt_count")) is not int
        or payload["network_enable_attempt_count"] != 0
        or type(payload.get("original_implementation_call_count")) is not int
        or payload["original_implementation_call_count"] != 0
    ):
        _child_proof_invalid()
    _validate_child_proof_hashes(payload, hashes)


def _validate_child_acquisition_payload(payload: Any) -> None:
    if (
        type(payload) is not dict
        or set(payload)
        != {
            "boot_frame_sha256",
            "connector_acquisitions",
            "control_frame_sha256",
            "control_nonce_sha256",
            "downstream_action_count",
            "exit_status_frame_sha256",
            "pre_activity_status_frame_sha256",
            "proof_scope",
        }
        or payload.get("proof_scope") != "production"
        or type(payload.get("downstream_action_count")) is not int
        or payload["downstream_action_count"] != 0
        or type(payload.get("connector_acquisitions")) is not list
        or len(payload["connector_acquisitions"]) != 2
    ):
        _child_proof_invalid()
    _validate_child_proof_hashes(
        payload,
        (
            "boot_frame_sha256",
            "control_frame_sha256",
            "control_nonce_sha256",
            "exit_status_frame_sha256",
            "pre_activity_status_frame_sha256",
        ),
    )
    for item, connector_key in zip(
        payload["connector_acquisitions"],
        _EXPECTED_CONNECTORS,
        strict=True,
    ):
        if (
            type(item) is not dict
            or set(item)
            != {
                "action_codes",
                "connector_key",
                "connector_run_id",
                "connector_run_target_id",
                "ledger_terminal_hash",
                "raw_content_sha256",
                "terminal_transition_count",
            }
            or item.get("connector_key") != connector_key
            or type(item.get("action_codes")) is not list
            or tuple(item["action_codes"])
            != (
                "derived_arming",
                "raw_acquisition",
                "terminal_transition",
            )
            or type(item.get("terminal_transition_count")) is not int
            or item["terminal_transition_count"] != 1
        ):
            _child_proof_invalid()
        _require_child_proof_identifier(item.get("connector_run_id"))
        _require_child_proof_identifier(item.get("connector_run_target_id"))
        _validate_child_proof_hashes(
            item,
            ("ledger_terminal_hash", "raw_content_sha256"),
        )


def _validate_child_downstream_payload(payload: Any) -> None:
    if (
        type(payload) is not dict
        or set(payload)
        != {
            "action_receipts",
            "boot_frame_sha256",
            "control_frame_sha256",
            "control_nonce_sha256",
            "downstream_actions",
            "exit_status_frame_sha256",
            "pre_activity_status_frame_sha256",
            "proof_scope",
            "source_bindings",
            "terminal_boundary",
        }
        or payload.get("proof_scope") != "production"
        or type(payload.get("downstream_actions")) is not list
        or tuple(payload["downstream_actions"]) != _PHASE_B_DOWNSTREAM_ACTIONS
        or payload.get("terminal_boundary") != "handoff_prepared"
        or type(payload.get("action_receipts")) is not list
        or len(payload["action_receipts"]) != len(_PHASE_B_DOWNSTREAM_ACTIONS)
        or type(payload.get("source_bindings")) is not list
        or len(payload["source_bindings"]) != 2
    ):
        _child_proof_invalid()
    _validate_child_proof_hashes(
        payload,
        (
            "boot_frame_sha256",
            "control_frame_sha256",
            "control_nonce_sha256",
            "exit_status_frame_sha256",
            "pre_activity_status_frame_sha256",
        ),
    )
    for action, receipt in zip(
        _PHASE_B_DOWNSTREAM_ACTIONS,
        payload["action_receipts"],
        strict=True,
    ):
        if (
            type(receipt) is not dict
            or set(receipt) != {"action", "result_sha256"}
            or receipt.get("action") != action
        ):
            _child_proof_invalid()
        _require_child_proof_sha256(receipt.get("result_sha256"))
    candidate_ids: set[str] = set()
    for item, connector_key in zip(
        payload["source_bindings"],
        _EXPECTED_CONNECTORS,
        strict=True,
    ):
        if (
            type(item) is not dict
            or set(item) != _PHASE_B_SOURCE_BINDING_KEYS
            or item.get("connector_key") != connector_key
            or item.get("source_shape") != _PHASE_B_SOURCE_SHAPES[connector_key]
            or type(item.get("output_package_ids")) is not list
            or len(item["output_package_ids"]) != 3
            or not all(
                type(package_id) is str
                for package_id in item["output_package_ids"]
            )
            or len(set(item["output_package_ids"])) != 3
            or type(item.get("package_kinds")) is not list
            or tuple(item["package_kinds"]) != _PACKAGE_KINDS
            or type(item.get("payload_hashes")) is not list
            or len(item["payload_hashes"]) != 3
            or not all(
                type(payload_hash) is str
                for payload_hash in item["payload_hashes"]
            )
        ):
            _child_proof_invalid()
        candidate_ids.add(_require_child_proof_identifier(item.get("candidate_id")))
        for name in (
            "analysis_plan_id",
            "connector_run_id",
            "connector_run_target_id",
            "handoff_export_envelope_ref",
            "package_review_submit_record_ref",
            "pass_run_id",
            "prepare_record_ref",
            "reconciliation_record_id",
            "result_review_record_ref",
            "session_id",
            "source_record_id",
        ):
            _require_child_proof_identifier(item.get(name))
        preview_id = _require_child_proof_identifier(
            item.get("package_review_preview_hash")
        )
        preview_prefix = _PHASE_B_PACKAGE_PREVIEW_PREFIXES[item["connector_key"]]
        if (
            re.fullmatch(
                f"{re.escape(preview_prefix)}[0-9a-f]{{16}}",
                preview_id,
            )
            is None
        ):
            _child_proof_invalid()
        analysis_run_id = item.get("analysis_run_id")
        if analysis_run_id is not None:
            _require_child_proof_identifier(analysis_run_id)
        for package_id in item["output_package_ids"]:
            _require_child_proof_identifier(package_id)
        for name in (
            "connector_origin_receipt_hash",
            "construction_basis_hash",
        ):
            _require_child_proof_sha256(item.get(name))
        for payload_hash in item["payload_hashes"]:
            _require_child_proof_sha256(payload_hash)
    if len(candidate_ids) != 2:
        _child_proof_invalid()


def _validate_child_proof_payload(
    *,
    phase: str,
    event: str,
    ordinal: int,
    payload: Any,
) -> None:
    if phase == "A" and event == "acquisition_boundary" and ordinal == 1:
        _validate_child_acquisition_payload(payload)
        return
    if phase == "B" and event == "guard" and ordinal in {1, 3}:
        _validate_child_guard_payload(payload, ordinal=ordinal)
        return
    if phase == "B" and event == "downstream_chain" and ordinal == 2:
        _validate_child_downstream_payload(payload)
        return
    _child_proof_invalid()


def _parse_child_proof_records(
    stdout_log: bytes,
) -> tuple[Mapping[str, Any], ...]:
    from app.services.connector_egress_evidence import (
        canonical_json_bytes,
        strict_json_loads,
    )

    if (
        not isinstance(stdout_log, bytes)
        or not stdout_log
        or not stdout_log.endswith(b"\n")
        or b"\r" in stdout_log
    ):
        _child_proof_invalid()
    lines = stdout_log[:-1].split(b"\n")
    if len(lines) != len(_CHILD_PROOF_SEQUENCE) or any(not line for line in lines):
        _child_proof_invalid()
    records: list[dict[str, Any]] = []
    phase_predecessors: dict[str, str | None] = {"A": None, "B": None}
    phase_identities: dict[str, tuple[str, str]] = {}
    for line, (phase, ordinal, event) in zip(
        lines,
        _CHILD_PROOF_SEQUENCE,
        strict=True,
    ):
        try:
            value = strict_json_loads(line)
        except (TypeError, ValueError) as exc:
            raise DualLiveEvaluationError("dual_live_child_proof_invalid") from exc
        if (
            type(value) is not dict
            or canonical_json_bytes(value) != line
            or tuple(value) != _CHILD_PROOF_TOP_KEYS
            or value.get("schema_id") != _CHILD_PROOF_SCHEMA_ID
            or value.get("phase") != phase
            or value.get("event") != event
            or type(value.get("ordinal")) is not int
            or value["ordinal"] != ordinal
            or value.get("previous_record_sha256")
            != phase_predecessors[phase]
        ):
            _child_proof_invalid()
        process_boot_id = _require_child_proof_sha256(
            value.get("process_boot_id")
        )
        status_nonce_sha256 = _require_child_proof_sha256(
            value.get("status_nonce_sha256")
        )
        identity = (process_boot_id, status_nonce_sha256)
        if phase in phase_identities and phase_identities[phase] != identity:
            _child_proof_invalid()
        phase_identities[phase] = identity
        record_sha256 = _require_child_proof_sha256(
            value.get("record_sha256")
        )
        preimage = {
            key: value[key]
            for key in _CHILD_PROOF_TOP_KEYS
            if key != "record_sha256"
        }
        if hashlib.sha256(canonical_json_bytes(preimage)).hexdigest() != record_sha256:
            _child_proof_invalid()
        _validate_child_proof_payload(
            phase=phase,
            event=event,
            ordinal=ordinal,
            payload=value.get("payload"),
        )
        phase_predecessors[phase] = record_sha256
        records.append(value)
    if (
        set(phase_identities) != {"A", "B"}
        or phase_identities["A"] == phase_identities["B"]
    ):
        _child_proof_invalid()
    b_common = (
        "boot_frame_sha256",
        "control_nonce_sha256",
        "pre_activity_status_frame_sha256",
    )
    if any(
        records[index]["payload"][name] != records[1]["payload"][name]
        for index in (2, 3)
        for name in b_common
    ) or any(
        records[index]["payload"][name] != records[2]["payload"][name]
        for index in (3,)
        for name in ("control_frame_sha256", "exit_status_frame_sha256")
    ):
        _child_proof_invalid()
    return tuple(_freeze_evidence(record) for record in records)


def _framed_payload_sha256(payload: bytes) -> str:
    if not isinstance(payload, bytes) or not payload:
        _child_proof_invalid()
    return hashlib.sha256(
        len(payload).to_bytes(4, "big", signed=False) + payload
    ).hexdigest()


def _parse_child_boot_records(
    app_log: bytes,
) -> Mapping[str, tuple[Mapping[str, Any], bytes]]:
    from app.services.connector_egress_evidence import (
        canonical_json_bytes,
        strict_json_loads,
    )

    if (
        not isinstance(app_log, bytes)
        or not app_log
        or not app_log.endswith(b"\n")
        or b"\r" in app_log
    ):
        _child_proof_invalid()
    by_phase: dict[str, tuple[Mapping[str, Any], bytes]] = {}
    reserved_markers = tuple(
        schema_id.encode("ascii")
        for schema_id in (
            _CHILD_BOOT_SCHEMA_ID,
            _CHILD_CONTROL_SCHEMA_ID,
            _CHILD_STATUS_SCHEMA_ID,
            _CHILD_PROOF_SCHEMA_ID,
        )
    )
    for line in app_log[:-1].split(b"\n"):
        if not line:
            _child_proof_invalid()
        try:
            value = strict_json_loads(line)
        except (TypeError, ValueError):
            if any(marker in line for marker in reserved_markers):
                _child_proof_invalid()
            continue
        if not isinstance(value, dict):
            continue
        schema_id = value.get("schema_id")
        if schema_id in {
            _CHILD_CONTROL_SCHEMA_ID,
            _CHILD_STATUS_SCHEMA_ID,
            _CHILD_PROOF_SCHEMA_ID,
        }:
            _child_proof_invalid()
        if schema_id != _CHILD_BOOT_SCHEMA_ID:
            continue
        if (
            canonical_json_bytes(value) != line
            or tuple(value)
            != (
                "control_nonce",
                "phase",
                "process_boot_id",
                "schema_id",
                "status_nonce_sha256",
            )
            or value.get("phase") not in {"A", "B"}
        ):
            _child_proof_invalid()
        phase = str(value["phase"])
        if phase in by_phase:
            _child_proof_invalid()
        _require_child_proof_sha256(value.get("control_nonce"))
        _require_child_proof_sha256(value.get("process_boot_id"))
        _require_child_proof_sha256(value.get("status_nonce_sha256"))
        by_phase[phase] = (_freeze_evidence(value), line)
    if set(by_phase) != {"A", "B"}:
        _child_proof_invalid()
    return MappingProxyType(by_phase)


def _phase_runtime_record(
    runtime_records: Sequence[Mapping[str, Any]],
    *,
    phase: str,
    event: str,
) -> Mapping[str, Any]:
    matches = tuple(
        record
        for record in runtime_records
        if record.get("phase") == phase and record.get("event") == event
    )
    if len(matches) != 1:
        _child_proof_invalid()
    return matches[0]


def _status_frame_sha256_from_runtime(
    *,
    phase: str,
    process_boot_id: str,
    status_nonce_sha256: str,
    ordinal: int,
    runtime_record: Mapping[str, Any],
) -> str:
    from app.services.connector_egress_evidence import canonical_json_bytes

    payload = _record_payload(runtime_record)
    point = "pre_activity" if ordinal == 1 else "exit" if ordinal == 2 else None
    if (
        point is None
        or payload.get("census_point") != point
        or type(payload.get("handler_count")) is not int
        or payload["handler_count"] < 0
        or type(payload.get("topology_sha256")) is not str
        or _LOWERCASE_SHA256.fullmatch(payload["topology_sha256"]) is None
    ):
        _child_proof_invalid()
    encoded = canonical_json_bytes(
        {
            "schema_id": _CHILD_STATUS_SCHEMA_ID,
            "phase": phase,
            "event": "logger_census",
            "process_boot_id": process_boot_id,
            "status_nonce_sha256": status_nonce_sha256,
            "ordinal": ordinal,
            "payload": {
                "census_point": point,
                "handler_count": payload["handler_count"],
                "topology_sha256": payload["topology_sha256"],
            },
        }
    )
    return _framed_payload_sha256(encoded)


def _validate_child_proof_runtime_bindings(
    *,
    child_proofs: Sequence[Mapping[str, Any]],
    runtime_records: Sequence[Mapping[str, Any]],
    app_log: bytes,
) -> None:
    from app.services.connector_egress_evidence import canonical_json_bytes

    if len(child_proofs) != len(_CHILD_PROOF_SEQUENCE):
        _child_proof_invalid()
    boot_records = _parse_child_boot_records(app_log)
    for phase, proof_indexes in (("A", (0,)), ("B", (1, 2, 3))):
        boot_record, boot_line = boot_records[phase]
        process_boot_id = str(boot_record["process_boot_id"])
        status_nonce_sha256 = str(boot_record["status_nonce_sha256"])
        control_nonce = str(boot_record["control_nonce"])
        start = _phase_runtime_record(
            runtime_records,
            phase=phase,
            event="phase_child_start",
        )
        go = _phase_runtime_record(
            runtime_records,
            phase=phase,
            event="phase_go",
        )
        censuses = tuple(
            record
            for record in runtime_records
            if record.get("phase") == phase
            and record.get("event") == "logger_census"
        )
        if (
            start.get("process_boot_id") != process_boot_id
            or go.get("process_boot_id") != process_boot_id
            or len(censuses) != 2
            or any(
                record.get("process_boot_id") != process_boot_id
                for record in censuses
            )
        ):
            _child_proof_invalid()
        control_nonce_sha256 = hashlib.sha256(
            control_nonce.encode("ascii")
        ).hexdigest()
        if _record_payload(go).get("control_nonce_sha256") != control_nonce_sha256:
            _child_proof_invalid()
        control_payload = canonical_json_bytes(
            {
                "schema_id": _CHILD_CONTROL_SCHEMA_ID,
                "phase": phase,
                "command": "GO",
                "control_nonce": control_nonce,
            }
        )
        expected_hashes = {
            "boot_frame_sha256": _framed_payload_sha256(boot_line),
            "control_frame_sha256": _framed_payload_sha256(control_payload),
            "control_nonce_sha256": control_nonce_sha256,
            "pre_activity_status_frame_sha256": (
                _status_frame_sha256_from_runtime(
                    phase=phase,
                    process_boot_id=process_boot_id,
                    status_nonce_sha256=status_nonce_sha256,
                    ordinal=1,
                    runtime_record=censuses[0],
                )
            ),
            "exit_status_frame_sha256": _status_frame_sha256_from_runtime(
                phase=phase,
                process_boot_id=process_boot_id,
                status_nonce_sha256=status_nonce_sha256,
                ordinal=2,
                runtime_record=censuses[1],
            ),
        }
        for index in proof_indexes:
            proof = child_proofs[index]
            proof_payload = _record_payload(proof)
            if (
                proof.get("process_boot_id") != process_boot_id
                or proof.get("status_nonce_sha256") != status_nonce_sha256
            ):
                _child_proof_invalid()
            required_hashes = (
                (
                    "boot_frame_sha256",
                    "control_nonce_sha256",
                    "pre_activity_status_frame_sha256",
                )
                if phase == "B" and proof.get("ordinal") == 1
                else tuple(expected_hashes)
            )
            if any(
                proof_payload.get(name) != expected_hashes[name]
                for name in required_hashes
            ):
                _child_proof_invalid()


def _json_observation_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=True,
        ).encode("utf-8")
    except (OverflowError, TypeError, ValueError):
        return b"\x00invalid-json-observation"


def _snapshot_hash(parts: Sequence[tuple[str, Any]]) -> str:
    return hashlib.sha256(_canonical_bytes(tuple(parts))).hexdigest()


def _domain_code(exc: BaseException) -> str:
    code = getattr(exc, "code", None)
    if isinstance(code, str) and re.fullmatch(r"[a-z0-9_]+", code):
        return code
    return "dual_live_evidence_internal_error"


def _materialize_dependency_errors(errors: dict[str, str]) -> None:
    dependencies: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("archive", ("authority",)),
        ("capture", ("authority",)),
        ("runtime", ("capture",)),
        ("counter", ("capture",)),
        ("ledger", ("authority", "capture", "counter")),
        ("origin", ("ledger",)),
        ("phase_b_sources", ("origin",)),
        ("downstream", ("origin", "phase_b_sources")),
        ("execution", ("downstream",)),
        ("review", ("execution",)),
        ("package_set", ("downstream",)),
        ("submit", ("package_set", "review", "execution")),
        ("handoff", ("submit",)),
        (
            "custody",
            ("authority", "capture", "ledger", "origin", "downstream"),
        ),
    )
    changed = True
    while changed:
        changed = False
        for domain, parents in dependencies:
            if domain in errors:
                continue
            inherited = next(
                (errors[parent] for parent in parents if parent in errors),
                None,
            )
            if inherited is not None:
                errors[domain] = inherited
                changed = True
    if errors and "stability" not in errors:
        errors["stability"] = next(iter(errors.values()))


def _select_campaign_slice(
    chain: Any,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
) -> tuple[Any, tuple[Any, ...], Any]:
    campaigns = tuple(
        item
        for item in chain.head.campaigns
        if item.campaign_id == campaign_id
        and item.campaign_fingerprint == campaign_fingerprint
    )
    entries = tuple(
        item
        for item in chain.head.entries
        if item.campaign_id == campaign_id
        and item.campaign_fingerprint == campaign_fingerprint
    )
    captures = tuple(
        item
        for item in chain.head.log_captures
        if item.campaign_id == campaign_id
        and item.campaign_fingerprint == campaign_fingerprint
    )
    if len(campaigns) != 1 or len(entries) != 2 or len(captures) != 1:
        raise DualLiveEvaluationError("dual_live_campaign_slice_cardinality_invalid")
    if tuple(sorted(item.connector_key for item in entries)) != _EXPECTED_CONNECTORS:
        raise DualLiveEvaluationError("dual_live_campaign_slice_connectors_invalid")
    return campaigns[0], entries, captures[0]


def _parse_capture_models(capture: Any) -> tuple[Any, Any]:
    from app.schemas.api import (
        ConnectorCampaignLogManifestV1,
        ConnectorCampaignLogSealV1,
    )

    try:
        manifest = ConnectorCampaignLogManifestV1.model_validate_json(
            capture.manifest_bytes
        )
        seal = ConnectorCampaignLogSealV1.model_validate_json(capture.seal_bytes)
    except (TypeError, ValueError) as exc:
        raise DualLiveEvaluationError("dual_live_capture_object_invalid") from exc
    return manifest, seal


def _stream_bytes(capture: Any, suffix: str) -> bytes:
    matches = tuple(
        payload
        for path, payload in capture.stream_bytes.items()
        if str(path).replace("\\", "/").endswith(f"/{suffix}")
    )
    if len(matches) != 1:
        raise DualLiveEvaluationError("dual_live_capture_stream_membership_invalid")
    return bytes(matches[0])


def _run_envelope(run: Any) -> dict[str, Any]:
    config = run.request_config_json
    envelope = config.get("connector_egress_arming") if isinstance(config, dict) else None
    if not isinstance(envelope, dict):
        raise DualLiveEvaluationError("dual_live_run_arming_missing")
    return dict(envelope)


def _model_field(value: Any, field_name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(field_name)
    return getattr(value, field_name, None)


def _model_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        result = dump(mode="json")
        if isinstance(result, Mapping):
            return result
    raise DualLiveEvaluationError("dual_live_origin_authority_invalid")


def _derive_origin_receipt_read_only(
    *,
    settings: Any,
    run: Any,
    target: Any,
    ledger: Any,
    historical: Any,
    envelope: Mapping[str, Any],
) -> Mapping[str, Any]:
    stored = _stored_origin_receipt(target)
    if stored is None or not _receipt_hash_is_valid(stored):
        raise DualLiveEvaluationError("dual_live_origin_receipt_invalid")
    receipt = dict(stored)
    raw_bytes = _source_blob_from_settings(settings, str(target.raw_storage_ref))
    raw_hash = hashlib.sha256(raw_bytes).hexdigest()
    connector_key = str(run.connector_key)
    if connector_key == "sciencebase_mcs":
        target_identity = {
            "item_id": str(target.sciencebase_item_id or ""),
            "exact_file_name": str(target.sciencebase_file_name or ""),
        }
    elif connector_key == "nrc_adams_aps":
        target_identity = {
            "accession_number": str(target.stable_release_key or "")
        }
    else:
        raise DualLiveEvaluationError("dual_live_origin_connector_invalid")
    if any(not value or value != value.strip() for value in target_identity.values()):
        raise DualLiveEvaluationError("dual_live_origin_target_invalid")

    definition = historical.definition_model
    grant = historical.model
    marker = historical.marker_model
    grant_target = _model_mapping(_model_field(grant, "target"))
    expected_grant_target = {
        "connector_key": connector_key,
        **target_identity,
    }
    if connector_key == "sciencebase_mcs":
        expected_grant_target["locator_key"] = "downloadUri"
    if dict(grant_target) != expected_grant_target:
        raise DualLiveEvaluationError("dual_live_origin_target_invalid")

    arming_hash = envelope.get("arming_fingerprint")
    arming_preimage = {
        key: value for key, value in envelope.items() if key != "arming_fingerprint"
    }
    if (
        not isinstance(arming_hash, str)
        or not _LOWERCASE_SHA256.fullmatch(arming_hash)
        or hashlib.sha256(_canonical_bytes(arming_preimage)).hexdigest()
        != arming_hash
        or run.request_fingerprint != arming_hash
    ):
        raise DualLiveEvaluationError("dual_live_origin_arming_invalid")

    marker_pairs = {
        "connector_key": connector_key,
        "campaign_id": str(envelope.get("campaign_id") or ""),
        "raw_grant_sha256": str(envelope.get("grant_sha256") or ""),
        "connector_run_id": str(run.connector_run_id),
    }
    if any(str(_model_field(marker, key)) != expected for key, expected in marker_pairs.items()):
        raise DualLiveEvaluationError("dual_live_origin_marker_invalid")

    projection = getattr(ledger, "canonical_projection", None)
    ledger_hash = getattr(ledger, "ledger_terminal_hash", None)
    if (
        getattr(ledger, "eligible", None) is not True
        or not isinstance(projection, Mapping)
        or not isinstance(ledger_hash, str)
        or not _LOWERCASE_SHA256.fullmatch(ledger_hash)
        or hashlib.sha256(_canonical_bytes(projection)).hexdigest() != ledger_hash
    ):
        raise DualLiveEvaluationError("dual_live_origin_ledger_invalid")

    expected = {
        "schema_id": "layer3.connector_origin_continuity.v1",
        "proof_class": "fresh_live",
        "connector_key": connector_key,
        "connector_run_id": str(run.connector_run_id),
        "connector_run_target_id": str(target.connector_run_target_id),
        "target_identity": target_identity,
        "source_artifact_key": str(target.source_artifact_key or ""),
        "raw_storage_ref": str(target.raw_storage_ref),
        "raw_content_sha256": raw_hash,
        "raw_content_size_bytes": len(raw_bytes),
        "campaign_id": str(envelope.get("campaign_id") or ""),
        "campaign_fingerprint": historical.canonical_campaign_fingerprint,
        "campaign_definition_sha256": historical.raw_definition_sha256,
        "campaign_introduction_index_revision": (
            historical.introduction_index_revision
        ),
        "campaign_introduction_index_sha256": (
            historical.introduction_index_sha256
        ),
        "arming_fingerprint": arming_hash,
        "grant_sha256": historical.raw_sha256,
        "canonical_grant_fingerprint": historical.canonical_fingerprint,
        "grant_consumption_marker_sha256": (
            historical.consumption_marker_sha256
        ),
        "ledger_terminal_hash": ledger_hash,
    }
    if connector_key == "sciencebase_mcs":
        expected.update(
            {
                "predecessor_nrc_connector_run_id": envelope.get(
                    "predecessor_nrc_connector_run_id"
                ),
                "predecessor_nrc_ledger_terminal_hash": envelope.get(
                    "predecessor_nrc_ledger_terminal_hash"
                ),
            }
        )
    elif {
        "predecessor_nrc_connector_run_id",
        "predecessor_nrc_ledger_terminal_hash",
    } & set(receipt):
        raise DualLiveEvaluationError("dual_live_origin_predecessor_invalid")
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise DualLiveEvaluationError("dual_live_origin_receipt_mismatch")
    if (
        str(_model_field(definition, "campaign_id")) != expected["campaign_id"]
        or str(_model_field(grant, "campaign_id")) != expected["campaign_id"]
        or _model_field(grant, "connector_key") != connector_key
        or str(_model_field(definition, "code_revision"))
        != str(envelope.get("code_revision"))
        or str(_model_field(grant, "code_revision"))
        != str(envelope.get("code_revision"))
        or target.downloaded_sha256 != raw_hash
    ):
        raise DualLiveEvaluationError("dual_live_origin_authority_invalid")
    return MappingProxyType(receipt)


def _rows_for_selected_authority(
    db: Any,
    *,
    runs: Sequence[Any],
    targets: Sequence[Any],
    sessions: Sequence[Any],
) -> tuple[tuple[str, Any], ...]:
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy import select

    from app.models.models import Base

    run_ids = {str(row.connector_run_id) for row in runs}
    target_ids = {str(row.connector_run_target_id) for row in targets}
    session_ids = {str(row.session_id) for row in sessions}
    collected: list[tuple[str, Any]] = []
    total = 0
    for mapper in sorted(Base.registry.mappers, key=lambda item: item.class_.__name__):
        model = mapper.class_
        table = mapper.local_table
        criteria = None
        if "connector_run_id" in table.c and run_ids:
            criteria = table.c.connector_run_id.in_(sorted(run_ids))
        elif "connector_run_target_id" in table.c and target_ids:
            criteria = table.c.connector_run_target_id.in_(sorted(target_ids))
        elif "target_id" in table.c and target_ids:
            criteria = table.c.target_id.in_(sorted(target_ids))
        elif "session_id" in table.c and session_ids:
            criteria = table.c.session_id.in_(sorted(session_ids))
        if criteria is None:
            continue
        rows = tuple(db.scalars(select(model).where(criteria).limit(MAX_DB_ROWS + 1)))
        total += len(rows)
        if total > MAX_DB_ROWS:
            raise DualLiveEvaluationError("dual_live_db_row_cap_exceeded")
        for row in rows:
            state = sa_inspect(row)
            identity = state.identity
            row_key = f"{model.__name__}:{_snapshot_hash((('id', identity),))}"
            for attribute in mapper.column_attrs:
                value = getattr(row, attribute.key)
                encoded = _canonical_bytes(value)
                if len(encoded) > MAX_DB_VALUE_BYTES:
                    raise DualLiveEvaluationError("dual_live_db_value_cap_exceeded")
                collected.append((f"{row_key}:{attribute.key}", value))
    return tuple(collected)


def _find_sessions_and_downstream(
    db: Any,
    *,
    origins: Mapping[str, Mapping[str, Any]],
) -> tuple[tuple[Any, ...], dict[str, Mapping[str, Any]]]:
    from sqlalchemy import select

    from app.models.models import L3PassRun, L3Session

    sessions = tuple(db.scalars(select(L3Session).limit(MAX_DB_ROWS + 1)))
    if len(sessions) > MAX_DB_ROWS:
        raise DualLiveEvaluationError("dual_live_db_row_cap_exceeded")
    pass_runs = tuple(db.scalars(select(L3PassRun).limit(MAX_DB_ROWS + 1)))
    if len(pass_runs) > MAX_DB_ROWS:
        raise DualLiveEvaluationError("dual_live_db_row_cap_exceeded")
    sessions_by_id = {str(session.session_id): session for session in sessions}
    if len(sessions_by_id) != len(sessions):
        raise DualLiveEvaluationError("dual_live_downstream_session_ambiguous")
    matched: dict[str, Any] = {}
    verified: dict[str, Mapping[str, Any]] = {}
    for connector_key in _EXPECTED_CONNECTORS:
        receipt = origins.get(connector_key)
        if receipt is None:
            raise DualLiveEvaluationError("dual_live_origin_receipt_missing")
        expected = _origin_integrity(receipt)
        candidates = tuple(
            pass_run
            for pass_run in pass_runs
            if isinstance(pass_run.summary_json, Mapping)
            and pass_run.summary_json.get("connector_origin_integrity_v1")
            == expected
        )
        session_ids = {str(pass_run.session_id) for pass_run in candidates}
        if len(session_ids) != 1:
            raise DualLiveEvaluationError("dual_live_downstream_session_ambiguous")
        session = sessions_by_id.get(next(iter(session_ids)))
        if session is None:
            raise DualLiveEvaluationError("dual_live_downstream_session_missing")
        matched[connector_key] = session
        verified[connector_key] = MappingProxyType(
            {
                "execution_output": MappingProxyType(
                    {
                        "connector_key": connector_key,
                        "connector_run_target_id": expected[
                            "connector_run_target_id"
                        ],
                        "connector_origin_receipt_hash": expected[
                            "connector_origin_receipt_hash"
                        ],
                        "proof_class": expected["proof_class"],
                        "boundary": "execution_output",
                    }
                )
            }
        )
    if set(matched) != set(_EXPECTED_CONNECTORS):
        raise DualLiveEvaluationError("dual_live_downstream_session_missing")
    return tuple(matched[key] for key in _EXPECTED_CONNECTORS), verified


def _load_phase_b_source_record_ids(
    db: Any,
    *,
    targets: Mapping[str, Any],
) -> dict[str, str]:
    from sqlalchemy import select

    from app.models.models import ApsContentLinkage, L3ConnectorSourceIntakeRecord

    if set(targets) != set(_EXPECTED_CONNECTORS):
        raise DualLiveEvaluationError("dual_live_phase_b_source_missing")
    nrc_target = targets["nrc_adams_aps"]
    sciencebase_target = targets["sciencebase_mcs"]
    nrc_rows = tuple(
        db.scalars(
            select(ApsContentLinkage)
            .where(ApsContentLinkage.target_id == nrc_target.connector_run_target_id)
            .order_by(ApsContentLinkage.aps_content_linkage_id.asc())
            .limit(2)
        )
    )
    sciencebase_rows = tuple(
        db.scalars(
            select(L3ConnectorSourceIntakeRecord)
            .where(
                L3ConnectorSourceIntakeRecord.connector_run_target_id
                == sciencebase_target.connector_run_target_id
            )
            .order_by(
                L3ConnectorSourceIntakeRecord.connector_source_intake_record_id.asc()
            )
            .limit(2)
        )
    )
    if len(nrc_rows) != 1 or len(sciencebase_rows) != 1:
        raise DualLiveEvaluationError("dual_live_phase_b_source_missing")
    nrc = nrc_rows[0]
    sciencebase = sciencebase_rows[0]
    if (
        nrc.run_id != nrc_target.connector_run_id
        or not isinstance(nrc.content_id, str)
        or not nrc.content_id
        or sciencebase.connector_key != "sciencebase_mcs"
        or sciencebase.connector_run_id != sciencebase_target.connector_run_id
        or sciencebase.status != "recorded"
        or not isinstance(sciencebase.connector_source_intake_record_id, str)
        or not sciencebase.connector_source_intake_record_id
    ):
        raise DualLiveEvaluationError("dual_live_phase_b_source_invalid")
    return {
        "nrc_adams_aps": nrc.content_id,
        "sciencebase_mcs": sciencebase.connector_source_intake_record_id,
    }


def _ordered_package_rows(rows: Sequence[Any]) -> tuple[Any, ...]:
    rank = {kind: index for index, kind in enumerate(_PACKAGE_KINDS)}
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                rank.get(str(row.package_kind), len(rank)),
                str(row.package_kind),
                str(row.output_package_id),
            ),
        )
    )


def _load_packages(
    db: Any,
    sessions: Mapping[str, Any],
) -> dict[str, tuple[Any, ...]]:
    from sqlalchemy import select

    from app.models.models import L3OutputPackage

    packages: dict[str, tuple[Any, ...]] = {}
    if set(sessions) != set(_EXPECTED_CONNECTORS):
        raise DualLiveEvaluationError("dual_live_downstream_session_missing")
    for connector_key in _EXPECTED_CONNECTORS:
        session = sessions[connector_key]
        session_id = session.session_id
        rows = tuple(
            db.scalars(
                select(L3OutputPackage)
                .where(L3OutputPackage.session_id == session_id)
                .order_by(L3OutputPackage.package_kind.asc())
                .limit(4)
            )
        )
        packages[connector_key] = _ordered_package_rows(rows)
    return packages


def _origin_integrity(receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    connector_key = receipt.get("connector_key")
    target_id = receipt.get("connector_run_target_id")
    receipt_hash = receipt.get("receipt_hash")
    proof_class = receipt.get("proof_class")
    if (
        connector_key not in _EXPECTED_CONNECTORS
        or not isinstance(target_id, str)
        or not target_id
        or not isinstance(receipt_hash, str)
        or not _LOWERCASE_SHA256.fullmatch(receipt_hash)
        or proof_class != "fresh_live"
    ):
        raise DualLiveEvaluationError("dual_live_origin_receipt_invalid")
    return MappingProxyType(
        {
            "schema_id": "layer3.connector_origin_integrity.v1",
            "connector_key": connector_key,
            "connector_run_target_id": target_id,
            "connector_origin_receipt_hash": receipt_hash,
            "proof_class": proof_class,
        }
    )


def _load_execution_evidence(
    db: Any,
    *,
    sessions: Mapping[str, Any],
    origins: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Mapping[str, Any]]]:
    from sqlalchemy import select

    from app.models.models import L3PassRun
    from app.services.layer3_execution_output import (
        Layer3ExecutionOutputIntegrityError,
        assert_pass_output_integrity,
    )

    pass_runs: dict[str, Any] = {}
    outputs: dict[str, Mapping[str, Any]] = {}
    for connector_key in _EXPECTED_CONNECTORS:
        session = sessions.get(connector_key)
        receipt = origins.get(connector_key)
        if session is None or receipt is None:
            raise DualLiveEvaluationError("dual_live_execution_evidence_missing")
        expected_origin = _origin_integrity(receipt)
        rows = tuple(
            db.scalars(
                select(L3PassRun)
                .where(L3PassRun.session_id == session.session_id)
                .order_by(L3PassRun.created_at.asc(), L3PassRun.pass_run_id.asc())
                .limit(MAX_DB_ROWS + 1)
            )
        )
        if len(rows) > MAX_DB_ROWS:
            raise DualLiveEvaluationError("dual_live_db_row_cap_exceeded")
        matched = tuple(
            row
            for row in rows
            if isinstance(row.summary_json, Mapping)
            and row.summary_json.get("connector_origin_integrity_v1")
            == expected_origin
        )
        if len(matched) != 1:
            raise DualLiveEvaluationError("dual_live_execution_evidence_ambiguous")
        pass_run = matched[0]
        pass_runs[connector_key] = pass_run
        if (
            pass_run.status not in {"completed", "completed_with_warnings"}
            or not str(pass_run.output_payload_ref or "").strip()
        ):
            outputs[connector_key] = MappingProxyType({})
            continue
        try:
            output = assert_pass_output_integrity(
                db,
                pass_run_id=pass_run.pass_run_id,
            )
        except Layer3ExecutionOutputIntegrityError:
            outputs[connector_key] = MappingProxyType({})
        else:
            outputs[connector_key] = MappingProxyType(dict(output))
    return pass_runs, outputs


def _load_review_states(
    pass_runs: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    states: dict[str, Mapping[str, Any]] = {}
    for connector_key in _EXPECTED_CONNECTORS:
        pass_run = pass_runs.get(connector_key)
        summary = getattr(pass_run, "summary_json", None)
        if not isinstance(summary, Mapping) or "execution_result_review" not in summary:
            raise DualLiveEvaluationError("dual_live_review_state_missing")
        raw = summary.get("execution_result_review")
        states[connector_key] = (
            MappingProxyType(dict(raw))
            if isinstance(raw, Mapping)
            else MappingProxyType({})
        )
    return states


def _load_reconciliations(
    db: Any,
    *,
    sessions: Mapping[str, Any],
) -> dict[str, Any]:
    from sqlalchemy import select

    from app.models.models import L3ReconciliationRecord

    reconciliations: dict[str, Any] = {}
    for connector_key in _EXPECTED_CONNECTORS:
        session = sessions.get(connector_key)
        if session is None:
            raise DualLiveEvaluationError("dual_live_reconciliation_missing")
        rows = tuple(
            db.scalars(
                select(L3ReconciliationRecord)
                .where(L3ReconciliationRecord.session_id == session.session_id)
                .limit(2)
            )
        )
        if len(rows) != 1:
            raise DualLiveEvaluationError("dual_live_reconciliation_missing")
        reconciliations[connector_key] = rows[0]
    return reconciliations


def _reconciliation_states(
    reconciliations: Mapping[str, Any],
    *,
    state_key: str,
    missing_code: str,
) -> dict[str, Mapping[str, Any]]:
    states: dict[str, Mapping[str, Any]] = {}
    for connector_key in _EXPECTED_CONNECTORS:
        reconciliation = reconciliations.get(connector_key)
        summary = getattr(reconciliation, "summary_json", None)
        if not isinstance(summary, Mapping) or state_key not in summary:
            raise DualLiveEvaluationError(missing_code)
        raw = summary.get(state_key)
        states[connector_key] = (
            MappingProxyType(dict(raw))
            if isinstance(raw, Mapping)
            else MappingProxyType({})
        )
    return states


def _strict_package_payload(payload_bytes: bytes) -> dict[str, Any]:
    from app.services.layer3_utils import stable_json_text_bytes

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object key")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"invalid JSON constant: {value}")

    try:
        payload = json.loads(
            payload_bytes.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except (RecursionError, UnicodeDecodeError, ValueError) as exc:
        raise DualLiveEvaluationError("dual_live_package_payload_invalid") from exc
    if (
        not isinstance(payload, dict)
        or payload_bytes != stable_json_text_bytes(payload)
    ):
        raise DualLiveEvaluationError("dual_live_package_payload_invalid")
    return payload


def _validate_package_integrity_pair(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    from app.services.layer3_execution_output import (
        Layer3ExecutionOutputIntegrityError,
        artifact_set_hash,
    )

    origin = payload.get("connector_origin_integrity_v1")
    output = payload.get("connector_output_integrity_v1")
    origin_fields = {
        "schema_id",
        "connector_key",
        "connector_run_target_id",
        "connector_origin_receipt_hash",
        "proof_class",
    }
    output_fields = {
        "schema_id",
        "connector_key",
        "connector_run_target_id",
        "connector_origin_receipt_hash",
        "proof_class",
        "artifact_receipts",
        "artifact_set_hash",
        "output_manifest_sha256",
    }
    if (
        not isinstance(origin, Mapping)
        or set(origin) != origin_fields
        or not isinstance(output, Mapping)
        or set(output) != output_fields
    ):
        raise DualLiveEvaluationError("dual_live_package_integrity_invalid")
    receipt_hash = origin.get("connector_origin_receipt_hash")
    artifact_hash = output.get("artifact_set_hash")
    manifest_hash = output.get("output_manifest_sha256")
    if (
        origin.get("schema_id") != "layer3.connector_origin_integrity.v1"
        or origin.get("connector_key") not in _EXPECTED_CONNECTORS
        or origin.get("proof_class") != "fresh_live"
        or not isinstance(origin.get("connector_run_target_id"), str)
        or not origin.get("connector_run_target_id")
        or not isinstance(receipt_hash, str)
        or not _LOWERCASE_SHA256.fullmatch(receipt_hash)
        or output.get("schema_id") != "layer3.connector_output_integrity.v1"
        or any(
            output.get(field) != origin.get(field)
            for field in (
                "connector_key",
                "connector_run_target_id",
                "connector_origin_receipt_hash",
                "proof_class",
            )
        )
        or not isinstance(artifact_hash, str)
        or not _LOWERCASE_SHA256.fullmatch(artifact_hash)
        or not isinstance(manifest_hash, str)
        or not _LOWERCASE_SHA256.fullmatch(manifest_hash)
        or not isinstance(output.get("artifact_receipts"), list)
    ):
        raise DualLiveEvaluationError("dual_live_package_integrity_invalid")
    try:
        computed_artifact_hash = artifact_set_hash(output["artifact_receipts"])
    except Layer3ExecutionOutputIntegrityError as exc:
        raise DualLiveEvaluationError(
            "dual_live_package_integrity_invalid"
        ) from exc
    if computed_artifact_hash != artifact_hash:
        raise DualLiveEvaluationError("dual_live_package_integrity_invalid")
    return dict(origin), dict(output)


def _package_payload_bytes(settings: Any, package: Any) -> bytes:
    root, root_info = _fixed_local_path_before_touch(
        Path(settings.artifact_storage_dir) / "layer3",
        code="dual_live_package_root_invalid",
    )
    if root_info is None or not stat.S_ISDIR(root_info.st_mode):
        raise DualLiveEvaluationError("dual_live_package_root_invalid")
    raw_ref = package.payload_ref
    if not isinstance(raw_ref, str) or not raw_ref or raw_ref != raw_ref.strip():
        raise DualLiveEvaluationError("dual_live_package_ref_unsafe")
    raw_candidate = PureWindowsPath(raw_ref.replace("/", "\\"))
    candidate_value = raw_ref if raw_candidate.is_absolute() else str(root / raw_ref)
    candidate, candidate_info = _fixed_local_path_before_touch(
        candidate_value,
        code="dual_live_package_ref_unsafe",
    )
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise DualLiveEvaluationError("dual_live_package_ref_outside_root") from exc
    if any(component in {"", ".", ".."} for component in relative.parts):
        raise DualLiveEvaluationError("dual_live_package_ref_outside_root")
    if candidate_info is None or not stat.S_ISREG(candidate_info.st_mode):
        raise DualLiveEvaluationError("dual_live_package_payload_missing")
    return _stable_bounded_read(
        candidate,
        max_bytes=MAX_SOURCE_BYTES,
        size_code="dual_live_package_payload_size_invalid",
        unsafe_code="dual_live_package_ref_unsafe",
        changed_code="dual_live_package_payload_changed",
    )


def _load_package_payloads(
    *,
    settings: Any,
    packages: Mapping[str, tuple[Any, ...]],
    origins: Mapping[str, Mapping[str, Any]],
    output_integrity: Mapping[str, Mapping[str, Any]],
) -> dict[str, tuple[Mapping[str, Any], ...]]:
    payloads: dict[str, tuple[Mapping[str, Any], ...]] = {}
    for connector_key in _EXPECTED_CONNECTORS:
        rows = _ordered_package_rows(packages.get(connector_key, ()))
        receipt = origins.get(connector_key)
        output = output_integrity.get(connector_key)
        if receipt is None or output is None or not output:
            payloads[connector_key] = ()
            continue
        try:
            if (
                len(rows) != len(_PACKAGE_KINDS)
                or {str(row.package_kind) for row in rows}
                != set(_PACKAGE_KINDS)
                or len({str(row.session_id or "") for row in rows}) != 1
                or "" in {str(row.session_id or "") for row in rows}
                or len(
                    {str(row.reconciliation_record_id or "") for row in rows}
                )
                != 1
                or ""
                in {str(row.reconciliation_record_id or "") for row in rows}
            ):
                raise DualLiveEvaluationError("dual_live_package_set_invalid")
            expected_origin = dict(_origin_integrity(receipt))
            expected_output = dict(output)
            verified: list[Mapping[str, Any]] = []
            observed_pair: tuple[dict[str, Any], dict[str, Any]] | None = None
            canonical_key = f"l3:{rows[0].session_id}:canonical_internal"
            for row in rows:
                payload_bytes = _package_payload_bytes(settings, row)
                if hashlib.sha256(payload_bytes).hexdigest() != row.payload_hash:
                    raise DualLiveEvaluationError(
                        "dual_live_package_payload_hash_invalid"
                    )
                payload = _strict_package_payload(payload_bytes)
                header = payload.get("package_header")
                package_kind = str(row.package_kind)
                if (
                    not isinstance(header, Mapping)
                    or header.get("package_kind") != package_kind
                    or header.get("schema_id") != _PACKAGE_SCHEMA_IDS[package_kind]
                    or header.get("session_id") != row.session_id
                    or header.get("package_status") != row.status
                    or header.get("package_key")
                    != f"l3:{row.session_id}:{package_kind}"
                    or (
                        package_kind == "canonical_internal"
                        and header.get("canonical_package_key") is not None
                    )
                    or (
                        package_kind != "canonical_internal"
                        and header.get("canonical_package_key") != canonical_key
                    )
                ):
                    raise DualLiveEvaluationError(
                        "dual_live_package_header_invalid"
                    )
                pair = _validate_package_integrity_pair(payload)
                if observed_pair is None:
                    observed_pair = pair
                elif pair != observed_pair:
                    raise DualLiveEvaluationError(
                        "dual_live_package_integrity_invalid"
                    )
                verified.append(payload)
            if observed_pair != (expected_origin, expected_output):
                raise DualLiveEvaluationError("dual_live_package_integrity_invalid")
        except (DualLiveEvaluationError, OSError):
            payloads[connector_key] = ()
        else:
            by_kind = {
                str(payload.get("package_header", {}).get("package_kind")): payload
                for payload in verified
                if isinstance(payload.get("package_header"), Mapping)
            }
            payloads[connector_key] = tuple(
                MappingProxyType(dict(by_kind[kind]))
                for kind in _PACKAGE_KINDS
                if kind in by_kind
            )
    return payloads


def _unsafe_path(code: str) -> NoReturn:
    raise DualLiveEvaluationError(code)


def _lexical_fixed_local_path(value: object, *, code: str) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        _unsafe_path(code)
    text = value if isinstance(value, str) else os.fspath(value)
    if not isinstance(text, str) or not text or text != text.strip() or "\x00" in text:
        _unsafe_path(code)
    normalized = text.replace("/", "\\")
    folded = normalized.casefold()
    if (
        folded.startswith(("\\\\", "\\??\\", "globalroot\\"))
        or not re.fullmatch(r"[A-Za-z]:\\.*", normalized)
        or ":" in normalized[2:]
    ):
        _unsafe_path(code)
    windows_path = PureWindowsPath(normalized)
    if not windows_path.is_absolute() or len(windows_path.drive) != 2:
        _unsafe_path(code)
    for component in windows_path.parts[1:]:
        if (
            component in {"", ".", ".."}
            or component.endswith((" ", "."))
            or any(character in component for character in '*?"<>|')
            or component.split(".", 1)[0].upper() in _WINDOWS_RESERVED_COMPONENTS
        ):
            _unsafe_path(code)
    path = Path(normalized)
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        drive_root = f"{windows_path.drive}\\"
        get_drive_type = ctypes.windll.kernel32.GetDriveTypeW
        get_drive_type.argtypes = (wintypes.LPCWSTR,)
        get_drive_type.restype = wintypes.UINT
        if get_drive_type(drive_root) != _DRIVE_FIXED:
            _unsafe_path(code)
    return path


def _path_has_reparse_attribute(info: os.stat_result) -> bool:
    return bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _fixed_local_path_before_touch(
    value: object,
    *,
    code: str,
) -> tuple[Path, os.stat_result | None]:
    path = _lexical_fixed_local_path(value, code=code)
    ordered = [Path(path.anchor)]
    ordered.extend(reversed(path.parents[:-1]))
    ordered.append(path)
    last: os.stat_result | None = None
    for component in ordered:
        try:
            info = component.lstat()
        except FileNotFoundError:
            return path, None
        if component.is_symlink() or _path_has_reparse_attribute(info):
            _unsafe_path(code)
        last = info
    return path, last


def _opened_windows_path(handle: Any, *, code: str) -> Path:
    if os.name != "nt":
        return Path(str(handle.name))
    import ctypes
    from ctypes import wintypes
    import msvcrt

    kernel32 = ctypes.windll.kernel32
    native_handle = msvcrt.get_osfhandle(handle.fileno())
    get_final_path = kernel32.GetFinalPathNameByHandleW
    get_final_path.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    get_final_path.restype = wintypes.DWORD
    capacity = 512
    while True:
        buffer = ctypes.create_unicode_buffer(capacity)
        length = get_final_path(
            wintypes.HANDLE(native_handle),
            buffer,
            capacity,
            0,
        )
        if length == 0:
            _unsafe_path(code)
        if length < capacity:
            final = buffer.value
            break
        capacity = int(length) + 1
        if capacity > 32_768:
            _unsafe_path(code)
    if final.casefold().startswith("\\\\?\\unc\\"):
        _unsafe_path(code)
    if final.startswith("\\\\?\\"):
        final = final[4:]
    return _lexical_fixed_local_path(final, code=code)


def _path_identity(value: Path) -> str:
    return os.path.normcase(os.path.normpath(str(value)))


def _assert_opened_fixed_local_path(
    handle: Any,
    *,
    expected_path: Path,
    code: str,
) -> None:
    opened = _opened_windows_path(handle, code=code)
    if _path_identity(opened) != _path_identity(expected_path):
        _unsafe_path(code)


def _collect_non_source_files(
    settings: Any,
    *,
    source_exemptions: Sequence[tuple[str, str]],
) -> tuple[tuple[str, bytes], ...]:
    raw_roots = tuple(
        value
        for value in (
            settings.connector_reports_dir,
            settings.connector_manifests_dir,
            settings.connector_snapshots_dir,
            settings.artifact_storage_dir,
            settings.dataset_storage_dir,
            settings.layer3_local_outbox_dir,
        )
        if str(value or "").strip()
    )
    exempt_absolute: set[str] = set()
    if source_exemptions:
        source_root, source_root_info = _fixed_local_path_before_touch(
            settings.connector_raw_dir,
            code="dual_live_source_root_invalid",
        )
        if source_root_info is None or not stat.S_ISDIR(source_root_info.st_mode):
            raise DualLiveEvaluationError("dual_live_source_root_invalid")
        for raw_ref, digest in source_exemptions:
            if (
                not isinstance(raw_ref, str)
                or not raw_ref
                or raw_ref != raw_ref.strip()
                or not isinstance(digest, str)
                or _LOWERCASE_SHA256.fullmatch(digest) is None
            ):
                raise DualLiveEvaluationError("dual_live_source_ref_unsafe")
            raw_candidate = PureWindowsPath(raw_ref.replace("/", "\\"))
            candidate_value = (
                raw_ref if raw_candidate.is_absolute() else str(source_root / raw_ref)
            )
            candidate, candidate_info = _fixed_local_path_before_touch(
                candidate_value,
                code="dual_live_source_ref_unsafe",
            )
            try:
                source_relative = candidate.relative_to(source_root)
            except ValueError as exc:
                raise DualLiveEvaluationError(
                    "dual_live_source_ref_outside_root"
                ) from exc
            if (
                any(
                    component in {"", ".", ".."}
                    for component in source_relative.parts
                )
                or candidate_info is None
                or not stat.S_ISREG(candidate_info.st_mode)
            ):
                raise DualLiveEvaluationError("dual_live_source_ref_unsafe")
            exempt_absolute.add(_path_identity(candidate))
    candidates: list[tuple[int, Path, str]] = []
    scanned_nodes = 0
    for root_index, raw_root in enumerate(raw_roots):
        root, root_stat = _fixed_local_path_before_touch(
            raw_root,
            code="dual_live_scan_root_unsafe",
        )
        if root_stat is None:
            continue
        if not stat.S_ISDIR(root_stat.st_mode):
            raise DualLiveEvaluationError("dual_live_scan_root_unsafe")
        pending = [root]
        while pending:
            directory = pending.pop()
            directory_entries: list[os.DirEntry[str]] = []
            with os.scandir(directory) as iterator:
                for entry in iterator:
                    scanned_nodes += 1
                    if scanned_nodes > MAX_SCAN_NODES:
                        raise DualLiveEvaluationError(
                            "dual_live_scan_node_cap_exceeded"
                        )
                    directory_entries.append(entry)
            for entry in sorted(directory_entries, key=lambda item: item.name):
                path = Path(entry.path)
                path_stat = entry.stat(follow_symlinks=False)
                if entry.is_symlink() or (
                    getattr(path_stat, "st_file_attributes", 0)
                    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
                ):
                    raise DualLiveEvaluationError("dual_live_scan_member_unsafe")
                if stat.S_ISDIR(path_stat.st_mode):
                    pending.append(path)
                    continue
                if not stat.S_ISREG(path_stat.st_mode):
                    raise DualLiveEvaluationError("dual_live_scan_member_unsafe")
                scan_relative = path.relative_to(root).as_posix()
                if _path_identity(path) in exempt_absolute:
                    continue
                candidates.append((root_index, path, scan_relative))
                if len(candidates) > MAX_SCAN_FILES:
                    raise DualLiveEvaluationError(
                        "dual_live_scan_file_cap_exceeded"
                    )

    total = 0
    for _root_index, path, _relative in candidates:
        size = path.lstat().st_size
        if size < 0 or size > MAX_SCAN_FILE_BYTES:
            raise DualLiveEvaluationError("dual_live_scan_file_size_exceeded")
        total += size
        if total > MAX_SCAN_TOTAL_BYTES:
            raise DualLiveEvaluationError("dual_live_scan_total_size_exceeded")

    files: list[tuple[str, bytes]] = []
    for root_index, path, scan_relative in sorted(
        candidates,
        key=lambda item: (item[0], item[2]),
    ):
        payload = _stable_bounded_read(
            path,
            max_bytes=MAX_SCAN_FILE_BYTES,
            size_code="dual_live_scan_file_size_exceeded",
            unsafe_code="dual_live_scan_member_unsafe",
            changed_code="dual_live_scan_member_changed",
        )
        files.append((f"root-{root_index}:{scan_relative}", payload))
    return tuple(files)


def _preflight_evidence_settings(settings: Any) -> None:
    root, root_info = _fixed_local_path_before_touch(
        settings.connector_campaign_evidence_root,
        code="dual_live_evidence_root_unsafe",
    )
    if root_info is None or not stat.S_ISDIR(root_info.st_mode):
        raise DualLiveEvaluationError("dual_live_evidence_root_unsafe")
    head_sha256 = str(settings.connector_campaign_evidence_index_sha256 or "")
    if _LOWERCASE_SHA256.fullmatch(head_sha256) is None:
        raise DualLiveEvaluationError("dual_live_evidence_index_unsafe")
    expected = root / "indexes" / f"{head_sha256}.json"
    configured, configured_info = _fixed_local_path_before_touch(
        settings.connector_campaign_evidence_index_path,
        code="dual_live_evidence_index_unsafe",
    )
    indexes, indexes_info = _fixed_local_path_before_touch(
        root / "indexes",
        code="dual_live_evidence_index_unsafe",
    )
    if (
        _path_identity(configured) != _path_identity(expected)
        or indexes_info is None
        or not stat.S_ISDIR(indexes_info.st_mode)
        or configured_info is None
        or not stat.S_ISREG(configured_info.st_mode)
    ):
        raise DualLiveEvaluationError("dual_live_evidence_index_unsafe")
    try:
        configured.relative_to(indexes)
    except ValueError as exc:
        raise DualLiveEvaluationError("dual_live_evidence_index_unsafe") from exc


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


def _stable_bounded_read(
    path: Path,
    *,
    max_bytes: int,
    size_code: str,
    unsafe_code: str,
    changed_code: str,
) -> bytes:
    before = path.lstat()
    if path.is_symlink() or (
        getattr(before, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    ) or not stat.S_ISREG(before.st_mode):
        raise DualLiveEvaluationError(unsafe_code)
    if before.st_size < 0 or before.st_size > max_bytes:
        raise DualLiveEvaluationError(size_code)
    chunks: list[bytes] = []
    total = 0
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        _assert_opened_fixed_local_path(
            handle,
            expected_path=path,
            code=unsafe_code,
        )
        if _stat_identity(opened) != _stat_identity(before):
            raise DualLiveEvaluationError(changed_code)
        while True:
            chunk = handle.read(min(1024 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise DualLiveEvaluationError(size_code)
        after = os.fstat(handle.fileno())
    final = path.lstat()
    if (
        _stat_identity(before) != _stat_identity(after)
        or _stat_identity(after) != _stat_identity(final)
    ):
        raise DualLiveEvaluationError(changed_code)
    return b"".join(chunks)


def _build_independent_observation_engine(settings: Any) -> Any:
    import sqlite3

    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    database_path = _database_path(settings)
    database_uri = (
        f"file:{database_path.as_posix()}?mode=ro&cache=private"
    )

    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(
            database_uri,
            uri=True,
            check_same_thread=False,
        )
        try:
            connection.execute("PRAGMA query_only=ON")
            return connection
        except BaseException:
            connection.close()
            raise

    return create_engine(
        "sqlite+pysqlite://",
        creator=connect,
        future=True,
        poolclass=NullPool,
    )


def _collect_independent_capture_evidence(
    *,
    settings: Any,
    chain: Any,
    capture_ref: Any,
    campaign_id: str,
    campaign_fingerprint: str,
) -> _IndependentCaptureEvidence:
    from sqlalchemy import select
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import Session as OwnedSession

    from app.models.models import ConnectorRun, ConnectorRunEvent
    from app.schemas.api import (
        ConnectorCampaignLogManifestV1,
        ConnectorCampaignLogSealV1,
    )
    from app.services.connector_egress_evidence import (
        MAX_AGGREGATE_BYTES,
        MAX_PROTECTED_JSON_BYTES,
        MAX_STREAM_BYTES,
        ConnectorEvidenceError,
        _parse_canonical_capture_model,
        _read_stable_capture_bytes,
        _validate_log_capture_paths,
        canonical_json_bytes,
    )

    expected_errors = (
        ConnectorEvidenceError,
        DualLiveEvaluationError,
        OSError,
        SQLAlchemyError,
        TypeError,
        ValueError,
    )
    errors: dict[str, str] = {}
    manifest = seal = None
    manifest_bytes = seal_bytes = b""
    manifest_sha256 = file_set_hash = seal_sha256 = ""
    stream_bytes: dict[str, bytes] = {}
    runs: tuple[_CaptureRunProjection, ...] = ()
    events: tuple[_CaptureSealEventProjection, ...] = ()

    try:
        _log_dir, manifest_relative_path, seal_relative_path = (
            _validate_log_capture_paths(capture_ref)
        )
    except expected_errors as exc:
        errors["paths"] = _domain_code(exc)
        return _IndependentCaptureEvidence(
            errors=MappingProxyType(errors),
        )

    try:
        manifest_snapshot = _read_stable_capture_bytes(
            chain.evidence_root,
            manifest_relative_path,
            max_bytes=MAX_PROTECTED_JSON_BYTES,
        )
        manifest = _parse_canonical_capture_model(
            manifest_snapshot,
            ConnectorCampaignLogManifestV1,
            label="campaign log manifest",
        )
        manifest_bytes = manifest_snapshot.data
        manifest_sha256 = manifest_snapshot.sha256
        file_set_hash = hashlib.sha256(
            canonical_json_bytes(
                {
                    "schema_id": "project6.connector_campaign_log_file_set.v1",
                    "files": [
                        item.model_dump(mode="python") for item in manifest.files
                    ],
                }
            )
        ).hexdigest()
    except expected_errors as exc:
        errors["manifest"] = _domain_code(exc)

    try:
        seal_snapshot = _read_stable_capture_bytes(
            chain.evidence_root,
            seal_relative_path,
            max_bytes=MAX_PROTECTED_JSON_BYTES,
        )
        seal = _parse_canonical_capture_model(
            seal_snapshot,
            ConnectorCampaignLogSealV1,
            label="campaign log seal",
        )
        seal_bytes = seal_snapshot.data
        seal_sha256 = seal_snapshot.sha256
    except expected_errors as exc:
        errors["seal"] = _domain_code(exc)

    if manifest is not None:
        aggregate = 0
        try:
            for item in manifest.files:
                snapshot = _read_stable_capture_bytes(
                    chain.evidence_root,
                    item.relative_path,
                    max_bytes=MAX_STREAM_BYTES,
                )
                aggregate += snapshot.size
                if aggregate > MAX_AGGREGATE_BYTES:
                    raise DualLiveEvaluationError(
                        "connector_campaign_log_read_aggregate_oversized"
                    )
                stream_bytes[item.relative_path] = snapshot.data
        except expected_errors as exc:
            errors["streams"] = _domain_code(exc)

    if seal is not None:
        independent_engine = None
        independent_connection = None
        independent_db = None
        try:
            database_path = _database_path(settings)
            independent_engine = _build_independent_observation_engine(
                settings
            )
            independent_connection = independent_engine.connect()
            query_only = independent_connection.exec_driver_sql(
                "PRAGMA query_only"
            ).scalar_one()
            journal_mode = independent_connection.exec_driver_sql(
                "PRAGMA journal_mode"
            ).scalar_one()
            database_list = tuple(
                independent_connection.exec_driver_sql(
                    "PRAGMA database_list"
                ).all()
            )
            if query_only != 1:
                raise DualLiveEvaluationError(
                    "dual_live_database_query_only_refused"
                )
            if str(journal_mode).casefold() != "delete":
                raise DualLiveEvaluationError(
                    "dual_live_database_journal_mode_unsafe"
                )
            if (
                len(database_list) != 1
                or database_list[0][1] != "main"
                or os.path.normcase(
                    str(Path(database_list[0][2]).resolve(strict=True))
                )
                != os.path.normcase(str(database_path.resolve(strict=True)))
            ):
                raise DualLiveEvaluationError(
                    "dual_live_database_attachment_unsafe"
                )
            if independent_connection.in_transaction():
                independent_connection.rollback()
            independent_db = OwnedSession(
                bind=independent_connection,
                autoflush=False,
                expire_on_commit=False,
                future=True,
            )
            arming = ConnectorRun.request_config_json["connector_egress_arming"]
            run_rows = tuple(
                independent_db.scalars(
                    select(ConnectorRun)
                    .where(
                        ConnectorRun.source_mode == "strict_live_egress",
                        arming["campaign_id"].as_string() == campaign_id,
                        arming["campaign_fingerprint"].as_string()
                        == campaign_fingerprint,
                    )
                    .order_by(ConnectorRun.connector_run_id.asc())
                    .limit(3)
                    .execution_options(populate_existing=True)
                )
            )
            runs = tuple(
                _CaptureRunProjection(
                    connector_run_id=str(run.connector_run_id),
                    status=str(run.status),
                )
                for run in run_rows
            )
            run_ids = tuple(run.connector_run_id for run in runs)
            if run_ids:
                event_rows = tuple(
                    independent_db.scalars(
                        select(ConnectorRunEvent)
                        .where(
                            ConnectorRunEvent.event_type
                            == "campaign_log_capture_sealed",
                            ConnectorRunEvent.connector_run_id.in_(run_ids),
                        )
                        .order_by(
                            ConnectorRunEvent.connector_run_id.asc(),
                            ConnectorRunEvent.created_at.asc(),
                            ConnectorRunEvent.connector_run_event_id.asc(),
                        )
                        .limit(3)
                        .execution_options(populate_existing=True)
                    )
                )
                events = tuple(
                    _CaptureSealEventProjection(
                        connector_run_event_id=str(
                            event.connector_run_event_id
                        ),
                        connector_run_id=str(event.connector_run_id),
                        connector_run_target_id=(
                            None
                            if event.connector_run_target_id is None
                            else str(event.connector_run_target_id)
                        ),
                        phase=str(event.phase),
                        stage=str(event.stage),
                        event_type=str(event.event_type),
                        status_before=(
                            None
                            if event.status_before is None
                            else str(event.status_before)
                        ),
                        status_after=(
                            None
                            if event.status_after is None
                            else str(event.status_after)
                        ),
                        reason_code=(
                            None
                            if event.reason_code is None
                            else str(event.reason_code)
                        ),
                        error_class=(
                            None
                            if event.error_class is None
                            else str(event.error_class)
                        ),
                        message=(
                            None if event.message is None else str(event.message)
                        ),
                        metrics_bytes=_json_observation_bytes(
                            event.metrics_json
                        ),
                        created_at=event.created_at,
                    )
                    for event in event_rows
                )
        except expected_errors as exc:
            errors["events"] = _domain_code(exc)
        finally:
            try:
                if independent_db is not None:
                    if independent_db.in_transaction():
                        independent_db.rollback()
                    independent_db.close()
            finally:
                try:
                    if independent_connection is not None:
                        if independent_connection.in_transaction():
                            independent_connection.rollback()
                        independent_connection.close()
                finally:
                    if independent_engine is not None:
                        independent_engine.dispose()

    return _IndependentCaptureEvidence(
        manifest=manifest,
        manifest_bytes=manifest_bytes,
        manifest_sha256=manifest_sha256,
        file_set_hash=file_set_hash,
        seal=seal,
        seal_bytes=seal_bytes,
        seal_sha256=seal_sha256,
        stream_bytes=MappingProxyType(stream_bytes),
        runs=runs,
        seal_events=events,
        errors=MappingProxyType(errors),
    )


def _database_path(settings: Any) -> Path:
    raw_url = str(settings.database_url).strip()
    prefix = "sqlite:///"
    if (
        not raw_url.startswith(prefix)
        or any(token in raw_url for token in ("?", "#"))
    ):
        raise DualLiveEvaluationError("dual_live_database_url_invalid")
    raw_path = raw_url[len(prefix) :]
    if not raw_path or raw_path == ":memory:" or raw_path.startswith("file:"):
        raise DualLiveEvaluationError("dual_live_database_url_invalid")
    path, info = _fixed_local_path_before_touch(
        raw_path,
        code="dual_live_database_path_unsafe",
    )
    if info is None or not stat.S_ISREG(info.st_mode):
        raise DualLiveEvaluationError("dual_live_database_path_unsafe")
    return path


def _database_file_fingerprint(path: Path) -> str:
    sidecars = tuple(Path(f"{path}{suffix}") for suffix in ("-journal", "-wal", "-shm"))
    checked_path, before = _fixed_local_path_before_touch(
        path,
        code="dual_live_database_path_unsafe",
    )
    if checked_path != path or before is None:
        raise DualLiveEvaluationError("dual_live_database_path_unsafe")
    if any(
        _fixed_local_path_before_touch(
            sidecar,
            code="dual_live_database_path_unsafe",
        )[1]
        is not None
        for sidecar in sidecars
    ):
        raise DualLiveEvaluationError("dual_live_database_sidecar_present")
    if not stat.S_ISREG(before.st_mode) or before.st_size <= 0:
        raise DualLiveEvaluationError("dual_live_database_path_unsafe")
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        _assert_opened_fixed_local_path(
            handle,
            expected_path=path,
            code="dual_live_database_path_unsafe",
        )
        opened = os.fstat(handle.fileno())
        if _stat_identity(opened) != _stat_identity(before):
            raise DualLiveEvaluationError("dual_live_database_file_changed")
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
            if total > before.st_size:
                raise DualLiveEvaluationError("dual_live_database_file_changed")
        after = os.fstat(handle.fileno())
    final = path.lstat()
    sidecar_present = any(
        _fixed_local_path_before_touch(
            sidecar,
            code="dual_live_database_path_unsafe",
        )[1]
        is not None
        for sidecar in sidecars
    )
    if (
        total != before.st_size
        or _stat_identity(before) != _stat_identity(after)
        or _stat_identity(after) != _stat_identity(final)
        or sidecar_present
    ):
        raise DualLiveEvaluationError("dual_live_database_file_changed")
    return _snapshot_hash(
        (
            ("identity", _stat_identity(final)),
            ("sha256", digest.hexdigest()),
        )
    )


def _evidence_snapshot(
    context: _EvidenceContext,
    *,
    chain: Any,
    historical: Mapping[str, Any],
    capture: Any,
    non_source_files: Sequence[tuple[str, bytes]],
) -> str:
    chain_snapshot = tuple(
        (
            item.model.revision,
            len(item.raw_bytes),
            item.raw_sha256,
        )
        for item in chain.revisions
    )
    archive_snapshot = tuple(
        (
            connector_key,
            evidence.raw_definition_sha256,
            evidence.raw_sha256,
            evidence.consumption_marker_sha256,
        )
        for connector_key, evidence in sorted(historical.items())
    )
    capture_snapshot = (
        len(capture.manifest_bytes),
        capture.manifest_sha256,
        capture.file_set_hash,
        len(capture.seal_bytes),
        capture.seal_sha256,
        tuple(
            (name, len(payload), hashlib.sha256(payload).hexdigest())
            for name, payload in sorted(capture.stream_bytes.items())
        ),
        capture.seal_event_ids,
        capture.stable_snapshot,
    )
    non_source_snapshot = tuple(
        (identity, len(payload), hashlib.sha256(payload).hexdigest())
        for identity, payload in non_source_files
    )
    source_snapshot = tuple(
        (
            raw_ref.replace("\\", "/"),
            hashlib.sha256(_source_blob(context, raw_ref)).hexdigest(),
        )
        for raw_ref, _expected_digest in context.source_exemptions
    )
    return _snapshot_hash(
        (
            ("chain", chain_snapshot),
            ("archive", archive_snapshot),
            ("capture", capture_snapshot),
            ("non_source", non_source_snapshot),
            ("source", source_snapshot),
        )
    )


def _database_snapshot(
    db_values: Sequence[tuple[str, Any]],
    database_file_fingerprint: str,
) -> str:
    return _snapshot_hash(
        (
            ("semantic", tuple(db_values)),
            ("file", database_file_fingerprint),
        )
    )


def _fresh_observation(
    context: _EvidenceContext,
    *,
    database_path: Path,
    runs: Sequence[Any],
    targets: Sequence[Any],
    sessions: Sequence[Any],
) -> tuple[str, str]:
    from sqlalchemy.orm import Session as OwnedSession

    from app.services.connector_egress_evidence import (
        load_evidence_index_chain_read_only,
        resolve_historical_connector_grant_evidence_read_only,
        verify_connector_campaign_log_capture_read_only,
    )

    bind = context.db.get_bind()
    engine = getattr(bind, "engine", bind)
    connect = getattr(engine, "connect", None)
    if not callable(connect):
        raise DualLiveEvaluationError("dual_live_database_fresh_session_unavailable")

    fresh_chain = None
    fresh_historical: dict[str, Any] = {}
    fresh_capture = None
    fresh_db_values: tuple[tuple[str, Any], ...] = ()
    with engine.connect() as connection:
        query_only = connection.exec_driver_sql("PRAGMA query_only").scalar_one()
        journal_mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar_one()
        database_list = tuple(
            connection.exec_driver_sql("PRAGMA database_list").all()
        )
        if query_only != 1:
            raise DualLiveEvaluationError("dual_live_database_query_only_refused")
        if str(journal_mode).casefold() != "delete":
            raise DualLiveEvaluationError("dual_live_database_journal_mode_unsafe")
        if (
            len(database_list) != 1
            or database_list[0][1] != "main"
            or os.path.normcase(str(Path(database_list[0][2]).resolve(strict=True)))
            != os.path.normcase(str(database_path.resolve(strict=True)))
        ):
            raise DualLiveEvaluationError("dual_live_database_attachment_unsafe")
        if connection.in_transaction():
            connection.rollback()

        fresh_db = OwnedSession(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )
        try:
            fresh_chain = load_evidence_index_chain_read_only(context.settings)
            _campaign_ref, fresh_entry_refs, _capture_ref = _select_campaign_slice(
                fresh_chain,
                campaign_id=context.campaign_id,
                campaign_fingerprint=context.campaign_fingerprint,
            )
            for entry in fresh_entry_refs:
                fresh_historical[entry.connector_key] = (
                    resolve_historical_connector_grant_evidence_read_only(
                        context.settings,
                        connector_key=entry.connector_key,
                        campaign_id=context.campaign_id,
                        expected_campaign_fingerprint=context.campaign_fingerprint,
                        expected_grant_sha256=entry.raw_grant_sha256,
                    )
                )
            fresh_capture = verify_connector_campaign_log_capture_read_only(
                fresh_db,
                fresh_chain,
                context.campaign_id,
                context.campaign_fingerprint,
            )
            fresh_db_values = _rows_for_selected_authority(
                fresh_db,
                runs=runs,
                targets=targets,
                sessions=sessions,
            )
            if fresh_db.new or fresh_db.dirty or fresh_db.deleted:
                raise DualLiveEvaluationError("dual_live_database_fresh_session_dirty")
        finally:
            if fresh_db.in_transaction():
                fresh_db.rollback()
            fresh_db.close()
            if connection.in_transaction():
                connection.rollback()

    if fresh_chain is None or fresh_capture is None:
        raise DualLiveEvaluationError("dual_live_fresh_evidence_unavailable")
    fresh_non_source_files = _collect_non_source_files(
        context.settings,
        source_exemptions=context.source_exemptions,
    )
    final_evidence = _evidence_snapshot(
        context,
        chain=fresh_chain,
        historical=MappingProxyType(fresh_historical),
        capture=fresh_capture,
        non_source_files=fresh_non_source_files,
    )
    final_database = _database_snapshot(
        fresh_db_values,
        _database_file_fingerprint(database_path),
    )
    return final_evidence, final_database


def _collect_evidence(
    db: Session,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
    settings: Settings,
) -> _EvidenceContext:
    from sqlalchemy import select
    from sqlalchemy.exc import SQLAlchemyError

    from app.models.models import ConnectorRunTarget
    from app.services.connector_egress_evidence import (
        ConnectorEvidenceError,
        ConnectorEgressTransportError,
        CounterEvidenceError,
        derive_terminal_request_ledger,
        load_evidence_index_chain_read_only,
        parse_connector_counter_records,
        read_runtime_records,
        resolve_historical_connector_grant_evidence_read_only,
        verify_connector_campaign_log_capture_read_only,
    )
    expected_errors = (
        ConnectorEvidenceError,
        ConnectorEgressTransportError,
        CounterEvidenceError,
        DualLiveEvaluationError,
        OSError,
        SQLAlchemyError,
        UnicodeError,
    )

    errors: dict[str, str] = {}
    chain = campaign_ref = capture_ref = capture = manifest = seal = None
    independent_capture: _IndependentCaptureEvidence | None = None
    entry_refs: tuple[Any, ...] = ()
    historical: dict[str, Any] = {}
    runtime_records: tuple[Mapping[str, Any], ...] = ()
    child_proofs: tuple[Mapping[str, Any], ...] = ()
    counter_records: tuple[Mapping[str, Any], ...] = ()
    runs: tuple[Any, ...] = ()
    run_by_connector: dict[str, Any] = {}
    envelopes: dict[str, Mapping[str, Any]] = {}
    targets: dict[str, Any] = {}
    ledgers: dict[str, Any] = {}
    origins: dict[str, Mapping[str, Any]] = {}
    downstream: dict[str, Mapping[str, Any]] = {}
    source_record_ids: dict[str, str] = {}
    sessions: tuple[Any, ...] = ()
    downstream_sessions: dict[str, Any] = {}
    pass_runs: dict[str, Any] = {}
    output_integrity: dict[str, Mapping[str, Any]] = {}
    review_states: dict[str, Mapping[str, Any]] = {}
    reconciliations: dict[str, Any] = {}
    package_commits: dict[str, Mapping[str, Any]] = {}
    submit_states: dict[str, Mapping[str, Any]] = {}
    handoff_states: dict[str, Mapping[str, Any]] = {}
    packages: dict[str, tuple[Any, ...]] = {}
    package_payloads: dict[str, tuple[Mapping[str, Any], ...]] = {}
    db_values: tuple[tuple[str, Any], ...] = ()
    non_source_files: tuple[tuple[str, bytes], ...] = ()
    source_exemptions: tuple[tuple[str, str], ...] = ()

    try:
        _preflight_evidence_settings(settings)
        chain = load_evidence_index_chain_read_only(settings)
        campaign_ref, entry_refs, capture_ref = _select_campaign_slice(
            chain,
            campaign_id=campaign_id,
            campaign_fingerprint=campaign_fingerprint,
        )
    except expected_errors as exc:
        errors["authority"] = _domain_code(exc)

    if chain is not None and campaign_ref is not None:
        try:
            for entry in entry_refs:
                historical[entry.connector_key] = (
                    resolve_historical_connector_grant_evidence_read_only(
                        settings,
                        connector_key=entry.connector_key,
                        campaign_id=campaign_id,
                        expected_campaign_fingerprint=campaign_fingerprint,
                        expected_grant_sha256=entry.raw_grant_sha256,
                    )
                )
        except expected_errors as exc:
            errors["archive"] = _domain_code(exc)

        try:
            capture = verify_connector_campaign_log_capture_read_only(
                db,
                chain,
                campaign_id,
                campaign_fingerprint,
            )
            manifest, seal = _parse_capture_models(capture)
        except expected_errors as exc:
            errors["capture"] = _domain_code(exc)

    if chain is not None and capture_ref is not None:
        try:
            independent_capture = _collect_independent_capture_evidence(
                settings=settings,
                chain=chain,
                capture_ref=capture_ref,
                campaign_id=campaign_id,
                campaign_fingerprint=campaign_fingerprint,
            )
        except expected_errors as exc:
            independent_capture = _IndependentCaptureEvidence(
                errors=MappingProxyType(
                    {"collection": _domain_code(exc)}
                ),
            )

    if capture is not None:
        try:
            app_log = _stream_bytes(capture, "app.jsonl")
            runtime_records = tuple(read_runtime_records(app_log))
            child_proofs = _parse_child_proof_records(
                _stream_bytes(capture, "stdout.log")
            )
            _validate_child_proof_runtime_bindings(
                child_proofs=child_proofs,
                runtime_records=runtime_records,
                app_log=app_log,
            )
        except expected_errors as exc:
            errors["runtime"] = _domain_code(exc)
        try:
            counter_records = tuple(
                parse_connector_counter_records(_stream_bytes(capture, "http.jsonl"))
            )
        except expected_errors as exc:
            errors["counter"] = _domain_code(exc)

    if seal is not None:
        try:
            from app.models.models import ConnectorRun

            loaded_runs = tuple(
                db.get(ConnectorRun, run_id) for run_id in seal.connector_run_ids
            )
            if any(run is None for run in loaded_runs):
                raise DualLiveEvaluationError("dual_live_extant_run_missing")
            runs = tuple(run for run in loaded_runs if run is not None)
            if len(runs) != 2:
                raise DualLiveEvaluationError("dual_live_extant_run_cardinality_invalid")
            run_by_connector = {str(run.connector_key): run for run in runs}
            if tuple(sorted(run_by_connector)) != _EXPECTED_CONNECTORS:
                raise DualLiveEvaluationError("dual_live_extant_run_connectors_invalid")
            envelopes = {
                connector_key: _run_envelope(run)
                for connector_key, run in run_by_connector.items()
            }
            target_rows = tuple(
                db.scalars(
                    select(ConnectorRunTarget)
                    .where(
                        ConnectorRunTarget.connector_run_id.in_(
                            [run.connector_run_id for run in runs]
                        )
                    )
                    .order_by(ConnectorRunTarget.connector_run_id.asc())
                    .limit(3)
                )
            )
            if len(target_rows) != 2:
                raise DualLiveEvaluationError("dual_live_target_cardinality_invalid")
            targets = {}
            for run in runs:
                matches = tuple(
                    target
                    for target in target_rows
                    if target.connector_run_id == run.connector_run_id
                )
                if len(matches) != 1:
                    raise DualLiveEvaluationError(
                        "dual_live_target_cardinality_invalid"
                    )
                targets[str(run.connector_key)] = matches[0]
        except expected_errors as exc:
            errors["ledger"] = _domain_code(exc)

    if run_by_connector and counter_records:
        try:
            ledgers = {
                connector_key: derive_terminal_request_ledger(
                    db,
                    connector_run_id=run.connector_run_id,
                    counter_records=counter_records,
                )
                for connector_key, run in run_by_connector.items()
            }
        except expected_errors as exc:
            errors["ledger"] = _domain_code(exc)

    if targets:
        try:
            if any(
                set(mapping) != set(_EXPECTED_CONNECTORS)
                for mapping in (run_by_connector, ledgers, historical, envelopes)
            ):
                raise DualLiveEvaluationError("dual_live_origin_evidence_missing")
            origins = {
                connector_key: _derive_origin_receipt_read_only(
                    settings=settings,
                    run=run_by_connector[connector_key],
                    target=target,
                    ledger=ledgers[connector_key],
                    historical=historical[connector_key],
                    envelope=envelopes[connector_key],
                )
                for connector_key, target in targets.items()
            }
            source_exemptions = tuple(
                sorted(
                    (
                        str(receipt["raw_storage_ref"]),
                        str(receipt["raw_content_sha256"]),
                    )
                    for receipt in origins.values()
                )
            )
        except expected_errors as exc:
            errors["origin"] = _domain_code(exc)

    if targets:
        try:
            source_record_ids = _load_phase_b_source_record_ids(
                db,
                targets=targets,
            )
        except expected_errors as exc:
            errors["phase_b_sources"] = _domain_code(exc)

    if origins:
        try:
            sessions, downstream = _find_sessions_and_downstream(db, origins=origins)
            downstream_sessions = dict(
                zip(_EXPECTED_CONNECTORS, sessions, strict=True)
            )
        except expected_errors as exc:
            errors["downstream"] = _domain_code(exc)

    if downstream_sessions:
        try:
            pass_runs, output_integrity = _load_execution_evidence(
                db,
                sessions=downstream_sessions,
                origins=origins,
            )
        except expected_errors as exc:
            errors["execution"] = _domain_code(exc)

        if pass_runs:
            try:
                review_states = _load_review_states(pass_runs)
            except expected_errors as exc:
                errors["review"] = _domain_code(exc)

        try:
            reconciliations = _load_reconciliations(
                db,
                sessions=downstream_sessions,
            )
        except expected_errors as exc:
            code = _domain_code(exc)
            errors["package_set"] = code
            errors["submit"] = code
            errors["handoff"] = code

        try:
            packages = _load_packages(db, downstream_sessions)
        except expected_errors as exc:
            errors["package_set"] = _domain_code(exc)

        if reconciliations:
            try:
                package_commits = _reconciliation_states(
                    reconciliations,
                    state_key="workbench_package_commit",
                    missing_code="dual_live_package_commit_missing",
                )
            except expected_errors as exc:
                errors["package_set"] = _domain_code(exc)
            try:
                submit_states = _reconciliation_states(
                    reconciliations,
                    state_key="package_review_submit",
                    missing_code="dual_live_submit_state_missing",
                )
            except expected_errors as exc:
                errors["submit"] = _domain_code(exc)
            try:
                handoff_states = _reconciliation_states(
                    reconciliations,
                    state_key="handoff_export_prepare",
                    missing_code="dual_live_handoff_state_missing",
                )
            except expected_errors as exc:
                errors["handoff"] = _domain_code(exc)

        if packages:
            package_payloads = _load_package_payloads(
                settings=settings,
                packages=packages,
                origins=origins,
                output_integrity=output_integrity,
            )

    if runs:
        try:
            db_values = _rows_for_selected_authority(
                db,
                runs=runs,
                targets=tuple(targets.values()),
                sessions=sessions,
            )
        except expected_errors as exc:
            errors["custody"] = _domain_code(exc)

    try:
        non_source_files = _collect_non_source_files(
            settings,
            source_exemptions=source_exemptions,
        )
    except expected_errors as exc:
        errors["custody"] = _domain_code(exc)

    _materialize_dependency_errors(errors)
    context = _EvidenceContext(
        campaign_id=campaign_id,
        campaign_fingerprint=campaign_fingerprint,
        settings=settings,
        db=db,
        chain=chain,
        campaign_ref=campaign_ref,
        entry_refs=entry_refs,
        capture_ref=capture_ref,
        historical=MappingProxyType(historical),
        capture=capture,
        independent_capture=independent_capture,
        manifest=manifest,
        seal=seal,
        runtime_records=runtime_records,
        child_proofs=child_proofs,
        counter_records=counter_records,
        runs=runs,
        run_by_connector=MappingProxyType(run_by_connector),
        envelopes=MappingProxyType(envelopes),
        targets=MappingProxyType(targets),
        ledgers=MappingProxyType(ledgers),
        origins=MappingProxyType(origins),
        downstream=MappingProxyType(downstream),
        source_record_ids=MappingProxyType(source_record_ids),
        downstream_sessions=MappingProxyType(downstream_sessions),
        pass_runs=MappingProxyType(pass_runs),
        output_integrity=MappingProxyType(output_integrity),
        review_states=MappingProxyType(review_states),
        reconciliations=MappingProxyType(reconciliations),
        package_commits=MappingProxyType(package_commits),
        submit_states=MappingProxyType(submit_states),
        handoff_states=MappingProxyType(handoff_states),
        packages=MappingProxyType(packages),
        package_payloads=MappingProxyType(package_payloads),
        db_values=db_values,
        non_source_files=non_source_files,
        source_exemptions=source_exemptions,
        domain_errors=MappingProxyType(errors),
    )
    initial_evidence = ""
    final_evidence = ""
    initial_database = ""
    final_database = ""
    if not errors:
        try:
            database_path = _database_path(settings)
            initial_evidence = _evidence_snapshot(
                context,
                chain=chain,
                historical=context.historical,
                capture=capture,
                non_source_files=non_source_files,
            )
            initial_database = _database_snapshot(
                db_values,
                _database_file_fingerprint(database_path),
            )
            final_evidence, final_database = _fresh_observation(
                context,
                database_path=database_path,
                runs=runs,
                targets=tuple(targets.values()),
                sessions=sessions,
            )
        except expected_errors as exc:
            errors["stability"] = _domain_code(exc)
    return replace(
        context,
        initial_snapshot_sha256=initial_evidence,
        final_snapshot_sha256=final_evidence,
        initial_database_snapshot_sha256=initial_database,
        final_database_snapshot_sha256=final_database,
        domain_errors=MappingProxyType(errors),
    )


def _events(context: _EvidenceContext, *, phase: str | None = None, event: str | None = None) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        record
        for record in context.runtime_records
        if (phase is None or record.get("phase") == phase)
        and (event is None or record.get("event") == event)
    )


def _record_payload(record: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = record.get("payload")
    return payload if isinstance(payload, Mapping) else MappingProxyType({})


def _child_proof_record(
    context: _EvidenceContext,
    *,
    phase: str,
    ordinal: int,
    event: str,
) -> Mapping[str, Any]:
    matches = tuple(
        record
        for record in context.child_proofs
        if record.get("phase") == phase
        and record.get("ordinal") == ordinal
        and record.get("event") == event
    )
    return matches[0] if len(matches) == 1 else MappingProxyType({})


def _child_proof_sequence_exact(context: _EvidenceContext) -> bool:
    return tuple(
        (record.get("phase"), record.get("ordinal"), record.get("event"))
        for record in context.child_proofs
    ) == _CHILD_PROOF_SEQUENCE


def _check_a01_input_identity(context: _EvidenceContext) -> CheckResult:
    check_id = "A01_INPUT_IDENTITY"
    try:
        _require_campaign_id(context.campaign_id)
        _require_campaign_fingerprint(context.campaign_fingerprint)
    except DualLiveEvaluationError:
        return _fail_result(check_id, "a01_input_identity_invalid")
    return _pass(check_id, canonical=True)


def _check_a02_index_linear_head(context: _EvidenceContext) -> CheckResult:
    check_id = "A02_INDEX_LINEAR_HEAD"
    blocked = _domain_error(context, check_id, "authority")
    if blocked:
        return blocked
    revisions = context.chain.revisions
    numbers = tuple(item.model.revision for item in revisions)
    if numbers != tuple(range(1, len(numbers) + 1)) or context.chain.head.revision != numbers[-1]:
        return _fail_result(check_id, "a02_index_linear_head_invalid")
    for prior, current in zip(revisions, revisions[1:]):
        if (
            current.model.predecessor_index_sha256 != prior.raw_sha256
            or current.model.predecessor_index_relative_path != prior.path.relative_to(
                context.chain.evidence_root
            ).as_posix()
        ):
            return _fail_result(check_id, "a02_index_predecessor_invalid")
    return _pass(check_id, revision_count=len(revisions), head_revision=numbers[-1])


def _check_a03_archive_exact(context: _EvidenceContext) -> CheckResult:
    check_id = "A03_ARCHIVE_EXACT"
    blocked = _domain_error(context, check_id, "archive") or _domain_error(
        context, check_id, "authority"
    )
    if blocked:
        return blocked
    if set(context.historical) != set(_EXPECTED_CONNECTORS):
        return _indeterminate(check_id, "a03_archive_missing")
    for entry in context.entry_refs:
        evidence = context.historical[entry.connector_key]
        if (
            evidence.raw_sha256 != entry.raw_grant_sha256
            or evidence.canonical_fingerprint != entry.canonical_grant_fingerprint
            or evidence.raw_definition_sha256 != context.campaign_ref.raw_definition_sha256
            or evidence.canonical_campaign_fingerprint != context.campaign_fingerprint
        ):
            return _fail_result(check_id, "a03_archive_binding_invalid")
    return _pass(check_id, archive_count=3)


def _check_a04_slice_cardinality(context: _EvidenceContext) -> CheckResult:
    check_id = "A04_SLICE_CARDINALITY"
    blocked = _domain_error(context, check_id, "authority")
    if blocked:
        return blocked
    if (
        context.campaign_ref is None
        or len(context.entry_refs) != 2
        or context.capture_ref is None
        or tuple(sorted(item.connector_key for item in context.entry_refs))
        != _EXPECTED_CONNECTORS
    ):
        return _fail_result(check_id, "a04_slice_cardinality_invalid")
    return _pass(check_id, definitions=1, grants=2, captures=1)


def _slice_sets(model: Any) -> tuple[set[tuple[str, str]], set[tuple[str, str, str]], set[tuple[str, str]]]:
    return (
        {(item.campaign_id, item.campaign_fingerprint) for item in model.campaigns},
        {
            (item.campaign_id, item.campaign_fingerprint, item.connector_key)
            for item in model.entries
        },
        {(item.campaign_id, item.campaign_fingerprint) for item in model.log_captures},
    )


def _check_a05_selected_union(context: _EvidenceContext) -> CheckResult:
    check_id = "A05_SELECTED_UNION"
    blocked = _domain_error(context, check_id, "authority")
    if blocked:
        return blocked
    revisions = context.chain.revisions
    prior: tuple[
        set[tuple[str, str]],
        set[tuple[str, str, str]],
        set[tuple[str, str]],
    ] = (set(), set(), set())
    for revision in revisions:
        current = _slice_sets(revision.model)
        additions = (
            current[0] - prior[0],
            current[1] - prior[1],
            current[2] - prior[2],
        )
        if any(not prior[index].issubset(current[index]) for index in range(3)):
            return _fail_result(check_id, "a05_selected_union_dropped_history")
        if len(additions[0]) != 1 or len(additions[1]) != 2 or len(additions[2]) != 1:
            return _fail_result(check_id, "a05_selected_union_partial_slice")
        introduced = next(iter(additions[0]))
        if additions[2] != {introduced} or {
            (campaign_id, fingerprint)
            for campaign_id, fingerprint, _connector in additions[1]
        } != {introduced}:
            return _fail_result(check_id, "a05_selected_union_cross_campaign")
        prior = current
    return _pass(
        check_id,
        retained_campaign_count=len(prior[0]),
        selected_definitions=1,
        selected_grants=2,
        selected_captures=1,
    )


def _introduction(context: _EvidenceContext) -> tuple[int, str]:
    for revision in context.chain.revisions:
        campaign_keys = {
            (item.campaign_id, item.campaign_fingerprint)
            for item in revision.model.campaigns
        }
        entry_keys = {
            (item.campaign_id, item.campaign_fingerprint, item.connector_key)
            for item in revision.model.entries
        }
        capture_keys = {
            (item.campaign_id, item.campaign_fingerprint)
            for item in revision.model.log_captures
        }
        key = (context.campaign_id, context.campaign_fingerprint)
        if (
            key in campaign_keys
            and capture_keys.issuperset({key})
            and {
                (context.campaign_id, context.campaign_fingerprint, connector)
                for connector in _EXPECTED_CONNECTORS
            }.issubset(entry_keys)
        ):
            return revision.model.revision, revision.raw_sha256
    raise DualLiveEvaluationError("dual_live_introduction_missing")


def _check_a06_introduction_parity(context: _EvidenceContext) -> CheckResult:
    check_id = "A06_INTRODUCTION_PARITY"
    blocked = _domain_error(context, check_id, "authority") or _domain_error(
        context, check_id, "capture"
    )
    if blocked:
        return blocked
    revision, digest = _introduction(context)
    pairs = {(context.seal.campaign_introduction_index_revision, context.seal.campaign_introduction_index_sha256)}
    pairs.update(
        (
            envelope.get("campaign_introduction_index_revision"),
            envelope.get("campaign_introduction_index_sha256"),
        )
        for envelope in context.envelopes.values()
    )
    pairs.update(
        (item.introduction_index_revision, item.introduction_index_sha256)
        for item in context.historical.values()
    )
    if pairs != {(revision, digest)}:
        return _fail_result(check_id, "a06_introduction_binding_invalid")
    return _pass(check_id, introduction_revision=revision, introduction_sha256=digest)


def _parent_arming_id(
    *,
    connector_key: str,
    campaign_id: str,
    grant_sha256: str,
    arming_nonce: UUID,
) -> str:
    preimage = (
        "project6:parent-arming:"
        f"{connector_key}:{campaign_id}:{grant_sha256}:{arming_nonce}"
    )
    return str(uuid5(NAMESPACE_URL, preimage))


def _check_a07_marker_one_use(context: _EvidenceContext) -> CheckResult:
    check_id = "A07_MARKER_ONE_USE"
    blocked = _domain_error(context, check_id, "archive") or _domain_error(
        context, check_id, "ledger"
    )
    if blocked:
        return blocked
    for connector_key, evidence in context.historical.items():
        marker = evidence.marker_model
        expected_run = _parent_arming_id(
            connector_key=connector_key,
            campaign_id=context.campaign_id,
            grant_sha256=evidence.raw_sha256,
            arming_nonce=evidence.model.arming_nonce,
        )
        if (
            marker.connector_run_id != expected_run
            or marker.max_armings != 1
            or marker.arming_nonce != evidence.model.arming_nonce
            or context.run_by_connector[connector_key].connector_run_id != expected_run
        ):
            return _fail_result(check_id, "a07_marker_binding_invalid")
    return _pass(check_id, marker_count=2)


def _parse_time(value: Any) -> Any:
    from datetime import datetime, timezone

    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    if not isinstance(value, str):
        raise ValueError("time")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("time")
    return parsed.astimezone(timezone.utc)


def _check_a08_original_windows(context: _EvidenceContext) -> CheckResult:
    check_id = "A08_ORIGINAL_WINDOWS"
    blocked = _domain_error(context, check_id, "ledger") or _domain_error(
        context, check_id, "archive"
    )
    if blocked:
        return blocked
    campaign = next(iter(context.historical.values())).definition_model
    for connector_key, ledger in context.ledgers.items():
        grant = context.historical[connector_key].model
        for entry in ledger.entries:
            for field_name in ("reserved_at", "send_started_at"):
                raw = entry.get(field_name)
                if raw is None:
                    continue
                instant = _parse_time(raw)
                if not (
                    campaign.not_before <= instant < campaign.expires_at
                    and grant.issued_at <= instant < grant.expires_at
                ):
                    return _fail_result(check_id, "a08_original_window_violation")
    return _pass(check_id, half_open=True)


def _check_a09_code_campaign_fingerprints(context: _EvidenceContext) -> CheckResult:
    check_id = "A09_CODE_CAMPAIGN_FINGERPRINTS"
    blocked = _domain_error(context, check_id, "authority") or _domain_error(
        context, check_id, "capture"
    )
    if blocked:
        return blocked
    code_revision = context.campaign_ref.code_revision
    values = {
        context.campaign_ref.campaign_fingerprint,
        context.capture_ref.campaign_fingerprint,
        context.manifest.campaign_fingerprint,
        context.seal.campaign_fingerprint,
        *(str(item.canonical_campaign_fingerprint) for item in context.historical.values()),
        *(str(item.get("campaign_fingerprint")) for item in context.envelopes.values()),
    }
    codes = {
        code_revision,
        context.capture_ref.code_revision,
        context.manifest.code_revision,
        context.seal.code_revision,
        *(str(item.model.code_revision) for item in context.historical.values()),
    }
    if values != {context.campaign_fingerprint} or codes != {code_revision} or not _LOWERCASE_CODE_REVISION.fullmatch(code_revision):
        return _fail_result(check_id, "a09_cross_domain_fingerprint_invalid")
    return _pass(check_id, code_revision=code_revision, campaign_fingerprint=context.campaign_fingerprint)


def _check_a10_proof_class(context: _EvidenceContext) -> CheckResult:
    check_id = "A10_PROOF_CLASS"
    blocked = _domain_error(context, check_id, "origin")
    if blocked:
        return blocked
    if set(context.origins) != set(_EXPECTED_CONNECTORS) or any(
        receipt.get("proof_class") != "fresh_live" for receipt in context.origins.values()
    ):
        return _fail_result(check_id, "a10_rederived_proof_class_invalid")
    return _pass(check_id, proof_class="fresh_live", connector_count=2)


def _check_r01_capture_membership(context: _EvidenceContext) -> CheckResult:
    check_id = "R01_CAPTURE_MEMBERSHIP"
    blocked = _domain_error(context, check_id, "capture")
    if blocked:
        return blocked
    suffixes = tuple(Path(str(path)).name for path in context.capture.stream_bytes)
    if suffixes != _EXPECTED_STREAM_FILES or len(context.capture.stable_snapshot) != 6:
        return _fail_result(check_id, "r01_capture_membership_invalid")
    return _pass(check_id, stream_count=4, protected_object_count=6)


def _independent_capture_error(
    context: _EvidenceContext,
    check_id: str,
    *components: str,
) -> CheckResult | None:
    capture = context.independent_capture
    if capture is None:
        return _domain_error(context, check_id, "capture")
    for component in components:
        reason_code = capture.errors.get(component)
        if reason_code is not None:
            return _indeterminate(
                check_id,
                f"{check_id.lower()}_evidence_unavailable",
                domain="capture",
                reason_code=reason_code,
            )
    return None


def _check_r02_manifest_file_hashes(context: _EvidenceContext) -> CheckResult:
    check_id = "R02_MANIFEST_FILE_HASHES"
    independent = context.independent_capture
    if independent is None:
        blocked = _domain_error(context, check_id, "capture")
        if blocked:
            return blocked
        for item in context.manifest.files:
            payload = _stream_bytes(
                context.capture,
                Path(item.relative_path).name,
            )
            if (
                item.byte_count != len(payload)
                or item.sha256 != hashlib.sha256(payload).hexdigest()
            ):
                return _fail_result(
                    check_id,
                    "r02_manifest_file_hash_invalid",
                )
        return _pass(
            check_id,
            file_count=4,
            file_set_hash=context.capture.file_set_hash,
        )
    blocked = _independent_capture_error(
        context,
        check_id,
        "collection",
        "paths",
        "manifest",
        "streams",
    )
    if blocked:
        return blocked
    if (
        context.manifest is not None
        and context.manifest.files != independent.manifest.files
    ):
        return _fail_result(check_id, "r02_manifest_file_hash_invalid")
    for item in independent.manifest.files:
        independent_payload = independent.stream_bytes.get(
            item.relative_path
        )
        if (
            independent_payload is None
            or item.byte_count != len(independent_payload)
            or item.sha256
            != hashlib.sha256(independent_payload).hexdigest()
        ):
            return _fail_result(check_id, "r02_manifest_file_hash_invalid")
    return _pass(
        check_id,
        file_count=len(independent.manifest.files),
        file_set_hash=independent.file_set_hash,
    )


def _check_r03_seal_parity(context: _EvidenceContext) -> CheckResult:
    check_id = "R03_SEAL_PARITY"
    independent = context.independent_capture
    if independent is None:
        blocked = _domain_error(context, check_id, "capture")
        if blocked:
            return blocked
        if (
            context.seal.manifest_sha256
            != context.capture.manifest_sha256
            or context.seal.file_set_hash != context.capture.file_set_hash
            or context.capture.seal_sha256
            != hashlib.sha256(context.capture.seal_bytes).hexdigest()
        ):
            return _fail_result(check_id, "r03_seal_parity_invalid")
        return _pass(
            check_id,
            seal_sha256=context.capture.seal_sha256,
        )
    blocked = _independent_capture_error(
        context,
        check_id,
        "collection",
        "paths",
        "manifest",
        "seal",
    )
    if blocked:
        return blocked
    if (
        independent.seal.manifest_sha256 != independent.manifest_sha256
        or independent.seal.file_set_hash != independent.file_set_hash
        or independent.seal_sha256
        != hashlib.sha256(independent.seal_bytes).hexdigest()
        or (
            context.capture is not None
            and (
                context.capture.manifest_sha256
                != independent.manifest_sha256
                or context.capture.file_set_hash != independent.file_set_hash
                or context.capture.seal_sha256 != independent.seal_sha256
            )
        )
    ):
        return _fail_result(check_id, "r03_seal_parity_invalid")
    return _pass(check_id, seal_sha256=independent.seal_sha256)


def _seal_event_metrics(
    context: _EvidenceContext,
    independent: _IndependentCaptureEvidence,
) -> dict[str, Any]:
    seal = independent.seal
    return {
        "schema_id": (
            "project6.connector_campaign_log_seal_event_metrics.v1"
        ),
        "campaign_id": seal.campaign_id,
        "campaign_fingerprint": seal.campaign_fingerprint,
        "campaign_definition_sha256": seal.campaign_definition_sha256,
        "code_revision": seal.code_revision,
        "campaign_introduction_index_revision": (
            seal.campaign_introduction_index_revision
        ),
        "campaign_introduction_index_sha256": (
            seal.campaign_introduction_index_sha256
        ),
        "manifest_relative_path": seal.manifest_relative_path,
        "manifest_sha256": seal.manifest_sha256,
        "file_set_hash": seal.file_set_hash,
        "seal_relative_path": context.capture_ref.seal_relative_path,
        "seal_sha256": independent.seal_sha256,
        "connector_run_ids": list(seal.connector_run_ids),
        "sealed_at": _parse_time(seal.sealed_at).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        ),
    }


def _check_r04_seal_event_parity(context: _EvidenceContext) -> CheckResult:
    check_id = "R04_SEAL_EVENT_PARITY"
    independent = context.independent_capture
    if independent is None:
        blocked = _domain_error(
            context,
            check_id,
            "capture",
        ) or _domain_error(context, check_id, "ledger")
        if blocked:
            return blocked
        if (
            tuple(context.seal.connector_run_ids)
            != tuple(sorted(run.connector_run_id for run in context.runs))
            or len(context.capture.seal_event_ids) != len(context.runs)
            or len(set(context.capture.seal_event_ids)) != len(context.runs)
        ):
            return _fail_result(check_id, "r04_seal_event_parity_invalid")
        return _pass(
            check_id,
            extant_run_count=len(context.runs),
            seal_event_count=len(context.capture.seal_event_ids),
        )
    blocked = _independent_capture_error(
        context,
        check_id,
        "collection",
        "paths",
        "seal",
        "events",
    )
    if blocked:
        return blocked
    run_ids = tuple(run.connector_run_id for run in independent.runs)
    events = independent.seal_events
    if (
        len(run_ids) != 2
        or tuple(independent.seal.connector_run_ids) != run_ids
        or len(events) != 2
        or tuple(sorted(event.connector_run_id for event in events))
        != run_ids
        or len({event.connector_run_event_id for event in events}) != 2
        or (
            context.capture is not None
            and tuple(sorted(context.capture.seal_event_ids))
            != tuple(sorted(event.connector_run_event_id for event in events))
        )
    ):
        return _fail_result(check_id, "r04_seal_event_parity_invalid")
    run_by_id = {run.connector_run_id: run for run in independent.runs}
    expected_metrics = _seal_event_metrics(context, independent)
    sealed_at = _parse_time(independent.seal.sealed_at)
    for event in events:
        run = run_by_id[event.connector_run_id]
        expected_event_id = str(
            uuid5(
                NAMESPACE_URL,
                "project6:connector-egress:"
                f"{run.connector_run_id}:campaign_log_capture_sealed:0",
            )
        )
        if (
            event.connector_run_event_id != expected_event_id
            or event.connector_run_target_id is not None
            or event.phase != "evidence"
            or event.stage != "campaign_log_capture"
            or event.event_type != "campaign_log_capture_sealed"
            or event.status_before != run.status
            or event.status_after != run.status
            or event.reason_code != "protected_log_capture_sealed"
            or event.error_class is not None
            or event.message is not None
            or event.metrics_bytes
            != _json_observation_bytes(expected_metrics)
            or _parse_time(event.created_at) != sealed_at
        ):
            return _fail_result(check_id, "r04_seal_event_parity_invalid")
    return _pass(
        check_id,
        extant_run_count=len(run_ids),
        seal_event_count=len(events),
    )


def _runtime_start_contract_evidence(
    context: _EvidenceContext,
) -> tuple[str, int, int] | None:
    starts = _events(context, phase="wrapper", event="runtime_start")
    if len(starts) != 1:
        return None
    payload = _record_payload(starts[0])
    if set(payload) != set(_RUNTIME_START_PAYLOAD_KEYS):
        return None
    if (
        not isinstance(payload["code_revision"], str)
        or not _LOWERCASE_CODE_REVISION.fullmatch(payload["code_revision"])
        or any(
            not isinstance(payload[field_name], str)
            or not _LOWERCASE_SHA256.fullmatch(payload[field_name])
            for field_name in (
                "wrapper_image_sha256",
                "interpreter_image_sha256",
                "dependency_set_sha256",
                "mutex_identity_sha256",
            )
        )
    ):
        return None

    contract = payload["phase_timeout_contract"]
    if not isinstance(contract, Mapping) or set(contract) != _PHASE_TIMEOUT_CONTRACT_KEYS:
        return None
    if contract["schema_id"] != _PHASE_TIMEOUT_SCHEMA_ID:
        return None
    scalar_fields = (
        "phase_a_timeout_ms",
        "phase_b_timeout_ms",
        "fixed_non_egress_overhead_ms",
        "counter_ack_timeout_ms",
    )
    if any(type(contract[field_name]) is not int for field_name in scalar_fields):
        return None
    phase_a_timeout = contract["phase_a_timeout_ms"]
    phase_b_timeout = contract["phase_b_timeout_ms"]
    fixed_overhead = contract["fixed_non_egress_overhead_ms"]
    counter_ack = contract["counter_ack_timeout_ms"]
    if (
        fixed_overhead != _FIXED_NON_EGRESS_OVERHEAD_MILLISECONDS
        or counter_ack != _COUNTER_ACK_TIMEOUT_MILLISECONDS
        or phase_b_timeout != _PHASE_B_TIMEOUT_MILLISECONDS
    ):
        return None

    grants = contract["connector_grants"]
    if (
        not isinstance(grants, (list, tuple))
        or len(grants) != len(_EXPECTED_PHASE_TIMEOUT_GRANTS)
        or set(context.historical) != set(_EXPECTED_CONNECTORS)
    ):
        return None
    derived_phase_a_timeout = fixed_overhead
    for grant, expected in zip(
        grants,
        _EXPECTED_PHASE_TIMEOUT_GRANTS,
        strict=True,
    ):
        if not isinstance(grant, Mapping) or set(grant) != _PHASE_TIMEOUT_GRANT_KEYS:
            return None
        connector_key, requests, request_timeout, interval = expected
        grant_values = (
            grant["connector_key"],
            grant["max_physical_requests"],
            grant["request_timeout_seconds"],
            grant["min_request_interval_ms"],
        )
        if (
            grant_values != expected
            or any(type(value) is not int for value in grant_values[1:])
        ):
            return None
        try:
            model = context.historical[connector_key].model
            model_values = (
                model.max_physical_requests,
                model.request_timeout_seconds,
                model.min_request_interval_ms,
            )
        except (AttributeError, KeyError, TypeError):
            return None
        if (
            model_values != expected[1:]
            or any(type(value) is not int for value in model_values)
        ):
            return None
        derived_phase_a_timeout += requests * (
            request_timeout * 1000 + counter_ack
        )
        derived_phase_a_timeout += (requests - 1) * interval

    if (
        phase_a_timeout != derived_phase_a_timeout
        or phase_a_timeout != _PHASE_A_TIMEOUT_MILLISECONDS
    ):
        return None
    return payload["dependency_set_sha256"], phase_a_timeout, phase_b_timeout


def _check_r05_runtime_chain(context: _EvidenceContext) -> CheckResult:
    check_id = "R05_RUNTIME_CHAIN"
    blocked = _domain_error(context, check_id, "runtime") or _domain_error(
        context,
        check_id,
        "archive",
    )
    if blocked:
        return blocked
    contract_evidence = _runtime_start_contract_evidence(context)
    if (
        not context.runtime_records
        or tuple(record["ordinal"] for record in context.runtime_records)
        != tuple(range(1, len(context.runtime_records) + 1))
        or contract_evidence is None
    ):
        return _fail_result(check_id, "r05_runtime_chain_invalid")
    dependency_set_sha256, phase_a_timeout_ms, phase_b_timeout_ms = (
        contract_evidence
    )
    return _pass(
        check_id,
        record_count=len(context.runtime_records),
        terminal_record_sha256=context.runtime_records[-1]["record_sha256"],
        dependency_set_sha256=dependency_set_sha256,
        phase_a_timeout_ms=phase_a_timeout_ms,
        phase_b_timeout_ms=phase_b_timeout_ms,
    )


def _check_r06_startup_logger_census(context: _EvidenceContext) -> CheckResult:
    check_id = "R06_STARTUP_LOGGER_CENSUS"
    blocked = _domain_error(context, check_id, "runtime")
    if blocked:
        return blocked
    records = tuple(record for record in _events(context, event="logger_census") if _record_payload(record).get("census_point") == "pre_activity")
    if tuple(record.get("phase") for record in records) != ("A", "B") or any(_record_payload(record).get("topology_matches_initial") is not True for record in records):
        return _fail_result(check_id, "r06_startup_logger_census_invalid")
    return _pass(check_id, census_count=2)


def _check_r07_exit_logger_census(context: _EvidenceContext) -> CheckResult:
    check_id = "R07_EXIT_LOGGER_CENSUS"
    blocked = _domain_error(context, check_id, "runtime")
    if blocked:
        return blocked
    for phase in ("A", "B"):
        records = _events(context, phase=phase, event="logger_census")
        if len(records) != 2:
            return _fail_result(check_id, "r07_exit_logger_census_missing")
        if {_record_payload(record).get("topology_sha256") for record in records}.__len__() != 1 or _record_payload(records[-1]).get("topology_matches_initial") is not True:
            return _fail_result(check_id, "r07_exit_logger_census_changed")
    return _pass(check_id, unchanged=True)


def _check_r08_phase_a_identity(context: _EvidenceContext) -> CheckResult:
    check_id = "R08_PHASE_A_IDENTITY"
    blocked = _domain_error(context, check_id, "runtime")
    if blocked:
        return blocked
    starts = _events(context, phase="A", event="phase_child_start")
    boots = {record.get("process_boot_id") for record in starts}
    if len(starts) != 1 or len(boots) != 1 or None in boots:
        return _fail_result(check_id, "r08_phase_a_identity_invalid")
    return _pass(check_id, process_boot_id=next(iter(boots)))


def _check_r09_phase_a_job_zero(context: _EvidenceContext) -> CheckResult:
    check_id = "R09_PHASE_A_JOB_ZERO"
    blocked = _domain_error(context, check_id, "runtime")
    if blocked:
        return blocked
    records = _events(context, phase="A", event="job_zero")
    if len(records) != 1 or _record_payload(records[0]).get("active_process_count") != 0:
        return _fail_result(check_id, "r09_phase_a_job_not_zero")
    return _pass(check_id, active_process_count=0)


def _socket_zero(payload: Mapping[str, Any]) -> bool:
    tcp4 = payload.get("tcp4_state_counts")
    tcp6 = payload.get("tcp6_state_counts")
    if not isinstance(tcp4, Mapping) or not isinstance(tcp6, Mapping):
        return False
    counts = (tcp4, tcp6)
    return bool(
        payload.get("stable") is True
        and all(set(value) == set(_WINDOWS_MIB_TCP_STATES) for value in counts)
        and all(
            count == 0
            for value in counts
            for state, count in value.items()
            if state != "MIB_TCP_STATE_TIME_WAIT"
        )
        and payload.get("udp4_count") == 0
        and payload.get("udp6_count") == 0
    )


def _check_r10_phase_a_socket_quiescence(context: _EvidenceContext) -> CheckResult:
    check_id = "R10_PHASE_A_SOCKET_QUIESCENCE"
    blocked = _domain_error(context, check_id, "runtime")
    if blocked:
        return blocked
    records = _events(context, phase="A", event="socket_census")
    if len(records) != 1 or not _socket_zero(_record_payload(records[0])):
        return _fail_result(check_id, "r10_phase_a_socket_not_quiescent")
    return _pass(check_id, prohibited_endpoint_count=0)


def _check_r11_authority_cleared(context: _EvidenceContext) -> CheckResult:
    check_id = "R11_AUTHORITY_CLEARED"
    blocked = _domain_error(context, check_id, "runtime")
    if blocked:
        return blocked
    records = _events(context, phase="A", event="authority_cleared")
    if len(records) != 1:
        return _fail_result(check_id, "r11_authority_not_cleared")
    payload = _record_payload(records[0])
    if (
        set(payload) != {"authority_posture_sha256", "all_required_absent"}
        or payload.get("all_required_absent") is not True
        or payload.get("authority_posture_sha256")
        != _AUTHORITY_CLEARED_POSTURE_SHA256
    ):
        return _fail_result(check_id, "r11_authority_not_cleared")
    return _pass(
        check_id,
        all_required_absent=True,
        authority_posture_sha256=_AUTHORITY_CLEARED_POSTURE_SHA256,
    )


def _check_r12_phase_b_guards(context: _EvidenceContext) -> CheckResult:
    check_id = "R12_PHASE_B_GUARDS"
    blocked = _domain_error(context, check_id, "runtime")
    if blocked:
        return blocked
    censuses = _events(context, phase="B", event="logger_census")
    go = _events(context, phase="B", event="phase_go")
    pre_go_proof = _child_proof_record(
        context,
        phase="B",
        ordinal=1,
        event="guard",
    )
    exit_proof = _child_proof_record(
        context,
        phase="B",
        ordinal=3,
        event="guard",
    )
    guard_payloads = tuple(
        _record_payload(record) for record in (pre_go_proof, exit_proof)
    )
    if (
        len(censuses) != 2
        or len(go) != 1
        or _record_payload(censuses[0]).get("guard_state") != "B_CENSUS_OK"
        or _record_payload(go[0]).get("prior_state") != "B_CENSUS_OK"
        or tuple(payload.get("proof_point") for payload in guard_payloads)
        != ("pre_go", "exit")
        or any(
            tuple(payload.get("denied_routes") or ())
            != _CHILD_PROOF_DENIED_ROUTES
            or payload.get("network_enable_attempt_count") != 0
            or payload.get("original_implementation_call_count") != 0
            or payload.get("proof_scope") != "production"
            for payload in guard_payloads
        )
    ):
        return _fail_result(check_id, "r12_phase_b_guards_unproven")
    return _pass(
        check_id,
        pre_import_guarded=True,
        denied_route_count=len(_CHILD_PROOF_DENIED_ROUTES),
        guard_proof_count=2,
    )


def _check_r13_phase_b_job_zero(context: _EvidenceContext) -> CheckResult:
    check_id = "R13_PHASE_B_JOB_ZERO"
    blocked = _domain_error(context, check_id, "runtime")
    if blocked:
        return blocked
    jobs = _events(context, phase="B", event="job_zero")
    sockets = _events(context, phase="B", event="socket_census")
    if (
        len(jobs) != 1
        or _record_payload(jobs[0]).get("active_process_count") != 0
        or len(sockets) != 1
        or not _socket_zero(_record_payload(sockets[0]))
    ):
        return _fail_result(check_id, "r13_phase_b_not_quiescent")
    return _pass(check_id, active_process_count=0, prohibited_endpoint_count=0)


def _check_r14_runtime_terminal(context: _EvidenceContext) -> CheckResult:
    check_id = "R14_RUNTIME_TERMINAL"
    blocked = _domain_error(context, check_id, "runtime")
    if blocked:
        return blocked
    terminals = _events(context, phase="wrapper", event="runtime_complete")
    phases = _events(context, event="phase_complete")
    phase_hashes = {
        str(record.get("phase")): record.get("record_sha256") for record in phases
    }
    terminal_payload = _record_payload(terminals[0]) if len(terminals) == 1 else {}
    proof_boots = {
        phase: {
            str(record.get("process_boot_id"))
            for record in context.child_proofs
            if record.get("phase") == phase
        }
        for phase in ("A", "B")
    }
    runtime_boots = {
        phase: {
            str(record.get("process_boot_id"))
            for record in _events(context, phase=phase, event="phase_child_start")
        }
        for phase in ("A", "B")
    }
    if (
        len(terminals) != 1
        or tuple(record.get("phase") for record in phases) != ("A", "B")
        or any(
            _record_payload(record).get("terminal_state") != "completed"
            for record in (*phases, *terminals)
        )
        or terminal_payload.get("phase_a_result_sha256") != phase_hashes.get("A")
        or terminal_payload.get("phase_b_result_sha256") != phase_hashes.get("B")
        or not _child_proof_sequence_exact(context)
        or any(
            len(proof_boots[phase]) != 1
            or proof_boots[phase] != runtime_boots[phase]
            for phase in ("A", "B")
        )
        or context.manifest is None
        or context.manifest.runtime_stopped_at < context.manifest.runtime_started_at
    ):
        return _fail_result(check_id, "r14_runtime_terminal_invalid")
    return _pass(
        check_id,
        terminal_state="completed",
        child_proof_count=len(context.child_proofs),
    )


def _check_r15_wrapper_network_inert(context: _EvidenceContext) -> CheckResult:
    check_id = "R15_WRAPPER_NETWORK_INERT"
    blocked = _domain_error(context, check_id, "runtime")
    if blocked:
        return blocked
    wrapper_events = {record.get("event") for record in _events(context, phase="wrapper")}
    allowed = {"runtime_start", "runtime_complete", "stop_latched"}
    phase_a_proof = _child_proof_record(
        context,
        phase="A",
        ordinal=1,
        event="acquisition_boundary",
    )
    phase_a_boot = phase_a_proof.get("process_boot_id")
    guard_payloads = tuple(
        _record_payload(
            _child_proof_record(
                context,
                phase="B",
                ordinal=ordinal,
                event="guard",
            )
        )
        for ordinal in (1, 3)
    )
    if not wrapper_events.issubset(allowed):
        return _fail_result(check_id, "r15_wrapper_network_role_invalid")
    if (
        phase_a_boot is None
        or not context.counter_records
        or any(
            record.get("process_boot_id") != phase_a_boot
            for record in context.counter_records
        )
        or any(
            payload.get("network_enable_attempt_count") != 0
            or payload.get("original_implementation_call_count") != 0
            for payload in guard_payloads
        )
    ):
        return _fail_result(check_id, "r15_counter_wrapper_identity_invalid")
    return _pass(
        check_id,
        wrapper_send_records=0,
        phase_b_network_enable_attempt_count=0,
    )


def _check_r16_phase_a_raw_only(context: _EvidenceContext) -> CheckResult:
    check_id = "R16_PHASE_A_RAW_ONLY"
    blocked = _domain_error(context, check_id, "runtime")
    if blocked:
        return blocked
    prohibited = {"layer3", "review", "package", "submit", "handoff", "seal"}
    proof = _child_proof_record(
        context,
        phase="A",
        ordinal=1,
        event="acquisition_boundary",
    )
    payload = _record_payload(proof)
    acquisitions = payload.get("connector_acquisitions")
    if any(
        any(token in str(record.get("event", "")).casefold() for token in prohibited)
        for record in _events(context, phase="A")
    ) or (
        payload.get("proof_scope") != "production"
        or payload.get("downstream_action_count") != 0
        or not isinstance(acquisitions, (list, tuple))
        or tuple(
            item.get("connector_key")
            for item in acquisitions
            if isinstance(item, Mapping)
        )
        != _EXPECTED_CONNECTORS
    ):
        return _fail_result(check_id, "r16_phase_a_downstream_action")
    return _pass(
        check_id,
        acquisition_only=True,
        connector_acquisition_count=2,
        downstream_action_count=0,
    )


def _r17_expected_source_binding(
    context: _EvidenceContext,
    connector_key: str,
) -> dict[str, Any] | None:
    target = context.targets.get(connector_key)
    origin = context.origins.get(connector_key)
    session = context.downstream_sessions.get(connector_key)
    pass_run = context.pass_runs.get(connector_key)
    review = context.review_states.get(connector_key)
    reconciliation = context.reconciliations.get(connector_key)
    commit = context.package_commits.get(connector_key)
    submit = context.submit_states.get(connector_key)
    handoff = context.handoff_states.get(connector_key)
    package_vectors = _package_vectors(context.packages.get(connector_key, ()))
    if (
        target is None
        or origin is None
        or session is None
        or pass_run is None
        or review is None
        or reconciliation is None
        or commit is None
        or submit is None
        or handoff is None
        or package_vectors is None
    ):
        return None
    operator_context = getattr(session, "operator_context_json", None)
    decision_manifest = (
        operator_context.get("layer3_gate_b_decision_manifest_v1")
        if isinstance(operator_context, Mapping)
        else None
    )
    decision_items = (
        decision_manifest.get("items")
        if isinstance(decision_manifest, Mapping)
        else None
    )
    summary = getattr(pass_run, "summary_json", None)
    execution_start = (
        summary.get("analysis_execution_start")
        if isinstance(summary, Mapping)
        else None
    )
    envelope = handoff.get("handoff_export_envelope")
    source_shape = _PHASE_B_SOURCE_SHAPES.get(connector_key)
    if (
        not isinstance(decision_items, list)
        or len(decision_items) != 1
        or not isinstance(decision_items[0], Mapping)
        or decision_items[0].get("decision") != "approved"
        or decision_items[0].get("source_class") != source_shape
        or not isinstance(execution_start, Mapping)
        or not isinstance(envelope, Mapping)
        or handoff.get("source_shape") != source_shape
        or envelope.get("source_shape") != source_shape
    ):
        return None
    package_ids, package_kinds, _payload_refs, payload_hashes = package_vectors
    return {
        "analysis_plan_id": str(pass_run.analysis_plan_id),
        "analysis_run_id": execution_start.get("analysis_run_id"),
        "candidate_id": decision_items[0].get("candidate_id"),
        "connector_key": connector_key,
        "connector_origin_receipt_hash": origin.get("receipt_hash"),
        "connector_run_id": str(target.connector_run_id),
        "connector_run_target_id": str(target.connector_run_target_id),
        "construction_basis_hash": commit.get("construction_basis_hash"),
        "handoff_export_envelope_ref": envelope.get("envelope_ref"),
        "output_package_ids": package_ids,
        "package_kinds": package_kinds,
        "package_review_preview_hash": commit.get(
            "package_review_preview_hash"
        ),
        "package_review_submit_record_ref": submit.get("submit_record_ref"),
        "pass_run_id": str(pass_run.pass_run_id),
        "payload_hashes": payload_hashes,
        "prepare_record_ref": handoff.get("prepare_record_ref"),
        "reconciliation_record_id": str(
            reconciliation.reconciliation_record_id
        ),
        "result_review_record_ref": review.get("review_record_ref"),
        "session_id": str(session.session_id),
        "source_shape": source_shape,
        "source_record_id": context.source_record_ids.get(connector_key),
    }


def _check_r17_phase_b_strict_flow(context: _EvidenceContext) -> CheckResult:
    check_id = "R17_PHASE_B_STRICT_FLOW"
    blocked = next(
        (
            result
            for domain in (
                "runtime",
                "downstream",
                "phase_b_sources",
                "execution",
                "review",
                "package_set",
                "submit",
                "handoff",
            )
            if (result := _domain_error(context, check_id, domain)) is not None
        ),
        None,
    )
    if blocked:
        return blocked
    phases = _events(context, event="phase_complete")
    proof = _child_proof_record(
        context,
        phase="B",
        ordinal=2,
        event="downstream_chain",
    )
    payload = _record_payload(proof)
    bindings = payload.get("source_bindings")
    action_receipts = payload.get("action_receipts")
    boundary_maps = (
        context.targets,
        context.origins,
        context.source_record_ids,
        context.downstream_sessions,
        context.pass_runs,
        context.review_states,
        context.reconciliations,
        context.packages,
        context.package_commits,
        context.submit_states,
        context.handoff_states,
    )
    if tuple(record.get("phase") for record in phases) != ("A", "B"):
        return _fail_result(check_id, "r17_phase_b_flow_invalid")
    if (
        payload.get("proof_scope") != "production"
        or tuple(payload.get("downstream_actions") or ())
        != _PHASE_B_DOWNSTREAM_ACTIONS
        or payload.get("terminal_boundary") != "handoff_prepared"
        or not isinstance(action_receipts, (list, tuple))
        or len(action_receipts) != len(_PHASE_B_DOWNSTREAM_ACTIONS)
        or tuple(
            receipt.get("action")
            for receipt in action_receipts
            if isinstance(receipt, Mapping)
        )
        != _PHASE_B_DOWNSTREAM_ACTIONS
        or not isinstance(bindings, (list, tuple))
        or len(bindings) != 2
        or set(context.source_record_ids) != set(_EXPECTED_CONNECTORS)
    ):
        return _fail_result(check_id, "r17_phase_b_flow_invalid")
    if any(set(mapping) != set(_EXPECTED_CONNECTORS) for mapping in boundary_maps):
        return _indeterminate(check_id, "r17_phase_b_flow_missing")
    for binding, connector_key in zip(bindings, _EXPECTED_CONNECTORS, strict=True):
        expected = _r17_expected_source_binding(context, connector_key)
        if (
            not isinstance(binding, Mapping)
            or expected is None
            or _thaw(binding) != expected
        ):
            return _fail_result(check_id, "r17_phase_b_flow_invalid")
    return _pass(
        check_id,
        action_receipt_count=len(_PHASE_B_DOWNSTREAM_ACTIONS),
        boundary_count=len(boundary_maps),
        connector_count=2,
        downstream_action_count=len(_PHASE_B_DOWNSTREAM_ACTIONS),
        source_binding_count=2,
        terminal_boundary="handoff_prepared",
    )


def _check_r18_phase_a_terminal_once(context: _EvidenceContext) -> CheckResult:
    check_id = "R18_PHASE_A_TERMINAL_ONCE"
    blocked = (
        _domain_error(context, check_id, "runtime")
        or _domain_error(context, check_id, "ledger")
        or _domain_error(context, check_id, "origin")
    )
    if blocked:
        return blocked
    proof = _child_proof_record(
        context,
        phase="A",
        ordinal=1,
        event="acquisition_boundary",
    )
    payload = _record_payload(proof)
    acquisitions = payload.get("connector_acquisitions")
    if (
        payload.get("proof_scope") != "production"
        or payload.get("downstream_action_count") != 0
        or not isinstance(acquisitions, (list, tuple))
        or len(acquisitions) != 2
    ):
        return _fail_result(check_id, "r18_phase_a_terminalization_invalid")
    if any(not ledger.eligible for ledger in context.ledgers.values()):
        return _fail_result(check_id, "r18_phase_a_terminalization_invalid")
    for acquisition, connector_key in zip(
        acquisitions,
        _EXPECTED_CONNECTORS,
        strict=True,
    ):
        receipt = context.origins.get(connector_key)
        target = context.targets.get(connector_key)
        run = context.run_by_connector.get(connector_key)
        ledger = context.ledgers.get(connector_key)
        if (
            not isinstance(acquisition, Mapping)
            or receipt is None
            or target is None
            or run is None
            or ledger is None
            or acquisition.get("connector_key") != connector_key
            or tuple(acquisition.get("action_codes") or ())
            != (
                "derived_arming",
                "raw_acquisition",
                "terminal_transition",
            )
            or acquisition.get("connector_run_id")
            != str(run.connector_run_id)
            or acquisition.get("connector_run_target_id")
            != str(target.connector_run_target_id)
            or acquisition.get("ledger_terminal_hash")
            != str(ledger.ledger_terminal_hash)
            or acquisition.get("raw_content_sha256")
            != str(target.downloaded_sha256)
            or acquisition.get("terminal_transition_count") != 1
            or receipt.get("raw_content_sha256") != target.downloaded_sha256
        ):
            return _fail_result(check_id, "r18_phase_a_terminalization_invalid")
    return _pass(
        check_id,
        terminal_run_count=2,
        raw_blob_count=2,
        terminal_transition_count=2,
    )


def _ordinal(context: _EvidenceContext, phase: str, event: str) -> int:
    records = _events(context, phase=phase, event=event)
    return int(records[0]["ordinal"]) if len(records) == 1 else -1


def _check_r19_a_to_b_order(context: _EvidenceContext) -> CheckResult:
    check_id = "R19_A_TO_B_ORDER"
    blocked = _domain_error(context, check_id, "runtime")
    if blocked:
        return blocked
    boundaries = (
        _ordinal(context, "A", "socket_census"),
        _ordinal(context, "A", "job_zero"),
        _ordinal(context, "A", "authority_cleared"),
        _ordinal(context, "A", "phase_complete"),
    )
    b_start = _ordinal(context, "B", "phase_child_start")
    a_proof = _child_proof_record(
        context,
        phase="A",
        ordinal=1,
        event="acquisition_boundary",
    )
    a_complete = _events(context, phase="A", event="phase_complete")
    b_child_start = _events(context, phase="B", event="phase_child_start")
    if (
        -1 in boundaries
        or b_start < 0
        or max(boundaries) >= b_start
        or not _child_proof_sequence_exact(context)
        or len(a_complete) != 1
        or len(b_child_start) != 1
        or a_proof.get("process_boot_id") != a_complete[0].get("process_boot_id")
        or a_proof.get("process_boot_id") == b_child_start[0].get("process_boot_id")
    ):
        return _fail_result(check_id, "r19_a_to_b_order_invalid")
    return _pass(
        check_id,
        phase_a_terminal_ordinal=boundaries[-1],
        phase_b_start_ordinal=b_start,
        proof_stream_phase_order="A_then_B",
    )


def _check_r20_four_stream_closeout(context: _EvidenceContext) -> CheckResult:
    check_id = "R20_FOUR_STREAM_CLOSEOUT"
    blocked = _domain_error(context, check_id, "capture") or _domain_error(
        context, check_id, "runtime"
    )
    if blocked:
        return blocked
    terminal = _events(context, phase="wrapper", event="runtime_complete")
    if (
        tuple(Path(str(path)).name for path in context.capture.stream_bytes) != _EXPECTED_STREAM_FILES
        or len(terminal) != 1
        or context.manifest.runtime_stopped_at < context.manifest.runtime_started_at
    ):
        return _fail_result(check_id, "r20_four_stream_closeout_invalid")
    return _pass(check_id, closed_stream_count=4)


def _check_r21_extant_run_seal_events(context: _EvidenceContext) -> CheckResult:
    check_id = "R21_EXTANT_RUN_SEAL_EVENTS"
    blocked = _domain_error(context, check_id, "capture") or _domain_error(
        context, check_id, "ledger"
    )
    if blocked:
        return blocked
    from sqlalchemy import select

    from app.models.models import ConnectorRunEvent

    event_ids = tuple(context.capture.seal_event_ids)
    events = tuple(
        context.db.scalars(
            select(ConnectorRunEvent)
            .where(ConnectorRunEvent.connector_run_event_id.in_(event_ids))
            .limit(3)
        )
    )
    run_ids = {run.connector_run_id for run in context.runs}
    if (
        len(event_ids) != 2
        or len(set(event_ids)) != 2
        or len(events) != 2
        or {event.connector_run_id for event in events} != run_ids
        or any(
            event.event_type != "campaign_log_capture_sealed"
            or event.stage != "campaign_log_capture"
            or event.status_after != "completed"
            or event.reason_code != "protected_log_capture_sealed"
            for event in events
        )
    ):
        return _fail_result(check_id, "r21_extant_run_seal_events_invalid")
    return _pass(check_id, extant_run_count=2, seal_event_count=2)


def _check_r22_capture_start_contract(context: _EvidenceContext) -> CheckResult:
    check_id = "R22_CAPTURE_START_CONTRACT"
    blocked = _domain_error(context, check_id, "capture") or _domain_error(
        context, check_id, "authority"
    )
    if blocked:
        return blocked
    expected = tuple(f"{name}" for name in _EXPECTED_STREAM_FILES)
    if tuple(context.capture_ref.expected_stream_files) != expected or tuple(
        Path(str(path)).name for path in context.capture.stream_bytes
    ) != expected:
        return _fail_result(check_id, "r22_capture_start_contract_invalid")
    return _pass(check_id, shared_stream_count=4, encoding="utf-8")


def _run_events(context: _EvidenceContext, run: Any) -> tuple[Any, ...]:
    from sqlalchemy import select

    from app.models.models import ConnectorRunEvent

    return tuple(
        context.db.scalars(
            select(ConnectorRunEvent)
            .where(ConnectorRunEvent.connector_run_id == run.connector_run_id)
            .order_by(
                ConnectorRunEvent.created_at.asc(),
                ConnectorRunEvent.connector_run_event_id.asc(),
            )
            .limit(MAX_DB_ROWS + 1)
        )
    )


def _terminal_events(context: _EvidenceContext, run: Any) -> tuple[Any, ...]:
    return tuple(
        event
        for event in _run_events(context, run)
        if event.event_type == "egress_run_terminal"
    )


def _check_l01_run_cardinality(context: _EvidenceContext) -> CheckResult:
    check_id = "L01_RUN_CARDINALITY"
    blocked = _domain_error(context, check_id, "ledger")
    if blocked:
        return blocked
    if len(context.runs) != 2 or tuple(sorted(context.run_by_connector)) != _EXPECTED_CONNECTORS:
        return _fail_result(check_id, "l01_run_cardinality_invalid")
    if any(run.source_mode != "strict_live_egress" for run in context.runs):
        return _fail_result(check_id, "l01_fixture_or_noncampaign_run")
    return _pass(check_id, connector_count=2)


def _check_l02_terminal_event(context: _EvidenceContext) -> CheckResult:
    check_id = "L02_TERMINAL_EVENT"
    blocked = _domain_error(context, check_id, "ledger")
    if blocked:
        return blocked
    for run in context.runs:
        terminals = _terminal_events(context, run)
        if (
            len(terminals) != 1
            or run.status != "completed"
            or run.completed_at is None
            or run.execution_lease_owner is not None
            or run.execution_lease_token is not None
            or terminals[0].status_after != "completed"
            or terminals[0].created_at != run.completed_at
        ):
            return _fail_result(check_id, "l02_terminal_event_invalid")
    return _pass(check_id, completed_run_count=2, terminal_event_count=2)


def _check_l03_post_terminal_extinction(context: _EvidenceContext) -> CheckResult:
    check_id = "L03_POST_TERMINAL_EXTINCTION"
    blocked = _domain_error(context, check_id, "ledger")
    if blocked:
        return blocked
    forbidden = {"failed", "cancelled", "cancelling", "lease_acquired", "lease_reacquired"}
    for run in context.runs:
        events = _run_events(context, run)
        terminal_positions = tuple(
            index
            for index, event in enumerate(events)
            if event.event_type == "egress_run_terminal"
        )
        if len(terminal_positions) != 1:
            return _indeterminate(check_id, "l03_terminal_ambiguous")
        if any(
            (
                str(event.event_type).casefold() in forbidden
                or str(event.status_after or "").casefold() in forbidden
                or "lease" in str(event.event_type).casefold()
            )
            for event in events[terminal_positions[0] + 1 :]
        ):
            return _fail_result(check_id, "l03_post_terminal_contradiction")
    return _pass(check_id, contradictory_tail_count=0)


def _check_l04_ledger_reconstruction(context: _EvidenceContext) -> CheckResult:
    check_id = "L04_LEDGER_RECONSTRUCTION"
    blocked = _domain_error(context, check_id, "ledger")
    if blocked:
        return blocked
    if set(context.ledgers) != set(_EXPECTED_CONNECTORS):
        return _indeterminate(check_id, "l04_ledger_missing")
    if any(not ledger.eligible or ledger.validation_errors for ledger in context.ledgers.values()):
        return _indeterminate(check_id, "l04_ledger_reconstruction_invalid")
    return _pass(
        check_id,
        ledger_count=2,
        terminal_hashes=tuple(context.ledgers[key].ledger_terminal_hash for key in _EXPECTED_CONNECTORS),
    )


def _counter_identity(record: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        record.get("ordinal"),
        record.get("stage"),
        record.get("request_fingerprint"),
        record.get("response_status"),
        record.get("decoded_body_bytes"),
        record.get("decoded_body_sha256"),
    )


def _ledger_identity(entry: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        entry.get("ordinal"),
        entry.get("stage"),
        entry.get("request_fingerprint"),
        entry.get("response_status"),
        entry.get("byte_count"),
        entry.get("body_sha256"),
    )


def _check_l05_counter_bijection(context: _EvidenceContext) -> CheckResult:
    check_id = "L05_COUNTER_BIJECTION"
    blocked = _domain_error(context, check_id, "counter") or _domain_error(
        context, check_id, "ledger"
    )
    if blocked:
        return blocked
    expected: list[tuple[Any, ...]] = []
    run_by_identity: dict[tuple[Any, ...], str] = {}
    for connector_key in _EXPECTED_CONNECTORS:
        ledger = context.ledgers.get(connector_key)
        if ledger is None or not isinstance(ledger.connector_run_id, str):
            return _indeterminate(check_id, "l05_counter_ledger_bijection_invalid")
        for entry in ledger.entries:
            if entry.get("send_started_at") is None:
                continue
            identity = _ledger_identity(entry)
            if identity in run_by_identity:
                return _indeterminate(
                    check_id,
                    "l05_counter_ledger_identity_ambiguous",
                )
            run_by_identity[identity] = ledger.connector_run_id
            expected.append((ledger.connector_run_id, *identity))
    observed: list[tuple[Any, ...]] = []
    for record in context.counter_records:
        identity = _counter_identity(record)
        connector_run_id = run_by_identity.get(identity)
        if connector_run_id is None:
            return _indeterminate(check_id, "l05_counter_ledger_bijection_invalid")
        observed.append((connector_run_id, *identity))
    if expected != observed:
        return _indeterminate(check_id, "l05_counter_ledger_bijection_invalid")
    return _pass(check_id, counter_count=len(observed), ledger_send_count=len(expected))


def _check_l06_counter_boot(context: _EvidenceContext) -> CheckResult:
    check_id = "L06_COUNTER_BOOT"
    blocked = _domain_error(context, check_id, "counter")
    if blocked:
        return blocked
    schemas = {record.get("schema_id") for record in context.counter_records}
    runtimes = {record.get("runtime_instance_id") for record in context.counter_records}
    boots = {record.get("process_boot_id") for record in context.counter_records}
    a_boots = {record.get("process_boot_id") for record in _events(context, phase="A", event="phase_child_start")}
    if schemas != {"project6.connector_http_counter.v2"} or len(runtimes) != 1 or len(boots) != 1 or boots != a_boots:
        return _indeterminate(check_id, "l06_counter_boot_ambiguous")
    return _pass(check_id, runtime_instance_count=1, process_boot_count=1)


def _records_for_ledger(
    context: _EvidenceContext,
    ledger: Any,
) -> tuple[Mapping[str, Any], ...]:
    identities = {_ledger_identity(entry) for entry in ledger.entries if entry.get("send_started_at") is not None}
    return tuple(record for record in context.counter_records if _counter_identity(record) in identities)


def _check_l07_byte_allowance(context: _EvidenceContext) -> CheckResult:
    check_id = "L07_BYTE_ALLOWANCE"
    blocked = _domain_error(context, check_id, "counter") or _domain_error(
        context, check_id, "archive"
    )
    if blocked:
        return blocked
    for connector_key, ledger in context.ledgers.items():
        grant = context.historical[connector_key].model
        counted = sum(
            int(record["canonical_status_header_bytes"])
            + int(record["delivered_body_bytes"])
            for record in _records_for_ledger(context, ledger)
        )
        excess = counted - grant.max_run_bytes
        if excess > grant.max_single_send_detection_allowance_bytes:
            return _indeterminate(check_id, "l07_detection_allowance_exceeded")
        if excess > 0 and context.run_by_connector[connector_key].status == "completed":
            return _fail_result(check_id, "l07_crossing_classification_invalid")
    return _pass(check_id, connector_count=2)


def _check_l08_request_cadence(context: _EvidenceContext) -> CheckResult:
    check_id = "L08_REQUEST_CADENCE"
    blocked = _domain_error(context, check_id, "counter") or _domain_error(
        context, check_id, "archive"
    )
    if blocked:
        return blocked
    for connector_key, ledger in context.ledgers.items():
        minimum = context.historical[connector_key].model.min_request_interval_ms / 1000
        starts = sorted(float(record["monotonic_started_at"]) for record in _records_for_ledger(context, ledger))
        if any(later - earlier < minimum for earlier, later in zip(starts, starts[1:])):
            return _fail_result(check_id, "l08_request_cadence_short")
    return _pass(check_id, cadence_verified=True)


def _check_l09_transport_policy(context: _EvidenceContext) -> CheckResult:
    check_id = "L09_TRANSPORT_POLICY"
    blocked = _domain_error(context, check_id, "ledger") or _domain_error(
        context, check_id, "archive"
    )
    if blocked:
        return blocked
    from app.services.connector_egress_evidence import (
        _EXACT_PATH_RULES,
        _QUERY_CLASSES,
    )

    for connector_key, ledger in context.ledgers.items():
        rules = {rule.stage: rule for rule in context.historical[connector_key].model.request_rules}
        for entry in ledger.entries:
            rule = rules.get(entry.get("stage"))
            if rule is None or (
                entry.get("method") != rule.method
                or entry.get("host") not in rule.allowed_hosts
                or entry.get("path_class")
                != _EXACT_PATH_RULES[rule.path_rule_id][1]
                or entry.get("query_class") != _QUERY_CLASSES[rule.query_rule_id]
                or entry.get("credential_audience") != rule.credential_audience
            ):
                return _fail_result(check_id, "l09_transport_policy_violation")
    return _pass(check_id, request_rule_count=sum(len(item.model.request_rules) for item in context.historical.values()))


def _check_l10_fresh_200_bytes(context: _EvidenceContext) -> CheckResult:
    check_id = "L10_FRESH_200_BYTES"
    blocked = _domain_error(context, check_id, "counter") or _domain_error(
        context, check_id, "origin"
    )
    if blocked:
        return blocked
    for connector_key, ledger in context.ledgers.items():
        digest = context.origins[connector_key].get("raw_content_sha256")
        size = context.origins[connector_key].get("raw_content_size_bytes")
        matching = tuple(
            record
            for record in _records_for_ledger(context, ledger)
            if record.get("response_status") == 200
            and record.get("decoded_body_sha256") == digest
            and record.get("decoded_body_bytes") == size
        )
        if len(matching) != 1:
            return _fail_result(check_id, "l10_fresh_200_bytes_invalid")
    return _pass(check_id, admitted_raw_response_count=2)


def _check_l11_nrc_first_binding(context: _EvidenceContext) -> CheckResult:
    check_id = "L11_NRC_FIRST_BINDING"
    blocked = _domain_error(context, check_id, "ledger")
    if blocked:
        return blocked
    nrc_run = context.run_by_connector.get("nrc_adams_aps")
    sciencebase = context.envelopes.get("sciencebase_mcs", {})
    nrc_ledger = context.ledgers.get("nrc_adams_aps")
    if nrc_run is None or nrc_ledger is None or (
        sciencebase.get("predecessor_nrc_connector_run_id") != nrc_run.connector_run_id
        or sciencebase.get("predecessor_nrc_ledger_terminal_hash") != nrc_ledger.ledger_terminal_hash
    ):
        return _fail_result(check_id, "l11_nrc_first_binding_invalid")
    return _pass(check_id, parent_run_id=nrc_run.connector_run_id, parent_terminal_hash=nrc_ledger.ledger_terminal_hash)


def _check_l12_reservation_resolution(context: _EvidenceContext) -> CheckResult:
    check_id = "L12_RESERVATION_RESOLUTION"
    blocked = _domain_error(context, check_id, "ledger")
    if blocked:
        return blocked
    if any(
        entry.get("completion_event_id") is None
        or entry.get("outcome_class") in {"reserved_not_sent", "spent_unknown"}
        for ledger in context.ledgers.values()
        for entry in ledger.entries
    ):
        return _fail_result(check_id, "l12_reservation_unresolved")
    return _pass(check_id, unresolved_reservation_count=0)


def _stored_origin_receipt(target: Any) -> Mapping[str, Any] | None:
    source_reference = target.source_reference_json
    if not isinstance(source_reference, Mapping):
        return None
    receipt = source_reference.get("connector_origin_receipt_v1")
    return receipt if isinstance(receipt, Mapping) else None


def _receipt_hash_is_valid(receipt: Mapping[str, Any]) -> bool:
    raw_hash = receipt.get("receipt_hash")
    if not isinstance(raw_hash, str) or not _LOWERCASE_SHA256.fullmatch(raw_hash):
        return False
    preimage = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    return hashlib.sha256(_canonical_bytes(preimage)).hexdigest() == raw_hash


def _check_d01_origin_receipt(context: _EvidenceContext) -> CheckResult:
    check_id = "D01_ORIGIN_RECEIPT"
    blocked = _domain_error(context, check_id, "origin")
    if blocked:
        return blocked
    if set(context.origins) != set(_EXPECTED_CONNECTORS):
        return _indeterminate(check_id, "d01_origin_receipt_missing")
    for connector_key in _EXPECTED_CONNECTORS:
        receipt = context.origins[connector_key]
        target = context.targets.get(connector_key)
        if (
            target is None
            or receipt.get("schema_id") != "layer3.connector_origin_continuity.v1"
            or receipt.get("proof_class") != "fresh_live"
            or receipt.get("connector_key") != connector_key
            or receipt.get("connector_run_target_id")
            != target.connector_run_target_id
            or dict(_stored_origin_receipt(target) or {}) != dict(receipt)
            or not _receipt_hash_is_valid(receipt)
        ):
            return _fail_result(check_id, "d01_origin_receipt_invalid")
    return _pass(check_id, rederived_receipt_count=2)


def _check_d02_raw_provenance_linkage(context: _EvidenceContext) -> CheckResult:
    check_id = "D02_RAW_PROVENANCE_LINKAGE"
    blocked = _domain_error(context, check_id, "origin")
    if blocked:
        return blocked
    for connector_key in _EXPECTED_CONNECTORS:
        receipt = context.origins.get(connector_key)
        target = context.targets.get(connector_key)
        run = context.run_by_connector.get(connector_key)
        if receipt is None or target is None or run is None:
            return _indeterminate(check_id, "d02_raw_linkage_missing")
        if (
            receipt.get("connector_run_id") != run.connector_run_id
            or receipt.get("connector_run_target_id")
            != target.connector_run_target_id
            or receipt.get("source_artifact_key") != target.source_artifact_key
            or receipt.get("raw_storage_ref") != target.raw_storage_ref
            or receipt.get("raw_content_sha256") != target.downloaded_sha256
            or not isinstance(receipt.get("raw_content_size_bytes"), int)
            or int(receipt["raw_content_size_bytes"]) <= 0
        ):
            return _fail_result(check_id, "d02_raw_provenance_linkage_invalid")
        if connector_key == "sciencebase_mcs" and any(
            not receipt.get(field_name)
            for field_name in (
                "dataset_version_id",
                "dataset_source_provenance_id",
                "connector_source_intake_record_id",
            )
        ):
            return _fail_result(check_id, "d02_raw_provenance_linkage_invalid")
        if connector_key == "nrc_adams_aps" and any(
            not receipt.get(field_name)
            for field_name in ("aps_content_linkage_id", "content_id")
        ):
            return _fail_result(check_id, "d02_raw_provenance_linkage_invalid")
    return _pass(check_id, linked_raw_blob_count=2)


def _stable_evidence_id(prefix: str, value: Mapping[str, Any]) -> str:
    return f"{prefix}-{hashlib.sha256(_canonical_bytes(value)).hexdigest()[:16]}"


def _connector_integrity_pair(
    context: _EvidenceContext,
    connector_key: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any]] | None:
    receipt = context.origins.get(connector_key)
    output = context.output_integrity.get(connector_key)
    if receipt is None or output is None:
        return None
    try:
        origin = _origin_integrity(receipt)
    except DualLiveEvaluationError:
        return None
    expected_output_fields = {
        "schema_id",
        "connector_key",
        "connector_run_target_id",
        "connector_origin_receipt_hash",
        "proof_class",
        "artifact_receipts",
        "artifact_set_hash",
        "output_manifest_sha256",
    }
    if (
        set(output) != expected_output_fields
        or output.get("schema_id") != "layer3.connector_output_integrity.v1"
        or any(
            output.get(field) != origin.get(field)
            for field in (
                "connector_key",
                "connector_run_target_id",
                "connector_origin_receipt_hash",
                "proof_class",
            )
        )
        or not isinstance(output.get("artifact_receipts"), (list, tuple))
        or not isinstance(output.get("artifact_set_hash"), str)
        or not _LOWERCASE_SHA256.fullmatch(str(output["artifact_set_hash"]))
        or not isinstance(output.get("output_manifest_sha256"), str)
        or not _LOWERCASE_SHA256.fullmatch(str(output["output_manifest_sha256"]))
    ):
        return None
    return origin, output


def _package_vectors(
    rows: Sequence[Any],
) -> tuple[list[str], list[str], list[str], list[str]] | None:
    ordered = _ordered_package_rows(rows)
    kinds = [str(row.package_kind) for row in ordered]
    if len(ordered) != 3 or kinds != list(_PACKAGE_KINDS):
        return None
    package_ids = [str(row.output_package_id or "") for row in ordered]
    payload_refs = [str(row.payload_ref or "") for row in ordered]
    payload_hashes = [str(row.payload_hash or "") for row in ordered]
    if (
        any(not value for value in (*package_ids, *payload_refs))
        or any(not _LOWERCASE_SHA256.fullmatch(value) for value in payload_hashes)
    ):
        return None
    return package_ids, kinds, payload_refs, payload_hashes


def _state_mirrors(
    state: Mapping[str, Any],
    basis: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> bool:
    return all(
        state.get(field) == value and basis.get(field) == value
        for field, value in expected.items()
    )


def _check_d03_layer3_execution(context: _EvidenceContext) -> CheckResult:
    check_id = "D03_LAYER3_EXECUTION"
    blocked = _domain_error(context, check_id, "execution")
    if blocked:
        return blocked
    if (
        set(context.pass_runs) != set(_EXPECTED_CONNECTORS)
        or set(context.output_integrity) != set(_EXPECTED_CONNECTORS)
        or set(context.downstream_sessions) != set(_EXPECTED_CONNECTORS)
    ):
        return _indeterminate(check_id, "d03_layer3_execution_missing")
    for connector_key in _EXPECTED_CONNECTORS:
        pass_run = context.pass_runs[connector_key]
        session = context.downstream_sessions[connector_key]
        pair = _connector_integrity_pair(context, connector_key)
        summary = getattr(pass_run, "summary_json", None)
        if pair is None:
            return _fail_result(check_id, "d03_layer3_execution_invalid")
        origin, output = pair
        if (
            pass_run.session_id != session.session_id
            or pass_run.status not in {"completed", "completed_with_warnings"}
            or not str(pass_run.output_payload_ref or "").strip()
            or not isinstance(summary, Mapping)
            or summary.get("connector_origin_integrity_v1") != origin
            or summary.get("connector_output_integrity_v1") != output
        ):
            return _fail_result(check_id, "d03_layer3_execution_invalid")
    return _pass(check_id, execution_result_count=2)


def _check_d04_review_result(context: _EvidenceContext) -> CheckResult:
    check_id = "D04_REVIEW_RESULT"
    blocked = _domain_error(context, check_id, "review")
    if blocked:
        return blocked
    if set(context.review_states) != set(_EXPECTED_CONNECTORS):
        return _indeterminate(check_id, "d04_review_result_missing")
    for connector_key in _EXPECTED_CONNECTORS:
        pass_run = context.pass_runs.get(connector_key)
        state = context.review_states[connector_key]
        pair = _connector_integrity_pair(context, connector_key)
        if pass_run is None or pair is None:
            return _indeterminate(check_id, "d04_review_result_missing")
        origin, output = pair
        if (
            state.get("schema_id")
            != "layer3.execution_result_review_state.v1"
            or state.get("review_state") != "execution_result_review_approved"
            or state.get("operator_decision") != "approved"
            or int(state.get("unresolved_trace_count") or 0) != 0
            or state.get("analysis_plan_id") != pass_run.analysis_plan_id
            or state.get("pass_run_id") != pass_run.pass_run_id
            or not str(state.get("review_record_ref") or "").strip()
            or state.get("connector_origin_integrity_v1") != origin
            or state.get("connector_output_integrity_v1") != output
        ):
            return _fail_result(check_id, "d04_review_result_invalid")
    return _pass(check_id, bound_review_count=2)


def _check_d05_package_set(context: _EvidenceContext) -> CheckResult:
    from app.services.layer3_utils import stable_json_text_hash

    check_id = "D05_PACKAGE_SET"
    blocked = _domain_error(context, check_id, "package_set")
    if blocked:
        return blocked
    required_maps = (
        context.packages,
        context.package_commits,
        context.reconciliations,
    )
    if any(set(mapping) != set(_EXPECTED_CONNECTORS) for mapping in required_maps):
        return _indeterminate(check_id, "d05_package_set_missing")
    for connector_key in _EXPECTED_CONNECTORS:
        rows = context.packages.get(connector_key, ())
        if len(rows) < 3:
            return _indeterminate(check_id, "d05_package_set_missing")
        vectors = _package_vectors(rows)
        session = context.downstream_sessions.get(connector_key)
        pass_run = context.pass_runs.get(connector_key)
        review = context.review_states.get(connector_key)
        reconciliation = context.reconciliations[connector_key]
        commit = context.package_commits[connector_key]
        if vectors is None or session is None or pass_run is None or review is None:
            return _fail_result(check_id, "d05_package_set_invalid")
        _package_ids, kinds, refs, hashes = vectors
        reconciliation_id = reconciliation.reconciliation_record_id
        basis = commit.get("authority_basis")
        if not isinstance(basis, Mapping):
            return _fail_result(check_id, "d05_package_set_invalid")
        thawed_basis = _thaw(basis)
        authority_hash = stable_json_text_hash(thawed_basis)
        construction_hash = stable_json_text_hash(
            {
                **thawed_basis,
                "package_kinds": kinds,
                "payload_refs": refs,
                "payload_hashes": hashes,
            }
        )
        if (
            reconciliation.session_id != session.session_id
            or any(
                row.session_id != session.session_id
                or row.reconciliation_record_id != reconciliation_id
                for row in rows
            )
            or commit.get("schema_id")
            != "layer3.workbench_package_commit_summary.v1"
            or basis.get("session_id") != session.session_id
            or basis.get("analysis_plan_id") != pass_run.analysis_plan_id
            or basis.get("pass_run_id") != pass_run.pass_run_id
            or basis.get("result_review_record_ref")
            != review.get("review_record_ref")
            or commit.get("result_review_record_ref")
            != review.get("review_record_ref")
            or commit.get("authority_basis_hash") != authority_hash
            or commit.get("construction_basis_hash") != construction_hash
        ):
            return _fail_result(check_id, "d05_package_set_invalid")
    return _pass(check_id, package_count=6, package_kind_count=3)


def _check_d06_package_payload(context: _EvidenceContext) -> CheckResult:
    check_id = "D06_PACKAGE_PAYLOAD"
    blocked = _domain_error(context, check_id, "package_set")
    if blocked:
        return blocked
    if (
        set(context.packages) != set(_EXPECTED_CONNECTORS)
        or set(context.package_payloads) != set(_EXPECTED_CONNECTORS)
    ):
        return _indeterminate(check_id, "d06_package_payload_missing")
    for connector_key in _EXPECTED_CONNECTORS:
        if _package_vectors(context.packages[connector_key]) is None:
            return _indeterminate(check_id, "d06_package_payload_missing")
        payloads = context.package_payloads.get(connector_key, ())
        pair = _connector_integrity_pair(context, connector_key)
        if len(payloads) != 3:
            return _fail_result(check_id, "d06_package_payload_invalid")
        if pair is None:
            return _indeterminate(check_id, "d06_package_payload_missing")
        origin, output = pair
        by_kind: dict[str, Mapping[str, Any]] = {}
        for payload in payloads:
            header = payload.get("package_header")
            if not isinstance(header, Mapping):
                return _fail_result(check_id, "d06_package_payload_invalid")
            kind = str(header.get("package_kind") or "")
            if kind in by_kind:
                return _fail_result(check_id, "d06_package_payload_invalid")
            by_kind[kind] = payload
        if set(by_kind) != set(_PACKAGE_KINDS):
            return _fail_result(check_id, "d06_package_payload_invalid")
        for kind in _PACKAGE_KINDS:
            payload = by_kind[kind]
            if (
                payload.get("connector_origin_integrity_v1") != origin
                or payload.get("connector_output_integrity_v1") != output
            ):
                return _fail_result(check_id, "d06_package_payload_invalid")
    return _pass(check_id, rehashed_payload_count=6)


def _check_d07_submit_receipt(context: _EvidenceContext) -> CheckResult:
    check_id = "D07_SUBMIT_RECEIPT"
    blocked = _domain_error(context, check_id, "submit")
    if blocked:
        return blocked
    if set(context.submit_states) != set(_EXPECTED_CONNECTORS):
        return _indeterminate(check_id, "d07_submit_receipt_missing")
    for connector_key in _EXPECTED_CONNECTORS:
        state = context.submit_states[connector_key]
        basis = state.get("authority_basis")
        session = context.downstream_sessions.get(connector_key)
        pass_run = context.pass_runs.get(connector_key)
        review = context.review_states.get(connector_key)
        reconciliation = context.reconciliations.get(connector_key)
        vectors = _package_vectors(context.packages.get(connector_key, ()))
        pair = _connector_integrity_pair(context, connector_key)
        if (
            not isinstance(basis, Mapping)
            or session is None
            or pass_run is None
            or review is None
            or reconciliation is None
            or vectors is None
            or pair is None
        ):
            return _indeterminate(check_id, "d07_submit_receipt_missing")
        package_ids, kinds, refs, hashes = vectors
        origin, output = pair
        expected = {
            "analysis_plan_id": pass_run.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "result_review_record_ref": review.get("review_record_ref"),
            "reconciliation_record_id": reconciliation.reconciliation_record_id,
            "output_package_ids": package_ids,
            "package_kinds": kinds,
            "payload_hashes": hashes,
            "operator_decision": "approved",
        }
        if (
            state.get("schema_id")
            != "layer3.package_review_submit_state.v1"
            or basis.get("schema_id")
            != "layer3.package_review_submit_authority.v1"
            or basis.get("session_id") != session.session_id
            or not _state_mirrors(state, basis, expected)
            or state.get("submit_record_ref")
            != _stable_evidence_id("l3-package-review-submit", basis)
            or state.get("package_review_state") != "package_review_approved"
            or state.get("payload_refs") != basis.get("payload_refs")
            or (
                state.get("payload_refs") is not None
                and state.get("payload_refs") != refs
            )
            or state.get("connector_origin_integrity_v1") != origin
            or state.get("connector_output_integrity_v1") != output
            or state.get("handoff_enabled") is not False
            or state.get("export_enabled") is not False
        ):
            return _fail_result(check_id, "d07_submit_receipt_invalid")
    return _pass(check_id, submit_receipt_count=2)


def _check_d08_handoff_receipt(context: _EvidenceContext) -> CheckResult:
    check_id = "D08_HANDOFF_RECEIPT"
    blocked = _domain_error(context, check_id, "handoff")
    if blocked:
        return blocked
    if set(context.handoff_states) != set(_EXPECTED_CONNECTORS):
        return _indeterminate(check_id, "d08_handoff_receipt_missing")
    flags = (
        "external_handoff_enabled",
        "external_export_enabled",
        "dispatch_enabled",
        "aps_handoff_enabled",
        "external_export_download_enabled",
        "connector_dispatch_enabled",
        "provider_public_url_enabled",
    )
    for connector_key in _EXPECTED_CONNECTORS:
        state = context.handoff_states[connector_key]
        basis = state.get("authority_basis")
        envelope = state.get("handoff_export_envelope")
        session = context.downstream_sessions.get(connector_key)
        pass_run = context.pass_runs.get(connector_key)
        review = context.review_states.get(connector_key)
        reconciliation = context.reconciliations.get(connector_key)
        submit = context.submit_states.get(connector_key)
        vectors = _package_vectors(context.packages.get(connector_key, ()))
        pair = _connector_integrity_pair(context, connector_key)
        if (
            not isinstance(basis, Mapping)
            or not isinstance(envelope, Mapping)
            or session is None
            or pass_run is None
            or review is None
            or reconciliation is None
            or submit is None
            or vectors is None
            or pair is None
        ):
            return _indeterminate(check_id, "d08_handoff_receipt_missing")
        package_ids, kinds, refs, hashes = vectors
        origin, output = pair
        expected = {
            "analysis_plan_id": pass_run.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "result_review_record_ref": review.get("review_record_ref"),
            "reconciliation_record_id": reconciliation.reconciliation_record_id,
            "output_package_ids": package_ids,
            "package_kinds": kinds,
            "payload_refs": refs,
            "payload_hashes": hashes,
            "package_review_submit_record_ref": submit.get("submit_record_ref"),
            "package_review_state": "package_review_approved",
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "operator_decision": "authorize_prepare",
        }
        envelope_expected = {
            key: value
            for key, value in expected.items()
            if key
            not in {
                "package_review_state",
                "handoff_target",
                "export_mode",
                "operator_decision",
            }
        }
        envelope_basis = {
            **dict(basis),
            "schema_id": "layer3.handoff_export_envelope_authority.v1",
        }
        if (
            state.get("schema_id")
            != "layer3.handoff_export_prepare_state.v1"
            or basis.get("schema_id")
            != "layer3.handoff_export_prepare_authority.v1"
            or basis.get("session_id") != session.session_id
            or not _state_mirrors(state, basis, expected)
            or state.get("prepare_record_ref")
            != _stable_evidence_id("l3-handoff-export-prepare", basis)
            or state.get("handoff_export_state") != "handoff_export_prepared"
            or envelope.get("schema_id") != "layer3.handoff_export_envelope.v1"
            or envelope.get("session_id") != session.session_id
            or any(
                envelope.get(field) != value
                for field, value in envelope_expected.items()
            )
            or envelope.get("envelope_ref")
            != _stable_evidence_id("l3-handoff-export-envelope", envelope_basis)
            or state.get("connector_origin_integrity_v1") != origin
            or state.get("connector_output_integrity_v1") != output
            or envelope.get("connector_origin_integrity_v1") != origin
            or envelope.get("connector_output_integrity_v1") != output
            or any(state.get(flag) is not False for flag in flags)
            or any(envelope.get(flag) is not False for flag in flags)
        ):
            return _fail_result(check_id, "d08_handoff_receipt_invalid")
    return _pass(check_id, prepared_internal_handoff_count=2, delivery_claim_count=0)


@dataclass(frozen=True, slots=True)
class _ScanResult:
    scanned_count: int
    hit_count: int
    first_hit_digest: str | None


def _json_unescape_once(value: str) -> str:
    simple = {
        '"': '"',
        "\\": "\\",
        "/": "/",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }

    def replace_escape(match: re.Match[str]) -> str:
        token = match.group(1)
        if token.startswith("u"):
            codepoint = int(token[1:], 16)
            if 0xD800 <= codepoint <= 0xDFFF:
                raise DualLiveEvaluationError("dual_live_scan_json_encoding_invalid")
            return chr(codepoint)
        return simple[token]

    return re.sub(r'\\(["\\/bfnrt]|u[0-9A-Fa-f]{4})', replace_escape, value)


def _strict_percent_decode(value: str) -> str:
    if _PERCENT_ESCAPE.search(value) is None:
        return value
    try:
        return unquote_to_bytes(value).decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise DualLiveEvaluationError(
            "dual_live_scan_percent_encoding_invalid"
        ) from exc


def _decoded_forms(payload: bytes, *, strict_utf8: bool) -> tuple[str, ...]:
    if len(payload) > MAX_SCAN_FILE_BYTES:
        raise DualLiveEvaluationError("dual_live_scan_payload_size_exceeded")
    try:
        raw = payload.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        if strict_utf8:
            raise DualLiveEvaluationError("dual_live_scan_utf8_invalid") from exc
        raw = payload.decode("latin-1")
    forms = {raw}
    pending = [(raw, 0)]
    while pending:
        current, depth = pending.pop()
        transformed_values = (
            html.unescape(current),
            _json_unescape_once(current),
            _strict_percent_decode(current),
        )
        for transformed in transformed_values:
            if transformed == current:
                continue
            if depth >= 2:
                raise DualLiveEvaluationError("dual_live_scan_third_encoding_layer")
            if transformed in forms:
                continue
            forms.add(transformed)
            if len(forms) > 32:
                raise DualLiveEvaluationError(
                    "dual_live_scan_decoder_fanout_exceeded"
                )
            pending.append((transformed, depth + 1))
    return tuple(sorted(forms))


def _forbidden_candidates(
    context: _EvidenceContext,
    *,
    include_secret: bool,
) -> tuple[str, ...]:
    candidates = {
        "ocp-apim-subscription-key",
        "subscription-key:",
        "subscription_key=",
    }
    for evidence in context.historical.values():
        grant = evidence.model
        for rule in grant.request_rules:
            candidates.update(f"https://{host}" for host in rule.allowed_hosts)
        target = grant.target
        file_name = getattr(target, "exact_file_name", None)
        if isinstance(file_name, str) and file_name:
            candidates.update((f"?f={file_name}", f"&f={file_name}", f"f={file_name}"))
    if include_secret:
        key = context.settings.nrc_adams_subscription_key
        if not isinstance(key, str) or not key:
            raise DualLiveEvaluationError("dual_live_secret_scan_key_unavailable")
        candidates.add(key)
    return tuple(sorted(candidates, key=lambda item: (item.casefold(), item)))


def _scan_payloads(
    payloads: Sequence[tuple[str, bytes]],
    *,
    candidates: Sequence[str],
    strict_utf8: bool,
) -> _ScanResult:
    if len(payloads) > MAX_SCAN_FILES:
        raise DualLiveEvaluationError("dual_live_scan_file_cap_exceeded")
    total = 0
    hit_count = 0
    first_hit_digest: str | None = None
    folded_candidates = tuple(item.casefold() for item in candidates if item)
    for sink_id, payload in payloads:
        if not isinstance(sink_id, str) or not isinstance(payload, bytes):
            raise DualLiveEvaluationError("dual_live_scan_payload_invalid")
        total += len(payload)
        if total > MAX_SCAN_TOTAL_BYTES:
            raise DualLiveEvaluationError("dual_live_scan_total_size_exceeded")
        forms = _decoded_forms(payload, strict_utf8=strict_utf8)
        for form_index, form in enumerate(forms):
            folded = form.casefold()
            for candidate_index, candidate in enumerate(folded_candidates):
                offset = folded.find(candidate)
                if offset < 0:
                    continue
                hit_count += 1
                if first_hit_digest is None:
                    descriptor = (
                        f"{sink_id}|{form_index}|{candidate_index}|{offset}"
                    ).encode("utf-8")
                    first_hit_digest = hashlib.sha256(descriptor).hexdigest()
    return _ScanResult(
        scanned_count=len(payloads),
        hit_count=hit_count,
        first_hit_digest=first_hit_digest,
    )


def _db_scan_payloads(context: _EvidenceContext) -> tuple[tuple[str, bytes], ...]:
    payloads: list[tuple[str, bytes]] = []
    nodes = 0
    for identity, value in context.db_values:
        nodes += 1
        if nodes > MAX_DB_JSON_TOKENS:
            raise DualLiveEvaluationError("dual_live_db_json_token_cap_exceeded")
        encoded = _canonical_bytes(value)
        if len(encoded) > MAX_DB_VALUE_BYTES:
            raise DualLiveEvaluationError("dual_live_db_value_cap_exceeded")
        payloads.append((identity, encoded))
    return tuple(payloads)


def _serialization_scan_payloads(
    context: _EvidenceContext,
) -> tuple[tuple[str, bytes], ...]:
    payloads = [
        (identity, _canonical_bytes(value))
        for identity, value in context.db_values
        if any(
            marker in identity.casefold()
            for marker in (
                "event",
                "json",
                "receipt",
                "summary",
                "report",
                "payload",
            )
        )
    ]
    for connector_key in _EXPECTED_CONNECTORS:
        for ordinal, payload in enumerate(
            context.package_payloads.get(connector_key, ()),
            start=1,
        ):
            payloads.append(
                (
                    f"package:{connector_key}:{ordinal}",
                    _canonical_bytes(payload),
                )
            )
    return tuple(payloads)


def _runtime_scan_payloads(context: _EvidenceContext) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (name, _stream_bytes(context.capture, name))
        for name in _EXPECTED_STREAM_FILES
    )


def _scan_check(
    context: _EvidenceContext,
    *,
    check_id: str,
    payloads: Sequence[tuple[str, bytes]],
    candidates: Sequence[str],
    strict_utf8: bool,
    fail_code: str,
) -> CheckResult:
    try:
        result = _scan_payloads(
            payloads,
            candidates=candidates,
            strict_utf8=strict_utf8,
        )
    except DualLiveEvaluationError:
        return _indeterminate(check_id, f"{check_id.lower()}_scan_indeterminate")
    if result.hit_count:
        return _fail_result(
            check_id,
            fail_code,
            hit_count=result.hit_count,
            first_hit_digest=result.first_hit_digest,
        )
    return _pass(check_id, scanned_sink_count=result.scanned_count, hit_count=0)


def _check_c01_strict_nulls(context: _EvidenceContext) -> CheckResult:
    check_id = "C01_STRICT_NULLS"
    blocked = _domain_error(context, check_id, "custody") or _domain_error(
        context, check_id, "ledger"
    )
    if blocked:
        return blocked
    from sqlalchemy import select

    from app.models.models import ConnectorArtifactAlias, DatasetSourceProvenance

    target_ids = [target.connector_run_target_id for target in context.targets.values()]
    run_ids = [run.connector_run_id for run in context.runs]
    aliases = tuple(
        context.db.scalars(
            select(ConnectorArtifactAlias)
            .where(ConnectorArtifactAlias.connector_run_target_id.in_(target_ids))
            .limit(MAX_DB_ROWS + 1)
        )
    )
    provenance = tuple(
        context.db.scalars(
            select(DatasetSourceProvenance)
            .where(DatasetSourceProvenance.connector_run_id.in_(run_ids))
            .limit(MAX_DB_ROWS + 1)
        )
    )
    if len(aliases) > MAX_DB_ROWS or len(provenance) > MAX_DB_ROWS:
        return _indeterminate(check_id, "c01_strict_null_row_cap_exceeded")
    if any(
        target.sciencebase_item_url is not None
        or target.sciencebase_download_uri is not None
        for target in context.targets.values()
    ) or any(alias.alias_url is not None for alias in aliases) or any(
        row.sciencebase_item_url is not None
        or row.sciencebase_download_uri is not None
        for row in provenance
    ):
        return _fail_result(check_id, "c01_strict_url_scalar_nonnull")
    return _pass(
        check_id,
        target_count=len(context.targets),
        alias_count=len(aliases),
        provenance_count=len(provenance),
    )


def _check_c02_db_scalar_json_scan(context: _EvidenceContext) -> CheckResult:
    check_id = "C02_DB_SCALAR_JSON_SCAN"
    blocked = _domain_error(context, check_id, "custody") or _domain_error(
        context, check_id, "archive"
    )
    if blocked:
        return blocked
    try:
        payloads = _db_scan_payloads(context)
        candidates = _forbidden_candidates(context, include_secret=False)
    except DualLiveEvaluationError:
        return _indeterminate(check_id, "c02_db_scan_indeterminate")
    return _scan_check(
        context,
        check_id=check_id,
        payloads=payloads,
        candidates=candidates,
        strict_utf8=True,
        fail_code="c02_forbidden_database_material",
    )


def _check_c03_non_source_file_scan(context: _EvidenceContext) -> CheckResult:
    check_id = "C03_NON_SOURCE_FILE_SCAN"
    blocked = _domain_error(context, check_id, "custody") or _domain_error(
        context, check_id, "archive"
    )
    if blocked:
        return blocked
    try:
        candidates = _forbidden_candidates(context, include_secret=False)
    except DualLiveEvaluationError:
        return _indeterminate(check_id, "c03_file_scan_indeterminate")
    return _scan_check(
        context,
        check_id=check_id,
        payloads=context.non_source_files,
        candidates=candidates,
        strict_utf8=False,
        fail_code="c03_forbidden_file_material",
    )


def _check_c04_serialization_event_scan(context: _EvidenceContext) -> CheckResult:
    check_id = "C04_SERIALIZATION_EVENT_SCAN"
    blocked = _domain_error(context, check_id, "custody") or _domain_error(
        context, check_id, "downstream"
    )
    if blocked:
        return blocked
    try:
        payloads = _serialization_scan_payloads(context)
        candidates = _forbidden_candidates(context, include_secret=False)
    except DualLiveEvaluationError:
        return _indeterminate(check_id, "c04_serialization_scan_indeterminate")
    return _scan_check(
        context,
        check_id=check_id,
        payloads=payloads,
        candidates=candidates,
        strict_utf8=True,
        fail_code="c04_forbidden_serialized_material",
    )


def _check_c05_runtime_log_scan(context: _EvidenceContext) -> CheckResult:
    check_id = "C05_RUNTIME_LOG_SCAN"
    blocked = _domain_error(context, check_id, "capture") or _domain_error(
        context, check_id, "archive"
    )
    if blocked:
        return blocked
    try:
        payloads = _runtime_scan_payloads(context)
        candidates = _forbidden_candidates(context, include_secret=False)
    except DualLiveEvaluationError:
        return _indeterminate(check_id, "c05_runtime_scan_indeterminate")
    return _scan_check(
        context,
        check_id=check_id,
        payloads=payloads,
        candidates=candidates,
        strict_utf8=True,
        fail_code="c05_forbidden_runtime_material",
    )


def _check_c06_bounded_decoders(context: _EvidenceContext) -> CheckResult:
    check_id = "C06_BOUNDED_DECODERS"
    blocked = _domain_error(context, check_id, "custody") or _domain_error(
        context, check_id, "capture"
    )
    if blocked:
        return blocked
    try:
        payloads = _db_scan_payloads(context) + _runtime_scan_payloads(context)
        decoded_form_count = sum(
            len(_decoded_forms(payload, strict_utf8=True))
            for _identity, payload in payloads
        )
    except DualLiveEvaluationError:
        return _indeterminate(check_id, "c06_bounded_decoder_invalid")
    return _pass(
        check_id,
        decoded_sink_count=len(payloads),
        decoded_form_count=decoded_form_count,
    )


def _source_blob_from_settings(settings: Any, raw_ref: str) -> bytes:
    root, root_info = _fixed_local_path_before_touch(
        settings.connector_raw_dir,
        code="dual_live_source_root_invalid",
    )
    if root_info is None or not stat.S_ISDIR(root_info.st_mode):
        raise DualLiveEvaluationError("dual_live_source_root_invalid")
    if not isinstance(raw_ref, str) or not raw_ref or raw_ref != raw_ref.strip():
        raise DualLiveEvaluationError("dual_live_source_ref_unsafe")
    raw_candidate = PureWindowsPath(raw_ref.replace("/", "\\"))
    if any(component in {"", ".", ".."} for component in raw_candidate.parts):
        raise DualLiveEvaluationError("dual_live_source_ref_outside_root")
    candidate_value = raw_ref if raw_candidate.is_absolute() else str(root / raw_ref)
    candidate, candidate_info = _fixed_local_path_before_touch(
        candidate_value,
        code="dual_live_source_ref_unsafe",
    )
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise DualLiveEvaluationError("dual_live_source_ref_outside_root") from exc
    if any(component in {"", ".", ".."} for component in relative.parts):
        raise DualLiveEvaluationError("dual_live_source_ref_outside_root")
    if candidate_info is None or not stat.S_ISREG(candidate_info.st_mode):
        raise DualLiveEvaluationError("dual_live_source_blob_missing")
    payload = _stable_bounded_read(
        candidate,
        max_bytes=MAX_SOURCE_BYTES,
        size_code="dual_live_source_blob_size_invalid",
        unsafe_code="dual_live_source_ref_unsafe",
        changed_code="dual_live_source_blob_changed",
    )
    if not payload:
        raise DualLiveEvaluationError("dual_live_source_blob_size_invalid")
    return payload


def _source_blob(context: _EvidenceContext, raw_ref: str) -> bytes:
    return _source_blob_from_settings(context.settings, raw_ref)


def _check_c07_source_exemption(context: _EvidenceContext) -> CheckResult:
    check_id = "C07_SOURCE_EXEMPTION"
    blocked = _domain_error(context, check_id, "origin")
    if blocked:
        return blocked
    expected = tuple(
        sorted(
            (
                str(context.origins[key].get("raw_storage_ref") or ""),
                str(context.origins[key].get("raw_content_sha256") or ""),
            )
            for key in _EXPECTED_CONNECTORS
        )
    )
    if (
        len(context.source_exemptions) != 2
        or len(set(context.source_exemptions)) != 2
        or tuple(context.source_exemptions) != expected
        or any(
            not ref or not _LOWERCASE_SHA256.fullmatch(digest)
            for ref, digest in context.source_exemptions
        )
    ):
        return _fail_result(check_id, "c07_source_exemption_invalid")
    try:
        for raw_ref, expected_digest in context.source_exemptions:
            if hashlib.sha256(_source_blob(context, raw_ref)).hexdigest() != expected_digest:
                return _fail_result(check_id, "c07_source_blob_hash_mismatch")
    except (DualLiveEvaluationError, OSError):
        return _indeterminate(check_id, "c07_source_blob_unavailable")
    return _pass(check_id, exact_source_exemption_count=2)


def _check_c08_secret_scan(context: _EvidenceContext) -> CheckResult:
    check_id = "C08_SECRET_SCAN"
    blocked = _domain_error(context, check_id, "custody") or _domain_error(
        context, check_id, "capture"
    )
    if blocked:
        return blocked
    if (
        len(context.source_exemptions) != 2
        or len({raw_ref for raw_ref, _digest in context.source_exemptions}) != 2
        or any(
            not raw_ref or _LOWERCASE_SHA256.fullmatch(digest) is None
            for raw_ref, digest in context.source_exemptions
        )
    ):
        return _fail_result(check_id, "c08_source_scope_invalid")
    try:
        candidates = _forbidden_candidates(context, include_secret=True)
        payloads = (
            _db_scan_payloads(context)
            + context.non_source_files
            + _runtime_scan_payloads(context)
        )
        secret = str(context.settings.nrc_adams_subscription_key or "")
        secret_bytes = secret.encode("utf-8")
        if not secret_bytes:
            raise DualLiveEvaluationError("dual_live_secret_scan_key_missing")
        source_payloads_list: list[tuple[str, bytes]] = []
        for index, (raw_ref, expected_digest) in enumerate(
            context.source_exemptions,
            start=1,
        ):
            payload = _source_blob(context, raw_ref)
            if hashlib.sha256(payload).hexdigest() != expected_digest:
                return _fail_result(check_id, "c08_source_scope_invalid")
            source_payloads_list.append((f"source-{index}", payload))
        source_payloads = tuple(source_payloads_list)
    except DualLiveEvaluationError:
        return _indeterminate(check_id, "c08_secret_scan_indeterminate")
    scanned = _scan_check(
        context,
        check_id=check_id,
        payloads=payloads,
        candidates=candidates,
        strict_utf8=False,
        fail_code="c08_forbidden_secret_material",
    )
    if scanned.status != "PASS":
        return scanned
    for identity, payload in source_payloads:
        offset = payload.find(secret_bytes)
        if offset >= 0:
            return _fail_result(
                check_id,
                "c08_forbidden_secret_material",
                hit_count=1,
                first_hit_digest=hashlib.sha256(
                    _canonical_bytes(
                        {
                            "sink": identity,
                            "offset": offset,
                            "candidate_sha256": hashlib.sha256(secret_bytes).hexdigest(),
                        }
                    )
                ).hexdigest(),
            )
    return _pass(
        check_id,
        scanned_sink_count=(
            int(scanned.evidence.get("scanned_sink_count", 0))
            + len(source_payloads)
        ),
        hit_count=0,
    )


def _check_f01_evidence_stability(context: _EvidenceContext) -> CheckResult:
    check_id = "F01_EVIDENCE_STABILITY"
    blocked = _domain_error(context, check_id, "stability") or _domain_error(
        context, check_id, "capture"
    ) or _domain_error(context, check_id, "authority")
    if blocked:
        return blocked
    if (
        not context.initial_snapshot_sha256
        or not context.final_snapshot_sha256
        or context.initial_snapshot_sha256 != context.final_snapshot_sha256
    ):
        return _indeterminate(check_id, "f01_evidence_stability_mismatch")
    return _pass(check_id, protected_snapshot_count=2)


def _check_f02_database_stability(context: _EvidenceContext) -> CheckResult:
    check_id = "F02_DATABASE_STABILITY"
    blocked = _domain_error(context, check_id, "stability") or _domain_error(
        context, check_id, "custody"
    )
    if blocked:
        return blocked
    if (
        not context.initial_database_snapshot_sha256
        or not context.final_database_snapshot_sha256
        or context.initial_database_snapshot_sha256
        != context.final_database_snapshot_sha256
    ):
        return _indeterminate(check_id, "f02_database_stability_mismatch")
    return _pass(check_id, semantic_snapshot_count=2)


def _check_f03_nonclaims_report(context: _EvidenceContext) -> CheckResult:
    check_id = "F03_NONCLAIMS_REPORT"
    expected = (
        "offline local-experiment evidence only",
        "no external live acquisition performed by evaluation",
        "no signature or WORM custody claim",
        "no cryptographic nonrepudiation claim",
        "no owning-account compromise resistance claim",
        "no coherent all-domain rewrite detection claim",
        "no visibility into OS, proxy, provider, or machine-global logs",
        "no deployment or production readiness claim",
    )
    if EVALUATOR_NONCLAIMS != expected:
        return _fail_result(check_id, "f03_nonclaims_contract_invalid")
    return _pass(check_id, nonclaim_count=len(expected))


def _check_f04_read_only_evaluation(context: _EvidenceContext) -> CheckResult:
    check_id = "F04_READ_ONLY_EVALUATION"
    new = tuple(context.db.new)
    dirty = tuple(context.db.dirty)
    deleted = tuple(context.db.deleted)
    if new or dirty or deleted:
        return _fail_result(check_id, "f04_session_has_pending_writes")
    if (
        (
            context.initial_snapshot_sha256
            and context.final_snapshot_sha256
            and context.initial_snapshot_sha256 != context.final_snapshot_sha256
        )
        or (
            context.initial_database_snapshot_sha256
            and context.final_database_snapshot_sha256
            and context.initial_database_snapshot_sha256
            != context.final_database_snapshot_sha256
        )
    ):
        return _indeterminate(check_id, "f04_protected_state_changed")
    return _pass(check_id, pending_write_count=0)


def _check_f05_projection_rederivation(context: _EvidenceContext) -> CheckResult:
    check_id = "F05_PROJECTION_REDERIVATION"
    blocked = _domain_error(context, check_id, "origin") or _domain_error(
        context, check_id, "downstream"
    )
    if blocked:
        return blocked
    for connector_key in _EXPECTED_CONNECTORS:
        receipt = context.origins.get(connector_key)
        target = context.targets.get(connector_key)
        payloads = context.package_payloads.get(connector_key, ())
        if receipt is None or target is None or len(payloads) != 3:
            return _indeterminate(check_id, "f05_projection_domain_missing")
        if dict(_stored_origin_receipt(target) or {}) != dict(receipt):
            return _fail_result(check_id, "f05_stored_receipt_projection_changed")
        for payload in payloads:
            origin = payload.get("connector_origin_integrity_v1")
            if not isinstance(origin, Mapping) or (
                origin.get("connector_origin_receipt_hash")
                != receipt.get("receipt_hash")
                or origin.get("proof_class") != receipt.get("proof_class")
            ):
                return _fail_result(check_id, "f05_package_projection_changed")
    return _pass(check_id, rederived_projection_domain_count=4)


def _ast_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _ast_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _source_module_path(module_name: str, source_root: Path) -> Path | None:
    parts = module_name.split(".")
    if not parts or any(
        re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part) is None for part in parts
    ):
        return None
    for candidate in (
        source_root.joinpath(*parts).with_suffix(".py"),
        source_root.joinpath(*parts, "__init__.py"),
    ):
        path, info = _fixed_local_path_before_touch(
            candidate,
            code="dual_live_source_graph_unavailable",
        )
        if info is not None and stat.S_ISREG(info.st_mode):
            return path
    return None


def _resolve_import_from(
    node: ast.ImportFrom,
    *,
    current_module: str,
    current_is_package: bool,
) -> str:
    if node.level == 0:
        return node.module or ""
    package = current_module if current_is_package else current_module.rpartition(".")[0]
    parts = package.split(".") if package else []
    remove = node.level - 1
    if remove > len(parts):
        return ""
    prefix = parts[: len(parts) - remove] if remove else parts
    if node.module:
        prefix.extend(node.module.split("."))
    return ".".join(prefix)


def _literal_dynamic_import(
    node: ast.Call,
    *,
    current_module: str,
    current_is_package: bool,
) -> str:
    called = _ast_name(node.func)
    if called not in {"__import__", "importlib.import_module"} or not node.args:
        return ""
    value = node.args[0]
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        return ""
    imported = value.value
    if not imported.startswith("."):
        return imported
    level = len(imported) - len(imported.lstrip("."))
    pseudo = ast.ImportFrom(
        module=imported[level:] or None,
        names=[],
        level=level,
    )
    return _resolve_import_from(
        pseudo,
        current_module=current_module,
        current_is_package=current_is_package,
    )


def _reachable_source_imports(
    module_names: Sequence[str],
    *,
    source_root: Path,
) -> tuple[str, ...]:
    pending = list(module_names)
    discovered: set[str] = set()
    while pending:
        module_name = pending.pop()
        if not module_name or module_name in discovered:
            continue
        discovered.add(module_name)
        source_path = _source_module_path(module_name, source_root)
        if source_path is None:
            continue
        parts = module_name.split(".")
        for index in range(1, len(parts)):
            package = ".".join(parts[:index])
            package_path = _source_module_path(package, source_root)
            if package_path is not None and package not in discovered:
                pending.append(package)
        try:
            source = _stable_bounded_read(
                source_path,
                max_bytes=4 * 1024 * 1024,
                size_code="dual_live_source_graph_unavailable",
                unsafe_code="dual_live_source_graph_unavailable",
                changed_code="dual_live_source_graph_unavailable",
            ).decode("utf-8", errors="strict")
            tree = ast.parse(source)
        except (DualLiveEvaluationError, OSError, SyntaxError, UnicodeError) as exc:
            raise DualLiveEvaluationError("dual_live_source_graph_unavailable") from exc
        current_is_package = source_path.name == "__init__.py"
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = _resolve_import_from(
                    node,
                    current_module=module_name,
                    current_is_package=current_is_package,
                )
                if base:
                    imports.add(base)
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        candidate = f"{base}.{alias.name}"
                        if _source_module_path(candidate, source_root) is not None:
                            imports.add(candidate)
            elif isinstance(node, ast.Call):
                imported = _literal_dynamic_import(
                    node,
                    current_module=module_name,
                    current_is_package=current_is_package,
                )
                if imported:
                    imports.add(imported)
        pending.extend(sorted(imports - discovered, reverse=True))
    return tuple(sorted(discovered))


def _check_f06_no_egress_dependency(context: _EvidenceContext) -> CheckResult:
    check_id = "F06_NO_EGRESS_DEPENDENCY"
    try:
        source_path, source_info = _fixed_local_path_before_touch(
            __file__,
            code="dual_live_source_graph_unavailable",
        )
        if source_info is None or not stat.S_ISREG(source_info.st_mode):
            raise DualLiveEvaluationError("dual_live_source_graph_unavailable")
        source_root = source_path.parents[2]
        source = _stable_bounded_read(
            source_path,
            max_bytes=4 * 1024 * 1024,
            size_code="dual_live_source_graph_unavailable",
            unsafe_code="dual_live_source_graph_unavailable",
            changed_code="dual_live_source_graph_unavailable",
        ).decode("utf-8", errors="strict")
        tree = ast.parse(source)
    except (DualLiveEvaluationError, OSError, SyntaxError, UnicodeError):
        return _indeterminate(check_id, "f06_source_graph_unavailable")
    forbidden_imports = {
        "requests",
        "socket",
        "subprocess",
        "urllib.request",
        "http.client",
        "httpx",
        "aiohttp",
        "urllib3",
        "app.services.connector_campaign_log_capture",
        "app.services.connector_egress_authorization",
        "app.services.connector_egress_arming",
        "app.services.connector_egress_transport",
        "app.services.dual_live_runtime",
        "app.services.layer3_origin_continuity",
        "app.services.layer3_package_entry",
        "app.services.connectors_nrc_adams",
        "app.services.connectors_sciencebase",
        "app.services.sciencebase_connector",
    }
    forbidden_calls = (
        "create_connection",
        "getaddrinfo",
        "execute_connector",
        "mint_connector",
        "materialize_package",
        "submit_package",
        "prepare_handoff",
    )
    forbidden_connect_roots = {
        "aiohttp",
        "http",
        "httpx",
        "requests",
        "socket",
        "urllib",
        "urllib3",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name in forbidden_imports for alias in node.names):
                return _fail_result(check_id, "f06_egress_import_present")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "") in forbidden_imports:
                return _fail_result(check_id, "f06_egress_import_present")
        elif isinstance(node, ast.Call):
            called = _ast_name(node.func).casefold()
            called_parts = called.split(".")
            if called_parts[-1] in forbidden_calls or (
                called_parts[-1] == "connect"
                and called_parts[0] in forbidden_connect_roots
            ):
                return _fail_result(check_id, "f06_write_or_egress_call_present")
    try:
        closure = _reachable_source_imports(
            (
                "app.services.dual_live_evaluator",
                "app.services.connector_egress_evidence",
            ),
            source_root=source_root,
        )
    except DualLiveEvaluationError:
        return _indeterminate(check_id, "f06_source_graph_unavailable")
    if any(
        module == forbidden
        or module.startswith(f"{forbidden}.")
        for module in closure
        for forbidden in forbidden_imports
    ):
        return _fail_result(check_id, "f06_egress_import_present")
    return _pass(
        check_id,
        forbidden_dependency_count=0,
        inspected_module_count=len(closure),
    )


def _check_f07_public_api_contract(context: _EvidenceContext) -> CheckResult:
    check_id = "F07_PUBLIC_API_CONTRACT"
    signature = inspect.signature(evaluate_dual_live_proof)
    parameters = tuple(signature.parameters.values())
    if (
        tuple(item.name for item in parameters)
        != ("db", "campaign_id", "expected_campaign_fingerprint", "settings")
        or parameters[0].kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD
        or any(
            item.kind is not inspect.Parameter.KEYWORD_ONLY for item in parameters[1:]
        )
        or str(parameters[0].annotation) != "Session"
        or str(parameters[3].annotation) != "Settings"
        or str(signature.return_annotation) != "dict[str, Any]"
    ):
        return _fail_result(check_id, "f07_public_api_contract_invalid")
    return _pass(check_id, public_parameter_count=4)


def _check_f08_result_aggregation(context: _EvidenceContext) -> CheckResult:
    check_id = "F08_RESULT_AGGREGATION"
    if (
        len(CHECKS) != 69
        or len({function.__name__ for function in CHECKS}) != 69
        or tuple(
            function.__name__.removeprefix("_check_").upper()
            for function in CHECKS
        )
        != EVALUATOR_CHECK_ORDER
    ):
        return _fail_result(check_id, "f08_check_registry_invalid")
    passing = tuple(
        CheckResult(item, "PASS", f"{item.lower()}_pass")
        for item in EVALUATOR_CHECK_ORDER
    )
    failing = passing[:-1] + (
        CheckResult(EVALUATOR_CHECK_ORDER[-1], "FAIL", "f08_synthetic_fail"),
    )
    uncertain = failing[:-2] + (
        CheckResult(EVALUATOR_CHECK_ORDER[-2], "INDETERMINATE", "f08_uncertain"),
        failing[-1],
    )
    if (
        _aggregate_check_results(passing) != ("PASS", "all_checks_pass")
        or _aggregate_check_results(failing) != ("FAIL", "f08_synthetic_fail")
        or _aggregate_check_results(uncertain)
        != ("INDETERMINATE", "f08_uncertain")
    ):
        return _fail_result(check_id, "f08_aggregation_precedence_invalid")
    return _pass(check_id, registered_check_count=69)


def _connector_result_projection(
    context: _EvidenceContext,
    connector_key: str,
) -> Mapping[str, Any]:
    receipt = context.origins.get(connector_key)
    ledger = context.ledgers.get(connector_key)
    run = context.run_by_connector.get(connector_key)
    payloads = context.package_payloads.get(connector_key, ())
    if (
        not isinstance(receipt, Mapping)
        or ledger is None
        or run is None
        or len(payloads) != 3
        or receipt.get("connector_key") != connector_key
    ):
        raise DualLiveEvaluationError("f09_result_domains_invalid")
    run_id = getattr(run, "connector_run_id", None)
    receipt_hash = receipt.get("receipt_hash")
    raw_hash = receipt.get("raw_content_sha256")
    ledger_hash = getattr(ledger, "ledger_terminal_hash", None)
    target_id = receipt.get("connector_run_target_id")
    if (
        not isinstance(run_id, str)
        or not run_id
        or receipt.get("connector_run_id") != run_id
        or getattr(ledger, "connector_run_id", None) != run_id
        or not isinstance(target_id, str)
        or not target_id
        or not isinstance(receipt_hash, str)
        or not _LOWERCASE_SHA256.fullmatch(receipt_hash)
        or not isinstance(raw_hash, str)
        or not _LOWERCASE_SHA256.fullmatch(raw_hash)
        or not isinstance(ledger_hash, str)
        or not _LOWERCASE_SHA256.fullmatch(ledger_hash)
    ):
        raise DualLiveEvaluationError("f09_result_domains_invalid")
    boundaries = tuple(
        mapping.get(connector_key)
        for mapping in (
            context.output_integrity,
            context.review_states,
            context.package_commits,
            context.submit_states,
            context.handoff_states,
        )
    )
    if not all(isinstance(boundary, Mapping) for boundary in boundaries):
        raise DualLiveEvaluationError("f09_result_domains_invalid")

    payloads_by_kind: dict[str, Mapping[str, Any]] = {}
    for payload in payloads:
        header = payload.get("package_header")
        origin = payload.get("connector_origin_integrity_v1")
        if (
            not isinstance(header, Mapping)
            or not isinstance(origin, Mapping)
            or origin.get("connector_origin_receipt_hash") != receipt_hash
        ):
            raise DualLiveEvaluationError("f09_result_domains_invalid")
        kind = str(header.get("package_kind") or "")
        if kind in payloads_by_kind:
            raise DualLiveEvaluationError("f09_result_domains_invalid")
        payloads_by_kind[kind] = payload
    if set(payloads_by_kind) != set(_PACKAGE_KINDS):
        raise DualLiveEvaluationError("f09_result_domains_invalid")
    package_hashes = tuple(
        hashlib.sha256(_canonical_bytes(payloads_by_kind[kind])).hexdigest()
        for kind in _PACKAGE_KINDS
    )

    return MappingProxyType(
        {
            "schema_id": "project6.dual_live_connector_result.v1",
            "campaign_id": context.campaign_id,
            "campaign_fingerprint": context.campaign_fingerprint,
            "connector_key": connector_key,
            "connector_run_id": run_id,
            "connector_run_target_id": target_id,
            "origin_receipt_sha256": receipt_hash,
            "raw_content_sha256": raw_hash,
            "ledger_terminal_sha256": ledger_hash,
            "boundary_sha256": tuple(
                hashlib.sha256(_canonical_bytes(boundary)).hexdigest()
                for boundary in boundaries
            ),
            "package_payload_sha256": package_hashes,
        }
    )


def _check_f09_connector_and_combined_reports(
    context: _EvidenceContext,
) -> CheckResult:
    check_id = "F09_CONNECTOR_AND_COMBINED_REPORTS"
    blocked = next(
        (
            result
            for domain in (
                "origin",
                "execution",
                "review",
                "package_set",
                "submit",
                "handoff",
            )
            if (result := _domain_error(context, check_id, domain)) is not None
        ),
        None,
    )
    if blocked:
        return blocked
    required_maps = (
        context.origins,
        context.output_integrity,
        context.review_states,
        context.package_commits,
        context.submit_states,
        context.handoff_states,
        context.package_payloads,
    )
    if any(tuple(sorted(mapping)) != _EXPECTED_CONNECTORS for mapping in required_maps):
        return _fail_result(check_id, "f09_result_domains_invalid")
    if any(
        check(context).status != "PASS"
        for check in (
            _check_d03_layer3_execution,
            _check_d04_review_result,
            _check_d05_package_set,
            _check_d06_package_payload,
            _check_d07_submit_receipt,
            _check_d08_handoff_receipt,
        )
    ):
        return _fail_result(check_id, "f09_result_domains_invalid")
    try:
        projections = tuple(
            _connector_result_projection(context, connector_key)
            for connector_key in _EXPECTED_CONNECTORS
        )
    except DualLiveEvaluationError:
        return _fail_result(check_id, "f09_result_domains_invalid")
    connector_digests = tuple(
        hashlib.sha256(_canonical_bytes(projection)).hexdigest()
        for projection in projections
    )
    independent_fields = (
        "connector_run_id",
        "connector_run_target_id",
        "origin_receipt_sha256",
        "raw_content_sha256",
        "ledger_terminal_sha256",
    )
    if len(set(connector_digests)) != 2 or any(
        len({projection[field] for projection in projections}) != 2
        for field in independent_fields
    ):
        return _fail_result(check_id, "f09_result_domains_invalid")
    combined_projection = {
        "schema_id": "project6.dual_live_combined_result.v1",
        "campaign_id": context.campaign_id,
        "campaign_fingerprint": context.campaign_fingerprint,
        "connector_results": tuple(
            (connector_key, digest)
            for connector_key, digest in zip(
                _EXPECTED_CONNECTORS,
                connector_digests,
                strict=True,
            )
        ),
    }
    combined_digest = hashlib.sha256(
        _canonical_bytes(combined_projection)
    ).hexdigest()
    if combined_digest in connector_digests:
        return _fail_result(check_id, "f09_result_domains_invalid")
    return _pass(
        check_id,
        connector_results=tuple(
            {
                "connector_key": connector_key,
                "projection_sha256": digest,
            }
            for connector_key, digest in zip(
                _EXPECTED_CONNECTORS,
                connector_digests,
                strict=True,
            )
        ),
        combined_result={"projection_sha256": combined_digest},
    )


CHECKS: tuple[Callable[[_EvidenceContext], CheckResult], ...] = (
    _check_a01_input_identity,
    _check_a02_index_linear_head,
    _check_a03_archive_exact,
    _check_a04_slice_cardinality,
    _check_a05_selected_union,
    _check_a06_introduction_parity,
    _check_a07_marker_one_use,
    _check_a08_original_windows,
    _check_a09_code_campaign_fingerprints,
    _check_a10_proof_class,
    _check_r01_capture_membership,
    _check_r02_manifest_file_hashes,
    _check_r03_seal_parity,
    _check_r04_seal_event_parity,
    _check_r05_runtime_chain,
    _check_r06_startup_logger_census,
    _check_r07_exit_logger_census,
    _check_r08_phase_a_identity,
    _check_r09_phase_a_job_zero,
    _check_r10_phase_a_socket_quiescence,
    _check_r11_authority_cleared,
    _check_r12_phase_b_guards,
    _check_r13_phase_b_job_zero,
    _check_r14_runtime_terminal,
    _check_r15_wrapper_network_inert,
    _check_r16_phase_a_raw_only,
    _check_r17_phase_b_strict_flow,
    _check_r18_phase_a_terminal_once,
    _check_r19_a_to_b_order,
    _check_r20_four_stream_closeout,
    _check_r21_extant_run_seal_events,
    _check_r22_capture_start_contract,
    _check_l01_run_cardinality,
    _check_l02_terminal_event,
    _check_l03_post_terminal_extinction,
    _check_l04_ledger_reconstruction,
    _check_l05_counter_bijection,
    _check_l06_counter_boot,
    _check_l07_byte_allowance,
    _check_l08_request_cadence,
    _check_l09_transport_policy,
    _check_l10_fresh_200_bytes,
    _check_l11_nrc_first_binding,
    _check_l12_reservation_resolution,
    _check_d01_origin_receipt,
    _check_d02_raw_provenance_linkage,
    _check_d03_layer3_execution,
    _check_d04_review_result,
    _check_d05_package_set,
    _check_d06_package_payload,
    _check_d07_submit_receipt,
    _check_d08_handoff_receipt,
    _check_c01_strict_nulls,
    _check_c02_db_scalar_json_scan,
    _check_c03_non_source_file_scan,
    _check_c04_serialization_event_scan,
    _check_c05_runtime_log_scan,
    _check_c06_bounded_decoders,
    _check_c07_source_exemption,
    _check_c08_secret_scan,
    _check_f01_evidence_stability,
    _check_f02_database_stability,
    _check_f03_nonclaims_report,
    _check_f04_read_only_evaluation,
    _check_f05_projection_rederivation,
    _check_f06_no_egress_dependency,
    _check_f07_public_api_contract,
    _check_f08_result_aggregation,
    _check_f09_connector_and_combined_reports,
)


def _aggregate_check_results(
    results: Sequence[CheckResult],
) -> tuple[EvaluationStatus, str]:
    if (
        len(results) != len(EVALUATOR_CHECK_ORDER)
        or tuple(result.check_id for result in results) != EVALUATOR_CHECK_ORDER
    ):
        raise DualLiveEvaluationError("dual_live_check_result_registry_invalid")
    for result in results:
        if result.status == "INDETERMINATE":
            return "INDETERMINATE", result.code
    for result in results:
        if result.status == "FAIL":
            return "FAIL", result.code
    return "PASS", "all_checks_pass"


def _evaluation_report(
    *,
    campaign_id: str,
    expected_campaign_fingerprint: str,
    results: Sequence[CheckResult],
    forced_code: str | None = None,
) -> dict[str, Any]:
    status, aggregate_code = _aggregate_check_results(results)
    code = forced_code if forced_code is not None else aggregate_code
    return {
        "schema_id": "project6.dual_live_evaluation.v1",
        "campaign_id": campaign_id,
        "expected_campaign_fingerprint": expected_campaign_fingerprint,
        "status": status,
        "fresh_live": status == "PASS",
        "evaluation_complete": status in {"PASS", "FAIL"},
        "code": code,
        "checks": [result.as_dict() for result in results],
        "nonclaims": list(EVALUATOR_NONCLAIMS),
    }


def build_indeterminate_dual_live_report(
    *,
    campaign_id: str,
    expected_campaign_fingerprint: str,
    code: str,
) -> dict[str, Any]:
    _require_campaign_id(campaign_id)
    _require_campaign_fingerprint(expected_campaign_fingerprint)
    if not isinstance(code, str) or not re.fullmatch(r"[a-z0-9_]+", code):
        raise DualLiveEvaluationError("dual_live_result_code_invalid")
    results = tuple(
        CheckResult(
            check_id=check_id,
            status="INDETERMINATE",
            code=code,
            evidence={},
        )
        for check_id in EVALUATOR_CHECK_ORDER
    )
    return _evaluation_report(
        campaign_id=campaign_id,
        expected_campaign_fingerprint=expected_campaign_fingerprint,
        results=results,
        forced_code=code,
    )


def _run_dual_live_checks(
    db: Session,
    *,
    campaign_id: str,
    expected_campaign_fingerprint: str,
    settings: Settings,
) -> tuple[CheckResult, ...]:
    context = _collect_evidence(
        db,
        campaign_id=campaign_id,
        campaign_fingerprint=expected_campaign_fingerprint,
        settings=settings,
    )
    results_list: list[CheckResult] = []
    for check_id, check in zip(EVALUATOR_CHECK_ORDER, CHECKS, strict=True):
        try:
            result = check(context)
        except (
            AttributeError,
            IndexError,
            KeyError,
            StopIteration,
            TypeError,
            ValueError,
        ):
            result = _indeterminate(
                check_id,
                f"{check_id.lower()}_evidence_unavailable",
            )
        results_list.append(result)
    results = tuple(results_list)
    if tuple(result.check_id for result in results) != EVALUATOR_CHECK_ORDER:
        raise DualLiveEvaluationError("dual_live_check_result_registry_invalid")
    return results


def evaluate_dual_live_proof(
    db: Session,
    *,
    campaign_id: str,
    expected_campaign_fingerprint: str,
    settings: Settings,
) -> dict[str, Any]:
    _require_campaign_id(campaign_id)
    _require_campaign_fingerprint(expected_campaign_fingerprint)
    try:
        if tuple(db.new) or tuple(db.dirty) or tuple(db.deleted):
            return build_indeterminate_dual_live_report(
                campaign_id=campaign_id,
                expected_campaign_fingerprint=expected_campaign_fingerprint,
                code="dual_live_evaluation_pending_session_state",
            )
        with db.no_autoflush:
            results = _run_dual_live_checks(
                db,
                campaign_id=campaign_id,
                expected_campaign_fingerprint=expected_campaign_fingerprint,
                settings=settings,
            )
    except Exception:
        return build_indeterminate_dual_live_report(
            campaign_id=campaign_id,
            expected_campaign_fingerprint=expected_campaign_fingerprint,
            code="dual_live_evaluation_internal_error",
        )
    return _evaluation_report(
        campaign_id=campaign_id,
        expected_campaign_fingerprint=expected_campaign_fingerprint,
        results=results,
    )
