from __future__ import annotations

import hashlib
import inspect
import io
import json
import logging
import logging.handlers
import queue
import subprocess
import sys
import threading
import time
from contextlib import suppress
from pathlib import Path

import pytest

from app.services import dual_live_runtime as dual_live_runtime_module
from app.services.dual_live_evaluator import (
    DualLiveEvaluationError,
    evaluate_dual_live_proof,
)
from app.services.dual_live_runtime import (
    CHILD_CONTROL_SCHEMA_ID,
    MAX_CAPTURE_BYTES,
    MAX_FRAME_BYTES,
    MAX_FRAMES_PER_STREAM,
    MAX_STREAM_BYTES,
    CHILD_STATUS_SCHEMA_ID,
    RUNTIME_RECORD_KEYS,
    RUNTIME_SCHEMA_ID,
    WINDOWS_MIB_TCP_STATES,
    CampaignPipeHandler,
    CampaignPipeSink,
    FirstStopLatch,
    FourStreamPumpGroup,
    LockedCampaignSink,
    PhaseControlState,
    DualLiveRuntimeError,
    PipeFrameBudget,
    RuntimeIdentity,
    RuntimeRecordWriter,
    census_loggers,
    decode_child_status_frame,
    encode_child_control_frame,
    encode_child_status_frame,
    encode_pipe_frame,
    freeze_logger_topology,
    read_pipe_frame,
    read_runtime_records,
)
from app.services.connector_egress_authorization import canonical_json_bytes


BACKEND = Path(__file__).resolve().parents[1]
CAMPAIGN_ID = "123e4567-e89b-42d3-a456-426614174000"
CAMPAIGN_FINGERPRINT = "a" * 64
STATUS_PROCESS_BOOT_ID = "b" * 64
STATUS_NONCE_SHA256 = "c" * 64
EXPECTED_REPORT = {
    "schema_id": "project6.dual_live_evaluation.v1",
    "campaign_id": CAMPAIGN_ID,
    "expected_campaign_fingerprint": CAMPAIGN_FINGERPRINT,
    "status": "INDETERMINATE",
    "fresh_live": False,
    "evaluation_complete": False,
    "code": "tracked_s3_clearance_and_privileged_runner_required",
    "blocking_dependencies": [
        "tracked_external_s3_clause_5_clearance",
        "privileged_dual_live_runner",
    ],
    "validated_surfaces": [],
    "nonclaims": [
        "no campaign evidence evaluated",
        "no connector run executed",
        "no live acquisition performed",
        "no Layer 3 continuity verdict",
        "no package or handoff verdict",
        "no production readiness claim",
    ],
}
RUNTIME_INSTANCE_ID = "223e4567-e89b-42d3-a456-426614174000"
BOOT_ID = "7" * 64
UUID_BOOT_ID = "323e4567-e89b-42d3-a456-426614174000"
RUNTIME_IDENTITY = RuntimeIdentity(
    runtime_instance_id=RUNTIME_INSTANCE_ID,
    wrapper_nonce_sha256="1" * 64,
    code_revision="2" * 40,
    wrapper_image_sha256="3" * 64,
    interpreter_image_sha256="4" * 64,
    root_mutex_identity_sha256="5" * 64,
    campaign_mutex_identity_sha256="6" * 64,
)
RUNTIME_START_PAYLOAD = {
    "code_revision": RUNTIME_IDENTITY.code_revision,
    "wrapper_image_sha256": RUNTIME_IDENTITY.wrapper_image_sha256,
    "interpreter_image_sha256": RUNTIME_IDENTITY.interpreter_image_sha256,
    "mutex_identity_sha256": "7" * 64,
}
CHILD_START_PAYLOAD = {
    "process_creation_identity_sha256": "8" * 64,
    "executable_sha256": "9" * 64,
    "job_policy_sha256": "a" * 64,
}
ZERO_TCP_STATE_COUNTS = {state: 0 for state in WINDOWS_MIB_TCP_STATES}
VALID_RUNTIME_EVENT_CASES = (
    ("wrapper", "runtime_start", None, RUNTIME_START_PAYLOAD),
    ("A", "phase_child_start", BOOT_ID, CHILD_START_PAYLOAD),
    (
        "A",
        "logger_census",
        BOOT_ID,
        {
            "census_point": "pre_activity",
            "topology_sha256": "b" * 64,
            "handler_count": 1,
            "guard_state": "A_CENSUS_OK",
            "topology_matches_initial": True,
        },
    ),
    (
        "A",
        "phase_go",
        BOOT_ID,
        {
            "prior_state": "A_CENSUS_OK",
            "next_state": "A_GO",
            "control_nonce_sha256": "c" * 64,
        },
    ),
    (
        "wrapper",
        "stop_latched",
        None,
        {"reason_code": "protocol_failure", "monotonic_tick_ns": 0},
    ),
    (
        "A",
        "socket_census",
        BOOT_ID,
        {
            "tcp4_state_counts": ZERO_TCP_STATE_COUNTS,
            "tcp6_state_counts": ZERO_TCP_STATE_COUNTS,
            "udp4_count": 0,
            "udp6_count": 0,
            "process_identity_sha256": "d" * 64,
            "stable": True,
        },
    ),
    (
        "A",
        "job_zero",
        BOOT_ID,
        {"active_process_count": 0, "process_list_sha256": "e" * 64},
    ),
    (
        "A",
        "authority_cleared",
        BOOT_ID,
        {"authority_posture_sha256": "f" * 64, "all_required_absent": True},
    ),
    (
        "A",
        "phase_complete",
        BOOT_ID,
        {"terminal_state": "completed", "exit_code": 0},
    ),
    (
        "wrapper",
        "runtime_complete",
        None,
        {
            "phase_a_result_sha256": "0" * 64,
            "phase_b_result_sha256": "1" * 64,
            "terminal_state": "completed",
        },
    ),
)


class NoAccess:
    def __getattribute__(self, name: str) -> object:
        raise AssertionError(f"unexpected dependency access: {name}")


class MemorySink(io.BytesIO):
    def bytes(self) -> bytes:
        return self.getvalue()


def _pipe_handler(
    pipe_token: str,
    writer: MemorySink | None = None,
) -> CampaignPipeHandler:
    actual_writer = writer if writer is not None else MemorySink()
    return CampaignPipeHandler(
        pipe_token,
        CampaignPipeSink(pipe_token, actual_writer),
    )


class NamedFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return True


class ReplacementFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return True


class ExitCensusMutationLogger(logging.Logger):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.mutate_on_census = False
        self.mutation_denied = False

    def getEffectiveLevel(self) -> int:
        if self.mutate_on_census:
            self.mutate_on_census = False
            try:
                self.addFilter(ReplacementFilter())
            except DualLiveRuntimeError as exc:
                if exc.code != "dual_live_logger_topology_frozen":
                    raise
                self.mutation_denied = True
        return super().getEffectiveLevel()


class ArbitraryHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        return None


def test_r06_pipe_handler_rejects_arbitrary_callback_even_with_allowed_token() -> None:
    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_logger_pipe_handler_invalid",
    ):
        CampaignPipeHandler("app-pipe", MemorySink().write)

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_logger_pipe_handler_invalid",
    ):
        CampaignPipeHandler(
            "app-pipe",
            CampaignPipeSink("other-pipe", MemorySink()),
        )


@pytest.fixture
def isolated_logging(monkeypatch: pytest.MonkeyPatch) -> logging.RootLogger:
    root = logging.RootLogger(logging.WARNING)
    manager = logging.Manager(root)
    root.manager = manager
    monkeypatch.setattr(logging, "root", root)
    monkeypatch.setattr(logging.Logger, "root", root)
    monkeypatch.setattr(logging.Logger, "manager", manager)
    monkeypatch.setattr(logging, "lastResort", None)
    return root


def _evaluate(
    *,
    campaign_id: str = CAMPAIGN_ID,
    campaign_fingerprint: str = CAMPAIGN_FINGERPRINT,
) -> dict[str, object]:
    return evaluate_dual_live_proof(
        NoAccess(),
        campaign_id=campaign_id,
        expected_campaign_fingerprint=campaign_fingerprint,
        settings=NoAccess(),
    )


def test_signature_is_the_public_keyword_only_contract() -> None:
    signature = inspect.signature(evaluate_dual_live_proof)

    assert list(signature.parameters) == [
        "db",
        "campaign_id",
        "expected_campaign_fingerprint",
        "settings",
    ]
    assert signature.parameters["db"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert signature.parameters["campaign_id"].kind is inspect.Parameter.KEYWORD_ONLY
    assert (
        signature.parameters["expected_campaign_fingerprint"].kind
        is inspect.Parameter.KEYWORD_ONLY
    )
    assert signature.parameters["settings"].kind is inspect.Parameter.KEYWORD_ONLY
    assert str(signature.parameters["db"].annotation) == "Session"
    assert str(signature.parameters["settings"].annotation) == "Settings"
    assert str(signature.return_annotation) == "dict[str, Any]"


def test_valid_inputs_return_exact_ordered_indeterminate_report() -> None:
    report = _evaluate()

    assert report == EXPECTED_REPORT
    assert list(report) == list(EXPECTED_REPORT)
    assert report is not EXPECTED_REPORT
    assert report["blocking_dependencies"] is not EXPECTED_REPORT["blocking_dependencies"]
    assert report["nonclaims"] is not EXPECTED_REPORT["nonclaims"]


def test_evaluation_is_repeatable_and_does_not_reuse_mutable_values() -> None:
    first = _evaluate()
    second = _evaluate()

    assert first == second == EXPECTED_REPORT
    assert first is not second
    assert first["blocking_dependencies"] is not second["blocking_dependencies"]
    assert first["validated_surfaces"] is not second["validated_surfaces"]
    assert first["nonclaims"] is not second["nonclaims"]


@pytest.mark.parametrize(
    "campaign_id",
    [
        "",
        " ",
        f" {CAMPAIGN_ID}",
        f"{CAMPAIGN_ID} ",
        CAMPAIGN_ID.upper(),
        "123e4567-e89b-12d3-a456-426614174000",
        "{123e4567-e89b-42d3-a456-426614174000}",
        "urn:uuid:123e4567-e89b-42d3-a456-426614174000",
        "123e4567e89b42d3a456426614174000",
        "not-a-uuid",
    ],
)
def test_campaign_id_must_be_strict_canonical_lowercase_uuid4(
    campaign_id: str,
) -> None:
    with pytest.raises(DualLiveEvaluationError) as caught:
        _evaluate(campaign_id=campaign_id)

    assert caught.value.code == "dual_live_campaign_id_invalid"


@pytest.mark.parametrize(
    "campaign_fingerprint",
    [
        "",
        " ",
        f" {CAMPAIGN_FINGERPRINT}",
        f"{CAMPAIGN_FINGERPRINT} ",
        "A" * 64,
        "a" * 63,
        "a" * 65,
        ("a" * 63) + "g",
    ],
)
def test_campaign_fingerprint_must_be_strict_lowercase_sha256_hex(
    campaign_fingerprint: str,
) -> None:
    with pytest.raises(DualLiveEvaluationError) as caught:
        _evaluate(campaign_fingerprint=campaign_fingerprint)

    assert caught.value.code == "dual_live_campaign_fingerprint_invalid"


def test_no_report_value_claims_positive_authority() -> None:
    serialized_values = json.dumps(list(_evaluate().values())).lower()

    for forbidden_claim in (
        '"pass"',
        '"complete"',
        '"valid"',
        '"fresh"',
        '"accepted"',
        '"ready"',
    ):
        assert forbidden_claim not in serialized_values


def test_import_is_inert_and_avoids_runtime_app_dependencies() -> None:
    probe = """
import json
import sys
import app.services.dual_live_evaluator
forbidden = [
    name for name in (
        "app.core.config",
        "app.db.session",
        "sqlalchemy",
    )
    if name in sys.modules
]
print(json.dumps(forbidden))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=BACKEND,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "[]\n"
    assert completed.stderr == ""


def test_r05_runtime_records_form_exact_canonical_hash_chain() -> None:
    sink = MemorySink()
    writer = RuntimeRecordWriter(sink.write, identity=RUNTIME_IDENTITY)

    first = writer.append(
        phase="wrapper",
        event="runtime_start",
        process_boot_id=None,
        payload=RUNTIME_START_PAYLOAD,
    )
    second = writer.append(
        phase="A",
        event="phase_child_start",
        process_boot_id=BOOT_ID,
        payload=CHILD_START_PAYLOAD,
    )

    assert tuple(first) == RUNTIME_RECORD_KEYS
    assert tuple(second) == RUNTIME_RECORD_KEYS
    assert first["schema_id"] == RUNTIME_SCHEMA_ID
    assert first["ordinal"] == 1
    assert first["previous_record_sha256"] is None
    assert second["ordinal"] == 2
    assert second["previous_record_sha256"] == first["record_sha256"]
    assert sink.bytes() == (
        canonical_json_bytes(first)
        + b"\n"
        + canonical_json_bytes(second)
        + b"\n"
    )
    assert read_runtime_records(sink.bytes()) == (first, second)


def _rehashed_phase_child_start_record(process_boot_id: str) -> dict[str, object]:
    record = RuntimeRecordWriter(
        MemorySink().write,
        identity=RUNTIME_IDENTITY,
    ).append(
        phase="wrapper",
        event="runtime_start",
        process_boot_id=None,
        payload=RUNTIME_START_PAYLOAD,
    )
    record["phase"] = "A"
    record["event"] = "phase_child_start"
    record["process_boot_id"] = process_boot_id
    record["payload"] = CHILD_START_PAYLOAD
    preimage = {key: value for key, value in record.items() if key != "record_sha256"}
    record["record_sha256"] = hashlib.sha256(
        canonical_json_bytes(preimage)
    ).hexdigest()
    return record


def test_r05_runtime_writer_accepts_lowercase_sha256_process_boot_id() -> None:
    record = RuntimeRecordWriter(
        MemorySink().write,
        identity=RUNTIME_IDENTITY,
    ).append(
        phase="A",
        event="phase_child_start",
        process_boot_id=BOOT_ID,
        payload=CHILD_START_PAYLOAD,
    )

    assert record["process_boot_id"] == BOOT_ID


@pytest.mark.parametrize("process_boot_id", (UUID_BOOT_ID, "A" * 64, "a" * 63))
def test_r05_runtime_writer_rejects_non_hash_process_boot_id(
    process_boot_id: str,
) -> None:
    writer = RuntimeRecordWriter(MemorySink().write, identity=RUNTIME_IDENTITY)

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_runtime_process_boot_id_invalid",
    ):
        writer.append(
            phase="A",
            event="phase_child_start",
            process_boot_id=process_boot_id,
            payload=CHILD_START_PAYLOAD,
        )


def test_r05_runtime_reader_accepts_lowercase_sha256_process_boot_id() -> None:
    record = _rehashed_phase_child_start_record(BOOT_ID)

    parsed = read_runtime_records(canonical_json_bytes(record) + b"\n")

    assert parsed[0]["process_boot_id"] == BOOT_ID


@pytest.mark.parametrize("process_boot_id", (UUID_BOOT_ID, "A" * 64, "a" * 63))
def test_r05_runtime_reader_rejects_non_hash_process_boot_id(
    process_boot_id: str,
) -> None:
    record = _rehashed_phase_child_start_record(process_boot_id)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_runtime_record_invalid"):
        read_runtime_records(canonical_json_bytes(record) + b"\n")


@pytest.mark.parametrize(
    ("phase", "event", "process_boot_id", "payload"),
    VALID_RUNTIME_EVENT_CASES,
)
def test_r05_runtime_record_event_union_accepts_exact_payloads(
    phase: str,
    event: str,
    process_boot_id: str | None,
    payload: dict[str, object],
) -> None:
    record = RuntimeRecordWriter(
        MemorySink().write,
        identity=RUNTIME_IDENTITY,
    ).append(
        phase=phase,
        event=event,
        process_boot_id=process_boot_id,
        payload=payload,
    )

    assert record["event"] == event
    assert record["payload"] == payload


def test_r05_job_zero_rejects_bool_false_as_active_process_count() -> None:
    writer = RuntimeRecordWriter(MemorySink().write, identity=RUNTIME_IDENTITY)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_runtime_payload_invalid"):
        writer.append(
            phase="A",
            event="job_zero",
            process_boot_id=BOOT_ID,
            payload={
                "active_process_count": False,
                "process_list_sha256": "e" * 64,
            },
        )


def test_r05_runtime_event_phase_matrix_rejects_cross_phase_records() -> None:
    writer = RuntimeRecordWriter(MemorySink().write, identity=RUNTIME_IDENTITY)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_runtime_phase_invalid"):
        writer.append(
            phase="wrapper",
            event="phase_child_start",
            process_boot_id=None,
            payload=CHILD_START_PAYLOAD,
        )
    with pytest.raises(DualLiveRuntimeError, match="dual_live_runtime_phase_invalid"):
        writer.append(
            phase="A",
            event="stop_latched",
            process_boot_id=BOOT_ID,
            payload={"reason_code": "protocol_failure", "monotonic_tick_ns": 0},
        )
    with pytest.raises(DualLiveRuntimeError, match="dual_live_runtime_phase_invalid"):
        writer.append(
            phase="B",
            event="phase_go",
            process_boot_id=BOOT_ID,
            payload={
                "prior_state": "A_CENSUS_OK",
                "next_state": "A_GO",
                "control_nonce_sha256": "c" * 64,
            },
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("runtime_instance_id", CAMPAIGN_ID.upper()),
        ("wrapper_nonce_sha256", "A" * 64),
        ("code_revision", "2" * 39),
        ("wrapper_image_sha256", "3" * 63),
    ],
)
def test_r05_runtime_identity_requires_canonical_uuid_and_hashes(
    field: str,
    value: str,
) -> None:
    identity = {
        "runtime_instance_id": RUNTIME_INSTANCE_ID,
        "wrapper_nonce_sha256": "1" * 64,
        "code_revision": "2" * 40,
        "wrapper_image_sha256": "3" * 64,
        "interpreter_image_sha256": "4" * 64,
        "root_mutex_identity_sha256": "5" * 64,
        "campaign_mutex_identity_sha256": "6" * 64,
    }
    identity[field] = value

    with pytest.raises(DualLiveRuntimeError, match="dual_live_runtime_identity_invalid"):
        RuntimeIdentity(**identity)


def test_r05_runtime_record_union_rejects_unknown_extra_and_unsafe_fields() -> None:
    writer = RuntimeRecordWriter(MemorySink().write, identity=RUNTIME_IDENTITY)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_runtime_event_invalid"):
        writer.append(
            phase="wrapper",
            event="runtime_unknown",
            process_boot_id=None,
            payload={},
        )
    with pytest.raises(DualLiveRuntimeError, match="dual_live_runtime_payload_invalid"):
        writer.append(
            phase="wrapper",
            event="runtime_start",
            process_boot_id=None,
            payload={**RUNTIME_START_PAYLOAD, "extra": True},
        )
    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_runtime_payload_unsafe_field",
    ):
        writer.append(
            phase="wrapper",
            event="runtime_start",
            process_boot_id=None,
            payload={**RUNTIME_START_PAYLOAD, "secret_value": "never"},
        )


def test_r05_runtime_start_must_match_bound_runtime_identity() -> None:
    writer = RuntimeRecordWriter(MemorySink().write, identity=RUNTIME_IDENTITY)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_runtime_identity_mismatch"):
        writer.append(
            phase="wrapper",
            event="runtime_start",
            process_boot_id=None,
            payload={**RUNTIME_START_PAYLOAD, "code_revision": "3" * 40},
        )


def test_r05_runtime_reader_rejects_rehashed_invalid_event_phase() -> None:
    record = RuntimeRecordWriter(
        MemorySink().write,
        identity=RUNTIME_IDENTITY,
    ).append(
        phase="wrapper",
        event="runtime_start",
        process_boot_id=None,
        payload=RUNTIME_START_PAYLOAD,
    )
    record["phase"] = "A"
    record["process_boot_id"] = BOOT_ID
    preimage = {key: value for key, value in record.items() if key != "record_sha256"}
    record["record_sha256"] = hashlib.sha256(
        canonical_json_bytes(preimage)
    ).hexdigest()

    with pytest.raises(DualLiveRuntimeError, match="dual_live_runtime_record_invalid"):
        read_runtime_records(canonical_json_bytes(record) + b"\n")


def test_r05_runtime_reader_rejects_rehashed_phase_go_edge_mismatch() -> None:
    record = RuntimeRecordWriter(
        MemorySink().write,
        identity=RUNTIME_IDENTITY,
    ).append(
        phase="A",
        event="phase_go",
        process_boot_id=BOOT_ID,
        payload={
            "prior_state": "A_CENSUS_OK",
            "next_state": "A_GO",
            "control_nonce_sha256": "c" * 64,
        },
    )
    record["phase"] = "B"
    preimage = {key: value for key, value in record.items() if key != "record_sha256"}
    record["record_sha256"] = hashlib.sha256(
        canonical_json_bytes(preimage)
    ).hexdigest()

    with pytest.raises(DualLiveRuntimeError, match="dual_live_runtime_record_invalid"):
        read_runtime_records(canonical_json_bytes(record) + b"\n")


def test_r05_pipe_frame_accepts_exact_64_kib_and_clean_eof() -> None:
    payload = b"x" * MAX_FRAME_BYTES
    encoded = encode_pipe_frame(payload)

    assert encoded[:4] == MAX_FRAME_BYTES.to_bytes(4, "big")
    assert encoded[4:] == payload
    assert read_pipe_frame(io.BytesIO(encoded)) == payload
    assert read_pipe_frame(io.BytesIO()) is None


@pytest.mark.parametrize(
    "framed",
    [
        b"\x00\x00",
        (3).to_bytes(4, "big") + b"xx",
    ],
)
def test_r05_pipe_frame_rejects_partial_prefix_or_body(framed: bytes) -> None:
    with pytest.raises(DualLiveRuntimeError, match="dual_live_frame_unexpected_eof"):
        read_pipe_frame(io.BytesIO(framed))


def test_r05_pipe_frame_rejects_empty_oversized_and_invalid_utf8() -> None:
    with pytest.raises(DualLiveRuntimeError, match="dual_live_frame_empty"):
        encode_pipe_frame(b"")
    with pytest.raises(DualLiveRuntimeError, match="dual_live_frame_oversized"):
        encode_pipe_frame(b"x" * (MAX_FRAME_BYTES + 1))
    with pytest.raises(DualLiveRuntimeError, match="dual_live_frame_oversized"):
        read_pipe_frame(
            io.BytesIO((MAX_FRAME_BYTES + 1).to_bytes(4, "big") + b"x")
        )
    with pytest.raises(DualLiveRuntimeError, match="dual_live_frame_invalid_utf8"):
        encode_pipe_frame(b"\xff")
    with pytest.raises(DualLiveRuntimeError, match="dual_live_frame_invalid_utf8"):
        read_pipe_frame(io.BytesIO((1).to_bytes(4, "big") + b"\xff"))


def test_r05_pipe_frame_rejects_child_selected_reserved_runtime_schema() -> None:
    payload = canonical_json_bytes({"schema_id": RUNTIME_SCHEMA_ID})
    framed = len(payload).to_bytes(4, "big") + payload

    with pytest.raises(DualLiveRuntimeError, match="dual_live_child_reserved_schema"):
        read_pipe_frame(io.BytesIO(framed))


def test_r05_pipe_budget_enforces_fixed_stream_frame_and_aggregate_caps() -> None:
    assert MAX_STREAM_BYTES == 16 * 1024 * 1024
    assert MAX_CAPTURE_BYTES == 32 * 1024 * 1024
    budget = PipeFrameBudget()
    frames_per_stream = MAX_STREAM_BYTES // MAX_FRAME_BYTES
    for stream in ("app", "http"):
        for _ in range(frames_per_stream):
            budget.consume(stream, MAX_FRAME_BYTES)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_aggregate_bytes"):
        budget.consume("stdout", 1)

    frame_budget = PipeFrameBudget()
    for _ in range(MAX_FRAMES_PER_STREAM):
        frame_budget.consume("stderr", 1)
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_frame_count"):
        frame_budget.consume("stderr", 1)


def test_pipe_budget_charges_emitted_newlines_and_wrapper_bytes_exactly() -> None:
    budget = PipeFrameBudget()
    newline_payload_bytes = MAX_FRAME_BYTES - 1
    for _ in range(MAX_STREAM_BYTES // MAX_FRAME_BYTES):
        budget.consume(
            "app",
            newline_payload_bytes,
            emitted_bytes=MAX_FRAME_BYTES,
        )

    with pytest.raises(
        DualLiveRuntimeError, match="dual_live_pump_stream_bytes_exceeded"
    ):
        budget.consume("app", 1, emitted_bytes=2)

    wrapper_budget = PipeFrameBudget()
    wrapper_budget.consume_wrapper("app", MAX_STREAM_BYTES)
    with pytest.raises(
        DualLiveRuntimeError, match="dual_live_pump_stream_bytes_exceeded"
    ):
        wrapper_budget.consume_wrapper("app", 1)


def test_pumps_charge_http_newline_and_wrapper_app_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dual_live_runtime_module, "MAX_STREAM_BYTES", 4)
    monkeypatch.setattr(dual_live_runtime_module, "MAX_CAPTURE_BYTES", 8)

    def make_group(
        http_frames: bytes = b"",
    ) -> tuple[FourStreamPumpGroup, dict[str, MemorySink]]:
        readers = {
            "app": io.BytesIO(),
            "http": io.BytesIO(http_frames),
            "stdout": io.BytesIO(),
            "stderr": io.BytesIO(),
        }
        writers = {stream: MemorySink() for stream in readers}
        return (
            FourStreamPumpGroup(
                readers=readers,
                writers=writers,
                status_callback=lambda _value: None,
                http_frame_validator=lambda _value: None,
                stop_latch=FirstStopLatch(),
                expected_status_phase="A",
                expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
                expected_status_nonce_sha256=STATUS_NONCE_SHA256,
            ),
            writers,
        )

    exact, exact_writers = make_group(encode_pipe_frame(b"abc"))
    exact.start()
    exact.join(timeout=2)
    assert exact_writers["http"].bytes() == b"abc\n"

    overflow, overflow_writers = make_group(
        encode_pipe_frame(b"abc") + encode_pipe_frame(b"x")
    )
    overflow.start()
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_failed") as exc:
        overflow.join(timeout=2)
    assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
    assert exc.value.__cause__.code == "dual_live_pump_stream_bytes_exceeded"
    assert overflow_writers["http"].bytes() == b"abc\n"

    wrapper, wrapper_writers = make_group()
    assert wrapper.app_write(b"1234") == 4
    with pytest.raises(
        DualLiveRuntimeError, match="dual_live_pump_stream_bytes_exceeded"
    ):
        wrapper.app_write(b"x")
    assert wrapper_writers["app"].bytes() == b"1234"


def test_r06_logger_census_projects_root_real_placeholder_and_last_resort(
    isolated_logging: logging.RootLogger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    isolated_logging.handlers.clear()
    secret = "never-project-pipe-callable-state"
    sink = MemorySink()
    root_handler = _pipe_handler("app-pipe", sink)
    root_handler.setLevel(logging.INFO)
    root_handler.setFormatter(logging.Formatter("%(message)s"))
    root_handler.addFilter(NamedFilter())
    isolated_logging.addHandler(root_handler)
    isolated_logging.addFilter(NamedFilter())

    real_logger = logging.getLogger("task8.real")
    real_logger.disabled = True
    real_logger.setLevel(logging.DEBUG)
    real_logger.propagate = False
    real_logger.addFilter(NamedFilter())
    real_logger.addHandler(_pipe_handler("http-pipe", sink))
    logging.getLogger("task8.placeholder.child")
    last_resort = _pipe_handler("last-pipe", sink)
    monkeypatch.setattr(logging, "lastResort", last_resort)

    census = census_loggers(frozenset(("app-pipe", "http-pipe", "last-pipe")))

    assert tuple(census) == (
        "schema_id",
        "loggers",
        "last_resort",
        "handler_count",
        "topology_sha256",
    )
    assert census["schema_id"] == "project6.dual_live_logger_topology.v1"
    assert census["handler_count"] == 3
    assert census["loggers"][0] == {
        "name": "",
        "kind": "root",
        "disabled": False,
        "level": logging.WARNING,
        "effective_level": logging.WARNING,
        "propagate": True,
        "filters": [f"{NamedFilter.__module__}.{NamedFilter.__qualname__}"],
        "handlers": [
            {
                "type_id": (
                    "app.services.dual_live_runtime.CampaignPipeHandler"
                ),
                "pipe_token": "app-pipe",
                "level": logging.INFO,
                "formatter_type_id": "logging.Formatter",
                "filters": [
                    f"{NamedFilter.__module__}.{NamedFilter.__qualname__}"
                ],
            }
        ],
    }
    entries = {entry["name"]: entry for entry in census["loggers"]}
    assert entries["task8.real"]["kind"] == "logger"
    assert entries["task8.real"]["disabled"] is True
    assert entries["task8.real"]["effective_level"] == logging.DEBUG
    assert entries["task8.real"]["propagate"] is False
    assert entries["task8"]["kind"] == "placeholder"
    assert entries["task8.placeholder"]["kind"] == "placeholder"
    assert census["last_resort"]["pipe_token"] == "last-pipe"
    preimage = {key: value for key, value in census.items() if key != "topology_sha256"}
    assert census["topology_sha256"] == hashlib.sha256(
        canonical_json_bytes(preimage)
    ).hexdigest()
    assert secret not in json.dumps(census, sort_keys=True)
    with pytest.raises(AttributeError):
        root_handler.pipe_token = "changed"


def test_r06_logger_census_allows_only_sinkless_exact_null_handler(
    isolated_logging: logging.RootLogger,
) -> None:
    isolated_logging.handlers.clear()
    isolated_logging.addHandler(logging.NullHandler())

    census = census_loggers(frozenset())

    handler = census["loggers"][0]["handlers"][0]
    assert handler == {
        "type_id": "logging.NullHandler",
        "pipe_token": None,
        "level": logging.NOTSET,
        "formatter_type_id": None,
        "filters": [],
    }


def test_r06_logger_census_rejects_forbidden_handler_classes(
    isolated_logging: logging.RootLogger,
    tmp_path: Path,
) -> None:
    event_log_handler = object.__new__(logging.handlers.NTEventLogHandler)
    logging.Handler.__init__(event_log_handler)
    handlers = [
        logging.FileHandler(tmp_path / "forbidden.log"),
        logging.StreamHandler(io.StringIO()),
        logging.handlers.QueueHandler(queue.SimpleQueue()),
        logging.handlers.MemoryHandler(1),
        logging.handlers.SocketHandler("127.0.0.1", 1),
        logging.handlers.HTTPHandler("example.invalid", "/"),
        logging.handlers.SMTPHandler(
            ("example.invalid", 25),
            "sender@example.invalid",
            "recipient@example.invalid",
            "subject",
        ),
        event_log_handler,
        ArbitraryHandler(),
    ]
    try:
        for handler in handlers:
            isolated_logging.handlers[:] = [handler]
            with pytest.raises(
                DualLiveRuntimeError,
                match="dual_live_logger_handler_invalid",
            ):
                census_loggers(frozenset())
    finally:
        for handler in handlers:
            handler.close()


def test_r06_logger_census_rejects_unknown_last_resort_and_placeholder_state(
    isolated_logging: logging.RootLogger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    isolated_logging.handlers.clear()
    monkeypatch.setattr(logging, "lastResort", logging.StreamHandler(io.StringIO()))
    with pytest.raises(DualLiveRuntimeError, match="dual_live_logger_handler_invalid"):
        census_loggers(frozenset())

    monkeypatch.setattr(logging, "lastResort", None)
    logging.Logger.manager.loggerDict["task8.invalid"] = object()
    with pytest.raises(DualLiveRuntimeError, match="dual_live_logger_entry_invalid"):
        census_loggers(frozenset())


def test_r06_logger_census_rejects_duplicate_or_unknown_pipe_destination(
    isolated_logging: logging.RootLogger,
) -> None:
    isolated_logging.handlers.clear()
    isolated_logging.addHandler(_pipe_handler("same-pipe"))
    child = logging.getLogger("task8.child")
    child.addHandler(_pipe_handler("same-pipe"))

    with pytest.raises(DualLiveRuntimeError, match="dual_live_logger_duplicate_pipe"):
        census_loggers(frozenset(("same-pipe",)))

    child.handlers.clear()
    with pytest.raises(DualLiveRuntimeError, match="dual_live_logger_pipe_token_invalid"):
        census_loggers(frozenset(("different-pipe",)))


def test_r06_logger_census_rejects_broken_handler_sink_identity(
    isolated_logging: logging.RootLogger,
) -> None:
    isolated_logging.handlers.clear()
    handler = _pipe_handler("app-pipe")
    handler._sink = CampaignPipeSink("app-pipe", MemorySink())
    isolated_logging.addHandler(handler)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_logger_pipe_binding_invalid"):
        census_loggers(frozenset(("app-pipe",)))


def test_r07_logger_freeze_blocks_normal_mutation_and_rechecks_exact_topology(
    isolated_logging: logging.RootLogger,
) -> None:
    isolated_logging.handlers.clear()
    handler = _pipe_handler("app-pipe")
    isolated_logging.addHandler(handler)
    logger = logging.getLogger("task8.real")
    logger.addFilter(NamedFilter())
    recheck = freeze_logger_topology(frozenset(("app-pipe",)))

    with pytest.raises(DualLiveRuntimeError, match="dual_live_logger_topology_frozen"):
        logger.addHandler(_pipe_handler("late-pipe"))
    with pytest.raises(DualLiveRuntimeError, match="dual_live_logger_topology_frozen"):
        isolated_logging.removeHandler(handler)
    with pytest.raises(DualLiveRuntimeError, match="dual_live_logger_topology_frozen"):
        handler.addFilter(ReplacementFilter())
    with pytest.raises(DualLiveRuntimeError, match="dual_live_logger_topology_frozen"):
        handler.close()

    final = recheck()
    assert final["topology_sha256"]


def test_r07_logger_exit_census_keeps_guards_until_comparison_then_restores(
    isolated_logging: logging.RootLogger,
) -> None:
    isolated_logging.handlers.clear()
    manager = logging.Logger.manager
    logger = ExitCensusMutationLogger("task8.exit-census")
    logger.parent = isolated_logging
    logger.manager = manager
    manager.loggerDict[logger.name] = logger
    recheck = freeze_logger_topology(frozenset())

    logger.mutate_on_census = True
    final = recheck()

    assert final["topology_sha256"]
    assert logger.mutation_denied is True
    assert logger.filters == []
    logger.addFilter(NamedFilter())
    assert len(logger.filters) == 1


def test_r07_logger_freeze_guards_future_logger_creation_and_restores_global_api(
    isolated_logging: logging.RootLogger,
) -> None:
    isolated_logging.handlers.clear()
    original_get_logger = logging.getLogger
    recheck = freeze_logger_topology(frozenset())

    try:
        with pytest.raises(
            DualLiveRuntimeError,
            match="dual_live_logger_topology_frozen",
        ):
            logging.getLogger("task8.future")
        with pytest.raises(
            DualLiveRuntimeError,
            match="dual_live_logger_topology_frozen",
        ):
            logging.Logger.manager.getLogger("task8.future.manager")
    finally:
        with suppress(DualLiveRuntimeError):
            recheck()

    assert logging.getLogger is original_get_logger


def test_r07_logger_exit_recheck_detects_direct_late_handler_and_filter_change(
    isolated_logging: logging.RootLogger,
) -> None:
    isolated_logging.handlers.clear()
    isolated_logging.addHandler(_pipe_handler("app-pipe"))
    logger = logging.getLogger("task8.real")
    logger.addFilter(NamedFilter())
    original_get_logger = logging.getLogger
    original_level = logger.level
    recheck = freeze_logger_topology(frozenset(("app-pipe", "late-pipe")))

    isolated_logging.handlers.append(_pipe_handler("late-pipe"))
    with pytest.raises(DualLiveRuntimeError, match="dual_live_logger_topology_changed"):
        recheck()
    assert logging.getLogger is original_get_logger
    logger.setLevel(logging.INFO)
    assert logger.level == logging.INFO
    logger.setLevel(original_level)

    isolated_logging.handlers.pop()
    filter_recheck = freeze_logger_topology(
        frozenset(("app-pipe", "late-pipe"))
    )
    logger.filters[:] = [ReplacementFilter()]
    with pytest.raises(DualLiveRuntimeError, match="dual_live_logger_topology_changed"):
        filter_recheck()


def test_phase_control_requires_census_and_consumes_one_nonce_bound_go() -> None:
    stop = FirstStopLatch()
    raw_nonce = "d" * 64
    control = PhaseControlState(
        phase="A",
        control_nonce_sha256=hashlib.sha256(raw_nonce.encode("ascii")).hexdigest(),
        stop_latch=stop,
    )

    with pytest.raises(DualLiveRuntimeError, match="dual_live_phase_go_early"):
        control.consume_frame(
            io.BytesIO(
                encode_child_control_frame(
                    phase="A", command="GO", control_nonce=raw_nonce
                )
            )
        )
    assert stop.reason_code == "protocol_failure"

    stop = FirstStopLatch()
    control = PhaseControlState(
        phase="A",
        control_nonce_sha256=hashlib.sha256(raw_nonce.encode("ascii")).hexdigest(),
        stop_latch=stop,
    )
    control.mark_census_ready()
    message = encode_child_control_frame(
        phase="A", command="GO", control_nonce=raw_nonce
    )

    assert control.consume_frame(io.BytesIO(message)) == "GO"
    with pytest.raises(DualLiveRuntimeError, match="dual_live_phase_go_duplicate"):
        control.consume_frame(io.BytesIO(message))
    assert stop.reason_code == "protocol_failure"


def test_phase_control_stop_is_first_reason_wins_and_late_go_refuses() -> None:
    stop = FirstStopLatch()
    raw_nonce = "d" * 64
    control = PhaseControlState(
        phase="B",
        control_nonce_sha256=hashlib.sha256(raw_nonce.encode("ascii")).hexdigest(),
        stop_latch=stop,
    )
    control.mark_census_ready()

    assert control.consume_frame(
        io.BytesIO(
            encode_child_control_frame(
                phase="B", command="STOP", reason_code="operator_stop"
            )
        )
    ) == "STOP"
    terminal_frames = (
        encode_child_control_frame(
            phase="B", command="GO", control_nonce=raw_nonce
        ),
        encode_child_control_frame(
            phase="B", command="STOP", reason_code="timeout"
        ),
    )
    for frame in terminal_frames:
        with pytest.raises(
            DualLiveRuntimeError, match="dual_live_phase_control_terminal"
        ):
            control.consume_frame(io.BytesIO(frame))
    assert stop.reason_code == "operator_stop"


def test_four_stream_pumps_intercept_status_and_write_owned_streams() -> None:
    status_frame = encode_child_status_frame(
        phase="A",
        event="logger_census",
        process_boot_id=STATUS_PROCESS_BOOT_ID,
        status_nonce_sha256=STATUS_NONCE_SHA256,
        ordinal=1,
        payload={
            "census_point": "pre_activity",
            "handler_count": 2,
            "topology_sha256": "e" * 64,
        },
    )
    app = canonical_json_bytes(
        {"schema_id": "project6.test_app_event.v1", "value": "safe"}
    )
    http = canonical_json_bytes(
        {"schema_id": "project6.connector_http_counter.v2", "ordinal": 1}
    )
    readers = {
        "app": io.BytesIO(status_frame + encode_pipe_frame(app)),
        "http": io.BytesIO(encode_pipe_frame(http)),
        "stdout": io.BytesIO(encode_pipe_frame(b"out")),
        "stderr": io.BytesIO(encode_pipe_frame(b"err")),
    }
    writers = {stream: MemorySink() for stream in readers}
    statuses: list[dict[str, object]] = []
    validated_http: list[bytes] = []
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers=writers,
        status_callback=lambda value: statuses.append(value),
        http_frame_validator=lambda value: validated_http.append(value),
        stop_latch=FirstStopLatch(),
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )

    pumps.start()
    pumps.join(timeout=2)

    assert statuses == [
        {
            "event": "logger_census",
            "ordinal": 1,
            "payload": {
                "census_point": "pre_activity",
                "handler_count": 2,
                "topology_sha256": "e" * 64,
            },
            "phase": "A",
            "process_boot_id": STATUS_PROCESS_BOOT_ID,
            "schema_id": CHILD_STATUS_SCHEMA_ID,
            "status_nonce_sha256": STATUS_NONCE_SHA256,
        }
    ]
    assert validated_http == [http]
    assert writers["app"].bytes() == app + b"\n"
    assert writers["http"].bytes() == http + b"\n"
    assert writers["stdout"].bytes() == b"out"
    assert writers["stderr"].bytes() == b"err"


def test_four_stream_pumps_reject_replayed_bound_child_status() -> None:
    process_boot_id = "b" * 64
    status_nonce_sha256 = "c" * 64
    status_frame = encode_child_status_frame(
        phase="A",
        event="logger_census",
        process_boot_id=process_boot_id,
        status_nonce_sha256=status_nonce_sha256,
        ordinal=1,
        payload={
            "census_point": "pre_activity",
            "handler_count": 0,
            "topology_sha256": "e" * 64,
        },
    )
    readers = {
        "app": io.BytesIO(status_frame + status_frame),
        "http": io.BytesIO(),
        "stdout": io.BytesIO(),
        "stderr": io.BytesIO(),
    }
    writers = {stream: MemorySink() for stream in readers}
    statuses: list[dict[str, object]] = []
    stop = FirstStopLatch()
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers=writers,
        status_callback=lambda value: statuses.append(value),
        http_frame_validator=lambda _value: None,
        stop_latch=stop,
        expected_status_phase="A",
        expected_status_process_boot_id=process_boot_id,
        expected_status_nonce_sha256=status_nonce_sha256,
    )

    pumps.start()
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_failed") as exc:
        pumps.join(timeout=2)

    assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
    assert exc.value.__cause__.code == "dual_live_child_status_invalid"
    assert len(statuses) == 1
    assert stop.reason_code == "pump_failure"


def test_pump_failure_latches_stop_and_writes_no_invalid_app_bytes() -> None:
    readers = {
        "app": io.BytesIO(encode_pipe_frame(b"not-json")),
        "http": io.BytesIO(),
        "stdout": io.BytesIO(),
        "stderr": io.BytesIO(),
    }
    writers = {stream: MemorySink() for stream in readers}
    stop = FirstStopLatch()
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers=writers,
        status_callback=lambda _value: None,
        http_frame_validator=lambda _value: None,
        stop_latch=stop,
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )

    pumps.start()
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_failed"):
        pumps.join(timeout=2)

    assert stop.reason_code == "pump_failure"
    assert writers["app"].bytes() == b""


def test_locked_campaign_sink_serializes_concurrent_wrapper_writes() -> None:
    class OverlapDetectingWriter:
        def __init__(self) -> None:
            self.active = False
            self.overlap = False
            self.chunks: list[bytes] = []

        def write(self, content: bytes) -> int:
            if self.active:
                self.overlap = True
            self.active = True
            time.sleep(0.01)
            self.chunks.append(content)
            self.active = False
            return len(content)

    writer = OverlapDetectingWriter()
    sink = LockedCampaignSink(writer, stop_latch=FirstStopLatch())
    threads = [
        threading.Thread(target=sink.write, args=(content,))
        for content in (b"wrapper\n", b"child\n")
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert writer.overlap is False
    assert sorted(writer.chunks) == [b"child\n", b"wrapper\n"]


def test_locked_campaign_sink_poison_is_permanent_after_short_write() -> None:
    class ShortOnceWriter:
        def __init__(self) -> None:
            self.calls = 0

        def write(self, content: bytes) -> int:
            self.calls += 1
            if self.calls == 1:
                return len(content) - 1
            return len(content)

    writer = ShortOnceWriter()
    stop = FirstStopLatch()
    sink = LockedCampaignSink(writer, stop_latch=stop)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_write_failed"):
        sink.write(b"first")
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_writer_poisoned"):
        sink.write(b"second")

    assert writer.calls == 1
    assert stop.reason_code == "writer_failure"


def test_locked_campaign_sink_failure_poison_wins_concurrent_race() -> None:
    class BlockingFailureWriter:
        def __init__(self) -> None:
            self.calls = 0
            self.entered = threading.Event()
            self.release = threading.Event()

        def write(self, _content: bytes) -> int:
            self.calls += 1
            self.entered.set()
            assert self.release.wait(2)
            raise OSError("disk failed")

    writer = BlockingFailureWriter()
    stop = FirstStopLatch()
    sink = LockedCampaignSink(writer, stop_latch=stop)
    errors: list[str] = []

    def write(content: bytes) -> None:
        try:
            sink.write(content)
        except DualLiveRuntimeError as exc:
            errors.append(exc.code)

    first = threading.Thread(target=write, args=(b"first",))
    second = threading.Thread(target=write, args=(b"second",))
    first.start()
    assert writer.entered.wait(2)
    second.start()
    writer.release.set()
    first.join(2)
    second.join(2)

    assert first.is_alive() is False
    assert second.is_alive() is False
    assert sorted(errors) == [
        "dual_live_pump_write_failed",
        "dual_live_pump_writer_poisoned",
    ]
    assert writer.calls == 1
    assert stop.reason_code == "writer_failure"


def test_wrapper_app_write_latches_writer_failure_and_stays_poisoned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ShortWriter(MemorySink):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def write(self, content: bytes) -> int:
            self.calls += 1
            super().write(content)
            return len(content) - 1

    monkeypatch.setattr(dual_live_runtime_module, "MAX_STREAM_BYTES", 7)
    monkeypatch.setattr(dual_live_runtime_module, "MAX_CAPTURE_BYTES", 14)
    readers = {
        stream: io.BytesIO() for stream in ("app", "http", "stdout", "stderr")
    }
    app_writer = ShortWriter()
    writers: dict[str, MemorySink] = {
        "app": app_writer,
        "http": MemorySink(),
        "stdout": MemorySink(),
        "stderr": MemorySink(),
    }
    stop = FirstStopLatch()
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers=writers,
        status_callback=lambda _value: None,
        http_frame_validator=lambda _value: None,
        stop_latch=stop,
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )

    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_write_failed"):
        pumps.app_write(b"record\n")
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_writer_poisoned"):
        pumps.app_write(b"second\n")

    assert app_writer.calls == 1
    assert stop.reason_code == "writer_failure"


def test_four_stream_pumps_reject_aliased_capture_writers() -> None:
    readers = {
        stream: io.BytesIO() for stream in ("app", "http", "stdout", "stderr")
    }
    shared = MemorySink()
    writers = {
        "app": shared,
        "http": shared,
        "stdout": MemorySink(),
        "stderr": MemorySink(),
    }

    with pytest.raises(
        DualLiveRuntimeError, match="dual_live_pump_writer_alias_invalid"
    ):
        FourStreamPumpGroup(
            readers=readers,
            writers=writers,
            status_callback=lambda _value: None,
            http_frame_validator=lambda _value: None,
            stop_latch=FirstStopLatch(),
            expected_status_phase="A",
            expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
            expected_status_nonce_sha256=STATUS_NONCE_SHA256,
        )


def test_first_stop_latch_is_idempotent_and_rejects_unknown_reason() -> None:
    stop = FirstStopLatch()
    results: list[tuple[str, bool]] = []
    barrier = threading.Barrier(3)

    def latch(reason: str) -> None:
        barrier.wait()
        results.append((reason, stop.latch(reason)))

    threads = [
        threading.Thread(target=latch, args=(reason,))
        for reason in ("timeout", "operator_stop")
    ]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    winners = [reason for reason, won in results if won]
    assert len(winners) == 1
    assert stop.reason_code == winners[0]
    assert stop.is_set is True
    assert stop.wait(0) is True
    with pytest.raises(DualLiveRuntimeError, match="dual_live_stop_reason_invalid"):
        stop.latch("unknown")


@pytest.mark.parametrize(
    ("case", "expected_code"),
    [
        ("malformed_json", "dual_live_phase_control_invalid"),
        ("wrong_nonce", "dual_live_phase_go_invalid"),
        ("wrong_phase", "dual_live_phase_control_invalid"),
        ("partial_frame", "dual_live_phase_control_invalid"),
    ],
)
def test_phase_control_refuses_each_malformed_or_unbound_go(
    case: str,
    expected_code: str,
) -> None:
    raw_nonce = "d" * 64
    stop = FirstStopLatch()
    control = PhaseControlState(
        phase="A",
        control_nonce_sha256=hashlib.sha256(raw_nonce.encode("ascii")).hexdigest(),
        stop_latch=stop,
    )
    control.mark_census_ready()
    if case == "malformed_json":
        framed = encode_pipe_frame(b"{}")
    elif case == "wrong_nonce":
        framed = encode_child_control_frame(
            phase="A", command="GO", control_nonce="e" * 64
        )
    elif case == "wrong_phase":
        framed = encode_child_control_frame(
            phase="B", command="GO", control_nonce=raw_nonce
        )
    else:
        framed = b"\x00\x00"

    with pytest.raises(DualLiveRuntimeError, match=expected_code):
        control.consume_frame(io.BytesIO(framed))

    assert stop.reason_code == "protocol_failure"


def test_phase_control_complete_is_terminal() -> None:
    raw_nonce = "d" * 64
    stop = FirstStopLatch()
    control = PhaseControlState(
        phase="A",
        control_nonce_sha256=hashlib.sha256(raw_nonce.encode("ascii")).hexdigest(),
        stop_latch=stop,
    )
    control.mark_census_ready()
    control.consume_frame(
        io.BytesIO(
            encode_child_control_frame(
                phase="A", command="GO", control_nonce=raw_nonce
            )
        )
    )
    control.complete()

    terminal_frames = (
        encode_child_control_frame(
            phase="A", command="GO", control_nonce=raw_nonce
        ),
        encode_child_control_frame(
            phase="A", command="STOP", reason_code="operator_stop"
        ),
    )
    for frame in terminal_frames:
        with pytest.raises(
            DualLiveRuntimeError, match="dual_live_phase_control_terminal"
        ):
            control.consume_frame(io.BytesIO(frame))

    assert stop.reason_code == "protocol_failure"


def test_phase_control_protocol_failure_permanently_refuses_go_and_stop() -> None:
    raw_nonce = "d" * 64
    stop = FirstStopLatch()
    control = PhaseControlState(
        phase="A",
        control_nonce_sha256=hashlib.sha256(raw_nonce.encode("ascii")).hexdigest(),
        stop_latch=stop,
    )
    control.mark_census_ready()

    with pytest.raises(DualLiveRuntimeError, match="dual_live_phase_go_invalid"):
        control.consume_frame(
            io.BytesIO(
                encode_child_control_frame(
                    phase="A", command="GO", control_nonce="e" * 64
                )
            )
        )
    assert control.state == "failed"

    for frame in (
        encode_child_control_frame(
            phase="A", command="GO", control_nonce=raw_nonce
        ),
        encode_child_control_frame(
            phase="A", command="STOP", reason_code="operator_stop"
        ),
    ):
        with pytest.raises(
            DualLiveRuntimeError, match="dual_live_phase_control_terminal"
        ):
            control.consume_frame(io.BytesIO(frame))

    assert control.state == "failed"
    assert stop.reason_code == "protocol_failure"


def test_phase_control_rejects_oversized_prefix_without_reading_body() -> None:
    class PrefixOnlyReader:
        def __init__(self) -> None:
            self.read_sizes: list[int] = []

        def read(self, size: int) -> bytes:
            self.read_sizes.append(size)
            if len(self.read_sizes) == 1:
                return (4097).to_bytes(4, "big")
            pytest.fail("oversized control body must not be read")

    reader = PrefixOnlyReader()
    stop = FirstStopLatch()
    control = PhaseControlState(
        phase="A",
        control_nonce_sha256="a" * 64,
        stop_latch=stop,
    )
    control.mark_census_ready()

    with pytest.raises(
        DualLiveRuntimeError, match="dual_live_phase_control_invalid"
    ) as exc:
        control.consume_frame(reader)

    assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
    assert exc.value.__cause__.code == "dual_live_phase_control_oversized"
    assert reader.read_sizes == [4]
    assert control.state == "failed"
    assert stop.reason_code == "protocol_failure"


def test_child_status_requires_exact_expected_bindings_and_payload() -> None:
    process_boot_id = "b" * 64
    status_nonce_sha256 = "c" * 64
    frame = encode_child_status_frame(
        phase="A",
        event="logger_census",
        process_boot_id=process_boot_id,
        status_nonce_sha256=status_nonce_sha256,
        ordinal=1,
        payload={
            "census_point": "pre_activity",
            "handler_count": 2,
            "topology_sha256": "e" * 64,
        },
    )

    decoded = decode_child_status_frame(
        frame[4:],
        expected_phase="A",
        expected_process_boot_id=process_boot_id,
        expected_status_nonce_sha256=status_nonce_sha256,
        expected_ordinal=1,
    )

    assert decoded == {
        "event": "logger_census",
        "ordinal": 1,
        "payload": {
            "census_point": "pre_activity",
            "handler_count": 2,
            "topology_sha256": "e" * 64,
        },
        "phase": "A",
        "process_boot_id": process_boot_id,
        "schema_id": CHILD_STATUS_SCHEMA_ID,
        "status_nonce_sha256": status_nonce_sha256,
    }


def test_child_status_rejects_wrong_bindings_extras_and_unsafe_values() -> None:
    process_boot_id = "b" * 64
    status_nonce_sha256 = "c" * 64
    valid = {
        "event": "logger_census",
        "ordinal": 1,
        "payload": {
            "census_point": "pre_activity",
            "handler_count": 0,
            "topology_sha256": "e" * 64,
        },
        "phase": "A",
        "process_boot_id": process_boot_id,
        "schema_id": CHILD_STATUS_SCHEMA_ID,
        "status_nonce_sha256": status_nonce_sha256,
    }
    canonical = canonical_json_bytes(valid)
    invalid_values: list[dict[str, object]] = []

    wrong_schema = dict(valid)
    wrong_schema["schema_id"] = "project6.wrong.v1"
    invalid_values.append(wrong_schema)

    extra_envelope = dict(valid)
    extra_envelope["extra"] = "smuggled"
    invalid_values.append(extra_envelope)

    for bad_payload in (
        {
            **valid["payload"],
            "extra": "smuggled",
        },
        {
            **valid["payload"],
            "census_point": "secret=never",
        },
        {
            **valid["payload"],
            "handler_count": True,
        },
        {
            **valid["payload"],
            "handler_count": -1,
        },
        {
            **valid["payload"],
            "topology_sha256": "E" * 64,
        },
    ):
        invalid = dict(valid)
        invalid["payload"] = bad_payload
        invalid_values.append(invalid)

    invalid_payloads = [b"{" + b" " + canonical[1:]]
    invalid_payloads.extend(canonical_json_bytes(value) for value in invalid_values)
    for payload in invalid_payloads:
        with pytest.raises(
            DualLiveRuntimeError, match="dual_live_child_status_invalid"
        ):
            decode_child_status_frame(
                payload,
                expected_phase="A",
                expected_process_boot_id=process_boot_id,
                expected_status_nonce_sha256=status_nonce_sha256,
                expected_ordinal=1,
            )

    wrong_expectations = (
        ("B", process_boot_id, status_nonce_sha256, 1),
        ("A", "d" * 64, status_nonce_sha256, 1),
        ("A", process_boot_id, "d" * 64, 1),
        ("A", process_boot_id, status_nonce_sha256, 2),
    )
    for phase, boot_id, nonce_hash, ordinal in wrong_expectations:
        with pytest.raises(
            DualLiveRuntimeError, match="dual_live_child_status_invalid"
        ):
            decode_child_status_frame(
                canonical,
                expected_phase=phase,
                expected_process_boot_id=boot_id,
                expected_status_nonce_sha256=nonce_hash,
                expected_ordinal=ordinal,
            )


@pytest.mark.parametrize(
    "schema_id",
    (CHILD_CONTROL_SCHEMA_ID, CHILD_STATUS_SCHEMA_ID, RUNTIME_SCHEMA_ID),
)
def test_public_pipe_encoder_rejects_every_reserved_schema(schema_id: str) -> None:
    with pytest.raises(DualLiveRuntimeError, match="dual_live_child_reserved_schema"):
        encode_pipe_frame(canonical_json_bytes({"schema_id": schema_id}))


@pytest.mark.parametrize(
    ("stream", "reserved_kind"),
    (
        ("app", "control"),
        ("app", "runtime"),
        ("stdout", "control"),
        ("stdout", "status"),
        ("stdout", "runtime"),
        ("stderr", "control"),
        ("stderr", "status"),
        ("stderr", "runtime"),
    ),
)
def test_pumps_never_capture_reserved_schema_on_wrong_route(
    stream: str,
    reserved_kind: str,
) -> None:
    if reserved_kind == "control":
        frame = encode_child_control_frame(
            phase="A", command="GO", control_nonce="d" * 64
        )
    elif reserved_kind == "status":
        frame = encode_child_status_frame(
            phase="A",
            event="logger_census",
            process_boot_id=STATUS_PROCESS_BOOT_ID,
            status_nonce_sha256=STATUS_NONCE_SHA256,
            ordinal=1,
            payload={
                "census_point": "pre_activity",
                "handler_count": 0,
                "topology_sha256": "e" * 64,
            },
        )
    else:
        payload = canonical_json_bytes({"schema_id": RUNTIME_SCHEMA_ID})
        frame = len(payload).to_bytes(4, "big") + payload

    readers = {
        name: io.BytesIO(frame if name == stream else b"")
        for name in ("app", "http", "stdout", "stderr")
    }
    writers = {name: MemorySink() for name in readers}
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers=writers,
        status_callback=lambda _value: None,
        http_frame_validator=lambda _value: None,
        stop_latch=FirstStopLatch(),
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )

    pumps.start()
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_failed") as exc:
        pumps.join(timeout=2)

    assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
    assert exc.value.__cause__.code == "dual_live_child_reserved_schema"
    assert writers[stream].bytes() == b""


@pytest.mark.parametrize(
    ("case", "expected_cause", "expected_stop"),
    [
        ("partial_eof", "dual_live_frame_unexpected_eof", "pump_failure"),
        (
            "http_validator",
            "dual_live_http_frame_validator_invalid",
            "pump_failure",
        ),
        (
            "status_callback",
            "dual_live_child_status_callback_invalid",
            "pump_failure",
        ),
        ("short_writer", "dual_live_pump_write_failed", "writer_failure"),
        ("reserved_app", "dual_live_child_reserved_schema", "pump_failure"),
    ],
)
def test_each_pump_boundary_failure_latches_and_surfaces_exact_cause(
    case: str,
    expected_cause: str,
    expected_stop: str,
) -> None:
    class ShortWriter(MemorySink):
        def write(self, content: bytes) -> int:
            super().write(content)
            return len(content) - 1

    readers: dict[str, io.BytesIO] = {
        stream: io.BytesIO() for stream in ("app", "http", "stdout", "stderr")
    }
    writers: dict[str, MemorySink] = {stream: MemorySink() for stream in readers}
    status_result: object | None = None
    http_result: object | None = None

    def status_callback(_value: dict[str, object]) -> object | None:
        return status_result

    def http_validator(_value: bytes) -> object | None:
        return http_result

    if case == "partial_eof":
        readers["app"] = io.BytesIO(b"\x00\x00")
    elif case == "http_validator":
        readers["http"] = io.BytesIO(encode_pipe_frame(b"counter"))
        http_result = False
    elif case == "status_callback":
        readers["app"] = io.BytesIO(
            encode_child_status_frame(
                phase="A",
                event="logger_census",
                process_boot_id=STATUS_PROCESS_BOOT_ID,
                status_nonce_sha256=STATUS_NONCE_SHA256,
                ordinal=1,
                payload={
                    "census_point": "pre_activity",
                    "handler_count": 0,
                    "topology_sha256": "e" * 64,
                },
            )
        )
        status_result = False
    elif case == "short_writer":
        readers["stdout"] = io.BytesIO(encode_pipe_frame(b"output"))
        writers["stdout"] = ShortWriter()
    else:
        readers["app"] = io.BytesIO(
            encode_child_control_frame(
                phase="A", command="GO", control_nonce="d" * 64
            )
        )
    stop = FirstStopLatch()
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers=writers,
        status_callback=status_callback,
        http_frame_validator=http_validator,
        stop_latch=stop,
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )

    pumps.start()
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_failed") as exc:
        pumps.join(timeout=2)

    assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
    assert exc.value.__cause__.code == expected_cause
    assert stop.reason_code == expected_stop


def test_pump_start_is_one_use_and_join_timeout_latches_first_stop() -> None:
    class BlockingReader:
        def __init__(self) -> None:
            self.release = threading.Event()
            self.closed = False

        def read(self, _size: int) -> bytes:
            self.release.wait()
            return b""

        def close(self) -> None:
            self.closed = True
            self.release.set()

    blocker = BlockingReader()
    readers = {
        "app": blocker,
        "http": io.BytesIO(),
        "stdout": io.BytesIO(),
        "stderr": io.BytesIO(),
    }
    writers = {stream: MemorySink() for stream in readers}
    stop = FirstStopLatch()
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers=writers,
        status_callback=lambda _value: None,
        http_frame_validator=lambda _value: None,
        stop_latch=stop,
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )
    pumps.start()
    alive_names = set(pumps.threads_alive)
    assert alive_names
    assert all(
        thread.daemon
        for thread in threading.enumerate()
        if thread.name in alive_names
    )

    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_already_started"):
        pumps.start()
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_join_timeout"):
        pumps.join(timeout=0.01)
    assert stop.reason_code == "timeout"
    assert blocker.closed is True
    assert pumps.threads_alive == ()

    pumps.join(timeout=2)


def test_pump_join_preserves_primary_error_while_cancelling_blocked_peer() -> None:
    class CancellableBlockingReader:
        def __init__(self) -> None:
            self.release = threading.Event()
            self.closed = False

        def read(self, _size: int) -> bytes:
            self.release.wait()
            return b""

        def close(self) -> None:
            self.closed = True
            self.release.set()

    blocker = CancellableBlockingReader()
    readers = {
        "app": io.BytesIO(b"\x00\x00"),
        "http": blocker,
        "stdout": io.BytesIO(),
        "stderr": io.BytesIO(),
    }
    writers = {stream: MemorySink() for stream in readers}
    stop = FirstStopLatch()
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers=writers,
        status_callback=lambda _value: None,
        http_frame_validator=lambda _value: None,
        stop_latch=stop,
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )
    pumps.start()

    try:
        with pytest.raises(
            DualLiveRuntimeError, match="dual_live_pump_failed"
        ) as exc:
            pumps.join(timeout=0.05)
    finally:
        blocker.close()
        with suppress(DualLiveRuntimeError):
            pumps.join(timeout=2)

    assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
    assert exc.value.__cause__.code == "dual_live_frame_unexpected_eof"
    assert blocker.closed is True
    assert pumps.threads_alive == ()
    assert stop.reason_code == "pump_failure"


def test_four_stream_pump_concurrent_start_has_exactly_one_winner() -> None:
    readers = {
        stream: io.BytesIO() for stream in ("app", "http", "stdout", "stderr")
    }
    writers = {stream: MemorySink() for stream in readers}
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers=writers,
        status_callback=lambda _value: None,
        http_frame_validator=lambda _value: None,
        stop_latch=FirstStopLatch(),
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )
    barrier = threading.Barrier(3)
    results: list[str] = []

    def start() -> None:
        barrier.wait()
        try:
            pumps.start()
        except DualLiveRuntimeError as exc:
            results.append(exc.code)
        else:
            results.append("started")

    callers = [threading.Thread(target=start) for _ in range(2)]
    for caller in callers:
        caller.start()
    barrier.wait()
    for caller in callers:
        caller.join(2)

    assert all(caller.is_alive() is False for caller in callers)
    assert sorted(results) == ["dual_live_pump_already_started", "started"]
    pumps.join(timeout=2)
    assert pumps.threads_alive == ()


def test_pump_primary_error_uses_deterministic_stream_priority() -> None:
    readers = {
        "app": io.BytesIO(b"\x00\x00"),
        "http": io.BytesIO(encode_pipe_frame(b"counter")),
        "stdout": io.BytesIO(),
        "stderr": io.BytesIO(),
    }
    writers = {stream: MemorySink() for stream in readers}
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers=writers,
        status_callback=lambda _value: None,
        http_frame_validator=lambda _value: False,
        stop_latch=FirstStopLatch(),
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )
    pumps.start()

    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_failed") as exc:
        pumps.join(timeout=2)

    assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
    assert exc.value.__cause__.code == "dual_live_frame_unexpected_eof"
