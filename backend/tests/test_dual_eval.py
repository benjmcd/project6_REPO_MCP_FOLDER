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
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any

import pytest
import test_dual_eval_acceptance as dual_live_acceptance

from app.services import connector_egress_evidence as connector_evidence_module
from app.services import dual_live_evaluator as dual_live_evaluator_module
from app.services import dual_live_runtime as dual_live_runtime_module
from app.services.dual_live_evaluator import (
    CHECKS,
    EVALUATOR_CHECK_ORDER,
    EVALUATOR_NONCLAIMS,
    CheckResult,
    DualLiveEvaluationError,
    _aggregate_check_results,
    build_indeterminate_dual_live_report,
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
    FourStreamPumpGroup as _RuntimeFourStreamPumpGroup,
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
from app.services.layer3_utils import stable_json_text_hash
from app.services.connector_egress_authorization import canonical_json_bytes


BACKEND = Path(__file__).resolve().parents[1]
CAMPAIGN_ID = "123e4567-e89b-42d3-a456-426614174000"
CAMPAIGN_FINGERPRINT = "a" * 64
STATUS_PROCESS_BOOT_ID = "b" * 64
STATUS_NONCE_SHA256 = "c" * 64


@pytest.fixture(scope="module", autouse=True)
def _restore_spawn_primitives_after_dual_eval_module():
    primitives: list[tuple[Any, str, Any]] = [
        (subprocess, "Popen", subprocess.Popen)
    ]
    primitives.extend(
        (os, name, getattr(os, name))
        for name in sorted(dir(os))
        if (
            name == "system"
            or name == "startfile"
            or name.startswith("spawn")
            or name.startswith("exec")
            or name.startswith("posix_spawn")
        )
        and callable(getattr(os, name, None))
    )
    try:
        yield
    finally:
        for owner, name, original in primitives:
            setattr(owner, name, original)


class FourStreamPumpGroup(_RuntimeFourStreamPumpGroup):
    def __init__(self, **kwargs: Any) -> None:
        status_callback = kwargs.get("status_callback")
        if (
            callable(status_callback)
            and len(inspect.signature(status_callback).parameters) == 1
        ):
            kwargs["status_callback"] = (
                lambda value, _frame_sha256: status_callback(value)
            )
        kwargs.setdefault("boot_callback", lambda _frame_sha256: None)
        kwargs.setdefault("proof_callback", lambda _proof: None)
        kwargs.setdefault("expected_control_nonce", "f" * 64)
        kwargs.setdefault("expected_proof_scope", "mechanical")
        super().__init__(**kwargs)


EXPECTED_REPORT = {
    "schema_id": "project6.dual_live_evaluation.v1",
    "campaign_id": CAMPAIGN_ID,
    "expected_campaign_fingerprint": CAMPAIGN_FINGERPRINT,
    "status": "INDETERMINATE",
    "fresh_live": False,
    "evaluation_complete": False,
    "code": "dual_live_evaluation_internal_error",
    "checks": [
        {
            "check_id": check_id,
            "status": "INDETERMINATE",
            "code": "dual_live_evaluation_internal_error",
            "evidence": {},
        }
        for check_id in EVALUATOR_CHECK_ORDER
    ],
    "nonclaims": list(EVALUATOR_NONCLAIMS),
}
RUNTIME_INSTANCE_ID = "223e4567-e89b-42d3-a456-426614174000"
BOOT_ID = "7" * 64
UUID_BOOT_ID = "323e4567-e89b-42d3-a456-426614174000"
PHASE_TIMEOUT_CONTRACT = {
    "schema_id": "project6.dual_live_phase_timeout.v1",
    "phase_a_timeout_ms": 205_750,
    "phase_b_timeout_ms": 30_000,
    "fixed_non_egress_overhead_ms": 30_000,
    "counter_ack_timeout_ms": 5_000,
    "connector_grants": [
        {
            "connector_key": "nrc_adams_aps",
            "max_physical_requests": 2,
            "request_timeout_seconds": 30,
            "min_request_interval_ms": 250,
        },
        {
            "connector_key": "sciencebase_mcs",
            "max_physical_requests": 3,
            "request_timeout_seconds": 30,
            "min_request_interval_ms": 250,
        },
    ],
}
RUNTIME_IDENTITY = RuntimeIdentity(
    runtime_instance_id=RUNTIME_INSTANCE_ID,
    wrapper_nonce_sha256="1" * 64,
    code_revision="2" * 40,
    wrapper_image_sha256="3" * 64,
    interpreter_image_sha256="4" * 64,
    dependency_set_sha256="8" * 64,
    root_mutex_identity_sha256="5" * 64,
    campaign_mutex_identity_sha256="6" * 64,
)
RUNTIME_START_PAYLOAD = {
    "code_revision": RUNTIME_IDENTITY.code_revision,
    "wrapper_image_sha256": RUNTIME_IDENTITY.wrapper_image_sha256,
    "interpreter_image_sha256": RUNTIME_IDENTITY.interpreter_image_sha256,
    "dependency_set_sha256": RUNTIME_IDENTITY.dependency_set_sha256,
    "phase_timeout_contract": PHASE_TIMEOUT_CONTRACT,
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


def test_evaluator_registry_is_exact_complete_and_immutable() -> None:
    expected = tuple(
        f"{prefix}{ordinal:02d}_{name}"
        for prefix, names in (
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
        for ordinal, name in enumerate(names, start=1)
    )

    assert EVALUATOR_CHECK_ORDER == expected
    assert isinstance(EVALUATOR_CHECK_ORDER, tuple)
    assert len(EVALUATOR_CHECK_ORDER) == 69
    assert len(set(EVALUATOR_CHECK_ORDER)) == 69


def test_check_registry_is_literal_ordered_executable_functions() -> None:
    assert isinstance(CHECKS, tuple)
    assert len(CHECKS) == 69
    assert len({function.__name__ for function in CHECKS}) == 69
    assert tuple(
        function.__name__.removeprefix("_check_").upper()
        for function in CHECKS
    ) == EVALUATOR_CHECK_ORDER
    assert all(callable(function) for function in CHECKS)


def test_check_result_is_frozen_and_secret_safe() -> None:
    result = CheckResult(
        check_id="A01_INPUT_IDENTITY",
        status="PASS",
        code="a01_input_identity_pass",
        evidence={"verified": True},
    )

    assert result.as_dict() == {
        "check_id": "A01_INPUT_IDENTITY",
        "status": "PASS",
        "code": "a01_input_identity_pass",
        "evidence": {"verified": True},
    }
    with pytest.raises((AttributeError, TypeError)):
        result.status = "FAIL"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.evidence["verified"] = False  # type: ignore[index]


def test_fixed_aggregation_precedence_is_indeterminate_then_fail_then_pass() -> None:
    passing = tuple(
        CheckResult(check_id=check_id, status="PASS", code="pass", evidence={})
        for check_id in EVALUATOR_CHECK_ORDER
    )
    failing = list(passing)
    failing[7] = CheckResult(
        check_id=EVALUATOR_CHECK_ORDER[7],
        status="FAIL",
        code="failure",
        evidence={},
    )
    indeterminate = list(failing)
    indeterminate[-1] = CheckResult(
        check_id=EVALUATOR_CHECK_ORDER[-1],
        status="INDETERMINATE",
        code="uncertain",
        evidence={},
    )

    assert _aggregate_check_results(passing) == ("PASS", "all_checks_pass")
    assert _aggregate_check_results(tuple(failing)) == ("FAIL", "failure")
    assert _aggregate_check_results(tuple(indeterminate)) == (
        "INDETERMINATE",
        "uncertain",
    )


def test_gate_owned_indeterminate_report_uses_fixed_evaluator_shape() -> None:
    report = build_indeterminate_dual_live_report(
        campaign_id=CAMPAIGN_ID,
        expected_campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        code="dual_live_database_changed_during_evaluation",
    )

    assert list(report) == [
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
    assert report["status"] == "INDETERMINATE"
    assert report["fresh_live"] is False
    assert report["evaluation_complete"] is False
    assert report["code"] == "dual_live_database_changed_during_evaluation"
    assert [item["check_id"] for item in report["checks"]] == list(
        EVALUATOR_CHECK_ORDER
    )
    assert {
        (item["status"], item["code"]) for item in report["checks"]
    } == {
        (
            "INDETERMINATE",
            "dual_live_database_changed_during_evaluation",
        )
    }
    assert report["nonclaims"] == list(EVALUATOR_NONCLAIMS)


def test_gate_owned_indeterminate_report_rejects_unsafe_code() -> None:
    with pytest.raises(DualLiveEvaluationError) as caught:
        build_indeterminate_dual_live_report(
            campaign_id=CAMPAIGN_ID,
            expected_campaign_fingerprint=CAMPAIGN_FINGERPRINT,
            code="unsafe code: secret-value",
        )

    assert caught.value.code == "dual_live_result_code_invalid"


def test_evaluator_refuses_pending_session_state_before_dependency_access() -> None:
    class PendingSession:
        new = (object(),)
        dirty: tuple[object, ...] = ()
        deleted: tuple[object, ...] = ()

        def __getattribute__(self, name: str) -> object:
            if name in {"new", "dirty", "deleted"}:
                return object.__getattribute__(self, name)
            raise AssertionError(f"unexpected dependency access: {name}")

    report = evaluate_dual_live_proof(
        PendingSession(),  # type: ignore[arg-type]
        campaign_id=CAMPAIGN_ID,
        expected_campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
    )

    assert report["status"] == "INDETERMINATE"
    assert report["code"] == "dual_live_evaluation_pending_session_state"


def test_origin_absence_returns_exact_69_ordered_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    errors = {"origin": "dual_live_origin_receipt_unavailable"}
    dual_live_evaluator_module._materialize_dependency_errors(errors)
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=SimpleNamespace(new=(), dirty=(), deleted=()),
        domain_errors=errors,
    )
    monkeypatch.setattr(
        dual_live_evaluator_module,
        "_collect_evidence",
        lambda *_args, **_kwargs: context,
    )

    results = dual_live_evaluator_module._run_dual_live_checks(
        NoAccess(),
        campaign_id=CAMPAIGN_ID,
        expected_campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
    )

    assert len(results) == 69
    assert tuple(result.check_id for result in results) == EVALUATOR_CHECK_ORDER
    assert all(isinstance(result, CheckResult) for result in results)


def test_origin_failure_structurally_blocks_phase_b_sources_for_r17() -> None:
    reason_code = "dual_live_origin_receipt_unavailable"
    errors = {"origin": reason_code}
    dual_live_evaluator_module._materialize_dependency_errors(errors)

    assert errors["phase_b_sources"] == reason_code

    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
        domain_errors=errors,
    )
    result = dual_live_evaluator_module._check_r17_phase_b_strict_flow(
        context
    )

    assert result.status == "INDETERMINATE"
    assert result.code == "r17_phase_b_strict_flow_evidence_unavailable"
    assert result.evidence == {
        "domain": "downstream",
        "reason_code": reason_code,
    }


@pytest.mark.parametrize(
    "reason_code",
    (
        "dual_live_phase_b_source_missing",
        "dual_live_phase_b_source_invalid",
    ),
)
def test_phase_b_source_failure_structurally_blocks_downstream_for_r17(
    reason_code: str,
) -> None:
    errors = {"phase_b_sources": reason_code}
    dual_live_evaluator_module._materialize_dependency_errors(errors)

    assert errors["downstream"] == reason_code
    assert errors["execution"] == reason_code
    assert errors["review"] == reason_code
    assert errors["package_set"] == reason_code
    assert errors["submit"] == reason_code
    assert errors["handoff"] == reason_code
    assert errors["custody"] == reason_code

    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
        domain_errors=errors,
    )
    result = dual_live_evaluator_module._check_r17_phase_b_strict_flow(
        context
    )

    assert result.status == "INDETERMINATE"
    assert result.code == "r17_phase_b_strict_flow_evidence_unavailable"
    assert result.evidence == {
        "domain": "downstream",
        "reason_code": reason_code,
    }


def test_domain_error_preserves_secret_safe_reason_code() -> None:
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
        domain_errors={
            "capture": "connector_campaign_log_read_object_oversized",
        },
    )

    result = dual_live_evaluator_module._domain_error(
        context,
        "R01_CAPTURE_MEMBERSHIP",
        "capture",
    )

    assert result is not None
    assert result.as_dict() == {
        "check_id": "R01_CAPTURE_MEMBERSHIP",
        "status": "INDETERMINATE",
        "code": "r01_capture_membership_evidence_unavailable",
        "evidence": {
            "domain": "capture",
            "reason_code": "connector_campaign_log_read_object_oversized",
        },
    }


@pytest.mark.parametrize(
    ("checker", "component", "check_id"),
    (
        (
            dual_live_evaluator_module._check_r02_manifest_file_hashes,
            "streams",
            "R02_MANIFEST_FILE_HASHES",
        ),
        (
            dual_live_evaluator_module._check_r03_seal_parity,
            "manifest",
            "R03_SEAL_PARITY",
        ),
        (
            dual_live_evaluator_module._check_r04_seal_event_parity,
            "events",
            "R04_SEAL_EVENT_PARITY",
        ),
    ),
)
def test_independent_capture_read_error_preserves_exact_taxonomy(
    checker: Callable[..., CheckResult],
    component: str,
    check_id: str,
) -> None:
    reason_code = "connector_campaign_log_read_changed"
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
        independent_capture=(
            dual_live_evaluator_module._IndependentCaptureEvidence(
                errors=MappingProxyType({component: reason_code}),
            )
        ),
        domain_errors={
            "capture": "connector_campaign_log_manifest_hash_mismatch",
        },
    )

    assert checker(context).as_dict() == {
        "check_id": check_id,
        "status": "INDETERMINATE",
        "code": f"{check_id.lower()}_evidence_unavailable",
        "evidence": {
            "domain": "capture",
            "reason_code": reason_code,
        },
    }


def test_independent_observation_engine_preserves_caller_transaction(
    tmp_path: Path,
) -> None:
    from sqlalchemy import create_engine

    database_path = tmp_path / "observer.db"
    caller_engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        future=True,
    )
    with caller_engine.begin() as setup_connection:
        setup_connection.exec_driver_sql(
            "CREATE TABLE observer_probe (value INTEGER NOT NULL)"
        )
    caller_connection = caller_engine.connect()
    caller_transaction = caller_connection.begin()
    try:
        caller_connection.exec_driver_sql(
            "INSERT INTO observer_probe (value) VALUES (1)"
        )
        assert caller_connection.exec_driver_sql(
            "SELECT COUNT(*) FROM observer_probe"
        ).scalar_one() == 1

        observation_engine = (
            dual_live_evaluator_module._build_independent_observation_engine(
                SimpleNamespace(
                    database_url=(
                        f"sqlite:///{database_path.as_posix()}"
                    )
                )
            )
        )
        try:
            with observation_engine.connect() as observation_connection:
                assert observation_connection.exec_driver_sql(
                    "PRAGMA query_only"
                ).scalar_one() == 1
                assert observation_connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM observer_probe"
                ).scalar_one() == 0
        finally:
            observation_engine.dispose()

        assert caller_connection.in_transaction()
        assert caller_connection.exec_driver_sql(
            "SELECT COUNT(*) FROM observer_probe"
        ).scalar_one() == 1
    finally:
        if caller_transaction.is_active:
            caller_transaction.rollback()
        caller_connection.close()
        caller_engine.dispose()


def _ledger_entry(*, ordinal: int, stage: str, fingerprint: str) -> dict[str, object]:
    return {
        "ordinal": ordinal,
        "stage": stage,
        "request_fingerprint": fingerprint,
        "response_status": 200,
        "byte_count": 4,
        "body_sha256": "d" * 64,
        "send_started_at": "2026-07-31T00:00:00.000000Z",
    }


def _counter_record(*, ordinal: int, stage: str, fingerprint: str) -> dict[str, object]:
    return {
        "ordinal": ordinal,
        "stage": stage,
        "request_fingerprint": fingerprint,
        "response_status": 200,
        "decoded_body_bytes": 4,
        "decoded_body_sha256": "d" * 64,
    }


def test_l05_binds_counter_order_to_nrc_then_sciencebase_ledgers() -> None:
    nrc = SimpleNamespace(
        connector_run_id="run-nrc",
        entries=(_ledger_entry(ordinal=1, stage="nrc", fingerprint="1" * 64),),
    )
    sciencebase = SimpleNamespace(
        connector_run_id="run-sciencebase",
        entries=(
            _ledger_entry(
                ordinal=1,
                stage="sciencebase",
                fingerprint="2" * 64,
            ),
        ),
    )
    ordered = (
        _counter_record(ordinal=1, stage="nrc", fingerprint="1" * 64),
        _counter_record(
            ordinal=1,
            stage="sciencebase",
            fingerprint="2" * 64,
        ),
    )
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
        ledgers={"nrc_adams_aps": nrc, "sciencebase_mcs": sciencebase},
        counter_records=ordered,
    )

    passing = dual_live_evaluator_module._check_l05_counter_bijection(context)
    changed = dual_live_evaluator_module._check_l05_counter_bijection(
        replace(
            context,
            counter_records=tuple(reversed(ordered)),
        )
    )

    assert (passing.status, passing.code) == (
        "PASS",
        "l05_counter_bijection_pass",
    )
    assert (changed.status, changed.code) == (
        "INDETERMINATE",
        "l05_counter_ledger_bijection_invalid",
    )


def test_l03_rejects_same_timestamp_post_terminal_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instant = datetime(2026, 7, 31, tzinfo=timezone.utc)
    run = SimpleNamespace(connector_run_id="run-nrc")
    events = (
        SimpleNamespace(
            event_type="egress_run_terminal",
            created_at=instant,
            status_after="completed",
        ),
        SimpleNamespace(
            event_type="failed",
            created_at=instant,
            status_after="failed",
        ),
    )
    monkeypatch.setattr(
        dual_live_evaluator_module,
        "_run_events",
        lambda _context, _run: events,
    )
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
        runs=(run,),
    )

    result = dual_live_evaluator_module._check_l03_post_terminal_extinction(
        context
    )

    assert (result.status, result.code) == (
        "FAIL",
        "l03_post_terminal_contradiction",
    )


def test_source_blob_rejects_parent_traversal_before_read(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    (tmp_path / "outside.bin").write_bytes(b"outside")
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=SimpleNamespace(connector_raw_dir=raw_root),
        db=NoAccess(),
    )

    with pytest.raises(DualLiveEvaluationError) as caught:
        dual_live_evaluator_module._source_blob(context, "../outside.bin")

    assert caught.value.code == "dual_live_source_ref_outside_root"


def _guard_unsafe_filesystem_touch(
    monkeypatch: pytest.MonkeyPatch,
    unsafe_root: str,
) -> None:
    original_exists = Path.exists
    original_resolve = Path.resolve
    original_lstat = Path.lstat
    original_open = Path.open
    original_scandir = os.scandir

    def is_unsafe(value: object) -> bool:
        return str(value).casefold().startswith(unsafe_root.casefold())

    def exists(path: Path) -> bool:
        if is_unsafe(path):
            raise AssertionError("unsafe path exists() touched")
        return original_exists(path)

    def resolve(path: Path, *args: object, **kwargs: object) -> Path:
        if is_unsafe(path):
            raise AssertionError("unsafe path resolve() touched")
        return original_resolve(path, *args, **kwargs)

    def lstat(path: Path, *args: object, **kwargs: object) -> os.stat_result:
        if is_unsafe(path):
            raise AssertionError("unsafe path lstat() touched")
        return original_lstat(path, *args, **kwargs)

    def open_path(path: Path, *args: object, **kwargs: object) -> object:
        if is_unsafe(path):
            raise AssertionError("unsafe path open() touched")
        return original_open(path, *args, **kwargs)

    def scandir(path: object) -> object:
        if is_unsafe(path):
            raise AssertionError("unsafe path scandir() touched")
        return original_scandir(path)

    monkeypatch.setattr(Path, "exists", exists)
    monkeypatch.setattr(Path, "resolve", resolve)
    monkeypatch.setattr(Path, "lstat", lstat)
    monkeypatch.setattr(Path, "open", open_path)
    monkeypatch.setattr(os, "scandir", scandir)


@pytest.mark.parametrize(
    "unsafe_root",
    (
        r"\\server\share\evidence",
        r"\\?\C:\evidence",
        r"\\.\C:\evidence",
        r"C:\evidence:stream",
        r"C:\CON\evidence",
        "C:\\evidence. ",
    ),
)
def test_non_source_root_rejects_unsafe_windows_alias_before_touch(
    monkeypatch: pytest.MonkeyPatch,
    unsafe_root: str,
) -> None:
    _guard_unsafe_filesystem_touch(monkeypatch, unsafe_root)

    with pytest.raises(DualLiveEvaluationError) as caught:
        dual_live_evaluator_module._collect_non_source_files(
            _non_source_settings(Path(unsafe_root)),
            source_exemptions=(),
        )

    assert caught.value.code == "dual_live_scan_root_unsafe"


@pytest.mark.parametrize(
    "unsafe_root",
    (
        r"\\server\share\raw",
        r"\\?\C:\raw",
        r"\\.\C:\raw",
        r"C:\raw:stream",
        r"C:\AUX\raw",
        "C:\\raw. ",
    ),
)
def test_source_root_rejects_unsafe_windows_alias_before_touch(
    monkeypatch: pytest.MonkeyPatch,
    unsafe_root: str,
) -> None:
    _guard_unsafe_filesystem_touch(monkeypatch, unsafe_root)
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=SimpleNamespace(connector_raw_dir=unsafe_root),
        db=NoAccess(),
    )

    with pytest.raises(DualLiveEvaluationError) as caught:
        dual_live_evaluator_module._source_blob(context, "blob.bin")

    assert caught.value.code == "dual_live_source_root_invalid"


@pytest.mark.parametrize(
    "unsafe_path",
    (
        r"\\server\share\proof.sqlite",
        r"\\?\C:\proof.sqlite",
        r"C:\proof.sqlite:stream",
        r"Z:\proof.sqlite",
    ),
)
def test_database_path_rejects_remote_alias_before_touch(
    monkeypatch: pytest.MonkeyPatch,
    unsafe_path: str,
) -> None:
    _guard_unsafe_filesystem_touch(monkeypatch, unsafe_path)

    with pytest.raises(DualLiveEvaluationError) as caught:
        dual_live_evaluator_module._database_path(
            SimpleNamespace(database_url=f"sqlite:///{unsafe_path}")
        )

    assert caught.value.code in {
        "dual_live_database_path_unsafe",
        "dual_live_database_url_invalid",
    }


@pytest.mark.parametrize(
    "unsafe_root",
    (
        r"\\server\share\evidence",
        r"\\?\C:\evidence",
        r"C:\evidence:stream",
        r"Z:\evidence",
    ),
)
def test_evidence_root_rejects_remote_alias_before_touch(
    monkeypatch: pytest.MonkeyPatch,
    unsafe_root: str,
) -> None:
    _guard_unsafe_filesystem_touch(monkeypatch, unsafe_root)

    with pytest.raises(DualLiveEvaluationError) as caught:
        dual_live_evaluator_module._preflight_evidence_settings(
            SimpleNamespace(
                connector_campaign_evidence_root=unsafe_root,
                connector_campaign_evidence_index_path=(
                    f"{unsafe_root}\\indexes\\{'a' * 64}.json"
                ),
                connector_campaign_evidence_index_sha256="a" * 64,
            )
        )

    assert caught.value.code == "dual_live_evidence_root_unsafe"


@pytest.mark.parametrize(
    "unsafe_root",
    (
        r"\\server\share\evidence",
        r"\\?\C:\evidence",
        r"C:\evidence:stream",
        r"Z:\evidence",
    ),
)
def test_evidence_leaf_rejects_remote_alias_before_touch(
    monkeypatch: pytest.MonkeyPatch,
    unsafe_root: str,
) -> None:
    _guard_unsafe_filesystem_touch(monkeypatch, unsafe_root)

    with pytest.raises(connector_evidence_module.ConnectorEvidenceError) as caught:
        connector_evidence_module._evidence_root(
            SimpleNamespace(connector_campaign_evidence_root=unsafe_root)
        )

    assert caught.value.code == "connector_evidence_path_invalid"


def test_evidence_leaf_binds_open_file_to_expected_fixed_local_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"proof")
    monkeypatch.setattr(
        connector_evidence_module,
        "_opened_fixed_local_evidence_path",
        lambda _handle: tmp_path / "other.bin",
    )

    with pytest.raises(connector_evidence_module.ConnectorEvidenceError) as caught:
        connector_evidence_module._read_evidence_file(
            tmp_path,
            source.name,
            max_bytes=16,
        )

    assert caught.value.code == "connector_evidence_path_invalid"


def test_evidence_leaf_reads_fixed_local_file_with_handle_binding(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"proof")

    snapshot = connector_evidence_module._read_evidence_file(
        tmp_path,
        source.name,
        max_bytes=16,
    )

    assert snapshot.data == b"proof"
    assert snapshot.sha256 == hashlib.sha256(b"proof").hexdigest()


def test_f06_evaluator_source_has_no_write_or_egress_dependency() -> None:
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
    )

    result = dual_live_evaluator_module._check_f06_no_egress_dependency(context)

    assert (result.status, result.code) == (
        "PASS",
        "f06_no_egress_dependency_pass",
    )


def test_f06_recursive_source_closure_detects_all_import_forms(tmp_path: Path) -> None:
    package = tmp_path / "fixture"
    package.mkdir()
    (package / "__init__.py").write_text(
        "from .entry import run\n",
        encoding="utf-8",
    )
    (package / "entry.py").write_text(
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from . import typed\n"
        "def run():\n"
        "    from . import local\n"
        "    return local.value\n",
        encoding="utf-8",
    )
    (package / "local.py").write_text(
        "import importlib\n"
        "value = importlib.import_module('socket')\n",
        encoding="utf-8",
    )
    (package / "typed.py").write_text("import requests\n", encoding="utf-8")

    closure = dual_live_evaluator_module._reachable_source_imports(
        ("fixture.entry",),
        source_root=tmp_path,
    )

    assert set(closure) >= {
        "fixture",
        "fixture.entry",
        "fixture.local",
        "fixture.typed",
        "requests",
        "socket",
    }


def _patch_f06_evaluator_source(
    monkeypatch: pytest.MonkeyPatch,
    source: str,
) -> None:
    original_read = dual_live_evaluator_module._stable_bounded_read
    evaluator_path = Path(dual_live_evaluator_module.__file__).resolve()

    def source_read(path: Path, *args: Any, **kwargs: Any) -> bytes:
        if Path(path).resolve() == evaluator_path:
            return source.encode("utf-8")
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(
        dual_live_evaluator_module,
        "_stable_bounded_read",
        source_read,
    )


def test_f06_allows_local_database_engine_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_f06_evaluator_source(
        monkeypatch,
        "with engine.connect() as connection:\n    pass\n",
    )
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
    )

    result = dual_live_evaluator_module._check_f06_no_egress_dependency(context)

    assert (result.status, result.code) == (
        "PASS",
        "f06_no_egress_dependency_pass",
    )


@pytest.mark.parametrize("qualified_call", ("requests.connect()", "socket.connect()"))
def test_f06_rejects_network_qualified_connect(
    monkeypatch: pytest.MonkeyPatch,
    qualified_call: str,
) -> None:
    _patch_f06_evaluator_source(
        monkeypatch,
        f"{qualified_call}\n",
    )
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
    )

    result = dual_live_evaluator_module._check_f06_no_egress_dependency(context)

    assert (result.status, result.code) == (
        "FAIL",
        "f06_write_or_egress_call_present",
    )


def test_l09_uses_the_canonical_read_only_transport_rule_tables() -> None:
    rule = SimpleNamespace(
        stage="exact_accession_api",
        method="GET",
        allowed_hosts=("adams.nrc.gov",),
        path_rule_id="nrc_get_document_exact_v1",
        query_rule_id="none_v1",
        credential_audience="nrc-aps",
    )
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
        historical={
            "nrc_adams_aps": SimpleNamespace(
                model=SimpleNamespace(request_rules=(rule,))
            ),
        },
        ledgers={
            "nrc_adams_aps": SimpleNamespace(
                entries=(
                    {
                        "stage": rule.stage,
                        "method": rule.method,
                        "host": rule.allowed_hosts[0],
                        "path_class": "nrc_accession_exact",
                        "query_class": "none",
                        "credential_audience": rule.credential_audience,
                    },
                )
            )
        },
    )

    result = dual_live_evaluator_module._check_l09_transport_policy(context)

    assert (result.status, result.code) == (
        "PASS",
        "l09_transport_policy_pass",
    )


def test_decoder_accepts_two_layers_and_rejects_any_third_layer() -> None:
    forms = dual_live_evaluator_module._decoded_forms(
        b"https&amp;#58;&amp;#47;&amp;#47;example.com",
        strict_utf8=True,
    )

    assert "https://example.com" in forms
    with pytest.raises(DualLiveEvaluationError) as caught:
        dual_live_evaluator_module._decoded_forms(
            b"https&amp;amp;#58;&amp;amp;#47;&amp;amp;#47;example.com",
            strict_utf8=True,
        )
    assert caught.value.code == "dual_live_scan_third_encoding_layer"


def test_decoder_preserves_literal_percent_and_decodes_real_escape() -> None:
    forms = dual_live_evaluator_module._decoded_forms(
        b"%PDF-1.7 progress=100%25 complete",
        strict_utf8=True,
    )

    assert "%PDF-1.7 progress=100% complete" in forms


def test_decoder_rejects_percent_escape_with_invalid_utf8() -> None:
    with pytest.raises(DualLiveEvaluationError) as caught:
        dual_live_evaluator_module._decoded_forms(
            b"invalid=%FF",
            strict_utf8=True,
        )

    assert caught.value.code == "dual_live_scan_percent_encoding_invalid"


@pytest.mark.parametrize(
    "payload",
    (
        b"\xffhttps%3A%2F%2Fexample.com",
        b"\xffhttps&#58;&#47;&#47;example.com",
        b"\xffhttps\\u003a\\u002f\\u002fexample.com",
    ),
)
def test_binary_decoder_still_decodes_ascii_escape_regions(payload: bytes) -> None:
    forms = dual_live_evaluator_module._decoded_forms(
        payload,
        strict_utf8=False,
    )

    assert any("https://example.com" in form for form in forms)


def test_binary_decoder_still_rejects_third_encoding_layer() -> None:
    with pytest.raises(DualLiveEvaluationError) as caught:
        dual_live_evaluator_module._decoded_forms(
            b"\xffhttps%25253A%25252F%25252Fexample.com",
            strict_utf8=False,
        )

    assert caught.value.code == "dual_live_scan_third_encoding_layer"


def test_canonical_bytes_thaws_frozen_package_mappings() -> None:
    frozen = MappingProxyType(
        {
            "nested": MappingProxyType({"value": "ok"}),
            "rows": (MappingProxyType({"ordinal": 1}),),
        }
    )

    assert dual_live_evaluator_module._canonical_bytes(frozen) == (
        b'{"nested":{"value":"ok"},"rows":[{"ordinal":1}]}'
    )


def _non_source_settings(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        connector_reports_dir=root,
        connector_manifests_dir="",
        connector_snapshots_dir="",
        artifact_storage_dir="",
        dataset_storage_dir="",
        layer3_local_outbox_dir="",
    )


def test_non_source_file_cap_is_checked_before_any_file_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "reports"
    root.mkdir()
    (root / "a.txt").write_bytes(b"a")
    (root / "b.txt").write_bytes(b"b")
    monkeypatch.setattr(dual_live_evaluator_module, "MAX_SCAN_FILES", 1)
    monkeypatch.setattr(
        Path,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("file read occurred before cardinality refusal")
        ),
    )

    with pytest.raises(DualLiveEvaluationError) as caught:
        dual_live_evaluator_module._collect_non_source_files(
            _non_source_settings(root),
            source_exemptions=(),
        )

    assert caught.value.code == "dual_live_scan_file_cap_exceeded"


def test_non_source_scan_does_not_exempt_same_relative_name_in_another_root(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    report_root = tmp_path / "reports"
    raw_root.mkdir()
    report_root.mkdir()
    source_payload = b"bound raw source"
    reflected = b"reflected-secret"
    (raw_root / "shared.bin").write_bytes(source_payload)
    (report_root / "shared.bin").write_bytes(reflected)
    settings = _non_source_settings(report_root)
    settings.connector_raw_dir = raw_root

    files = dual_live_evaluator_module._collect_non_source_files(
        settings,
        source_exemptions=(
            ("shared.bin", hashlib.sha256(source_payload).hexdigest()),
        ),
    )

    assert files == (("root-0:shared.bin", reflected),)


def test_source_size_cap_is_checked_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "raw"
    root.mkdir()
    oversized = root / "oversized.bin"
    with oversized.open("wb") as handle:
        handle.truncate(2)
    monkeypatch.setattr(dual_live_evaluator_module, "MAX_SOURCE_BYTES", 1)
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=SimpleNamespace(connector_raw_dir=root),
        db=NoAccess(),
    )
    monkeypatch.setattr(
        Path,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("oversized source was opened")
        ),
    )

    with pytest.raises(DualLiveEvaluationError) as caught:
        dual_live_evaluator_module._source_blob(context, "oversized.bin")

    assert caught.value.code == "dual_live_source_blob_size_invalid"


def test_r11_requires_exact_authority_posture_digest() -> None:
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
        runtime_records=(
            {
                "phase": "A",
                "event": "authority_cleared",
                "payload": {
                    "all_required_absent": True,
                    "authority_posture_sha256": "0" * 64,
                },
            },
        ),
    )

    result = dual_live_evaluator_module._check_r11_authority_cleared(context)

    assert (result.status, result.code) == (
        "FAIL",
        "r11_authority_not_cleared",
    )


def test_r11_accepts_only_bound_authority_posture_digest() -> None:
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
        runtime_records=(
            {
                "phase": "A",
                "event": "authority_cleared",
                "payload": {
                    "all_required_absent": True,
                    "authority_posture_sha256": (
                        "59629217f25b985366b9b16a9f6bd7b9"
                        "a45d5544375dc04f847f1b7bc1e07cd2"
                    ),
                },
            },
        ),
    )

    result = dual_live_evaluator_module._check_r11_authority_cleared(context)

    assert (result.status, result.code) == (
        "PASS",
        "r11_authority_cleared_pass",
    )


def _production_phase_proof_material(
    *,
    phase: str,
    process_boot_id: str,
    status_nonce_sha256: str,
    control_nonce: str,
) -> SimpleNamespace:
    boot_payload = canonical_json_bytes(
        {
            "control_nonce": control_nonce,
            "phase": phase,
            "process_boot_id": process_boot_id,
            "schema_id": dual_live_runtime_module.CHILD_BOOT_SCHEMA_ID,
            "status_nonce_sha256": status_nonce_sha256,
        }
    )
    boot_frame = dual_live_runtime_module.encode_pipe_frame(boot_payload)
    status_frames = tuple(
        dual_live_runtime_module.encode_child_status_frame(
            phase=phase,
            event="logger_census",
            process_boot_id=process_boot_id,
            status_nonce_sha256=status_nonce_sha256,
            ordinal=ordinal,
            payload={
                "census_point": point,
                "handler_count": 1,
                "topology_sha256": "9" * 64,
            },
        )
        for ordinal, point in ((1, "pre_activity"), (2, "exit"))
    )
    control_frame = encode_child_control_frame(
        phase=phase,
        command="GO",
        control_nonce=control_nonce,
    )
    common = {
        "boot_frame_sha256": hashlib.sha256(boot_frame).hexdigest(),
        "control_nonce_sha256": hashlib.sha256(
            control_nonce.encode("ascii")
        ).hexdigest(),
        "pre_activity_status_frame_sha256": hashlib.sha256(
            status_frames[0]
        ).hexdigest(),
        "proof_scope": "production",
    }
    terminal = {
        **common,
        "control_frame_sha256": hashlib.sha256(control_frame).hexdigest(),
        "exit_status_frame_sha256": hashlib.sha256(status_frames[1]).hexdigest(),
    }
    runtime_records = (
        {
            "phase": phase,
            "event": "phase_child_start",
            "process_boot_id": process_boot_id,
            "payload": CHILD_START_PAYLOAD,
        },
        {
            "phase": phase,
            "event": "logger_census",
            "process_boot_id": process_boot_id,
            "payload": {
                "census_point": "pre_activity",
                "topology_sha256": "9" * 64,
                "handler_count": 1,
                "guard_state": f"{phase}_CENSUS_OK",
                "topology_matches_initial": True,
            },
        },
        {
            "phase": phase,
            "event": "phase_go",
            "process_boot_id": process_boot_id,
            "payload": {
                "prior_state": f"{phase}_CENSUS_OK",
                "next_state": f"{phase}_GO",
                "control_nonce_sha256": common["control_nonce_sha256"],
            },
        },
        {
            "phase": phase,
            "event": "logger_census",
            "process_boot_id": process_boot_id,
            "payload": {
                "census_point": "exit",
                "topology_sha256": "9" * 64,
                "handler_count": 1,
                "guard_state": f"{phase}_STOPPED",
                "topology_matches_initial": True,
            },
        },
    )
    return SimpleNamespace(
        boot_payload=boot_payload,
        common=common,
        terminal=terminal,
        runtime_records=runtime_records,
    )


def _production_child_proof_materials() -> tuple[SimpleNamespace, SimpleNamespace]:
    return (
        _production_phase_proof_material(
            phase="A",
            process_boot_id="1" * 64,
            status_nonce_sha256="3" * 64,
            control_nonce="5" * 64,
        ),
        _production_phase_proof_material(
            phase="B",
            process_boot_id="2" * 64,
            status_nonce_sha256="4" * 64,
            control_nonce="6" * 64,
        ),
    )


def _production_child_proof_stdout() -> bytes:
    phase_a, phase_b = _production_child_proof_materials()
    phase_a_boot = "1" * 64
    phase_b_boot = "2" * 64
    phase_a_status = "3" * 64
    phase_b_status = "4" * 64
    common_a = phase_a.terminal
    common_b = phase_b.common
    terminal_b = phase_b.terminal
    acquisitions = [
        {
            "action_codes": [
                "derived_arming",
                "raw_acquisition",
                "terminal_transition",
            ],
            "connector_key": connector_key,
            "connector_run_id": f"run-{connector_key}",
            "connector_run_target_id": f"target-{connector_key}",
            "ledger_terminal_hash": ("f" if ordinal == 1 else "0") * 64,
            "raw_content_sha256": ("1" if ordinal == 1 else "2") * 64,
            "terminal_transition_count": 1,
        }
        for ordinal, connector_key in enumerate(
            ("nrc_adams_aps", "sciencebase_mcs"),
            start=1,
        )
    ]
    bindings = [
        {
            "analysis_plan_id": f"plan-{connector_key}",
            "analysis_run_id": None,
            "candidate_id": f"candidate-{connector_key}",
            "connector_key": connector_key,
            "connector_origin_receipt_hash": (
                "3" if ordinal == 1 else "4"
            )
            * 64,
            "connector_run_id": f"run-{connector_key}",
            "connector_run_target_id": f"target-{connector_key}",
            "construction_basis_hash": (
                "5" if ordinal == 1 else "6"
            )
            * 64,
            "handoff_export_envelope_ref": f"envelope-{connector_key}",
            "output_package_ids": [
                f"package-{connector_key}-{package_ordinal}"
                for package_ordinal in range(3)
            ],
            "package_kinds": [
                "canonical_internal",
                "user_facing",
                "review_facing",
            ],
            "package_review_preview_hash": (
                "l3-qual-aps-package-preview-7777777777777777"
                if ordinal == 1
                else "l3-source-intake-package-preview-8888888888888888"
            ),
            "package_review_submit_record_ref": f"submit-{connector_key}",
            "pass_run_id": f"pass-{connector_key}",
            "payload_hashes": [
                f"{ordinal * 3 + package_ordinal:064x}"
                for package_ordinal in range(3)
            ],
            "prepare_record_ref": f"prepare-{connector_key}",
            "reconciliation_record_id": f"reconciliation-{connector_key}",
            "result_review_record_ref": f"review-{connector_key}",
            "session_id": f"session-{connector_key}",
            "source_shape": (
                "aps_content_document"
                if connector_key == "nrc_adams_aps"
                else "strict_sciencebase_connector_single_source"
            ),
            "source_record_id": f"source-{connector_key}",
        }
        for ordinal, connector_key in enumerate(
            ("nrc_adams_aps", "sciencebase_mcs"),
            start=1,
        )
    ]
    frames: list[bytes] = []
    frames.append(
        dual_live_runtime_module.encode_child_proof_frame(
            phase="A",
            event="acquisition_boundary",
            process_boot_id=phase_a_boot,
            status_nonce_sha256=phase_a_status,
            ordinal=1,
            previous_record_sha256=None,
            payload={
                **common_a,
                "connector_acquisitions": acquisitions,
                "downstream_action_count": 0,
            },
        )
    )
    phase_b_pre = dual_live_runtime_module.encode_child_proof_frame(
        phase="B",
        event="guard",
        process_boot_id=phase_b_boot,
        status_nonce_sha256=phase_b_status,
        ordinal=1,
        previous_record_sha256=None,
        payload={
            **common_b,
            "denied_routes": [
                "dns",
                "http",
                "socket",
                "subprocess",
                "connector_transport",
            ],
            "network_enable_attempt_count": 0,
            "original_implementation_call_count": 0,
            "proof_point": "pre_go",
        },
    )
    frames.append(phase_b_pre)
    predecessor = json.loads(phase_b_pre[4:].decode("utf-8"))["record_sha256"]
    phase_b_chain = dual_live_runtime_module.encode_child_proof_frame(
        phase="B",
        event="downstream_chain",
        process_boot_id=phase_b_boot,
        status_nonce_sha256=phase_b_status,
        ordinal=2,
        previous_record_sha256=predecessor,
        payload={
            **terminal_b,
            "action_receipts": [
                {
                    "action": action,
                    "result_sha256": f"{index:064x}",
                }
                for index, action in enumerate(
                    dual_live_evaluator_module._PHASE_B_DOWNSTREAM_ACTIONS,
                    start=1,
                )
            ],
            "downstream_actions": list(
                dual_live_evaluator_module._PHASE_B_DOWNSTREAM_ACTIONS
            ),
            "source_bindings": bindings,
            "terminal_boundary": "handoff_prepared",
        },
    )
    frames.append(phase_b_chain)
    predecessor = json.loads(phase_b_chain[4:].decode("utf-8"))["record_sha256"]
    frames.append(
        dual_live_runtime_module.encode_child_proof_frame(
            phase="B",
            event="guard",
            process_boot_id=phase_b_boot,
            status_nonce_sha256=phase_b_status,
            ordinal=3,
            previous_record_sha256=predecessor,
            payload={
                **terminal_b,
                "denied_routes": [
                    "dns",
                    "http",
                    "socket",
                    "subprocess",
                    "connector_transport",
                ],
                "network_enable_attempt_count": 0,
                "original_implementation_call_count": 0,
                "proof_point": "exit",
            },
        )
    )
    return b"".join(frame[4:] + b"\n" for frame in frames)


def test_child_proof_parser_accepts_exact_production_sequence() -> None:
    records = dual_live_evaluator_module._parse_child_proof_records(
        _production_child_proof_stdout()
    )

    assert tuple(
        (record["phase"], record["ordinal"], record["event"])
        for record in records
    ) == (
        ("A", 1, "acquisition_boundary"),
        ("B", 1, "guard"),
        ("B", 2, "downstream_chain"),
        ("B", 3, "guard"),
    )


def test_child_proofs_bind_to_boot_status_control_and_runtime() -> None:
    phase_a, phase_b = _production_child_proof_materials()
    records = dual_live_evaluator_module._parse_child_proof_records(
        _production_child_proof_stdout()
    )

    dual_live_evaluator_module._validate_child_proof_runtime_bindings(
        child_proofs=records,
        runtime_records=phase_a.runtime_records + phase_b.runtime_records,
        app_log=phase_a.boot_payload + b"\n" + phase_b.boot_payload + b"\n",
    )


def test_child_proofs_reject_changed_runtime_control_binding() -> None:
    phase_a, phase_b = _production_child_proof_materials()
    records = dual_live_evaluator_module._parse_child_proof_records(
        _production_child_proof_stdout()
    )
    runtime_records = list(phase_a.runtime_records + phase_b.runtime_records)
    changed = dict(runtime_records[2])
    changed["payload"] = {
        **changed["payload"],
        "control_nonce_sha256": "0" * 64,
    }
    runtime_records[2] = changed

    with pytest.raises(DualLiveEvaluationError) as caught:
        dual_live_evaluator_module._validate_child_proof_runtime_bindings(
            child_proofs=records,
            runtime_records=runtime_records,
            app_log=phase_a.boot_payload + b"\n" + phase_b.boot_payload + b"\n",
        )

    assert caught.value.code == "dual_live_child_proof_invalid"


def test_child_proof_parser_rejects_guard_enable_attempt_even_if_rehashed() -> None:
    lines = _production_child_proof_stdout().splitlines()
    record = json.loads(lines[1])
    record["payload"]["network_enable_attempt_count"] = 1
    record["record_sha256"] = hashlib.sha256(
        canonical_json_bytes(
            {
                key: value
                for key, value in record.items()
                if key != "record_sha256"
            }
        )
    ).hexdigest()
    lines[1] = canonical_json_bytes(record)

    with pytest.raises(DualLiveEvaluationError) as caught:
        dual_live_evaluator_module._parse_child_proof_records(
            b"\n".join(lines) + b"\n"
        )

    assert caught.value.code == "dual_live_child_proof_invalid"


def test_child_proof_parser_rejects_noncanonical_package_preview_id() -> None:
    lines = _production_child_proof_stdout().splitlines()
    downstream = json.loads(lines[2])
    downstream["payload"]["source_bindings"][0][
        "package_review_preview_hash"
    ] = "7" * 64
    downstream["record_sha256"] = hashlib.sha256(
        canonical_json_bytes(
            {
                key: value
                for key, value in downstream.items()
                if key != "record_sha256"
            }
        )
    ).hexdigest()
    lines[2] = canonical_json_bytes(downstream)
    exit_guard = json.loads(lines[3])
    exit_guard["previous_record_sha256"] = downstream["record_sha256"]
    exit_guard["record_sha256"] = hashlib.sha256(
        canonical_json_bytes(
            {
                key: value
                for key, value in exit_guard.items()
                if key != "record_sha256"
            }
        )
    ).hexdigest()
    lines[3] = canonical_json_bytes(exit_guard)

    with pytest.raises(DualLiveEvaluationError) as caught:
        dual_live_evaluator_module._parse_child_proof_records(
            b"\n".join(lines) + b"\n"
        )

    assert caught.value.code == "dual_live_child_proof_invalid"


def _proof_check_context() -> dual_live_evaluator_module._EvidenceContext:
    phase_a, phase_b = _production_child_proof_materials()
    a_boot = "1" * 64
    b_boot = "2" * 64
    a_complete_hash = "a" * 64
    b_complete_hash = "b" * 64
    runtime_records = (
        {
            "ordinal": 1,
            "phase": "wrapper",
            "event": "runtime_start",
            "process_boot_id": None,
            "payload": RUNTIME_START_PAYLOAD,
        },
        {
            "ordinal": 2,
            **phase_a.runtime_records[0],
        },
        {"ordinal": 3, **phase_a.runtime_records[1]},
        {"ordinal": 4, **phase_a.runtime_records[2]},
        {"ordinal": 5, **phase_a.runtime_records[3]},
        {
            "ordinal": 6,
            "phase": "A",
            "event": "socket_census",
            "process_boot_id": a_boot,
            "payload": {
                "tcp4_state_counts": ZERO_TCP_STATE_COUNTS,
                "tcp6_state_counts": ZERO_TCP_STATE_COUNTS,
                "udp4_count": 0,
                "udp6_count": 0,
                "process_identity_sha256": "c" * 64,
                "stable": True,
            },
        },
        {
            "ordinal": 7,
            "phase": "A",
            "event": "job_zero",
            "process_boot_id": a_boot,
            "payload": {
                "active_process_count": 0,
                "process_list_sha256": "d" * 64,
            },
        },
        {
            "ordinal": 8,
            "phase": "A",
            "event": "authority_cleared",
            "process_boot_id": a_boot,
            "payload": {
                "authority_posture_sha256": (
                    dual_live_evaluator_module._AUTHORITY_CLEARED_POSTURE_SHA256
                ),
                "all_required_absent": True,
            },
        },
        {
            "ordinal": 9,
            "phase": "A",
            "event": "phase_complete",
            "process_boot_id": a_boot,
            "record_sha256": a_complete_hash,
            "payload": {"terminal_state": "completed", "exit_code": 0},
        },
        {"ordinal": 10, **phase_b.runtime_records[0]},
        {"ordinal": 11, **phase_b.runtime_records[1]},
        {"ordinal": 12, **phase_b.runtime_records[2]},
        {"ordinal": 13, **phase_b.runtime_records[3]},
        {
            "ordinal": 14,
            "phase": "B",
            "event": "phase_complete",
            "process_boot_id": b_boot,
            "record_sha256": b_complete_hash,
            "payload": {"terminal_state": "completed", "exit_code": 0},
        },
        {
            "ordinal": 15,
            "phase": "wrapper",
            "event": "runtime_complete",
            "process_boot_id": None,
            "payload": {
                "phase_a_result_sha256": a_complete_hash,
                "phase_b_result_sha256": b_complete_hash,
                "terminal_state": "completed",
            },
        },
    )
    connectors = ("nrc_adams_aps", "sciencebase_mcs")
    runs = {
        connector: SimpleNamespace(connector_run_id=f"run-{connector}")
        for connector in connectors
    }
    targets = {
        connector: SimpleNamespace(
            connector_run_id=f"run-{connector}",
            connector_run_target_id=f"target-{connector}",
            downloaded_sha256=("1" if ordinal == 1 else "2") * 64,
        )
        for ordinal, connector in enumerate(connectors, start=1)
    }
    ledgers = {
        connector: SimpleNamespace(
            eligible=True,
            ledger_terminal_hash=("f" if ordinal == 1 else "0") * 64,
        )
        for ordinal, connector in enumerate(connectors, start=1)
    }
    origins = {
        connector: {
            "receipt_hash": ("3" if ordinal == 1 else "4") * 64,
            "raw_content_sha256": ("1" if ordinal == 1 else "2") * 64,
        }
        for ordinal, connector in enumerate(connectors, start=1)
    }
    source_shapes = {
        "nrc_adams_aps": "aps_content_document",
        "sciencebase_mcs": "strict_sciencebase_connector_single_source",
    }
    downstream_sessions = {
        connector: SimpleNamespace(
            session_id=f"session-{connector}",
            operator_context_json={
                "layer3_gate_b_decision_manifest_v1": {
                    "items": [
                        {
                            "candidate_id": f"candidate-{connector}",
                            "decision": "approved",
                            "source_class": source_shapes[connector],
                        }
                    ]
                }
            },
        )
        for connector in connectors
    }
    pass_runs = {
        connector: SimpleNamespace(
            analysis_plan_id=f"plan-{connector}",
            pass_run_id=f"pass-{connector}",
            summary_json={
                "analysis_execution_start": {"analysis_run_id": None}
            },
        )
        for connector in connectors
    }
    review_states = {
        connector: {"review_record_ref": f"review-{connector}"}
        for connector in connectors
    }
    reconciliations = {
        connector: SimpleNamespace(
            reconciliation_record_id=f"reconciliation-{connector}"
        )
        for connector in connectors
    }
    packages = {
        connector: tuple(
            SimpleNamespace(
                package_kind=package_kind,
                output_package_id=f"package-{connector}-{package_ordinal}",
                payload_ref=f"payload-{connector}-{package_ordinal}",
                payload_hash=f"{ordinal * 3 + package_ordinal:064x}",
            )
            for package_ordinal, package_kind in enumerate(
                ("canonical_internal", "user_facing", "review_facing")
            )
        )
        for ordinal, connector in enumerate(connectors, start=1)
    }
    package_commits = {
        connector: {
            "construction_basis_hash": (
                "5" if ordinal == 1 else "6"
            )
            * 64,
            "package_review_preview_hash": (
                "l3-qual-aps-package-preview-7777777777777777"
                if ordinal == 1
                else "l3-source-intake-package-preview-8888888888888888"
            ),
        }
        for ordinal, connector in enumerate(connectors, start=1)
    }
    submit_states = {
        connector: {"submit_record_ref": f"submit-{connector}"}
        for connector in connectors
    }
    handoff_states = {
        connector: {
            "prepare_record_ref": f"prepare-{connector}",
            "source_shape": source_shapes[connector],
            "handoff_export_envelope": {
                "envelope_ref": f"envelope-{connector}",
                "source_shape": source_shapes[connector],
            },
        }
        for connector in connectors
    }
    return dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
        manifest=SimpleNamespace(runtime_started_at=0, runtime_stopped_at=1),
        runtime_records=runtime_records,
        child_proofs=dual_live_evaluator_module._parse_child_proof_records(
            _production_child_proof_stdout()
        ),
        counter_records=(
            {"process_boot_id": a_boot},
            {"process_boot_id": a_boot},
        ),
        run_by_connector=runs,
        targets=targets,
        ledgers=ledgers,
        origins=origins,
        source_record_ids={
            connector: f"source-{connector}" for connector in connectors
        },
        downstream_sessions=downstream_sessions,
        pass_runs=pass_runs,
        review_states=review_states,
        reconciliations=reconciliations,
        packages=packages,
        package_commits=package_commits,
        submit_states=submit_states,
        handoff_states=handoff_states,
    )


@pytest.mark.parametrize(
    "check",
    (
        dual_live_evaluator_module._check_r12_phase_b_guards,
        dual_live_evaluator_module._check_r14_runtime_terminal,
        dual_live_evaluator_module._check_r15_wrapper_network_inert,
        dual_live_evaluator_module._check_r16_phase_a_raw_only,
        dual_live_evaluator_module._check_r17_phase_b_strict_flow,
        dual_live_evaluator_module._check_r18_phase_a_terminal_once,
        dual_live_evaluator_module._check_r19_a_to_b_order,
    ),
)
def test_r12_r14_through_r19_accept_exact_bound_child_proofs(
    check: Callable[[object], CheckResult],
) -> None:
    assert check(_proof_check_context()).status == "PASS"


def _changed_child_payload(
    context: dual_live_evaluator_module._EvidenceContext,
    *,
    index: int,
    changes: dict[str, object],
) -> tuple[dict[str, object], ...]:
    records = [
        json.loads(dual_live_evaluator_module._canonical_bytes(record))
        for record in context.child_proofs
    ]
    records[index]["payload"] = {**records[index]["payload"], **changes}
    return tuple(records)


def test_r12_rejects_guard_replacement_or_enable_attempt() -> None:
    context = _proof_check_context()
    changed = replace(
        context,
        child_proofs=_changed_child_payload(
            context,
            index=1,
            changes={"network_enable_attempt_count": 1},
        ),
    )

    result = dual_live_evaluator_module._check_r12_phase_b_guards(changed)

    assert (result.status, result.code) == (
        "FAIL",
        "r12_phase_b_guards_unproven",
    )


def test_r14_rejects_missing_child_terminal_proof() -> None:
    context = _proof_check_context()
    result = dual_live_evaluator_module._check_r14_runtime_terminal(
        replace(context, child_proofs=context.child_proofs[:-1])
    )

    assert (result.status, result.code) == (
        "FAIL",
        "r14_runtime_terminal_invalid",
    )


def test_r15_rejects_counter_outside_phase_a_child() -> None:
    context = _proof_check_context()
    result = dual_live_evaluator_module._check_r15_wrapper_network_inert(
        replace(context, counter_records=({"process_boot_id": "2" * 64},))
    )

    assert result.status == "FAIL"


def test_r16_rejects_phase_a_downstream_action_proof() -> None:
    context = _proof_check_context()
    changed = replace(
        context,
        child_proofs=_changed_child_payload(
            context,
            index=0,
            changes={"downstream_action_count": 1},
        ),
    )

    assert dual_live_evaluator_module._check_r16_phase_a_raw_only(changed).status == (
        "FAIL"
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("source_record_id", "foreign-source"),
        ("connector_run_id", "foreign-run"),
        (
            "package_review_preview_hash",
            "l3-qual-aps-package-preview-9999999999999999",
        ),
        (
            "output_package_ids",
            ["foreign-package-0", "foreign-package-1", "foreign-package-2"],
        ),
    ),
)
def test_r17_rejects_changed_phase_b_source_binding(
    field: str,
    replacement: object,
) -> None:
    context = _proof_check_context()
    records = list(context.child_proofs)
    downstream = json.loads(
        dual_live_evaluator_module._canonical_bytes(records[2])
    )
    downstream["payload"]["source_bindings"][0][field] = replacement
    records[2] = downstream

    result = dual_live_evaluator_module._check_r17_phase_b_strict_flow(
        replace(context, child_proofs=tuple(records))
    )

    assert (result.status, result.code) == (
        "FAIL",
        "r17_phase_b_flow_invalid",
    )


def test_r18_rejects_unbound_phase_a_raw_digest() -> None:
    context = _proof_check_context()
    records = list(context.child_proofs)
    acquisition = json.loads(
        dual_live_evaluator_module._canonical_bytes(records[0])
    )
    acquisition["payload"]["connector_acquisitions"][0][
        "raw_content_sha256"
    ] = "9" * 64
    records[0] = acquisition

    result = dual_live_evaluator_module._check_r18_phase_a_terminal_once(
        replace(context, child_proofs=tuple(records))
    )

    assert (result.status, result.code) == (
        "FAIL",
        "r18_phase_a_terminalization_invalid",
    )


def test_r19_rejects_phase_b_creation_before_phase_a_quiescence() -> None:
    context = _proof_check_context()
    records = tuple(
        {**record, "ordinal": 7}
        if record.get("phase") == "B" and record.get("event") == "phase_child_start"
        else record
        for record in context.runtime_records
    )

    result = dual_live_evaluator_module._check_r19_a_to_b_order(
        replace(context, runtime_records=records)
    )

    assert (result.status, result.code) == (
        "FAIL",
        "r19_a_to_b_order_invalid",
    )


@pytest.mark.parametrize("reflected_ref", ("nrc.bin", "sciencebase.bin"))
def test_c08_scans_each_c07_bound_raw_blob_for_exact_nrc_key(
    monkeypatch: pytest.MonkeyPatch,
    reflected_ref: str,
) -> None:
    secret = "matrix-nrc-key"
    payloads = {
        "nrc.bin": b"safe-nrc",
        "sciencebase.bin": b"safe-sciencebase",
    }
    payloads[reflected_ref] = b"prefix:" + secret.encode("utf-8") + b":suffix"
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=SimpleNamespace(nrc_adams_subscription_key=secret),
        db=NoAccess(),
        source_exemptions=tuple(
            (raw_ref, hashlib.sha256(payloads[raw_ref]).hexdigest())
            for raw_ref in ("nrc.bin", "sciencebase.bin")
        ),
    )
    monkeypatch.setattr(
        dual_live_evaluator_module,
        "_forbidden_candidates",
        lambda *_args, **_kwargs: (secret,),
    )
    monkeypatch.setattr(dual_live_evaluator_module, "_db_scan_payloads", lambda _c: ())
    monkeypatch.setattr(
        dual_live_evaluator_module,
        "_runtime_scan_payloads",
        lambda _c: (),
    )
    monkeypatch.setattr(
        dual_live_evaluator_module,
        "_source_blob",
        lambda _context, raw_ref: payloads[raw_ref],
    )

    result = dual_live_evaluator_module._check_c08_secret_scan(context)

    assert (result.status, result.code) == (
        "FAIL",
        "c08_forbidden_secret_material",
    )
    assert secret not in json.dumps(result.as_dict(), sort_keys=True)


def test_c08_raw_source_scan_does_not_decode_or_scan_url_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "matrix-nrc-key"
    raw_payload = b"https://forbidden.invalid/raw matrix%2Dnrc%2Dkey"
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=SimpleNamespace(nrc_adams_subscription_key=secret),
        db=NoAccess(),
        source_exemptions=(
            ("nrc.bin", hashlib.sha256(raw_payload).hexdigest()),
            ("sciencebase.bin", hashlib.sha256(raw_payload).hexdigest()),
        ),
    )
    monkeypatch.setattr(
        dual_live_evaluator_module,
        "_forbidden_candidates",
        lambda *_args, **_kwargs: (secret, "https://forbidden.invalid/raw"),
    )
    monkeypatch.setattr(dual_live_evaluator_module, "_db_scan_payloads", lambda _c: ())
    monkeypatch.setattr(
        dual_live_evaluator_module,
        "_runtime_scan_payloads",
        lambda _c: (),
    )
    monkeypatch.setattr(
        dual_live_evaluator_module,
        "_source_blob",
        lambda _context, _raw_ref: raw_payload,
    )

    result = dual_live_evaluator_module._check_c08_secret_scan(context)

    assert result.status == "PASS"


def test_c08_rejects_non_exact_source_scope_before_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=SimpleNamespace(nrc_adams_subscription_key="matrix-nrc-key"),
        db=NoAccess(),
        source_exemptions=(("nrc.bin", "a" * 64),),
    )
    monkeypatch.setattr(
        dual_live_evaluator_module,
        "_source_blob",
        lambda *_args, **_kwargs: pytest.fail("source read must not occur"),
    )

    result = dual_live_evaluator_module._check_c08_secret_scan(context)

    assert (result.status, result.code) == (
        "FAIL",
        "c08_source_scope_invalid",
    )


def test_f01_and_f02_use_separate_fresh_observation_domains() -> None:
    context = dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
        initial_snapshot_sha256="a" * 64,
        final_snapshot_sha256="a" * 64,
        initial_database_snapshot_sha256="b" * 64,
        final_database_snapshot_sha256="b" * 64,
    )

    evidence = dual_live_evaluator_module._check_f01_evidence_stability(context)
    database = dual_live_evaluator_module._check_f02_database_stability(context)
    changed = dual_live_evaluator_module._check_f02_database_stability(
        replace(context, final_database_snapshot_sha256="c" * 64)
    )

    assert evidence.status == "PASS"
    assert database.status == "PASS"
    assert (changed.status, changed.code) == (
        "INDETERMINATE",
        "f02_database_stability_mismatch",
    )


def _test_stable_id(prefix: str, value: object) -> str:
    return (
        f"{prefix}-"
        f"{hashlib.sha256(dual_live_evaluator_module._canonical_bytes(value)).hexdigest()[:16]}"
    )


def _durable_downstream_context() -> object:
    connectors = ("nrc_adams_aps", "sciencebase_mcs")
    origins: dict[str, dict[str, object]] = {}
    sessions: dict[str, object] = {}
    pass_runs: dict[str, object] = {}
    outputs: dict[str, dict[str, object]] = {}
    reviews: dict[str, dict[str, object]] = {}
    reconciliations: dict[str, object] = {}
    packages: dict[str, tuple[object, ...]] = {}
    payloads: dict[str, tuple[dict[str, object], ...]] = {}
    commits: dict[str, dict[str, object]] = {}
    submits: dict[str, dict[str, object]] = {}
    handoffs: dict[str, dict[str, object]] = {}
    for ordinal, connector_key in enumerate(connectors, start=1):
        session_id = f"session-{ordinal}"
        pass_run_id = f"pass-{ordinal}"
        analysis_plan_id = f"plan-{ordinal}"
        reconciliation_id = f"reconciliation-{ordinal}"
        receipt_hash = str(ordinal) * 64
        target_id = f"target-{ordinal}"
        origin = {
            "schema_id": "layer3.connector_origin_integrity.v1",
            "connector_key": connector_key,
            "connector_run_target_id": target_id,
            "connector_origin_receipt_hash": receipt_hash,
            "proof_class": "fresh_live",
        }
        output = {
            "schema_id": "layer3.connector_output_integrity.v1",
            "connector_key": connector_key,
            "connector_run_target_id": target_id,
            "connector_origin_receipt_hash": receipt_hash,
            "proof_class": "fresh_live",
            "artifact_receipts": [],
            "artifact_set_hash": str(ordinal + 2) * 64,
            "output_manifest_sha256": str(ordinal + 4) * 64,
        }
        review_ref = f"review-{ordinal}"
        review = {
            "schema_id": "layer3.execution_result_review_state.v1",
            "review_record_ref": review_ref,
            "review_state": "execution_result_review_approved",
            "operator_decision": "approved",
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "unresolved_trace_count": 0,
            "connector_origin_integrity_v1": origin,
            "connector_output_integrity_v1": output,
        }
        pass_run = SimpleNamespace(
            pass_run_id=pass_run_id,
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            status="completed",
            output_payload_ref=f"output-{ordinal}.json",
            summary_json={
                "connector_origin_integrity_v1": origin,
                "connector_output_integrity_v1": output,
                "execution_result_review": review,
            },
        )
        package_rows = tuple(
            SimpleNamespace(
                output_package_id=f"package-{ordinal}-{kind}",
                session_id=session_id,
                reconciliation_record_id=reconciliation_id,
                package_kind=kind,
                status="complete",
                payload_ref=f"payload-{ordinal}-{kind}.json",
                payload_hash=str(ordinal + index + 5) * 64,
            )
            for index, kind in enumerate(
                ("canonical_internal", "user_facing", "review_facing")
            )
        )
        package_ids = [row.output_package_id for row in package_rows]
        package_kinds = [row.package_kind for row in package_rows]
        payload_refs = [row.payload_ref for row in package_rows]
        payload_hashes = [row.payload_hash for row in package_rows]
        commit_basis = {
            "schema_id": "layer3.workbench_package_construction_authority.v1",
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "result_review_record_ref": review_ref,
        }
        commit = {
            "schema_id": "layer3.workbench_package_commit_summary.v1",
            "authority_basis": commit_basis,
            "authority_basis_hash": stable_json_text_hash(commit_basis),
            "construction_basis_hash": stable_json_text_hash(
                {
                    **commit_basis,
                    "package_kinds": package_kinds,
                    "payload_refs": payload_refs,
                    "payload_hashes": payload_hashes,
                }
            ),
            "result_review_record_ref": review_ref,
        }
        submit_basis = {
            "schema_id": "layer3.package_review_submit_authority.v1",
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "result_review_record_ref": review_ref,
            "reconciliation_record_id": reconciliation_id,
            "output_package_ids": package_ids,
            "package_kinds": package_kinds,
            "payload_hashes": payload_hashes,
            "operator_decision": "approved",
        }
        submit_ref = _test_stable_id("l3-package-review-submit", submit_basis)
        submit = {
            "schema_id": "layer3.package_review_submit_state.v1",
            "submit_record_ref": submit_ref,
            "authority_basis": submit_basis,
            "package_review_state": "package_review_approved",
            "operator_decision": "approved",
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "result_review_record_ref": review_ref,
            "reconciliation_record_id": reconciliation_id,
            "output_package_ids": package_ids,
            "package_kinds": package_kinds,
            "payload_hashes": payload_hashes,
            "handoff_enabled": False,
            "export_enabled": False,
            "connector_origin_integrity_v1": origin,
            "connector_output_integrity_v1": output,
        }
        handoff_basis = {
            "schema_id": "layer3.handoff_export_prepare_authority.v1",
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "result_review_record_ref": review_ref,
            "reconciliation_record_id": reconciliation_id,
            "output_package_ids": package_ids,
            "package_kinds": package_kinds,
            "payload_refs": payload_refs,
            "payload_hashes": payload_hashes,
            "package_review_submit_record_ref": submit_ref,
            "package_review_state": "package_review_approved",
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "operator_decision": "authorize_prepare",
        }
        envelope_basis = {
            **handoff_basis,
            "schema_id": "layer3.handoff_export_envelope_authority.v1",
        }
        flags = {
            "external_handoff_enabled": False,
            "external_export_enabled": False,
            "dispatch_enabled": False,
            "aps_handoff_enabled": False,
            "external_export_download_enabled": False,
            "connector_dispatch_enabled": False,
            "provider_public_url_enabled": False,
        }
        envelope = {
            "schema_id": "layer3.handoff_export_envelope.v1",
            "envelope_ref": _test_stable_id(
                "l3-handoff-export-envelope", envelope_basis
            ),
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "result_review_record_ref": review_ref,
            "package_review_submit_record_ref": submit_ref,
            "reconciliation_record_id": reconciliation_id,
            "output_package_ids": package_ids,
            "package_kinds": package_kinds,
            "payload_refs": payload_refs,
            "payload_hashes": payload_hashes,
            "connector_origin_integrity_v1": origin,
            "connector_output_integrity_v1": output,
            **flags,
        }
        handoff = {
            "schema_id": "layer3.handoff_export_prepare_state.v1",
            "prepare_record_ref": _test_stable_id(
                "l3-handoff-export-prepare", handoff_basis
            ),
            "authority_basis": handoff_basis,
            "package_review_submit_record_ref": submit_ref,
            "package_review_state": "package_review_approved",
            "operator_decision": "authorize_prepare",
            "handoff_export_state": "handoff_export_prepared",
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "result_review_record_ref": review_ref,
            "reconciliation_record_id": reconciliation_id,
            "output_package_ids": package_ids,
            "package_kinds": package_kinds,
            "payload_refs": payload_refs,
            "payload_hashes": payload_hashes,
            "connector_origin_integrity_v1": origin,
            "connector_output_integrity_v1": output,
            "handoff_export_envelope": envelope,
            **flags,
        }
        origins[connector_key] = {
            "connector_key": connector_key,
            "receipt_hash": receipt_hash,
            "connector_run_target_id": target_id,
            "proof_class": "fresh_live",
        }
        sessions[connector_key] = SimpleNamespace(session_id=session_id)
        pass_runs[connector_key] = pass_run
        outputs[connector_key] = output
        reviews[connector_key] = review
        reconciliations[connector_key] = SimpleNamespace(
            reconciliation_record_id=reconciliation_id,
            session_id=session_id,
        )
        packages[connector_key] = package_rows
        payloads[connector_key] = tuple(
            {
                "package_header": {"package_kind": row.package_kind},
                "connector_origin_integrity_v1": origin,
                "connector_output_integrity_v1": output,
            }
            for row in package_rows
        )
        commits[connector_key] = commit
        submits[connector_key] = submit
        handoffs[connector_key] = handoff
    return dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
        origins=origins,
        downstream_sessions=sessions,
        pass_runs=pass_runs,
        output_integrity=outputs,
        review_states=reviews,
        reconciliations=reconciliations,
        packages=packages,
        package_payloads=payloads,
        package_commits=commits,
        submit_states=submits,
        handoff_states=handoffs,
    )


@pytest.mark.parametrize(
    ("check", "field"),
    (
        (dual_live_evaluator_module._check_d03_layer3_execution, "pass_runs"),
        (dual_live_evaluator_module._check_d04_review_result, "review_states"),
        (dual_live_evaluator_module._check_d05_package_set, "packages"),
        (dual_live_evaluator_module._check_d06_package_payload, "package_payloads"),
        (dual_live_evaluator_module._check_d07_submit_receipt, "submit_states"),
        (dual_live_evaluator_module._check_d08_handoff_receipt, "handoff_states"),
    ),
)
def test_d03_d08_indetermine_one_deleted_required_boundary(
    check: Callable[[object], CheckResult],
    field: str,
) -> None:
    context = _durable_downstream_context()
    changed = dict(getattr(context, field))
    changed.pop("sciencebase_mcs")

    result = check(replace(context, **{field: changed}))

    assert result.status == "INDETERMINATE"


def test_d03_rejects_mutated_execution_output_binding() -> None:
    context = _durable_downstream_context()
    pass_runs = dict(context.pass_runs)
    original = pass_runs["sciencebase_mcs"]
    summary = dict(original.summary_json)
    summary["connector_output_integrity_v1"] = {
        **summary["connector_output_integrity_v1"],
        "artifact_set_hash": "f" * 64,
    }
    pass_runs["sciencebase_mcs"] = SimpleNamespace(
        **{**vars(original), "summary_json": summary}
    )

    result = dual_live_evaluator_module._check_d03_layer3_execution(
        replace(context, pass_runs=pass_runs)
    )

    assert (result.status, result.code) == (
        "FAIL",
        "d03_layer3_execution_invalid",
    )


def test_d04_rejects_mutated_review_output_binding_only() -> None:
    context = _durable_downstream_context()
    reviews = {key: dict(value) for key, value in context.review_states.items()}
    reviews["sciencebase_mcs"]["connector_output_integrity_v1"] = {
        **reviews["sciencebase_mcs"]["connector_output_integrity_v1"],
        "artifact_set_hash": "f" * 64,
    }

    assert dual_live_evaluator_module._check_d03_layer3_execution(context).status == "PASS"
    result = dual_live_evaluator_module._check_d04_review_result(
        replace(context, review_states=reviews)
    )

    assert (result.status, result.code) == ("FAIL", "d04_review_result_invalid")


def test_d05_rejects_mutated_package_commit_hash_only() -> None:
    context = _durable_downstream_context()
    commits = {key: dict(value) for key, value in context.package_commits.items()}
    commits["sciencebase_mcs"]["authority_basis_hash"] = "f" * 64

    result = dual_live_evaluator_module._check_d05_package_set(
        replace(context, package_commits=commits)
    )

    assert (result.status, result.code) == ("FAIL", "d05_package_set_invalid")


def test_d05_accepts_production_package_hash_encoding() -> None:
    result = dual_live_evaluator_module._check_d05_package_set(
        _durable_downstream_context()
    )

    assert result.status == "PASS"


def test_d06_keys_payloads_by_kind_not_query_order() -> None:
    context = _durable_downstream_context()
    reversed_payloads = {
        key: tuple(reversed(value)) for key, value in context.package_payloads.items()
    }

    result = dual_live_evaluator_module._check_d06_package_payload(
        replace(context, package_payloads=reversed_payloads)
    )

    assert result.status == "PASS"


def test_d06_rejects_mutated_payload_output_binding_only() -> None:
    context = _durable_downstream_context()
    payloads = {key: list(value) for key, value in context.package_payloads.items()}
    changed = dict(payloads["sciencebase_mcs"][1])
    changed["connector_output_integrity_v1"] = {
        **changed["connector_output_integrity_v1"],
        "artifact_set_hash": "f" * 64,
    }
    payloads["sciencebase_mcs"][1] = changed

    result = dual_live_evaluator_module._check_d06_package_payload(
        replace(
            context,
            package_payloads={key: tuple(value) for key, value in payloads.items()},
        )
    )

    assert (result.status, result.code) == ("FAIL", "d06_package_payload_invalid")


def test_d07_rejects_mutated_submit_package_hash_only() -> None:
    context = _durable_downstream_context()
    submits = {key: dict(value) for key, value in context.submit_states.items()}
    submits["sciencebase_mcs"]["payload_hashes"] = ["f" * 64] * 3

    result = dual_live_evaluator_module._check_d07_submit_receipt(
        replace(context, submit_states=submits)
    )

    assert (result.status, result.code) == ("FAIL", "d07_submit_receipt_invalid")


def test_d08_rejects_single_delivery_claim_only() -> None:
    context = _durable_downstream_context()
    handoffs = {key: dict(value) for key, value in context.handoff_states.items()}
    handoffs["sciencebase_mcs"]["dispatch_enabled"] = True

    assert dual_live_evaluator_module._check_d07_submit_receipt(context).status == "PASS"
    result = dual_live_evaluator_module._check_d08_handoff_receipt(
        replace(context, handoff_states=handoffs)
    )

    assert (result.status, result.code) == ("FAIL", "d08_handoff_receipt_invalid")


def _f09_context() -> object:
    context = _durable_downstream_context()
    origins = {key: dict(value) for key, value in context.origins.items()}
    ledgers: dict[str, object] = {}
    runs: dict[str, object] = {}
    for ordinal, connector_key in enumerate(
        ("nrc_adams_aps", "sciencebase_mcs"),
        start=1,
    ):
        run_id = f"run-{ordinal}"
        origins[connector_key].update(
            {
                "connector_run_id": run_id,
                "raw_content_sha256": str(ordinal + 2) * 64,
            }
        )
        ledgers[connector_key] = SimpleNamespace(
            connector_run_id=run_id,
            ledger_terminal_hash=str(ordinal + 4) * 64,
        )
        runs[connector_key] = SimpleNamespace(connector_run_id=run_id)
    return replace(
        context,
        origins=origins,
        ledgers=ledgers,
        run_by_connector=runs,
    )


def test_f09_emits_independent_connector_and_combined_projections() -> None:
    context = _f09_context()

    result = dual_live_evaluator_module._check_f09_connector_and_combined_reports(
        context
    )

    assert result.status == "PASS"
    assert tuple(item["connector_key"] for item in result.evidence["connector_results"]) == (
        "nrc_adams_aps",
        "sciencebase_mcs",
    )
    connector_digests = {
        item["projection_sha256"] for item in result.evidence["connector_results"]
    }
    assert len(connector_digests) == 2
    assert result.evidence["combined_result"]["projection_sha256"] not in connector_digests


def test_f09_rejects_copied_connector_result_domain() -> None:
    context = _f09_context()
    origins = {key: dict(value) for key, value in context.origins.items()}
    copied_hash = origins["nrc_adams_aps"]["receipt_hash"]
    origins["sciencebase_mcs"]["receipt_hash"] = copied_hash

    result = dual_live_evaluator_module._check_f09_connector_and_combined_reports(
        replace(context, origins=origins)
    )

    assert (result.status, result.code) == (
        "FAIL",
        "f09_result_domains_invalid",
    )


def test_valid_inputs_return_exact_ordered_indeterminate_report() -> None:
    report = _evaluate()

    assert report == EXPECTED_REPORT
    assert list(report) == list(EXPECTED_REPORT)
    assert report is not EXPECTED_REPORT
    assert report["checks"] is not EXPECTED_REPORT["checks"]
    assert report["nonclaims"] is not EXPECTED_REPORT["nonclaims"]


def test_evaluation_is_repeatable_and_does_not_reuse_mutable_values() -> None:
    first = _evaluate()
    second = _evaluate()

    assert first == second == EXPECTED_REPORT
    assert first is not second
    assert first["checks"] is not second["checks"]
    assert first["checks"][0] is not second["checks"][0]
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


def _r05_evaluator_context(
    payload: dict[str, object] = RUNTIME_START_PAYLOAD,
) -> object:
    historical = {
        connector_key: SimpleNamespace(
            model=SimpleNamespace(
                max_physical_requests=max_physical_requests,
                request_timeout_seconds=30,
                min_request_interval_ms=250,
            )
        )
        for connector_key, max_physical_requests in (
            ("nrc_adams_aps", 2),
            ("sciencebase_mcs", 3),
        )
    }
    return dual_live_evaluator_module._EvidenceContext(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        settings=NoAccess(),
        db=NoAccess(),
        historical=historical,
        runtime_records=(
            {
                "ordinal": 1,
                "phase": "wrapper",
                "event": "runtime_start",
                "payload": payload,
                "record_sha256": "f" * 64,
            },
        ),
    )


def test_r05_evaluator_rederives_exact_producer_timeout_contract() -> None:
    result = dual_live_evaluator_module._check_r05_runtime_chain(
        _r05_evaluator_context()
    )

    assert (result.status, result.code) == (
        "PASS",
        "r05_runtime_chain_pass",
    )
    assert result.evidence["dependency_set_sha256"] == "8" * 64
    assert result.evidence["phase_a_timeout_ms"] == 205_750
    assert result.evidence["phase_b_timeout_ms"] == 30_000


def test_r05_evaluator_requires_exactly_one_runtime_start() -> None:
    context = _r05_evaluator_context()
    duplicate = {
        **context.runtime_records[0],
        "ordinal": 2,
        "record_sha256": "e" * 64,
    }

    result = dual_live_evaluator_module._check_r05_runtime_chain(
        replace(
            context,
            runtime_records=(*context.runtime_records, duplicate),
        )
    )

    assert (result.status, result.code) == (
        "FAIL",
        "r05_runtime_chain_invalid",
    )


def test_r05_evaluator_rejects_historical_timeout_grant_mismatch() -> None:
    context = _r05_evaluator_context()
    historical = dict(context.historical)
    historical["nrc_adams_aps"] = SimpleNamespace(
        model=SimpleNamespace(
            max_physical_requests=2,
            request_timeout_seconds=31,
            min_request_interval_ms=250,
        )
    )

    result = dual_live_evaluator_module._check_r05_runtime_chain(
        replace(context, historical=historical)
    )

    assert (result.status, result.code) == (
        "FAIL",
        "r05_runtime_chain_invalid",
    )


@pytest.mark.parametrize(
    "payload",
    (
        {
            **RUNTIME_START_PAYLOAD,
            "dependency_set_sha256": "A" * 64,
        },
        {
            **RUNTIME_START_PAYLOAD,
            "phase_timeout_contract": {
                **PHASE_TIMEOUT_CONTRACT,
                "connector_grants": list(
                    reversed(PHASE_TIMEOUT_CONTRACT["connector_grants"])
                ),
            },
        },
        {
            **RUNTIME_START_PAYLOAD,
            "phase_timeout_contract": {
                **PHASE_TIMEOUT_CONTRACT,
                "phase_a_timeout_ms": 207_750,
                "connector_grants": [
                    {
                        **PHASE_TIMEOUT_CONTRACT["connector_grants"][0],
                        "request_timeout_seconds": 31,
                    },
                    PHASE_TIMEOUT_CONTRACT["connector_grants"][1],
                ],
            },
        },
    ),
    ids=("dependency-digest", "grant-order", "coherent-timeout-rewrite"),
)
def test_r05_evaluator_rejects_rewritten_producer_contract(
    payload: dict[str, object],
) -> None:
    result = dual_live_evaluator_module._check_r05_runtime_chain(
        _r05_evaluator_context(payload)
    )

    assert (result.status, result.code) == (
        "FAIL",
        "r05_runtime_chain_invalid",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("runtime_instance_id", CAMPAIGN_ID.upper()),
        ("wrapper_nonce_sha256", "A" * 64),
        ("code_revision", "2" * 39),
        ("wrapper_image_sha256", "3" * 63),
        ("dependency_set_sha256", "8" * 63),
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
        "dependency_set_sha256": "8" * 64,
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
        readers["stderr"] = io.BytesIO(encode_pipe_frame(payload))
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
    proof_frame = dual_live_runtime_module.encode_child_proof_frame(
        phase="A",
        event="acquisition_boundary",
        process_boot_id=STATUS_PROCESS_BOOT_ID,
        status_nonce_sha256=STATUS_NONCE_SHA256,
        ordinal=1,
        previous_record_sha256=None,
        payload={
            "boot_frame_sha256": "1" * 64,
            "connector_acquisitions": [],
            "control_frame_sha256": "2" * 64,
            "control_nonce_sha256": "3" * 64,
            "downstream_action_count": 0,
            "exit_status_frame_sha256": "4" * 64,
            "pre_activity_status_frame_sha256": "5" * 64,
            "proof_scope": "mechanical",
        },
    )
    readers = {
        "app": io.BytesIO(status_frame + encode_pipe_frame(app)),
        "http": io.BytesIO(encode_pipe_frame(http)),
        "stdout": io.BytesIO(proof_frame),
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
    assert writers["stdout"].bytes() == proof_frame[4:] + b"\n"
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
        readers["stderr"] = io.BytesIO(encode_pipe_frame(b"output"))
        writers["stderr"] = ShortWriter()
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
    boot_payload = canonical_json_bytes(
        {
            "control_nonce": control_nonce,
            "phase": phase,
            "process_boot_id": process_boot_id,
            "schema_id": dual_live_runtime_module.CHILD_BOOT_SCHEMA_ID,
            "status_nonce_sha256": status_nonce_sha256,
        }
    )
    boot_frame = encode_pipe_frame(boot_payload)
    pre_status_frame = encode_child_status_frame(
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
    readers["app"].feed(boot_frame)
    readers["app"].feed(pre_status_frame)
    proof_common = {
        "boot_frame_sha256": hashlib.sha256(boot_frame).hexdigest(),
        "control_nonce_sha256": hashlib.sha256(
            control_nonce.encode("ascii")
        ).hexdigest(),
        "pre_activity_status_frame_sha256": hashlib.sha256(
            pre_status_frame
        ).hexdigest(),
        "proof_scope": "mechanical",
    }
    previous_proof_sha256: str | None = None
    if phase == "B":
        preproof = dual_live_runtime_module.encode_child_proof_frame(
            phase="B",
            event="guard",
            process_boot_id=process_boot_id,
            status_nonce_sha256=status_nonce_sha256,
            ordinal=1,
            previous_record_sha256=None,
            payload={
                **proof_common,
                "denied_routes": [
                    "dns",
                    "http",
                    "socket",
                    "subprocess",
                    "connector_transport",
                ],
                "network_enable_attempt_count": 0,
                "original_implementation_call_count": 0,
                "proof_point": "pre_go",
            },
        )
        previous_proof_sha256 = json.loads(
            preproof[4:].decode("utf-8")
        )["record_sha256"]
        readers["stdout"].feed(preproof)
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
        exit_status_frame = encode_child_status_frame(
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
        readers["app"].feed(exit_status_frame)
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
        terminal_common = {
            **proof_common,
            "control_frame_sha256": hashlib.sha256(frame).hexdigest(),
            "exit_status_frame_sha256": hashlib.sha256(
                exit_status_frame
            ).hexdigest(),
        }
        if phase == "A":
            readers["stdout"].feed(
                dual_live_runtime_module.encode_child_proof_frame(
                    phase="A",
                    event="acquisition_boundary",
                    process_boot_id=process_boot_id,
                    status_nonce_sha256=status_nonce_sha256,
                    ordinal=1,
                    previous_record_sha256=None,
                    payload={
                        **terminal_common,
                        "connector_acquisitions": [],
                        "downstream_action_count": 0,
                    },
                )
            )
        else:
            assert isinstance(previous_proof_sha256, str)
            downstream = dual_live_runtime_module.encode_child_proof_frame(
                phase="B",
                event="downstream_chain",
                process_boot_id=process_boot_id,
                status_nonce_sha256=status_nonce_sha256,
                ordinal=2,
                previous_record_sha256=previous_proof_sha256,
                payload={
                    **terminal_common,
                    "downstream_actions": [],
                    "source_bindings": [],
                    "terminal_boundary": "mechanical_complete",
                },
            )
            downstream_sha256 = json.loads(
                downstream[4:].decode("utf-8")
            )["record_sha256"]
            readers["stdout"].feed(downstream)
            readers["stdout"].feed(
                dual_live_runtime_module.encode_child_proof_frame(
                    phase="B",
                    event="guard",
                    process_boot_id=process_boot_id,
                    status_nonce_sha256=status_nonce_sha256,
                    ordinal=3,
                    previous_record_sha256=downstream_sha256,
                    payload={
                        **terminal_common,
                        "denied_routes": [
                            "dns",
                            "http",
                            "socket",
                            "subprocess",
                            "connector_transport",
                        ],
                        "network_enable_attempt_count": 0,
                        "original_implementation_call_count": 0,
                        "proof_point": "exit",
                    },
                )
            )
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


def _mechanical_phase_a_proof_frame() -> bytes:
    process_boot_id = "a" * 64
    status_nonce_sha256 = "c" * 64
    control_nonce = "e" * 64
    boot_frame = encode_pipe_frame(
        canonical_json_bytes(
            {
                "control_nonce": control_nonce,
                "phase": "A",
                "process_boot_id": process_boot_id,
                "schema_id": dual_live_runtime_module.CHILD_BOOT_SCHEMA_ID,
                "status_nonce_sha256": status_nonce_sha256,
            }
        )
    )
    pre_status_frame = encode_child_status_frame(
        phase="A",
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
    exit_status_frame = encode_child_status_frame(
        phase="A",
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
    control_frame = encode_child_control_frame(
        phase="A",
        command="GO",
        control_nonce=control_nonce,
    )
    return dual_live_runtime_module.encode_child_proof_frame(
        phase="A",
        event="acquisition_boundary",
        process_boot_id=process_boot_id,
        status_nonce_sha256=status_nonce_sha256,
        ordinal=1,
        previous_record_sha256=None,
        payload={
            "boot_frame_sha256": hashlib.sha256(boot_frame).hexdigest(),
            "connector_acquisitions": [],
            "control_frame_sha256": hashlib.sha256(control_frame).hexdigest(),
            "control_nonce_sha256": hashlib.sha256(
                control_nonce.encode("ascii")
            ).hexdigest(),
            "downstream_action_count": 0,
            "exit_status_frame_sha256": hashlib.sha256(
                exit_status_frame
            ).hexdigest(),
            "pre_activity_status_frame_sha256": hashlib.sha256(
                pre_status_frame
            ).hexdigest(),
            "proof_scope": "mechanical",
        },
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


def test_swallowed_stop_bridge_failure_before_go_is_terminal_without_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }
    original_consume = PhaseControlState.consume_frame

    def fail_bridge_before_go(
        control: PhaseControlState,
        reader: object,
    ) -> str:
        result = original_consume(control, reader)
        assert result == "GO"
        try:
            control._stop_latch.latch("pump_failure")
        except DualLiveRuntimeError as exc:
            assert exc.code == "dual_live_stop_publish_failed"
        else:  # pragma: no cover - bridge is deliberately fatal
            raise AssertionError("bridge failure was not raised")
        assert control._stop_latch.reason_code is None
        assert control._stop_latch.snapshot is None
        return result

    def fail_bridge(_reason: str) -> None:
        events.append("revoke-failed-A")
        raise RuntimeError("revocation bridge failed")

    monkeypatch.setattr(PhaseControlState, "consume_frame", fail_bridge_before_go)

    with pytest.raises(DualLiveRuntimeError):
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child("A", events),
            create_phase_b=lambda: events.append("create-B"),
            quiesce_phase=lambda _phase, _child: (),
            clear_authority=lambda _phase, _child: {},
            http_frame_validator=lambda _payload: None,
            seal=lambda: events.append("seal"),
            timeout_seconds=0.1,
            _before_stop_publish=fail_bridge,
        )

    assert events.count("revoke-failed-A") == 1
    assert "go-A" not in events
    records = read_runtime_records(writers["app"].getvalue())
    assert all(record["event"] not in {"phase_go", "stop_latched"} for record in records)
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
        readers["stdout"].feed(_mechanical_phase_a_proof_frame())
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
        readers["stdout"].feed(_mechanical_phase_a_proof_frame())
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
    assert events.index("wait-release-A") < events.index("quiesce-A")
    assert events.index("quiesce-A") < events.index("authority-A")
    assert events.count("stop-A") == 1
    assert "create-B" not in events
    assert "seal" not in events
    completions = [
        record
        for record in read_runtime_records(writers["app"].getvalue())
        if record["event"] == "phase_complete"
    ]
    assert completions == []


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
    assert events.index("wait-release-A") < events.index("quiesce-A")
    assert events.index("quiesce-A") < events.index("authority-A")
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


def test_owner_close_failure_uses_stream_order_not_completion_order() -> None:
    http_failed = threading.Event()
    reader_names = iter(PIPE_STREAM_CLASSES)

    class OrderedFailReader(_ControllerReader):
        def __init__(self) -> None:
            super().__init__()
            self.stream = next(reader_names)

        def close(self) -> None:
            if self.stream == "app":
                assert http_failed.wait(timeout=1)
                raise RuntimeError("app-close-failed")
            if self.stream == "http":
                http_failed.set()
                raise RuntimeError("http-close-failed-first")
            super().close()

    events: list[str] = []
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_reader_close_failed",
    ) as exc:
        dual_live_runtime_module._run_two_phase_controller(
            identity=RUNTIME_IDENTITY,
            runtime_start_payload=RUNTIME_START_PAYLOAD,
            writers=writers,
            create_phase_a=lambda: _controller_child(
                "A",
                events,
                reader_factory=OrderedFailReader,
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
            timeout_seconds=1,
        )

    assert isinstance(exc.value.__cause__, RuntimeError)
    assert str(exc.value.__cause__) == "app-close-failed"
    assert "create-B" not in events
    assert "seal" not in events


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
    captured_pumps: list[_RuntimeFourStreamPumpGroup] = []
    captured_readers: list[_CountingCloseControllerReader] = []
    started_cancel_threads: list[threading.Thread] = []
    cancel_start_count = 0
    original_thread_start = threading.Thread.start
    original_pump_start = _RuntimeFourStreamPumpGroup.start
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    def reader_factory() -> _CountingCloseControllerReader:
        reader = _CountingCloseControllerReader()
        captured_readers.append(reader)
        return reader

    def capture_pumps_start(pumps: _RuntimeFourStreamPumpGroup) -> None:
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

    monkeypatch.setattr(
        _RuntimeFourStreamPumpGroup,
        "start",
        capture_pumps_start,
    )
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
    captured_pumps: list[_RuntimeFourStreamPumpGroup] = []
    captured_readers: list[dict[str, _ControllerReader]] = []
    original_start = _RuntimeFourStreamPumpGroup.start
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    def capture_start(pumps: _RuntimeFourStreamPumpGroup) -> None:
        captured_pumps.append(pumps)
        original_start(pumps)

    def inject_malformed_frame(readers: dict[str, _ControllerReader]) -> None:
        captured_readers.append(readers)
        readers["stdout"].feed(b"\x00\x00\x00\x00")

    monkeypatch.setattr(_RuntimeFourStreamPumpGroup, "start", capture_start)
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


def test_task5_controller_quiesces_and_clears_phase_a_authority_before_b() -> None:
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
    assert events.index("stop-A") < events.index("quiesce-A")
    assert events.index("quiesce-A") < events.index("authority-A")
    assert events.index("authority-A") < events.index("create-B")
    assert events[-1] == "seal"
    assert events.index("stop-B") < events.index("flush-app")
    assert events.count("stop-A") == 1
    assert events.count("stop-B") == 1
    assert all(writer.closed_clean for writer in writers.values())
    proof_records = [
        json.loads(line) for line in writers["stdout"].getvalue().splitlines()
    ]
    assert [
        (record["phase"], record["event"]) for record in proof_records
    ] == [
        ("A", "acquisition_boundary"),
        ("B", "guard"),
        ("B", "downstream_chain"),
        ("B", "guard"),
    ]
    assert all(record["payload"]["proof_scope"] == "mechanical" for record in proof_records)
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
    assert events.index("stop-A") < events.index("quiesce-A")
    assert events.index("quiesce-A") < events.index("authority-A")
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


def test_bind_01_owned_nonproduction_binder_is_private_and_exact() -> None:
    binder = getattr(dual_live_runtime_module, "_run_owned_two_phase_controller")
    owned_type = getattr(dual_live_runtime_module, "_OwnedControllerContext")

    assert tuple(inspect.signature(binder).parameters) == ("context",)
    assert inspect.isclass(owned_type)
    with pytest.raises(TypeError):
        owned_type()  # type: ignore[call-arg]
    source = inspect.getsource(binder)
    assert "Callable" not in source
    assert "writers" not in inspect.signature(binder).parameters
    assert "environment" not in inspect.signature(binder).parameters
    assert "path" not in inspect.signature(binder).parameters
    assert "handle" not in inspect.signature(binder).parameters


def test_bind_02_owned_context_is_factory_only_and_nonproduction() -> None:
    factory = getattr(
        dual_live_runtime_module,
        "_make_nonproduction_owned_controller_context",
    )
    context_type = getattr(dual_live_runtime_module, "_OwnedControllerContext")
    events: list[str] = []
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }

    context = factory(
        identity=RUNTIME_IDENTITY,
        runtime_start_payload=RUNTIME_START_PAYLOAD,
        app_writer=writers["app"],
        http_writer=writers["http"],
        stdout_writer=writers["stdout"],
        stderr_writer=writers["stderr"],
        timeout_seconds=2,
    )

    assert type(context) is context_type
    assert context.nonproduction_mechanical_only is True
    assert context.sealed is False
    with pytest.raises(TypeError):
        context_type(  # type: ignore[call-arg]
            RUNTIME_IDENTITY,
            RUNTIME_START_PAYLOAD,
            writers,
            2,
        )


class _FakeOwnedPhaseProcess:
    def __init__(
        self,
        phase: str,
        events: list[str],
        *,
        exit_code: int = 0,
        revoke_failure: BaseException | None = None,
        close_failure: BaseException | None = None,
        leave_readers_open: bool = False,
    ) -> None:
        self.phase = phase
        self.events = events
        self.process_boot_id = ("a" if phase == "A" else "b") * 64
        self.process_creation_identity_sha256 = ("2" if phase == "A" else "7") * 64
        self.executable_sha256 = "3" * 64
        self.job_policy_sha256 = "4" * 64
        self.status_nonce_sha256 = ("c" if phase == "A" else "d") * 64
        self.control_nonce = ("e" if phase == "A" else "f") * 64
        self.readers: dict[str, _ControllerReader] = {
            str(stream): _ControllerReader() for stream in PIPE_STREAM_CLASSES
        }
        self._exit_code = exit_code
        self._revoke_failure = revoke_failure
        self._close_failure = close_failure
        self._leave_readers_open = leave_readers_open
        self._go_sent = False
        self._closed = False
        self.close_calls = 0
        self._boot_frame = encode_pipe_frame(
            canonical_json_bytes(
                {
                    "control_nonce": self.control_nonce,
                    "phase": phase,
                    "process_boot_id": self.process_boot_id,
                    "schema_id": dual_live_runtime_module.CHILD_BOOT_SCHEMA_ID,
                    "status_nonce_sha256": self.status_nonce_sha256,
                }
            )
        )
        self._pre_status_frame = encode_child_status_frame(
            phase=phase,
            event="logger_census",
            process_boot_id=self.process_boot_id,
            status_nonce_sha256=self.status_nonce_sha256,
            ordinal=1,
            payload={
                "census_point": "pre_activity",
                "handler_count": 1,
                "topology_sha256": "1" * 64,
            },
        )
        self.readers["app"].feed(self._boot_frame)
        self.readers["app"].feed(self._pre_status_frame)
        self._previous_proof_sha256: str | None = None
        if phase == "B":
            preproof = dual_live_runtime_module.encode_child_proof_frame(
                phase="B",
                event="guard",
                process_boot_id=self.process_boot_id,
                status_nonce_sha256=self.status_nonce_sha256,
                ordinal=1,
                previous_record_sha256=None,
                payload={
                    **self._proof_common(),
                    "denied_routes": [
                        "dns",
                        "http",
                        "socket",
                        "subprocess",
                        "connector_transport",
                    ],
                    "network_enable_attempt_count": 0,
                    "original_implementation_call_count": 0,
                    "proof_point": "pre_go",
                },
            )
            self._previous_proof_sha256 = json.loads(
                preproof[4:].decode("utf-8")
            )["record_sha256"]
            self.readers["stdout"].feed(preproof)

    def _proof_common(self) -> dict[str, object]:
        return {
            "boot_frame_sha256": hashlib.sha256(self._boot_frame).hexdigest(),
            "control_nonce_sha256": hashlib.sha256(
                self.control_nonce.encode("ascii")
            ).hexdigest(),
            "pre_activity_status_frame_sha256": hashlib.sha256(
                self._pre_status_frame
            ).hexdigest(),
            "proof_scope": "mechanical",
        }

    def send_control(self, frame: bytes) -> None:
        assert frame == encode_child_control_frame(
            phase=self.phase,
            command="GO",
            control_nonce=self.control_nonce,
        )
        self.events.append(f"go-{self.phase}")
        self._go_sent = True
        exit_status_frame = encode_child_status_frame(
            phase=self.phase,
            event="logger_census",
            process_boot_id=self.process_boot_id,
            status_nonce_sha256=self.status_nonce_sha256,
            ordinal=2,
            payload={
                "census_point": "exit",
                "handler_count": 1,
                "topology_sha256": "1" * 64,
            },
        )
        self.readers["app"].feed(exit_status_frame)
        terminal_common = {
            **self._proof_common(),
            "control_frame_sha256": hashlib.sha256(frame).hexdigest(),
            "exit_status_frame_sha256": hashlib.sha256(
                exit_status_frame
            ).hexdigest(),
        }
        if self.phase == "A":
            self.readers["stdout"].feed(
                dual_live_runtime_module.encode_child_proof_frame(
                    phase="A",
                    event="acquisition_boundary",
                    process_boot_id=self.process_boot_id,
                    status_nonce_sha256=self.status_nonce_sha256,
                    ordinal=1,
                    previous_record_sha256=None,
                    payload={
                        **terminal_common,
                        "connector_acquisitions": [],
                        "downstream_action_count": 0,
                    },
                )
            )
        else:
            assert isinstance(self._previous_proof_sha256, str)
            downstream = dual_live_runtime_module.encode_child_proof_frame(
                phase="B",
                event="downstream_chain",
                process_boot_id=self.process_boot_id,
                status_nonce_sha256=self.status_nonce_sha256,
                ordinal=2,
                previous_record_sha256=self._previous_proof_sha256,
                payload={
                    **terminal_common,
                    "downstream_actions": [],
                    "source_bindings": [],
                    "terminal_boundary": "mechanical_complete",
                },
            )
            downstream_sha256 = json.loads(
                downstream[4:].decode("utf-8")
            )["record_sha256"]
            self.readers["stdout"].feed(downstream)
            self.readers["stdout"].feed(
                dual_live_runtime_module.encode_child_proof_frame(
                    phase="B",
                    event="guard",
                    process_boot_id=self.process_boot_id,
                    status_nonce_sha256=self.status_nonce_sha256,
                    ordinal=3,
                    previous_record_sha256=downstream_sha256,
                    payload={
                        **terminal_common,
                        "denied_routes": [
                            "dns",
                            "http",
                            "socket",
                            "subprocess",
                            "connector_transport",
                        ],
                        "network_enable_attempt_count": 0,
                        "original_implementation_call_count": 0,
                        "proof_point": "exit",
                    },
                )
            )
        if not self._leave_readers_open:
            for reader in self.readers.values():
                reader.finish()

    def poll_exit(self, _timeout: float) -> int | None:
        return self._exit_code if self._go_sent else None

    def revoke_before_stop(self, reason: str) -> None:
        self.events.append(f"revoke-{self.phase}-{reason}")
        if self._revoke_failure is not None:
            raise self._revoke_failure

    def stop(self) -> None:
        self.events.append(f"stop-{self.phase}")

    def quiesce_and_close(
        self,
    ) -> tuple[dict[str, object], dict[str, object]]:
        self.events.append(f"quiesce-{self.phase}")
        return (
            _controller_socket_census(),
            {"active_process_count": 0, "process_list_sha256": "5" * 64},
        )

    def authority_cleared_payload(self) -> dict[str, object]:
        self.events.append(f"authority-{self.phase}")
        return {
            "authority_posture_sha256": "6" * 64,
            "all_required_absent": True,
        }

    def close(self) -> None:
        self.close_calls += 1
        if self._close_failure is not None:
            self.events.append(f"close-failed-{self.phase}")
            raise self._close_failure
        if not self._closed:
            self.events.append(f"close-{self.phase}")
            self._closed = True
        for reader in self.readers.values():
            reader.close()


def _owned_test_context(
    events: list[str],
    *,
    timeout_seconds: float = 1,
    app_writer: _ControllerWriter | None = None,
) -> tuple[
    dual_live_runtime_module._OwnedControllerContext,
    dict[str, _ControllerWriter],
]:
    writers = {
        stream: (
            app_writer
            if stream == "app" and app_writer is not None
            else _ControllerWriter(stream, events)
        )
        for stream in PIPE_STREAM_CLASSES
    }
    context = dual_live_runtime_module._make_nonproduction_owned_controller_context(
        identity=RUNTIME_IDENTITY,
        runtime_start_payload=RUNTIME_START_PAYLOAD,
        app_writer=writers["app"],
        http_writer=writers["http"],
        stdout_writer=writers["stdout"],
        stderr_writer=writers["stderr"],
        timeout_seconds=timeout_seconds,
    )
    return context, writers


def test_seq_owned_binder_records_exact_two_phase_order_and_seals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_windows

    events: list[str] = []
    created: list[_FakeOwnedPhaseProcess] = []

    def create(phase: str, _runtime_id: str, _wrapper_nonce: str) -> object:
        process = _FakeOwnedPhaseProcess(phase, events)
        created.append(process)
        return process

    monkeypatch.setattr(
        dual_live_windows,
        "_create_owned_phase_process",
        create,
        raising=False,
    )
    context, writers = _owned_test_context(events)

    result = dual_live_runtime_module._run_owned_two_phase_controller(context)

    records = read_runtime_records(writers["app"].getvalue())
    assert result is None
    assert context.sealed is True
    assert [record["event"] for record in records] == [
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
    assert [record["phase"] for record in records] == [
        "wrapper",
        *("A" for _ in range(8)),
        *("B" for _ in range(7)),
        "wrapper",
    ]
    assert [process.process_boot_id for process in created] == ["a" * 64, "b" * 64]
    assert [process.close_calls for process in created] == [1, 1]
    assert context._owned_processes == []
    assert context._active_process is None
    assert events.index("quiesce-A") < events.index("go-B")
    assert events.index("quiesce-A") < events.index("close-A")
    assert events.index("close-A") < events.index("go-B")
    assert events.index("quiesce-B") < events.index("close-app")


def test_owned_binder_failed_close_retains_active_process_for_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_windows

    events: list[str] = []
    created: list[_FakeOwnedPhaseProcess] = []

    def create(phase: str, _runtime_id: str, _wrapper_nonce: str) -> object:
        process = _FakeOwnedPhaseProcess(
            phase,
            events,
            close_failure=RuntimeError("close failed"),
        )
        created.append(process)
        return process

    monkeypatch.setattr(
        dual_live_windows,
        "_create_owned_phase_process",
        create,
        raising=False,
    )
    context, _writers = _owned_test_context(events)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_owned_close_failed"):
        dual_live_runtime_module._run_owned_two_phase_controller(context)

    assert len(created) == 1
    assert context._owned_processes == [("A", created[0])]
    assert context._active_process is created[0]
    assert context._quiescing_process is None
    assert context._closed_process_ids == set()


def test_owned_context_overlap_retains_new_process_until_cleanup_retry() -> None:
    events: list[str] = []
    context, _writers = _owned_test_context(events)
    active = _FakeOwnedPhaseProcess("A", events)
    overlap = _FakeOwnedPhaseProcess(
        "B",
        events,
        close_failure=RuntimeError("persistent overlap close failure"),
    )
    context._begin_run()
    context._bind_process("A", active)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_owned_close_failed"):
        context._bind_process("B", overlap)

    assert context._owned_processes == [("A", active), ("B", overlap)]
    assert context._active_process is active
    assert overlap.close_calls == 1
    assert context.sealed is False
    assert "go-B" not in events

    overlap._close_failure = None
    assert context._close_all_processes() is None
    assert overlap.close_calls == 2
    assert active.close_calls == 1
    assert context._owned_processes == []
    assert context._active_process is None
    assert context.sealed is False


def test_owned_context_quiesce_does_not_hold_lock_while_close_waits_on_revoke(
) -> None:
    events: list[str] = []
    context, _writers = _owned_test_context(events)
    process = _FakeOwnedPhaseProcess("A", events)
    projection_readers: dict[str, object] = {
        stream: reader for stream, reader in process.readers.items()
    }
    child = _controller_projection(projection_readers, events)
    workers: list[threading.Thread] = []
    revoked = threading.Event()

    def revoke_and_signal() -> None:
        context._revoke_active("quiesce_race")
        revoked.set()

    def close_during_revoke() -> None:
        worker = threading.Thread(
            target=revoke_and_signal,
            name="owned-quiesce-race",
        )
        workers.append(worker)
        worker.start()
        worker.join(0.25)
        if worker.is_alive():
            raise RuntimeError("context lock held across close")

    setattr(process, "close", close_during_revoke)
    context._begin_run()
    context._bind_process("A", process)

    try:
        result = context._quiesce_phase("A", child)
    finally:
        for worker in workers:
            worker.join(1)

    assert revoked.is_set()
    assert result[1]["active_process_count"] == 0
    assert context._active_process is None
    assert context._quiescing_process is None
    assert context._quiesced_process_ids == {id(process)}
    assert context._closed_process_ids == {id(process)}


def test_owned_context_invalid_quiescence_clears_marker_but_retains_custody(
) -> None:
    events: list[str] = []
    context, _writers = _owned_test_context(events)
    process = _FakeOwnedPhaseProcess("A", events)
    projection_readers: dict[str, object] = {
        stream: reader for stream, reader in process.readers.items()
    }
    child = _controller_projection(projection_readers, events)
    setattr(process, "quiesce_and_close", lambda: ({},))
    context._begin_run()
    context._bind_process("A", process)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_quiescence_invalid"):
        context._quiesce_phase("A", child)

    assert context._owned_processes == [("A", process)]
    assert context._active_process is process
    assert context._quiescing_process is None
    assert context._quiesced_process_ids == set()
    assert context._closed_process_ids == set()


def test_stop_owned_binder_revokes_kills_and_never_seals_or_starts_b(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_windows

    events: list[str] = []

    def create(phase: str, _runtime_id: str, _wrapper_nonce: str) -> object:
        events.append(f"create-{phase}")
        return _FakeOwnedPhaseProcess(phase, events, exit_code=9)

    monkeypatch.setattr(
        dual_live_windows,
        "_create_owned_phase_process",
        create,
        raising=False,
    )
    context, _writers = _owned_test_context(events)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_phase_failed"):
        dual_live_runtime_module._run_owned_two_phase_controller(context)

    assert events.index("revoke-A-child_exit_nonzero") < events.index("stop-A")
    assert events.count("stop-A") == 1
    assert "create-B" not in events
    assert context.sealed is False


def test_owned_binder_revocation_failure_is_fatal_and_cannot_seal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_windows

    events: list[str] = []

    def create(phase: str, _runtime_id: str, _wrapper_nonce: str) -> object:
        events.append(f"create-{phase}")
        return _FakeOwnedPhaseProcess(
            phase,
            events,
            exit_code=9,
            revoke_failure=RuntimeError("fail-stop revocation failed"),
        )

    monkeypatch.setattr(
        dual_live_windows,
        "_create_owned_phase_process",
        create,
        raising=False,
    )
    context, _writers = _owned_test_context(events)

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_stop_publish_failed",
    ) as exc:
        dual_live_runtime_module._run_owned_two_phase_controller(context)

    assert isinstance(exc.value.__cause__, RuntimeError)
    assert events.count("revoke-A-child_exit_nonzero") == 1
    assert events.count("stop-A") == 1
    assert "create-B" not in events
    assert context.sealed is False


def test_owned_binder_writer_failure_closes_capture_without_children_or_seal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_windows

    events: list[str] = []
    factory_calls: list[str] = []

    def create(phase: str, _runtime_id: str, _wrapper_nonce: str) -> object:
        factory_calls.append(phase)
        return _FakeOwnedPhaseProcess(phase, events)

    monkeypatch.setattr(
        dual_live_windows,
        "_create_owned_phase_process",
        create,
        raising=False,
    )
    app_writer = _FailingControllerWriter("app", events)
    context, writers = _owned_test_context(events, app_writer=app_writer)

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_runtime_writer_failure",
    ):
        dual_live_runtime_module._run_owned_two_phase_controller(context)

    assert factory_calls == []
    assert context.sealed is False
    assert all(writer.closed_clean for writer in writers.values())


def test_owned_binder_cancel_path_closes_child_and_cannot_seal_or_start_b(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_windows

    events: list[str] = []

    def create(phase: str, _runtime_id: str, _wrapper_nonce: str) -> object:
        events.append(f"create-{phase}")
        return _FakeOwnedPhaseProcess(
            phase,
            events,
            leave_readers_open=True,
        )

    monkeypatch.setattr(
        dual_live_windows,
        "_create_owned_phase_process",
        create,
        raising=False,
    )
    context, _writers = _owned_test_context(events, timeout_seconds=0.05)

    with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_failed") as exc:
        dual_live_runtime_module._run_owned_two_phase_controller(context)

    assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
    assert exc.value.__cause__.code == "dual_live_pump_join_timeout"
    assert any(event.startswith("revoke-A-") for event in events)
    assert events.count("stop-A") == 1
    assert "create-B" not in events
    assert context.sealed is False


def test_owned_binder_projection_failure_closes_factory_created_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_windows

    events: list[str] = []
    created: list[_FakeOwnedPhaseProcess] = []

    def create(phase: str, _runtime_id: str, _wrapper_nonce: str) -> object:
        events.append(f"create-{phase}")
        process = _FakeOwnedPhaseProcess(phase, events)
        process.readers["http"] = process.readers["app"]
        created.append(process)
        return process

    monkeypatch.setattr(
        dual_live_windows,
        "_create_owned_phase_process",
        create,
        raising=False,
    )
    context, _writers = _owned_test_context(events)

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_pump_reader_alias_invalid",
    ):
        dual_live_runtime_module._run_owned_two_phase_controller(context)

    assert len(created) == 1
    assert created[0].close_calls == 1
    assert "create-B" not in events
    assert context.sealed is False


@pytest.mark.skipif(os.name != "nt", reason="Windows owned child proof")
def test_seq_owned_binder_runs_real_inert_children_and_seals_exactly_once() -> None:
    script = f"""
import ctypes
import gc
import io
import json
import sys
import threading
from ctypes import wintypes
sys.path.insert(0, {str(BACKEND)!r})
from app.services import dual_live_runtime as runtime
from app.services import dual_live_windows as windows
assert windows.OwnedPhaseProcess is not None

class Writer(io.BytesIO):
    def __init__(self):
        super().__init__()
        self.closed_clean = False
    def close(self):
        self.closed_clean = True

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.GetCurrentProcess.argtypes = ()
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.GetProcessHandleCount.argtypes = (
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.DWORD),
)
kernel32.GetProcessHandleCount.restype = wintypes.BOOL

def handle_count():
    count = wintypes.DWORD()
    if not kernel32.GetProcessHandleCount(
        kernel32.GetCurrentProcess(), ctypes.byref(count)
    ):
        raise OSError(ctypes.get_last_error())
    return int(count.value)

payload = {RUNTIME_START_PAYLOAD!r}

def run_once(runtime_instance_id):
    identity = runtime.RuntimeIdentity(
        runtime_instance_id=runtime_instance_id,
        wrapper_nonce_sha256={'1' * 64!r},
        code_revision={'2' * 40!r},
        wrapper_image_sha256={'3' * 64!r},
        interpreter_image_sha256={'4' * 64!r},
        dependency_set_sha256={'8' * 64!r},
        root_mutex_identity_sha256={'5' * 64!r},
        campaign_mutex_identity_sha256={'6' * 64!r},
    )
    writers = {{name: Writer() for name in runtime.PIPE_STREAM_CLASSES}}
    context = runtime._make_nonproduction_owned_controller_context(
        identity=identity,
        runtime_start_payload=payload,
        app_writer=writers["app"],
        http_writer=writers["http"],
        stdout_writer=writers["stdout"],
        stderr_writer=writers["stderr"],
        timeout_seconds=10,
    )
    before_handles = handle_count()
    result = runtime._run_owned_two_phase_controller(context)
    after_handles = handle_count()
    records = runtime.read_runtime_records(writers["app"].getvalue())
    starts = [record for record in records if record["event"] == "phase_child_start"]
    return {{
        "active_released": context._active_process is None,
        "after_handles": after_handles,
        "before_handles": before_handles,
        "closed_process_count": len(context._closed_process_ids),
        "result_is_none": result is None,
        "owned_process_count": len(context._owned_processes),
        "quiesced_process_count": len(context._quiesced_process_ids),
        "quiescing_released": context._quiescing_process is None,
        "sealed": context.sealed,
        "events": [record["event"] for record in records],
        "phases": [record["phase"] for record in records],
        "boots": [record["process_boot_id"] for record in starts],
        "creation_ids": [
            record["payload"]["process_creation_identity_sha256"]
            for record in starts
        ],
        "job_policies": [
            record["payload"]["job_policy_sha256"] for record in starts
        ],
        "writers_closed": [
            writers[name].closed_clean for name in runtime.PIPE_STREAM_CLASSES
        ],
    }}, context

cold_handles = handle_count()
first, first_context = run_once({RUNTIME_INSTANCE_ID!r})
first_live_handles = handle_count()
del first_context
gc.collect()
warmed_handles = handle_count()
first_threads = [
    thread.name
    for thread in threading.enumerate()
    if thread is not threading.current_thread() and thread.is_alive()
]
second, second_context = run_once("323e4567-e89b-42d3-a456-426614174000")
second_live_handles = handle_count()
final_threads = [
    thread.name
    for thread in threading.enumerate()
    if thread is not threading.current_thread() and thread.is_alive()
]
del second_context
gc.collect()
final_handles = handle_count()
print(json.dumps({{
    "cold_handles": cold_handles,
    "final_handles": final_handles,
    "final_threads": final_threads,
    "first": first,
    "first_live_handles": first_live_handles,
    "first_threads": first_threads,
    "second": second,
    "second_live_handles": second_live_handles,
    "warmed_handles": warmed_handles,
}}, sort_keys=True, separators=(",", ":")))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script],
        cwd=BACKEND.parent,
        capture_output=True,
        text=True,
        # Four real child lifecycles retain their own bounded boot and phase
        # deadlines; this outer watchdog must not preempt those diagnostics.
        timeout=90,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    summary = json.loads(completed.stdout)
    expected_events = [
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
    expected_phases = [
        "wrapper",
        *("A" for _ in range(8)),
        *("B" for _ in range(7)),
        "wrapper",
    ]
    for run in (summary["first"], summary["second"]):
        assert run["active_released"] is True
        assert run["closed_process_count"] == 2
        assert run["owned_process_count"] == 0
        assert run["quiesced_process_count"] == 2
        assert run["quiescing_released"] is True
        assert run["result_is_none"] is True
        assert run["sealed"] is True
        assert run["events"] == expected_events
        assert run["phases"] == expected_phases
        assert len(run["boots"]) == 2
        assert run["boots"][0] != run["boots"][1]
        assert run["creation_ids"][0] != run["creation_ids"][1]
        assert run["job_policies"][0] == run["job_policies"][1]
        assert run["writers_closed"] == [True, True, True, True]
    assert set(summary["first"]["boots"]).isdisjoint(summary["second"]["boots"])
    assert set(summary["first"]["creation_ids"]).isdisjoint(
        summary["second"]["creation_ids"]
    )
    assert summary["first_threads"] == []
    assert summary["final_threads"] == []
    assert summary["first"]["before_handles"] == summary["cold_handles"] + 1
    assert summary["first"]["after_handles"] == summary["first_live_handles"]
    assert summary["first_live_handles"] == summary["warmed_handles"] + 1
    assert summary["second"]["before_handles"] == summary["warmed_handles"] + 1
    assert summary["second"]["after_handles"] == summary["second_live_handles"]
    assert summary["second_live_handles"] == summary["warmed_handles"] + 1
    assert summary["final_handles"] == summary["warmed_handles"]


def test_stop_bridge_revokes_before_python_stop_publication() -> None:
    events: list[str] = []
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
            _before_stop_publish=lambda _reason: events.append("revoke-A"),
        )

    assert events.index("revoke-A") < events.index("record-stop")
    assert events.index("record-stop") < events.index("stop-A")
    assert events.count("revoke-A") == 1
    assert "create-B" not in events
    assert "seal" not in events


def test_fatal_stop_bridge_failure_cannot_publish_or_seal() -> None:
    events: list[str] = []
    writers = {
        stream: (
            _StopRecordControllerWriter(stream, events)
            if stream == "app"
            else _ControllerWriter(stream, events)
        )
        for stream in PIPE_STREAM_CLASSES
    }

    def fail_stop(_reason: str) -> None:
        events.append("terminate-A")
        raise RuntimeError("revocation failed after fail-stop")

    with pytest.raises(
        DualLiveRuntimeError,
        match="dual_live_stop_publish_failed",
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
            _before_stop_publish=fail_stop,
        )

    assert isinstance(exc.value.__cause__, RuntimeError)
    assert events.count("terminate-A") == 1
    assert "record-stop" not in events
    assert "create-B" not in events
    assert "seal" not in events


def test_cancel_start_then_raise_retains_launched_reader_custody(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BlockingReader:
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

    blocker = BlockingReader()
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
    original_start = threading.Thread.start
    launched: list[threading.Thread] = []

    def start_then_raise(thread: threading.Thread) -> None:
        original_start(thread)
        if thread.name == "dual-live-app-cancel":
            launched.append(thread)
            assert blocker.close_entered.wait(timeout=1)
            raise RuntimeError("start returned failure after launch")

    pumps.start()
    monkeypatch.setattr(threading.Thread, "start", start_then_raise)
    try:
        with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_cancel_failed"):
            pumps.join(timeout=0)

        owned, completed = pumps.cancellation_reader_custody
        assert id(blocker) in owned
        assert id(blocker) not in completed
        assert launched and launched[0].is_alive()
    finally:
        blocker.close_release.set()
        blocker.read_release.set()
        for thread in launched:
            thread.join(timeout=1)


def test_exit_unproven_dead_reader_close_is_bounded_and_never_seals() -> None:
    class DeadBlockingCloseReader(_ControllerReader):
        def __init__(self) -> None:
            super().__init__()
            self.close_entered = threading.Event()
            self.close_release = threading.Event()

        def close(self) -> None:
            self.close_entered.set()
            self.close_release.wait()
            super().close()

    events: list[str] = []
    blocker = DeadBlockingCloseReader()
    writers = {
        stream: _ControllerWriter(stream, events) for stream in PIPE_STREAM_CLASSES
    }
    results: list[BaseException] = []

    def run() -> None:
        try:
            dual_live_runtime_module._run_two_phase_controller(
                identity=RUNTIME_IDENTITY,
                runtime_start_payload=RUNTIME_START_PAYLOAD,
                writers=writers,
                create_phase_a=lambda: _controller_child(
                    "A",
                    events,
                    app_reader=blocker,
                    wait_error=RuntimeError("exit unproven"),
                ),
                create_phase_b=lambda: events.append("create-B"),
                quiesce_phase=lambda _phase, _child: (),
                clear_authority=lambda _phase, _child: {},
                http_frame_validator=lambda _payload: None,
                seal=lambda: events.append("seal"),
                timeout_seconds=0.05,
            )
        except BaseException as exc:
            results.append(exc)

    caller = threading.Thread(target=run, daemon=True)
    caller.start()
    assert blocker.close_entered.wait(timeout=1)
    caller.join(timeout=0.3)
    try:
        assert caller.is_alive() is False
        assert results
        assert isinstance(results[0], DualLiveRuntimeError)
        assert "seal" not in events
        assert all(not writer.closed_clean for writer in writers.values())
    finally:
        blocker.close_release.set()
        caller.join(timeout=1)


def test_writer_failure_precedes_secondary_cancel_start_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BlockingReader:
        def __init__(self) -> None:
            self.release = threading.Event()

        def read(self, _size: int) -> bytes:
            self.release.wait()
            return b""

        def close(self) -> None:
            self.release.set()

    class ShortWriter(MemorySink):
        def write(self, content: bytes) -> int:
            super().write(content[:-1])
            return len(content) - 1

    blocker = BlockingReader()
    readers = {
        "app": blocker,
        "http": io.BytesIO(),
        "stdout": io.BytesIO(),
        "stderr": io.BytesIO(encode_pipe_frame(b"writer-failure")),
    }
    writers = {stream: MemorySink() for stream in readers}
    writers["stderr"] = ShortWriter()
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
    original_start = threading.Thread.start

    def fail_app_cancel_start(thread: threading.Thread) -> None:
        if thread.name == "dual-live-app-cancel":
            raise RuntimeError("secondary cancel start failed")
        original_start(thread)

    pumps.start()
    deadline = time.monotonic() + 1
    while stop.reason_code != "writer_failure" and time.monotonic() < deadline:
        time.sleep(0.001)
    assert stop.reason_code == "writer_failure"
    monkeypatch.setattr(threading.Thread, "start", fail_app_cancel_start)
    try:
        with pytest.raises(DualLiveRuntimeError, match="dual_live_pump_failed") as exc:
            pumps.join(timeout=0)

        assert isinstance(exc.value.__cause__, DualLiveRuntimeError)
        assert exc.value.__cause__.code == "dual_live_pump_write_failed"
        assert isinstance(exc.value.__context__, DualLiveRuntimeError)
        assert exc.value.__context__.code == "dual_live_pump_cancel_failed"
        assert stop.reason_code == "writer_failure"
    finally:
        blocker.release.set()


# Canonical V4 collection surface. Bind acceptance nodes last because strict NRC
# parsing installs the production process-lifetime spawn guard by design.
sealed_campaign_template = dual_live_acceptance.sealed_campaign_template
matrix_campaign = dual_live_acceptance.matrix_campaign
test_all_69_checks_have_positive_and_named_negative_evidence = (
    dual_live_acceptance.test_all_69_checks_have_positive_and_named_negative_evidence
)
test_real_constructor_campaign_evaluates_all_69_checks_pass_once = (
    dual_live_acceptance.test_real_constructor_campaign_evaluates_all_69_checks_pass_once
)
test_public_nrc_path_proves_integrity_through_handoff_and_reporting = (
    dual_live_acceptance.test_public_nrc_path_proves_integrity_through_handoff_and_reporting
)
test_public_sciencebase_path_proves_strict_origin_through_handoff = (
    dual_live_acceptance.test_public_sciencebase_path_proves_strict_origin_through_handoff
)
test_real_gate_process_runs_g01_g02_then_all_69_checks_pass = (
    dual_live_acceptance.test_real_gate_process_runs_g01_g02_then_all_69_checks_pass
)
test_writable_caller_session_fails_closed_without_mutation = (
    dual_live_acceptance.test_writable_caller_session_fails_closed_without_mutation
)
test_one_log_byte_and_rebuilt_manifest_preserve_exact_seal_taxonomy = (
    dual_live_acceptance.test_one_log_byte_and_rebuilt_manifest_preserve_exact_seal_taxonomy
)
test_one_log_byte_rebuilt_manifest_and_seal_exposes_database_witness = (
    dual_live_acceptance.test_one_log_byte_rebuilt_manifest_and_seal_exposes_database_witness
)
test_database_seal_event_rewrite_cannot_rewrite_original_files = (
    dual_live_acceptance.test_database_seal_event_rewrite_cannot_rewrite_original_files
)
