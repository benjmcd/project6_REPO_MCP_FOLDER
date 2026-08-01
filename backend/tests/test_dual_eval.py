from __future__ import annotations

import hashlib
import inspect
import io
import json
import logging
import logging.handlers
import os
import queue
import subprocess
import sys
import threading
import time
from collections.abc import Callable
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
    PIPE_STREAM_CLASSES,
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


@pytest.mark.parametrize("bad_count", (None, True, "short", "long", "exception"))
def test_runtime_writer_requires_exact_int_byte_count(bad_count: object) -> None:
    class SequenceSink:
        def __init__(self) -> None:
            self.calls = 0
            self.physical = bytearray()

        def __call__(self, content: bytes) -> object:
            self.calls += 1
            if bad_count == "exception":
                self.physical.extend(content[:7])
                raise OSError("write failed")
            if bad_count == "short":
                self.physical.extend(content[:-1])
                return len(content) - 1
            self.physical.extend(content)
            if bad_count == "long":
                return len(content) + 1
            return bad_count

    sink = SequenceSink()
    writer = RuntimeRecordWriter(sink, identity=RUNTIME_IDENTITY)
    with pytest.raises(
        DualLiveRuntimeError, match="dual_live_runtime_writer_failure"
    ) as exc:
        writer.append(
            phase="wrapper",
            event="runtime_start",
            process_boot_id=None,
            payload=RUNTIME_START_PAYLOAD,
        )

    if bad_count == "exception":
        assert isinstance(exc.value.__cause__, OSError)
    physical_after_failure = bytes(sink.physical)
    with pytest.raises(
        DualLiveRuntimeError, match="dual_live_runtime_writer_poisoned"
    ):
        writer.append(
            phase="wrapper",
            event="runtime_start",
            process_boot_id=None,
            payload=RUNTIME_START_PAYLOAD,
        )
    assert sink.calls == 1
    assert bytes(sink.physical) == physical_after_failure


def test_runtime_writer_failure_poison_wins_concurrent_append_race() -> None:
    class BlockingFailureSink:
        def __init__(self) -> None:
            self.calls = 0
            self.entered = threading.Event()
            self.release = threading.Event()
            self.physical = bytearray()

        def __call__(self, content: bytes) -> int:
            self.calls += 1
            self.physical.extend(content[:7])
            self.entered.set()
            assert self.release.wait(2)
            raise OSError("write failed")

    sink = BlockingFailureSink()
    writer = RuntimeRecordWriter(sink, identity=RUNTIME_IDENTITY)
    errors: list[str] = []

    def append() -> None:
        try:
            writer.append(
                phase="wrapper",
                event="runtime_start",
                process_boot_id=None,
                payload=RUNTIME_START_PAYLOAD,
            )
        except DualLiveRuntimeError as exc:
            errors.append(exc.code)

    first = threading.Thread(target=append)
    second = threading.Thread(target=append)
    first.start()
    assert sink.entered.wait(2)
    second.start()
    sink.release.set()
    first.join(2)
    second.join(2)

    assert first.is_alive() is False
    assert second.is_alive() is False
    assert sorted(errors) == [
        "dual_live_runtime_writer_failure",
        "dual_live_runtime_writer_poisoned",
    ]
    assert sink.calls == 1
    assert bytes(sink.physical)


@pytest.mark.parametrize("failure_type", (KeyboardInterrupt, SystemExit))
def test_runtime_writer_base_exception_after_partial_write_poison_is_permanent(
    failure_type: type[BaseException],
) -> None:
    class InterruptingSink:
        def __init__(self) -> None:
            self.calls = 0
            self.physical = bytearray()

        def __call__(self, content: bytes) -> int:
            self.calls += 1
            self.physical.extend(content[:7])
            raise failure_type("interrupted")

    sink = InterruptingSink()
    writer = RuntimeRecordWriter(sink, identity=RUNTIME_IDENTITY)

    with pytest.raises(failure_type):
        writer.append(
            phase="wrapper",
            event="runtime_start",
            process_boot_id=None,
            payload=RUNTIME_START_PAYLOAD,
        )
    physical_after_failure = bytes(sink.physical)
    with pytest.raises(
        DualLiveRuntimeError, match="dual_live_runtime_writer_poisoned"
    ):
        writer.append(
            phase="wrapper",
            event="runtime_start",
            process_boot_id=None,
            payload=RUNTIME_START_PAYLOAD,
        )

    assert sink.calls == 1
    assert bytes(sink.physical) == physical_after_failure


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


def test_controller_budget_is_shared_across_wrapper_and_both_phase_pumps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dual_live_runtime_module, "MAX_CAPTURE_BYTES", 7)
    budget = PipeFrameBudget()
    budget.consume_wrapper("app", 1)
    writers = {stream: MemorySink() for stream in PIPE_STREAM_CLASSES}
    stop = FirstStopLatch()

    def pump(payload: bytes) -> FourStreamPumpGroup:
        readers = {stream: io.BytesIO() for stream in PIPE_STREAM_CLASSES}
        readers["stdout"] = io.BytesIO(encode_pipe_frame(payload))
        return FourStreamPumpGroup(
            readers=readers,
            writers=writers,
            status_callback=lambda _value: None,
            http_frame_validator=lambda _value: None,
            stop_latch=stop,
            expected_status_phase="A",
            expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
            expected_status_nonce_sha256=STATUS_NONCE_SHA256,
            budget=budget,
        )

    phase_a = pump(b"aaa")
    phase_a.start()
    phase_a.join(timeout=2)
    phase_b = pump(b"bbbb")
    phase_b.start()
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_failed") as exc:
        phase_b.join(timeout=2)

    assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
    assert exc.value.__cause__.code == "dual_live_pump_aggregate_bytes_exceeded"
    assert stop.reason_code == "pump_failure"


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


@pytest.mark.parametrize("bad_count", (None, True, "long"))
def test_locked_campaign_sink_invalid_write_count_poison_is_permanent(
    bad_count: object,
) -> None:
    class InvalidCountWriter:
        def __init__(self) -> None:
            self.calls = 0

        def write(self, content: bytes) -> object:
            self.calls += 1
            if bad_count == "long":
                return len(content) + 1
            return bad_count

    writer = InvalidCountWriter()
    stop = FirstStopLatch()
    sink = LockedCampaignSink(writer, stop_latch=stop)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_write_failed"):
        sink.write(b"first")
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_writer_poisoned"):
        sink.write(b"second")

    assert writer.calls == 1
    assert stop.reason_code == "writer_failure"


@pytest.mark.parametrize("bad_count", (None, True, "short", "long", "exception"))
def test_campaign_pipe_sink_requires_exact_int_byte_count(bad_count: object) -> None:
    class CountWriter:
        def __init__(self) -> None:
            self.calls = 0
            self.physical = bytearray()

        def write(self, content: bytes) -> object:
            self.calls += 1
            if bad_count == "exception":
                self.physical.extend(content[:3])
                raise OSError("pipe write failed")
            if bad_count == "short":
                self.physical.extend(content[:-1])
                return len(content) - 1
            self.physical.extend(content)
            if bad_count == "long":
                return len(content) + 1
            return bad_count

    writer = CountWriter()
    sink = CampaignPipeSink("app-pipe", writer)
    handler = CampaignPipeHandler("app-pipe", sink)
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "message", (), None)

    with pytest.raises(
        DualLiveRuntimeError, match="dual_live_logger_pipe_write_failed"
    ) as exc:
        handler.handle(record)

    if bad_count == "exception":
        assert isinstance(exc.value.__cause__, OSError)
    physical_after_failure = bytes(writer.physical)
    with pytest.raises(
        DualLiveRuntimeError, match="dual_live_logger_pipe_writer_poisoned"
    ):
        handler.handle(record)
    assert writer.calls == 1
    assert bytes(writer.physical) == physical_after_failure


def test_campaign_pipe_sink_failure_poison_wins_concurrent_emit_race() -> None:
    class BlockingFailureWriter:
        def __init__(self) -> None:
            self.calls = 0
            self.entered = threading.Event()
            self.release = threading.Event()
            self.physical = bytearray()

        def write(self, content: bytes) -> int:
            self.calls += 1
            self.physical.extend(content[:3])
            self.entered.set()
            assert self.release.wait(2)
            raise OSError("pipe write failed")

    writer = BlockingFailureWriter()
    handler = CampaignPipeHandler(
        "app-pipe",
        CampaignPipeSink("app-pipe", writer),
    )
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "message", (), None)
    errors: list[str] = []

    def emit() -> None:
        try:
            handler.handle(record)
        except DualLiveRuntimeError as exc:
            errors.append(exc.code)

    first = threading.Thread(target=emit)
    second = threading.Thread(target=emit)
    first.start()
    assert writer.entered.wait(2)
    second.start()
    writer.release.set()
    first.join(2)
    second.join(2)

    assert first.is_alive() is False
    assert second.is_alive() is False
    assert sorted(errors) == [
        "dual_live_logger_pipe_write_failed",
        "dual_live_logger_pipe_writer_poisoned",
    ]
    assert writer.calls == 1
    assert bytes(writer.physical)


@pytest.mark.parametrize("failure_type", (KeyboardInterrupt, SystemExit))
def test_campaign_pipe_sink_base_exception_after_partial_write_poison_is_permanent(
    failure_type: type[BaseException],
) -> None:
    class InterruptingWriter:
        def __init__(self) -> None:
            self.calls = 0
            self.physical = bytearray()

        def write(self, content: bytes) -> int:
            self.calls += 1
            self.physical.extend(content[:3])
            raise failure_type("interrupted")

    writer = InterruptingWriter()
    handler = CampaignPipeHandler(
        "app-pipe",
        CampaignPipeSink("app-pipe", writer),
    )
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "message", (), None)

    with pytest.raises(failure_type):
        handler.handle(record)
    physical_after_failure = bytes(writer.physical)
    with pytest.raises(
        DualLiveRuntimeError, match="dual_live_logger_pipe_writer_poisoned"
    ):
        handler.handle(record)

    assert writer.calls == 1
    assert bytes(writer.physical) == physical_after_failure


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


@pytest.mark.parametrize("failure_type", (KeyboardInterrupt, SystemExit))
def test_locked_campaign_sink_base_exception_after_partial_write_poison_is_permanent(
    failure_type: type[BaseException],
) -> None:
    class InterruptingWriter:
        def __init__(self) -> None:
            self.calls = 0
            self.physical = bytearray()

        def write(self, content: bytes) -> int:
            self.calls += 1
            self.physical.extend(content[:3])
            raise failure_type("interrupted")

    writer = InterruptingWriter()
    stop = FirstStopLatch()
    sink = LockedCampaignSink(writer, stop_latch=stop)

    with pytest.raises(failure_type):
        sink.write(b"first")
    physical_after_failure = bytes(writer.physical)
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_writer_poisoned"):
        sink.write(b"second")

    assert writer.calls == 1
    assert bytes(writer.physical) == physical_after_failure
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


def test_four_stream_pumps_reject_distinct_writers_for_same_destination(
    tmp_path: Path,
) -> None:
    readers = {
        stream: io.BytesIO() for stream in ("app", "http", "stdout", "stderr")
    }
    capture_path = tmp_path / "capture.log"
    first = capture_path.open("wb")
    second = capture_path.open("ab")
    try:
        writers = {
            "app": first,
            "http": second,
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
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize("fileno_result", (None, True, -1, "1", "exception"))
def test_four_stream_pumps_reject_invalid_writer_fileno(
    fileno_result: object,
) -> None:
    class InvalidFilenoWriter:
        def write(self, content: bytes) -> int:
            return len(content)

        def fileno(self) -> object:
            if fileno_result == "exception":
                raise OSError("invalid handle")
            return fileno_result

    readers = {
        stream: io.BytesIO() for stream in ("app", "http", "stdout", "stderr")
    }
    writers = {
        "app": InvalidFilenoWriter(),
        "http": MemorySink(),
        "stdout": MemorySink(),
        "stderr": MemorySink(),
    }

    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_writer_invalid"):
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


def test_four_stream_pumps_reject_non_memory_writer_without_fileno() -> None:
    class NoFilenoWriter:
        def write(self, content: bytes) -> int:
            return len(content)

    readers = {
        stream: io.BytesIO() for stream in ("app", "http", "stdout", "stderr")
    }
    writers = {
        "app": NoFilenoWriter(),
        "http": MemorySink(),
        "stdout": MemorySink(),
        "stderr": MemorySink(),
    }

    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_writer_invalid"):
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
    assert control.commit_go_if_clear()
    control.finish_go_dispatch(dispatched=True)
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


def test_phase_control_finishes_in_flight_stop_as_stopped() -> None:
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

    assert control.commit_go_if_clear()
    assert stop.latch("writer_failure")
    control.finish_go_dispatch(dispatched=True)

    assert control.state == "stopped"


def test_phase_control_stop_precedes_failed_dispatch_state() -> None:
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

    assert control.commit_go_if_clear()
    assert stop.latch("pump_failure")
    control.finish_go_dispatch(dispatched=False)

    assert control.state == "stopped"


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


@pytest.mark.parametrize("failure", (OSError("read failed"), TypeError("bad read")))
def test_phase_control_reader_exception_permanently_poison_state(
    failure: Exception,
) -> None:
    class FailingReader:
        def read(self, _size: int) -> bytes:
            raise failure

    raw_nonce = "d" * 64
    stop = FirstStopLatch()
    control = PhaseControlState(
        phase="A",
        control_nonce_sha256=hashlib.sha256(raw_nonce.encode("ascii")).hexdigest(),
        stop_latch=stop,
    )
    control.mark_census_ready()

    with pytest.raises(
        DualLiveRuntimeError, match="dual_live_phase_control_invalid"
    ) as exc:
        control.consume_frame(FailingReader())

    assert exc.value.__cause__ is failure
    assert control.state == "failed"
    assert stop.reason_code == "protocol_failure"
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


def test_phase_control_does_not_catch_base_exception() -> None:
    class InterruptedReader:
        def read(self, _size: int) -> bytes:
            raise KeyboardInterrupt

    stop = FirstStopLatch()
    control = PhaseControlState(
        phase="A",
        control_nonce_sha256="a" * 64,
        stop_latch=stop,
    )
    control.mark_census_ready()

    with pytest.raises(KeyboardInterrupt):
        control.consume_frame(InterruptedReader())

    assert control.state == "census_ready"
    assert stop.reason_code is None


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


@pytest.mark.parametrize("schema_id", (None, True, 1, [], {}))
def test_public_pipe_encoder_handles_non_string_schema_id(schema_id: object) -> None:
    payload = canonical_json_bytes({"schema_id": schema_id})

    assert encode_pipe_frame(payload) == len(payload).to_bytes(4, "big") + payload


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


@pytest.mark.parametrize(
    ("stream", "expected_code"),
    (
        ("app", "dual_live_child_status_callback_invalid"),
        ("http", "dual_live_http_frame_validator_invalid"),
    ),
)
def test_pump_callback_exception_is_normalized_with_cause(
    stream: str,
    expected_code: str,
) -> None:
    failure = LookupError(f"{stream} callback failed")

    def raise_failure(_value: object) -> None:
        raise failure

    readers = {
        name: io.BytesIO() for name in ("app", "http", "stdout", "stderr")
    }
    if stream == "app":
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
    else:
        readers["http"] = io.BytesIO(encode_pipe_frame(b"counter"))
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers={name: MemorySink() for name in readers},
        status_callback=raise_failure if stream == "app" else lambda _value: None,
        http_frame_validator=(
            raise_failure if stream == "http" else lambda _value: None
        ),
        stop_latch=FirstStopLatch(),
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )

    pumps.start()
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_failed") as exc:
        pumps.join(timeout=2)

    assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
    assert exc.value.__cause__.code == expected_code
    assert exc.value.__cause__.__cause__ is failure


@pytest.mark.parametrize(
    "failure",
    (None, KeyboardInterrupt("interrupted"), SystemExit("interrupted")),
)
def test_pre_cancel_writer_failure_survives_forced_cancel_boundary_race(
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException | None,
) -> None:
    class CancelErrorReader:
        def __init__(self) -> None:
            self.cancelled = threading.Event()

        def read(self, _size: int) -> bytes:
            self.cancelled.wait()
            raise OSError("app cancellation read failure")

        def close(self) -> None:
            self.cancelled.set()

    class BlockingFailureWriter(MemorySink):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def write(self, content: bytes) -> int:
            self.calls += 1
            super().write(content[:-1])
            if failure is not None:
                raise failure
            return len(content) - 1

    writer_failure_latched = threading.Event()
    allow_sink_raise = threading.Event()
    original_latch = FirstStopLatch.latch

    def gated_latch(self: FirstStopLatch, reason_code: str) -> bool:
        won = original_latch(self, reason_code)
        if reason_code == "writer_failure":
            writer_failure_latched.set()
            assert allow_sink_raise.wait(2)
        return won

    monkeypatch.setattr(FirstStopLatch, "latch", gated_latch)
    readers = {
        "app": CancelErrorReader(),
        "http": io.BytesIO(),
        "stdout": io.BytesIO(),
        "stderr": io.BytesIO(encode_pipe_frame(b"output")),
    }
    stderr_writer = BlockingFailureWriter()
    writers: dict[str, MemorySink] = {
        "app": MemorySink(),
        "http": MemorySink(),
        "stdout": MemorySink(),
        "stderr": stderr_writer,
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
    pumps.start()
    assert writer_failure_latched.wait(1)
    results: list[tuple[str, BaseException | None]] = []

    def join() -> None:
        try:
            pumps.join(timeout=0)
        except DualLiveRuntimeError as exc:
            results.append((exc.code, exc.__cause__))

    caller = threading.Thread(target=join)
    caller.start()
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        with pumps._errors_lock:
            if pumps._cancel_started:
                break
        time.sleep(0.001)
    else:
        pytest.fail("join never marked cancellation boundary")

    allow_sink_raise.set()
    caller.join(2)

    assert caller.is_alive() is False
    assert len(results) == 1
    assert results[0][0] == "dual_live_pump_failed"
    if failure is None:
        assert isinstance(results[0][1], DualLiveRuntimeError)
        assert results[0][1].code == "dual_live_pump_write_failed"
    else:
        assert results[0][1] is failure
    assert stop.reason_code == "writer_failure"
    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_writer_poisoned"):
        pumps._sinks["stderr"].write(b"again")
    assert stderr_writer.calls == 1
    assert stderr_writer.bytes() == b"outpu"
    assert pumps.threads_alive == ()


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


def test_pump_join_preserves_late_pre_cancel_errors_in_stream_priority() -> None:
    class GatedErrorReader:
        def __init__(self, failure: Exception) -> None:
            self.failure = failure
            self.entered = threading.Event()
            self.release = threading.Event()

        def read(self, _size: int) -> bytes:
            self.entered.set()
            self.release.wait()
            raise self.failure

        def close(self) -> None:
            self.release.set()

    class BlockingReader:
        def __init__(self) -> None:
            self.release = threading.Event()

        def read(self, _size: int) -> bytes:
            self.release.wait()
            return b""

        def close(self) -> None:
            self.release.set()

    app_failure = OSError("late app failure")
    http_failure = OSError("late http failure")
    app_reader = GatedErrorReader(app_failure)
    http_reader = GatedErrorReader(http_failure)
    blocker = BlockingReader()
    readers = {
        "app": app_reader,
        "http": http_reader,
        "stdout": io.BytesIO(),
        "stderr": blocker,
    }
    stop = FirstStopLatch()
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers={stream: MemorySink() for stream in readers},
        status_callback=lambda _value: None,
        http_frame_validator=lambda _value: None,
        stop_latch=stop,
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )
    pumps.start()
    assert app_reader.entered.wait(1)
    assert http_reader.entered.wait(1)
    join_started = threading.Event()
    results: list[tuple[str, BaseException | None]] = []

    def join() -> None:
        join_started.set()
        try:
            pumps.join(timeout=0.2)
        except DualLiveRuntimeError as exc:
            results.append((exc.code, exc.__cause__))

    caller = threading.Thread(target=join)
    caller.start()
    assert join_started.wait(1)
    app_reader.release.set()
    http_reader.release.set()
    caller.join(2)

    assert caller.is_alive() is False
    assert results == [("dual_live_pump_failed", app_failure)]
    assert stop.reason_code == "pump_failure"
    assert pumps.threads_alive == ()


def test_pump_join_is_bounded_when_reader_close_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BlockingCloseReader:
        def __init__(self) -> None:
            self.read_release = threading.Event()
            self.close_entered = threading.Event()
            self.close_release = threading.Event()

        def read(self, _size: int) -> bytes:
            self.read_release.wait()
            return b""

        def close(self) -> None:
            self.close_entered.set()
            self.close_release.wait()
            self.read_release.set()

    monkeypatch.setattr(dual_live_runtime_module, "PUMP_CANCEL_JOIN_SECONDS", 0.05)
    blocker = BlockingCloseReader()
    readers = {
        "app": blocker,
        "http": io.BytesIO(),
        "stdout": io.BytesIO(),
        "stderr": io.BytesIO(),
    }
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers={stream: MemorySink() for stream in readers},
        status_callback=lambda _value: None,
        http_frame_validator=lambda _value: None,
        stop_latch=FirstStopLatch(),
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )
    pumps.start()

    started = time.monotonic()
    try:
        with pytest.raises(
            DualLiveRuntimeError, match="dual_live_pump_cancel_failed"
        ) as exc:
            pumps.join(timeout=0.01)
        elapsed = time.monotonic() - started

        assert elapsed < 0.5
        assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
        assert exc.value.__cause__.code == "dual_live_pump_cancel_stuck"
        assert blocker.close_entered.is_set()
        related = [
            thread
            for thread in threading.enumerate()
            if thread.name.startswith("dual-live-app-")
        ]
        assert related
        assert all(thread.daemon for thread in related)
    finally:
        blocker.close_release.set()
        blocker.read_release.set()


def test_pump_join_reports_reader_close_exception_with_domain_taxonomy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingCloseReader:
        def __init__(self) -> None:
            self.read_release = threading.Event()

        def read(self, _size: int) -> bytes:
            self.read_release.wait()
            return b""

        def close(self) -> None:
            raise OSError("close failed")

    monkeypatch.setattr(dual_live_runtime_module, "PUMP_CANCEL_JOIN_SECONDS", 0.05)
    blocker = FailingCloseReader()
    readers = {
        "app": blocker,
        "http": io.BytesIO(),
        "stdout": io.BytesIO(),
        "stderr": io.BytesIO(),
    }
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers={stream: MemorySink() for stream in readers},
        status_callback=lambda _value: None,
        http_frame_validator=lambda _value: None,
        stop_latch=FirstStopLatch(),
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )
    pumps.start()

    try:
        with pytest.raises(
            DualLiveRuntimeError, match="dual_live_pump_cancel_failed"
        ) as exc:
            pumps.join(timeout=0)

        assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
        assert exc.value.__cause__.code == "dual_live_pump_cancel_reader_failed"
        assert isinstance(exc.value.__cause__.__cause__, OSError)
    finally:
        blocker.read_release.set()


def test_pump_concurrent_join_refuses_while_join_is_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CoordinatedReader:
        def __init__(self) -> None:
            self.read_release = threading.Event()
            self.close_entered = threading.Event()
            self.close_release = threading.Event()

        def read(self, _size: int) -> bytes:
            self.read_release.wait()
            return b""

        def close(self) -> None:
            self.close_entered.set()
            self.close_release.wait()
            self.read_release.set()

    monkeypatch.setattr(dual_live_runtime_module, "PUMP_CANCEL_JOIN_SECONDS", 0.5)
    blocker = CoordinatedReader()
    readers = {
        "app": blocker,
        "http": io.BytesIO(),
        "stdout": io.BytesIO(),
        "stderr": io.BytesIO(),
    }
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers={stream: MemorySink() for stream in readers},
        status_callback=lambda _value: None,
        http_frame_validator=lambda _value: None,
        stop_latch=FirstStopLatch(),
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )
    pumps.start()
    results: list[str] = []

    def join() -> None:
        try:
            pumps.join(timeout=0)
        except DualLiveRuntimeError as exc:
            results.append(exc.code)

    caller = threading.Thread(target=join)
    caller.start()
    assert blocker.close_entered.wait(1)
    try:
        with pytest.raises(
            DualLiveRuntimeError, match="dual_live_pump_join_in_progress"
        ):
            pumps.join(timeout=0)
    finally:
        blocker.close_release.set()
        blocker.read_release.set()
    caller.join(2)

    assert caller.is_alive() is False
    assert results == ["dual_live_pump_join_timeout"]


def test_pump_join_keeps_timeout_when_cancellation_causes_read_errors() -> None:
    class CancelErrorReader:
        def __init__(self, failure: Exception) -> None:
            self.failure = failure
            self.cancelled = threading.Event()

        def read(self, _size: int) -> bytes:
            self.cancelled.wait()
            raise self.failure

        def close(self) -> None:
            self.cancelled.set()

    app_failure = OSError("app cancelled read")
    http_failure = OSError("http cancelled read")
    readers = {
        "app": CancelErrorReader(app_failure),
        "http": CancelErrorReader(http_failure),
        "stdout": io.BytesIO(),
        "stderr": io.BytesIO(),
    }
    stop = FirstStopLatch()
    pumps = FourStreamPumpGroup(
        readers=readers,
        writers={stream: MemorySink() for stream in readers},
        status_callback=lambda _value: None,
        http_frame_validator=lambda _value: None,
        stop_latch=stop,
        expected_status_phase="A",
        expected_status_process_boot_id=STATUS_PROCESS_BOOT_ID,
        expected_status_nonce_sha256=STATUS_NONCE_SHA256,
    )
    pumps.start()

    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_join_timeout"):
        pumps.join(timeout=0)

    assert stop.reason_code == "timeout"
    assert pumps.threads_alive == ()


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


class _ControllerReader:
    def __init__(self) -> None:
        self._chunks: queue.Queue[bytes | None] = queue.Queue()
        self._buffer = b""
        self._closed = False

    def feed(self, content: bytes) -> None:
        self._chunks.put(content)

    def finish(self) -> None:
        self._chunks.put(None)

    def read(self, size: int) -> bytes:
        while not self._buffer:
            chunk = self._chunks.get(timeout=2)
            if chunk is None:
                return b""
            self._buffer = chunk
        result, self._buffer = self._buffer[:size], self._buffer[size:]
        return result

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self.finish()


class _DescriptorControllerReader(_ControllerReader):
    def __init__(self, descriptor: int) -> None:
        super().__init__()
        self._descriptor = descriptor

    def fileno(self) -> int:
        return self._descriptor


class _CountingCloseControllerReader(_ControllerReader):
    def __init__(self) -> None:
        super().__init__()
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1
        super().close()


class _StuckCloseControllerReader(_ControllerReader):
    def __init__(
        self,
        *,
        close_started: threading.Event,
        close_release: threading.Event,
        closed: threading.Event,
    ) -> None:
        super().__init__()
        self._close_started = close_started
        self._close_release = close_release
        self._closed_event = closed
        self._close_lock = threading.Lock()
        self.close_calls = 0

    def close(self) -> None:
        with self._close_lock:
            self.close_calls += 1
            call = self.close_calls
        if call != 1:
            raise RuntimeError("controller attempted duplicate reader close")
        self._close_started.set()
        assert self._close_release.wait(timeout=2)
        super().close()
        self._closed_event.set()


class _ControllerWriter(io.BytesIO):
    def __init__(self, stream: str, events: list[str]) -> None:
        super().__init__()
        self.stream = stream
        self.events = events
        self.closed_clean = False

    def flush(self) -> None:
        self.events.append(f"flush-{self.stream}")

    def close(self) -> None:
        self.events.append(f"close-{self.stream}")
        self.closed_clean = True


class _StopRecordControllerWriter(_ControllerWriter):
    def write(self, content: bytes) -> int:
        if b'"event":"stop_latched"' in content:
            self.events.append("record-stop")
        return super().write(content)


class _FailingControllerWriter(_ControllerWriter):
    def write(self, _content: bytes) -> int:
        raise OSError("runtime start write failed")


class _NthFailControllerWriter(_ControllerWriter):
    def __init__(
        self,
        stream: str,
        events: list[str],
        *,
        fail_on_write: int,
    ) -> None:
        super().__init__(stream, events)
        self._fail_on_write = fail_on_write
        self._writes = 0

    def write(self, content: bytes) -> int:
        self._writes += 1
        if self._writes == self._fail_on_write:
            raise OSError("late custody write failed")
        return super().write(content)


class _WaitActiveFailWriter(_ControllerWriter):
    def __init__(
        self,
        stream: str,
        events: list[str],
        *,
        wait_active: threading.Event,
    ) -> None:
        super().__init__(stream, events)
        self._wait_active = wait_active

    def write(self, _content: bytes) -> int:
        assert self._wait_active.wait(timeout=2)
        self.events.append(f"writer-fail-{self.stream}")
        raise OSError("capture write failed during child wait")


def _controller_socket_census(*, stable: bool = True) -> dict[str, object]:
    return {
        "tcp4_state_counts": dict(ZERO_TCP_STATE_COUNTS),
        "tcp6_state_counts": dict(ZERO_TCP_STATE_COUNTS),
        "udp4_count": 0,
        "udp6_count": 0,
        "process_identity_sha256": "d" * 64,
        "stable": stable,
    }


def _controller_projection(
    readers: dict[str, object],
    events: list[str],
) -> object:
    return dual_live_runtime_module._ControllerChild(
        process_boot_id="a" * 64,
        process_creation_identity_sha256="2" * 64,
        executable_sha256="3" * 64,
        job_policy_sha256="4" * 64,
        status_nonce_sha256="c" * 64,
        control_nonce="e" * 64,
        readers=readers,
        send_control=lambda _frame: events.append("go-A"),
        wait=lambda _timeout: 0,
        stop=lambda: events.append("stop-A"),
    )


def _controller_child(
    phase: str,
    events: list[str],
    *,
    exit_code: int = 0,
    wait_active: threading.Event | None = None,
    wait_release: threading.Event | None = None,
    wait_error: BaseException | None = None,
    wait_error_once: BaseException | None = None,
    never_exit: bool = False,
    send_before_go: Callable[[dict[str, _ControllerReader]], None] | None = None,
    app_reader: _ControllerReader | None = None,
    reader_factory: Callable[[], _ControllerReader] | None = None,
    finish_readers: bool = True,
) -> object:
    process_boot_id = ("a" if phase == "A" else "b") * 64
    status_nonce_sha256 = ("c" if phase == "A" else "d") * 64
    control_nonce = ("e" if phase == "A" else "f") * 64
    factory = _ControllerReader if reader_factory is None else reader_factory
    readers = {stream: factory() for stream in PIPE_STREAM_CLASSES}
    if app_reader is not None:
        readers["app"] = app_reader
    readers["app"].feed(
        encode_child_status_frame(
            phase=phase,
            event="logger_census",
            process_boot_id=process_boot_id,
            status_nonce_sha256=status_nonce_sha256,
            ordinal=1,
            payload={
                "census_point": "pre_activity",
                "handler_count": 1,
                "topology_sha256": "1" * 64,
            },
        )
    )
    wait_error_raised = False

    def send_control(frame: bytes) -> None:
        if send_before_go is not None:
            send_before_go(readers)
        events.append(f"go-{phase}")
        assert frame == encode_child_control_frame(
            phase=phase,
            command="GO",
            control_nonce=control_nonce,
        )
        readers["app"].feed(
            encode_pipe_frame(
                canonical_json_bytes(
                    {
                        "schema_id": "project6.test_child_app.v1",
                        "phase": phase,
                    }
                )
            )
        )
        readers["app"].feed(
            encode_child_status_frame(
                phase=phase,
                event="logger_census",
                process_boot_id=process_boot_id,
                status_nonce_sha256=status_nonce_sha256,
                ordinal=2,
                payload={
                    "census_point": "exit",
                    "handler_count": 1,
                    "topology_sha256": "1" * 64,
                },
            )
        )
        readers["http"].feed(
            encode_pipe_frame(
                canonical_json_bytes(
                    {
                        "schema_id": "project6.connector_http_counter.v2",
                        "phase": phase,
                    }
                )
            )
        )
        readers["stdout"].feed(encode_pipe_frame(f"out-{phase}".encode()))
        readers["stderr"].feed(encode_pipe_frame(f"err-{phase}".encode()))
        if finish_readers:
            for reader in readers.values():
                reader.finish()

    def wait(_timeout: float) -> int | None:
        nonlocal wait_error_raised
        events.append(f"wait-{phase}")
        if wait_error is not None:
            raise wait_error
        if wait_error_once is not None and not wait_error_raised:
            wait_error_raised = True
            events.append(f"wait-raise-{phase}")
            raise wait_error_once
        if never_exit:
            return None
        if wait_active is not None:
            if not wait_active.is_set():
                events.append(f"wait-active-{phase}")
                wait_active.set()
            if wait_release is not None and not wait_release.is_set():
                return None
            events.append(f"wait-release-{phase}")
        return exit_code

    def stop() -> None:
        events.append(f"stop-{phase}")
        if wait_release is not None:
            wait_release.set()

    return dual_live_runtime_module._ControllerChild(
        process_boot_id=process_boot_id,
        process_creation_identity_sha256="2" * 64,
        executable_sha256="3" * 64,
        job_policy_sha256="4" * 64,
        status_nonce_sha256=status_nonce_sha256,
        control_nonce=control_nonce,
        readers=readers,
        send_control=send_control,
        wait=wait,
        stop=stop,
    )


def test_controller_child_rejects_same_reader_object_before_use() -> None:
    events: list[str] = []
    shared = _ControllerReader()
    readers: dict[str, object] = {
        stream: shared if stream in {"app", "http"} else _ControllerReader()
        for stream in PIPE_STREAM_CLASSES
    }

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_pump_reader_alias_invalid",
    ):
        _controller_projection(readers, events)

    assert events == []


def test_controller_child_rejects_same_numeric_descriptor_before_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    readers: dict[str, object] = {
        stream: _DescriptorControllerReader(41 if stream in {"app", "http"} else i)
        for i, stream in enumerate(PIPE_STREAM_CLASSES, start=42)
    }
    zero_stat = type("ZeroStat", (), {"st_dev": 0, "st_ino": 0})()
    monkeypatch.setattr(dual_live_runtime_module.os, "fstat", lambda _fd: zero_stat)

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_pump_reader_alias_invalid",
    ):
        _controller_projection(readers, events)

    assert events == []


def test_controller_child_rejects_duplicate_stable_reader_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    readers: dict[str, object] = {
        stream: _DescriptorControllerReader(descriptor)
        for stream, descriptor in zip(PIPE_STREAM_CLASSES, range(51, 55), strict=True)
    }
    shared_stat = type("SharedStat", (), {"st_dev": 7, "st_ino": 11})()
    monkeypatch.setattr(dual_live_runtime_module.os, "fstat", lambda _fd: shared_stat)

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_pump_reader_alias_invalid",
    ):
        _controller_projection(readers, events)

    assert events == []


def test_controller_child_accepts_distinct_zero_identity_pipe_readers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    readers: dict[str, object] = {
        stream: _DescriptorControllerReader(descriptor)
        for stream, descriptor in zip(PIPE_STREAM_CLASSES, range(61, 65), strict=True)
    }
    zero_stat = type("ZeroStat", (), {"st_dev": 0, "st_ino": 0})()
    monkeypatch.setattr(dual_live_runtime_module.os, "fstat", lambda _fd: zero_stat)
    monkeypatch.setattr(
        dual_live_runtime_module,
        "_validate_windows_reader_descriptors_distinct",
        lambda _descriptors: None,
    )

    child = _controller_projection(readers, events)

    assert child.readers == readers
    assert events == []


@pytest.mark.skipif(os.name != "nt", reason="Windows pipe identity proof")
def test_controller_child_rejects_duplicated_windows_pipe_descriptor() -> None:
    events: list[str] = []
    pipe_pairs = [os.pipe() for _ in range(3)]
    duplicate = os.dup(pipe_pairs[0][0])
    descriptors = (
        pipe_pairs[0][0],
        duplicate,
        pipe_pairs[1][0],
        pipe_pairs[2][0],
    )
    owned_descriptors = [
        descriptor for pair in pipe_pairs for descriptor in pair
    ] + [duplicate]
    readers: dict[str, object] = {
        stream: _DescriptorControllerReader(descriptor)
        for stream, descriptor in zip(
            PIPE_STREAM_CLASSES,
            descriptors,
            strict=True,
        )
    }

    try:
        with pytest.raises(
            DualLiveRuntimeError,
            match="dual_live_pump_reader_alias_invalid",
        ):
            _controller_projection(readers, events)
    finally:
        for descriptor in owned_descriptors:
            with suppress(OSError):
                os.close(descriptor)

    assert events == []


@pytest.mark.skipif(os.name != "nt", reason="Windows pipe identity proof")
def test_controller_child_accepts_distinct_windows_pipe_descriptors() -> None:
    events: list[str] = []
    pipe_pairs = [os.pipe() for _ in PIPE_STREAM_CLASSES]
    owned_descriptors = [
        descriptor for pair in pipe_pairs for descriptor in pair
    ]
    readers: dict[str, object] = {
        stream: _DescriptorControllerReader(pair[0])
        for stream, pair in zip(PIPE_STREAM_CLASSES, pipe_pairs, strict=True)
    }

    try:
        child = _controller_projection(readers, events)
    finally:
        for descriptor in owned_descriptors:
            with suppress(OSError):
                os.close(descriptor)

    assert child.readers == readers
    assert events == []


@pytest.mark.skipif(os.name != "nt", reason="Windows pipe identity proof")
def test_controller_child_fails_closed_on_windows_pipe_identity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_windows

    events: list[str] = []
    pipe_pairs = [os.pipe() for _ in PIPE_STREAM_CLASSES]
    owned_descriptors = [
        descriptor for pair in pipe_pairs for descriptor in pair
    ]
    readers: dict[str, object] = {
        stream: _DescriptorControllerReader(pair[0])
        for stream, pair in zip(PIPE_STREAM_CLASSES, pipe_pairs, strict=True)
    }

    def identity_failure(_left: int, _right: int) -> bool:
        raise RuntimeError("opaque pipe identity failure")

    monkeypatch.setattr(
        dual_live_windows,
        "pipe_descriptors_same",
        identity_failure,
    )
    try:
        with pytest.raises(
            DualLiveRuntimeError,
            match="dual_live_controller_child_invalid",
        ) as exc:
            _controller_projection(readers, events)
    finally:
        for descriptor in owned_descriptors:
            with suppress(OSError):
                os.close(descriptor)

    assert isinstance(exc.value.__cause__, RuntimeError)
    assert str(exc.value) == "dual_live_controller_child_invalid"
    assert events == []


def test_controller_child_rejects_null_raw_handle() -> None:
    events: list[str] = []
    readers: dict[str, object] = {
        stream: _ControllerReader() for stream in PIPE_STREAM_CLASSES
    }
    readers["app"].handle = 0

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_controller_child_invalid",
    ):
        _controller_projection(readers, events)

    assert events == []


def test_stop_latch_publishes_first_reason_and_preserves_first_tick_after_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = {"tick": 101}
    monkeypatch.setattr(
        dual_live_runtime_module.time,
        "monotonic_ns",
        lambda: clock["tick"],
    )
    stop = FirstStopLatch()

    assert stop.commit_if_clear()
    assert stop.latch("writer_failure")
    clock["tick"] = 202
    assert stop.reason_code == "writer_failure"
    assert stop.is_set
    assert stop.monotonic_tick_ns == 101
    assert not stop.commit_if_clear()
    assert not stop.latch("pump_failure")
    assert stop.monotonic_tick_ns == 101


def test_controller_latch_between_control_parse_and_go_prevents_send(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }
    original_consume = PhaseControlState.consume_frame

    def latch_before_go(
        control: PhaseControlState,
        reader: object,
    ) -> str:
        result = original_consume(control, reader)
        assert result == "GO"
        control._stop_latch.latch("pump_failure")
        return result

    monkeypatch.setattr(PhaseControlState, "consume_frame", latch_before_go)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_phase_stopped"):
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child("A", events),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda phase, _child: (
                events.append(f"quiesce-{phase}")
                or _controller_socket_census(),
                {"active_process_count": 0, "process_list_sha256": "5" * 64},
            ),
            clear_authority=lambda phase, _child: {
                "authority_posture_sha256": "6" * 64,
                "all_required_absent": events.append(f"authority-{phase}") is None,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=0.1,
        )

    assert "go-A" not in events
    records = read_runtime_records(writers["app"].getvalue())
    assert all(record["event"] != "phase_go" for record in records)
    assert events.count("stop-A") == 1
    assert "create-B" not in events
    assert "seal" not in events


def test_controller_publishes_stop_during_one_in_flight_go_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    clock = {"tick": 303}
    send_active = threading.Event()
    latch_attempted = threading.Event()
    wait_active = threading.Event()
    wait_release = threading.Event()
    captured_latch: list[FirstStopLatch] = []
    published_during_send: list[bool] = []
    original_latch = FirstStopLatch.latch

    monkeypatch.setattr(
        dual_live_runtime_module.time,
        "monotonic_ns",
        lambda: clock["tick"],
    )

    def observe_latch(stop: FirstStopLatch, reason_code: str) -> bool:
        won = original_latch(stop, reason_code)
        if reason_code == "writer_failure" and won:
            captured_latch.append(stop)
            latch_attempted.set()
        return won

    monkeypatch.setattr(FirstStopLatch, "latch", observe_latch)
    writers = {
        stream: (
            _WaitActiveFailWriter(stream, events, wait_active=send_active)
            if stream == "stdout"
            else _ControllerWriter(stream, events)
        )
        for stream in PIPE_STREAM_CLASSES
    }

    def fail_writer_before_dispatch(
        readers: dict[str, _ControllerReader],
    ) -> None:
        events.append("send-start-A")
        send_active.set()
        readers["stdout"].feed(encode_pipe_frame(b"race"))
        assert latch_attempted.wait(timeout=2)
        published_during_send.append(captured_latch[0].is_set)
        assert captured_latch[0].reason_code == "writer_failure"
        assert captured_latch[0].monotonic_tick_ns == 303
        clock["tick"] = 404
        events.append("dispatch-complete-A")

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_runtime_writer_failure",
    ):
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child(
                "A",
                events,
                wait_active=wait_active,
                wait_release=wait_release,
                send_before_go=fail_writer_before_dispatch,
            ),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda _phase, _child: (
                _controller_socket_census(),
                {"active_process_count": 0, "process_list_sha256": "5" * 64},
            ),
            clear_authority=lambda _phase, _child: {
                "authority_posture_sha256": "6" * 64,
                "all_required_absent": True,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=2,
        )

    assert published_during_send == [True]
    assert events.index("writer-fail-stdout") < events.index("dispatch-complete-A")
    assert events.index("dispatch-complete-A") < events.index("go-A")
    assert events.index("go-A") < events.index("stop-A")
    assert events.count("go-A") == 1
    assert events.count("stop-A") == 1
    assert "create-B" not in events
    assert "seal" not in events
    records = read_runtime_records(writers["app"].getvalue())
    stop_records = [record for record in records if record["event"] == "stop_latched"]
    assert len(stop_records) == 1
    assert stop_records[0]["payload"] == {
        "reason_code": "writer_failure",
        "monotonic_tick_ns": 303,
    }


def test_controller_rechecks_stop_after_phase_go_record_before_send(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    captured_latches: list[FirstStopLatch] = []
    original_init = FirstStopLatch.__init__
    original_append = RuntimeRecordWriter.append

    def capture_latch(stop: FirstStopLatch) -> None:
        original_init(stop)
        captured_latches.append(stop)

    def latch_after_phase_go(
        writer: RuntimeRecordWriter,
        *,
        phase: str,
        event: str,
        process_boot_id: str | None,
        payload: object,
    ) -> dict[str, object]:
        record = original_append(
            writer,
            phase=phase,
            event=event,
            process_boot_id=process_boot_id,
            payload=payload,
        )
        if event == "phase_go":
            assert len(captured_latches) == 1
            assert captured_latches[0].latch("pump_failure")
        return record

    monkeypatch.setattr(FirstStopLatch, "__init__", capture_latch)
    monkeypatch.setattr(RuntimeRecordWriter, "append", latch_after_phase_go)
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    with pytest.raises(DualLiveRuntimeError, match="dual_live_phase_stopped"):
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child("A", events),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda _phase, _child: (
                _controller_socket_census(),
                {"active_process_count": 0, "process_list_sha256": "5" * 64},
            ),
            clear_authority=lambda _phase, _child: {
                "authority_posture_sha256": "6" * 64,
                "all_required_absent": True,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=0.1,
        )

    assert "go-A" not in events
    assert events.count("stop-A") == 1
    assert "create-B" not in events
    assert "seal" not in events
    records = read_runtime_records(writers["app"].getvalue())
    assert [record["event"] for record in records].count("phase_go") == 1


def test_suppressed_send_stop_accepts_raced_exit_census(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    captured_latches: list[FirstStopLatch] = []
    captured_readers: list[dict[str, _ControllerReader]] = []
    finished_states: list[str] = []
    exit_observed: list[bool] = []
    exit_recorded = threading.Event()
    original_init = FirstStopLatch.__init__
    original_append = RuntimeRecordWriter.append
    original_finish = PhaseControlState.finish_go_dispatch

    def capture_latch(stop: FirstStopLatch) -> None:
        original_init(stop)
        captured_latches.append(stop)

    def observe_records(
        writer: RuntimeRecordWriter,
        *,
        phase: str,
        event: str,
        process_boot_id: str | None,
        payload: object,
    ) -> dict[str, object]:
        record = original_append(
            writer,
            phase=phase,
            event=event,
            process_boot_id=process_boot_id,
            payload=payload,
        )
        if event == "phase_go":
            assert len(captured_latches) == 1
            assert captured_latches[0].latch("pump_failure")
        if (
            event == "logger_census"
            and isinstance(payload, dict)
            and payload.get("census_point") == "exit"
        ):
            exit_recorded.set()
        return record

    def race_exit_after_finish(
        control: PhaseControlState,
        *,
        dispatched: bool,
    ) -> None:
        original_finish(control, dispatched=dispatched)
        finished_states.append(control.state)
        readers = captured_readers[0]
        readers["app"].feed(
            encode_child_status_frame(
                phase="A",
                event="logger_census",
                process_boot_id="a" * 64,
                status_nonce_sha256="c" * 64,
                ordinal=2,
                payload={
                    "census_point": "exit",
                    "handler_count": 1,
                    "topology_sha256": "1" * 64,
                },
            )
        )
        for reader in readers.values():
            reader.finish()
        exit_observed.append(exit_recorded.wait(timeout=0.2))

    def create_child() -> object:
        child = _controller_child("A", events, finish_readers=False)
        captured_readers.append(dict(child.readers))
        return child

    monkeypatch.setattr(FirstStopLatch, "__init__", capture_latch)
    monkeypatch.setattr(RuntimeRecordWriter, "append", observe_records)
    monkeypatch.setattr(
        PhaseControlState,
        "finish_go_dispatch",
        race_exit_after_finish,
    )
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    with pytest.raises(DualLiveRuntimeError, match="dual_live_phase_stopped"):
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=create_child,
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda _phase, _child: (
                _controller_socket_census(),
                {"active_process_count": 0, "process_list_sha256": "5" * 64},
            ),
            clear_authority=lambda _phase, _child: {
                "authority_posture_sha256": "6" * 64,
                "all_required_absent": True,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=0.5,
        )

    assert finished_states == ["stopped"]
    assert exit_observed == [True]
    assert "go-A" not in events
    assert "create-B" not in events
    assert "seal" not in events


def test_send_exception_latches_before_raced_exit_census(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    captured_readers: list[dict[str, _ControllerReader]] = []
    finished_states: list[str] = []
    exit_observed: list[bool] = []
    exit_recorded = threading.Event()
    original_append = RuntimeRecordWriter.append
    original_finish = PhaseControlState.finish_go_dispatch

    def observe_exit_record(
        writer: RuntimeRecordWriter,
        *,
        phase: str,
        event: str,
        process_boot_id: str | None,
        payload: object,
    ) -> dict[str, object]:
        record = original_append(
            writer,
            phase=phase,
            event=event,
            process_boot_id=process_boot_id,
            payload=payload,
        )
        if (
            event == "logger_census"
            and isinstance(payload, dict)
            and payload.get("census_point") == "exit"
        ):
            exit_recorded.set()
        return record

    def race_exit_after_finish(
        control: PhaseControlState,
        *,
        dispatched: bool,
    ) -> None:
        original_finish(control, dispatched=dispatched)
        finished_states.append(control.state)
        readers = captured_readers[0]
        readers["app"].feed(
            encode_child_status_frame(
                phase="A",
                event="logger_census",
                process_boot_id="a" * 64,
                status_nonce_sha256="c" * 64,
                ordinal=2,
                payload={
                    "census_point": "exit",
                    "handler_count": 1,
                    "topology_sha256": "1" * 64,
                },
            )
        )
        for reader in readers.values():
            reader.finish()
        exit_observed.append(exit_recorded.wait(timeout=0.2))

    def raise_send(_readers: dict[str, _ControllerReader]) -> None:
        raise RuntimeError("send failed")

    def create_child() -> object:
        child = _controller_child(
            "A",
            events,
            send_before_go=raise_send,
            finish_readers=False,
        )
        captured_readers.append(dict(child.readers))
        return child

    monkeypatch.setattr(RuntimeRecordWriter, "append", observe_exit_record)
    monkeypatch.setattr(
        PhaseControlState,
        "finish_go_dispatch",
        race_exit_after_finish,
    )
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    with pytest.raises(DualLiveRuntimeError, match="dual_live_phase_failed") as exc:
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=create_child,
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda _phase, _child: (
                _controller_socket_census(),
                {"active_process_count": 0, "process_list_sha256": "5" * 64},
            ),
            clear_authority=lambda _phase, _child: {
                "authority_posture_sha256": "6" * 64,
                "all_required_absent": True,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=0.5,
        )

    assert isinstance(exc.value.__cause__, RuntimeError)
    assert finished_states == ["stopped"]
    assert exit_observed == [True]
    assert "go-A" not in events
    assert "create-B" not in events
    assert "seal" not in events


def test_in_flight_writer_failure_precedes_unproven_child_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    send_active = threading.Event()
    writer_failed = threading.Event()
    original_latch = FirstStopLatch.latch

    def observe_writer_failure(stop: FirstStopLatch, reason_code: str) -> bool:
        won = original_latch(stop, reason_code)
        if reason_code == "writer_failure":
            writer_failed.set()
        return won

    monkeypatch.setattr(FirstStopLatch, "latch", observe_writer_failure)
    writers = {
        stream: (
            _WaitActiveFailWriter(stream, events, wait_active=send_active)
            if stream == "stdout"
            else _ControllerWriter(stream, events)
        )
        for stream in PIPE_STREAM_CLASSES
    }

    def fail_writer_during_go(readers: dict[str, _ControllerReader]) -> None:
        send_active.set()
        readers["stdout"].feed(encode_pipe_frame(b"race"))
        assert writer_failed.wait(timeout=2)

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_runtime_writer_failure",
    ) as caught:
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child(
                "A",
                events,
                never_exit=True,
                send_before_go=fail_writer_during_go,
            ),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda _phase, _child: (
                _controller_socket_census(),
                {"active_process_count": 0, "process_list_sha256": "5" * 64},
            ),
            clear_authority=lambda _phase, _child: {
                "authority_posture_sha256": "6" * 64,
                "all_required_absent": True,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=0.1,
        )

    pump_error = caught.value.__cause__
    assert isinstance(pump_error, DualLiveRuntimeError)
    assert pump_error.code == "dual_live_pump_failed"
    assert isinstance(pump_error.__cause__, DualLiveRuntimeError)
    assert pump_error.__cause__.code == "dual_live_pump_write_failed"
    prior_error = caught.value.__context__
    assert isinstance(prior_error, DualLiveRuntimeError)
    assert prior_error.code == "dual_live_runtime_writer_failure"
    assert isinstance(prior_error.__cause__, DualLiveRuntimeError)
    assert prior_error.__cause__.code == "dual_live_phase_stopped"
    assert events.count("go-A") == 1
    assert events.count("stop-A") == 1
    assert "create-B" not in events
    assert "seal" not in events
    records = read_runtime_records(writers["app"].getvalue())
    stop_records = [record for record in records if record["event"] == "stop_latched"]
    assert len(stop_records) == 1
    assert stop_records[0]["payload"]["reason_code"] == "writer_failure"


def test_controller_writer_failure_during_wait_stops_before_real_exit() -> None:
    events: list[str] = []
    wait_active = threading.Event()
    wait_release = threading.Event()
    writers = {
        stream: (
            _WaitActiveFailWriter(stream, events, wait_active=wait_active)
            if stream == "stdout"
            else _ControllerWriter(stream, events)
        )
        for stream in PIPE_STREAM_CLASSES
    }

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_runtime_writer_failure",
    ):
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child(
                "A",
                events,
                wait_active=wait_active,
                wait_release=wait_release,
            ),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda phase, _child: (
                events.append(f"quiesce-{phase}")
                or _controller_socket_census(),
                {"active_process_count": 0, "process_list_sha256": "5" * 64},
            ),
            clear_authority=lambda phase, _child: {
                "authority_posture_sha256": "6" * 64,
                "all_required_absent": events.append(f"authority-{phase}") is None,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=2,
        )

    assert events.index("wait-active-A") < events.index("writer-fail-stdout")
    assert events.index("writer-fail-stdout") < events.index("stop-A")
    assert events.index("stop-A") < events.index("wait-release-A")
    assert events.index("wait-release-A") < events.index("authority-A")
    assert events.index("authority-A") < events.index("quiesce-A")
    assert events.count("stop-A") == 1
    assert "create-B" not in events
    assert "seal" not in events
    completions = [
        record
        for record in read_runtime_records(writers["app"].getvalue())
        if record["event"] == "phase_complete"
    ]
    assert len(completions) == 1
    assert completions[0]["payload"] == {
        "terminal_state": "failed",
        "exit_code": 0,
    }


def test_controller_wait_raises_then_stop_repolls_real_exit() -> None:
    events: list[str] = []
    wait_active = threading.Event()
    wait_release = threading.Event()
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    with pytest.raises(DualLiveRuntimeError, match="dual_live_phase_failed") as exc:
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child(
                "A",
                events,
                wait_active=wait_active,
                wait_release=wait_release,
                wait_error_once=RuntimeError("wait interrupted"),
            ),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda phase, _child: (
                events.append(f"quiesce-{phase}")
                or _controller_socket_census(),
                {"active_process_count": 0, "process_list_sha256": "5" * 64},
            ),
            clear_authority=lambda phase, _child: {
                "authority_posture_sha256": "6" * 64,
                "all_required_absent": events.append(f"authority-{phase}") is None,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=2,
        )

    assert isinstance(exc.value.__cause__, RuntimeError)
    assert events.index("wait-raise-A") < events.index("stop-A")
    assert events.index("stop-A") < events.index("wait-release-A")
    assert events.index("wait-release-A") < events.index("authority-A")
    assert events.index("authority-A") < events.index("quiesce-A")
    assert events.count("stop-A") == 1
    assert "create-B" not in events
    assert "seal" not in events
    completions = [
        record
        for record in read_runtime_records(writers["app"].getvalue())
        if record["event"] == "phase_complete"
    ]
    assert len(completions) == 1
    assert completions[0]["payload"] == {
        "terminal_state": "failed",
        "exit_code": 0,
    }


def test_controller_never_exits_skips_teardown_evidence_and_returns_bounded() -> None:
    events: list[str] = []
    app_reader = _ControllerReader()
    captured_readers: list[dict[str, _ControllerReader]] = []
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }
    started = time.monotonic()

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_capture_ownership_unproven",
    ) as exc:
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child(
                "A",
                events,
                never_exit=True,
                app_reader=app_reader,
                finish_readers=False,
                send_before_go=lambda readers: captured_readers.append(readers),
            ),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda phase, _child: events.append(f"quiesce-{phase}"),
            clear_authority=lambda phase, _child: events.append(
                f"authority-{phase}"
            ),
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=0.05,
        )

    try:
        assert time.monotonic() - started < 0.5
        assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
        assert exc.value.__cause__.code == "dual_live_phase_exit_timeout"
        assert events.count("stop-A") == 1
        assert not app_reader._closed
        assert all(not writer.closed_clean for writer in writers.values())
        assert not any(event.startswith(("flush-", "close-")) for event in events)
        assert "quiesce-A" not in events
        assert "authority-A" not in events
        assert "create-B" not in events
        assert "seal" not in events
        records = read_runtime_records(writers["app"].getvalue())
        completions = [
            record for record in records if record["event"] == "phase_complete"
        ]
        assert completions == []
        stop_records = [
            record for record in records if record["event"] == "stop_latched"
        ]
        assert len(stop_records) == 1
        assert stop_records[0]["payload"]["reason_code"] == "timeout"
    finally:
        for reader in captured_readers[0].values():
            reader.close()


def test_exit_unproven_closes_each_dead_pump_reader_once() -> None:
    events: list[str] = []
    captured_readers: list[dict[str, _CountingCloseControllerReader]] = []
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    def create_child() -> object:
        child = _controller_child(
            "A",
            events,
            never_exit=True,
            reader_factory=_CountingCloseControllerReader,
        )
        captured_readers.append(dict(child.readers))
        return child

    try:
        with pytest.raises(
            DualLiveRuntimeError,
            match="dual_live_phase_exit_timeout",
        ):
            dual_live_runtime_module._run_two_phase_controller(
                identity=RUNTIME_IDENTITY,
                runtime_start_payload=RUNTIME_START_PAYLOAD,
                writers=writers,
                create_phase_a=create_child,
                create_phase_b=lambda: events.append("create-B"),
                quiesce_phase=lambda phase, _child: events.append(
                    f"quiesce-{phase}"
                ),
                clear_authority=lambda phase, _child: events.append(
                    f"authority-{phase}"
                ),
                http_frame_validator=lambda _payload: None,
                seal=lambda: events.append("seal"),
                timeout_seconds=0.05,
            )

        readers = tuple(captured_readers[0].values())
        assert [reader.close_calls for reader in readers] == [1, 1, 1, 1]
        assert all(reader._closed for reader in readers)
        assert all(writer.closed_clean for writer in writers.values())
        assert "quiesce-A" not in events
        assert "authority-A" not in events
        assert "create-B" not in events
        assert "seal" not in events
    finally:
        for reader in captured_readers[0].values():
            if not reader._closed:
                reader.close()


def test_controller_stop_record_uses_immutable_first_latch_tick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    clock = {"tick": 111}
    monkeypatch.setattr(
        dual_live_runtime_module.time,
        "monotonic_ns",
        lambda: clock["tick"],
    )
    original_latch = FirstStopLatch.latch

    def advance_after_latch(stop: FirstStopLatch, reason_code: str) -> bool:
        won = original_latch(stop, reason_code)
        if won:
            clock["tick"] = 222
        return won

    monkeypatch.setattr(FirstStopLatch, "latch", advance_after_latch)
    writers = {
        stream: (
            _StopRecordControllerWriter(stream, events)
            if stream == "app"
            else _ControllerWriter(stream, events)
        )
        for stream in PIPE_STREAM_CLASSES
    }

    with pytest.raises(DualLiveRuntimeError, match="dual_live_phase_failed"):
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child("A", events, exit_code=9),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda _phase, _child: (
                _controller_socket_census(),
                {"active_process_count": 0, "process_list_sha256": "5" * 64},
            ),
            clear_authority=lambda _phase, _child: {
                "authority_posture_sha256": "6" * 64,
                "all_required_absent": True,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=2,
        )

    stop_records = [
        record
        for record in read_runtime_records(writers["app"].getvalue())
        if record["event"] == "stop_latched"
    ]
    assert len(stop_records) == 1
    assert stop_records[0]["payload"]["monotonic_tick_ns"] == 111
    assert events.index("record-stop") < events.index("stop-A")


def test_partial_pump_start_failure_never_closes_live_writer_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    captured_readers: list[dict[str, _ControllerReader]] = []
    started_pumps: list[threading.Thread] = []
    pump_start_count = 0
    original_start = threading.Thread.start
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    def fail_second_pump_start(thread: threading.Thread) -> None:
        nonlocal pump_start_count
        if thread.name.startswith("dual-live-") and thread.name.endswith("-pump"):
            pump_start_count += 1
            if pump_start_count == 2:
                raise RuntimeError("partial pump start")
        original_start(thread)
        if thread.name.startswith("dual-live-") and thread.name.endswith("-pump"):
            started_pumps.append(thread)

    def create_child() -> object:
        child = _controller_child(
            "A",
            events,
            never_exit=True,
            finish_readers=False,
        )
        captured_readers.append(dict(child.readers))
        return child

    monkeypatch.setattr(threading.Thread, "start", fail_second_pump_start)
    started = time.monotonic()
    try:
        with pytest.raises(
            DualLiveRuntimeError,
            match="dual_live_capture_ownership_unproven",
        ) as exc:
            dual_live_runtime_module._run_two_phase_controller(
                identity=RUNTIME_IDENTITY,
                runtime_start_payload=RUNTIME_START_PAYLOAD,
                writers=writers,
                create_phase_a=create_child,
                create_phase_b=lambda: events.append("create-B"),
                quiesce_phase=lambda phase, _child: events.append(
                    f"quiesce-{phase}"
                ),
                clear_authority=lambda phase, _child: events.append(
                    f"authority-{phase}"
                ),
                http_frame_validator=lambda _payload: None,
                seal=lambda: events.append("seal"),
                timeout_seconds=0.05,
            )

        assert time.monotonic() - started < 0.5
        assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
        assert exc.value.__cause__.code == "dual_live_phase_failed"
        assert isinstance(exc.value.__cause__.__cause__, RuntimeError)
        assert pump_start_count == 2
        assert len(started_pumps) == 1
        assert started_pumps[0].is_alive()
        assert all(not writer.closed_clean for writer in writers.values())
        assert not any(event.startswith(("flush-", "close-")) for event in events)
        assert "quiesce-A" not in events
        assert "authority-A" not in events
        assert "create-B" not in events
        assert "seal" not in events
    finally:
        for reader in captured_readers[0].values():
            reader.close()
        for thread in started_pumps:
            thread.join(timeout=1)


def test_partial_cancel_start_closes_only_unassigned_readers_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    captured_pumps: list[FourStreamPumpGroup] = []
    captured_readers: list[_CountingCloseControllerReader] = []
    started_cancel_threads: list[threading.Thread] = []
    cancel_start_count = 0
    original_thread_start = threading.Thread.start
    original_pump_start = FourStreamPumpGroup.start
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    def reader_factory() -> _CountingCloseControllerReader:
        reader = _CountingCloseControllerReader()
        captured_readers.append(reader)
        return reader

    def capture_pumps_start(pumps: FourStreamPumpGroup) -> None:
        captured_pumps.append(pumps)
        original_pump_start(pumps)

    def fail_second_cancel_start(thread: threading.Thread) -> None:
        nonlocal cancel_start_count
        if thread.name.startswith("dual-live-") and thread.name.endswith(
            "-cancel"
        ):
            cancel_start_count += 1
            if cancel_start_count == 2:
                for reader in captured_readers[1:]:
                    reader.finish()
                for started_thread in started_cancel_threads:
                    started_thread.join(timeout=1)
                deadline = time.monotonic() + 1
                while (
                    captured_pumps[0].threads_alive
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.001)
                assert captured_pumps[0].threads_alive == ()
                raise RuntimeError("partial cancel start")
        original_thread_start(thread)
        if thread.name.startswith("dual-live-") and thread.name.endswith(
            "-cancel"
        ):
            started_cancel_threads.append(thread)

    monkeypatch.setattr(FourStreamPumpGroup, "start", capture_pumps_start)
    monkeypatch.setattr(threading.Thread, "start", fail_second_cancel_start)
    try:
        with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_failed") as exc:
            dual_live_runtime_module._run_two_phase_controller(
                identity=RUNTIME_IDENTITY,
                runtime_start_payload=RUNTIME_START_PAYLOAD,
                writers=writers,
                create_phase_a=lambda: _controller_child(
                    "A",
                    events,
                    reader_factory=reader_factory,
                    finish_readers=False,
                ),
                create_phase_b=lambda: events.append("create-B"),
                quiesce_phase=lambda _phase, _child: (
                    _controller_socket_census(),
                    {
                        "active_process_count": 0,
                        "process_list_sha256": "5" * 64,
                    },
                ),
                clear_authority=lambda _phase, _child: {
                    "authority_posture_sha256": "6" * 64,
                    "all_required_absent": True,
                },
                http_frame_validator=lambda _payload: None,
                seal=lambda: events.append("seal"),
                timeout_seconds=0.05,
            )

        cancel_failure = exc.value.__cause__
        assert isinstance(cancel_failure, DualLiveRuntimeError)
        assert cancel_failure.code == "dual_live_pump_cancel_failed"
        assert isinstance(cancel_failure.__cause__, DualLiveRuntimeError)
        assert cancel_failure.__cause__.code == "dual_live_pump_cancel_start_failed"
        assert isinstance(cancel_failure.__cause__.__cause__, RuntimeError)
        assert cancel_start_count == 4
        assert len(started_cancel_threads) == 3
        assert all(not thread.is_alive() for thread in started_cancel_threads)
        assert captured_pumps[0].threads_alive == ()
        owned, completed = captured_pumps[0].cancellation_reader_custody
        assert owned == completed == frozenset(
            id(captured_readers[index]) for index in (0, 2, 3)
        )
        assert [reader.close_calls for reader in captured_readers] == [1, 1, 1, 1]
        assert all(reader._closed for reader in captured_readers)
        assert all(writer.closed_clean for writer in writers.values())
        assert "create-B" not in events
        assert "seal" not in events
    finally:
        for reader in captured_readers:
            if not reader._closed:
                reader.close()
        for thread in started_cancel_threads:
            thread.join(timeout=1)


def test_completed_pump_error_closes_each_controller_owned_reader_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    captured_pumps: list[FourStreamPumpGroup] = []
    captured_readers: list[dict[str, _ControllerReader]] = []
    original_start = FourStreamPumpGroup.start
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    def capture_start(pumps: FourStreamPumpGroup) -> None:
        captured_pumps.append(pumps)
        original_start(pumps)

    def inject_malformed_frame(readers: dict[str, _ControllerReader]) -> None:
        captured_readers.append(readers)
        readers["stdout"].feed(b"\x00\x00\x00\x00")

    monkeypatch.setattr(FourStreamPumpGroup, "start", capture_start)
    try:
        with pytest.raises(DualLiveRuntimeError):
            dual_live_runtime_module._run_two_phase_controller(
                identity=RUNTIME_IDENTITY,
                runtime_start_payload=RUNTIME_START_PAYLOAD,
                writers=writers,
                create_phase_a=lambda: _controller_child(
                    "A",
                    events,
                    send_before_go=inject_malformed_frame,
                    reader_factory=_CountingCloseControllerReader,
                ),
                create_phase_b=lambda: events.append("create-B"),
                quiesce_phase=lambda _phase, _child: (
                    _controller_socket_census(),
                    {
                        "active_process_count": 0,
                        "process_list_sha256": "5" * 64,
                    },
                ),
                clear_authority=lambda _phase, _child: {
                    "authority_posture_sha256": "6" * 64,
                    "all_required_absent": True,
                },
                http_frame_validator=lambda _payload: None,
                seal=lambda: events.append("seal"),
                timeout_seconds=2,
            )

        assert len(captured_pumps) == 1
        assert captured_pumps[0].threads_alive == ()
        assert not captured_pumps[0].has_live_workers
        readers = tuple(captured_readers[0].values())
        assert all(
            isinstance(reader, _CountingCloseControllerReader)
            for reader in readers
        )
        assert [reader.close_calls for reader in readers] == [1, 1, 1, 1]
        assert sum(not reader._closed for reader in readers) == 0
        assert "create-B" not in events
        assert "seal" not in events
    finally:
        for reader in captured_readers[0].values():
            if not reader._closed:
                reader.close()


def test_controller_stuck_pump_cancel_is_not_closed_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dual_live_runtime_module, "PUMP_CANCEL_JOIN_SECONDS", 0.05)
    events: list[str] = []
    close_started = threading.Event()
    close_release = threading.Event()
    closed = threading.Event()
    app_reader = _StuckCloseControllerReader(
        close_started=close_started,
        close_release=close_release,
        closed=closed,
    )
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }
    started = time.monotonic()

    try:
        with pytest.raises(
            DualLiveRuntimeError,
            match="dual_live_capture_ownership_unproven",
        ) as exc:
            dual_live_runtime_module._run_two_phase_controller(
                identity=RUNTIME_IDENTITY,
                runtime_start_payload=RUNTIME_START_PAYLOAD,
                writers=writers,
                create_phase_a=lambda: _controller_child(
                    "A",
                    events,
                    app_reader=app_reader,
                    finish_readers=False,
                ),
                create_phase_b=lambda: events.append("create-B"),
                quiesce_phase=lambda _phase, _child: (
                    _controller_socket_census(),
                    {
                        "active_process_count": 0,
                        "process_list_sha256": "5" * 64,
                    },
                ),
                clear_authority=lambda _phase, _child: {
                    "authority_posture_sha256": "6" * 64,
                    "all_required_absent": True,
                },
                http_frame_validator=lambda _payload: None,
                seal=lambda: events.append("seal"),
                timeout_seconds=0.05,
            )
    finally:
        elapsed = time.monotonic() - started
        close_release.set()

    assert elapsed < 0.5
    assert close_started.is_set()
    assert closed.wait(timeout=1)
    assert app_reader.close_calls == 1
    assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
    assert exc.value.__cause__.code == "dual_live_pump_failed"
    assert all(not writer.closed_clean for writer in writers.values())
    assert not any(event.startswith(("flush-", "close-")) for event in events)
    assert events.count("stop-A") == 1
    assert "create-B" not in events
    assert "seal" not in events


def test_controller_wait_baseexception_has_no_fabricated_completion() -> None:
    events: list[str] = []
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    with pytest.raises(DualLiveRuntimeError, match="dual_live_phase_failed") as exc:
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child(
                "A",
                events,
                wait_error=KeyboardInterrupt(),
            ),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda _phase, _child: (
                _controller_socket_census(),
                {"active_process_count": 0, "process_list_sha256": "5" * 64},
            ),
            clear_authority=lambda _phase, _child: {
                "authority_posture_sha256": "6" * 64,
                "all_required_absent": True,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=2,
        )

    assert isinstance(exc.value.__cause__, KeyboardInterrupt)
    assert events.count("stop-A") == 1
    assert "create-B" not in events
    assert "seal" not in events
    runtime_events = [
        record["event"] for record in read_runtime_records(writers["app"].getvalue())
    ]
    assert "phase_complete" not in runtime_events


def test_task5_controller_clears_phase_a_authority_before_quiescence_and_b() -> None:
    events: list[str] = []
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    def create(phase: str) -> object:
        events.append(f"create-{phase}")
        return _controller_child(phase, events)

    def quiesce(phase: str, _child: object) -> tuple[dict[str, object], ...]:
        events.append(f"quiesce-{phase}")
        return (
            _controller_socket_census(),
            {"active_process_count": 0, "process_list_sha256": "5" * 64},
        )

    def clear_authority(phase: str, _child: object) -> dict[str, object]:
        events.append(f"authority-{phase}")
        return {
            "authority_posture_sha256": "6" * 64,
            "all_required_absent": True,
        }

    result = dual_live_runtime_module._run_two_phase_controller(
        identity=RUNTIME_IDENTITY,
        runtime_start_payload=RUNTIME_START_PAYLOAD,
        writers=writers,
        create_phase_a=lambda: create("A"),
        create_phase_b=lambda: create("B"),
        quiesce_phase=quiesce,
        clear_authority=clear_authority,
        http_frame_validator=lambda payload: None if json.loads(payload) else None,
        seal=lambda: events.append("seal") or "sealed",
        timeout_seconds=2,
    )

    assert result == "sealed"
    assert events.index("stop-A") < events.index("authority-A")
    assert events.index("authority-A") < events.index("quiesce-A")
    assert events.index("quiesce-A") < events.index("create-B")
    assert events[-1] == "seal"
    assert events.index("stop-B") < events.index("flush-app")
    assert events.count("stop-A") == 1
    assert events.count("stop-B") == 1
    assert all(writer.closed_clean for writer in writers.values())
    assert b"out-Aout-B" == writers["stdout"].getvalue()
    assert b"err-Aerr-B" == writers["stderr"].getvalue()
    assert writers["http"].getvalue().count(b"\n") == 2
    runtime_events = [
        record["event"] for record in read_runtime_records(writers["app"].getvalue())
    ]
    assert runtime_events == [
        "runtime_start",
        "phase_child_start",
        "logger_census",
        "phase_go",
        "logger_census",
        "socket_census",
        "job_zero",
        "authority_cleared",
        "phase_complete",
        "phase_child_start",
        "logger_census",
        "phase_go",
        "logger_census",
        "socket_census",
        "job_zero",
        "phase_complete",
        "runtime_complete",
    ]
    assert "authority-B" not in events


def test_phase_a_authority_failure_still_quiesces_before_suppressing_b() -> None:
    events: list[str] = []
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    def clear_authority(phase: str, _child: object) -> dict[str, object]:
        events.append(f"authority-{phase}")
        raise RuntimeError("authority clear failed")

    def quiesce(phase: str, _child: object) -> tuple[dict[str, object], ...]:
        events.append(f"quiesce-{phase}")
        return (
            _controller_socket_census(),
            {"active_process_count": 0, "process_list_sha256": "5" * 64},
        )

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_authority_clear_failed",
    ) as exc:
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child("A", events),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=quiesce,
            clear_authority=clear_authority,
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=2,
        )

    assert isinstance(exc.value.__cause__, RuntimeError)
    assert events.index("stop-A") < events.index("authority-A")
    assert events.index("authority-A") < events.index("quiesce-A")
    assert "create-B" not in events
    assert "seal" not in events
    assert all(writer.closed_clean for writer in writers.values())
    runtime_events = [
        record["event"] for record in read_runtime_records(writers["app"].getvalue())
    ]
    assert "authority_cleared" not in runtime_events
    assert runtime_events.index("socket_census") < runtime_events.index("job_zero")
    assert runtime_events.index("job_zero") < runtime_events.index("phase_complete")


def test_task5_controller_phase_a_failure_latches_and_never_creates_b() -> None:
    events: list[str] = []
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    with pytest.raises(DualLiveRuntimeError, match="dual_live_phase_failed"):
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child("A", events, exit_code=9),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda _phase, _child: (
                _controller_socket_census(),
                {"active_process_count": 0, "process_list_sha256": "5" * 64},
            ),
            clear_authority=lambda _phase, _child: {
                "authority_posture_sha256": "6" * 64,
                "all_required_absent": True,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=2,
        )

    assert "create-B" not in events
    assert "seal" not in events
    assert all(writer.closed_clean for writer in writers.values())
    stop_records = [
        record
        for record in read_runtime_records(writers["app"].getvalue())
        if record["event"] == "stop_latched"
    ]
    assert len(stop_records) == 1
    assert stop_records[0]["payload"]["reason_code"] == "child_exit_nonzero"


def test_controller_runtime_start_writer_failure_closes_all_without_child_or_seal() -> None:
    events: list[str] = []
    writers = {
        stream: (
            _FailingControllerWriter(stream, events)
            if stream == "app"
            else _ControllerWriter(stream, events)
        )
        for stream in PIPE_STREAM_CLASSES
    }

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_runtime_writer_failure",
    ):
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: events.append("create-A"),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda _phase, _child: (),
            clear_authority=lambda _phase, _child: {},
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=2,
        )

    assert "create-A" not in events
    assert "create-B" not in events
    assert "seal" not in events
    assert all(writer.closed_clean for writer in writers.values())


def test_late_writer_failure_takes_precedence_over_phase_failure() -> None:
    events: list[str] = []
    writers = {
        stream: (
            _NthFailControllerWriter(
                stream,
                events,
                fail_on_write=8,
            )
            if stream == "app"
            else _ControllerWriter(stream, events)
        )
        for stream in PIPE_STREAM_CLASSES
    }

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_runtime_writer_failure",
    ) as exc:
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child("A", events, exit_code=9),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda _phase, _child: (
                _controller_socket_census(),
                {"active_process_count": 0, "process_list_sha256": "5" * 64},
            ),
            clear_authority=lambda _phase, _child: {
                "authority_posture_sha256": "6" * 64,
                "all_required_absent": True,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=2,
        )

    contexts: list[str] = []
    context = exc.value.__context__
    while context is not None:
        if isinstance(context, DualLiveRuntimeError):
            contexts.append(context.code)
        context = context.__context__
    assert "dual_live_phase_failed" in contexts
    assert "create-B" not in events
    assert "seal" not in events
    assert all(writer.closed_clean for writer in writers.values())


def test_r13_phase_b_survivor_prevents_seal_after_bounded_close() -> None:
    events: list[str] = []
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    def quiesce(phase: str, _child: object) -> tuple[dict[str, object], ...]:
        if phase == "B":
            raise RuntimeError("survivor")
        return (
            _controller_socket_census(),
            {"active_process_count": 0, "process_list_sha256": "5" * 64},
        )

    with pytest.raises(DualLiveRuntimeError, match="dual_live_quiescence_failed"):
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child("A", events),
            create_phase_b=lambda: _controller_child("B", events),
            quiesce_phase=quiesce,
            clear_authority=lambda _phase, _child: {
                "authority_posture_sha256": "6" * 64,
                "all_required_absent": True,
            },
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=2,
        )

    assert "seal" not in events
    assert all(writer.closed_clean for writer in writers.values())
