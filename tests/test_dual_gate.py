from __future__ import annotations

import ast
import base64
from collections.abc import Mapping
from contextlib import AbstractContextManager, contextmanager
import ctypes
from dataclasses import FrozenInstanceError, fields
import gc
import hashlib
import importlib.util
import inspect
import io
import json
import os
import runpy
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.dual_live_windows import (  # noqa: E402
    DualLiveWindowsError,
    JobChild,
    ProofLocks,
    acquire_proof_locks,
    acquire_proof_locks_staged,
    create_child_in_job,
    prove_child_quiescence,
)
from app.services import dual_live_windows  # noqa: E402
from app.services.connector_egress_authorization import (  # noqa: E402
    canonical_json_bytes as framework_canonical_json_bytes,
)
from app.services.dual_live_runtime import WINDOWS_MIB_TCP_STATES  # noqa: E402
from app.services.dual_live_evaluator import (  # noqa: E402
    EVALUATOR_CHECK_ORDER,
    EVALUATOR_NONCLAIMS,
    build_indeterminate_dual_live_report,
)


GATE = ROOT / "tools" / "dual_live_gate.py"
RUNNER = ROOT / "tools" / "dual_live_run.py"
PROJECT6 = ROOT / "project6.ps1"
FROZEN_PLAN = ROOT / "docs" / "superpowers" / "plans" / "2026-07-29-dual-live-proof.md"
PILOT_TEST = ROOT / "backend" / "tests" / "test_layer3_connector_vertical_loop.py"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
CAMPAIGN_ID = "123e4567-e89b-42d3-a456-426614174000"
CAMPAIGN_FINGERPRINT = "a" * 64
DEFINITION_SHA = "b" * 64
OTHER_CAMPAIGN_ID = "223e4567-e89b-42d3-a456-426614174000"
RUNTIME_INSTANCE_ID = "323e4567-e89b-42d3-a456-426614174000"
WRAPPER_NONCE_SHA = "c" * 64
EXPECTED_FROZEN_PLAN_BLOB = "68f740af86dc7d1ac2227f81a6ea28e7e2c7458f"
TASK8_IMPLEMENTATION_BASE = "49cc7e20d1a4dcd6f84df076aafc18d0cd03b876"
FORBIDDEN_REQUIRED_ALIASES = (
    "DUAL_LIVE_POSTRUN",
    "DUAL_LIVE_ATTESTATION",
    "DUAL_LIVE_ISSUER",
)
FORBIDDEN_PRODUCTION_PATHS = (
    "backend/app/services/dual_live_postrun_evidence.py",
    "tools/dual_live_issue.py",
)
ALLOWED_NEW_PRODUCTION_PATHS = (
    "backend/app/services/dual_live_runtime.py",
    "backend/app/services/dual_live_windows.py",
    "tools/dual_live_run.py",
)
G2_PREP_ALLOWED_CHANGED_PRODUCTION_PATHS = (
    "backend/app/api/router.py",
    "tools/dual_live_recovery.py",
)
FIRST_TRANCHE_REQUIRED_PRODUCTION_PATHS = (
    "backend/app/services/dual_live_runtime.py",
)
ALLOWED_CHANGED_PRODUCTION_PATHS = frozenset(
    (
        *ALLOWED_NEW_PRODUCTION_PATHS,
        *G2_PREP_ALLOWED_CHANGED_PRODUCTION_PATHS,
        "backend/app/core/config.py",
        "backend/app/services/connector_egress_authorization.py",
        "backend/app/services/connector_egress_evidence.py",
        "backend/app/services/connector_egress_transport.py",
        "backend/app/services/connectors_nrc_adams.py",
        "backend/app/services/connectors_sciencebase.py",
        "backend/app/services/connector_egress_arming.py",
        "backend/app/services/connector_campaign_log_capture.py",
        "backend/app/services/dual_live_dependencies.py",
        "backend/app/services/dual_live_evaluator.py",
        "backend/app/services/layer3_gate_b_state.py",
        "backend/app/services/layer3_connector_source_intake.py",
        "backend/app/services/layer3_execution_output.py",
        "backend/app/services/layer3_origin_continuity.py",
        "backend/app/services/layer3_pass_entry.py",
        "backend/app/services/layer3_typing_entry.py",
        "backend/app/services/layer3_workbench.py",
        "backend/app/services/nrc_aps_phase_b_linkage.py",
        "tools/dual_live_gate.py",
        "project6.ps1",
    )
)
AUTHORITY_VARIABLES = (
    "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
    "CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
    "CONNECTOR_SCIENCEBASE_GRANT_PATH",
    "CONNECTOR_SCIENCEBASE_GRANT_SHA256",
    "CONNECTOR_NRC_APS_GRANT_PATH",
    "CONNECTOR_NRC_APS_GRANT_SHA256",
)
def _git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def _is_production_path(path: str) -> bool:
    return (
        path == "project6.ps1"
        or path.startswith("backend/app/")
        or path.startswith("tools/")
    )


def _changed_production_surface() -> tuple[frozenset[str], frozenset[str]]:
    diff_lines = _git_output(
        "diff",
        "--name-status",
        "--diff-filter=ACMRD",
        TASK8_IMPLEMENTATION_BASE,
    ).splitlines()
    untracked = _git_output(
        "ls-files",
        "--others",
        "--exclude-standard",
        "--",
        "backend/app",
        "tools",
        "project6.ps1",
    ).splitlines()
    changed: set[str] = set()
    deleted: set[str] = set()
    for line in diff_lines:
        fields = line.split("\t")
        status = fields[0]
        if status.startswith("R"):
            old_path, new_path = fields[1:]
            if _is_production_path(old_path):
                changed.add(old_path)
                deleted.add(old_path)
            if _is_production_path(new_path):
                changed.add(new_path)
        elif status.startswith("C"):
            new_path = fields[-1]
            if _is_production_path(new_path):
                changed.add(new_path)
        else:
            path = fields[-1]
            if _is_production_path(path):
                changed.add(path)
                if status == "D":
                    deleted.add(path)
    changed.update(path for path in untracked if _is_production_path(path))
    return frozenset(changed), frozenset(deleted)


def _changed_production_paths() -> frozenset[str]:
    changed, _ = _changed_production_surface()
    return changed


def _deleted_production_paths() -> frozenset[str]:
    _, deleted = _changed_production_surface()
    return deleted


def _a_scoped_production_surface_is_allowed() -> bool:
    changed, deleted = _changed_production_surface()
    return not deleted and changed <= ALLOWED_CHANGED_PRODUCTION_PATHS


def _tracked_source_text() -> str:
    paths = ALLOWED_CHANGED_PRODUCTION_PATHS | _changed_production_paths()
    return "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in sorted(paths)
        if (ROOT / path).is_file()
    )


def _git_blob_sha(path: Path) -> str:
    return _git_output("hash-object", str(path.relative_to(ROOT)))


def _init_source_identity_repo(tmp_path: Path) -> tuple[Path, Path]:
    git_path = Path(r"C:\Program Files\Git\cmd\git.exe")
    assert git_path.is_file()
    repo = tmp_path / "source-repo"
    wrapper = repo / "tools" / "dual_live_run.py"
    module = repo / "backend" / "app" / "services" / "runtime.py"
    readme = repo / "README.md"
    wrapper.parent.mkdir(parents=True)
    module.parent.mkdir(parents=True)
    wrapper.write_bytes(b"print('owned wrapper')\n")
    module.write_bytes(b"VALUE = 1\n")
    readme.write_bytes(b"reviewed tree\n")
    commands = (
        ("init", "--quiet"),
        ("config", "user.name", "Project6 Test"),
        ("config", "user.email", "project6-test@example.invalid"),
        (
            "add",
            "--",
            "tools/dual_live_run.py",
            "backend/app/services/runtime.py",
            "README.md",
        ),
        ("commit", "--quiet", "-m", "fixture"),
    )
    for command in commands:
        completed = subprocess.run(
            [str(git_path), *command],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
    return repo, wrapper


def _pilot_seal() -> str:
    tree = ast.parse(PILOT_TEST.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == "FIXTURE_SOURCE_FILE_GIT_BLOB":
            value = ast.literal_eval(node.value)
            assert isinstance(value, str)
            return value
    raise AssertionError("pilot seal constant is missing")


def test_a_scoped_build_adds_no_attestation_index_or_env_contract() -> None:
    tracked = _tracked_source_text()
    assert all(alias not in tracked for alias in FORBIDDEN_REQUIRED_ALIASES)
    assert all(not (ROOT / path).exists() for path in FORBIDDEN_PRODUCTION_PATHS)


def test_a_scoped_changed_production_surface_is_allowlisted() -> None:
    assert _a_scoped_production_surface_is_allowed()


def test_deleted_production_path_is_detected_and_forbidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deleted = "backend/app/services/dual_live_runtime.py"

    def fake_git_output(*args: str) -> str:
        if args and args[0] == "diff":
            return f"D\t{deleted}"
        return ""

    monkeypatch.setattr(sys.modules[__name__], "_git_output", fake_git_output)

    assert deleted in _changed_production_paths()
    assert deleted in _deleted_production_paths()
    assert not _a_scoped_production_surface_is_allowed()


def test_frozen_and_sealed_authority_files_are_unchanged() -> None:
    assert _git_blob_sha(FROZEN_PLAN) == EXPECTED_FROZEN_PLAN_BLOB
    assert _pilot_seal() == "b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2"


def test_a_scoped_build_has_required_runtime_units() -> None:
    assert all(
        (ROOT / path).is_file() for path in FIRST_TRANCHE_REQUIRED_PRODUCTION_PATHS
    )


def test_refuse_direct_tool_no_args_has_exact_output_and_no_side_effects(
    tmp_path: Path,
) -> None:
    before = tuple(tmp_path.iterdir())

    completed = subprocess.run(
        [sys.executable, "-I", "-B", str(RUNNER)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "dual_live_run_refused\n"
    assert tuple(tmp_path.iterdir()) == before


@pytest.mark.parametrize(
    "arguments",
    (
        ("--owned-child", "not-a-canonical-capsule"),
        ("--owned-child", "e30"),
        ("--owned-child", "e30", "extra"),
    ),
)
def test_refuse_malformed_or_nonisolated_owned_child_invocation(
    tmp_path: Path,
    arguments: tuple[str, ...],
) -> None:
    before = tuple(tmp_path.iterdir())

    completed = subprocess.run(
        [sys.executable, "-B", str(RUNNER), *arguments],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "dual_live_run_refused\n"
    assert tuple(tmp_path.iterdir()) == before


def test_refuse_nonisolated_structurally_valid_owned_capsule(tmp_path: Path) -> None:
    payload = {
        "handles": {
            "child_app_write_handle": 101,
            "child_control_read_handle": 102,
            "child_http_write_handle": 103,
            "child_stderr_write_handle": 104,
            "child_stdout_write_handle": 105,
        },
        "phase": "B",
        "runtime_instance_id": RUNTIME_INSTANCE_ID,
        "schema_id": "project6.dual_live_owned_child.v1",
        "wrapper_nonce_sha256": WRAPPER_NONCE_SHA,
    }
    capsule = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()

    completed = subprocess.run(
        [sys.executable, "-B", str(RUNNER), "--owned-child", capsule],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "dual_live_run_refused\n"
    assert tuple(tmp_path.iterdir()) == ()


def test_owned_process_surface_is_factory_only_and_opaque() -> None:
    assert tuple(inspect.signature(
        dual_live_windows._create_owned_phase_process
    ).parameters) == (
        "phase",
        "runtime_instance_id",
        "wrapper_nonce_sha256",
        "environment",
    )
    with pytest.raises(
        DualLiveWindowsError,
        match="dual_live_owned_process_factory_only",
    ):
        dual_live_windows.OwnedPhaseProcess()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_factory_boot_reader_bypass_refuses_outside_native_custody_window() -> None:
    reader = object.__new__(dual_live_windows._OwnedPipeReader)

    with pytest.raises(
        DualLiveWindowsError,
        match="dual_live_owned_process_factory_only",
    ):
        reader._read_in_native_custody_window(
            1,
            dual_live_windows._OWNED_PROCESS_FACTORY_TOKEN,
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("phase", ("A", "B"))
def test_owned_child_boot_go_exit_job_and_inert_authority_contract(
    phase: str,
) -> None:
    from app.services.dual_live_runtime import (
        CHILD_PROOF_SCHEMA_ID,
        canonical_json_bytes,
        decode_child_proof_frame,
        decode_child_status_frame,
        encode_child_control_frame,
        encode_pipe_frame,
        read_pipe_frame,
    )

    child = dual_live_windows._create_owned_phase_process(
        phase,
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    assert isinstance(child, dual_live_windows.OwnedPhaseProcess)
    assert all(
        isinstance(value, str) and len(value) == 64
        for value in (
            child.process_boot_id,
            child.process_creation_identity_sha256,
            child.executable_sha256,
            child.job_policy_sha256,
            child.status_nonce_sha256,
            child.control_nonce,
        )
    )
    assert set(child.readers) == {"app", "http", "stdout", "stderr"}
    assert len({id(reader) for reader in child.readers.values()}) == 4
    assert all(
        not hasattr(reader, "handle") and not hasattr(reader, "fileno")
        for reader in child.readers.values()
    )
    assert all(
        not hasattr(child, name)
        for name in ("pid", "job_handle", "process_handle", "argv", "environment")
    )

    try:
        from app.services import dual_live_runtime

        pre_payload = dual_live_runtime._read_pipe_frame(
            child.readers["app"],
            allowed_reserved_schema_ids=frozenset(
                (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
            ),
        )
        assert pre_payload is not None
        pre = decode_child_status_frame(
            pre_payload,
            expected_phase=phase,
            expected_process_boot_id=child.process_boot_id,
            expected_status_nonce_sha256=child.status_nonce_sha256,
            expected_ordinal=1,
        )
        assert pre["payload"]["census_point"] == "pre_activity"
        boot_frame_sha256 = hashlib.sha256(
            encode_pipe_frame(
                canonical_json_bytes(
                    {
                        "control_nonce": child.control_nonce,
                        "phase": phase,
                        "process_boot_id": child.process_boot_id,
                        "schema_id": "project6.dual_live_owned_boot.v1",
                        "status_nonce_sha256": child.status_nonce_sha256,
                    }
                )
            )
        ).hexdigest()
        pre_status_frame_sha256 = hashlib.sha256(
            len(pre_payload).to_bytes(4, "big") + pre_payload
        ).hexdigest()
        previous_proof_sha256: str | None = None

        def read_proof(ordinal: int) -> dict[str, object]:
            nonlocal previous_proof_sha256
            payload = dual_live_runtime._read_pipe_frame(
                child.readers["stdout"],
                allowed_reserved_schema_ids=frozenset((CHILD_PROOF_SCHEMA_ID,)),
            )
            assert payload is not None
            proof = decode_child_proof_frame(
                payload,
                expected_phase=phase,
                expected_process_boot_id=child.process_boot_id,
                expected_status_nonce_sha256=child.status_nonce_sha256,
                expected_ordinal=ordinal,
                expected_previous_record_sha256=previous_proof_sha256,
                expected_proof_scope="mechanical",
            )
            previous_proof_sha256 = cast(str, proof["record_sha256"])
            return cast(dict[str, object], proof)

        if phase == "B":
            pre_guard = read_proof(1)
            pre_guard_payload = cast(dict[str, object], pre_guard["payload"])
            assert pre_guard_payload["proof_point"] == "pre_go"
            assert pre_guard_payload["boot_frame_sha256"] == boot_frame_sha256
            assert (
                pre_guard_payload["pre_activity_status_frame_sha256"]
                == pre_status_frame_sha256
            )

        go_frame = encode_child_control_frame(
            phase=phase,
            command="GO",
            control_nonce=child.control_nonce,
        )
        child.send_control(go_frame)
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_control_consumed",
        ):
            child.send_control(go_frame)
        assert child.poll_exit(10) == 0

        exit_payload = dual_live_runtime._read_pipe_frame(
            child.readers["app"],
            allowed_reserved_schema_ids=frozenset(
                (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
            ),
        )
        assert exit_payload is not None
        exited = decode_child_status_frame(
            exit_payload,
            expected_phase=phase,
            expected_process_boot_id=child.process_boot_id,
            expected_status_nonce_sha256=child.status_nonce_sha256,
            expected_ordinal=2,
        )
        assert exited["payload"]["census_point"] == "exit"
        assert exited["payload"]["topology_sha256"] == pre["payload"][
            "topology_sha256"
        ]
        exit_status_frame_sha256 = hashlib.sha256(
            len(exit_payload).to_bytes(4, "big") + exit_payload
        ).hexdigest()
        control_frame_sha256 = hashlib.sha256(go_frame).hexdigest()
        assert read_pipe_frame(child.readers["app"]) is None
        assert read_pipe_frame(child.readers["http"]) is None
        terminal_proofs = [read_proof(1 if phase == "A" else 2)]
        if phase == "B":
            terminal_proofs.append(read_proof(3))
        for proof in terminal_proofs:
            proof_payload = cast(dict[str, object], proof["payload"])
            assert proof_payload["boot_frame_sha256"] == boot_frame_sha256
            assert proof_payload["control_frame_sha256"] == control_frame_sha256
            assert (
                proof_payload["pre_activity_status_frame_sha256"]
                == pre_status_frame_sha256
            )
            assert (
                proof_payload["exit_status_frame_sha256"]
                == exit_status_frame_sha256
            )
        if phase == "A":
            assert terminal_proofs[0]["event"] == "acquisition_boundary"
            assert cast(dict[str, object], terminal_proofs[0]["payload"])[
                "connector_acquisitions"
            ] == []
        else:
            assert [proof["event"] for proof in terminal_proofs] == [
                "downstream_chain",
                "guard",
            ]
            assert cast(dict[str, object], terminal_proofs[0]["payload"])[
                "terminal_boundary"
            ] == "mechanical_complete"
            assert cast(dict[str, object], terminal_proofs[1]["payload"])[
                "proof_point"
            ] == "exit"
        assert read_pipe_frame(child.readers["stdout"]) is None
        assert read_pipe_frame(child.readers["stderr"]) is None

        child.stop()
        child.stop()
        socket_payload, job_payload = child.quiesce_and_close()
        assert socket_payload["stable"] is True
        assert job_payload["active_process_count"] == 0
        if phase == "A":
            authority = child.authority_cleared_payload()
            assert authority["all_required_absent"] is True
            assert (
                authority["authority_posture_sha256"]
                == dual_live_runtime.AUTHORITY_CLEARED_POSTURE_SHA256
            )
        else:
            child.revoke_before_stop("permanent_denial")
    finally:
        child.close()


@pytest.mark.parametrize(
    ("wait_result", "expected_exit", "expected_guard_calls", "raises"),
    (
        (0x102, 0, [], False),
        (0, 23, [], False),
        (0xFFFFFFFF, None, [], True),
        (7, None, [], True),
    ),
)
def test_phase_a_guard_window_requires_exact_revocation_wait_result(
    wait_result: int,
    expected_exit: int | None,
    expected_guard_calls: list[str],
    raises: bool,
) -> None:
    runner = runpy.run_path(str(RUNNER))
    actual_guard_calls: list[str] = []
    idle_set_calls = 0

    class Kernel:
        def ResetEvent(self, _handle: int) -> int:
            return 1

        def WaitForSingleObject(self, _handle: int, _timeout: int) -> int:
            return wait_result

        def SetEvent(self, _handle: int) -> int:
            nonlocal idle_set_calls
            idle_set_calls += 1
            return 1

    class Guards:
        def restore(self) -> None:
            actual_guard_calls.append("restore")

        def install(self) -> None:
            actual_guard_calls.append("install")

    operation = runner["_phase_a_guard_window"]
    if raises:
        with pytest.raises(OSError):
            operation(Kernel(), Guards(), idle=11, revoked=12)
    else:
        assert operation(Kernel(), Guards(), idle=11, revoked=12) == expected_exit
    assert actual_guard_calls == expected_guard_calls
    assert idle_set_calls == 1


def test_phase_b_standard_guards_are_permanent_and_report_exact_routes() -> None:
    runner = runpy.run_path(str(RUNNER))
    guards = runner["_StandardLibraryGuards"]("B")
    try:
        guards.install()
        assert guards.exercise(connector_probe=lambda: None) == {
            "denied_routes": [
                "dns",
                "http",
                "socket",
                "subprocess",
                "connector_transport",
            ],
            "network_enable_attempt_count": 0,
            "original_implementation_call_count": 0,
        }
        with pytest.raises(
            PermissionError,
            match="dual_live_inert_guard_enable_denied",
        ):
            guards.enable_phase_a_transport()
        with pytest.raises(
            RuntimeError,
            match="dual_live_inert_guard_enable_attempted",
        ):
            guards.assert_intact()
        with pytest.raises(
            RuntimeError,
            match="dual_live_inert_guard_permanent",
        ):
            guards.restore()
    finally:
        for target, name, original in guards._entries:
            setattr(target, name, original)


def test_phase_a_network_guard_can_open_once_then_seals() -> None:
    runner = runpy.run_path(str(RUNNER))
    guards = runner["_StandardLibraryGuards"]("A")
    try:
        guards.install()
        guards.enable_phase_a_transport()
        guards.assert_intact()
        guards.install()
        guards.assert_intact()
        with pytest.raises(
            PermissionError,
            match="dual_live_inert_guard_enable_denied",
        ):
            guards.enable_phase_a_transport()
        guards.assert_intact()
    finally:
        for target, name, original in guards._entries:
            setattr(target, name, original)


def test_wrapper_guard_stages_network_before_permanent_subprocess_denial() -> None:
    runner = runpy.run_path(str(RUNNER))
    guards = runner["_StandardLibraryGuards"]("wrapper")
    try:
        guards.install_wrapper_network_denial()
        assert all(
            getattr(target, name) is guards._guard
            for target, name, _original in guards._network_entries
        )
        assert all(
            getattr(target, name) is original
            for target, name, original in guards._subprocess_entries
        )
        with pytest.raises(RuntimeError, match="dual_live_inert_guard_changed"):
            guards.assert_intact()

        guards.install()
        guards.assert_intact()
        assert all(
            getattr(target, name) is guards._guard
            for target, name, _original in guards._entries
        )
        for _target, _name, callback in (
            (target, name, getattr(target, name))
            for target, name, _original in guards._subprocess_entries
        ):
            with pytest.raises(PermissionError, match="dual_live_inert_guard"):
                callback((sys.executable, "-I", "-B", "-c", "pass"))
    finally:
        for target, name, original in guards._entries:
            setattr(target, name, original)


def test_wrapper_guard_precedes_backend_import_and_preserves_native_factory() -> None:
    from app.services import dual_live_runtime

    runner = runpy.run_path(str(RUNNER))
    blocker = runner["_WrapperConnectorImportGuard"]()
    for module_name in runner["_WRAPPER_BLOCKED_CONNECTOR_MODULES"]:
        with pytest.raises(
            ImportError,
            match="dual_live_wrapper_connector_import_denied",
        ):
            blocker.find_spec(module_name)
    assert blocker.find_spec("app.services.dual_live_runtime") is None

    public_source = inspect.getsource(runner["_run_public_mode"])
    assert (
        public_source.index('_StandardLibraryGuards("wrapper")')
        < public_source.index("guards.install_wrapper_network_denial()")
        < public_source.index("_install_wrapper_connector_import_guard()")
        < public_source.index('backend = Path(__file__).resolve()')
        < public_source.index("from app.services import dual_live_windows")
        < public_source.index("guards.install()")
        < public_source.index(
            "dual_live_windows._register_subprocess_gate_baseline(guards._guard)"
        )
        < public_source.index(
            "from app.services.dual_live_runtime import run_dual_live_campaign"
        )
    )
    assert public_source.count("from app.services import dual_live_windows") == 1
    windows_module_source = inspect.getsource(dual_live_windows)
    reviewed_git_source = inspect.getsource(dual_live_windows._run_reviewed_git)
    assert windows_module_source.count("_REVIEWED_GIT_POPEN") == 2
    assert "process = _REVIEWED_GIT_POPEN(" in reviewed_git_source
    assert "_SUBPROCESS_GATE_BASELINE" not in reviewed_git_source
    assert "shell=False" in reviewed_git_source
    assert "cwd=str(repo_root)" in reviewed_git_source
    assert "env=_reviewed_git_environment()" in reviewed_git_source
    controller_source = inspect.getsource(
        dual_live_runtime._run_bound_owned_two_phase_controller
    )
    assert controller_source.count(
        "dual_live_windows._create_owned_phase_process"
    ) == 1
    assert controller_source.index(
        "owned_child_factory = dual_live_windows._create_owned_phase_process"
    ) < controller_source.index("def create(")
    windows_source = inspect.getsource(
        dual_live_windows._create_child_in_job_locked
    )
    assert "CreateProcessW" in windows_source
    assert "subprocess.Popen" not in windows_source
    assert "subprocess.run" not in windows_source


def test_owned_child_window_restores_one_time_registered_wrapper_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_popen = subprocess.Popen

    def wrapper_denial(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("wrapper denial")

    def mutation(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("mutated")

    monkeypatch.setattr(
        dual_live_windows,
        "_SUBPROCESS_GATE_BASELINE",
        original_popen,
    )
    monkeypatch.setattr(
        dual_live_windows,
        "_SUBPROCESS_GATE_BASELINE_REGISTERED",
        False,
    )
    try:
        setattr(subprocess, "Popen", wrapper_denial)
        dual_live_windows._register_subprocess_gate_baseline(wrapper_denial)

        with dual_live_windows._owned_child_creation_window():
            assert subprocess.Popen is dual_live_windows._refuse_unrelated_subprocess
        assert subprocess.Popen is wrapper_denial

        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_subprocess_gate_baseline_already_registered",
        ):
            dual_live_windows._register_subprocess_gate_baseline(wrapper_denial)

        setattr(subprocess, "Popen", mutation)
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_subprocess_gate_compromised",
        ):
            with dual_live_windows._owned_child_creation_window():
                raise AssertionError("pre-window mutation was admitted")
        assert subprocess.Popen is wrapper_denial

        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_subprocess_gate_compromised",
        ):
            with dual_live_windows._owned_child_creation_window():
                setattr(subprocess, "Popen", mutation)
        assert subprocess.Popen is wrapper_denial
    finally:
        setattr(subprocess, "Popen", original_popen)


@pytest.mark.skipif(os.name != "nt", reason="Windows wrapper activation only")
def test_fresh_wrapper_activation_preserves_only_reviewed_git_launch(
) -> None:
    probe = f"""
import importlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

runner = runpy.run_path({str(RUNNER)!r})
original_popen = subprocess.Popen
guards = runner["_StandardLibraryGuards"]("wrapper")
guards.install_wrapper_network_denial()
runner["_install_wrapper_connector_import_guard"]()
sys.path.insert(0, {str(BACKEND)!r})
assert "app.services.dual_live_windows" not in sys.modules
assert "app.services.dual_live_runtime" not in sys.modules
from app.services import dual_live_windows as windows
assert windows._REVIEWED_GIT_POPEN is original_popen
assert "app.services.dual_live_runtime" not in sys.modules
assert not any(
    name in sys.modules for name in runner["_WRAPPER_BLOCKED_CONNECTOR_MODULES"]
)

guards.install()
windows._register_subprocess_gate_baseline(guards._guard)
guards.assert_intact()

def assert_denied() -> None:
    for name in ("Popen", "run", "check_call", "check_output"):
        try:
            getattr(subprocess, name)((sys.executable, "-I", "-B", "-c", "pass"))
        except PermissionError as exc:
            assert str(exc) == "dual_live_inert_guard"
        else:
            raise AssertionError(name)

def assert_permanent() -> None:
    guards.assert_intact()
    assert all(
        getattr(target, name) is guards._guard
        for target, name, _original in guards._network_entries
    )
    assert_denied()
    for module_name in runner["_WRAPPER_BLOCKED_CONNECTOR_MODULES"]:
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            assert str(exc) == "dual_live_wrapper_connector_import_denied"
        else:
            raise AssertionError(module_name)

assert_permanent()
git_custody = windows._open_executable_custody(str(windows._trusted_git_path()))
try:
    git_code, git_output = windows._run_reviewed_git(
        git_custody,
        Path({str(ROOT)!r}),
        "rev-parse",
        "--show-toplevel",
    )
finally:
    windows._close_handle(git_custody.handle)
assert git_code == 0 and git_output.strip()
assert_permanent()

created = []
marker = object()
original_create = windows.create_child_in_job
def fake_create_child(**kwargs):
    assert subprocess.Popen is windows._refuse_unrelated_subprocess
    created.append(tuple(kwargs["argv"]))
    return marker
windows.create_child_in_job = fake_create_child
try:
    for phase in ("A", "B"):
        channels = windows.create_phase_channels(phase)
        try:
            assert channels._admit_owned_child(
                windows._PHASE_CHANNELS_FACTORY_TOKEN,
                runtime_instance_id={RUNTIME_INSTANCE_ID!r},
                wrapper_nonce_sha256={WRAPPER_NONCE_SHA!r},
            ) is marker
        finally:
            channels.close()
        assert subprocess.Popen is guards._guard
finally:
    windows.create_child_in_job = original_create
assert len(created) == 2
assert_permanent()

runtime = importlib.import_module("app.services.dual_live_runtime")
assert callable(runtime.run_dual_live_campaign)
asyncio_windows = importlib.import_module("asyncio.windows_utils")
try:
    asyncio_windows.Popen((sys.executable, "-I", "-B", "-c", "pass"))
except PermissionError as exc:
    assert str(exc) == "dual_live_inert_guard"
else:
    raise AssertionError("asyncio subprocess denial was bypassed")
assert not any(
    name in sys.modules for name in runner["_WRAPPER_BLOCKED_CONNECTOR_MODULES"]
)
assert_permanent()
os.write(1, json.dumps({{"git": True, "phases": len(created)}}).encode("ascii"))
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-X",
            "pycache_prefix=NUL",
            "-c",
            probe,
        ],
        cwd=ROOT,
        env=_job_environment(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"git": True, "phases": 2}


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_duplicate_reclaims_false_nonzero_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = dual_live_windows.create_phase_channels("B")
    original_duplicate = dual_live_windows._kernel32.DuplicateHandle
    original_get = dual_live_windows._kernel32.GetHandleInformation
    original_close = dual_live_windows._kernel32.CloseHandle
    try:
        with _lease_wrapper_handles(channels) as handles:
            source = handles["wrapper_control_write_handle"]
            baseline = _process_handle_count()

            def duplicate_then_fail(*arguments: object) -> int:
                assert original_duplicate(*arguments)
                ctypes.set_last_error(5)
                return 0

            monkeypatch.setattr(
                dual_live_windows._kernel32,
                "DuplicateHandle",
                duplicate_then_fail,
            )
            with pytest.raises(
                DualLiveWindowsError,
                match="dual_live_owned_handle_duplicate_failed",
            ):
                dual_live_windows._duplicate_owned_handle(source)
            assert _process_handle_count() == baseline

            monkeypatch.setattr(
                dual_live_windows._kernel32,
                "DuplicateHandle",
                original_duplicate,
            )
            monkeypatch.setattr(
                dual_live_windows._kernel32,
                "GetHandleInformation",
                lambda *_arguments: 0,
            )
            monkeypatch.setattr(
                dual_live_windows._kernel32,
                "CloseHandle",
                lambda _handle: 0,
            )
            with pytest.raises(
                DualLiveWindowsError,
                match="dual_live_owned_handle_cleanup_failed",
            ):
                dual_live_windows._duplicate_owned_handle(source)
            assert len(dual_live_windows._retained_owned_handles) == 1
            assert _process_handle_count() == baseline + 1

            monkeypatch.setattr(
                dual_live_windows._kernel32,
                "GetHandleInformation",
                original_get,
            )
            monkeypatch.setattr(
                dual_live_windows._kernel32,
                "CloseHandle",
                original_close,
            )
            dual_live_windows._retry_retained_owned_handles()
            assert dual_live_windows._retained_owned_handles == set()
            assert _process_handle_count() == baseline
    finally:
        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "DuplicateHandle",
            original_duplicate,
        )
        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "GetHandleInformation",
            original_get,
        )
        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "CloseHandle",
            original_close,
        )
        dual_live_windows._retry_retained_owned_handles()
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_native_custody_gate_bounds_concurrent_duplicate_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = dual_live_windows.create_phase_channels("B")
    original_duplicate = dual_live_windows._kernel32.DuplicateHandle
    original_get = dual_live_windows._kernel32.GetHandleInformation
    original_close = dual_live_windows._kernel32.CloseHandle
    first_duplicate_entered = threading.Event()
    release_first_duplicate = threading.Event()
    duplicated_handles: set[int] = set()
    duplicate_calls = 0
    errors: list[BaseException] = []
    source = _phase_private_handles(
        channels,
        ("wrapper_control_write_handle",),
    )[0]

    def duplicate_and_pause(*arguments: object) -> int:
        nonlocal duplicate_calls
        assert original_duplicate(*arguments)
        copied = ctypes.cast(
            arguments[3],
            ctypes.POINTER(ctypes.wintypes.HANDLE),
        ).contents.value
        assert copied is not None
        duplicate_calls += 1
        duplicated_handles.add(int(copied))
        if duplicate_calls == 1:
            first_duplicate_entered.set()
            assert release_first_duplicate.wait(2)
        return 1

    def reject_duplicate_validation(handle: object, flags: object) -> int:
        if int(handle) in duplicated_handles:
            ctypes.set_last_error(5)
            return 0
        return int(original_get(handle, flags))

    def retain_duplicate(handle: object) -> int:
        if int(handle) in duplicated_handles:
            ctypes.set_last_error(5)
            return 0
        return int(original_close(handle))

    def duplicate_worker(source: int) -> None:
        try:
            dual_live_windows._duplicate_owned_handle(source)
        except BaseException as exc:
            errors.append(exc)

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "DuplicateHandle",
        duplicate_and_pause,
    )
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetHandleInformation",
        reject_duplicate_validation,
    )
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "CloseHandle",
        retain_duplicate,
    )
    try:
        first = threading.Thread(target=duplicate_worker, args=(source,))
        second = threading.Thread(target=duplicate_worker, args=(source,))
        first.start()
        assert first_duplicate_entered.wait(2)
        second.start()
        second.join(0.1)
        assert second.is_alive()
        release_first_duplicate.set()
        first.join(2)
        second.join(2)
        assert not first.is_alive() and not second.is_alive()

        assert duplicate_calls == 1
        assert len(duplicated_handles) == 1
        assert dual_live_windows._retained_owned_handles == duplicated_handles
        assert len(errors) == 2
        assert all(
            isinstance(error, DualLiveWindowsError)
            and error.code == "dual_live_owned_handle_cleanup_failed"
            for error in errors
        )
    finally:
        release_first_duplicate.set()
        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "DuplicateHandle",
            original_duplicate,
        )
        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "GetHandleInformation",
            original_get,
        )
        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "CloseHandle",
            original_close,
        )
        dual_live_windows._retry_retained_owned_handles()
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_reader_allocation_and_close_failures_retain_exact_custody(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = dual_live_windows.create_phase_channels("B")
    original_buffer = ctypes.create_string_buffer
    original_read = dual_live_windows._kernel32.ReadFile
    original_close = dual_live_windows._kernel32.CloseHandle
    reader: dual_live_windows._OwnedPipeReader | None = None
    try:
        with _lease_wrapper_handles(channels) as handles:
            reader = dual_live_windows._OwnedPipeReader(
                dual_live_windows._duplicate_owned_handle(
                    handles["wrapper_app_read_handle"]
                )
            )
            baseline = _process_handle_count()
            monkeypatch.setattr(
                ctypes,
                "create_string_buffer",
                lambda *_args, **_kwargs: (_ for _ in ()).throw(MemoryError()),
            )
            with pytest.raises(MemoryError):
                reader.read(1)
            assert reader._active_thread_handle is None
            assert _process_handle_count() == baseline

            monkeypatch.setattr(ctypes, "create_string_buffer", original_buffer)

            def broken_pipe(*_arguments: object) -> int:
                ctypes.set_last_error(dual_live_windows._ERROR_BROKEN_PIPE)
                return 0

            failed_handle: int | None = None
            pipe_handle = reader._pipe_handle
            assert pipe_handle is not None

            def fail_active_close_once(handle: object) -> int:
                nonlocal failed_handle
                assert isinstance(handle, int)
                value = handle
                if value != pipe_handle and failed_handle is None:
                    failed_handle = value
                    ctypes.set_last_error(5)
                    return 0
                return int(original_close(handle))

            monkeypatch.setattr(dual_live_windows._kernel32, "ReadFile", broken_pipe)
            monkeypatch.setattr(
                dual_live_windows._kernel32,
                "CloseHandle",
                fail_active_close_once,
            )
            with pytest.raises(
                DualLiveWindowsError,
                match="dual_live_owned_reader_close_failed",
            ):
                reader.read(1)
            assert reader._active_thread is None
            assert reader._active_thread_handle == failed_handle
            assert _process_handle_count() == baseline + 1

            reader.close()
            assert reader._active_thread_handle is None
            assert reader._pipe_handle is None
            assert _process_handle_count() == baseline - 1
            monkeypatch.setattr(
                dual_live_windows._kernel32,
                "CloseHandle",
                original_close,
            )
            reader = None
    finally:
        monkeypatch.setattr(ctypes, "create_string_buffer", original_buffer)
        monkeypatch.setattr(dual_live_windows._kernel32, "ReadFile", original_read)
        monkeypatch.setattr(dual_live_windows._kernel32, "CloseHandle", original_close)
        if reader is not None:
            reader.close()
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_a_revoked_before_go_cannot_complete_inert_enable_edge() -> None:
    from app.services import dual_live_runtime

    child = dual_live_windows._create_owned_phase_process(
        "A",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    try:
        assert dual_live_runtime._read_pipe_frame(
            child.readers["app"],
            allowed_reserved_schema_ids=frozenset(
                (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
            ),
        ) is not None
        child.revoke_before_stop("operator_stop")
        child.send_control(
            dual_live_runtime.encode_child_control_frame(
                phase="A",
                command="GO",
                control_nonce=child.control_nonce,
            )
        )
        assert child.poll_exit(10) == 23
        assert dual_live_runtime._read_pipe_frame(
            child.readers["app"],
            allowed_reserved_schema_ids=frozenset(
                (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
            ),
        ) is not None
        child.stop()
        _, job_payload = child.quiesce_and_close()
        assert job_payload["active_process_count"] == 0
        assert child.authority_cleared_payload()["all_required_absent"] is True
    finally:
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_a_revocation_completes_while_owned_go_write_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_runtime

    child = dual_live_windows._create_owned_phase_process(
        "A",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    write_entered = threading.Event()
    release_write = threading.Event()
    revoke_done = threading.Event()
    go_errors: list[BaseException] = []
    revoke_errors: list[BaseException] = []
    go_thread: threading.Thread | None = None
    revoke_thread: threading.Thread | None = None
    try:
        assert dual_live_runtime._read_pipe_frame(
            child.readers["app"],
            allowed_reserved_schema_ids=frozenset(
                (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
            ),
        ) is not None
        original_write = dual_live_windows._kernel32.WriteFile

        def blocked_write(*arguments: object) -> int:
            write_entered.set()
            assert release_write.wait(5)
            return int(original_write(*arguments))

        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "WriteFile",
            blocked_write,
        )
        go_frame = dual_live_runtime.encode_child_control_frame(
            phase="A",
            command="GO",
            control_nonce=child.control_nonce,
        )

        def send_go() -> None:
            try:
                child.send_control(go_frame)
            except BaseException as exc:
                go_errors.append(exc)

        def revoke() -> None:
            try:
                child.revoke_before_stop("operator_stop")
            except BaseException as exc:
                revoke_errors.append(exc)
            finally:
                revoke_done.set()

        go_thread = threading.Thread(target=send_go, name="owned-go-race")
        go_thread.start()
        assert write_entered.wait(5)
        revoke_thread = threading.Thread(target=revoke, name="owned-revoke-race")
        revoke_thread.start()

        assert revoke_done.wait(1)
        assert revoke_errors == []
        assert (
            dual_live_windows._kernel32.WaitForSingleObject(
                child._revocation_event_handle,
                0,
            )
            == dual_live_windows._WAIT_OBJECT_0
        )

        release_write.set()
        go_thread.join(timeout=5)
        revoke_thread.join(timeout=5)
        assert not go_thread.is_alive()
        assert not revoke_thread.is_alive()
        assert go_errors == []
        assert child.poll_exit(10) == 23
    finally:
        release_write.set()
        if go_thread is not None:
            go_thread.join(timeout=5)
        if revoke_thread is not None:
            revoke_thread.join(timeout=5)
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_a_revocation_linearizes_while_thread_start_is_paused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_runtime

    child = dual_live_windows._create_owned_phase_process(
        "A",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    assert dual_live_runtime._read_pipe_frame(
        child.readers["app"],
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
        ),
    ) is not None
    write_entered = threading.Event()
    release_write = threading.Event()
    start_paused = threading.Event()
    release_start = threading.Event()
    revoke_done = threading.Event()
    send_errors: list[BaseException] = []
    revoke_errors: list[BaseException] = []
    original_write = dual_live_windows._kernel32.WriteFile
    original_start = threading.Thread.start

    def blocked_write(*arguments: object) -> int:
        write_entered.set()
        assert release_write.wait(5)
        return int(original_write(*arguments))

    def paused_start(thread: threading.Thread) -> None:
        original_start(thread)
        if thread.name == "dual-live-owned-control":
            assert write_entered.wait(5)
            start_paused.set()
            assert release_start.wait(5)

    monkeypatch.setattr(dual_live_windows._kernel32, "WriteFile", blocked_write)
    monkeypatch.setattr(threading.Thread, "start", paused_start)
    go_frame = dual_live_runtime.encode_child_control_frame(
        phase="A",
        command="GO",
        control_nonce=child.control_nonce,
    )

    def send_go() -> None:
        try:
            child.send_control(go_frame)
        except BaseException as exc:
            send_errors.append(exc)

    def revoke() -> None:
        try:
            child.revoke_before_stop("operator_stop")
        except BaseException as exc:
            revoke_errors.append(exc)
        finally:
            revoke_done.set()

    sender = threading.Thread(target=send_go, name="owned-start-linearization")
    revoker: threading.Thread | None = None
    try:
        sender.start()
        assert start_paused.wait(5)
        revoker = threading.Thread(target=revoke, name="owned-start-revocation")
        revoker.start()
        assert revoke_done.wait(1)
        assert revoke_errors == []

        release_write.set()
        release_start.set()
        sender.join(timeout=5)
        revoker.join(timeout=5)
        assert not sender.is_alive()
        assert not revoker.is_alive()
        assert send_errors == []
        assert child.poll_exit(10) == 23
    finally:
        release_write.set()
        release_start.set()
        sender.join(timeout=5)
        if revoker is not None:
            revoker.join(timeout=5)
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("phase", ("A", "B"))
def test_owned_control_pre_ready_timeout_retains_custody_until_retry(
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    from app.services import dual_live_runtime

    child = dual_live_windows._create_owned_phase_process(
        phase,
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    assert dual_live_runtime._read_pipe_frame(
        child.readers["app"],
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
        ),
    ) is not None
    source_handle = child._control_write_handle
    assert source_handle is not None
    worker_entered = threading.Event()
    release_worker = threading.Event()
    send_errors: list[BaseException] = []
    write_handles: list[int] = []
    closed_handles: list[int] = []
    original_thread_duplicate = dual_live_windows._duplicate_current_thread_handle
    original_write = dual_live_windows._kernel32.WriteFile
    original_close = dual_live_windows._kernel32.CloseHandle

    def delayed_thread_duplicate() -> int:
        worker_entered.set()
        assert release_worker.wait(5)
        return original_thread_duplicate()

    def record_write(*arguments: object) -> int:
        write_handles.append(int(arguments[0]))
        return int(original_write(*arguments))

    def record_close(handle: object) -> int:
        closed_handles.append(int(handle))
        return int(original_close(handle))

    monkeypatch.setattr(dual_live_windows, "_OWNED_IO_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(
        dual_live_windows,
        "_duplicate_current_thread_handle",
        delayed_thread_duplicate,
    )
    monkeypatch.setattr(dual_live_windows._kernel32, "WriteFile", record_write)
    monkeypatch.setattr(dual_live_windows._kernel32, "CloseHandle", record_close)
    go_frame = dual_live_runtime.encode_child_control_frame(
        phase=phase,
        command="GO",
        control_nonce=child.control_nonce,
    )

    def send_go() -> None:
        try:
            child.send_control(go_frame)
        except BaseException as exc:
            send_errors.append(exc)

    sender = threading.Thread(target=send_go, name=f"owned-pre-ready-{phase}")
    try:
        sender.start()
        assert worker_entered.wait(5)
        sender.join(timeout=2)
        assert not sender.is_alive()
        assert len(send_errors) == 1
        assert isinstance(send_errors[0], DualLiveWindowsError)
        assert send_errors[0].code == "dual_live_owned_control_write_stuck"
        writer = child._control_writer
        assert writer is not None
        pipe_handle = writer._pipe_handle
        assert pipe_handle is not None and pipe_handle != source_handle
        assert writer._thread.daemon is False
        assert write_handles == []
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_control_custody_unproven",
        ):
            child.quiesce_and_close()

        release_worker.set()
        assert writer._done.wait(5)
        thread_handle = writer._thread_handle
        assert thread_handle is not None
        child.close()

        assert write_handles == []
        assert closed_handles.count(thread_handle) == 1
        assert closed_handles.count(pipe_handle) == 1
        assert closed_handles.count(source_handle) == 1
        assert child._control_writer is None
        assert child._control_write_handle is None
        assert all(
            thread.name != "dual-live-owned-control" or not thread.is_alive()
            for thread in threading.enumerate()
        )
    finally:
        release_worker.set()
        sender.join(timeout=5)
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_control_start_then_raise_reclaims_each_capability_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_runtime

    child = dual_live_windows._create_owned_phase_process(
        "B",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    assert dual_live_runtime._read_pipe_frame(
        child.readers["app"],
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
        ),
    ) is not None
    source_handle = child._control_write_handle
    assert source_handle is not None
    duplicates: list[int] = []
    closed_handles: list[int] = []
    original_duplicate = dual_live_windows._duplicate_owned_handle_locked
    original_close = dual_live_windows._kernel32.CloseHandle
    original_start = threading.Thread.start

    def record_duplicate(source: int) -> int:
        duplicate = original_duplicate(source)
        duplicates.append(duplicate)
        return duplicate

    def record_close(handle: object) -> int:
        closed_handles.append(int(handle))
        return int(original_close(handle))

    def start_then_raise(thread: threading.Thread) -> None:
        original_start(thread)
        if thread.name == "dual-live-owned-control":
            raise RuntimeError("start-then-raise")

    monkeypatch.setattr(
        dual_live_windows,
        "_duplicate_owned_handle_locked",
        record_duplicate,
    )
    monkeypatch.setattr(dual_live_windows._kernel32, "CloseHandle", record_close)
    monkeypatch.setattr(threading.Thread, "start", start_then_raise)
    go_frame = dual_live_runtime.encode_child_control_frame(
        phase="B",
        command="GO",
        control_nonce=child.control_nonce,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_control_start_failed",
        ):
            child.send_control(go_frame)
        assert len(duplicates) == 2
        assert all(closed_handles.count(handle) == 1 for handle in duplicates)
        assert closed_handles.count(source_handle) == 1
        assert child._control_writer is None
        assert child._control_write_handle is None
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_control_consumed",
        ):
            child.send_control(go_frame)
        assert all(
            thread.name != "dual-live-owned-control" or not thread.is_alive()
            for thread in threading.enumerate()
        )
    finally:
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_control_thread_constructor_failure_closes_duplicate_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_runtime

    child = dual_live_windows._create_owned_phase_process(
        "B",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    assert dual_live_runtime._read_pipe_frame(
        child.readers["app"],
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
        ),
    ) is not None
    source_handle = child._control_write_handle
    assert source_handle is not None
    duplicates: list[int] = []
    closed_handles: list[int] = []
    original_duplicate = dual_live_windows._duplicate_owned_handle_locked
    original_close = dual_live_windows._kernel32.CloseHandle
    original_thread = threading.Thread

    def record_duplicate(source: int) -> int:
        duplicate = original_duplicate(source)
        duplicates.append(duplicate)
        return duplicate

    def record_close(handle: object) -> int:
        closed_handles.append(int(handle))
        return int(original_close(handle))

    def reject_thread(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("thread-constructor-failed")

    monkeypatch.setattr(
        dual_live_windows,
        "_duplicate_owned_handle_locked",
        record_duplicate,
    )
    monkeypatch.setattr(dual_live_windows._kernel32, "CloseHandle", record_close)
    monkeypatch.setattr(threading, "Thread", reject_thread)
    go_frame = dual_live_runtime.encode_child_control_frame(
        phase="B",
        command="GO",
        control_nonce=child.control_nonce,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_control_start_failed",
        ):
            child.send_control(go_frame)
        assert len(duplicates) == 1
        assert closed_handles.count(duplicates[0]) == 1
        assert closed_handles.count(source_handle) == 0
        assert child._control_writer is None
    finally:
        monkeypatch.setattr(threading, "Thread", original_thread)
        child.close()
    assert closed_handles.count(source_handle) == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_control_cancel_before_start_prevents_worker_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_runtime

    child = dual_live_windows._create_owned_phase_process(
        "B",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    assert dual_live_runtime._read_pipe_frame(
        child.readers["app"],
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
        ),
    ) is not None
    source_handle = child._control_write_handle
    assert source_handle is not None
    start_entered = threading.Event()
    release_start = threading.Event()
    send_errors: list[BaseException] = []
    duplicates: list[int] = []
    closed_handles: list[int] = []
    original_start = dual_live_windows._OwnedControlWriter.start
    original_duplicate = dual_live_windows._duplicate_owned_handle_locked
    original_close = dual_live_windows._kernel32.CloseHandle

    def delayed_start(writer: object) -> None:
        start_entered.set()
        assert release_start.wait(5)
        original_start(writer)

    def record_duplicate(source: int) -> int:
        duplicate = original_duplicate(source)
        duplicates.append(duplicate)
        return duplicate

    def record_close(handle: object) -> int:
        closed_handles.append(int(handle))
        return int(original_close(handle))

    monkeypatch.setattr(
        dual_live_windows._OwnedControlWriter,
        "start",
        delayed_start,
    )
    monkeypatch.setattr(
        dual_live_windows,
        "_duplicate_owned_handle_locked",
        record_duplicate,
    )
    monkeypatch.setattr(dual_live_windows._kernel32, "CloseHandle", record_close)
    go_frame = dual_live_runtime.encode_child_control_frame(
        phase="B",
        command="GO",
        control_nonce=child.control_nonce,
    )

    def send_go() -> None:
        try:
            child.send_control(go_frame)
        except BaseException as exc:
            send_errors.append(exc)

    sender = threading.Thread(target=send_go, name="owned-cancel-before-start")
    try:
        sender.start()
        assert start_entered.wait(5)
        child.close()
        assert len(duplicates) == 1
        assert closed_handles.count(duplicates[0]) == 1
        assert closed_handles.count(source_handle) == 1
        assert child._control_writer is None

        release_start.set()
        sender.join(timeout=5)
        assert not sender.is_alive()
        assert len(send_errors) == 1
        assert isinstance(send_errors[0], DualLiveWindowsError)
        assert send_errors[0].code == "dual_live_owned_control_start_failed"
        assert all(
            thread.name != "dual-live-owned-control" or not thread.is_alive()
            for thread in threading.enumerate()
        )
    finally:
        release_start.set()
        sender.join(timeout=5)
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_control_cancel_failure_retains_blocked_writer_until_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_runtime

    child = dual_live_windows._create_owned_phase_process(
        "B",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    assert dual_live_runtime._read_pipe_frame(
        child.readers["app"],
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
        ),
    ) is not None
    source_handle = child._control_write_handle
    assert source_handle is not None
    write_entered = threading.Event()
    release_write = threading.Event()
    send_errors: list[BaseException] = []
    write_handles: list[int] = []
    cancel_handles: list[int] = []
    closed_handles: list[int] = []
    original_write = dual_live_windows._kernel32.WriteFile
    original_close = dual_live_windows._kernel32.CloseHandle

    def blocked_write(*arguments: object) -> int:
        write_handles.append(int(arguments[0]))
        write_entered.set()
        assert release_write.wait(5)
        return int(original_write(*arguments))

    def fail_cancel(handle: int) -> int:
        cancel_handles.append(int(handle))
        ctypes.set_last_error(5)
        return 0

    def record_close(handle: object) -> int:
        closed_handles.append(int(handle))
        return int(original_close(handle))

    monkeypatch.setattr(dual_live_windows, "_OWNED_IO_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(dual_live_windows._kernel32, "WriteFile", blocked_write)
    monkeypatch.setattr(dual_live_windows, "_cancel_synchronous_io", fail_cancel)
    monkeypatch.setattr(dual_live_windows._kernel32, "CloseHandle", record_close)
    go_frame = dual_live_runtime.encode_child_control_frame(
        phase="B",
        command="GO",
        control_nonce=child.control_nonce,
    )

    def send_go() -> None:
        try:
            child.send_control(go_frame)
        except BaseException as exc:
            send_errors.append(exc)

    sender = threading.Thread(target=send_go, name="owned-cancel-failure")
    try:
        sender.start()
        assert write_entered.wait(5)
        sender.join(timeout=2)
        assert not sender.is_alive()
        assert len(send_errors) == 1
        assert isinstance(send_errors[0], DualLiveWindowsError)
        assert send_errors[0].code == "dual_live_owned_control_write_stuck"
        codes: list[str] = []
        pending: list[BaseException] = [send_errors[0]]
        seen: set[int] = set()
        while pending:
            error = pending.pop()
            if id(error) in seen:
                continue
            seen.add(id(error))
            if isinstance(error, DualLiveWindowsError):
                codes.append(error.code)
            if error.__context__ is not None:
                pending.append(error.__context__)
            if error.__cause__ is not None:
                pending.append(error.__cause__)
        assert "dual_live_owned_control_cancel_failed" in codes

        writer = child._control_writer
        assert writer is not None
        pipe_handle = writer._pipe_handle
        thread_handle = writer._thread_handle
        assert pipe_handle is not None
        assert thread_handle is not None
        assert write_handles == [pipe_handle]
        assert pipe_handle != source_handle
        assert cancel_handles == [thread_handle]
        assert closed_handles.count(pipe_handle) == 0
        assert closed_handles.count(thread_handle) == 0
        assert closed_handles.count(source_handle) == 0

        release_write.set()
        assert writer._done.wait(5)
        child.close()
        assert closed_handles.count(pipe_handle) == 1
        assert closed_handles.count(thread_handle) == 1
        assert closed_handles.count(source_handle) == 1
        assert child._control_writer is None
    finally:
        release_write.set()
        sender.join(timeout=5)
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_control_join_failure_retains_capabilities_for_close_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_runtime

    child = dual_live_windows._create_owned_phase_process(
        "B",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    assert dual_live_runtime._read_pipe_frame(
        child.readers["app"],
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
        ),
    ) is not None
    source_handle = child._control_write_handle
    assert source_handle is not None
    duplicates: list[int] = []
    closed_handles: list[int] = []
    join_failures = 0
    original_duplicate = dual_live_windows._duplicate_owned_handle_locked
    original_close = dual_live_windows._kernel32.CloseHandle
    original_join = threading.Thread.join

    def record_duplicate(source: int) -> int:
        duplicate = original_duplicate(source)
        duplicates.append(duplicate)
        return duplicate

    def record_close(handle: object) -> int:
        closed_handles.append(int(handle))
        return int(original_close(handle))

    def fail_first_control_join(
        thread: threading.Thread,
        timeout: float | None = None,
    ) -> None:
        nonlocal join_failures
        if thread.name == "dual-live-owned-control" and join_failures == 0:
            join_failures += 1
            raise RuntimeError("join-failed")
        original_join(thread, timeout)

    monkeypatch.setattr(
        dual_live_windows,
        "_duplicate_owned_handle_locked",
        record_duplicate,
    )
    monkeypatch.setattr(dual_live_windows._kernel32, "CloseHandle", record_close)
    monkeypatch.setattr(threading.Thread, "join", fail_first_control_join)
    go_frame = dual_live_runtime.encode_child_control_frame(
        phase="B",
        command="GO",
        control_nonce=child.control_nonce,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_control_write_stuck",
        ) as error:
            child.send_control(go_frame)
        assert isinstance(error.value.__cause__, RuntimeError)
        assert join_failures == 1
        assert len(duplicates) == 2
        writer = child._control_writer
        assert writer is not None
        pipe_handle = writer._pipe_handle
        thread_handle = writer._thread_handle
        assert pipe_handle == duplicates[0]
        assert thread_handle == duplicates[1]
        assert closed_handles.count(pipe_handle) == 0
        assert closed_handles.count(thread_handle) == 0
        assert closed_handles.count(source_handle) == 0
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_control_custody_unproven",
        ):
            child.quiesce_and_close()

        child.close()
        assert closed_handles.count(pipe_handle) == 1
        assert closed_handles.count(thread_handle) == 1
        assert closed_handles.count(source_handle) == 1
        assert child._control_writer is None
        assert all(
            thread.name != "dual-live-owned-control" or not thread.is_alive()
            for thread in threading.enumerate()
        )
    finally:
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_control_race_cannot_create_phase_b_or_seal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_runtime

    class CaptureWriter(io.BytesIO):
        def close(self) -> None:
            self.flush()

    identity = dual_live_runtime.RuntimeIdentity(
        runtime_instance_id=RUNTIME_INSTANCE_ID,
        wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
        code_revision="2" * 40,
        wrapper_image_sha256="3" * 64,
        interpreter_image_sha256="4" * 64,
        dependency_set_sha256="8" * 64,
        root_mutex_identity_sha256="5" * 64,
        campaign_mutex_identity_sha256="6" * 64,
    )
    writers = {
        stream: CaptureWriter()
        for stream in dual_live_runtime.PIPE_STREAM_CLASSES
    }
    context = dual_live_runtime._make_nonproduction_owned_controller_context(
        identity=identity,
        runtime_start_payload={
            "code_revision": identity.code_revision,
            "wrapper_image_sha256": identity.wrapper_image_sha256,
            "interpreter_image_sha256": identity.interpreter_image_sha256,
            "dependency_set_sha256": identity.dependency_set_sha256,
            "phase_timeout_contract": {
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
            },
            "mutex_identity_sha256": "7" * 64,
        },
        app_writer=writers["app"],
        http_writer=writers["http"],
        stdout_writer=writers["stdout"],
        stderr_writer=writers["stderr"],
        timeout_seconds=5,
    )
    phases: list[str] = []
    run_errors: list[BaseException] = []
    write_entered = threading.Event()
    release_write = threading.Event()
    original_create = dual_live_windows._create_owned_phase_process
    original_write = dual_live_windows._kernel32.WriteFile

    def record_create(
        phase: str,
        runtime_instance_id: str,
        wrapper_nonce_sha256: str,
    ) -> dual_live_windows.OwnedPhaseProcess:
        phases.append(phase)
        process = original_create(
            phase,
            runtime_instance_id,
            wrapper_nonce_sha256,
        )
        monkeypatch.setattr(dual_live_windows, "_OWNED_IO_TIMEOUT_SECONDS", 0.05)
        return process

    def blocked_write(*arguments: object) -> int:
        write_entered.set()
        assert release_write.wait(5)
        return int(original_write(*arguments))

    monkeypatch.setattr(
        dual_live_windows,
        "_create_owned_phase_process",
        record_create,
    )
    monkeypatch.setattr(dual_live_windows._kernel32, "WriteFile", blocked_write)

    def run_controller() -> None:
        try:
            dual_live_runtime._run_owned_two_phase_controller(context)
        except BaseException as exc:
            run_errors.append(exc)

    try:
        run_controller()
        assert write_entered.is_set()
        assert len(run_errors) == 1
        assert phases == ["A"]
        assert context.sealed is False

        release_write.set()
        processes = tuple(context._owned_processes)
        assert len(processes) == 1
        process = processes[0][1]
        assert isinstance(process, dual_live_windows.OwnedPhaseProcess)
        writer = process._control_writer
        assert writer is not None
        assert writer._done.wait(5)
        assert context._close_all_processes() is None
        assert context.sealed is False
        assert context._owned_processes == []
        assert all(
            thread.name != "dual-live-owned-control" or not thread.is_alive()
            for thread in threading.enumerate()
        )
    finally:
        release_write.set()
        context._close_all_processes()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize(
    ("carried_boot_sha256", "inner_failure"),
    (
        (None, "dual_live_child_proof_incomplete"),
        ("0" * 64, "dual_live_child_proof_binding_invalid"),
    ),
    ids=("missing", "tampered"),
)
def test_consumed_boot_carry_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    carried_boot_sha256: str | None,
    inner_failure: str,
) -> None:
    from app.services import dual_live_runtime

    identity = dual_live_runtime.RuntimeIdentity(
        runtime_instance_id=RUNTIME_INSTANCE_ID,
        wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
        code_revision="2" * 40,
        wrapper_image_sha256="3" * 64,
        interpreter_image_sha256="4" * 64,
        dependency_set_sha256="8" * 64,
        root_mutex_identity_sha256="5" * 64,
        campaign_mutex_identity_sha256="6" * 64,
    )
    context = dual_live_runtime._make_nonproduction_owned_controller_context(
        identity=identity,
        runtime_start_payload={
            "code_revision": identity.code_revision,
            "wrapper_image_sha256": identity.wrapper_image_sha256,
            "interpreter_image_sha256": identity.interpreter_image_sha256,
            "dependency_set_sha256": identity.dependency_set_sha256,
            "phase_timeout_contract": {
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
            },
            "mutex_identity_sha256": "7" * 64,
        },
        app_writer=io.BytesIO(),
        http_writer=io.BytesIO(),
        stdout_writer=io.BytesIO(),
        stderr_writer=io.BytesIO(),
        timeout_seconds=10,
    )
    original_create = dual_live_windows._create_owned_phase_process

    def create_with_invalid_carry(
        phase: str,
        runtime_instance_id: str,
        wrapper_nonce_sha256: str,
    ) -> dual_live_windows.OwnedPhaseProcess:
        process = original_create(
            phase,
            runtime_instance_id,
            wrapper_nonce_sha256,
        )
        process.boot_frame_sha256 = carried_boot_sha256  # type: ignore[assignment]
        return process

    monkeypatch.setattr(
        dual_live_windows,
        "_create_owned_phase_process",
        create_with_invalid_carry,
    )

    with pytest.raises(
        dual_live_runtime.DualLiveRuntimeError,
        match="dual_live_phase_proof_failed",
    ) as error:
        dual_live_runtime._run_owned_two_phase_controller(context)

    assert dual_live_runtime._exception_chain_has_runtime_code(
        error.value,
        inner_failure,
    )
    assert context.sealed is False
    assert context._owned_processes == []


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_stop_terminates_job_even_when_revocation_publish_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_runtime

    child = dual_live_windows._create_owned_phase_process(
        "A",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    assert dual_live_runtime._read_pipe_frame(
        child.readers["app"],
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
        ),
    ) is not None
    monkeypatch.setattr(dual_live_windows._kernel32, "SetEvent", lambda _: 0)
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_revocation_failed",
        ):
            child.stop()
        assert isinstance(child.poll_exit(5), int)
    finally:
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_reader_cancel_failure_still_joins_and_closes_pipe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_runtime

    child = dual_live_windows._create_owned_phase_process(
        "B",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    reader = child.readers["app"]
    assert dual_live_runtime._read_pipe_frame(
        reader,
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
        ),
    ) is not None
    errors: list[BaseException] = []

    def block() -> None:
        try:
            reader.read(4)
        except BaseException as exc:
            errors.append(exc)

    blocked = threading.Thread(target=block, name="owned-reader-block")
    blocked.start()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and reader._active_thread_handle is None:
        time.sleep(0.01)
    assert reader._active_thread_handle is not None
    original_cancel = dual_live_windows._cancel_synchronous_io
    assert original_cancel is not None

    def cancel_but_report_failure(handle: int) -> int:
        assert original_cancel(handle)
        ctypes.set_last_error(5)
        return 0

    monkeypatch.setattr(
        dual_live_windows,
        "_cancel_synchronous_io",
        cancel_but_report_failure,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_reader_cancel_failed",
        ):
            reader.close()
        blocked.join(timeout=5)
        assert not blocked.is_alive()
        assert reader._pipe_handle is None
        assert errors == []
    finally:
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_reader_close_retries_after_prior_stuck_cancellation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ControlledThread:
        def __init__(self) -> None:
            self.joins = 0

        def join(self, _timeout: float) -> None:
            self.joins += 1

        def is_alive(self) -> bool:
            return self.joins == 1

    reader = dual_live_windows._OwnedPipeReader(101)
    controlled = ControlledThread()
    reader._active_thread = controlled  # type: ignore[assignment]
    reader._active_thread_handle = 202
    closed: list[int] = []
    monkeypatch.setattr(dual_live_windows, "_cancel_synchronous_io", lambda _: 1)
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "CloseHandle",
        lambda handle: closed.append(int(handle)) or 1,
    )

    with pytest.raises(
        DualLiveWindowsError,
        match="dual_live_owned_reader_cancel_stuck",
    ):
        reader.close()
    assert reader._pipe_handle == 101

    reader.close()
    assert reader._pipe_handle is None
    assert closed == [101]


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_factory_refuses_missing_native_io_primitive_before_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_calls: list[str] = []
    monkeypatch.setattr(dual_live_windows._kernel32, "SetEvent", None)
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "CreatePipe",
        lambda *_args: create_calls.append("create") or 0,
    )

    with pytest.raises(DualLiveWindowsError, match="dual_live_job_unsupported"):
        dual_live_windows._create_owned_phase_process(
            "A",
            RUNTIME_INSTANCE_ID,
            WRAPPER_NONCE_SHA,
        )
    assert create_calls == []


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_factory_retains_persistent_reader_close_custody_until_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BootProbe(RuntimeError):
        pass

    warm = dual_live_windows._create_owned_phase_process(
        "B",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    warm.close()
    del warm
    gc.collect()
    baseline = _process_handle_count()
    original_close = dual_live_windows._kernel32.CloseHandle
    target_handle: int | None = None

    def reject_boot(reader: dual_live_windows._OwnedPipeReader) -> None:
        nonlocal target_handle
        target_handle = reader._pipe_handle
        raise BootProbe

    def fail_target_close(handle: object) -> int:
        assert isinstance(handle, int)
        if target_handle is not None and handle == target_handle:
            ctypes.set_last_error(5)
            return 0
        return int(original_close(handle))

    monkeypatch.setattr(dual_live_windows, "_read_owned_boot", reject_boot)
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "CloseHandle",
        fail_target_close,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_cleanup_failed",
        ) as exc:
            dual_live_windows._create_owned_phase_process(
                "B",
                RUNTIME_INSTANCE_ID,
                WRAPPER_NONCE_SHA,
            )
        assert isinstance(exc.value.__context__, BootProbe)
        assert target_handle is not None
        assert len(dual_live_windows._failed_owned_custodies) == 1
        custody = dual_live_windows._failed_owned_custodies[0]
        assert custody.child is None and custody.terminated is True
        assert tuple(custody.readers) == ("app",)
        flags = ctypes.wintypes.DWORD()
        assert dual_live_windows._kernel32.GetHandleInformation(
            target_handle,
            ctypes.byref(flags),
        )

        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "CloseHandle",
            original_close,
        )
        dual_live_windows._retry_failed_owned_custodies()
        assert dual_live_windows._failed_owned_custodies == []
        assert not dual_live_windows._kernel32.GetHandleInformation(
            target_handle,
            ctypes.byref(flags),
        )
        del custody, exc
        gc.collect()
        assert _process_handle_count() == baseline
    finally:
        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "CloseHandle",
            original_close,
        )
        dual_live_windows._retry_failed_owned_custodies()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_quiescence_is_serialized_and_cached() -> None:
    from app.services import dual_live_runtime

    child = dual_live_windows._create_owned_phase_process(
        "B",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    assert dual_live_runtime._read_pipe_frame(
        child.readers["app"],
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
        ),
    ) is not None
    child.send_control(
        dual_live_runtime.encode_child_control_frame(
            phase="B",
            command="GO",
            control_nonce=child.control_nonce,
        )
    )
    assert child.poll_exit(10) == 0
    child.stop()
    barrier = threading.Barrier(3)
    results: list[tuple[Mapping[str, object], Mapping[str, object]]] = []
    errors: list[BaseException] = []

    def quiesce() -> None:
        barrier.wait()
        try:
            results.append(child.quiesce_and_close())
        except BaseException as exc:
            errors.append(exc)

    workers = [threading.Thread(target=quiesce) for _ in range(2)]
    try:
        for worker in workers:
            worker.start()
        barrier.wait(timeout=5)
        for worker in workers:
            worker.join(timeout=10)
        assert all(not worker.is_alive() for worker in workers)
        assert errors == []
        assert len(results) == 2
        assert results[0] == results[1]
    finally:
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_lifecycle_releases_all_parent_handles_across_repeated_phases() -> None:
    from app.services import dual_live_runtime

    class HandleEntry(ctypes.Structure):
        _fields_ = (
            ("object", ctypes.c_void_p),
            ("process_id", ctypes.c_size_t),
            ("handle", ctypes.c_size_t),
            ("access", ctypes.c_ulong),
            ("trace", ctypes.c_ushort),
            ("type_index", ctypes.c_ushort),
            ("attributes", ctypes.c_ulong),
            ("reserved", ctypes.c_ulong),
        )

    ntdll = ctypes.WinDLL("ntdll", use_last_error=False)
    query_system = ntdll.NtQuerySystemInformation
    query_system.argtypes = (
        ctypes.c_ulong,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
    )
    query_system.restype = ctypes.c_long

    def current_handles() -> frozenset[int]:
        size = 1 << 20
        while True:
            buffer = ctypes.create_string_buffer(size)
            needed = ctypes.c_ulong()
            status = int(query_system(64, buffer, size, ctypes.byref(needed)))
            if status == ctypes.c_long(0xC0000004).value:
                size = max(size * 2, int(needed.value))
                continue
            assert status == 0
            count = ctypes.c_size_t.from_buffer(buffer, 0).value
            offset = 2 * ctypes.sizeof(ctypes.c_size_t)
            entries = (HandleEntry * count).from_buffer(buffer, offset)
            return frozenset(
                int(entry.handle)
                for entry in entries
                if int(entry.process_id) == os.getpid()
            )

    def wait_for_handle_ceiling(maximum: int) -> frozenset[int]:
        deadline = time.monotonic() + 1
        observed = current_handles()
        while len(observed) > maximum and time.monotonic() < deadline:
            gc.collect()
            time.sleep(0.01)
            observed = current_handles()
        return observed

    # Initialize three independently proven process-global Windows facilities
    # before measuring owned custody: anonymous pipes, ordinary process launch,
    # and IP Helper socket-table enumeration. Their first calls retain opaque
    # process-global File/Key/ETW handles that no called API returns to us.
    warm_channels = dual_live_windows.create_phase_channels("B")
    warm_channels.close()
    assert warm_channels.closed
    del warm_channels
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", "pass"],
        check=False,
        env=_job_environment(),
    )
    assert completed.returncode == 0
    assert dual_live_windows._socket_sample(frozenset()) == ()
    del completed
    gc.collect()
    handle_ceiling = len(current_handles())

    for phase in ("A", "B", "A", "B"):
        before_handles = current_handles()
        before_count = len(before_handles)
        assert before_count <= handle_ceiling
        child = dual_live_windows._create_owned_phase_process(
            phase,
            RUNTIME_INSTANCE_ID,
            WRAPPER_NONCE_SHA,
        )
        try:
            assert dual_live_runtime._read_pipe_frame(
                child.readers["app"],
                allowed_reserved_schema_ids=frozenset(
                    (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
                ),
            ) is not None
            child.send_control(
                dual_live_runtime.encode_child_control_frame(
                    phase=phase,
                    command="GO",
                    control_nonce=child.control_nonce,
                )
            )
            assert child.poll_exit(10) == 0
            assert dual_live_runtime._read_pipe_frame(
                child.readers["app"],
                allowed_reserved_schema_ids=frozenset(
                    (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
                ),
            ) is not None
            for stream in ("app", "http", "stdout", "stderr"):
                while (
                    dual_live_runtime._read_pipe_frame(
                        child.readers[stream],
                        allowed_reserved_schema_ids=(
                            frozenset(
                                (dual_live_runtime.CHILD_PROOF_SCHEMA_ID,)
                            )
                            if stream == "stdout"
                            else frozenset()
                        ),
                    )
                    is not None
                ):
                    pass
            owned_handles = {
                handle
                for handle in (
                    child._control_write_handle,
                    child._counter_ack_event_handle,
                    child._revocation_event_handle,
                    child._send_idle_event_handle,
                    *(reader._pipe_handle for reader in child.readers.values()),
                )
                if handle is not None
            }
            job_child = child._child
            assert job_child is not None
            owned_handles.update(
                handle
                for handle in (job_child._job_handle, job_child._process_handle)
                if handle is not None
            )
            owned_handles.update(
                retained[0] for retained in job_child._retained_processes.values()
            )
            child.stop()
            child.quiesce_and_close()
            if phase == "A":
                assert (
                    child.authority_cleared_payload()["all_required_absent"]
                    is True
                )
        finally:
            child.close()

        assert child._child is None
        assert child._control_write_handle is None
        assert child._counter_ack_event_handle is None
        assert child._revocation_event_handle is None
        assert child._send_idle_event_handle is None
        assert all(
            reader._pipe_handle is None for reader in child.readers.values()
        )
        flags = ctypes.wintypes.DWORD()
        assert all(
            not dual_live_windows._kernel32.GetHandleInformation(
                handle,
                ctypes.byref(flags),
            )
            for handle in owned_handles
        )

        del job_child, child
        gc.collect()
        observed = wait_for_handle_ceiling(before_count)
        assert len(observed) <= before_count, {
            "phase": phase,
            "before_count": before_count,
            "after_count": len(observed),
            "new_handle_values": sorted(observed - before_handles),
        }
        handle_ceiling = min(handle_ceiling, len(observed))


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_phase_a_ack_handle_close_failure_is_retryable_without_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warmup = dual_live_windows._create_owned_phase_process(
        "A",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    warmup.close()
    del warmup
    gc.collect()
    baseline = _process_handle_count()

    child = dual_live_windows._create_owned_phase_process(
        "A",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    ack_handle = child._counter_ack_event_handle
    assert ack_handle is not None
    original_close = dual_live_windows._kernel32.CloseHandle
    ack_close_calls = 0

    def fail_ack_close_once(handle: object) -> int:
        nonlocal ack_close_calls
        if int(handle) == ack_handle:
            ack_close_calls += 1
            if ack_close_calls == 1:
                ctypes.set_last_error(5)
                return 0
        return int(original_close(handle))

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "CloseHandle",
        fail_ack_close_once,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_cleanup_failed",
        ):
            child.close()
        assert ack_close_calls == 1
        assert child._counter_ack_event_handle == ack_handle
        flags = ctypes.wintypes.DWORD()
        assert dual_live_windows._kernel32.GetHandleInformation(
            ack_handle,
            ctypes.byref(flags),
        )

        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "CloseHandle",
            original_close,
        )
        child.close()
        assert child._counter_ack_event_handle is None
        assert not dual_live_windows._kernel32.GetHandleInformation(
            ack_handle,
            ctypes.byref(flags),
        )
    finally:
        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "CloseHandle",
            original_close,
        )
        child.close()

    del child
    gc.collect()
    assert _process_handle_count() <= baseline


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_proof_locks_are_root_then_campaign_and_busy_refuses(tmp_path: Path) -> None:
    with acquire_proof_locks(
        evidence_root=tmp_path,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        campaign_definition_sha256=DEFINITION_SHA,
    ):
        with pytest.raises(DualLiveWindowsError, match="dual_live_lock_busy"):
            acquire_proof_locks(
                evidence_root=tmp_path,
                campaign_id=CAMPAIGN_ID,
                campaign_fingerprint=CAMPAIGN_FINGERPRINT,
                campaign_definition_sha256=DEFINITION_SHA,
            )


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_active_proof_lock_validator_binds_canonical_authority_and_thread(
    tmp_path: Path,
) -> None:
    locks = acquire_proof_locks(
        evidence_root=tmp_path,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        campaign_definition_sha256=DEFINITION_SHA,
    )
    try:
        assert (
            dual_live_windows._require_active_proof_locks(
                locks,
                evidence_root=tmp_path,
                campaign_id=CAMPAIGN_ID,
                campaign_fingerprint=CAMPAIGN_FINGERPRINT,
                campaign_definition_sha256=DEFINITION_SHA,
                root_mutex_identity_sha256=locks.root_identity_sha256,
                campaign_mutex_identity_sha256=locks.campaign_identity_sha256,
            )
            is locks
        )

        failures: list[BaseException] = []

        def validate_from_wrong_thread() -> None:
            try:
                dual_live_windows._require_active_proof_locks(
                    locks,
                    evidence_root=tmp_path,
                    campaign_id=CAMPAIGN_ID,
                    campaign_fingerprint=CAMPAIGN_FINGERPRINT,
                    campaign_definition_sha256=DEFINITION_SHA,
                    root_mutex_identity_sha256=locks.root_identity_sha256,
                    campaign_mutex_identity_sha256=locks.campaign_identity_sha256,
                )
            except BaseException as exc:
                failures.append(exc)

        worker = threading.Thread(target=validate_from_wrong_thread)
        worker.start()
        worker.join(2)
        assert not worker.is_alive()
        assert len(failures) == 1
        assert isinstance(failures[0], DualLiveWindowsError)
        assert failures[0].code == "dual_live_proof_locks_inactive"

        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_proof_locks_identity_mismatch",
        ):
            dual_live_windows._require_active_proof_locks(
                locks,
                evidence_root=tmp_path,
                campaign_id=CAMPAIGN_ID,
                campaign_fingerprint=CAMPAIGN_FINGERPRINT,
                campaign_definition_sha256=DEFINITION_SHA,
                root_mutex_identity_sha256="0" * 64,
                campaign_mutex_identity_sha256=locks.campaign_identity_sha256,
            )

        assert dual_live_windows._kernel32 is not None
        replacement_mutex = dual_live_windows._kernel32.CreateMutexW(
            None,
            False,
            None,
        )
        assert replacement_mutex
        assert (
            dual_live_windows._kernel32.WaitForSingleObject(
                replacement_mutex,
                0,
            )
            == dual_live_windows._WAIT_OBJECT_0
        )
        original_campaign_mutex = locks._campaign_mutex
        locks._campaign_mutex = int(replacement_mutex)
        try:
            with pytest.raises(
                DualLiveWindowsError,
                match="dual_live_proof_locks_inactive",
            ):
                dual_live_windows._require_active_proof_locks(
                    locks,
                    evidence_root=tmp_path,
                    campaign_id=CAMPAIGN_ID,
                    campaign_fingerprint=CAMPAIGN_FINGERPRINT,
                    campaign_definition_sha256=DEFINITION_SHA,
                    root_mutex_identity_sha256=(
                        locks.root_identity_sha256
                    ),
                    campaign_mutex_identity_sha256=(
                        locks.campaign_identity_sha256
                    ),
                )
        finally:
            locks._campaign_mutex = original_campaign_mutex
            assert dual_live_windows._kernel32.ReleaseMutex(
                replacement_mutex
            )
            assert dual_live_windows._kernel32.CloseHandle(
                replacement_mutex
            )

        other_root = tmp_path / "other"
        other_root.mkdir()
        replacement_root, _ = dual_live_windows._open_evidence_root(
            other_root
        )
        original_root_handle = locks._root_directory
        locks._root_directory = replacement_root
        try:
            with pytest.raises(
                DualLiveWindowsError,
                match="dual_live_proof_locks_identity_mismatch",
            ):
                dual_live_windows._require_active_proof_locks(
                    locks,
                    evidence_root=tmp_path,
                    campaign_id=CAMPAIGN_ID,
                    campaign_fingerprint=CAMPAIGN_FINGERPRINT,
                    campaign_definition_sha256=DEFINITION_SHA,
                    root_mutex_identity_sha256=(
                        locks.root_identity_sha256
                    ),
                    campaign_mutex_identity_sha256=(
                        locks.campaign_identity_sha256
                    ),
                )
        finally:
            locks._root_directory = original_root_handle
            dual_live_windows._close_handle(replacement_root)

        assert dual_live_windows._kernel32.ReleaseMutex(
            locks._campaign_mutex
        )
        assert dual_live_windows._kernel32.ReleaseMutex(locks._root_mutex)
        try:
            with pytest.raises(
                DualLiveWindowsError,
                match="dual_live_proof_locks_inactive",
            ):
                dual_live_windows._require_active_proof_locks(
                    locks,
                    evidence_root=tmp_path,
                    campaign_id=CAMPAIGN_ID,
                    campaign_fingerprint=CAMPAIGN_FINGERPRINT,
                    campaign_definition_sha256=DEFINITION_SHA,
                    root_mutex_identity_sha256=(
                        locks.root_identity_sha256
                    ),
                    campaign_mutex_identity_sha256=(
                        locks.campaign_identity_sha256
                    ),
                )
        finally:
            assert (
                dual_live_windows._kernel32.WaitForSingleObject(
                    locks._root_mutex,
                    0,
                )
                == dual_live_windows._WAIT_OBJECT_0
            )
            assert (
                dual_live_windows._kernel32.WaitForSingleObject(
                    locks._campaign_mutex,
                    0,
                )
                == dual_live_windows._WAIT_OBJECT_0
            )
    finally:
        locks.close()

    with pytest.raises(
        DualLiveWindowsError,
        match="dual_live_proof_locks_inactive",
    ):
        dual_live_windows._require_active_proof_locks(
            locks,
            evidence_root=tmp_path,
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=CAMPAIGN_FINGERPRINT,
            campaign_definition_sha256=DEFINITION_SHA,
            root_mutex_identity_sha256=locks.root_identity_sha256,
            campaign_mutex_identity_sha256=locks.campaign_identity_sha256,
        )

def test_dual_live_windows_import_is_transitive_stdlib_only() -> None:
    probe = """
import json
import sys
from app.services import dual_live_windows
print(json.dumps({
    "config": "app.core.config" in sys.modules,
    "connector": any(name.startswith("app.services.connector_") for name in sys.modules),
    "runtime": "app.services.dual_live_runtime" in sys.modules,
    "sqlalchemy": any(name == "sqlalchemy" or name.startswith("sqlalchemy.") for name in sys.modules),
}))
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(BACKEND)
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "config": False,
        "connector": False,
        "runtime": False,
        "sqlalchemy": False,
    }
    assert completed.stderr == ""


@pytest.mark.parametrize(
    "preimage",
    (
        {
            "file_id": "00ff",
            "final_path": "c:/proof/\u2603",
            "security_descriptor_sha256": "a" * 64,
            "volume_serial_number": 17,
        },
        {
            "campaign_definition_sha256": "b" * 64,
            "campaign_fingerprint": "a" * 64,
            "campaign_id": CAMPAIGN_ID,
        },
        {
            "file_attributes": 32,
            "file_id": "00ff",
            "final_path": "c:/python.exe",
            "volume_serial_number": 17,
        },
        {"limit_flags": 8192},
        {"creation_filetime": 1337, "pid": 42},
        {
            "executable_sha256": "c" * 64,
            "pid": 42,
            "process_creation_identity_sha256": "d" * 64,
            "runtime_instance_id": RUNTIME_INSTANCE_ID,
            "wrapper_nonce_sha256": WRAPPER_NONCE_SHA,
        },
        {
            "executable_sha256": "c" * 64,
            "pid": 42,
            "process_creation_identity_sha256": "d" * 64,
        },
        ["a" * 64, "b" * 64],
        [],
    ),
)
def test_dual_live_windows_canonical_hash_preimages_match_framework(
    preimage: object,
) -> None:
    assert dual_live_windows._canonical_json_bytes(
        preimage
    ) == framework_canonical_json_bytes(preimage)


def test_dual_live_windows_local_canonical_json_is_narrow_and_tcp_states_match(
) -> None:
    with pytest.raises(ValueError, match="string object keys"):
        dual_live_windows._canonical_json_bytes({1: "value"})
    with pytest.raises(TypeError, match="cannot encode tuple"):
        dual_live_windows._canonical_json_bytes(("not", "a", "preimage"))
    with pytest.raises(ValueError, match="non-finite"):
        dual_live_windows._canonical_json_bytes({"value": float("inf")})
    assert dual_live_windows.WINDOWS_MIB_TCP_STATES == WINDOWS_MIB_TCP_STATES


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_staged_proof_lock_resolves_once_after_root_owned_and_matches_legacy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    original_wait = dual_live_windows._wait_mutex

    def recording_wait(handle: int, wait_ms: int) -> bool:
        result = original_wait(handle, wait_ms)
        events.append("root_wait" if not events else "campaign_wait")
        return result

    def resolve() -> str:
        events.append("resolve")
        assert len(dual_live_windows._held_roots) == 1
        assert not dual_live_windows._held_campaigns
        return DEFINITION_SHA

    monkeypatch.setattr(dual_live_windows, "_wait_mutex", recording_wait)
    with acquire_proof_locks_staged(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        resolve,
    ) as staged:
        staged_campaign_identity = staged.campaign_identity_sha256
    assert events == ["root_wait", "resolve", "campaign_wait"]

    monkeypatch.setattr(dual_live_windows, "_wait_mutex", original_wait)
    with acquire_proof_locks(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    ) as legacy:
        assert legacy.campaign_identity_sha256 == staged_campaign_identity


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("mode", ("invalid", "raise"))
def test_staged_proof_lock_resolver_failure_cleans_root_without_campaign(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    created_mutex_names: list[str] = []
    original_create_mutex = dual_live_windows._kernel32.CreateMutexW

    def recording_create_mutex(*args: object) -> int:
        created_mutex_names.append(str(args[2]))
        return int(original_create_mutex(*args))

    def resolve() -> str:
        if mode == "raise":
            raise RuntimeError("resolver failed")
        return "not-a-digest"

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "CreateMutexW",
        recording_create_mutex,
    )
    expected = RuntimeError if mode == "raise" else DualLiveWindowsError
    with pytest.raises(expected):
        acquire_proof_locks_staged(
            tmp_path,
            CAMPAIGN_ID,
            CAMPAIGN_FINGERPRINT,
            resolve,
        )

    assert len(created_mutex_names) == 1
    assert "\\root-" in created_mutex_names[0]
    assert not dual_live_windows._held_roots
    assert not dual_live_windows._held_campaigns
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "CreateMutexW",
        original_create_mutex,
    )
    with acquire_proof_locks(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    ):
        pass


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize(
    ("root_outcome", "expected_code"),
    (
        ("busy", "dual_live_lock_busy"),
        ("abandoned", "dual_live_lock_abandoned"),
        ("access", "dual_live_lock_access_refused"),
    ),
)
def test_staged_proof_lock_root_refusal_never_calls_resolver_and_cleans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    root_outcome: str,
    expected_code: str,
) -> None:
    resolver_calls = 0
    original_wait = dual_live_windows._wait_mutex

    def refuse_root(handle: int, wait_ms: int) -> bool:
        if root_outcome == "busy":
            raise DualLiveWindowsError("dual_live_lock_busy")
        if root_outcome == "access":
            raise DualLiveWindowsError("dual_live_lock_access_refused")
        assert original_wait(handle, wait_ms) is False
        return True

    def resolve() -> str:
        nonlocal resolver_calls
        resolver_calls += 1
        return DEFINITION_SHA

    monkeypatch.setattr(dual_live_windows, "_wait_mutex", refuse_root)
    with pytest.raises(DualLiveWindowsError, match=expected_code):
        acquire_proof_locks_staged(
            tmp_path,
            CAMPAIGN_ID,
            CAMPAIGN_FINGERPRINT,
            resolve,
        )

    assert resolver_calls == 0
    assert not dual_live_windows._held_roots
    assert not dual_live_windows._held_campaigns


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_staged_proof_lock_root_acl_refusal_never_calls_resolver_and_cleans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver_calls = 0
    original_verify = dual_live_windows._verify_private_handle

    def refuse_root_acl(handle: int, user_sid: str, expected_mask: int) -> None:
        if expected_mask == dual_live_windows._MUTEX_ALL_ACCESS:
            raise DualLiveWindowsError("dual_live_lock_acl_mismatch")
        original_verify(handle, user_sid, expected_mask)

    def resolve() -> str:
        nonlocal resolver_calls
        resolver_calls += 1
        return DEFINITION_SHA

    monkeypatch.setattr(
        dual_live_windows,
        "_verify_private_handle",
        refuse_root_acl,
    )
    with pytest.raises(DualLiveWindowsError, match="dual_live_lock_acl_mismatch"):
        acquire_proof_locks_staged(
            tmp_path,
            CAMPAIGN_ID,
            CAMPAIGN_FINGERPRINT,
            resolve,
        )

    assert resolver_calls == 0
    assert not dual_live_windows._held_roots
    assert not dual_live_windows._held_campaigns


_LOCK_PROBE = """
import os
import sys
import time
from pathlib import Path

from app.services.dual_live_windows import DualLiveWindowsError, acquire_proof_locks

try:
    locks = acquire_proof_locks(
        evidence_root=Path(sys.argv[1]),
        campaign_id=sys.argv[2],
        campaign_fingerprint="a" * 64,
        campaign_definition_sha256="b" * 64,
        wait_ms=int(sys.argv[3]),
    )
except DualLiveWindowsError as exc:
    print(exc.code, flush=True)
else:
    print("acquired", flush=True)
    if sys.argv[4] == "abandon":
        time.sleep(1.0)
        os._exit(0)
    locks.close()
"""


def _lock_probe(
    evidence_root: Path,
    campaign_id: str,
    *,
    wait_ms: int = 0,
    mode: str = "close",
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(BACKEND)
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            _LOCK_PROBE,
            str(evidence_root),
            campaign_id,
            str(wait_ms),
            mode,
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("campaign_id", [CAMPAIGN_ID, OTHER_CAMPAIGN_ID])
def test_proof_lock_cross_process_root_contention_refuses(
    tmp_path: Path, campaign_id: str
) -> None:
    with acquire_proof_locks(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    ):
        completed = _lock_probe(tmp_path, campaign_id)

    assert completed.returncode == 0
    assert completed.stdout == "dual_live_lock_busy\n"
    assert completed.stderr == ""


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_proof_lock_same_campaign_contends_across_evidence_roots(
    tmp_path: Path,
) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    with acquire_proof_locks(
        first_root,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    ) as first:
        completed = _lock_probe(second_root, CAMPAIGN_ID)

    assert completed.returncode == 0
    assert completed.stdout == "dual_live_lock_busy\n"
    assert completed.stderr == ""
    with acquire_proof_locks(
        second_root,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    ) as second:
        assert first.root_identity_sha256 != second.root_identity_sha256
        assert first.campaign_identity_sha256 == second.campaign_identity_sha256


def test_proof_locks_public_constructor_is_exact_and_inert_close_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert tuple(inspect.signature(ProofLocks).parameters) == (
        "root_identity_sha256",
        "campaign_identity_sha256",
    )
    locks = ProofLocks("a" * 64, "b" * 64)
    monkeypatch.setattr(dual_live_windows, "_kernel32", None)
    locks.close()
    locks.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_proof_lock_abandoned_mutex_refuses(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(BACKEND)
    holder = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-c",
            _LOCK_PROBE,
            str(tmp_path),
            CAMPAIGN_ID,
            "0",
            "abandon",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline() == "acquired\n"
        completed = _lock_probe(tmp_path, CAMPAIGN_ID, wait_ms=5_000)
        assert holder.wait(timeout=5) == 0
    finally:
        if holder.poll() is None:
            holder.kill()
            holder.wait(timeout=5)

    assert completed.returncode == 0
    assert completed.stdout == "dual_live_lock_abandoned\n"
    assert completed.stderr == ""


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_proof_lock_abandoned_release_failure_retains_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_wait = dual_live_windows._wait_mutex
    original_release = dual_live_windows._kernel32.ReleaseMutex
    original_create_mutex = dual_live_windows._kernel32.CreateMutexW
    created_mutexes: list[int] = []

    def recording_create_mutex(*args: object) -> int:
        handle = int(original_create_mutex(*args))
        created_mutexes.append(handle)
        return handle

    def acquire_then_report_abandoned(handle: int, wait_ms: int) -> bool:
        assert original_wait(handle, wait_ms) is False
        return True

    def fail_release(handle: object) -> int:
        return 0

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "CreateMutexW",
        recording_create_mutex,
    )
    monkeypatch.setattr(
        dual_live_windows,
        "_wait_mutex",
        acquire_then_report_abandoned,
    )
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "ReleaseMutex",
        fail_release,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_lock_cleanup_failed",
        ):
            acquire_proof_locks(
                tmp_path,
                CAMPAIGN_ID,
                CAMPAIGN_FINGERPRINT,
                DEFINITION_SHA,
            )
        assert len(created_mutexes) == 1
        assert len(dual_live_windows._held_roots) == 1
        assert len(dual_live_windows._held_campaigns) == 1
        with pytest.raises(DualLiveWindowsError, match="dual_live_lock_busy"):
            acquire_proof_locks(
                tmp_path,
                CAMPAIGN_ID,
                CAMPAIGN_FINGERPRINT,
                DEFINITION_SHA,
            )
    finally:
        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "ReleaseMutex",
            original_release,
        )
        if created_mutexes:
            assert original_release(created_mutexes[0])
            assert dual_live_windows._kernel32.CloseHandle(created_mutexes[0])
        with dual_live_windows._held_lock:
            dual_live_windows._held_roots.clear()
            dual_live_windows._held_campaigns.clear()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_proof_lock_handles_are_private_and_release_campaign_then_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    locks = acquire_proof_locks(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    )
    flags = ctypes.c_ulong()
    for handle in (
        locks._namespace_handle,
        locks._root_mutex,
        locks._campaign_mutex,
        locks._root_directory,
    ):
        assert dual_live_windows._kernel32.GetHandleInformation(
            handle, ctypes.byref(flags)
        )
        assert flags.value & 1 == 0
    _, user_sid = dual_live_windows._current_user_sid()
    assert dual_live_windows._dacl_entries(
        dual_live_windows._object_security_bytes(
            locks._root_mutex, dual_live_windows._DACL_SECURITY_INFORMATION
        )
    ) == (
        ("S-1-5-18", dual_live_windows._MUTEX_ALL_ACCESS),
        (user_sid, dual_live_windows._MUTEX_ALL_ACCESS),
    )
    assert not any(
        name in {"handle", "root_handle", "campaign_handle", "namespace_handle"}
        for name in dir(locks)
        if not name.startswith("_")
    )
    released: list[int] = []
    original_release = dual_live_windows._kernel32.ReleaseMutex

    def recording_release(handle: int) -> int:
        released.append(int(handle))
        return original_release(handle)

    monkeypatch.setattr(
        dual_live_windows._kernel32, "ReleaseMutex", recording_release
    )
    campaign_mutex = locks._campaign_mutex
    root_mutex = locks._root_mutex
    locks.close()
    locks.close()

    assert released == [campaign_mutex, root_mutex]
    with acquire_proof_locks(
        tmp_path,
        OTHER_CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    ):
        pass


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_proof_lock_wrong_thread_close_refuses_before_mutation(
    tmp_path: Path,
) -> None:
    locks = acquire_proof_locks(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    )
    before = (
        locks._root_directory,
        locks._namespace_handle,
        locks._boundary_descriptor,
        locks._security_descriptor,
        locks._root_mutex,
        locks._campaign_mutex,
    )
    outcomes: list[str] = []

    def wrong_thread_close() -> None:
        try:
            locks.close()
        except DualLiveWindowsError as exc:
            outcomes.append(exc.code)
        else:
            outcomes.append("closed")

    worker = threading.Thread(target=wrong_thread_close)
    worker.start()
    worker.join(timeout=5)
    try:
        assert not worker.is_alive()
        assert outcomes == ["dual_live_lock_wrong_thread"]
        assert locks._acquiring_thread_id == threading.get_ident()
        assert not locks._closed
        assert locks._root_owned and locks._campaign_owned
        assert before == (
            locks._root_directory,
            locks._namespace_handle,
            locks._boundary_descriptor,
            locks._security_descriptor,
            locks._root_mutex,
            locks._campaign_mutex,
        )
        assert locks.root_identity_sha256 in dual_live_windows._held_roots
        assert locks.campaign_identity_sha256 in dual_live_windows._held_campaigns
    finally:
        locks.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("failed_mutex", ("campaign", "root"))
def test_proof_lock_partial_release_failure_is_retryable(
    tmp_path: Path,
    failed_mutex: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    locks = acquire_proof_locks(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    )
    assert locks._campaign_mutex is not None and locks._root_mutex is not None
    campaign_mutex = locks._campaign_mutex
    root_mutex = locks._root_mutex
    target = (
        campaign_mutex if failed_mutex == "campaign" else root_mutex
    )
    original_release = dual_live_windows._kernel32.ReleaseMutex
    calls: list[int] = []
    failed_once = False

    def fail_once(handle: object) -> int:
        nonlocal failed_once
        value = int(handle)
        calls.append(value)
        if value == target and not failed_once:
            failed_once = True
            return 0
        return int(original_release(handle))

    monkeypatch.setattr(dual_live_windows._kernel32, "ReleaseMutex", fail_once)
    with pytest.raises(DualLiveWindowsError, match="dual_live_lock_release_failed"):
        locks.close()
    assert not locks._closed
    assert locks._root_owned
    assert locks._campaign_owned is (failed_mutex == "campaign")
    assert locks.root_identity_sha256 in dual_live_windows._held_roots
    assert locks.campaign_identity_sha256 in dual_live_windows._held_campaigns
    flags = ctypes.wintypes.DWORD()
    assert dual_live_windows._kernel32.GetHandleInformation(
        locks._root_mutex,
        ctypes.byref(flags),
    )
    assert dual_live_windows._kernel32.GetHandleInformation(
        locks._campaign_mutex,
        ctypes.byref(flags),
    )

    locks.close()
    assert locks._closed
    assert not locks._root_owned and not locks._campaign_owned
    assert locks.root_identity_sha256 not in dual_live_windows._held_roots
    assert locks.campaign_identity_sha256 not in dual_live_windows._held_campaigns
    if failed_mutex == "campaign":
        assert calls == [
            campaign_mutex,
            campaign_mutex,
            root_mutex,
        ]
    else:
        assert calls == [
            campaign_mutex,
            root_mutex,
            root_mutex,
        ]


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("failed_resource", ("root_directory", "namespace", "security"))
def test_proof_lock_cleanup_failure_retries_remaining_resource(
    tmp_path: Path,
    failed_resource: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    locks = acquire_proof_locks(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    )
    root_directory = locks._root_directory
    namespace_handle = locks._namespace_handle
    security_descriptor = locks._security_descriptor
    original_close = dual_live_windows._kernel32.CloseHandle
    original_close_namespace = dual_live_windows._kernel32.ClosePrivateNamespace
    original_local_free = dual_live_windows._kernel32.LocalFree
    failed_once = False

    def close_handle_once(handle: object) -> int:
        nonlocal failed_once
        if (
            failed_resource == "root_directory"
            and int(handle) == root_directory
            and not failed_once
        ):
            failed_once = True
            return 0
        return int(original_close(handle))

    def close_namespace_once(handle: object, flags: int) -> int:
        nonlocal failed_once
        if (
            failed_resource == "namespace"
            and int(handle) == namespace_handle
            and not failed_once
        ):
            failed_once = True
            return 0
        return int(original_close_namespace(handle, flags))

    def local_free_once(handle: object) -> object:
        nonlocal failed_once
        handle_value = ctypes.cast(handle, ctypes.c_void_p).value
        if (
            failed_resource == "security"
            and handle_value == security_descriptor
            and not failed_once
        ):
            failed_once = True
            return handle
        return original_local_free(handle)

    monkeypatch.setattr(dual_live_windows._kernel32, "CloseHandle", close_handle_once)
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "ClosePrivateNamespace",
        close_namespace_once,
    )
    monkeypatch.setattr(dual_live_windows._kernel32, "LocalFree", local_free_once)

    with pytest.raises(DualLiveWindowsError, match="dual_live_lock_cleanup_failed"):
        locks.close()
    assert failed_once
    assert not locks._closed
    assert locks._registered
    assert locks.root_identity_sha256 in dual_live_windows._held_roots
    assert locks.campaign_identity_sha256 in dual_live_windows._held_campaigns

    locks.close()
    assert locks._closed
    assert not locks._registered
    assert locks.root_identity_sha256 not in dual_live_windows._held_roots
    assert locks.campaign_identity_sha256 not in dual_live_windows._held_campaigns
    with acquire_proof_locks(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    ):
        pass


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_proof_lock_final_transfer_failure_cleans_and_allows_reacquire(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_transfer(*args: object, **kwargs: object) -> object:
        raise DualLiveWindowsError("dual_live_lock_transfer_failed")

    monkeypatch.setattr(
        dual_live_windows.ProofLocks,
        "_from_owned_handles",
        classmethod(fail_transfer),
    )
    with pytest.raises(DualLiveWindowsError, match="dual_live_lock_transfer_failed"):
        acquire_proof_locks(
            tmp_path,
            CAMPAIGN_ID,
            CAMPAIGN_FINGERPRINT,
            DEFINITION_SHA,
        )
    assert not dual_live_windows._held_roots
    assert not dual_live_windows._held_campaigns

    monkeypatch.undo()
    with acquire_proof_locks(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    ):
        pass


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_failed_lock_acquisition_release_failure_retains_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    locks = acquire_proof_locks(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    )
    resources = {
        "root_identity_sha256": locks.root_identity_sha256,
        "campaign_identity_sha256": locks.campaign_identity_sha256,
        "root_registered": True,
        "root_directory": locks._root_directory,
        "namespace_handle": locks._namespace_handle,
        "boundary_descriptor": locks._boundary_descriptor,
        "security_descriptor": locks._security_descriptor,
        "root_mutex": locks._root_mutex,
        "campaign_mutex": locks._campaign_mutex,
        "root_owned": True,
        "campaign_owned": True,
    }
    campaign_mutex = locks._campaign_mutex
    locks._root_directory = None
    locks._namespace_handle = None
    locks._boundary_descriptor = None
    locks._security_descriptor = None
    locks._root_mutex = None
    locks._campaign_mutex = None
    locks._root_owned = False
    locks._campaign_owned = False
    locks._registered = False
    locks._closed = True

    original_release = dual_live_windows._kernel32.ReleaseMutex

    def fail_campaign_release(handle: object) -> int:
        if int(handle) == campaign_mutex:
            return 0
        return int(original_release(handle))

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "ReleaseMutex",
        fail_campaign_release,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_lock_cleanup_failed",
        ):
            dual_live_windows._cleanup_failed_lock_acquisition(**resources)
        assert resources["root_identity_sha256"] in dual_live_windows._held_roots
        assert (
            resources["campaign_identity_sha256"]
            in dual_live_windows._held_campaigns
        )
        with pytest.raises(DualLiveWindowsError, match="dual_live_lock_busy"):
            acquire_proof_locks(
                tmp_path,
                CAMPAIGN_ID,
                CAMPAIGN_FINGERPRINT,
                DEFINITION_SHA,
            )
    finally:
        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "ReleaseMutex",
            original_release,
        )
        assert original_release(campaign_mutex)
        assert dual_live_windows._kernel32.CloseHandle(campaign_mutex)
        with dual_live_windows._held_lock:
            dual_live_windows._held_roots.discard(
                resources["root_identity_sha256"]
            )
            dual_live_windows._held_campaigns.discard(
                resources["campaign_identity_sha256"]
            )


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_proof_lock_acl_mismatch_refuses(tmp_path: Path) -> None:
    locks = acquire_proof_locks(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    )
    _, user_sid = dual_live_windows._current_user_sid()
    bad_descriptor = ctypes.c_void_p()
    bad_size = ctypes.c_ulong()
    try:
        assert dual_live_windows._advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            f"D:P(A;;GA;;;{user_sid})",
            dual_live_windows._SDDL_REVISION_1,
            ctypes.byref(bad_descriptor),
            ctypes.byref(bad_size),
        )
        set_security = dual_live_windows._advapi32.SetKernelObjectSecurity
        set_security.argtypes = (
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_void_p,
        )
        set_security.restype = ctypes.c_int
        assert set_security(
            locks._root_mutex,
            dual_live_windows._DACL_SECURITY_INFORMATION,
            bad_descriptor,
        )
        with pytest.raises(DualLiveWindowsError, match="dual_live_lock_acl_mismatch"):
            dual_live_windows._verify_private_handle(
                locks._root_mutex,
                user_sid,
                dual_live_windows._MUTEX_ALL_ACCESS,
            )
    finally:
        if bad_descriptor.value:
            dual_live_windows._kernel32.LocalFree(bad_descriptor)
        locks.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_proof_lock_namespace_squatting_refuses(tmp_path: Path) -> None:
    locks = acquire_proof_locks(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    )
    squatted_namespace = locks._namespace_handle
    locks._namespace_handle = 0
    locks.close()
    try:
        with pytest.raises(
            DualLiveWindowsError, match="dual_live_lock_namespace_squatted"
        ):
            acquire_proof_locks(
                tmp_path,
                CAMPAIGN_ID,
                CAMPAIGN_FINGERPRINT,
                DEFINITION_SHA,
            )
    finally:
        dual_live_windows._kernel32.ClosePrivateNamespace(squatted_namespace, 0)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_proof_lock_reparse_root_refuses(tmp_path: Path) -> None:
    real_root = tmp_path / "real"
    real_root.mkdir()
    linked_root = tmp_path / "linked"
    linked_root.symlink_to(real_root, target_is_directory=True)

    with pytest.raises(DualLiveWindowsError, match="dual_live_evidence_root_reparse"):
        acquire_proof_locks(
            linked_root,
            CAMPAIGN_ID,
            CAMPAIGN_FINGERPRINT,
            DEFINITION_SHA,
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_proof_lock_acquires_without_protected_file_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden_read(*args: object, **kwargs: object) -> None:
        raise AssertionError("protected read occurred before proof locks")

    monkeypatch.setattr(Path, "open", forbidden_read)
    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
    monkeypatch.setattr(Path, "read_text", forbidden_read)
    monkeypatch.setattr(Path, "iterdir", forbidden_read)

    with acquire_proof_locks(
        tmp_path,
        CAMPAIGN_ID,
        CAMPAIGN_FINGERPRINT,
        DEFINITION_SHA,
    ):
        pass


def _job_environment() -> dict[str, str]:
    environment: dict[str, str] = {"PYTHONUTF8": "1"}
    for name in ("SystemRoot", "WINDIR", "TEMP", "TMP"):
        value = os.environ.get(name)
        if value is not None:
            environment[name] = value
    return environment


def _run_shadow_config(tmp_path: Path, *, isolated: bool) -> dict[str, bool]:
    shadow_backend = tmp_path / ("isolated" if isolated else "normal") / "backend"
    shadow_core = shadow_backend / "app" / "core"
    shadow_core.mkdir(parents=True)
    (shadow_backend / "app" / "__init__.py").write_text("", encoding="utf-8")
    (shadow_core / "__init__.py").write_text("", encoding="utf-8")
    shutil.copyfile(BACKEND / "app" / "core" / "config.py", shadow_core / "config.py")

    grant_path = shadow_backend / "grant.json"
    (shadow_backend / ".env").write_text(
        "\n".join(
            (
                "SENATE_LDA_API_KEY=dotenv-only-fake-key",
                f"CONNECTOR_NRC_APS_GRANT_PATH={grant_path.as_posix()}",
                f"CONNECTOR_NRC_APS_GRANT_SHA256={'d' * 64}",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    probe = (
        "import json,sys; "
        "sys.path.insert(0, sys.argv[1]); "
        "from app.core.config import settings; "
        "print(json.dumps({"
        "'api_key': bool(settings.senate_lda_api_key), "
        "'grant_path': settings.connector_nrc_aps_grant_path is not None, "
        "'grant_sha': bool(settings.connector_nrc_aps_grant_sha256)"
        "}, sort_keys=True))"
    )
    command = [sys.executable]
    if isolated:
        command.append("-I")
    command.extend(("-c", probe, str(shadow_backend)))
    blocked_names = {
        "senate_lda_api_key",
        "connector_nrc_aps_grant_path",
        "connector_nrc_aps_grant_sha256",
    }
    environment = {
        name: value
        for name, value in os.environ.items()
        if name.casefold() not in blocked_names
    }
    completed = subprocess.run(
        command,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _inheritable_pipe() -> tuple[int, int]:
    security = dual_live_windows._SECURITY_ATTRIBUTES(
        ctypes.sizeof(dual_live_windows._SECURITY_ATTRIBUTES), None, True
    )
    read_handle = ctypes.c_void_p()
    write_handle = ctypes.c_void_p()
    assert dual_live_windows._kernel32.CreatePipe(
        ctypes.byref(read_handle),
        ctypes.byref(write_handle),
        ctypes.byref(security),
        0,
    )
    assert dual_live_windows._kernel32.SetHandleInformation(
        read_handle, 1, 0
    )
    return int(read_handle.value), int(write_handle.value)


def _create_test_child(code: str, *arguments: str) -> JobChild:
    read_handle, write_handle = _inheritable_pipe()
    try:
        return create_child_in_job(
            argv=(sys.executable, "-B", "-c", code, *arguments),
            environment=_job_environment(),
            inherited_handles=(write_handle,),
            runtime_instance_id=RUNTIME_INSTANCE_ID,
            wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
        )
    finally:
        dual_live_windows._kernel32.CloseHandle(read_handle)
        dual_live_windows._kernel32.CloseHandle(write_handle)


def _marker_argv(marker: Path) -> tuple[str, ...]:
    return (
        sys.executable,
        "-B",
        "-c",
        "from pathlib import Path; Path(__import__('sys').argv[1]).touch()",
        str(marker),
    )


def _create_signaling_test_child(
    code: str, *arguments: str
) -> tuple[JobChild, int]:
    read_handle, write_handle = _inheritable_pipe()
    try:
        child = create_child_in_job(
            argv=(
                sys.executable,
                "-B",
                "-c",
                code,
                str(write_handle),
                *arguments,
            ),
            environment=_job_environment(),
            inherited_handles=(write_handle,),
            runtime_instance_id=RUNTIME_INSTANCE_ID,
            wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
        )
    except BaseException:
        dual_live_windows._kernel32.CloseHandle(read_handle)
        raise
    finally:
        dual_live_windows._kernel32.CloseHandle(write_handle)
    return child, read_handle


def _read_child_signal(read_handle: int, child: JobChild) -> None:
    peek = dual_live_windows._kernel32.PeekNamedPipe
    peek.argtypes = (
        ctypes.wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.wintypes.DWORD,
        ctypes.POINTER(ctypes.wintypes.DWORD),
        ctypes.POINTER(ctypes.wintypes.DWORD),
        ctypes.POINTER(ctypes.wintypes.DWORD),
    )
    peek.restype = ctypes.wintypes.BOOL
    deadline = time.monotonic() + 5
    try:
        while True:
            available = ctypes.wintypes.DWORD()
            if not peek(
                read_handle,
                None,
                0,
                None,
                ctypes.byref(available),
                None,
            ):
                pytest.fail("child signal pipe became unreadable")
            if available.value:
                payload = ctypes.create_string_buffer(1)
                received = ctypes.wintypes.DWORD()
                assert dual_live_windows._kernel32.ReadFile(
                    read_handle,
                    payload,
                    1,
                    ctypes.byref(received),
                    None,
                )
                assert received.value == 1 and payload.raw == b"1"
                return
            assert child._process_handle is not None
            if (
                dual_live_windows._kernel32.WaitForSingleObject(
                    child._process_handle,
                    0,
                )
                == dual_live_windows._WAIT_OBJECT_0
            ):
                pytest.fail("child exited before signaling readiness")
            if time.monotonic() >= deadline:
                pytest.fail("child readiness signal timed out")
            time.sleep(0.01)
    finally:
        dual_live_windows._kernel32.CloseHandle(read_handle)


def _assert_quiescence_record(record: dict[str, object]) -> None:
    assert set(record) == {
        "active_process_count",
        "process_list_sha256",
        "tcp4_state_counts",
        "tcp6_state_counts",
        "udp4_count",
        "udp6_count",
        "process_identity_sha256",
        "stable",
    }
    assert record["active_process_count"] == 0
    assert record["stable"] is True
    assert record["udp4_count"] == 0
    assert record["udp6_count"] == 0
    for family in ("tcp4_state_counts", "tcp6_state_counts"):
        counts = record[family]
        assert isinstance(counts, dict)
        assert tuple(counts) == WINDOWS_MIB_TCP_STATES
        assert all(isinstance(value, int) and value >= 0 for value in counts.values())
        assert all(
            value == 0
            for state, value in counts.items()
            if state != "MIB_TCP_STATE_TIME_WAIT"
        )
    for name in ("process_list_sha256", "process_identity_sha256"):
        value = record[name]
        assert isinstance(value, str)
        assert len(value) == 64
        int(value, 16)
    encoded = json.dumps(record, sort_keys=True)
    assert all(
        marker not in encoded.lower()
        for marker in (
            "endpoint",
            "command_line",
            "secret",
            "credential",
            "raw_path",
            "address",
            "port",
        )
    )


def test_current_user_sid_sha256_is_os_derived_and_does_not_return_raw_sid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_sid = "S-1-5-21-111111111-222222222-333333333-1001"
    keepalive = ctypes.create_string_buffer(b"sid")
    monkeypatch.setattr(dual_live_windows, "_kernel32", object())
    monkeypatch.setattr(dual_live_windows, "_advapi32", object())
    monkeypatch.setattr(
        dual_live_windows,
        "_current_user_sid",
        lambda: (keepalive, raw_sid),
    )

    sid_sha256 = dual_live_windows.current_user_sid_sha256()

    assert sid_sha256 == hashlib.sha256(raw_sid.encode("utf-8")).hexdigest()
    assert raw_sid not in sid_sha256


def test_current_user_sid_sha256_fails_closed_without_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dual_live_windows, "_kernel32", None)
    monkeypatch.setattr(dual_live_windows, "_advapi32", None)

    with pytest.raises(DualLiveWindowsError, match="dual_live_windows_unsupported"):
        dual_live_windows.current_user_sid_sha256()


def _handle_flags(handle: int) -> int:
    flags = ctypes.wintypes.DWORD()
    assert dual_live_windows._kernel32.GetHandleInformation(
        handle,
        ctypes.byref(flags),
    )
    return int(flags.value)


def _phase_channel_constructor_args(
    channels: object,
) -> dict[str, object]:
    names = (
        "wrapper_control_write_handle",
        "wrapper_app_read_handle",
        "wrapper_http_read_handle",
        "wrapper_stdout_read_handle",
        "wrapper_stderr_read_handle",
        "wrapper_revocation_event_handle",
        "wrapper_send_idle_event_handle",
        "child_control_read_handle",
        "child_app_write_handle",
        "child_http_write_handle",
        "child_stdout_write_handle",
        "child_stderr_write_handle",
        "child_revocation_event_handle",
        "child_send_idle_event_handle",
    )
    handles = getattr(channels, "_handles")
    return {
        "phase": getattr(channels, "phase"),
        **{name: handles[name] for name in names},
    }


def _process_handle_count() -> int:
    count = ctypes.wintypes.DWORD()
    assert dual_live_windows._kernel32.GetProcessHandleCount(
        dual_live_windows._kernel32.GetCurrentProcess(),
        ctypes.byref(count),
    )
    return int(count.value)


def _phase_private_handles(
    channels: object,
    roles: tuple[str, ...],
) -> tuple[int, ...]:
    handles = getattr(channels, "_handles")
    return tuple(handles[role] for role in roles if handles[role] is not None)


def _lease_wrapper_handles(
    channels: dual_live_windows.PhaseChannels,
) -> AbstractContextManager[Mapping[str, int]]:
    return channels._lease_wrapper_handles(
        dual_live_windows._PHASE_CHANNELS_FACTORY_TOKEN
    )


def _lease_child_handles(
    channels: dual_live_windows.PhaseChannels,
) -> AbstractContextManager[Mapping[str, int]]:
    return channels._lease_child_handles(
        dual_live_windows._PHASE_CHANNELS_FACTORY_TOKEN
    )


def _assert_phase_constructor_is_factory_only(arguments: dict[str, object]) -> None:
    unexpected = None
    try:
        unexpected = dual_live_windows.PhaseChannels(**arguments)
    except DualLiveWindowsError as exc:
        assert exc.code == "dual_live_phase_channels_factory_only"
    else:
        unexpected._handles = {  # type: ignore[attr-defined]
            role: None for role in unexpected._handles  # type: ignore[attr-defined]
        }
        pytest.fail("PhaseChannels accepted public raw-handle construction")


def _assert_phase_factory_rejects(call: object) -> None:
    unexpected = None
    try:
        unexpected = call()  # type: ignore[operator]
    except DualLiveWindowsError as exc:
        assert exc.code == "dual_live_phase_channels_invalid"
    else:
        pytest.fail("phase-channel factory accepted invalid capability graph")
    finally:
        if unexpected is not None:
            unexpected.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize(("phase", "expected_child_count"), (("A", 11), ("B", 8)))
def test_phase_channels_are_read_only_owned_and_phase_exact(
    phase: str,
    expected_child_count: int,
) -> None:
    channels = dual_live_windows.create_phase_channels(phase)
    try:
        assert isinstance(channels, dual_live_windows.PhaseChannels)
        assert channels.phase == phase
        with _lease_wrapper_handles(channels) as wrapper_handles:
            with _lease_child_handles(channels) as child_handles:
                assert len(wrapper_handles) == (9 if phase == "A" else 6)
                assert len(child_handles) == expected_child_count
                all_handles = tuple(wrapper_handles.values()) + tuple(
                    child_handles.values()
                )
                assert len(set(all_handles)) == len(all_handles)
                assert all(handle > 0 for handle in all_handles)
                assert (
                    "wrapper_revocation_event_handle" in wrapper_handles
                ) is (phase == "A")
                assert ("wrapper_send_idle_event_handle" in wrapper_handles) is (
                    phase == "A"
                )
                assert (
                    "wrapper_counter_ack_event_handle" in wrapper_handles
                ) is (phase == "A")
                assert ("child_revocation_event_handle" in child_handles) is (
                    phase == "A"
                )
                assert ("child_send_idle_event_handle" in child_handles) is (
                    phase == "A"
                )
                assert ("child_counter_ack_event_handle" in child_handles) is (
                    phase == "A"
                )
        with pytest.raises(AttributeError):
            channels.phase = "B"
    finally:
        channels.close()
    assert channels.closed
    with pytest.raises(DualLiveWindowsError, match="dual_live_phase_channels_closed"):
        with _lease_wrapper_handles(channels):
            pass
    with pytest.raises(DualLiveWindowsError, match="dual_live_phase_channels_closed"):
        with _lease_child_handles(channels):
            pass


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_channels_reject_public_clone_and_valid_role_permutation() -> None:
    channels = dual_live_windows.create_phase_channels("A")
    try:
        clone = _phase_channel_constructor_args(channels)
        _assert_phase_constructor_is_factory_only(clone)

        permuted = dict(clone)
        permuted["child_app_write_handle"], permuted["child_http_write_handle"] = (
            permuted["child_http_write_handle"],
            permuted["child_app_write_handle"],
        )
        _assert_phase_constructor_is_factory_only(permuted)
    finally:
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_channels_expose_only_bounded_handle_leases() -> None:
    channels = dual_live_windows.create_phase_channels("A")
    raw_names = tuple(
        name
        for name in _phase_channel_constructor_args(channels)
        if name != "phase"
    ) + (
        "wrapper_handles",
        "child_handles",
        "wrapper_stream_pipe_handles",
        "child_stream_pipe_handles",
    )
    try:
        assert all(not hasattr(channels, name) for name in raw_names)
        assert not hasattr(channels, "lease_wrapper_handles")
        assert not hasattr(channels, "lease_child_handles")
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_channels_factory_only",
        ):
            channels._lease_wrapper_handles(object())
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_channels_factory_only",
        ):
            channels._lease_child_handles(object())
        with _lease_wrapper_handles(channels) as wrapper_handles:
            with _lease_child_handles(channels) as child_handles:
                assert tuple(wrapper_handles) == dual_live_windows._PHASE_WRAPPER_ROLES
                assert tuple(child_handles) == dual_live_windows._PHASE_CHILD_ROLES
    finally:
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("phase", ("A", "B"))
def test_phase_factory_retains_only_noninheritable_owner_capabilities(
    phase: str,
) -> None:
    channels = dual_live_windows.create_phase_channels(phase)
    try:
        owner_handles = _phase_private_handles(
            channels,
            dual_live_windows._PHASE_WRAPPER_ROLES
            + dual_live_windows._PHASE_CHILD_ROLES,
        )
        assert all(_handle_flags(handle) == 0 for handle in owner_handles)

        with _lease_child_handles(channels) as child_handles:
            leased = tuple(child_handles.values())
            assert set(leased).isdisjoint(owner_handles)
            assert all(
                _handle_flags(handle) == dual_live_windows._HANDLE_FLAG_INHERIT
                for handle in leased
            )
        flags = ctypes.wintypes.DWORD()
        assert all(
            not dual_live_windows._kernel32.GetHandleInformation(
                handle,
                ctypes.byref(flags),
            )
            for handle in leased
        )
    finally:
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_owner_child_events_do_not_reach_unrelated_inherit_all_child() -> None:
    channels = dual_live_windows.create_phase_channels("A")
    handles = getattr(channels, "_handles")
    child_code = r"""
import ctypes
import sys

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.SetEvent(ctypes.c_void_p(int(sys.argv[1])))
kernel32.ResetEvent(ctypes.c_void_p(int(sys.argv[2])))
"""
    try:
        with _lease_wrapper_handles(channels) as wrapper_handles:
            completed = subprocess.run(
                (
                    sys.executable,
                    "-B",
                    "-c",
                    child_code,
                    str(handles["child_revocation_event_handle"]),
                    str(handles["child_send_idle_event_handle"]),
                ),
                close_fds=False,
                check=False,
                env=_job_environment(),
                timeout=5,
            )
            assert completed.returncode == 0
            assert (
                dual_live_windows._kernel32.WaitForSingleObject(
                    wrapper_handles["wrapper_revocation_event_handle"],
                    0,
                )
                == dual_live_windows._WAIT_TIMEOUT
            )
            assert (
                dual_live_windows._kernel32.WaitForSingleObject(
                    wrapper_handles["wrapper_send_idle_event_handle"],
                    0,
                )
                == dual_live_windows._WAIT_OBJECT_0
            )
    finally:
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_factory_rejects_cross_side_pipe_object_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel32 = dual_live_windows._kernel32
    original_create_pipe = kernel32.CreatePipe
    original_duplicate = kernel32.DuplicateHandle
    pipe_calls = 0
    duplicate_calls = 0
    wrapper_control_write = 0

    def capture_control_pipe(
        read_pointer: object,
        write_pointer: object,
        *arguments: object,
    ) -> int:
        nonlocal pipe_calls, wrapper_control_write
        created = int(original_create_pipe(read_pointer, write_pointer, *arguments))
        pipe_calls += 1
        if pipe_calls == 1:
            wrapper_control_write = int(
                ctypes.cast(
                    write_pointer,
                    ctypes.POINTER(ctypes.wintypes.HANDLE),
                ).contents.value
            )
        return created

    def alias_child_app(
        source_process: object,
        source_handle: object,
        target_process: object,
        duplicate_pointer: object,
        desired_access: object,
        inheritable: object,
        options: object,
    ) -> int:
        nonlocal duplicate_calls
        duplicate_calls += 1
        if duplicate_calls == 2:
            source_handle = wrapper_control_write
        return int(
            original_duplicate(
                source_process,
                source_handle,
                target_process,
                duplicate_pointer,
                desired_access,
                inheritable,
                options,
            )
        )

    monkeypatch.setattr(kernel32, "CreatePipe", capture_control_pipe)
    monkeypatch.setattr(kernel32, "DuplicateHandle", alias_child_app)

    _assert_phase_factory_rejects(
        lambda: dual_live_windows.create_phase_channels("B")
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_factory_rejects_event_cross_alias_and_wrong_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel32 = dual_live_windows._kernel32
    original_create_event = kernel32.CreateEventW
    original_duplicate = kernel32.DuplicateHandle
    event_calls = 0
    duplicate_calls = 0
    wrapper_revocation = 0

    def capture_revocation(*arguments: object) -> int:
        nonlocal event_calls, wrapper_revocation
        event_handle = int(original_create_event(*arguments))
        event_calls += 1
        if event_calls == 1:
            wrapper_revocation = event_handle
        return event_handle

    def cross_alias_send_idle(
        source_process: object,
        source_handle: object,
        target_process: object,
        duplicate_pointer: object,
        desired_access: object,
        inheritable: object,
        options: object,
    ) -> int:
        nonlocal duplicate_calls
        duplicate_calls += 1
        if duplicate_calls == 10:
            source_handle = wrapper_revocation
        return int(
            original_duplicate(
                source_process,
                source_handle,
                target_process,
                duplicate_pointer,
                desired_access,
                inheritable,
                options,
            )
        )

    monkeypatch.setattr(kernel32, "CreateEventW", capture_revocation)
    monkeypatch.setattr(kernel32, "DuplicateHandle", cross_alias_send_idle)

    _assert_phase_factory_rejects(
        lambda: dual_live_windows.create_phase_channels("A")
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_a_leases_preserve_exact_event_pairs_and_cross_pair_distinctness() -> None:
    channels = dual_live_windows.create_phase_channels("A")
    try:
        with _lease_wrapper_handles(channels) as wrapper_handles:
            with _lease_child_handles(channels) as child_handles:
                assert dual_live_windows._compare_object_handles(
                    wrapper_handles["wrapper_revocation_event_handle"],
                    child_handles["child_revocation_event_handle"],
                )
                assert dual_live_windows._compare_object_handles(
                    wrapper_handles["wrapper_send_idle_event_handle"],
                    child_handles["child_send_idle_event_handle"],
                )
                ctypes.set_last_error(0)
                assert not dual_live_windows._compare_object_handles(
                    wrapper_handles["wrapper_revocation_event_handle"],
                    child_handles["child_send_idle_event_handle"],
                )
                assert ctypes.get_last_error() == dual_live_windows._ERROR_NOT_SAME_OBJECT
    finally:
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_handle_lease_remains_valid_during_concurrent_owner_close() -> None:
    channels = dual_live_windows.create_phase_channels("A")
    owner_handles = _phase_private_handles(
        channels,
        dual_live_windows._PHASE_HANDLE_ROLES,
    )
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def close_owner() -> None:
        try:
            barrier.wait(timeout=5)
            channels.close()
        except BaseException as exc:
            errors.append(exc)

    try:
        with _lease_child_handles(channels) as child_handles:
            leased = tuple(child_handles.values())
            assert set(leased).isdisjoint(owner_handles)
            closer = threading.Thread(target=close_owner)
            closer.start()
            barrier.wait(timeout=5)
            closer.join(timeout=5)
            assert not closer.is_alive()
            assert errors == []
            assert channels.closed
            assert all(_handle_flags(handle) == 1 for handle in leased)
        assert not child_handles
        flags = ctypes.wintypes.DWORD()
        assert all(
            not dual_live_windows._kernel32.GetHandleInformation(
                handle,
                ctypes.byref(flags),
            )
            for handle in leased
        )
        assert all(
            not dual_live_windows._kernel32.GetHandleInformation(
                handle,
                ctypes.byref(flags),
            )
            for handle in owner_handles
        )
    finally:
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_lease_finalizer_preserves_recycled_different_object_handle() -> None:
    channels = dual_live_windows.create_phase_channels("B")
    baseline = _process_handle_count()
    recycled_events: list[int] = []
    victim = 0
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_channels_lease_compromised",
        ):
            with _lease_wrapper_handles(channels) as wrapper_handles:
                borrowed = wrapper_handles["wrapper_control_write_handle"]
                assert dual_live_windows._kernel32.CloseHandle(borrowed)
                for _ in range(1024):
                    candidate = dual_live_windows._kernel32.CreateEventW(
                        None,
                        True,
                        False,
                        None,
                    )
                    assert candidate
                    value = int(candidate)
                    recycled_events.append(value)
                    if value == borrowed:
                        victim = value
                        break
                assert victim == borrowed

        assert not wrapper_handles
        flags = ctypes.wintypes.DWORD()
        assert dual_live_windows._kernel32.GetHandleInformation(
            victim,
            ctypes.byref(flags),
        )
        assert (
            dual_live_windows._kernel32.WaitForSingleObject(victim, 0)
            == dual_live_windows._WAIT_TIMEOUT
        )
        assert _process_handle_count() == baseline + 1
    finally:
        flags = ctypes.wintypes.DWORD()
        for handle in recycled_events:
            if dual_live_windows._kernel32.GetHandleInformation(
                handle,
                ctypes.byref(flags),
            ):
                dual_live_windows._kernel32.CloseHandle(handle)
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_lease_finalizer_retries_actual_close_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = dual_live_windows.create_phase_channels("B")
    baseline = _process_handle_count()
    original_close = dual_live_windows._kernel32.CloseHandle
    failed_handle = 0
    failed_once = False
    calls: list[int] = []

    def fail_once(handle: object) -> int:
        nonlocal failed_once
        value = int(handle)
        calls.append(value)
        if value == failed_handle and not failed_once:
            failed_once = True
            ctypes.set_last_error(5)
            return 0
        return int(original_close(handle))

    monkeypatch.setattr(dual_live_windows._kernel32, "CloseHandle", fail_once)
    try:
        with _lease_wrapper_handles(channels) as wrapper_handles:
            failed_handle = wrapper_handles["wrapper_control_write_handle"]
        assert not wrapper_handles
        assert calls.count(failed_handle) == 2
        assert _process_handle_count() == baseline
    finally:
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_a_channel_flags_events_and_child_admission_close_are_exact() -> None:
    channels = dual_live_windows.create_phase_channels("A")
    try:
        with _lease_wrapper_handles(channels) as wrapper_capabilities:
            wrapper_handles = tuple(wrapper_capabilities.values())
            with _lease_child_handles(channels) as child_capabilities:
                child_handles = tuple(child_capabilities.values())
                assert all(_handle_flags(handle) == 0 for handle in wrapper_handles)
                assert all(
                    _handle_flags(handle) == dual_live_windows._HANDLE_FLAG_INHERIT
                    for handle in child_handles
                )
                assert (
                    dual_live_windows._kernel32.WaitForSingleObject(
                        wrapper_capabilities["wrapper_revocation_event_handle"],
                        0,
                    )
                    == dual_live_windows._WAIT_TIMEOUT
                )
                assert (
                    dual_live_windows._kernel32.WaitForSingleObject(
                        wrapper_capabilities["wrapper_send_idle_event_handle"],
                        0,
                    )
                    == dual_live_windows._WAIT_OBJECT_0
                )

                channels.close_child_handles_after_admission()
                channels.close_child_handles_after_admission()

                with pytest.raises(
                    DualLiveWindowsError,
                    match="dual_live_phase_channels_closed",
                ):
                    with _lease_child_handles(channels):
                        pass
                assert all(
                    _handle_flags(handle) == dual_live_windows._HANDLE_FLAG_INHERIT
                    for handle in child_handles
                )
            flags = ctypes.wintypes.DWORD()
            assert all(
                not dual_live_windows._kernel32.GetHandleInformation(
                    handle,
                    ctypes.byref(flags),
                )
                for handle in child_handles
            )
            assert all(_handle_flags(handle) == 0 for handle in wrapper_handles)
    finally:
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_native_std_binding_captures_raw_output_and_early_refusal_exactly() -> None:
    def launch(argv: tuple[str, ...]) -> tuple[int, bytes, bytes]:
        channels = dual_live_windows.create_phase_channels("B")
        child: JobChild | None = None
        readers: list[dual_live_windows._OwnedPipeReader] = []
        try:
            with _lease_wrapper_handles(channels) as wrapper_handles:
                with _lease_child_handles(channels) as child_handles:
                    readers = [
                        dual_live_windows._OwnedPipeReader(
                            dual_live_windows._duplicate_owned_handle(
                                wrapper_handles[f"wrapper_{stream}_read_handle"]
                            )
                        )
                        for stream in ("stdout", "stderr")
                    ]
                    assert child_handles["child_stdout_write_handle"] != child_handles[
                        "child_stdio_stdout_write_handle"
                    ]
                    assert child_handles["child_stderr_write_handle"] != child_handles[
                        "child_stdio_stderr_write_handle"
                    ]
                    assert dual_live_windows._compare_object_handles(
                        child_handles["child_stdout_write_handle"],
                        child_handles["child_stdio_stdout_write_handle"],
                    )
                    assert dual_live_windows._compare_object_handles(
                        child_handles["child_stderr_write_handle"],
                        child_handles["child_stdio_stderr_write_handle"],
                    )
                    child = create_child_in_job(
                        argv=argv,
                        environment=_job_environment(),
                        inherited_handles=tuple(child_handles.values()),
                        runtime_instance_id=RUNTIME_INSTANCE_ID,
                        wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
                        standard_handles=(
                            child_handles["child_stdio_stdin_read_handle"],
                            child_handles["child_stdio_stdout_write_handle"],
                            child_handles["child_stdio_stderr_write_handle"],
                        ),
                    )
            channels.close()
            exit_code = child.wait(10)
            return exit_code, readers[0].read(4096), readers[1].read(4096)
        finally:
            for reader in readers:
                reader.close()
            if child is not None:
                child.close()
            channels.close()

    raw_code = (
        "import os; assert os.read(0, 1) == b''; "
        "os.write(1, b'raw-owned-out'); os.write(2, b'raw-owned-err')"
    )
    assert launch((sys.executable, "-I", "-B", "-c", raw_code)) == (
        0,
        b"raw-owned-out",
        b"raw-owned-err",
    )
    assert launch(
        (sys.executable, "-I", "-B", str(RUNNER), "--owned-child", "invalid")
    ) == (2, b"", b"dual_live_run_refused\n")


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_channel_public_constructor_rejects_all_raw_capabilities() -> None:
    channels = dual_live_windows.create_phase_channels("A")
    try:
        duplicate = _phase_channel_constructor_args(channels)
        duplicate["child_http_write_handle"] = duplicate["child_app_write_handle"]
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_channels_factory_only",
        ):
            dual_live_windows.PhaseChannels(**duplicate)

        wrong = _phase_channel_constructor_args(channels)
        wrong["child_control_read_handle"], wrong["child_revocation_event_handle"] = (
            wrong["child_revocation_event_handle"],
            wrong["child_control_read_handle"],
        )
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_channels_factory_only",
        ):
            dual_live_windows.PhaseChannels(**wrong)
    finally:
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_stream_pipe_comparison_is_kernel_bound_and_boolean_only() -> None:
    channels = dual_live_windows.create_phase_channels("B")
    duplicate = ctypes.wintypes.HANDLE()
    try:
        with _lease_child_handles(channels) as child_capabilities:
            with _lease_wrapper_handles(channels) as wrapper_capabilities:
                app_handle = child_capabilities["child_app_write_handle"]
                assert dual_live_windows._kernel32.DuplicateHandle(
                    dual_live_windows._kernel32.GetCurrentProcess(),
                    app_handle,
                    dual_live_windows._kernel32.GetCurrentProcess(),
                    ctypes.byref(duplicate),
                    0,
                    True,
                    dual_live_windows._DUPLICATE_SAME_ACCESS,
                )
                assert duplicate.value
                same = dual_live_windows.pipe_capabilities_same(
                    app_handle,
                    int(duplicate.value),
                )
                assert same is True
                assert isinstance(same, bool)

                child_streams = {
                    role: child_capabilities[role]
                    for role in dual_live_windows._PHASE_CHILD_STREAM_PIPE_ROLES
                }
                wrapper_streams = tuple(
                    wrapper_capabilities[role]
                    for role in dual_live_windows._PHASE_WRAPPER_STREAM_PIPE_ROLES
                )
                assert all(
                    dual_live_windows.pipe_capabilities_same(left, right)
                    == (
                        frozenset((left_role, right_role))
                        in dual_live_windows._PHASE_SHARED_PIPE_ROLE_PAIRS
                    )
                    for index, (left_role, left) in enumerate(child_streams.items())
                    for right_role, right in tuple(child_streams.items())[index + 1 :]
                )
                assert len(wrapper_streams) == 5
                channels.validate_stream_pipe_capabilities()
    finally:
        if duplicate.value:
            dual_live_windows._kernel32.CloseHandle(duplicate)
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_stream_validation_never_creates_inheritable_capabilities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = dual_live_windows.create_phase_channels("A")
    observed_flags: list[tuple[int, ...]] = []
    leaked_bytes: list[tuple[int, ...]] = []
    original_validate = dual_live_windows._validate_phase_pipe_relationships
    child_code = r"""
import ctypes
import sys
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
for value in sys.argv[1:]:
    payload = ctypes.create_string_buffer(b"x")
    written = wintypes.DWORD()
    kernel32.WriteFile(
        ctypes.c_void_p(int(value)),
        payload,
        1,
        ctypes.byref(written),
        None,
    )
"""

    def probe(handles: Mapping[str, int]) -> None:
        values = tuple(handles.values())
        observed_flags.append(tuple(_handle_flags(handle) for handle in values))
        results: list[subprocess.CompletedProcess[bytes]] = []

        def race() -> None:
            results.append(
                subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        "-B",
                        "-c",
                        child_code,
                        *(str(handle) for handle in values),
                    ],
                    close_fds=False,
                    check=False,
                    env=_job_environment(),
                )
            )

        attacker = threading.Thread(target=race, name="validation-inherit-race")
        attacker.start()
        attacker.join(timeout=5)
        assert not attacker.is_alive()
        assert len(results) == 1 and results[0].returncode == 0

        available_counts: list[int] = []
        for role in (
            "wrapper_app_read_handle",
            "wrapper_http_read_handle",
            "wrapper_stdout_read_handle",
            "wrapper_stderr_read_handle",
        ):
            handle = handles[role]
            available = ctypes.wintypes.DWORD()
            assert dual_live_windows._kernel32.PeekNamedPipe(
                handle,
                None,
                0,
                None,
                ctypes.byref(available),
                None,
            )
            available_counts.append(int(available.value))
        leaked_bytes.append(tuple(available_counts))
        original_validate(handles)

    monkeypatch.setattr(
        dual_live_windows,
        "_validate_phase_pipe_relationships",
        probe,
    )
    try:
        channels.validate_stream_pipe_capabilities()
        assert leaked_bytes == [(0, 0, 0, 0)]
        assert observed_flags == [(0,) * 12]
    finally:
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_child_admission_refuses_inherit_all_race_and_restores_popen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class AdmissionProbe(RuntimeError):
        pass

    original_popen = subprocess.Popen
    inherited: tuple[int, ...] = ()
    refusal: list[BaseException] = []

    def probe_create_child(
        argv: object,
        environment: object,
        inherited_handles: object,
        runtime_instance_id: object,
        wrapper_nonce_sha256: object,
        standard_handles: object,
    ) -> object:
        nonlocal inherited
        inherited = tuple(inherited_handles)  # type: ignore[arg-type]
        assert inherited
        assert all(_handle_flags(handle) == 1 for handle in inherited)
        assert isinstance(standard_handles, tuple)
        assert tuple(standard_handles) == (
            inherited[1],
            inherited[5],
            inherited[7],
        )

        def race() -> None:
            try:
                subprocess.run(
                    [sys.executable, "-I", "-B", "-c", "pass"],
                    close_fds=False,
                    check=True,
                )
            except BaseException as exc:
                refusal.append(exc)

        attacker = threading.Thread(target=race, name="inherit-all-race")
        attacker.start()
        attacker.join(timeout=5)
        assert not attacker.is_alive()
        raise AdmissionProbe

    monkeypatch.setattr(
        dual_live_windows,
        "create_child_in_job",
        probe_create_child,
    )
    channels = dual_live_windows.create_phase_channels("A")
    try:
        with pytest.raises(AdmissionProbe):
            channels._admit_owned_child(
                dual_live_windows._PHASE_CHANNELS_FACTORY_TOKEN,
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
    finally:
        channels.close()

    assert len(refusal) == 1
    assert isinstance(refusal[0], DualLiveWindowsError)
    assert refusal[0].code == "dual_live_subprocess_refused"
    assert subprocess.Popen is original_popen
    flags = ctypes.wintypes.DWORD()
    assert all(
        not dual_live_windows._kernel32.GetHandleInformation(
            handle,
            ctypes.byref(flags),
        )
        for handle in inherited
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", "pass"],
        check=False,
    )
    assert completed.returncode == 0


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_child_admission_refuses_preexisting_live_python_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered = threading.Event()
    release = threading.Event()
    create_calls: list[str] = []

    def hold_thread() -> None:
        entered.set()
        release.wait()

    def observe_create(**_arguments: object) -> object:
        create_calls.append("create")
        raise AssertionError("low-level child creation must not be reached")

    monkeypatch.setattr(
        dual_live_windows,
        "create_child_in_job",
        observe_create,
    )
    blocker = threading.Thread(target=hold_thread, name="preexisting-live-thread")
    blocker.start()
    assert entered.wait(timeout=5)

    channels = dual_live_windows.create_phase_channels("A")
    baseline_handles = _process_handle_count()
    original_popen = subprocess.Popen
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_subprocess_gate_busy",
        ):
            channels._admit_owned_child(
                dual_live_windows._PHASE_CHANNELS_FACTORY_TOKEN,
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )

        assert create_calls == []
        assert subprocess.Popen is original_popen
        assert _process_handle_count() == baseline_handles
        owner_handles = _phase_private_handles(
            channels,
            dual_live_windows._PHASE_HANDLE_ROLES,
        )
        assert all(_handle_flags(handle) == 0 for handle in owner_handles)
    finally:
        release.set()
        blocker.join(timeout=5)
        channels.close()

    assert not blocker.is_alive()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_child_admission_detects_popen_mutation_and_restores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class AdmissionProbe(RuntimeError):
        pass

    original_popen = subprocess.Popen

    def mutate_gate(**_arguments: object) -> object:
        setattr(subprocess, "Popen", lambda *_args, **_kwargs: None)
        raise AdmissionProbe("admission also failed")

    monkeypatch.setattr(
        dual_live_windows,
        "create_child_in_job",
        mutate_gate,
    )
    channels = dual_live_windows.create_phase_channels("B")
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_subprocess_gate_compromised",
        ) as exc:
            channels._admit_owned_child(
                dual_live_windows._PHASE_CHANNELS_FACTORY_TOKEN,
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
    finally:
        channels.close()

    assert isinstance(exc.value.__context__, AdmissionProbe)
    assert subprocess.Popen is original_popen


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_child_cleanup_failure_dominates_and_retains_retryable_custody(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class AdmissionProbe(RuntimeError):
        pass

    class ContainmentProbe(RuntimeError):
        pass

    class CloseProbe(RuntimeError):
        pass

    child = JobChild(1, "a" * 64, "b" * 64)
    cleanup_events: list[str] = []
    original_containment = JobChild.retain_then_terminate_tree
    original_close = JobChild.close

    def return_child(**_arguments: object) -> JobChild:
        return child

    def fail_admission_close(_channels: object) -> None:
        raise AdmissionProbe("post-create admission close failed")

    def fail_containment(_child: object) -> None:
        cleanup_events.append("contain")
        raise ContainmentProbe("containment failed")

    def fail_close(_child: object) -> None:
        cleanup_events.append("close")
        raise CloseProbe("close failed")

    monkeypatch.setattr(dual_live_windows, "create_child_in_job", return_child)
    monkeypatch.setattr(
        dual_live_windows.PhaseChannels,
        "close_child_handles_after_admission",
        fail_admission_close,
    )
    monkeypatch.setattr(JobChild, "retain_then_terminate_tree", fail_containment)
    monkeypatch.setattr(JobChild, "close", fail_close)

    channels = dual_live_windows.create_phase_channels("B")
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_child_cleanup_failed",
        ) as exc:
            channels._admit_owned_child(
                dual_live_windows._PHASE_CHANNELS_FACTORY_TOKEN,
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
    finally:
        channels._close_roles(dual_live_windows._PHASE_HANDLE_ROLES)

    assert cleanup_events == ["contain", "contain"]
    assert isinstance(exc.value.__context__, AdmissionProbe)
    assert isinstance(exc.value.__cause__, DualLiveWindowsError)
    assert isinstance(exc.value.__cause__.__cause__, ContainmentProbe)
    assert len(dual_live_windows._failed_owned_custodies) == 1
    custody = dual_live_windows._failed_owned_custodies[0]
    assert custody.child is child
    assert custody.terminated is False

    monkeypatch.setattr(JobChild, "retain_then_terminate_tree", lambda _child: None)
    monkeypatch.setattr(JobChild, "close", lambda _child: None)
    dual_live_windows._retry_failed_owned_custodies()
    assert dual_live_windows._failed_owned_custodies == []
    monkeypatch.setattr(JobChild, "retain_then_terminate_tree", original_containment)
    monkeypatch.setattr(JobChild, "close", original_close)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_child_persistent_close_retains_terminated_custody(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class AdmissionProbe(RuntimeError):
        pass

    class CloseProbe(RuntimeError):
        pass

    child = JobChild(1, "a" * 64, "b" * 64)
    events: list[str] = []
    original_containment = JobChild.retain_then_terminate_tree
    original_close = JobChild.close
    monkeypatch.setattr(
        dual_live_windows,
        "create_child_in_job",
        lambda **_arguments: child,
    )
    monkeypatch.setattr(
        dual_live_windows.PhaseChannels,
        "close_child_handles_after_admission",
        lambda _channels: (_ for _ in ()).throw(AdmissionProbe()),
    )
    monkeypatch.setattr(
        JobChild,
        "retain_then_terminate_tree",
        lambda _child: events.append("contain"),
    )

    def fail_close(_child: JobChild) -> None:
        events.append("close")
        raise CloseProbe

    monkeypatch.setattr(JobChild, "close", fail_close)
    channels = dual_live_windows.create_phase_channels("B")
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_child_cleanup_failed",
        ) as exc:
            channels._admit_owned_child(
                dual_live_windows._PHASE_CHANNELS_FACTORY_TOKEN,
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
    finally:
        channels._close_roles(dual_live_windows._PHASE_HANDLE_ROLES)

    assert events == ["contain", "close", "close"]
    assert isinstance(exc.value.__context__, AdmissionProbe)
    assert len(dual_live_windows._failed_owned_custodies) == 1
    custody = dual_live_windows._failed_owned_custodies[0]
    assert custody.child is child and custody.terminated is True
    monkeypatch.setattr(JobChild, "close", lambda _child: None)
    dual_live_windows._retry_failed_owned_custodies()
    assert dual_live_windows._failed_owned_custodies == []
    monkeypatch.setattr(JobChild, "retain_then_terminate_tree", original_containment)
    monkeypatch.setattr(JobChild, "close", original_close)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_child_cleanup_retries_transient_job_handle_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class AdmissionProbe(RuntimeError):
        pass

    child = _create_test_child("import time; time.sleep(30)")
    assert child._job_handle is not None
    job_handle = child._job_handle
    original_close = dual_live_windows._kernel32.CloseHandle
    job_close_calls = 0

    def return_child(**_arguments: object) -> JobChild:
        return child

    def fail_admission_close(_channels: object) -> None:
        raise AdmissionProbe("post-create admission close failed")

    def fail_job_close_once(handle: int) -> int:
        nonlocal job_close_calls
        if int(handle) == job_handle:
            job_close_calls += 1
            if job_close_calls == 1:
                ctypes.set_last_error(5)
                return 0
        return int(original_close(handle))

    monkeypatch.setattr(dual_live_windows, "create_child_in_job", return_child)
    monkeypatch.setattr(
        dual_live_windows.PhaseChannels,
        "close_child_handles_after_admission",
        fail_admission_close,
    )
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "CloseHandle",
        fail_job_close_once,
    )

    channels = dual_live_windows.create_phase_channels("B")
    owned_handles = set(
        _phase_private_handles(
            channels,
            dual_live_windows._PHASE_HANDLE_ROLES,
        )
    )
    assert child._job_handle is not None
    assert child._process_handle is not None
    owned_handles.update((child._job_handle, child._process_handle))
    owned_handles.update(
        retained[0] for retained in child._retained_processes.values()
    )
    try:
        with pytest.raises(AdmissionProbe) as exc:
            channels._admit_owned_child(
                dual_live_windows._PHASE_CHANNELS_FACTORY_TOKEN,
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )

        assert job_close_calls == 2
        assert child._job_handle is None
        assert child._process_handle is None
        assert child._retained_processes == {}
        assert child._closed
        assert exc.value.__context__ is None
        assert dual_live_windows._failed_owned_custodies == []
        assert dual_live_windows._retained_owned_handles == set()
    finally:
        if not child._closed:
            try:
                child.terminate_tree()
            except DualLiveWindowsError:
                pass
            child.close()
        channels._close_roles(dual_live_windows._PHASE_HANDLE_ROLES)

    flags = ctypes.wintypes.DWORD()
    assert all(
        not dual_live_windows._kernel32.GetHandleInformation(
            handle,
            ctypes.byref(flags),
        )
        for handle in owned_handles
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_pipe_descriptor_comparison_delegates_to_kernel_object_identity() -> None:
    first_read, first_write = os.pipe()
    duplicate_write = os.dup(first_write)
    second_read, second_write = os.pipe()
    closed_write = os.dup(first_write)
    file_fd = os.open(__file__, os.O_RDONLY)
    os.close(closed_write)
    try:
        same = dual_live_windows.pipe_descriptors_same(
            first_write,
            duplicate_write,
        )
        assert same is True
        assert isinstance(same, bool)
        assert dual_live_windows.pipe_descriptors_same(first_write, second_write) is False
        for invalid in (True, -1, closed_write, file_fd):
            with pytest.raises(
                DualLiveWindowsError,
                match="dual_live_phase_channels_invalid",
            ):
                dual_live_windows.pipe_descriptors_same(first_write, invalid)
    finally:
        for fd in (
            file_fd,
            duplicate_write,
            first_write,
            first_read,
            second_write,
            second_read,
        ):
            os.close(fd)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_pipe_descriptor_comparison_propagates_indeterminate_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read_fd, write_fd = os.pipe()
    duplicate_fd = os.dup(write_fd)

    def deny_comparison(*_: object) -> int:
        ctypes.set_last_error(5)
        return 0

    monkeypatch.setattr(
        dual_live_windows,
        "_compare_object_handles",
        deny_comparison,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_pipe_identity_indeterminate",
        ):
            dual_live_windows.pipe_descriptors_same(write_fd, duplicate_fd)
    finally:
        for fd in (duplicate_fd, write_fd, read_fd):
            os.close(fd)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_handle_validation_rejects_same_pipe_object_under_new_handle() -> None:
    channels = dual_live_windows.create_phase_channels("B")
    duplicate = ctypes.wintypes.HANDLE()
    duplicate_args = _phase_channel_constructor_args(channels)
    phase = duplicate_args.pop("phase")
    app_handle = duplicate_args["child_app_write_handle"]
    assert isinstance(app_handle, int)
    try:
        assert dual_live_windows._kernel32.DuplicateHandle(
            dual_live_windows._kernel32.GetCurrentProcess(),
            app_handle,
            dual_live_windows._kernel32.GetCurrentProcess(),
            ctypes.byref(duplicate),
            0,
            False,
            dual_live_windows._DUPLICATE_SAME_ACCESS,
        )
        duplicate_args["child_http_write_handle"] = int(duplicate.value)
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_channels_invalid",
        ):
            dual_live_windows._validated_phase_handles(phase, duplicate_args)
    finally:
        if duplicate.value:
            dual_live_windows._kernel32.CloseHandle(duplicate)
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_pipe_comparison_api_absence_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = dual_live_windows.create_phase_channels("B")
    first, second = _phase_private_handles(
        channels,
        dual_live_windows._PHASE_CHILD_STREAM_PIPE_ROLES,
    )[:2]
    monkeypatch.setattr(dual_live_windows, "_compare_object_handles", None)
    try:
        with pytest.raises(DualLiveWindowsError, match="dual_live_job_unsupported"):
            dual_live_windows.pipe_capabilities_same(first, second)
        with pytest.raises(DualLiveWindowsError, match="dual_live_job_unsupported"):
            dual_live_windows.create_phase_channels("B")
    finally:
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_channel_partial_close_is_retryable_without_double_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = dual_live_windows.create_phase_channels("B")
    handles = _phase_private_handles(
        channels,
        dual_live_windows._PHASE_CHILD_ROLES + dual_live_windows._PHASE_WRAPPER_ROLES,
    )
    failed_handle = getattr(channels, "_handles")["wrapper_http_read_handle"]
    assert isinstance(failed_handle, int)
    original_close = dual_live_windows._kernel32.CloseHandle
    calls: list[int] = []
    failed_once = False

    def fail_once(handle: object) -> int:
        nonlocal failed_once
        value = int(handle)
        calls.append(value)
        if value == failed_handle and not failed_once:
            failed_once = True
            return 0
        return int(original_close(handle))

    monkeypatch.setattr(dual_live_windows._kernel32, "CloseHandle", fail_once)
    with pytest.raises(
        DualLiveWindowsError,
        match="dual_live_phase_channels_cleanup_failed",
    ):
        channels.close()
    assert _phase_private_handles(
        channels,
        dual_live_windows._PHASE_WRAPPER_ROLES,
    ) == (failed_handle,)
    assert _phase_private_handles(channels, dual_live_windows._PHASE_CHILD_ROLES) == ()
    assert not channels.closed

    channels.close()
    channels.close()
    assert channels.closed
    assert calls.count(failed_handle) == 2
    assert all(calls.count(handle) == 1 for handle in handles if handle != failed_handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_channel_concurrent_close_never_double_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = dual_live_windows.create_phase_channels("A")
    handles = _phase_private_handles(
        channels,
        dual_live_windows._PHASE_CHILD_ROLES + dual_live_windows._PHASE_WRAPPER_ROLES,
    )
    original_close = dual_live_windows._kernel32.CloseHandle
    calls: list[int] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(4)

    def recording_close(handle: object) -> int:
        calls.append(int(handle))
        return int(original_close(handle))

    def close_repeatedly() -> None:
        try:
            barrier.wait(timeout=5)
            for _ in range(20):
                channels.close_child_handles_after_admission()
                channels.close()
        except BaseException as exc:
            errors.append(exc)

    def read_repeatedly() -> None:
        try:
            barrier.wait(timeout=5)
            for _ in range(200):
                assert isinstance(channels.closed, bool)
        except BaseException as exc:
            errors.append(exc)

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "CloseHandle",
        recording_close,
    )
    workers = (
        threading.Thread(target=close_repeatedly),
        threading.Thread(target=close_repeatedly),
        threading.Thread(target=read_repeatedly),
    )
    for worker in workers:
        worker.start()
    barrier.wait(timeout=5)
    for worker in workers:
        worker.join(timeout=5)

    assert all(not worker.is_alive() for worker in workers)
    assert errors == []
    assert channels.closed
    assert all(calls.count(handle) == 1 for handle in handles)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("duplicate_failure_call", (3, 11))
def test_phase_channel_creation_failure_and_success_cleanup_do_not_leak_handles(
    duplicate_failure_call: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warmup = dual_live_windows.create_phase_channels("A")
    warmup.close()
    baseline = _process_handle_count()
    original_duplicate = dual_live_windows._kernel32.DuplicateHandle
    duplicate_calls = 0

    def fail_selected_duplicate(*args: object) -> int:
        nonlocal duplicate_calls
        duplicate_calls += 1
        if duplicate_calls == duplicate_failure_call:
            ctypes.set_last_error(5)
            return 0
        return int(original_duplicate(*args))

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "DuplicateHandle",
        fail_selected_duplicate,
    )
    with pytest.raises(
        DualLiveWindowsError,
        match="dual_live_phase_channels_create_failed",
    ):
        dual_live_windows.create_phase_channels("A")
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "DuplicateHandle",
        original_duplicate,
    )
    assert _process_handle_count() == baseline

    for phase in ("A", "B", "A", "B"):
        channels = dual_live_windows.create_phase_channels(phase)
        channels.close_child_handles_after_admission()
        channels.close()
    assert _process_handle_count() == baseline


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_handle_lease_partial_duplicate_output_is_reclaimed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = dual_live_windows.create_phase_channels("A")
    with _lease_child_handles(channels):
        pass
    baseline = _process_handle_count()
    original_duplicate = dual_live_windows._kernel32.DuplicateHandle
    calls = 0

    def duplicate_then_fail(*arguments: object) -> int:
        nonlocal calls
        calls += 1
        created = int(original_duplicate(*arguments))
        if calls == 3:
            assert created
            ctypes.set_last_error(5)
            return 0
        return created

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "DuplicateHandle",
        duplicate_then_fail,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_channels_lease_failed",
        ):
            with _lease_child_handles(channels):
                pass
        assert _process_handle_count() == baseline
    finally:
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("api_name", ("CreatePipe", "DuplicateHandle"))
def test_phase_channel_partial_api_output_is_reclaimed(
    api_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warmup = dual_live_windows.create_phase_channels("A")
    warmup.close()
    baseline = _process_handle_count()
    original = getattr(dual_live_windows._kernel32, api_name)

    def create_then_fail(*args: object) -> int:
        assert original(*args)
        ctypes.set_last_error(5)
        return 0

    monkeypatch.setattr(dual_live_windows._kernel32, api_name, create_then_fail)
    with pytest.raises(
        DualLiveWindowsError,
        match="dual_live_phase_channels_create_failed",
    ):
        dual_live_windows.create_phase_channels("A")
    monkeypatch.setattr(dual_live_windows._kernel32, api_name, original)
    assert _process_handle_count() == baseline


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_child_handle_bootstrap_clears_inheritance_and_rejects_bad_sets(
    tmp_path: Path,
) -> None:
    channels = dual_live_windows.create_phase_channels("A")
    disallowed, keepalive = _make_inheritable_disallowed_handle("file", tmp_path)
    try:
        with _lease_child_handles(channels) as child_handles:
            before = tuple(child_handles.values())
            assert all(_handle_flags(handle) == 1 for handle in before)
            dual_live_windows.make_inherited_handles_non_inheritable(before)
            assert all(_handle_flags(handle) == 0 for handle in before)
            with pytest.raises(
                DualLiveWindowsError,
                match="dual_live_job_inherited_handles_invalid",
            ):
                dual_live_windows.make_inherited_handles_non_inheritable(
                    (before[0], before[0])
                )
            with pytest.raises(
                DualLiveWindowsError,
                match="dual_live_job_inherited_handles_invalid",
            ):
                dual_live_windows.make_inherited_handles_non_inheritable(
                    (disallowed,)
                )
    finally:
        channels.close()
        if isinstance(keepalive, socket.socket):
            keepalive.close()
        else:
            dual_live_windows._kernel32.CloseHandle(disallowed)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_child_handle_bootstrap_set_failure_attempts_all_handles_then_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = dual_live_windows.create_phase_channels("A")
    original_set = dual_live_windows._kernel32.SetHandleInformation
    calls: list[int] = []
    failed_once = False

    def fail_once(handle: object, mask: object, flags: object) -> int:
        nonlocal failed_once
        value = int(handle)
        calls.append(value)
        if value == failed_handle and not failed_once:
            failed_once = True
            ctypes.set_last_error(5)
            return 0
        return int(original_set(handle, mask, flags))

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "SetHandleInformation",
        fail_once,
    )
    try:
        with _lease_child_handles(channels) as child_handles:
            handles = tuple(child_handles.values())
            failed_handle = handles[1]
            with pytest.raises(
                DualLiveWindowsError,
                match="dual_live_job_inherited_handles_invalid",
            ):
                dual_live_windows.make_inherited_handles_non_inheritable(handles)
            assert calls == list(handles)
            assert (
                _handle_flags(failed_handle)
                == dual_live_windows._HANDLE_FLAG_INHERIT
            )
            assert all(
                _handle_flags(handle) == 0
                for handle in handles
                if handle != failed_handle
            )

            monkeypatch.setattr(
                dual_live_windows._kernel32,
                "SetHandleInformation",
                original_set,
            )
            dual_live_windows.make_inherited_handles_non_inheritable(handles)
            assert all(_handle_flags(handle) == 0 for handle in handles)
    finally:
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_child_handle_bootstrap_readback_failure_is_aggregated_and_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = dual_live_windows.create_phase_channels("A")
    original_get = dual_live_windows._kernel32.GetHandleInformation
    calls = 0

    def fail_first_readback(handle: object, flags_pointer: object) -> int:
        nonlocal calls
        calls += 1
        if calls == len(handles) + 1:
            ctypes.set_last_error(5)
            return 0
        return int(original_get(handle, flags_pointer))

    try:
        with _lease_child_handles(channels) as child_handles:
            handles = tuple(child_handles.values())
            monkeypatch.setattr(
                dual_live_windows._kernel32,
                "GetHandleInformation",
                fail_first_readback,
            )
            with pytest.raises(
                DualLiveWindowsError,
                match="dual_live_job_inherited_handles_invalid",
            ):
                dual_live_windows.make_inherited_handles_non_inheritable(handles)
            assert calls == len(handles) * 2

            monkeypatch.setattr(
                dual_live_windows._kernel32,
                "GetHandleInformation",
                original_get,
            )
            assert all(_handle_flags(handle) == 0 for handle in handles)
            dual_live_windows.make_inherited_handles_non_inheritable(handles)
            assert all(_handle_flags(handle) == 0 for handle in handles)
    finally:
        channels.close()


def test_phase_channels_and_current_boot_id_fail_closed_without_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dual_live_windows, "_kernel32", None)
    monkeypatch.setattr(dual_live_windows, "_advapi32", None)

    for operation in (
        lambda: dual_live_windows.create_phase_channels("A"),
        lambda: dual_live_windows.make_inherited_handles_non_inheritable((1,)),
        lambda: dual_live_windows.pipe_descriptors_same(1, 2),
        lambda: dual_live_windows.current_process_boot_id(
            RUNTIME_INSTANCE_ID,
            WRAPPER_NONCE_SHA,
        ),
    ):
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_windows_unsupported",
        ):
            operation()


def test_boot_id_callers_share_one_canonical_derivation() -> None:
    derivation_call = "_derive_process_boot_identity("
    create_source = inspect.getsource(dual_live_windows._create_child_in_job_locked)
    current_source = inspect.getsource(dual_live_windows.current_process_boot_id)
    assert create_source.count(derivation_call) == 1
    assert current_source.count(derivation_call) == 1
    assert "wrapper_nonce_sha256" in create_source
    assert "wrapper_nonce_sha256" in current_source
    assert "hashlib.sha256" not in create_source
    assert "hashlib.sha256" not in current_source


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_current_process_boot_id_refuses_identity_probe_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetProcessTimes",
        lambda *args: 0,
    )

    with pytest.raises(
        DualLiveWindowsError,
        match="dual_live_process_identity_indeterminate",
    ):
        dual_live_windows.current_process_boot_id(
            RUNTIME_INSTANCE_ID,
            WRAPPER_NONCE_SHA,
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_child_current_boot_id_matches_parent_and_handles_do_not_reach_grandchild() -> None:
    channels = dual_live_windows.create_phase_channels("A")
    child_code = r"""
import sys
sys.path.insert(0, sys.argv[1])
from app.services.dual_live_windows import current_process_boot_id, make_inherited_handles_non_inheritable

handles = tuple(int(value) for value in sys.argv[4].split(","))
make_inherited_handles_non_inheritable(handles)

import ctypes
import json
import subprocess

probe = r'''import ctypes, sys
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.SetEvent.argtypes = (ctypes.c_void_p,)
kernel32.SetEvent.restype = ctypes.c_int
kernel32.SetEvent(ctypes.c_void_p(int(sys.argv[1])))
'''
grandchild = subprocess.run(
    [sys.executable, "-B", "-c", probe, sys.argv[6]],
    close_fds=False,
    check=False,
)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.WriteFile.argtypes = (
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_ulong,
    ctypes.POINTER(ctypes.c_ulong),
    ctypes.c_void_p,
)
kernel32.WriteFile.restype = ctypes.c_int
flags = ctypes.c_ulong()
own_flags_clear = all(
    kernel32.GetHandleInformation(ctypes.c_void_p(handle), ctypes.byref(flags))
    and flags.value == 0
    for handle in handles
)
revocation_unsignaled = (
    kernel32.WaitForSingleObject(ctypes.c_void_p(int(sys.argv[6])), 0) == 0x102
)
payload = json.dumps(
    {
        "boot_id": current_process_boot_id(sys.argv[2], sys.argv[3]),
        "grandchild_probe_ran": grandchild.returncode == 0,
        "own_flags_clear": own_flags_clear,
        "revocation_unsignaled": revocation_unsignaled,
    },
    sort_keys=True,
).encode("ascii")
written = ctypes.c_ulong()
ok = kernel32.WriteFile(
    ctypes.c_void_p(int(sys.argv[5])),
    payload,
    len(payload),
    ctypes.byref(written),
    None,
)
raise SystemExit(0 if ok and written.value == len(payload) else 8)
"""
    child: JobChild | None = None
    try:
        with _lease_child_handles(channels) as child_capabilities:
            with _lease_wrapper_handles(channels) as wrapper_capabilities:
                inherited_handles = tuple(child_capabilities.values())
                app_write_handle = child_capabilities["child_app_write_handle"]
                revocation_handle = child_capabilities[
                    "child_revocation_event_handle"
                ]
                app_read_handle = wrapper_capabilities["wrapper_app_read_handle"]
                child = create_child_in_job(
                    argv=(
                        sys.executable,
                        "-B",
                        "-c",
                        child_code,
                        str(BACKEND),
                        RUNTIME_INSTANCE_ID,
                        WRAPPER_NONCE_SHA,
                        ",".join(str(handle) for handle in inherited_handles),
                        str(app_write_handle),
                        str(revocation_handle),
                    ),
                    environment=_job_environment(),
                    inherited_handles=inherited_handles,
                    runtime_instance_id=RUNTIME_INSTANCE_ID,
                    wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
                )
                channels.close_child_handles_after_admission()
                assert child.wait(10) == 0
                payload_buffer = ctypes.create_string_buffer(1024)
                received = ctypes.wintypes.DWORD()
                assert dual_live_windows._kernel32.ReadFile(
                    app_read_handle,
                    payload_buffer,
                    len(payload_buffer),
                    ctypes.byref(received),
                    None,
                )
                payload = json.loads(payload_buffer.raw[: received.value])
                assert payload == {
                    "boot_id": child.process_boot_id,
                    "grandchild_probe_ran": True,
                    "own_flags_clear": True,
                    "revocation_unsignaled": True,
                }
                assert (
                    dual_live_windows._kernel32.WaitForSingleObject(
                        wrapper_capabilities["wrapper_revocation_event_handle"],
                        0,
                    )
                    == dual_live_windows._WAIT_TIMEOUT
                )
    finally:
        if child is not None:
            child.close()
        channels.close()


def test_job_start_evidence_has_exact_frozen_public_shape() -> None:
    evidence_type = dual_live_windows.JobStartEvidence
    assert tuple(field.name for field in fields(evidence_type)) == (
        "pid",
        "process_creation_identity_sha256",
        "process_boot_id",
        "executable_sha256",
        "job_policy_sha256",
    )
    evidence = evidence_type(
        pid=1,
        process_creation_identity_sha256="a" * 64,
        process_boot_id="b" * 64,
        executable_sha256="c" * 64,
        job_policy_sha256="d" * 64,
    )

    with pytest.raises(FrozenInstanceError):
        evidence.pid = 2


def test_job_start_evidence_is_unavailable_for_inert_public_child() -> None:
    child = JobChild(1, "a" * 64, "b" * 64)

    with pytest.raises(
        DualLiveWindowsError,
        match="dual_live_child_start_evidence_unavailable",
    ):
        _ = child.start_evidence
    child.close()
    with pytest.raises(
        DualLiveWindowsError,
        match="dual_live_child_start_evidence_unavailable",
    ):
        _ = child.start_evidence


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_start_evidence_projects_retained_creation_facts_after_close() -> None:
    child = _create_test_child("raise SystemExit(0)")
    evidence = child.start_evidence
    expected_executable_sha256 = hashlib.sha256(
        Path(sys.executable).read_bytes()
    ).hexdigest()
    expected_job_policy_sha256 = hashlib.sha256(
        dual_live_windows._canonical_json_bytes(
            {"limit_flags": dual_live_windows._JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE}
        )
    ).hexdigest()
    assert evidence.pid == child.pid
    assert (
        evidence.process_creation_identity_sha256
        == child.process_creation_identity_sha256
    )
    assert evidence.process_boot_id == child.process_boot_id
    assert evidence.executable_sha256 == expected_executable_sha256
    assert evidence.job_policy_sha256 == expected_job_policy_sha256
    assert evidence.executable_sha256 == child._executable_sha256
    assert evidence.job_policy_sha256 == child._job_policy_sha256

    assert child.wait(5) == 0
    child.close()
    assert child.start_evidence is evidence


def test_isolated_config_module_singleton_ignores_shadow_dotenv(tmp_path: Path) -> None:
    assert _run_shadow_config(tmp_path, isolated=True) == {
        "api_key": False,
        "grant_path": False,
        "grant_sha": False,
    }


def test_nonisolated_config_module_singleton_preserves_shadow_dotenv(
    tmp_path: Path,
) -> None:
    assert _run_shadow_config(tmp_path, isolated=False) == {
        "api_key": True,
        "grant_path": True,
        "grant_sha": True,
    }


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("exit_code", [0, 7, 259])
def test_job_child_exit_is_identity_bound(exit_code: int) -> None:
    child = _create_test_child("import sys; raise SystemExit(int(sys.argv[1]))", str(exit_code))
    with child:
        assert child.wait(5) == exit_code
        assert child.wait(0) == exit_code
        assert child.pid > 0
        assert len(child.process_creation_identity_sha256) == 64
        executable_sha256 = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
        assert child.process_boot_id == hashlib.sha256(
            dual_live_windows._canonical_json_bytes(
                {
                    "executable_sha256": executable_sha256,
                    "pid": child.pid,
                    "process_creation_identity_sha256": (
                        child.process_creation_identity_sha256
                    ),
                    "runtime_instance_id": RUNTIME_INSTANCE_ID,
                    "wrapper_nonce_sha256": WRAPPER_NONCE_SHA,
                }
            )
        ).hexdigest()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_child_quiescence_is_secret_safe() -> None:
    child = _create_test_child("raise SystemExit(0)")
    with child:
        assert child.wait(5) == 0
        _assert_quiescence_record(prove_child_quiescence(child))


def test_job_child_public_constructor_is_exact_and_inert_close_is_idempotent() -> None:
    assert tuple(inspect.signature(JobChild).parameters) == (
        "pid",
        "process_creation_identity_sha256",
        "process_boot_id",
    )
    child = JobChild(1, "a" * 64, "b" * 64)
    child.close()
    child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_child_empty_handle_list_refuses_before_child_effect(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "forbidden-marker"
    with pytest.raises(
        DualLiveWindowsError, match="dual_live_job_inherited_handles_invalid"
    ):
        create_child_in_job(
            argv=(
                sys.executable,
                "-B",
                "-c",
                "from pathlib import Path; Path(__import__('sys').argv[1]).touch()",
                str(marker),
            ),
            environment=_job_environment(),
            inherited_handles=(),
            runtime_instance_id=RUNTIME_INSTANCE_ID,
            wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
        )
    assert not marker.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_environment_block_is_sorted_unique_and_double_nul() -> None:
    assert dual_live_windows._environment_block({})[:] == "\0\0"
    block = dual_live_windows._environment_block(
        {"zeta": "3", "Alpha": "1", "beta": "2"}
    )
    assert block[:] == "Alpha=1\0beta=2\0zeta=3\0\0"
    with pytest.raises(
        DualLiveWindowsError, match="dual_live_windows_arguments_invalid"
    ):
        dual_live_windows._environment_block({"Path": "a", "PATH": "b"})


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("mode", ("unexpected_success", "wrong_error", "zero_size"))
def test_job_attribute_list_null_probe_requires_exact_sizing_status(
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def wrong_probe(
        attribute_list: object,
        attribute_count: int,
        flags: int,
        size_pointer: object,
    ) -> int:
        del attribute_count, flags
        assert not attribute_list
        size = ctypes.cast(
            size_pointer, ctypes.POINTER(ctypes.c_size_t)
        ).contents
        size.value = 0 if mode == "zero_size" else 128
        ctypes.set_last_error(
            dual_live_windows._ERROR_INSUFFICIENT_BUFFER
            if mode != "wrong_error"
            else 5
        )
        return int(mode == "unexpected_success")

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "InitializeProcThreadAttributeList",
        wrong_probe,
    )
    with pytest.raises(DualLiveWindowsError, match="dual_live_job_unsupported"):
        dual_live_windows._attribute_list_size()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_leaf_reparse_executable_refuses_before_child_effect(
    tmp_path: Path,
) -> None:
    executable_link = tmp_path / "python-link.exe"
    executable_link.symlink_to(Path(sys.executable), target_is_directory=False)
    marker = tmp_path / "forbidden-marker"
    read_handle, write_handle = _inheritable_pipe()
    try:
        with pytest.raises(
            DualLiveWindowsError, match="dual_live_executable_invalid"
        ):
            create_child_in_job(
                argv=(
                    str(executable_link),
                    "-B",
                    "-c",
                    "from pathlib import Path; Path(__import__('sys').argv[1]).touch()",
                    str(marker),
                ),
                environment=_job_environment(),
                inherited_handles=(write_handle,),
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
    finally:
        dual_live_windows._kernel32.CloseHandle(read_handle)
        dual_live_windows._kernel32.CloseHandle(write_handle)
    assert not marker.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize(
    "unsafe_executable",
    (
        r"\\server\share\python.exe",
        r"\\.\C:\python.exe",
        r"\\?\C:\python.exe",
        r"\??\C:\python.exe",
    ),
)
def test_job_unsafe_executable_namespace_refuses_before_any_io(
    unsafe_executable: str,
) -> None:
    with pytest.raises(
        DualLiveWindowsError, match="dual_live_executable_invalid"
    ):
        dual_live_windows._validated_executable_path_text(unsafe_executable)


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
@pytest.mark.parametrize(
    "unsafe_path",
    (
        r"\\server\share\proof",
        r"//SERVER/share/proof",
        r"\\.\C:\proof",
        r"\\?\UNC\server\share\proof",
        r"\\?\c:\proof",
        r"\??\C:\proof",
        r"\Device\Mup\server\share\proof",
        r"C:\proof\index.json:stream",
        r"C:\proof\CON.json",
        "C:\\proof\\trailing.\\index.json",
        "C:\\proof\\trailing \\index.json",
    ),
)
def test_local_fixed_path_rejects_namespaces_before_drive_probe(
    unsafe_path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    drive_probes: list[str] = []
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetDriveTypeW",
        lambda root: drive_probes.append(str(root)) or 3,
    )

    with pytest.raises(DualLiveWindowsError, match="dual_live_path_not_fixed_local"):
        dual_live_windows.assert_local_fixed_path_before_touch(
            unsafe_path,
            code="dual_live_path_not_fixed_local",
        )

    assert drive_probes == []


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
def test_local_fixed_path_rejects_mapped_drive_before_path_touch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probes: list[str] = []
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetDriveTypeW",
        lambda root: probes.append(str(root)) or 4,
    )

    with pytest.raises(DualLiveWindowsError, match="dual_live_path_not_fixed_local"):
        dual_live_windows.assert_local_fixed_path_before_touch(
            r"z:\proof\evidence",
            code="dual_live_path_not_fixed_local",
        )

    assert probes == ["z:\\"]


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
def test_local_fixed_path_accepts_drive_letter_on_fixed_volume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probes: list[str] = []
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetDriveTypeW",
        lambda root: probes.append(str(root)) or 3,
    )

    result = dual_live_windows.assert_local_fixed_path_before_touch(
        r"C:\proof\evidence",
        code="dual_live_path_not_fixed_local",
    )

    assert result == Path(r"C:\proof\evidence")
    assert probes == ["C:\\"]


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
def test_fixed_local_ancestor_walk_rejects_reparse_before_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probes: list[str] = []
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetDriveTypeW",
        lambda _root: 3,
    )

    def attributes(path: str) -> int:
        probes.append(str(path))
        return 0x400 if str(path).casefold() == r"c:\proof" else 0x10

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetFileAttributesW",
        attributes,
        raising=False,
    )

    with pytest.raises(DualLiveWindowsError, match="dual_live_path_not_fixed_local"):
        dual_live_windows.assert_fixed_local_no_reparse_path_before_open(
            r"C:\proof\evidence\index.json",
            code="dual_live_path_not_fixed_local",
        )

    assert probes == ["C:\\", r"C:\proof"]


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
def test_fixed_local_ancestor_walk_fails_closed_on_missing_descendant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetDriveTypeW",
        lambda _root: 3,
    )
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetFileAttributesW",
        lambda _path: 0xFFFFFFFF,
        raising=False,
    )

    with pytest.raises(DualLiveWindowsError, match="dual_live_path_not_fixed_local"):
        dual_live_windows.assert_fixed_local_no_reparse_path_before_open(
            r"C:\missing\proof.db",
            code="dual_live_path_not_fixed_local",
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
@pytest.mark.parametrize(
    "final_path",
    (
        r"\\?\UNC\server\share\proof.db",
        r"\Device\Mup\server\share\proof.db",
        r"\\.\C:\proof.db",
    ),
)
def test_open_handle_rejects_remote_or_device_final_path(
    final_path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    drive_probes: list[str] = []
    monkeypatch.setattr(
        dual_live_windows,
        "_final_path_name_from_handle",
        lambda _handle, *, code: final_path,
        raising=False,
    )
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetDriveTypeW",
        lambda root: drive_probes.append(str(root)) or 3,
    )

    with pytest.raises(DualLiveWindowsError, match="dual_live_path_not_fixed_local"):
        dual_live_windows.assert_open_handle_local_fixed(
            123,
            expected_path=Path(r"C:\proof.db"),
            code="dual_live_path_not_fixed_local",
        )

    assert drive_probes == []


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
def test_open_handle_accepts_matching_fixed_local_final_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dual_live_windows,
        "_final_path_name_from_handle",
        lambda _handle, *, code: r"\\?\C:\proof.db",
        raising=False,
    )
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetDriveTypeW",
        lambda _root: 3,
    )

    assert dual_live_windows.assert_open_handle_local_fixed(
        123,
        expected_path=Path(r"c:\PROOF.db"),
        code="dual_live_path_not_fixed_local",
    ) == Path(r"C:\proof.db")


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_nonlocal_executable_volume_refuses_before_child_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "python.exe"
    shutil.copyfile(sys.executable, executable)
    marker = tmp_path / "forbidden-marker"
    read_handle, write_handle = _inheritable_pipe()
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetDriveTypeW",
        lambda _: 4,
        raising=False,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError, match="dual_live_executable_invalid"
        ):
            create_child_in_job(
                argv=(str(executable), "-B", "-c", "raise SystemExit(0)"),
                environment=_job_environment(),
                inherited_handles=(write_handle,),
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
    finally:
        dual_live_windows._kernel32.CloseHandle(read_handle)
        dual_live_windows._kernel32.CloseHandle(write_handle)
    assert not marker.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_executable_handle_denies_write_and_replace_through_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "python.exe"
    replacement = tmp_path / "replacement.exe"
    shutil.copyfile(sys.executable, executable)
    shutil.copyfile(sys.executable, replacement)
    read_handle, write_handle = _inheritable_pipe()
    observed: dict[str, bool] = {}

    def probe_create_process(*args: object) -> int:
        write_probe = dual_live_windows._kernel32.CreateFileW(
            str(executable),
            0x40000000,
            0x7,
            None,
            3,
            0x80,
            None,
        )
        observed["write_denied"] = write_probe in (
            None,
            ctypes.c_void_p(-1).value,
        )
        if not observed["write_denied"]:
            dual_live_windows._kernel32.CloseHandle(write_probe)
        try:
            os.replace(replacement, executable)
        except OSError:
            observed["replace_denied"] = True
        else:
            observed["replace_denied"] = False
        try:
            shutil.copyfile(replacement, executable)
        except OSError:
            observed["restore_denied"] = True
        else:
            observed["restore_denied"] = False
        ctypes.set_last_error(5)
        return 0

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "CreateProcessW",
        probe_create_process,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError, match="dual_live_job_admission_refused"
        ):
            create_child_in_job(
                argv=(str(executable), "-B", "-c", "raise SystemExit(0)"),
                environment=_job_environment(),
                inherited_handles=(write_handle,),
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
    finally:
        dual_live_windows._kernel32.CloseHandle(read_handle)
        dual_live_windows._kernel32.CloseHandle(write_handle)
    assert observed == {
        "write_denied": True,
        "replace_denied": True,
        "restore_denied": True,
    }


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_missing_owner_table_api_refuses_before_child_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "forbidden-marker"
    read_handle, write_handle = _inheritable_pipe()
    monkeypatch.setattr(dual_live_windows._iphlpapi, "GetExtendedTcpTable", None)
    try:
        with pytest.raises(
            DualLiveWindowsError, match="dual_live_job_unsupported"
        ):
            create_child_in_job(
                argv=_marker_argv(marker),
                environment=_job_environment(),
                inherited_handles=(write_handle,),
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
    finally:
        dual_live_windows._kernel32.CloseHandle(read_handle)
        dual_live_windows._kernel32.CloseHandle(write_handle)
    assert not marker.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_platform_absence_refuses_before_child_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "forbidden-marker"
    read_handle, write_handle = _inheritable_pipe()
    kernel32 = dual_live_windows._kernel32
    monkeypatch.setattr(dual_live_windows, "_kernel32", None)
    try:
        with pytest.raises(
            DualLiveWindowsError, match="dual_live_windows_unsupported"
        ):
            create_child_in_job(
                argv=_marker_argv(marker),
                environment=_job_environment(),
                inherited_handles=(write_handle,),
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
    finally:
        kernel32.CloseHandle(read_handle)
        kernel32.CloseHandle(write_handle)
    assert not marker.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_allows_only_genuine_pipe_and_event_handles() -> None:
    create_event = dual_live_windows._kernel32.CreateEventW
    create_event.argtypes = (
        ctypes.c_void_p,
        ctypes.wintypes.BOOL,
        ctypes.wintypes.BOOL,
        ctypes.wintypes.LPCWSTR,
    )
    create_event.restype = ctypes.wintypes.HANDLE
    event_handle = int(create_event(None, False, False, None))
    read_handle, write_handle = _inheritable_pipe()
    assert event_handle
    assert dual_live_windows._kernel32.SetHandleInformation(
        event_handle,
        dual_live_windows._HANDLE_FLAG_INHERIT,
        dual_live_windows._HANDLE_FLAG_INHERIT,
    )
    child_code = """
import ctypes
import sys

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
pipe_ok = kernel32.GetFileType(ctypes.c_void_p(int(sys.argv[1]))) == 3
event_wait = kernel32.WaitForSingleObject(ctypes.c_void_p(int(sys.argv[2])), 0)
raise SystemExit(0 if pipe_ok and event_wait == 0x102 else 9)
"""
    try:
        child = create_child_in_job(
            argv=(
                sys.executable,
                "-B",
                "-c",
                child_code,
                str(write_handle),
                str(event_handle),
            ),
            environment=_job_environment(),
            inherited_handles=(write_handle, event_handle),
            runtime_instance_id=RUNTIME_INSTANCE_ID,
            wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
        )
        with child:
            assert child.wait(5) == 0
    finally:
        dual_live_windows._kernel32.CloseHandle(read_handle)
        dual_live_windows._kernel32.CloseHandle(write_handle)
        dual_live_windows._kernel32.CloseHandle(event_handle)


def _make_inheritable_disallowed_handle(
    kind: str,
    tmp_path: Path,
) -> tuple[int, object | None]:
    kernel32 = dual_live_windows._kernel32
    keepalive: object | None = None
    if kind == "token":
        value = ctypes.c_void_p()
        assert kernel32.OpenProcessToken(
            kernel32.GetCurrentProcess(),
            dual_live_windows._TOKEN_QUERY,
            ctypes.byref(value),
        )
        handle = int(value.value)
    elif kind == "section":
        create_mapping = kernel32.CreateFileMappingW
        create_mapping.argtypes = (
            ctypes.wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.wintypes.DWORD,
            ctypes.wintypes.DWORD,
            ctypes.wintypes.DWORD,
            ctypes.wintypes.LPCWSTR,
        )
        create_mapping.restype = ctypes.wintypes.HANDLE
        handle = int(
            create_mapping(ctypes.c_void_p(-1), None, 0x04, 0, 4096, None)
        )
    elif kind == "file":
        path = tmp_path / "ordinary.bin"
        path.write_bytes(b"not a capability pipe")
        handle = int(
            kernel32.CreateFileW(
                str(path),
                0x80000000,
                0x7,
                None,
                3,
                0x80,
                None,
            )
        )
    elif kind == "socket":
        keepalive = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        handle = int(keepalive.fileno())
    elif kind == "job":
        handle = int(kernel32.CreateJobObjectW(None, None))
    elif kind == "process":
        handle = int(
            kernel32.OpenProcess(
                dual_live_windows._PROCESS_QUERY_LIMITED_INFORMATION,
                False,
                os.getpid(),
            )
        )
    elif kind == "thread":
        get_thread_id = kernel32.GetCurrentThreadId
        get_thread_id.argtypes = ()
        get_thread_id.restype = ctypes.wintypes.DWORD
        open_thread = kernel32.OpenThread
        open_thread.argtypes = (
            ctypes.wintypes.DWORD,
            ctypes.wintypes.BOOL,
            ctypes.wintypes.DWORD,
        )
        open_thread.restype = ctypes.wintypes.HANDLE
        handle = int(open_thread(0x0800, False, get_thread_id()))
    else:  # pragma: no cover - closed parametrization
        raise AssertionError(kind)
    assert handle
    assert kernel32.SetHandleInformation(
        handle,
        dual_live_windows._HANDLE_FLAG_INHERIT,
        dual_live_windows._HANDLE_FLAG_INHERIT,
    )
    return handle, keepalive


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize(
    "kind",
    ("token", "section", "file", "socket", "job", "process", "thread"),
)
def test_job_disallowed_inherited_capabilities_refuse_before_child_effect(
    tmp_path: Path,
    kind: str,
) -> None:
    marker = tmp_path / "forbidden-marker"
    handle, keepalive = _make_inheritable_disallowed_handle(kind, tmp_path)
    try:
        child: JobChild | None = None
        try:
            child = create_child_in_job(
                argv=_marker_argv(marker),
                environment=_job_environment(),
                inherited_handles=(handle,),
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
        except DualLiveWindowsError as exc:
            assert exc.code == "dual_live_job_inherited_handles_invalid"
        else:
            child.close()
            pytest.fail(f"{kind} capability was inherited")
    finally:
        if isinstance(keepalive, socket.socket):
            keepalive.close()
        else:
            dual_live_windows._kernel32.CloseHandle(handle)
    assert not marker.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_policy_readback_mismatch_refuses_before_child_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "forbidden-marker"
    read_handle, write_handle = _inheritable_pipe()
    original_query = dual_live_windows._kernel32.QueryInformationJobObject

    def mismatched_query(
        job_handle: int,
        information_class: int,
        information: object,
        information_length: int,
        returned_length: object,
    ) -> int:
        result = original_query(
            job_handle,
            information_class,
            information,
            information_length,
            returned_length,
        )
        if result and information_class == 9:
            policy = ctypes.cast(
                information,
                ctypes.POINTER(
                    dual_live_windows._JOBOBJECT_EXTENDED_LIMIT_INFORMATION
                ),
            ).contents
            policy.BasicLimitInformation.LimitFlags |= (
                dual_live_windows._JOB_OBJECT_LIMIT_BREAKAWAY_OK
            )
        return int(result)

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "QueryInformationJobObject",
        mismatched_query,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError, match="dual_live_job_policy_invalid"
        ):
            create_child_in_job(
                argv=_marker_argv(marker),
                environment=_job_environment(),
                inherited_handles=(write_handle,),
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
    finally:
        dual_live_windows._kernel32.CloseHandle(read_handle)
        dual_live_windows._kernel32.CloseHandle(write_handle)
    assert not marker.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_nested_job_incompatibility_refuses_without_child_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "forbidden-marker"
    original_configure = dual_live_windows._configure_job

    def configure_with_active_limit(job_handle: int) -> str:
        original_configure(job_handle)
        policy = dual_live_windows._JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        policy.BasicLimitInformation.LimitFlags = (
            dual_live_windows._JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | 0x8
        )
        policy.BasicLimitInformation.ActiveProcessLimit = 1
        assert dual_live_windows._kernel32.SetInformationJobObject(
            job_handle,
            9,
            ctypes.byref(policy),
            ctypes.sizeof(policy),
        )
        return hashlib.sha256(
            dual_live_windows._canonical_json_bytes(
                {"limit_flags": int(policy.BasicLimitInformation.LimitFlags)}
            )
        ).hexdigest()

    monkeypatch.setattr(
        dual_live_windows, "_configure_job", configure_with_active_limit
    )
    nested_code = """
import ctypes
import os
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from app.services import dual_live_windows as windows

security = windows._SECURITY_ATTRIBUTES(
    ctypes.sizeof(windows._SECURITY_ATTRIBUTES), None, True
)
read_handle = ctypes.c_void_p()
write_handle = ctypes.c_void_p()
if not windows._kernel32.CreatePipe(
    ctypes.byref(read_handle),
    ctypes.byref(write_handle),
    ctypes.byref(security),
    0,
):
    raise SystemExit(20)
windows._kernel32.SetHandleInformation(read_handle, 1, 0)
try:
    try:
        nested = windows.create_child_in_job(
            argv=(
                sys.executable,
                "-B",
                "-c",
                "from pathlib import Path; Path(__import__('sys').argv[1]).touch()",
                sys.argv[2],
            ),
            environment=dict(os.environ),
            inherited_handles=(int(write_handle.value),),
            runtime_instance_id=sys.argv[3],
            wrapper_nonce_sha256=sys.argv[4],
        )
    except windows.DualLiveWindowsError as exc:
        correct = exc.code == "dual_live_job_admission_refused"
        raise SystemExit(0 if correct and not Path(sys.argv[2]).exists() else 21)
    else:
        nested.terminate_tree()
        nested.close()
        raise SystemExit(22)
finally:
    windows._kernel32.CloseHandle(read_handle)
    windows._kernel32.CloseHandle(write_handle)
"""
    child = _create_test_child(
        nested_code,
        str(BACKEND),
        str(marker),
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    with child:
        assert child.wait(5) == 0
        _assert_quiescence_record(prove_child_quiescence(child))
    assert not marker.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_create_child_drains_unresolved_custody_before_executable_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel32 = dual_live_windows._kernel32
    original_close = kernel32.CloseHandle
    retained_handle, inherited_handle = _inheritable_pipe()
    allocation_calls: list[str] = []
    dual_live_windows._retain_owned_handle_for_retry(retained_handle)

    def retain_raw(handle: object) -> int:
        if int(handle) == retained_handle:
            ctypes.set_last_error(5)
            return 0
        return int(original_close(handle))

    def unexpected_allocation(_executable: str) -> object:
        allocation_calls.append("open-executable")
        raise AssertionError("allocation occurred before custody drain")

    monkeypatch.setattr(kernel32, "CloseHandle", retain_raw)
    monkeypatch.setattr(
        dual_live_windows,
        "_open_executable_custody",
        unexpected_allocation,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_handle_cleanup_failed",
        ):
            create_child_in_job(
                argv=(sys.executable, "-B", "-c", "raise SystemExit(0)"),
                environment=_job_environment(),
                inherited_handles=(inherited_handle,),
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
        assert allocation_calls == []
        assert dual_live_windows._retained_owned_handles == {retained_handle}
    finally:
        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        dual_live_windows._retry_retained_owned_handles()
        original_close(inherited_handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_pre_provisional_raw_close_failure_retains_exact_custody(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class PolicyProbe(RuntimeError):
        pass

    kernel32 = dual_live_windows._kernel32
    original_create_job = kernel32.CreateJobObjectW
    original_close = kernel32.CloseHandle
    captured_job: int | None = None

    def capture_job(*args: object) -> int:
        nonlocal captured_job
        captured_job = int(original_create_job(*args))
        return captured_job

    def fail_policy(_job_handle: int) -> str:
        raise PolicyProbe("pre-provisional policy failure")

    def retain_job(handle: object) -> int:
        if captured_job is not None and int(handle) == captured_job:
            ctypes.set_last_error(5)
            return 0
        return int(original_close(handle))

    monkeypatch.setattr(kernel32, "CreateJobObjectW", capture_job)
    monkeypatch.setattr(dual_live_windows, "_configure_job", fail_policy)
    monkeypatch.setattr(kernel32, "CloseHandle", retain_job)
    read_handle, write_handle = _inheritable_pipe()
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_child_cleanup_failed",
        ) as exc:
            create_child_in_job(
                argv=(sys.executable, "-B", "-c", "raise SystemExit(0)"),
                environment=_job_environment(),
                inherited_handles=(write_handle,),
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
        assert isinstance(exc.value.__context__, PolicyProbe)
        assert captured_job is not None
        assert dual_live_windows._retained_owned_handles == {captured_job}
        flags = ctypes.wintypes.DWORD()
        assert kernel32.GetHandleInformation(captured_job, ctypes.byref(flags))

        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        dual_live_windows._retry_retained_owned_handles()
        assert dual_live_windows._retained_owned_handles == set()
        assert not kernel32.GetHandleInformation(captured_job, ctypes.byref(flags))
    finally:
        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        dual_live_windows._retry_retained_owned_handles()
        original_close(read_handle)
        original_close(write_handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("cleanup_failure", (None, "terminate", "job_close"))
def test_job_post_create_failure_has_checked_bounded_cleanup(
    cleanup_failure: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel32 = dual_live_windows._kernel32
    original_create_job = kernel32.CreateJobObjectW
    original_create_process = kernel32.CreateProcessW
    original_terminate = kernel32.TerminateJobObject
    original_wait = kernel32.WaitForSingleObject
    original_close = kernel32.CloseHandle
    captured: dict[str, int] = {}
    cleanup_waits: list[int] = []
    close_failed = False

    def capture_job(*args: object) -> int:
        handle = int(original_create_job(*args))
        captured["job"] = handle
        return handle

    def capture_process(*args: object) -> int:
        result = int(original_create_process(*args))
        if result:
            process_info = ctypes.cast(
                args[-1],
                ctypes.POINTER(dual_live_windows._PROCESS_INFORMATION),
            ).contents
            captured["process"] = int(process_info.hProcess)
            captured["observer"] = int(
                kernel32.OpenProcess(
                    dual_live_windows._PROCESS_QUERY_LIMITED_INFORMATION
                    | dual_live_windows._SYNCHRONIZE,
                    False,
                    int(process_info.dwProcessId),
                )
            )
            assert captured["observer"]
        return result

    def reject_membership(
        process_handle: object,
        job_handle: object,
        membership_pointer: object,
    ) -> int:
        del process_handle, job_handle
        ctypes.cast(
            membership_pointer,
            ctypes.POINTER(ctypes.wintypes.BOOL),
        ).contents.value = 0
        return 1

    def terminate(job_handle: object, exit_code: int) -> int:
        if cleanup_failure == "terminate":
            return 0
        return int(original_terminate(job_handle, exit_code))

    def wait(handle: object, timeout_ms: int) -> int:
        if int(handle) == captured.get("process"):
            cleanup_waits.append(timeout_ms)
        return int(original_wait(handle, timeout_ms))

    def close(handle: object) -> int:
        nonlocal close_failed
        if (
            cleanup_failure == "job_close"
            and int(handle) == captured.get("job")
            and not close_failed
        ):
            close_failed = True
            return 0
        return int(original_close(handle))

    monkeypatch.setattr(kernel32, "CreateJobObjectW", capture_job)
    monkeypatch.setattr(kernel32, "CreateProcessW", capture_process)
    monkeypatch.setattr(kernel32, "IsProcessInJob", reject_membership)
    monkeypatch.setattr(kernel32, "TerminateJobObject", terminate)
    monkeypatch.setattr(kernel32, "WaitForSingleObject", wait)
    monkeypatch.setattr(kernel32, "CloseHandle", close)
    read_handle, write_handle = _inheritable_pipe()
    try:
        expected = (
            "dual_live_job_admission_refused"
            if cleanup_failure is None
            else "dual_live_child_cleanup_failed"
        )
        with pytest.raises(DualLiveWindowsError, match=expected):
            create_child_in_job(
                argv=(sys.executable, "-B", "-c", "import time; time.sleep(30)"),
                environment=_job_environment(),
                inherited_handles=(write_handle,),
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
        assert cleanup_waits
        assert all(0 < timeout_ms <= 5_000 for timeout_ms in cleanup_waits)
        assert (
            original_wait(captured["observer"], 5_000)
            == dual_live_windows._WAIT_OBJECT_0
        )
    finally:
        original_close(read_handle)
        original_close(write_handle)
        observer = captured.get("observer")
        if observer:
            original_close(observer)
        job_handle = captured.get("job")
        if job_handle:
            flags = ctypes.wintypes.DWORD()
            if kernel32.GetHandleInformation(job_handle, ctypes.byref(flags)):
                original_terminate(
                    job_handle,
                    dual_live_windows._TERMINATE_EXIT_CODE,
                )
                original_close(job_handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_persistent_provisional_failure_retains_owner_until_exact_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel32 = dual_live_windows._kernel32
    original_create_job = kernel32.CreateJobObjectW
    original_create_process = kernel32.CreateProcessW
    original_terminate = kernel32.TerminateJobObject
    original_close = kernel32.CloseHandle
    captured: dict[str, int] = {}

    def capture_job(*args: object) -> int:
        captured["job"] = int(original_create_job(*args))
        return captured["job"]

    def capture_process(*args: object) -> int:
        result = int(original_create_process(*args))
        if result:
            process_info = ctypes.cast(
                args[-1],
                ctypes.POINTER(dual_live_windows._PROCESS_INFORMATION),
            ).contents
            captured["process"] = int(process_info.hProcess)
            captured["thread"] = int(process_info.hThread)
            captured["observer"] = int(
                kernel32.OpenProcess(
                    dual_live_windows._PROCESS_QUERY_LIMITED_INFORMATION
                    | dual_live_windows._SYNCHRONIZE,
                    False,
                    int(process_info.dwProcessId),
                )
            )
            assert captured["observer"]
        return result

    def reject_membership(
        _process_handle: object,
        _job_handle: object,
        membership_pointer: object,
    ) -> int:
        ctypes.cast(
            membership_pointer,
            ctypes.POINTER(ctypes.wintypes.BOOL),
        ).contents.value = 0
        return 1

    def fail_termination(job_handle: object, _exit_code: int) -> int:
        if int(job_handle) == captured.get("job"):
            ctypes.set_last_error(5)
            return 0
        return int(original_terminate(job_handle, _exit_code))

    def retain_provisional(handle: object) -> int:
        if int(handle) in {
            captured.get("job"),
            captured.get("process"),
            captured.get("thread"),
        }:
            ctypes.set_last_error(5)
            return 0
        return int(original_close(handle))

    monkeypatch.setattr(kernel32, "CreateJobObjectW", capture_job)
    monkeypatch.setattr(kernel32, "CreateProcessW", capture_process)
    monkeypatch.setattr(kernel32, "IsProcessInJob", reject_membership)
    monkeypatch.setattr(kernel32, "TerminateJobObject", fail_termination)
    monkeypatch.setattr(kernel32, "CloseHandle", retain_provisional)
    read_handle, write_handle = _inheritable_pipe()
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_child_cleanup_failed",
        ):
            create_child_in_job(
                argv=(sys.executable, "-B", "-c", "import time; time.sleep(30)"),
                environment=_job_environment(),
                inherited_handles=(write_handle,),
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
        assert len(dual_live_windows._failed_provisional_owners) == 1
        owner = dual_live_windows._failed_provisional_owners[0]
        assert owner.job_handle == captured["job"]
        assert owner.process_handle == captured["process"]
        assert owner.thread_handle == captured["thread"]
        flags = ctypes.wintypes.DWORD()
        assert all(
            kernel32.GetHandleInformation(handle, ctypes.byref(flags))
            for handle in (owner.job_handle, owner.process_handle, owner.thread_handle)
        )

        monkeypatch.setattr(kernel32, "TerminateJobObject", original_terminate)
        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        dual_live_windows._retry_failed_provisional_owners()
        assert dual_live_windows._failed_provisional_owners == []
        assert owner.released
        assert all(
            not kernel32.GetHandleInformation(handle, ctypes.byref(flags))
            for handle in (
                captured["job"],
                captured["process"],
                captured["thread"],
            )
        )
        assert (
            kernel32.WaitForSingleObject(captured["observer"], 5_000)
            == dual_live_windows._WAIT_OBJECT_0
        )
    finally:
        monkeypatch.setattr(kernel32, "TerminateJobObject", original_terminate)
        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        for owner in tuple(
            getattr(dual_live_windows, "_failed_provisional_owners", ())
        ):
            owner.cleanup_after_failure()
        flags = ctypes.wintypes.DWORD()
        job_handle = captured.get("job")
        if job_handle and kernel32.GetHandleInformation(job_handle, ctypes.byref(flags)):
            original_terminate(job_handle, dual_live_windows._TERMINATE_EXIT_CODE)
        for role in ("thread", "process", "job", "observer"):
            handle = captured.get(role)
            if handle and kernel32.GetHandleInformation(handle, ctypes.byref(flags)):
                original_close(handle)
        original_close(read_handle)
        original_close(write_handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_abrupt_wrapper_close_kills_job_child() -> None:
    wrapper_code = """
import ctypes
import json
import os
import sys

sys.path.insert(0, sys.argv[1])
from app.services import dual_live_windows as windows

security = windows._SECURITY_ATTRIBUTES(
    ctypes.sizeof(windows._SECURITY_ATTRIBUTES), None, True
)
read_handle = ctypes.c_void_p()
write_handle = ctypes.c_void_p()
if not windows._kernel32.CreatePipe(
    ctypes.byref(read_handle),
    ctypes.byref(write_handle),
    ctypes.byref(security),
    0,
):
    raise SystemExit(30)
windows._kernel32.SetHandleInformation(read_handle, 1, 0)
try:
    child = windows.create_child_in_job(
        argv=(sys.executable, "-B", "-c", "import time; time.sleep(30)"),
        environment=dict(os.environ),
        inherited_handles=(int(write_handle.value),),
        runtime_instance_id=sys.argv[2],
        wrapper_nonce_sha256=sys.argv[3],
    )
finally:
    windows._kernel32.CloseHandle(read_handle)
    windows._kernel32.CloseHandle(write_handle)
print(json.dumps({
    "pid": child.pid,
    "process_creation_identity_sha256": child.process_creation_identity_sha256,
}), flush=True)
sys.stdin.buffer.read()
os._exit(0)
"""
    wrapper = subprocess.Popen(
        (
            sys.executable,
            "-B",
            "-c",
            wrapper_code,
            str(BACKEND),
            RUNTIME_INSTANCE_ID,
            WRAPPER_NONCE_SHA,
        ),
        cwd=ROOT,
        env=_job_environment(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    process_handle = 0
    try:
        assert wrapper.stdout is not None
        record = json.loads(wrapper.stdout.readline())
        process_handle = int(
            dual_live_windows._kernel32.OpenProcess(
                dual_live_windows._PROCESS_QUERY_LIMITED_INFORMATION
                | dual_live_windows._SYNCHRONIZE,
                False,
                int(record["pid"]),
            )
        )
        assert process_handle
        creation_filetime = dual_live_windows._process_creation_filetime(
            process_handle
        )
        assert record["process_creation_identity_sha256"] == hashlib.sha256(
            dual_live_windows._canonical_json_bytes(
                {"creation_filetime": creation_filetime, "pid": record["pid"]}
            )
        ).hexdigest()
        assert wrapper.stdin is not None
        wrapper.stdin.close()
        assert wrapper.wait(5) == 0
        assert (
            dual_live_windows._kernel32.WaitForSingleObject(process_handle, 5000)
            == dual_live_windows._WAIT_OBJECT_0
        )
    finally:
        if wrapper.poll() is None:
            wrapper.kill()
            wrapper.wait(5)
        if process_handle:
            dual_live_windows._kernel32.CloseHandle(process_handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owner_pid_tables_observe_all_loopback_socket_families() -> None:
    socket_code = """
import msvcrt
import os
import socket
import sys
import time

sockets = []
for family, kind, address in (
    (socket.AF_INET, socket.SOCK_STREAM, ("127.0.0.1", 0)),
    (socket.AF_INET6, socket.SOCK_STREAM, ("::1", 0)),
    (socket.AF_INET, socket.SOCK_DGRAM, ("127.0.0.1", 0)),
    (socket.AF_INET6, socket.SOCK_DGRAM, ("::1", 0)),
):
    sock = socket.socket(family, kind)
    if family == socket.AF_INET6:
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    sock.bind(address)
    if kind == socket.SOCK_STREAM:
        sock.listen(1)
    sockets.append(sock)
descriptor = msvcrt.open_osfhandle(int(sys.argv[1]), os.O_WRONLY)
os.write(descriptor, b"1")
os.close(descriptor)
time.sleep(30)
"""
    child, signal_handle = _create_signaling_test_child(socket_code)
    try:
        _read_child_signal(signal_handle, child)
        deadline = time.monotonic() + 5
        stable_sample: tuple[tuple[object, ...], ...] = ()
        while time.monotonic() < deadline:
            first = dual_live_windows._socket_sample(frozenset((child.pid,)))
            second = dual_live_windows._socket_sample(frozenset((child.pid,)))
            if first == second and {int(row[0]) for row in first} == {0, 1, 2, 3}:
                stable_sample = first
                break
            time.sleep(0.01)
        assert stable_sample
        assert all(int(row[-1]) == child.pid for row in stable_sample)
        with pytest.raises(
            DualLiveWindowsError, match="dual_live_child_not_quiescent"
        ):
            prove_child_quiescence(child)
        child.terminate_tree()
        child.wait(5)
        _assert_quiescence_record(prove_child_quiescence(child))
    finally:
        if child._job_handle is not None:
            try:
                child.terminate_tree()
            except DualLiveWindowsError:
                pass
        child.close()


def _single_axis_socket_sample(kind: str, pid: int) -> tuple[tuple[object, ...], ...]:
    prohibited_state = WINDOWS_MIB_TCP_STATES.index("MIB_TCP_STATE_ESTAB") + 1
    if kind == "tcp4":
        return ((0, prohibited_state, 0, 0, 0, 0, pid),)
    if kind == "tcp6":
        return ((1, prohibited_state, bytes(16), 0, 0, bytes(16), 0, 0, pid),)
    if kind == "udp4":
        return ((2, 0, 0, pid),)
    if kind == "udp6":
        return ((3, bytes(16), 0, 0, pid),)
    if kind == "invalid_tcp_state":
        return ((0, len(WINDOWS_MIB_TCP_STATES) + 1, 0, 0, 0, 0, pid),)
    raise AssertionError(kind)  # pragma: no cover - closed parametrization


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize(
    ("kind", "error_code"),
    (
        ("tcp4", "dual_live_child_not_quiescent"),
        ("tcp6", "dual_live_child_not_quiescent"),
        ("udp4", "dual_live_child_not_quiescent"),
        ("udp6", "dual_live_child_not_quiescent"),
        ("invalid_tcp_state", "dual_live_quiescence_indeterminate"),
    ),
)
def test_job_zero_socket_sample_single_axis_is_classified(
    kind: str,
    error_code: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_classifier = dual_live_windows._classify_socket_sample
    child = _create_test_child("raise SystemExit(0)")
    with child:
        assert child.wait(5) == 0
        sample = _single_axis_socket_sample(kind, child.pid)
        classified: list[tuple[tuple[object, ...], ...]] = []

        def classify(
            rows: tuple[tuple[object, ...], ...],
        ) -> tuple[dict[str, int], dict[str, int], int, int]:
            classified.append(rows)
            return original_classifier(rows)

        monkeypatch.setattr(dual_live_windows, "_socket_sample", lambda _: sample)
        monkeypatch.setattr(
            dual_live_windows,
            "_classify_socket_sample",
            classify,
        )
        with pytest.raises(DualLiveWindowsError, match=error_code):
            prove_child_quiescence(child)
        assert classified == [sample]


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_real_tcp4_time_wait_is_allowed_after_child_exit() -> None:
    time_wait_code = """
import msvcrt
import os
import socket
import sys
import time

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("127.0.0.1", 0))
server.listen(1)
client = socket.create_connection(server.getsockname())
accepted, _ = server.accept()
client.shutdown(socket.SHUT_WR)
accepted.recv(1)
client.close()
accepted.close()
server.close()
descriptor = msvcrt.open_osfhandle(int(sys.argv[1]), os.O_WRONLY)
os.write(descriptor, b"1")
os.close(descriptor)
time.sleep(1)
"""
    state_number = WINDOWS_MIB_TCP_STATES.index("MIB_TCP_STATE_TIME_WAIT") + 1
    baseline = sum(
        1
        for row in dual_live_windows._owner_table_rows(
            family=dual_live_windows._AF_INET,
            protocol="tcp",
        )
        if int(row[0]) == state_number
    )
    child, signal_handle = _create_signaling_test_child(time_wait_code)
    with child:
        _read_child_signal(signal_handle, child)
        deadline = time.monotonic() + 5
        observed = False
        while time.monotonic() < deadline:
            rows = dual_live_windows._owner_table_rows(
                family=dual_live_windows._AF_INET,
                protocol="tcp",
            )
            if sum(1 for row in rows if int(row[0]) == state_number) > baseline:
                observed = True
                break
            time.sleep(0.01)
        assert observed
        assert child.wait(5) == 0
        record = prove_child_quiescence(child)
        _assert_quiescence_record(record)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_attributed_time_wait_only_is_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child = _create_test_child("raise SystemExit(0)")
    with child:
        assert child.wait(5) == 0
        state_number = WINDOWS_MIB_TCP_STATES.index(
            "MIB_TCP_STATE_TIME_WAIT"
        ) + 1
        sample = ((0, state_number, 0, 0, 0, 0, child.pid),)
        monkeypatch.setattr(dual_live_windows, "_socket_sample", lambda _: sample)
        record = prove_child_quiescence(child)
        _assert_quiescence_record(record)
        tcp4_counts = record["tcp4_state_counts"]
        assert isinstance(tcp4_counts, dict)
        assert tcp4_counts["MIB_TCP_STATE_TIME_WAIT"] == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owner_table_buffer_growth_is_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def growing_table(
        buffer: object,
        size_pointer: object,
        ordered: bool,
        family: int,
        table_class: int,
        reserved: int,
    ) -> int:
        nonlocal calls
        del ordered, family, table_class, reserved
        calls += 1
        size = ctypes.cast(
            size_pointer, ctypes.POINTER(ctypes.wintypes.ULONG)
        ).contents
        if buffer is None:
            size.value = 8
            return dual_live_windows._ERROR_INSUFFICIENT_BUFFER
        if calls == 2:
            assert size.value == 8
            size.value = 64
            return dual_live_windows._ERROR_INSUFFICIENT_BUFFER
        ctypes.c_uint32.from_buffer(buffer, 0).value = 0
        size.value = 4
        return 0

    monkeypatch.setattr(
        dual_live_windows._iphlpapi,
        "GetExtendedTcpTable",
        growing_table,
    )
    assert dual_live_windows._owner_table_rows(
        family=dual_live_windows._AF_INET,
        protocol="tcp",
    ) == ()
    assert calls == 3


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owner_table_null_probe_requires_insufficient_buffer_exactly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def wrong_null_status(
        buffer: object,
        size_pointer: object,
        ordered: bool,
        family: int,
        table_class: int,
        reserved: int,
    ) -> int:
        del ordered, family, table_class, reserved
        size = ctypes.cast(
            size_pointer, ctypes.POINTER(ctypes.wintypes.ULONG)
        ).contents
        size.value = 4
        if buffer is None:
            return 0
        ctypes.c_uint32.from_buffer(buffer, 0).value = 0
        return 0

    monkeypatch.setattr(
        dual_live_windows._iphlpapi,
        "GetExtendedTcpTable",
        wrong_null_status,
    )
    with pytest.raises(
        DualLiveWindowsError, match="dual_live_quiescence_indeterminate"
    ):
        dual_live_windows._owner_table_rows(
            family=dual_live_windows._AF_INET,
            protocol="tcp",
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("failure_mode", ["status", "truncated"])
def test_owner_table_bad_status_or_truncation_is_indeterminate(
    failure_mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def bad_table(
        buffer: object,
        size_pointer: object,
        ordered: bool,
        family: int,
        table_class: int,
        reserved: int,
    ) -> int:
        del ordered, family, table_class, reserved
        size = ctypes.cast(
            size_pointer, ctypes.POINTER(ctypes.wintypes.ULONG)
        ).contents
        if failure_mode == "status":
            return 5
        if buffer is None:
            size.value = 4
            return dual_live_windows._ERROR_INSUFFICIENT_BUFFER
        ctypes.c_uint32.from_buffer(buffer, 0).value = 1
        size.value = 4
        return 0

    monkeypatch.setattr(
        dual_live_windows._iphlpapi,
        "GetExtendedTcpTable",
        bad_table,
    )
    with pytest.raises(
        DualLiveWindowsError, match="dual_live_quiescence_indeterminate"
    ):
        dual_live_windows._owner_table_rows(
            family=dual_live_windows._AF_INET,
            protocol="tcp",
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owner_table_snapshot_churn_is_indeterminate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child = _create_test_child("raise SystemExit(0)")
    with child:
        assert child.wait(5) == 0
        samples = iter(((), ((2, 0, 0, child.pid),)))
        monkeypatch.setattr(
            dual_live_windows,
            "_socket_sample",
            lambda _: next(samples),
        )
        with pytest.raises(
            DualLiveWindowsError, match="dual_live_quiescence_indeterminate"
        ):
            prove_child_quiescence(child)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_pid_occupancy_is_bound_before_between_and_after_socket_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child = _create_test_child("raise SystemExit(0)")
    with child:
        assert child.wait(5) == 0
        events: list[str] = []

        def occupancy(_: JobChild) -> None:
            events.append("occupancy")

        def socket_sample(_: frozenset[int]) -> tuple[tuple[object, ...], ...]:
            events.append("socket")
            return ()

        monkeypatch.setattr(
            dual_live_windows,
            "_validate_fresh_pid_occupancy",
            occupancy,
        )
        monkeypatch.setattr(dual_live_windows, "_socket_sample", socket_sample)
        _assert_quiescence_record(prove_child_quiescence(child))
        assert events == [
            "occupancy",
            "socket",
            "occupancy",
            "socket",
            "occupancy",
        ]


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_fresh_pid_occupancy_allows_no_current_occupant() -> None:
    child = _create_test_child("raise SystemExit(0)")
    with child:
        assert child.wait(5) == 0
        dual_live_windows._validate_fresh_pid_occupancy(child)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
@pytest.mark.parametrize("mode", ("same_creation", "different_creation", "denied"))
def test_job_fresh_pid_occupancy_classifies_creation_identity(
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child = _create_test_child("raise SystemExit(0)")
    with child:
        assert child.wait(5) == 0
        assert child._creation_filetime is not None
        sentinel = 0x7FFFFFF1
        original_get_pid = dual_live_windows._kernel32.GetProcessId
        original_creation = dual_live_windows._process_creation_filetime
        original_close = dual_live_windows._kernel32.CloseHandle

        def open_process(*args: object) -> int:
            del args
            if mode == "denied":
                ctypes.set_last_error(5)
                return 0
            return sentinel

        def get_pid(handle: object) -> int:
            return child.pid if int(handle) == sentinel else int(original_get_pid(handle))

        def creation(handle: int) -> int:
            if handle == sentinel:
                return child._creation_filetime + int(mode == "different_creation")
            return original_creation(handle)

        def close(handle: object) -> int:
            return 1 if int(handle) == sentinel else int(original_close(handle))

        monkeypatch.setattr(dual_live_windows._kernel32, "OpenProcess", open_process)
        monkeypatch.setattr(dual_live_windows._kernel32, "GetProcessId", get_pid)
        monkeypatch.setattr(dual_live_windows, "_process_creation_filetime", creation)
        monkeypatch.setattr(dual_live_windows._kernel32, "CloseHandle", close)
        if mode == "same_creation":
            dual_live_windows._validate_fresh_pid_occupancy(child)
        else:
            with pytest.raises(
                DualLiveWindowsError, match="dual_live_quiescence_indeterminate"
            ):
                dual_live_windows._validate_fresh_pid_occupancy(child)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_child_close_failure_is_reported_and_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child = _create_test_child("import time; time.sleep(30)")
    assert child._job_handle is not None
    job_handle = child._job_handle
    original_close = dual_live_windows._kernel32.CloseHandle
    failed_once = False
    retry_completed = False

    def fail_job_close_once(handle: object) -> int:
        nonlocal failed_once
        handle_value = int(handle.value) if hasattr(handle, "value") else int(handle)
        if handle_value == job_handle and not failed_once:
            failed_once = True
            return 0
        return int(original_close(handle))

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "CloseHandle",
        fail_job_close_once,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError, match="dual_live_child_cleanup_failed"
        ):
            child.close()
        assert not child._closed
        child.close()
        retry_completed = True
        assert child._closed
    finally:
        if not retry_completed:
            dual_live_windows._kernel32.TerminateJobObject(
                job_handle, dual_live_windows._TERMINATE_EXIT_CODE
            )
            original_close(job_handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_child_close_kills_process_and_closes_owned_handles() -> None:
    child = _create_test_child("import time; time.sleep(30)")
    assert child._job_handle is not None and child._process_handle is not None
    job_handle = child._job_handle
    process_handle = child._process_handle
    observer_handle = int(
        dual_live_windows._kernel32.OpenProcess(
            dual_live_windows._PROCESS_QUERY_LIMITED_INFORMATION
            | dual_live_windows._SYNCHRONIZE,
            False,
            child.pid,
        )
    )
    assert observer_handle
    try:
        child.close()
        assert (
            dual_live_windows._kernel32.WaitForSingleObject(
                observer_handle, 5000
            )
            == dual_live_windows._WAIT_OBJECT_0
        )
        for closed_handle in (job_handle, process_handle):
            flags = ctypes.wintypes.DWORD()
            ctypes.set_last_error(0)
            assert not dual_live_windows._kernel32.GetHandleInformation(
                closed_handle, ctypes.byref(flags)
            )
            assert ctypes.get_last_error() == 6
        child.close()
    finally:
        dual_live_windows._kernel32.CloseHandle(observer_handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_child_timeout_then_tree_termination_reaches_quiescence() -> None:
    child = _create_test_child("import time; time.sleep(30)")
    with child:
        assert child.poll_exit(0.01) is None
        with pytest.raises(DualLiveWindowsError, match="dual_live_child_timeout"):
            child.wait(0.01)
        child.terminate_tree()
        exit_code = child.poll_exit(5)
        assert isinstance(exit_code, int)
        assert child.wait(0) == exit_code
        _assert_quiescence_record(prove_child_quiescence(child))


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_retain_then_terminate_kills_after_retention_failure_and_poison_proof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child = _create_test_child("import time; time.sleep(30)")
    original_stable = dual_live_windows._stable_job_process_ids

    def retention_failure(_job_handle: int) -> tuple[int, ...]:
        raise DualLiveWindowsError("dual_live_quiescence_indeterminate")

    try:
        monkeypatch.setattr(
            dual_live_windows,
            "_stable_job_process_ids",
            retention_failure,
        )
        child.retain_then_terminate_tree()
        exit_code = child.poll_exit(5)
        assert isinstance(exit_code, int)

        monkeypatch.setattr(
            dual_live_windows,
            "_stable_job_process_ids",
            original_stable,
        )
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_quiescence_indeterminate",
        ):
            prove_child_quiescence(child)
    finally:
        if child._job_handle is not None:
            try:
                child.terminate_tree()
            except DualLiveWindowsError:
                pass
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_concurrent_retain_then_terminate_is_serialized_without_handle_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_lock = threading.Lock()
    active_calls = 0
    maximum_active = 0
    barrier = threading.Barrier(3)
    errors: list[BaseException] = []
    child = _create_test_child(
        "import subprocess, sys, time; "
        "subprocess.Popen([sys.executable, '-B', '-c', "
        "'import time; time.sleep(30)']); time.sleep(30)"
    )
    job_handle = child._job_handle
    assert job_handle is not None
    original_retain = dual_live_windows._retain_active_job_processes

    def observe_retain(
        target: JobChild,
        process_ids: tuple[int, ...],
    ) -> None:
        nonlocal active_calls, maximum_active
        with active_lock:
            active_calls += 1
            maximum_active = max(maximum_active, active_calls)
        try:
            time.sleep(0.05)
            original_retain(target, process_ids)
        finally:
            with active_lock:
                active_calls -= 1

    def terminate() -> None:
        barrier.wait()
        try:
            child.retain_then_terminate_tree()
        except BaseException as exc:
            errors.append(exc)

    monkeypatch.setattr(
        dual_live_windows,
        "_retain_active_job_processes",
        observe_retain,
    )
    callers = [threading.Thread(target=terminate) for _ in range(2)]
    before_close: int | None = None
    owned_handle_count = 0
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                if len(dual_live_windows._stable_job_process_ids(job_handle)) == 2:
                    break
            except DualLiveWindowsError:
                pass
            time.sleep(0.01)
        else:
            raise AssertionError("child and descendant did not stabilize")

        for caller in callers:
            caller.start()
        barrier.wait(timeout=5)
        for caller in callers:
            caller.join(timeout=5)

        assert all(not caller.is_alive() for caller in callers)
        assert errors == []
        assert maximum_active == 1
        assert isinstance(child.poll_exit(5), int)
        owned_handle_count = 1 + len(child._retained_processes)
        before_close = _process_handle_count()
    finally:
        if child._job_handle is not None:
            try:
                child.terminate_tree()
            except DualLiveWindowsError:
                pass
        child.close()

    assert before_close is not None
    assert _process_handle_count() == before_close - owned_handle_count


@pytest.mark.parametrize(
    "timeout",
    (True, -1, float("inf"), float("nan"), "0"),
)
def test_job_child_poll_exit_preserves_wait_timeout_validation(timeout: object) -> None:
    child = JobChild(1, "a" * 64, "b" * 64)

    with pytest.raises(
        DualLiveWindowsError,
        match="dual_live_windows_arguments_invalid",
    ):
        child.poll_exit(timeout)  # type: ignore[arg-type]


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_child_sleeping_grandchild_blocks_until_tree_terminated() -> None:
    child = _create_test_child(
        "import subprocess, sys; "
        "subprocess.Popen([sys.executable, '-B', '-c', "
        "'import time; time.sleep(30)'])"
    )
    with child:
        assert child.wait(5) == 0
        with pytest.raises(
            DualLiveWindowsError, match="dual_live_child_not_quiescent"
        ):
            prove_child_quiescence(child)
        child.terminate_tree()
        deadline = time.monotonic() + 5
        while True:
            try:
                record = prove_child_quiescence(child)
                break
            except DualLiveWindowsError as exc:
                if exc.code != "dual_live_child_not_quiescent" or time.monotonic() >= deadline:
                    raise
                time.sleep(0.01)
        _assert_quiescence_record(record)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_pid_list_resizes_until_all_members_are_returned() -> None:
    child = _create_test_child(
        "import subprocess, sys, time; "
        "children = [subprocess.Popen([sys.executable, '-B', '-c', "
        "'import time; time.sleep(30)']) for _ in range(12)]; "
        "time.sleep(30)"
    )
    try:
        deadline = time.monotonic() + 5
        pids: tuple[int, ...] = ()
        while len(pids) < 13 and time.monotonic() < deadline:
            try:
                pids = dual_live_windows._stable_job_process_ids(child._job_handle)
            except DualLiveWindowsError as exc:
                if exc.code != "dual_live_quiescence_indeterminate":
                    raise
                pids = ()
            time.sleep(0.01)
        assert len(pids) == 13
        assert child.pid in pids
    finally:
        child.terminate_tree()
        child.wait(5)
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_pid_list_success_with_truncated_return_length_is_indeterminate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def truncated_query(
        job_handle: int,
        information_class: int,
        information: object,
        information_length: int,
        returned_length: object,
    ) -> int:
        del job_handle, information_length
        assert information_class == 3
        ctypes.c_uint32.from_buffer(information, 0).value = 1
        ctypes.c_uint32.from_buffer(information, 4).value = 1
        ctypes.c_size_t.from_buffer(information, 8).value = os.getpid()
        ctypes.cast(
            returned_length, ctypes.POINTER(ctypes.wintypes.DWORD)
        ).contents.value = 4
        return 1

    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "QueryInformationJobObject",
        truncated_query,
    )
    with pytest.raises(
        DualLiveWindowsError, match="dual_live_quiescence_indeterminate"
    ):
        dual_live_windows._query_job_process_ids_once(1)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_process_identity_ambiguity_is_indeterminate() -> None:
    child = _create_test_child("raise SystemExit(0)")
    with child:
        assert child.wait(5) == 0
        assert child._creation_filetime is not None
        child._creation_filetime += 1
        with pytest.raises(
            DualLiveWindowsError, match="dual_live_quiescence_indeterminate"
        ):
            prove_child_quiescence(child)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_retained_process_handle_pid_mismatch_is_indeterminate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child = _create_test_child("raise SystemExit(0)")
    with child:
        assert child.wait(5) == 0
        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "GetProcessId",
            lambda _: child.pid + 4,
            raising=False,
        )
        with pytest.raises(
            DualLiveWindowsError, match="dual_live_quiescence_indeterminate"
        ):
            prove_child_quiescence(child)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_fresh_handle_new_creation_pid_substitution_is_indeterminate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child = _create_test_child("raise SystemExit(0)")
    with child:
        assert child.wait(5) == 0
        assert child._creation_filetime is not None
        substitute_handle = int(
            dual_live_windows._kernel32.OpenProcess(
                dual_live_windows._PROCESS_QUERY_LIMITED_INFORMATION
                | dual_live_windows._SYNCHRONIZE,
                False,
                os.getpid(),
            )
        )
        assert substitute_handle
        assert (
            dual_live_windows._process_creation_filetime(substitute_handle)
            != child._creation_filetime
        )
        original_get_pid = dual_live_windows._kernel32.GetProcessId

        def substituted_open(*args: object) -> int:
            del args
            return substitute_handle

        def substituted_pid(handle: object) -> int:
            if int(handle) == substitute_handle:
                return child.pid
            return int(original_get_pid(handle))

        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "OpenProcess",
            substituted_open,
        )
        monkeypatch.setattr(
            dual_live_windows._kernel32,
            "GetProcessId",
            substituted_pid,
        )
        try:
            with pytest.raises(
                DualLiveWindowsError, match="dual_live_quiescence_indeterminate"
            ):
                dual_live_windows._validate_fresh_pid_occupancy(child)
        finally:
            flags = ctypes.wintypes.DWORD()
            if dual_live_windows._kernel32.GetHandleInformation(
                substitute_handle,
                ctypes.byref(flags),
            ):
                dual_live_windows._kernel32.CloseHandle(substitute_handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_child_inherits_exact_handle_list_and_not_job_handle() -> None:
    security = dual_live_windows._SECURITY_ATTRIBUTES(
        ctypes.sizeof(dual_live_windows._SECURITY_ATTRIBUTES), None, True
    )
    included_event = dual_live_windows._kernel32.CreateEventW(
        ctypes.byref(security),
        True,
        False,
        None,
    )
    assert included_event
    excluded_event = None
    try:
        excluded_event = dual_live_windows._kernel32.CreateEventW(
            ctypes.byref(security),
            True,
            False,
            None,
        )
        assert excluded_event
        child_code = """
import ctypes
import sys

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
included = kernel32.SetEvent(ctypes.c_void_p(int(sys.argv[1])))
kernel32.SetEvent(ctypes.c_void_p(int(sys.argv[2])))
raise SystemExit(0 if included else 9)
"""
        child = create_child_in_job(
            argv=(
                sys.executable,
                "-B",
                "-c",
                child_code,
                str(included_event),
                str(excluded_event),
            ),
            environment=_job_environment(),
            inherited_handles=(int(included_event),),
            runtime_instance_id=RUNTIME_INSTANCE_ID,
            wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
        )
        with child:
            assert child.wait(5) == 0
            assert (
                dual_live_windows._kernel32.WaitForSingleObject(included_event, 0)
                == dual_live_windows._WAIT_OBJECT_0
            )
            assert (
                dual_live_windows._kernel32.WaitForSingleObject(excluded_event, 0)
                == dual_live_windows._WAIT_TIMEOUT
            )
            flags = ctypes.c_ulong()
            assert dual_live_windows._kernel32.GetHandleInformation(
                child._job_handle, ctypes.byref(flags)
            )
            assert flags.value & 1 == 0
    finally:
        for handle in (included_event, excluded_event):
            if handle:
                dual_live_windows._kernel32.CloseHandle(handle)


def _compact(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode()
        + os.linesep.encode()
    )


def _refusal(code: str) -> bytes:
    return _compact(
        {
            "schema_id": "project6.dual_live_gate_refusal.v1",
            "status": "REFUSED",
            "fresh_live": False,
            "evaluation_complete": False,
            "code": code,
        }
    )


def _load_gate_contract_module() -> object:
    module_name = f"dual_live_gate_contract_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
    return module


def _load_runner_contract_module() -> object:
    module_name = f"dual_live_run_contract_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(module_name, RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
    return module


def _runner_public_path_environment() -> dict[str, str]:
    return {
        "CONNECTOR_CAMPAIGN_DEFINITION_PATH": r"C:\proof\definition.json",
        "CONNECTOR_SCIENCEBASE_GRANT_PATH": r"C:\proof\sciencebase.json",
        "CONNECTOR_NRC_APS_GRANT_PATH": r"C:\proof\nrc.json",
        "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT": r"C:\proof\evidence",
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH": r"C:\proof\evidence\index.json",
        "DATABASE_URL": "sqlite:///C:/proof/proof.db",
        "STORAGE_DIR": r"C:\proof\storage",
    }


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
def test_runner_rejects_unc_before_kernel_or_backend_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner_contract_module()
    environ = _runner_public_path_environment()
    environ["CONNECTOR_CAMPAIGN_DEFINITION_PATH"] = r"\\server\share\definition.json"
    backend_effects: list[str] = []
    monkeypatch.setattr(runner, "_public_path_kernel32", lambda: backend_effects.append("kernel"))

    with pytest.raises(ValueError, match="dual_live_public_path_invalid"):
        runner._preflight_public_paths(environ)

    assert backend_effects == []


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
def test_runner_rejects_mapped_drive_before_ancestor_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner_contract_module()
    environ = _runner_public_path_environment()
    environ["STORAGE_DIR"] = r"z:\proof\storage"

    class Kernel:
        def GetDriveTypeW(self, root: str) -> int:
            return 4 if str(root).casefold() == "z:\\" else 3

        def GetFileAttributesW(self, _path: str) -> int:
            raise AssertionError("ancestor probe reached for mapped drive")

    monkeypatch.setattr(runner, "_public_path_kernel32", Kernel)

    with pytest.raises(ValueError, match="dual_live_public_path_invalid"):
        runner._preflight_public_paths(environ)


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
def test_runner_rejects_reparse_before_backend_path_or_runtime_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner_contract_module()
    environ = _runner_public_path_environment()
    before_sys_path = tuple(sys.path)

    class Kernel:
        def GetDriveTypeW(self, _root: str) -> int:
            return 3

        def GetFileAttributesW(self, path: str) -> int:
            return 0x400 if str(path).casefold() == r"c:\proof" else 0x10

    monkeypatch.setattr(runner, "_public_path_kernel32", Kernel)

    with pytest.raises(ValueError, match="dual_live_public_path_invalid"):
        runner._run_public_mode(
            ("--campaign-id", CAMPAIGN_ID, "--campaign-fingerprint", "a" * 64),
            environ=environ,
        )

    assert tuple(sys.path) == before_sys_path


def _evaluation_report(
    *, status: str = "INDETERMINATE", code: str = "test_indeterminate"
) -> dict[str, object]:
    report = build_indeterminate_dual_live_report(
        campaign_id=CAMPAIGN_ID,
        expected_campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        code=code,
    )
    if status == "PASS":
        report["status"] = "PASS"
        report["fresh_live"] = True
        report["evaluation_complete"] = True
        report["code"] = "all_checks_pass"
        for check in report["checks"]:
            check["status"] = "PASS"
            check["code"] = f"{check['check_id'].lower()}_pass"
    elif status == "FAIL":
        report["status"] = "FAIL"
        report["evaluation_complete"] = True
        report["code"] = "test_failure"
        report["checks"][0]["status"] = "FAIL"
        report["checks"][0]["code"] = "test_failure"
    return report


def test_gate_registry_is_exact_frozen_and_immutable() -> None:
    gate = _load_gate_contract_module()

    assert gate.GATE_CHECK_ORDER == (
        "G01_GATE_REFUSAL_PRECONDITIONS",
        "G02_GATE_NETWORK_DENIAL",
    )
    result = gate.GateCheckResult(
        check_id="G01_GATE_REFUSAL_PRECONDITIONS",
        status="PASS",
        code="g01_gate_preconditions_passed",
    )
    assert tuple(field.name for field in fields(result)) == (
        "check_id",
        "status",
        "code",
    )
    with pytest.raises(FrozenInstanceError):
        result.status = "REFUSED"

    with pytest.raises(Exception, match="dual_live_gate_check_id_invalid"):
        gate.GateCheckResult(check_id="G99_UNKNOWN", status="PASS", code="valid_code")


def test_gate_allowlist_covers_every_evaluator_pass_evidence_keyword() -> None:
    gate = _load_gate_contract_module()
    evaluator_tree = ast.parse(
        (BACKEND / "app" / "services" / "dual_live_evaluator.py").read_text(
            encoding="utf-8"
        )
    )
    emitted_keys = {
        keyword.arg
        for node in ast.walk(evaluator_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_pass"
        for keyword in node.keywords
        if keyword.arg is not None
    }

    assert emitted_keys <= (
        gate._SAFE_EVIDENCE_KEYS | set(gate._RUNTIME_START_EVIDENCE_KEYS)
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows proof custody only")
def test_read_only_database_custody_is_query_only_and_byte_stable(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "proof.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("CREATE TABLE proof (value TEXT NOT NULL)")
        connection.execute("INSERT INTO proof VALUES ('stable')")
        connection.commit()
    finally:
        connection.close()
    before = database_path.read_bytes()
    gate = _load_gate_contract_module()

    with gate._ReadOnlyDatabase.open(database_path) as database:
        assert Path(database._engine.url.database).resolve() == database_path.resolve()
        first_identity = database.stable_identity()
        with database.session() as session:
            assert session.connection().exec_driver_sql("PRAGMA query_only").scalar_one() == 1
            assert (
                session.connection().exec_driver_sql("PRAGMA journal_mode").scalar_one()
                == "delete"
            )
            assert session.execute(gate._sql_text("SELECT value FROM proof")).scalar_one() == "stable"
            with pytest.raises(Exception):
                session.execute(gate._sql_text("UPDATE proof SET value='changed'"))
        assert database.stable_identity() == first_identity

    assert database_path.read_bytes() == before
    assert not any((tmp_path / f"proof.db{suffix}").exists() for suffix in ("-journal", "-wal", "-shm"))


@pytest.mark.parametrize("status,exit_code", [("PASS", 0), ("FAIL", 1), ("INDETERMINATE", 2)])
def test_evaluator_status_has_exact_exit_mapping(status: str, exit_code: int) -> None:
    gate = _load_gate_contract_module()

    assert gate._exit_code_for_status(status) == exit_code


def test_report_contract_requires_exact_registry_nonclaims_and_safe_evidence() -> None:
    gate = _load_gate_contract_module()
    report = _evaluation_report(status="PASS")
    report["checks"][0]["evidence"] = {
        "campaign_fingerprint": CAMPAIGN_FINGERPRINT,
        "connector_count": 2,
        "terminal_hashes": ["b" * 64, "c" * 64],
        "process_boot_id": "d" * 64,
        "parent_run_id": "54b073bc-4b09-5fbc-9065-9623aae6c0d9",
        "code_revision": "e" * 40,
        "canonical": True,
    }

    assert gate._report_is_exact(
        report,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
    )

    adversaries = []
    wrong_order = json.loads(json.dumps(report))
    wrong_order["checks"][0], wrong_order["checks"][1] = (
        wrong_order["checks"][1],
        wrong_order["checks"][0],
    )
    adversaries.append(wrong_order)
    wrong_nonclaims = json.loads(json.dumps(report))
    wrong_nonclaims["nonclaims"] = [*EVALUATOR_NONCLAIMS, "secretcredential"]
    adversaries.append(wrong_nonclaims)
    unsafe_path = json.loads(json.dumps(report))
    unsafe_path["checks"][0]["evidence"] = {"detail": "C:\\secret\\credential.txt"}
    adversaries.append(unsafe_path)
    unsafe_token = json.loads(json.dumps(report))
    unsafe_token["checks"][0]["evidence"] = {"domain": "secretcredential"}
    adversaries.append(unsafe_token)
    oversized = json.loads(json.dumps(report))
    oversized["checks"][0]["evidence"] = {"detail": "x" * 129}
    adversaries.append(oversized)
    too_deep = json.loads(json.dumps(report))
    too_deep["checks"][0]["evidence"] = {"a": {"b": {"c": {"d": 1}}}}
    adversaries.append(too_deep)

    assert tuple(check["check_id"] for check in report["checks"]) == EVALUATOR_CHECK_ORDER
    assert all(
        not gate._report_is_exact(
            candidate,
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        )
        for candidate in adversaries
    )


def test_report_contract_requires_canonical_uuid5_parent_arming_id() -> None:
    gate = _load_gate_contract_module()
    report = _evaluation_report(status="PASS")
    l11 = report["checks"][EVALUATOR_CHECK_ORDER.index("L11_NRC_FIRST_BINDING")]
    l11["evidence"] = {
        "parent_run_id": "54b073bc-4b09-5fbc-9065-9623aae6c0d9",
        "parent_terminal_hash": "b" * 64,
    }

    assert gate._report_is_exact(
        report,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
    )

    for invalid in (CAMPAIGN_ID, "run-nrc", "54B073BC-4B09-5FBC-9065-9623AAE6C0D9"):
        candidate = json.loads(json.dumps(report))
        candidate["checks"][EVALUATOR_CHECK_ORDER.index("L11_NRC_FIRST_BINDING")][
            "evidence"
        ]["parent_run_id"] = invalid
        assert not gate._report_is_exact(
            candidate,
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        )


def test_report_contract_accepts_exact_indeterminate_domain_error_only() -> None:
    gate = _load_gate_contract_module()
    report = _evaluation_report(status="INDETERMINATE", code="origin_unavailable")
    report["checks"][0]["evidence"] = {
        "domain": "origin",
        "reason_code": "layer3_origin_nrc_phase_b_invalid",
    }

    assert gate._report_is_exact(
        report,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
    )

    for evidence in (
        {"domain": "unknown", "reason_code": "layer3_origin_nrc_phase_b_invalid"},
        {"domain": "origin", "reason_code": "unsafe-value"},
        {
            "domain": "origin",
            "reason_code": "layer3_origin_nrc_phase_b_invalid",
            "extra": 1,
        },
    ):
        candidate = json.loads(json.dumps(report))
        candidate["checks"][0]["evidence"] = evidence
        assert not gate._report_is_exact(
            candidate,
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        )

    pass_candidate = _evaluation_report(status="PASS")
    pass_candidate["checks"][0]["evidence"] = report["checks"][0]["evidence"]
    assert not gate._report_is_exact(
        pass_candidate,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
    )


def test_report_contract_accepts_exact_runtime_start_contract_evidence() -> None:
    gate = _load_gate_contract_module()
    report = _evaluation_report(status="PASS")
    r05 = report["checks"][EVALUATOR_CHECK_ORDER.index("R05_RUNTIME_CHAIN")]
    r05["evidence"] = {
        "record_count": 18,
        "terminal_record_sha256": "b" * 64,
        "dependency_set_sha256": "c" * 64,
        "phase_a_timeout_ms": 120_000,
        "phase_b_timeout_ms": 30_000,
    }

    assert gate._report_is_exact(
        report,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
    )

    for key, invalid in (
        ("dependency_set_sha256", "not-a-digest"),
        ("phase_a_timeout_ms", 0),
        ("phase_a_timeout_ms", 0xFFFFFFFF),
        ("phase_b_timeout_ms", True),
    ):
        candidate = json.loads(json.dumps(report))
        candidate["checks"][EVALUATOR_CHECK_ORDER.index("R05_RUNTIME_CHAIN")][
            "evidence"
        ][key] = invalid
        assert not gate._report_is_exact(
            candidate,
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        )


def test_report_contract_accepts_f06_inspected_count_only_by_exact_key() -> None:
    gate = _load_gate_contract_module()
    report = _evaluation_report(status="PASS")
    f06_index = EVALUATOR_CHECK_ORDER.index("F06_NO_EGRESS_DEPENDENCY")
    report["checks"][f06_index]["evidence"] = {
        "forbidden_dependency_count": 0,
        "inspected_module_count": 45,
    }

    assert gate._report_is_exact(
        report,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
    )

    unknown_key = json.loads(json.dumps(report))
    unknown_key["checks"][f06_index]["evidence"]["inspected_module_total"] = 45
    assert not gate._report_is_exact(
        unknown_key,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
    )


def test_report_contract_accepts_full_new_pass_evidence_shape_only() -> None:
    from app.services import dual_live_evaluator, dual_live_runtime

    gate = _load_gate_contract_module()
    action_count = len(dual_live_evaluator._PHASE_B_DOWNSTREAM_ACTIONS)
    evidence_by_check = {
        "F06_NO_EGRESS_DEPENDENCY": {
            "forbidden_dependency_count": 0,
            "inspected_module_count": 45,
        },
        "R11_AUTHORITY_CLEARED": {
            "all_required_absent": True,
            "authority_posture_sha256": (
                dual_live_runtime.AUTHORITY_CLEARED_POSTURE_SHA256
            ),
        },
        "R12_PHASE_B_GUARDS": {
            "pre_import_guarded": True,
            "denied_route_count": len(
                dual_live_evaluator._CHILD_PROOF_DENIED_ROUTES
            ),
            "guard_proof_count": 2,
        },
        "R14_RUNTIME_TERMINAL": {
            "terminal_state": "completed",
            "child_proof_count": 4,
        },
        "R15_WRAPPER_NETWORK_INERT": {
            "wrapper_send_records": 0,
            "phase_b_network_enable_attempt_count": 0,
        },
        "R16_PHASE_A_RAW_ONLY": {
            "acquisition_only": True,
            "connector_acquisition_count": 2,
            "downstream_action_count": 0,
        },
        "R17_PHASE_B_STRICT_FLOW": {
            "action_receipt_count": action_count,
            "boundary_count": 14,
            "connector_count": 2,
            "downstream_action_count": action_count,
            "source_binding_count": 2,
            "terminal_boundary": "handoff_prepared",
        },
        "R18_PHASE_A_TERMINAL_ONCE": {
            "terminal_run_count": 2,
            "raw_blob_count": 2,
            "terminal_transition_count": 2,
        },
        "R19_A_TO_B_ORDER": {
            "phase_a_terminal_ordinal": 9,
            "phase_b_start_ordinal": 10,
            "proof_stream_phase_order": "A_then_B",
        },
    }
    results = tuple(
        dual_live_evaluator.CheckResult(
            check_id=check_id,
            status="PASS",
            code=f"{check_id.lower()}_pass",
            evidence=evidence_by_check.get(check_id, {}),
        )
        for check_id in EVALUATOR_CHECK_ORDER
    )
    report = dual_live_evaluator._evaluation_report(
        campaign_id=CAMPAIGN_ID,
        expected_campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        results=results,
    )

    assert gate._report_is_exact(
        report,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
    )

    adversaries = []
    for check_id, key, invalid in (
        ("F06_NO_EGRESS_DEPENDENCY", "unexpected_count", 1),
        ("F06_NO_EGRESS_DEPENDENCY", "inspected_module_count", True),
        ("R11_AUTHORITY_CLEARED", "authority_posture_sha256", "not-a-hash"),
        ("R17_PHASE_B_STRICT_FLOW", "terminal_boundary", "external_delivered"),
        ("R19_A_TO_B_ORDER", "proof_stream_phase_order", "B_then_A"),
        ("R19_A_TO_B_ORDER", "phase_a_terminal_ordinal", -1),
    ):
        candidate = json.loads(json.dumps(report))
        candidate["checks"][EVALUATOR_CHECK_ORDER.index(check_id)]["evidence"][
            key
        ] = invalid
        adversaries.append(candidate)

    assert all(
        not gate._report_is_exact(
            candidate,
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        )
        for candidate in adversaries
    )


def test_report_contract_accepts_real_evaluator_f09_pass_shape_only() -> None:
    from app.services import dual_live_evaluator

    gate = _load_gate_contract_module()
    f09_evidence = {
        "connector_results": (
            {
                "connector_key": "nrc_adams_aps",
                "projection_sha256": "1" * 64,
            },
            {
                "connector_key": "sciencebase_mcs",
                "projection_sha256": "2" * 64,
            },
        ),
        "combined_result": {"projection_sha256": "3" * 64},
    }
    results = tuple(
        dual_live_evaluator.CheckResult(
            check_id=check_id,
            status="PASS",
            code=f"{check_id.lower()}_pass",
            evidence=(
                f09_evidence
                if check_id == "F09_CONNECTOR_AND_COMBINED_REPORTS"
                else {}
            ),
        )
        for check_id in EVALUATOR_CHECK_ORDER
    )
    report = dual_live_evaluator._evaluation_report(
        campaign_id=CAMPAIGN_ID,
        expected_campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        results=results,
    )

    assert gate._report_is_exact(
        report,
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
    )

    f09_index = EVALUATOR_CHECK_ORDER.index("F09_CONNECTOR_AND_COMBINED_REPORTS")
    wrong_connector_order = json.loads(json.dumps(report))
    wrong_connector_order["checks"][f09_index]["evidence"]["connector_results"].reverse()
    wrong_nested_key = json.loads(json.dumps(report))
    wrong_nested_key["checks"][f09_index]["evidence"]["combined_result"][
        "detail"
    ] = "4" * 64
    wrong_digest = json.loads(json.dumps(report))
    wrong_digest["checks"][f09_index]["evidence"]["connector_results"][0][
        "projection_sha256"
    ] = "secretcredential"
    wrong_check = json.loads(json.dumps(report))
    wrong_check["checks"][0]["evidence"] = wrong_check["checks"][f09_index][
        "evidence"
    ]

    assert all(
        not gate._report_is_exact(
            candidate,
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        )
        for candidate in (
            wrong_connector_order,
            wrong_nested_key,
            wrong_digest,
            wrong_check,
        )
    )


def test_exception_code_boundary_rejects_arbitrary_secret_code() -> None:
    gate = _load_gate_contract_module()

    class SecretError(RuntimeError):
        code = "secretcredential"

    assert (
        gate._safe_exception_code(SecretError("must-not-escape"), "safe_fallback")
        == "safe_fallback"
    )
    assert (
        gate._safe_exception_code(
            gate.DualLiveGateError("dual_live_database_sidecar_present"),
            "safe_fallback",
        )
        == "dual_live_database_sidecar_present"
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows proof custody only")
def test_session_exception_still_runs_stability_checks_and_preserves_primary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "proof.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE proof (value TEXT NOT NULL)")
    connection.commit()
    connection.close()
    gate = _load_gate_contract_module()
    stability_calls = 0

    class PrimaryFailure(RuntimeError):
        pass

    def fail_stability(_database: object) -> None:
        nonlocal stability_calls
        stability_calls += 1
        raise gate.DualLiveGateError("dual_live_database_custody_changed")

    database = gate._ReadOnlyDatabase.open(database_path)
    monkeypatch.setattr(gate._ReadOnlyDatabase, "assert_stable", fail_stability)
    with database:
        with pytest.raises(PrimaryFailure) as caught:
            with database.session():
                raise PrimaryFailure("primary")

    assert stability_calls >= 1
    assert "dual_live_database_custody_changed" in " ".join(caught.value.__notes__)


def test_database_close_attempts_retained_handle_after_engine_dispose_failure() -> None:
    gate = _load_gate_contract_module()
    custody_closed = False

    class Engine:
        def dispose(self, *, close: bool) -> None:
            assert close is True
            raise RuntimeError("dispose failed")

    class Custody:
        def close(self) -> None:
            nonlocal custody_closed
            custody_closed = True

    database = gate._ReadOnlyDatabase(Path("C:/proof.db"), Custody(), Engine())

    with pytest.raises(RuntimeError, match="dispose failed"):
        database.close()
    assert custody_closed is True


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
def test_g01_g02_pass_before_evaluator_and_final_reread_follows_snapshot_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = _load_gate_contract_module()
    database_path = tmp_path / "proof.db"
    database_path.write_bytes(b"proof")
    events: list[str] = []
    chain = SimpleNamespace(
        head=SimpleNamespace(
            campaigns=(
                SimpleNamespace(
                    campaign_id=CAMPAIGN_ID,
                    campaign_fingerprint=CAMPAIGN_FINGERPRINT,
                    raw_definition_sha256=DEFINITION_SHA,
                ),
            )
        ),
        revisions=(
            SimpleNamespace(
                model=SimpleNamespace(revision=1),
                raw_sha256="d" * 64,
                raw_bytes=b"index",
            ),
        ),
    )
    settings = SimpleNamespace(storage_dir=str(tmp_path))
    load_count = 0

    def load_chain(_settings: object) -> object:
        nonlocal load_count
        load_count += 1
        events.append("initial_chain" if load_count == 1 else "final_chain")
        return chain

    @contextmanager
    def staged_locks(
        _root: Path,
        _campaign_id: str,
        _campaign_fingerprint: str,
        resolver: object,
    ) -> object:
        events.append("root_lock")
        resolver()
        events.append("campaign_lock")
        try:
            yield
        finally:
            events.append("locks_released")

    class FakeDatabase:
        def __enter__(self) -> object:
            return self

        def __exit__(self, *exc_info: object) -> None:
            events.append("database_closed")

        @contextmanager
        def session(self) -> object:
            yield SimpleNamespace()

        def stable_identity(self) -> tuple[str]:
            events.append("database_identity")
            return ("stable",)

        def assert_stable(self) -> None:
            events.append("database_stable")

    class FakeReadOnlyDatabase:
        @classmethod
        def open(cls, _path: Path) -> FakeDatabase:
            return FakeDatabase()

    capture_count = 0

    def verify_capture(*_args: object) -> None:
        nonlocal capture_count
        capture_count += 1
        events.append("g01_capture" if capture_count == 1 else "final_capture")

    evaluation_count = 0
    report = _evaluation_report()

    def evaluate(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal evaluation_count
        evaluation_count += 1
        events.append(f"evaluate_{evaluation_count}")
        return json.loads(json.dumps(report))

    def g01() -> object:
        events.append("g01_pass")
        return gate.GateCheckResult(
            "G01_GATE_REFUSAL_PRECONDITIONS", "PASS", "g01_gate_preconditions_passed"
        )

    def g02() -> object:
        events.append("g02_pass")
        return gate.GateCheckResult(
            "G02_GATE_NETWORK_DENIAL", "PASS", "g02_network_denial_passed"
        )

    def install_connector_guard() -> None:
        events.append("connector_guard_installed")

    import app.services.connector_campaign_log_capture as capture_module
    import app.services.connector_egress_authorization as authorization_module
    import app.services.dual_live_evaluator as evaluator_module
    import app.services.dual_live_windows as windows_module

    monkeypatch.setattr(
        gate,
        "_settings_and_paths",
        lambda _environ: (settings, tmp_path, database_path),
    )
    monkeypatch.setattr(gate, "_ReadOnlyDatabase", FakeReadOnlyDatabase)
    monkeypatch.setattr(gate, "_g01_pass", g01)
    monkeypatch.setattr(gate, "_g02_pass", g02)
    monkeypatch.setattr(gate, "_install_connector_transport_guard", install_connector_guard)
    monkeypatch.setattr(
        capture_module, "verify_connector_campaign_log_capture_read_only", verify_capture
    )
    monkeypatch.setattr(
        authorization_module, "load_evidence_index_chain_read_only", load_chain
    )
    monkeypatch.setattr(windows_module, "acquire_proof_locks_staged", staged_locks)
    monkeypatch.setattr(evaluator_module, "evaluate_dual_live_proof", evaluate)

    result = gate._run_guarded_evaluation(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        environ={},
    )

    assert result == report
    assert (
        events.index("g01_pass")
        < events.index("connector_guard_installed")
        < events.index("g02_pass")
        < events.index("evaluate_1")
    )
    assert events.index("evaluate_2") < events.index("final_chain")
    assert events.index("final_chain") < events.index("final_capture")
    final_identity = max(
        index for index, event in enumerate(events) if event == "database_identity"
    )
    assert events.index("final_capture") < final_identity
    assert events.index("database_closed") < events.index("locks_released")


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
def test_g01_refuses_unsealed_capture_before_evaluator_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = _load_gate_contract_module()
    database_path = tmp_path / "proof.db"
    database_path.write_bytes(b"proof")
    chain = SimpleNamespace(
        head=SimpleNamespace(
            campaigns=(
                SimpleNamespace(
                    campaign_id=CAMPAIGN_ID,
                    campaign_fingerprint=CAMPAIGN_FINGERPRINT,
                    raw_definition_sha256=DEFINITION_SHA,
                ),
            )
        ),
        revisions=(),
    )
    settings = SimpleNamespace(storage_dir=str(tmp_path))
    evaluator_calls = 0
    connector_guard_calls = 0

    @contextmanager
    def staged_locks(*args: object) -> object:
        args[-1]()
        yield

    class FakeDatabase:
        def __enter__(self) -> object:
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

        @contextmanager
        def session(self) -> object:
            yield SimpleNamespace()

        def stable_identity(self) -> tuple[str]:
            return ("stable",)

    class FakeReadOnlyDatabase:
        @classmethod
        def open(cls, _path: Path) -> FakeDatabase:
            return FakeDatabase()

    def evaluate(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal evaluator_calls
        evaluator_calls += 1
        return _evaluation_report()

    def install_connector_guard() -> None:
        nonlocal connector_guard_calls
        connector_guard_calls += 1

    import app.services.connector_campaign_log_capture as capture_module
    import app.services.connector_egress_authorization as authorization_module
    import app.services.dual_live_evaluator as evaluator_module
    import app.services.dual_live_windows as windows_module

    monkeypatch.setattr(
        gate,
        "_settings_and_paths",
        lambda _environ: (settings, tmp_path, database_path),
    )
    monkeypatch.setattr(gate, "_ReadOnlyDatabase", FakeReadOnlyDatabase)
    monkeypatch.setattr(gate, "_install_connector_transport_guard", install_connector_guard)
    monkeypatch.setattr(
        capture_module,
        "verify_connector_campaign_log_capture_read_only",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("unsealed")),
    )
    monkeypatch.setattr(
        authorization_module,
        "load_evidence_index_chain_read_only",
        lambda _settings: chain,
    )
    monkeypatch.setattr(windows_module, "acquire_proof_locks_staged", staged_locks)
    monkeypatch.setattr(evaluator_module, "evaluate_dual_live_proof", evaluate)

    with pytest.raises(gate.DualLiveGateError, match="dual_live_capture_unsealed"):
        gate._run_guarded_evaluation(
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=CAMPAIGN_FINGERPRINT,
            environ={},
        )
    assert evaluator_calls == 0
    assert connector_guard_calls == 0


def test_gate_lock_refusal_never_enters_evaluator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = _load_gate_contract_module()
    database_path = tmp_path / "proof.db"
    database_path.write_bytes(b"proof")
    evaluator_calls = 0
    connector_guard_calls = 0

    def refuse_lock(*_args: object) -> object:
        raise DualLiveWindowsError("dual_live_lock_busy")

    def evaluate(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal evaluator_calls
        evaluator_calls += 1
        return _evaluation_report()

    def install_connector_guard() -> None:
        nonlocal connector_guard_calls
        connector_guard_calls += 1

    import app.services.dual_live_evaluator as evaluator_module
    import app.services.dual_live_windows as windows_module

    monkeypatch.setattr(
        gate,
        "_settings_and_paths",
        lambda _environ: (SimpleNamespace(storage_dir=str(tmp_path)), tmp_path, database_path),
    )
    monkeypatch.setattr(windows_module, "acquire_proof_locks_staged", refuse_lock)
    monkeypatch.setattr(evaluator_module, "evaluate_dual_live_proof", evaluate)
    monkeypatch.setattr(gate, "_install_connector_transport_guard", install_connector_guard)

    with pytest.raises(DualLiveWindowsError, match="dual_live_lock_busy"):
        gate._run_guarded_evaluation(
            campaign_id=CAMPAIGN_ID,
            campaign_fingerprint=CAMPAIGN_FINGERPRINT,
            environ={},
        )
    assert evaluator_calls == 0
    assert connector_guard_calls == 0


@pytest.mark.parametrize(
    "authority_name",
    [AUTHORITY_VARIABLES[0].lower(), AUTHORITY_VARIABLES[1].swapcase()],
)
def test_g01_refuses_case_variant_authority_aliases(authority_name: str) -> None:
    gate = _load_gate_contract_module()

    assert (
        gate._environment_refusal({authority_name: "secretcredential"})
        == "dual_live_send_authority_environment_present"
    )


def _complete_gate_environment(tmp_path: Path, database_url: str) -> dict[str, str]:
    return {
        "DATABASE_URL": database_url,
        "STORAGE_DIR": str(tmp_path),
        "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT": str(tmp_path),
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH": str(tmp_path / "index.json"),
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256": "d" * 64,
        "NRC_ADAMS_APS_SUBSCRIPTION_KEY": "fake-scan-key",
    }


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
@pytest.mark.parametrize(
    ("name", "value", "code"),
    (
        ("STORAGE_DIR", r"Z:\proof\storage", "dual_live_storage_invalid"),
        (
            "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT",
            r"z:\proof\evidence",
            "dual_live_evidence_root_invalid",
        ),
        (
            "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH",
            r"Z:\proof\index.json",
            "dual_live_evidence_index_path_invalid",
        ),
        (
            "DATABASE_URL",
            "sqlite:///Z:/proof/proof.db",
            "dual_live_database_path_unsafe",
        ),
    ),
)
def test_gate_rejects_mapped_config_before_settings_or_path_touch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
    code: str,
) -> None:
    gate = _load_gate_contract_module()
    environ = _complete_gate_environment(
        tmp_path,
        f"sqlite:///{(tmp_path / 'proof.db').as_posix()}",
    )
    environ[name] = value
    touched: list[str] = []
    monkeypatch.setattr(
        dual_live_windows._kernel32,
        "GetDriveTypeW",
        lambda root: 4 if str(root).casefold() == "z:\\" else 3,
    )
    monkeypatch.setattr(
        gate,
        "_load_settings",
        lambda _environ: touched.append("settings"),
    )
    monkeypatch.setattr(
        gate,
        "_path_has_reparse_component",
        lambda _path: touched.append("lstat") or False,
    )

    with pytest.raises(gate.DualLiveGateError, match=code):
        gate._settings_and_paths(environ)

    assert touched == []


def test_gate_rejects_send_authority_before_settings_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = _load_gate_contract_module()
    environ = _complete_gate_environment(
        tmp_path,
        f"sqlite:///{(tmp_path / 'proof.db').as_posix()}",
    )
    environ["CONNECTOR_CAMPAIGN_DEFINITION_PATH"] = r"\\server\share\definition.json"
    settings_calls = 0

    def load_settings(_environ: Mapping[str, str]) -> object:
        nonlocal settings_calls
        settings_calls += 1
        return object()

    monkeypatch.setattr(gate, "_load_settings", load_settings)

    with pytest.raises(
        gate.DualLiveGateError,
        match="dual_live_send_authority_environment_present",
    ):
        gate._settings_and_paths(environ)

    assert settings_calls == 0


@pytest.mark.skipif(os.name != "nt", reason="Windows fixed-volume proof only")
@pytest.mark.parametrize(
    ("database_url", "code"),
    [
        ("sqlite:///:memory:", "dual_live_database_url_invalid"),
        ("sqlite:///relative.db", "dual_live_database_path_unsafe"),
        ("sqlite://///server/share/proof.db", "dual_live_database_path_unsafe"),
        ("sqlite:///C:/proof.db?mode=rw", "dual_live_database_url_invalid"),
        ("postgresql://localhost/proof", "dual_live_database_url_invalid"),
    ],
)
def test_g01_refuses_nonlocal_or_overridden_database_before_effect(
    tmp_path: Path,
    database_url: str,
    code: str,
) -> None:
    completed = _run_gate(
        tmp_path,
        env_updates=_complete_gate_environment(tmp_path, database_url),
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal(code)
    assert completed.stderr == b""
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows proof custody only")
def test_database_refuses_sidecar_active_writer_and_replacement(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "proof.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE proof (value TEXT NOT NULL)")
    connection.commit()
    connection.close()
    gate = _load_gate_contract_module()
    sidecar = Path(f"{database_path}-wal")
    sidecar.write_bytes(b"unsafe")
    with pytest.raises(gate.DualLiveGateError, match="dual_live_database_sidecar_present"):
        gate._ReadOnlyDatabase.open(database_path)
    sidecar.unlink()

    replacement = tmp_path / "replacement.db"
    replacement.write_bytes(database_path.read_bytes())
    with gate._ReadOnlyDatabase.open(database_path) as database:
        with pytest.raises((OSError, sqlite3.OperationalError)):
            writer = sqlite3.connect(database_path, timeout=0)
            try:
                writer.execute("INSERT INTO proof VALUES ('changed')")
                writer.commit()
            finally:
                writer.close()
        with pytest.raises(OSError):
            os.replace(replacement, database_path)
        database.assert_stable()


def test_same_connection_data_version_drift_is_detected(tmp_path: Path) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    database_path = tmp_path / "proof.db"
    writer = sqlite3.connect(database_path)
    writer.execute("CREATE TABLE proof (value TEXT NOT NULL)")
    writer.execute("INSERT INTO proof VALUES ('before')")
    writer.commit()
    writer.close()
    gate = _load_gate_contract_module()
    uri = f"file:{database_path.as_posix()}?mode=ro&cache=private"

    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(uri, uri=True)
        connection.execute("PRAGMA query_only=ON")
        return connection

    class FakeCustody:
        def stable_identity(self) -> tuple[str]:
            return ("stable",)

        def assert_stable(self) -> None:
            return None

        def close(self) -> None:
            return None

    engine = create_engine(
        "sqlite+pysqlite://",
        creator=connect,
        future=True,
        poolclass=NullPool,
    )
    database = gate._ReadOnlyDatabase(database_path, FakeCustody(), engine)

    with pytest.raises(
        gate.DualLiveGateError,
        match="dual_live_database_data_version_changed",
    ):
        with database.session():
            writer = sqlite3.connect(database_path)
            writer.execute("UPDATE proof SET value='after'")
            writer.commit()
            writer.close()
    database.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof custody and locks only")
def test_guarded_fixture_uses_real_locks_and_read_only_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = _load_gate_contract_module()
    database_path = tmp_path / "proof.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE proof (value TEXT NOT NULL)")
    connection.execute("INSERT INTO proof VALUES ('stable')")
    connection.commit()
    connection.close()
    before_bytes = database_path.read_bytes()
    before_files = tuple(sorted(path.name for path in tmp_path.iterdir()))
    chain = SimpleNamespace(
        head=SimpleNamespace(
            campaigns=(
                SimpleNamespace(
                    campaign_id=CAMPAIGN_ID,
                    campaign_fingerprint=CAMPAIGN_FINGERPRINT,
                    raw_definition_sha256=DEFINITION_SHA,
                ),
            )
        ),
        revisions=(
            SimpleNamespace(
                model=SimpleNamespace(revision=1),
                raw_sha256="d" * 64,
                raw_bytes=b"index",
            ),
        ),
    )
    settings = SimpleNamespace(storage_dir=str(tmp_path))
    capture_calls = 0
    evaluator_calls = 0
    report = _evaluation_report()

    def verify_capture(session: object, *_args: object) -> None:
        nonlocal capture_calls
        capture_calls += 1
        assert session.connection().exec_driver_sql("PRAGMA query_only").scalar_one() == 1

    def evaluate(session: object, **_kwargs: object) -> dict[str, object]:
        nonlocal evaluator_calls
        evaluator_calls += 1
        assert session.execute(gate._sql_text("SELECT value FROM proof")).scalar_one() == "stable"
        return json.loads(json.dumps(report))

    import app.services.connector_campaign_log_capture as capture_module
    import app.services.connector_egress_authorization as authorization_module
    import app.services.dual_live_evaluator as evaluator_module

    monkeypatch.setattr(
        gate,
        "_settings_and_paths",
        lambda _environ: (settings, tmp_path, database_path),
    )
    monkeypatch.setattr(
        capture_module,
        "verify_connector_campaign_log_capture_read_only",
        verify_capture,
    )
    monkeypatch.setattr(
        authorization_module,
        "load_evidence_index_chain_read_only",
        lambda _settings: chain,
    )
    monkeypatch.setattr(evaluator_module, "evaluate_dual_live_proof", evaluate)
    monkeypatch.setattr(gate, "_install_connector_transport_guard", lambda: None)
    monkeypatch.setattr(
        gate,
        "_g02_pass",
        lambda: gate.GateCheckResult(
            "G02_GATE_NETWORK_DENIAL", "PASS", "g02_network_denial_passed"
        ),
    )

    result = gate._run_guarded_evaluation(
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
        environ={},
    )

    assert result == report
    assert capture_calls == 2
    assert evaluator_calls == 2
    assert database_path.read_bytes() == before_bytes
    assert tuple(sorted(path.name for path in tmp_path.iterdir())) == before_files


def test_main_emits_exact_safe_report_and_rejects_nested_secret() -> None:
    probe = f"""
import contextlib
import importlib.util
import io
import json
import os
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
check_ids = {EVALUATOR_CHECK_ORDER!r}
nonclaims = {EVALUATOR_NONCLAIMS!r}
def report(secret=False):
    checks = [{{
        "check_id": check_id,
        "status": "PASS",
        "code": check_id.lower() + "_pass",
        "evidence": {{}},
    }} for check_id in check_ids]
    if secret:
        checks[0]["evidence"] = {{"detail": "C:/secret/credential.txt"}}
    return {{
        "schema_id": "project6.dual_live_evaluation.v1",
        "campaign_id": {CAMPAIGN_ID!r},
        "expected_campaign_fingerprint": {CAMPAIGN_FINGERPRINT!r},
        "status": "PASS",
        "fresh_live": True,
        "evaluation_complete": True,
        "code": "all_checks_pass",
        "checks": checks,
        "nonclaims": list(nonclaims),
    }}
module._install_network_guard = lambda: None
module._install_connector_transport_guard = lambda: None
module._network_guard_intact = lambda: True
module._base_network_guard_intact = lambda: True
module._unsafe_backend_module_preloaded = lambda: False
module._backend_path = lambda: None
key = "PYMUPDF_SUGGEST_LAYOUT_ANALYZER"
os.environ.pop(key, None)
outputs = []
for secret in (False, True):
    observed = []
    def evaluate(**kwargs):
        observed.append(os.environ.get(key))
        if os.environ.get(key) != "0":
            print("pymupdf recommendation")
        return report(secret)
    module._run_guarded_evaluation = evaluate
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = module.main({ _valid_args()!r}, {{}})
    outputs.append([result, output.getvalue(), observed, key in os.environ])
print(json.dumps(outputs))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    safe, unsafe = json.loads(completed.stdout)
    assert safe[0] == 0
    assert safe[1] == _captured(_evaluation_report(status="PASS"))
    assert safe[2:] == [["0"], False]
    assert unsafe == [
        2,
        _captured_refusal("dual_live_evaluation_contract_invalid"),
        ["0"],
        False,
    ]
    assert "secret" not in unsafe[1]
    assert completed.stderr == ""


def test_pymupdf_layout_suppression_restores_exact_prior_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = _load_gate_contract_module()
    key = "PYMUPDF_SUGGEST_LAYOUT_ANALYZER"

    monkeypatch.delenv(key, raising=False)
    with gate._suppress_pymupdf_layout_recommendation():
        assert os.environ[key] == "0"
    assert key not in os.environ

    monkeypatch.setenv(key, "owner-value")
    with gate._suppress_pymupdf_layout_recommendation():
        assert os.environ[key] == "0"
    assert os.environ[key] == "owner-value"


def _captured(payload: dict[str, object]) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True) + "\n"


def _captured_refusal(code: str) -> str:
    return _refusal(code).decode().removesuffix(os.linesep) + "\n"


def _clean_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("CONNECTOR_LIVE_EGRESS_ENABLED", None)
    env.pop("DUAL_LIVE_CAMPAIGN_ID", None)
    env.pop("DUAL_LIVE_CAMPAIGN_FINGERPRINT", None)
    env.pop("PYTHONPATH", None)
    for name in (
        *AUTHORITY_VARIABLES,
        "DATABASE_URL",
        "STORAGE_DIR",
        "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT",
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH",
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256",
        "NRC_ADAMS_APS_SUBSCRIPTION_KEY",
    ):
        env.pop(name, None)
    return env


def _valid_args() -> list[str]:
    return [
        "--campaign-id",
        CAMPAIGN_ID,
        "--campaign-fingerprint",
        CAMPAIGN_FINGERPRINT,
    ]


def _run_gate(
    tmp_path: Path,
    *,
    args: list[str] | None = None,
    env_updates: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    env = _clean_env()
    if env_updates:
        env.update(env_updates)
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(GATE),
            *(args if args is not None else _valid_args()),
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
    )


def _run_powershell(
    tmp_path: Path,
    *,
    action: str,
    env_updates: dict[str, str] | None = None,
    empty_path: bool = False,
    action_args: list[str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    if POWERSHELL is None:
        raise AssertionError("PowerShell is required for the dual-live gate contract")
    env = _clean_env()
    if env_updates:
        env.update(env_updates)
    if empty_path:
        env["PATH"] = ""
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PROJECT6),
            "-Action",
            action,
            "-PythonVersion",
            "3.11",
            *(action_args or []),
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
    )


def test_gate_refuses_missing_runtime_exactly_and_cwd_independently(
    tmp_path: Path,
) -> None:
    completed = _run_gate(
        tmp_path,
        env_updates={"CONNECTOR_LIVE_EGRESS_ENABLED": "OFF", "PYTHONPATH": ""},
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_database_missing")
    assert completed.stderr == b""
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("false_value", ["", "0", "false", "FALSE", "no", "NO", "off", "OFF"])
def test_false_egress_values_are_accepted_without_stripping(
    tmp_path: Path, false_value: str
) -> None:
    completed = _run_gate(
        tmp_path,
        env_updates={"CONNECTOR_LIVE_EGRESS_ENABLED": false_value},
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_database_missing")
    assert completed.stderr == b""


def test_empty_false_egress_value_remains_false_in_environment_only_settings() -> None:
    gate = _load_gate_contract_module()
    gate._backend_path()

    settings = gate._load_settings({"CONNECTOR_LIVE_EGRESS_ENABLED": ""})

    assert settings.connector_live_egress_enabled is False


@pytest.mark.parametrize("true_value", ["1", "true", "TRUE", "yes", "YES", "on", "ON"])
def test_true_egress_values_refuse_before_authority_or_arguments(
    tmp_path: Path, true_value: str
) -> None:
    completed = _run_gate(
        tmp_path,
        args=["--unknown"],
        env_updates={
            "CONNECTOR_LIVE_EGRESS_ENABLED": true_value,
            AUTHORITY_VARIABLES[0]: "secret-authority",
        },
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_egress_enabled")
    assert completed.stderr == b""
    assert b"secret-authority" not in completed.stdout


@pytest.mark.parametrize("invalid_value", [" false ", " true ", "2", "enabled", "\t"])
def test_invalid_egress_value_has_total_precedence(
    tmp_path: Path, invalid_value: str
) -> None:
    completed = _run_gate(
        tmp_path,
        args=["--unknown"],
        env_updates={
            "CONNECTOR_LIVE_EGRESS_ENABLED": invalid_value,
            AUTHORITY_VARIABLES[0]: "secret-authority",
        },
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_egress_flag_invalid")
    assert completed.stderr == b""
    assert invalid_value.encode() not in completed.stdout


@pytest.mark.parametrize("authority_name", AUTHORITY_VARIABLES)
def test_each_nonempty_authority_variable_refuses_without_disclosure(
    tmp_path: Path, authority_name: str
) -> None:
    secret = f"secret-{authority_name}"
    completed = _run_gate(
        tmp_path,
        args=["--unknown"],
        env_updates={authority_name: secret},
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_send_authority_environment_present")
    assert completed.stderr == b""
    assert authority_name.encode() not in completed.stdout
    assert secret.encode() not in completed.stdout


def test_whitespace_authority_is_present_and_empty_authority_is_absent(
    tmp_path: Path,
) -> None:
    present = _run_gate(tmp_path, env_updates={AUTHORITY_VARIABLES[0]: " "})
    absent = _run_gate(tmp_path, env_updates={AUTHORITY_VARIABLES[0]: ""})

    assert present.stdout == _refusal("dual_live_send_authority_environment_present")
    assert absent.stdout == _refusal("dual_live_database_missing")


@pytest.mark.parametrize(
    ("args", "code"),
    [
        (["--help"], "dual_live_arguments_invalid"),
        (["--"], "dual_live_arguments_invalid"),
        (["positional"], "dual_live_arguments_invalid"),
        ([f"--campaign-id={CAMPAIGN_ID}"], "dual_live_arguments_invalid"),
        (["--campaign-i", CAMPAIGN_ID], "dual_live_arguments_invalid"),
        (["--unknown", "value"], "dual_live_arguments_invalid"),
        (
            [
                "--campaign-id",
                CAMPAIGN_ID,
                "--campaign-id",
                CAMPAIGN_ID,
                "--campaign-fingerprint",
                CAMPAIGN_FINGERPRINT,
            ],
            "dual_live_arguments_invalid",
        ),
        ([], "dual_live_campaign_id_missing"),
        (["--campaign-fingerprint", CAMPAIGN_FINGERPRINT], "dual_live_campaign_id_missing"),
        (["--campaign-id"], "dual_live_campaign_id_missing"),
        (
            ["--campaign-id", "--campaign-fingerprint", CAMPAIGN_FINGERPRINT],
            "dual_live_campaign_id_missing",
        ),
        (
            ["--campaign-id", "", "--campaign-fingerprint", CAMPAIGN_FINGERPRINT],
            "dual_live_campaign_id_invalid",
        ),
        (["--campaign-id", CAMPAIGN_ID], "dual_live_campaign_fingerprint_missing"),
        (
            ["--campaign-id", CAMPAIGN_ID, "--campaign-fingerprint"],
            "dual_live_campaign_fingerprint_missing",
        ),
        (
            ["--campaign-id", CAMPAIGN_ID, "--campaign-fingerprint", ""],
            "dual_live_campaign_fingerprint_invalid",
        ),
    ],
)
def test_strict_argument_grammar_and_field_refusals(
    tmp_path: Path, args: list[str], code: str
) -> None:
    completed = _run_gate(tmp_path, args=args)

    assert completed.returncode == 2
    assert completed.stdout == _refusal(code)
    assert completed.stderr == b""


@pytest.mark.parametrize(
    "campaign_id",
    [
        CAMPAIGN_ID.upper(),
        "123e4567-e89b-12d3-a456-426614174000",
        "{123e4567-e89b-42d3-a456-426614174000}",
        "123e4567e89b42d3a456426614174000",
    ],
)
def test_cli_rejects_noncanonical_or_non_v4_uuid_forms(
    tmp_path: Path, campaign_id: str
) -> None:
    completed = _run_gate(
        tmp_path,
        args=[
            "--campaign-id",
            campaign_id,
            "--campaign-fingerprint",
            CAMPAIGN_FINGERPRINT,
        ],
    )

    assert completed.stdout == _refusal("dual_live_campaign_id_invalid")


def test_invalid_id_precedes_missing_fingerprint(tmp_path: Path) -> None:
    completed = _run_gate(tmp_path, args=["--campaign-id", "not-a-uuid"])

    assert completed.stdout == _refusal("dual_live_campaign_id_invalid")


@pytest.mark.parametrize(
    "campaign_fingerprint",
    ["A" * 64, "a" * 63, "a" * 65, ("a" * 63) + "g"],
)
def test_cli_rejects_noncanonical_fingerprint(
    tmp_path: Path, campaign_fingerprint: str
) -> None:
    completed = _run_gate(
        tmp_path,
        args=[
            "--campaign-id",
            CAMPAIGN_ID,
            "--campaign-fingerprint",
            campaign_fingerprint,
        ],
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_campaign_fingerprint_invalid")
    assert completed.stderr == b""


def test_import_is_side_effect_free() -> None:
    probe = f"""
import importlib.util
import io
import json
import socket
import sys
from contextlib import redirect_stderr, redirect_stdout
before = (socket.socket.connect, socket.getaddrinfo, sys.dont_write_bytecode)
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
stdout = io.StringIO()
stderr = io.StringIO()
with redirect_stdout(stdout), redirect_stderr(stderr):
    spec.loader.exec_module(module)
after = (socket.socket.connect, socket.getaddrinfo, sys.dont_write_bytecode)
print(json.dumps({{
    "guard_unchanged": before == after,
    "stdout": stdout.getvalue(),
    "stderr": stderr.getvalue(),
    "requests_loaded": "requests" in sys.modules,
    "app_loaded": any(name == "app" or name.startswith("app.") for name in sys.modules),
}}))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "guard_unchanged": True,
        "stdout": "",
        "stderr": "",
        "requests_loaded": False,
        "app_loaded": False,
    }
    assert completed.stderr == ""


def test_early_refusal_installs_only_low_level_guard() -> None:
    probe = f"""
import contextlib
import importlib.util
import io
import json
import socket
import sys
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
output = io.StringIO()
with contextlib.redirect_stdout(output):
    result = module.main(["--unknown"], {{}})
try:
    socket.getaddrinfo("example.invalid", 443)
except OSError as exc:
    denial = [type(exc).__name__, getattr(exc, "code", None), str(exc)]
else:
    denial = None
print(json.dumps({{
    "result": result,
    "output": output.getvalue(),
    "denial": denial,
    "requests_loaded": "requests" in sys.modules,
    "evaluator_loaded": "app.services.dual_live_evaluator" in sys.modules,
}}))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["result"] == 2
    assert payload["output"] == _captured_refusal("dual_live_arguments_invalid")
    assert payload["denial"] == [
        "DualLiveNetworkDenied",
        "dual_live_network_denied",
        "dual_live_network_denied",
    ]
    assert payload["requests_loaded"] is False
    assert payload["evaluator_loaded"] is False
    assert completed.stderr == ""


def test_full_guard_is_idempotent_and_denies_all_required_entrypoints() -> None:
    probe = f"""
import importlib.util
import json
import socket
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module._install_network_guard()
import requests
identities = (socket.socket.connect, socket.getaddrinfo, requests.Session.send)
module._install_network_guard()
idempotent = identities == (socket.socket.connect, socket.getaddrinfo, requests.Session.send)
sock = socket.socket()
session = requests.Session()
adapter = requests.adapters.HTTPAdapter()
probes = [
    lambda: sock.connect(("127.0.0.1", 1)),
    lambda: sock.connect_ex(("127.0.0.1", 1)),
    lambda: sock.bind(("127.0.0.1", 0)),
    lambda: sock.sendto(b"x", ("127.0.0.1", 1)),
    lambda: socket.create_connection(("127.0.0.1", 1)),
    lambda: socket.getaddrinfo("example.invalid", 443),
    lambda: socket.gethostbyname("example.invalid"),
    lambda: socket.gethostbyname_ex("example.invalid"),
    lambda: socket.gethostbyaddr("127.0.0.1"),
    lambda: socket.getnameinfo(("127.0.0.1", 1), 0),
    lambda: socket.getfqdn("example.invalid"),
    lambda: requests.api.request("GET", "https://example.invalid"),
    lambda: requests.request("GET", "https://example.invalid"),
    lambda: session.request("GET", "https://example.invalid"),
    lambda: session.send(requests.Request("GET", "https://example.invalid").prepare()),
    lambda: adapter.send(requests.Request("GET", "https://example.invalid").prepare()),
]
denials = []
for invoke in probes:
    try:
        invoke()
    except OSError as exc:
        denials.append([type(exc).__name__, getattr(exc, "code", None), str(exc)])
    else:
        denials.append(None)
sock.close()
session.close()
adapter.close()
print(json.dumps({{"idempotent": idempotent, "denials": denials}}))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["idempotent"] is True
    assert payload["denials"] == [
        ["DualLiveNetworkDenied", "dual_live_network_denied", "dual_live_network_denied"]
    ] * 16
    assert completed.stderr == ""


def test_g02_connector_transport_guard_precedes_observer_counter_and_reservation() -> None:
    probe = f"""
import importlib.util
import json
import sys
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    module._install_connector_transport_guard()
except RuntimeError:
    prerequisite_refused = True
else:
    prerequisite_refused = False
transport_preloaded = "app.services.connector_egress_transport" in sys.modules
module._install_network_guard()
module._backend_path()
module._install_connector_transport_guard()
from app.services import connector_egress_transport as transport
observer_calls = []
reservation_calls = []
original_reserve = transport.reserve_physical_request
transport.reserve_physical_request = lambda **kwargs: reservation_calls.append(kwargs)
counter = transport._DeliveredByteCounter()
adapter = transport.CountingHTTPAdapter(
    observe_prepared=lambda request: observer_calls.append(request),
    counter=counter,
)
denials = []
for invoke in (
    lambda: adapter.send(object()),
    lambda: transport.BoundedConnectorTransport.send_once(
        object(), ordinal=1, stage="detail", request=object()
    ),
):
    try:
        invoke()
    except OSError as exc:
        denials.append([type(exc).__name__, getattr(exc, "code", None), str(exc)])
    else:
        denials.append(None)
transport.reserve_physical_request = original_reserve
guard_hook = transport.CountingHTTPAdapter.send
transport.CountingHTTPAdapter.send = lambda *args, **kwargs: None
tamper_detected = not module._network_guard_intact()
transport.CountingHTTPAdapter.send = guard_hook
print(json.dumps({{
    "adapter_hook": transport.CountingHTTPAdapter.send is module._deny_network,
    "transport_hook": transport.BoundedConnectorTransport.send_once is module._deny_network,
    "guard_intact": module._network_guard_intact(),
    "tamper_detected": tamper_detected,
    "denials": denials,
    "observer_calls": len(observer_calls),
    "reservation_calls": len(reservation_calls),
    "delivered_body_bytes": counter.delivered_body_bytes,
    "network_send_started": adapter.network_send_started,
    "counter_runtime_records": len(transport._COUNTER_RUNTIME_RECORDS),
    "prerequisite_refused": prerequisite_refused,
    "transport_preloaded": transport_preloaded,
}}))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload == {
        "adapter_hook": True,
        "transport_hook": True,
        "guard_intact": True,
        "tamper_detected": True,
        "denials": [
            [
                "DualLiveNetworkDenied",
                "dual_live_network_denied",
                "dual_live_network_denied",
            ]
        ]
        * 2,
        "observer_calls": 0,
        "reservation_calls": 0,
        "delivered_body_bytes": 0,
        "network_send_started": False,
        "counter_runtime_records": 0,
        "prerequisite_refused": True,
        "transport_preloaded": False,
    }
    assert completed.stderr == ""


def test_connector_transport_import_does_not_bind_runtime_settings_or_database() -> None:
    probe = f"""
import json
import sys
sys.path.insert(0, {str(BACKEND)!r})
from app.services import connector_egress_transport as transport
print(json.dumps({{
    "config_loaded": "app.core.config" in sys.modules,
    "db_session_loaded": "app.db.session" in sys.modules,
    "factory_name": transport.SESSION_FACTORY.__name__,
}}))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-W", "ignore", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "config_loaded": False,
        "db_session_loaded": False,
        "factory_name": "_default_session_factory",
    }
    assert completed.stderr == ""


def test_missing_runtime_refuses_before_transport_or_evaluator_import() -> None:
    probe = f"""
import contextlib
import importlib.util
import io
import json
import sys
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
output = io.StringIO()
with contextlib.redirect_stdout(output):
    result = module.main({_valid_args()!r}, {{}})
transport = sys.modules.get("app.services.connector_egress_transport")
print(json.dumps({{
    "result": result,
    "output": output.getvalue(),
    "transport_loaded": transport is not None,
    "db_session_loaded": "app.db.session" in sys.modules,
    "evaluator_loaded": "app.services.dual_live_evaluator" in sys.modules,
}}))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["result"] == 2
    assert payload["output"] == _captured_refusal("dual_live_database_missing")
    assert payload["transport_loaded"] is False
    assert payload["db_session_loaded"] is False
    assert payload["evaluator_loaded"] is False
    assert completed.stderr == ""


@pytest.mark.parametrize(
    "forbidden_module",
    [
        "app.core.config",
        "app.db.session",
        "app.services.some_connector",
        "sqlalchemy",
    ],
)
def test_valid_main_rejects_preloaded_forbidden_modules(
    forbidden_module: str,
) -> None:
    probe = f"""
import contextlib
import importlib.util
import io
import json
import sys
import types
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.modules[{forbidden_module!r}] = types.ModuleType({forbidden_module!r})
output = io.StringIO()
with contextlib.redirect_stdout(output):
    result = module.main({_valid_args()!r}, {{}})
print(json.dumps({{"result": result, "output": output.getvalue()}}))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["result"] == 2
    assert payload["output"] == _captured_refusal("dual_live_gate_internal_error")
    assert forbidden_module not in payload["output"]
    assert completed.stderr == ""


def test_guard_reverification_detects_replacement() -> None:
    probe = f"""
import contextlib
import importlib.util
import io
import json
import socket
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module._install_low_level_guard()
socket.getaddrinfo = lambda *args, **kwargs: []
output = io.StringIO()
with contextlib.redirect_stdout(output):
    result = module.main({_valid_args()!r}, {{}})
print(json.dumps({{"result": result, "output": output.getvalue()}}))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["result"] == 2
    assert payload["output"] == _captured_refusal("dual_live_gate_internal_error")
    assert completed.stderr == ""


def test_report_drift_is_internal_refusal() -> None:
    gate = _load_gate_contract_module()

    assert not gate._report_is_exact(
        {"status": "PASS"},
        campaign_id=CAMPAIGN_ID,
        campaign_fingerprint=CAMPAIGN_FINGERPRINT,
    )


def test_unexpected_valid_path_failure_is_secret_safe() -> None:
    probe = f"""
import contextlib
import importlib.util
import io
import json
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
secret = "must-not-escape"
def fail_guard():
    raise RuntimeError(secret)
module._install_network_guard = fail_guard
output = io.StringIO()
with contextlib.redirect_stdout(output):
    result = module.main({_valid_args()!r}, {{}})
print(json.dumps({{"result": result, "output": output.getvalue()}}))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["result"] == 2
    assert payload["output"] == _captured_refusal("dual_live_gate_internal_error")
    assert "must-not-escape" not in payload["output"]
    assert completed.stderr == ""


def test_run_action_prechecks_missing_id_without_child_or_side_effect(
    tmp_path: Path,
) -> None:
    completed = _run_powershell(
        tmp_path,
        action="run-dual-live-proof",
        empty_path=True,
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_campaign_id_missing")
    assert completed.stderr == b""
    assert list(tmp_path.iterdir()) == []


def test_run_action_contains_mandated_isolated_launcher_shape() -> None:
    source = PROJECT6.read_text(encoding="utf-8")
    required = """Push-Location $RepoRoot
        try {
            & py "-$PythonVersion" -I -B .\\tools\\dual_live_run.py --campaign-id $env:DUAL_LIVE_CAMPAIGN_ID --campaign-fingerprint $env:DUAL_LIVE_CAMPAIGN_FINGERPRINT
            $DualLiveRunExitCode = $LASTEXITCODE
        }
        finally {
            Pop-Location
        }
        exit $DualLiveRunExitCode"""

    assert required in source


@pytest.mark.parametrize(
    ("env_updates", "code"),
    [
        ({}, "dual_live_campaign_id_missing"),
        ({"DUAL_LIVE_CAMPAIGN_ID": CAMPAIGN_ID}, "dual_live_campaign_fingerprint_missing"),
    ],
)
def test_validate_action_prechecks_missing_environment_without_child(
    tmp_path: Path, env_updates: dict[str, str], code: str
) -> None:
    completed = _run_powershell(
        tmp_path,
        action="validate-dual-live-proof",
        env_updates=env_updates,
        empty_path=True,
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal(code)
    assert completed.stderr == b""
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("action", ["run-dual-live-proof", "validate-dual-live-proof"])
def test_powershell_actions_reject_remaining_arguments(
    tmp_path: Path, action: str
) -> None:
    completed = _run_powershell(
        tmp_path,
        action=action,
        env_updates={
            "DUAL_LIVE_CAMPAIGN_ID": CAMPAIGN_ID,
            "DUAL_LIVE_CAMPAIGN_FINGERPRINT": CAMPAIGN_FINGERPRINT,
        },
        empty_path=True,
        action_args=["unexpected"],
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_arguments_invalid")
    assert completed.stderr == b""
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows py-launcher proof only")
def test_validate_action_directly_preserves_gate_output_exit_and_cwd(
    tmp_path: Path,
) -> None:
    completed = _run_powershell(
        tmp_path,
        action="validate-dual-live-proof",
        env_updates={
            "DUAL_LIVE_CAMPAIGN_ID": CAMPAIGN_ID,
            "DUAL_LIVE_CAMPAIGN_FINGERPRINT": CAMPAIGN_FINGERPRINT,
            "CONNECTOR_LIVE_EGRESS_ENABLED": "off",
            "PYTHONPATH": "",
        },
    )

    assert completed.returncode == 2
    assert completed.stdout == _refusal("dual_live_database_missing")
    assert completed.stderr == b""
    assert list(tmp_path.iterdir()) == []


def test_validate_action_contains_mandated_direct_launcher_shape() -> None:
    source = PROJECT6.read_text(encoding="utf-8")
    required = """Push-Location $RepoRoot
        try {
            & py "-$PythonVersion" -I -B .\\tools\\dual_live_gate.py --campaign-id $env:DUAL_LIVE_CAMPAIGN_ID --campaign-fingerprint $env:DUAL_LIVE_CAMPAIGN_FINGERPRINT
            $DualLiveGateExitCode = $LASTEXITCODE
        }
        finally {
            Pop-Location
        }
        exit $DualLiveGateExitCode"""

    assert required in source


def test_powershell_declares_each_dual_live_action_once() -> None:
    source = PROJECT6.read_text(encoding="utf-8")
    validate_set = source.split("[ValidateSet(", 1)[1].split(")]", 1)[0]

    assert validate_set.count('"run-dual-live-proof"') == 1
    assert validate_set.count('"validate-dual-live-proof"') == 1
    assert source.count('\n    "run-dual-live-proof" {') == 1
    assert source.count('\n    "validate-dual-live-proof" {') == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_job_owner_exists_before_create_process_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class OwnerProbe(RuntimeError):
        pass

    kernel32 = dual_live_windows._kernel32
    original_owner = dual_live_windows._ProvisionalJobOwner
    original_create = kernel32.CreateProcessW
    create_calls = 0

    def reject_owner(*_args: object, **_kwargs: object) -> None:
        raise OwnerProbe("owner allocation refused")

    def fake_create_process(*arguments: object) -> int:
        nonlocal create_calls
        create_calls += 1
        process_info = ctypes.cast(
            arguments[-1],
            ctypes.POINTER(dual_live_windows._PROCESS_INFORMATION),
        ).contents
        process_info.hProcess = 0x7FFF1234
        process_info.hThread = 0x7FFF1235
        process_info.dwProcessId = 424242
        return 1

    monkeypatch.setattr(dual_live_windows, "_ProvisionalJobOwner", reject_owner)
    monkeypatch.setattr(kernel32, "CreateProcessW", fake_create_process)
    read_handle, write_handle = _inheritable_pipe()
    try:
        with pytest.raises(OwnerProbe):
            create_child_in_job(
                argv=(sys.executable, "-B", "-c", "raise SystemExit(0)"),
                environment=_job_environment(),
                inherited_handles=(write_handle,),
                runtime_instance_id=RUNTIME_INSTANCE_ID,
                wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
            )
        assert create_calls == 0
    finally:
        monkeypatch.setattr(dual_live_windows, "_ProvisionalJobOwner", original_owner)
        monkeypatch.setattr(kernel32, "CreateProcessW", original_create)
        kernel32.CloseHandle(read_handle)
        kernel32.CloseHandle(write_handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_create_persistent_cleanup_retains_map_and_blocks_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel32 = dual_live_windows._kernel32
    original_create_pipe = kernel32.CreatePipe
    original_close = kernel32.CloseHandle
    created: list[int] = []
    create_calls = 0
    target = 0

    def create_one_pipe_then_fail(*arguments: object) -> int:
        nonlocal create_calls, target
        create_calls += 1
        if create_calls == 2:
            ctypes.set_last_error(5)
            return 0
        result = int(original_create_pipe(*arguments))
        assert result
        read_handle = ctypes.cast(
            arguments[0], ctypes.POINTER(ctypes.wintypes.HANDLE)
        ).contents.value
        write_handle = ctypes.cast(
            arguments[1], ctypes.POINTER(ctypes.wintypes.HANDLE)
        ).contents.value
        assert read_handle is not None and write_handle is not None
        created.extend((int(read_handle), int(write_handle)))
        target = int(read_handle)
        return result

    def retain_target(handle: object) -> int:
        if int(handle) == target:
            ctypes.set_last_error(5)
            return 0
        return int(original_close(handle))

    monkeypatch.setattr(kernel32, "CreatePipe", create_one_pipe_then_fail)
    monkeypatch.setattr(kernel32, "CloseHandle", retain_target)
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_channels_cleanup_failed",
        ):
            dual_live_windows.create_phase_channels("B")
        custodies = dual_live_windows._failed_phase_handle_custodies
        assert len(custodies) == 1
        assert target in custodies[0].handles.values()

        blocked_calls = 0

        def unexpected_create(*_arguments: object) -> int:
            nonlocal blocked_calls
            blocked_calls += 1
            ctypes.set_last_error(5)
            return 0

        monkeypatch.setattr(kernel32, "CreatePipe", unexpected_create)
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_channels_cleanup_failed",
        ):
            dual_live_windows.create_phase_channels("B")
        assert blocked_calls == 0

        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        dual_live_windows._retry_failed_phase_handle_custodies()
        assert dual_live_windows._failed_phase_handle_custodies == []
        flags = ctypes.wintypes.DWORD()
        assert not kernel32.GetHandleInformation(target, ctypes.byref(flags))
    finally:
        monkeypatch.setattr(kernel32, "CreatePipe", original_create_pipe)
        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        retry = getattr(
            dual_live_windows,
            "_retry_failed_phase_handle_custodies",
            None,
        )
        if callable(retry):
            retry()
        flags = ctypes.wintypes.DWORD()
        for handle in created:
            if kernel32.GetHandleInformation(handle, ctypes.byref(flags)):
                original_close(handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_partial_duplicate_persistent_cleanup_retains_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = dual_live_windows.create_phase_channels("B")
    kernel32 = dual_live_windows._kernel32
    original_duplicate = kernel32.DuplicateHandle
    original_close = kernel32.CloseHandle
    duplicate_calls = 0
    copied: list[int] = []
    target = 0

    def create_one_pair_then_fail(*arguments: object) -> int:
        nonlocal duplicate_calls, target
        duplicate_calls += 1
        if duplicate_calls == 3:
            ctypes.set_last_error(5)
            return 0
        result = int(original_duplicate(*arguments))
        assert result
        handle = ctypes.cast(
            arguments[3], ctypes.POINTER(ctypes.wintypes.HANDLE)
        ).contents.value
        assert handle is not None
        copied.append(int(handle))
        if duplicate_calls == 1:
            target = int(handle)
        return result

    def retain_target(handle: object) -> int:
        if int(handle) == target:
            ctypes.set_last_error(5)
            return 0
        return int(original_close(handle))

    monkeypatch.setattr(kernel32, "DuplicateHandle", create_one_pair_then_fail)
    monkeypatch.setattr(kernel32, "CloseHandle", retain_target)
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_channels_cleanup_failed",
        ):
            with _lease_wrapper_handles(channels):
                pass
        custodies = dual_live_windows._failed_phase_handle_custodies
        assert len(custodies) == 1
        assert target in custodies[0].handles.values()

        blocked_calls = 0

        def unexpected_duplicate(*_arguments: object) -> int:
            nonlocal blocked_calls
            blocked_calls += 1
            ctypes.set_last_error(5)
            return 0

        monkeypatch.setattr(kernel32, "DuplicateHandle", unexpected_duplicate)
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_channels_cleanup_failed",
        ):
            with _lease_wrapper_handles(channels):
                pass
        assert blocked_calls == 0

        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        dual_live_windows._retry_failed_phase_handle_custodies()
        assert dual_live_windows._failed_phase_handle_custodies == []
    finally:
        monkeypatch.setattr(kernel32, "DuplicateHandle", original_duplicate)
        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        retry = getattr(
            dual_live_windows,
            "_retry_failed_phase_handle_custodies",
            None,
        )
        if callable(retry):
            retry()
        flags = ctypes.wintypes.DWORD()
        for handle in copied:
            if kernel32.GetHandleInformation(handle, ctypes.byref(flags)):
                original_close(handle)
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_phase_postyield_retry_preserves_recycled_unrelated_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channels = dual_live_windows.create_phase_channels("B")
    kernel32 = dual_live_windows._kernel32
    original_duplicate = kernel32.DuplicateHandle
    original_close = kernel32.CloseHandle
    copied: list[int] = []
    recycled_events: list[int] = []
    target = 0
    victim = 0

    def capture_duplicate(*arguments: object) -> int:
        result = int(original_duplicate(*arguments))
        assert result
        copied_handle = ctypes.cast(
            arguments[3], ctypes.POINTER(ctypes.wintypes.HANDLE)
        ).contents.value
        assert copied_handle is not None
        copied.append(int(copied_handle))
        return result

    def retain_target(handle: object) -> int:
        if int(handle) == target:
            ctypes.set_last_error(5)
            return 0
        return int(original_close(handle))

    monkeypatch.setattr(kernel32, "DuplicateHandle", capture_duplicate)
    monkeypatch.setattr(kernel32, "CloseHandle", retain_target)
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_channels_cleanup_failed",
        ):
            with _lease_wrapper_handles(channels) as handles:
                target = handles["wrapper_control_write_handle"]
        assert len(dual_live_windows._failed_phase_handle_custodies) == 1
        custody = dual_live_windows._failed_phase_handle_custodies[0]
        assert custody.mode == "guarded_yield"
        assert target in custody.handles.values()
        assert custody.guards

        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        assert original_close(target)
        for _ in range(2048):
            candidate = kernel32.CreateEventW(None, True, False, None)
            assert candidate
            value = int(candidate)
            recycled_events.append(value)
            if value == target:
                victim = value
                break
        assert victim == target

        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_phase_channels_lease_compromised",
        ):
            dual_live_windows._retry_failed_phase_handle_custodies()
        assert dual_live_windows._failed_phase_handle_custodies == []
        flags = ctypes.wintypes.DWORD()
        assert kernel32.GetHandleInformation(victim, ctypes.byref(flags))
        assert kernel32.WaitForSingleObject(victim, 0) == dual_live_windows._WAIT_TIMEOUT
    finally:
        monkeypatch.setattr(kernel32, "DuplicateHandle", original_duplicate)
        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        try:
            dual_live_windows._retry_failed_phase_handle_custodies()
        except DualLiveWindowsError:
            pass
        flags = ctypes.wintypes.DWORD()
        for handle in (*copied, *recycled_events):
            if kernel32.GetHandleInformation(handle, ctypes.byref(flags)):
                original_close(handle)
        channels.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_control_constructor_cleanup_failure_retains_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import dual_live_runtime

    child = dual_live_windows._create_owned_phase_process(
        "B",
        RUNTIME_INSTANCE_ID,
        WRAPPER_NONCE_SHA,
    )
    assert dual_live_runtime._read_pipe_frame(
        child.readers["app"],
        allowed_reserved_schema_ids=frozenset(
            (dual_live_runtime.CHILD_STATUS_SCHEMA_ID,)
        ),
    ) is not None
    kernel32 = dual_live_windows._kernel32
    original_duplicate = kernel32.DuplicateHandle
    original_close = kernel32.CloseHandle
    original_thread = threading.Thread
    duplicate_calls = 0
    target = 0

    def capture_duplicate(*arguments: object) -> int:
        nonlocal duplicate_calls, target
        duplicate_calls += 1
        result = int(original_duplicate(*arguments))
        assert result
        copied = ctypes.cast(
            arguments[3], ctypes.POINTER(ctypes.wintypes.HANDLE)
        ).contents.value
        assert copied is not None
        target = int(copied)
        return result

    def retain_target(handle: object) -> int:
        if int(handle) == target:
            ctypes.set_last_error(5)
            return 0
        return int(original_close(handle))

    def reject_thread(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("thread-constructor-failed")

    monkeypatch.setattr(kernel32, "DuplicateHandle", capture_duplicate)
    monkeypatch.setattr(kernel32, "CloseHandle", retain_target)
    monkeypatch.setattr(threading, "Thread", reject_thread)
    frame = dual_live_runtime.encode_child_control_frame(
        phase="B",
        command="GO",
        control_nonce=child.control_nonce,
    )
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_control_cleanup_failed",
        ) as exc:
            child.send_control(frame)
        assert isinstance(exc.value.__context__, DualLiveWindowsError)
        assert isinstance(exc.value.__context__.__context__, RuntimeError)
        assert target in dual_live_windows._retained_owned_handles

        blocked_calls = duplicate_calls
        monkeypatch.setattr(
            kernel32,
            "DuplicateHandle",
            lambda *_arguments: (_ for _ in ()).throw(
                AssertionError("allocation before custody drain")
            ),
        )
        source = child._control_write_handle
        assert source is not None
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_handle_cleanup_failed",
        ):
            dual_live_windows._duplicate_owned_handle(source)
        assert duplicate_calls == blocked_calls

        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        dual_live_windows._retry_retained_owned_handles()
        assert dual_live_windows._retained_owned_handles == set()
    finally:
        monkeypatch.setattr(kernel32, "DuplicateHandle", original_duplicate)
        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        monkeypatch.setattr(threading, "Thread", original_thread)
        dual_live_windows._retry_retained_owned_handles()
        flags = ctypes.wintypes.DWORD()
        if target and kernel32.GetHandleInformation(target, ctypes.byref(flags)):
            original_close(target)
        child.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows proof containment only")
def test_owned_factory_reader_failure_retains_unpopped_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ReaderProbe(RuntimeError):
        pass

    kernel32 = dual_live_windows._kernel32
    original_reader = dual_live_windows._OwnedPipeReader
    original_close = kernel32.CloseHandle
    target = 0

    def reject_reader(handle: int) -> None:
        nonlocal target
        target = handle
        raise ReaderProbe("reader construction failed")

    def retain_target(handle: object) -> int:
        if int(handle) == target:
            ctypes.set_last_error(5)
            return 0
        return int(original_close(handle))

    monkeypatch.setattr(dual_live_windows, "_OwnedPipeReader", reject_reader)
    monkeypatch.setattr(kernel32, "CloseHandle", retain_target)
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_owned_cleanup_failed",
        ) as exc:
            dual_live_windows._create_owned_phase_process(
                "B",
                RUNTIME_INSTANCE_ID,
                WRAPPER_NONCE_SHA,
            )
        assert isinstance(exc.value.__context__, ReaderProbe)
        assert target
        assert len(dual_live_windows._failed_owned_custodies) == 1
        custody = dual_live_windows._failed_owned_custodies[0]
        assert target in custody.handles.values()

        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        dual_live_windows._retry_failed_owned_custodies()
        assert dual_live_windows._failed_owned_custodies == []
    finally:
        monkeypatch.setattr(dual_live_windows, "_OwnedPipeReader", original_reader)
        monkeypatch.setattr(kernel32, "CloseHandle", original_close)
        dual_live_windows._retry_failed_owned_custodies()
        flags = ctypes.wintypes.DWORD()
        if target and kernel32.GetHandleInformation(target, ctypes.byref(flags)):
            original_close(target)


@pytest.mark.skipif(os.name != "nt", reason="Windows source custody only")
def test_reviewed_source_tree_derives_clean_head_and_wrapper_bytes(
    tmp_path: Path,
) -> None:
    repo, wrapper = _init_source_identity_repo(tmp_path)
    git_path = Path(r"C:\Program Files\Git\cmd\git.exe")
    wrapper_custody = dual_live_windows._open_executable_custody(str(wrapper))
    try:
        state = dual_live_windows._verify_reviewed_git_tree(
            repo,
            git_path,
            wrapper_custody,
        )
    finally:
        dual_live_windows._close_handle(wrapper_custody.handle)

    expected_revision = subprocess.run(
        [str(git_path), "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert state.code_revision == expected_revision
    assert state.wrapper_image_sha256 == hashlib.sha256(
        wrapper.read_bytes()
    ).hexdigest()


@pytest.mark.skipif(os.name != "nt", reason="Windows source custody only")
def test_reviewed_source_tree_computes_wrapper_oid_independently(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, wrapper = _init_source_identity_repo(tmp_path)
    git_path = Path(r"C:\Program Files\Git\cmd\git.exe")
    original_git = dual_live_windows._run_reviewed_git

    def no_hash_object(
        git_custody: object,
        repo_root: Path,
        *arguments: str,
        **kwargs: object,
    ) -> tuple[int, bytes]:
        assert arguments[:1] != ("hash-object",)
        return original_git(git_custody, repo_root, *arguments, **kwargs)

    monkeypatch.setattr(dual_live_windows, "_run_reviewed_git", no_hash_object)
    wrapper_custody = dual_live_windows._open_executable_custody(str(wrapper))
    try:
        state = dual_live_windows._verify_reviewed_git_tree(
            repo,
            git_path,
            wrapper_custody,
        )
    finally:
        dual_live_windows._close_handle(wrapper_custody.handle)

    assert state.wrapper_image_sha256 == hashlib.sha256(
        wrapper.read_bytes()
    ).hexdigest()


@pytest.mark.skipif(os.name != "nt", reason="Windows source custody only")
def test_reviewed_source_tree_refuses_hidden_tracked_source_drift(
    tmp_path: Path,
) -> None:
    repo, wrapper = _init_source_identity_repo(tmp_path)
    git_path = Path(r"C:\Program Files\Git\cmd\git.exe")
    hidden_source = repo / "README.md"
    marked = subprocess.run(
        [
            str(git_path),
            "update-index",
            "--assume-unchanged",
            "--",
            "README.md",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    assert marked.returncode == 0, marked.stderr
    hidden_source.write_bytes(b"VALUE = 2\n")
    wrapper_custody = dual_live_windows._open_executable_custody(str(wrapper))
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_source_identity_invalid",
        ):
            dual_live_windows._verify_reviewed_git_tree(
                repo,
                git_path,
                wrapper_custody,
            )
    finally:
        dual_live_windows._close_handle(wrapper_custody.handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows source custody only")
def test_reviewed_source_tree_refuses_process_launching_repo_config(
    tmp_path: Path,
) -> None:
    repo, wrapper = _init_source_identity_repo(tmp_path)
    git_path = Path(r"C:\Program Files\Git\cmd\git.exe")
    configured = subprocess.run(
        [
            str(git_path),
            "config",
            "--local",
            "filter.project6-evil.process",
            str(tmp_path / "must-not-run.exe"),
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    assert configured.returncode == 0, configured.stderr
    wrapper_custody = dual_live_windows._open_executable_custody(str(wrapper))
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_source_identity_invalid",
        ):
            dual_live_windows._verify_reviewed_git_tree(
                repo,
                git_path,
                wrapper_custody,
            )
    finally:
        dual_live_windows._close_handle(wrapper_custody.handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows source custody only")
def test_reviewed_source_tree_refuses_worktree_config_before_diff(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, wrapper = _init_source_identity_repo(tmp_path)
    git_path = Path(r"C:\Program Files\Git\cmd\git.exe")
    for arguments in (
        ("config", "extensions.worktreeConfig", "true"),
        ("config", "--worktree", "core.attributesFile", str(tmp_path / "attrs")),
        ("config", "--worktree", "diff.project6.command", "must-not-run.exe"),
    ):
        configured = subprocess.run(
            [str(git_path), *arguments],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        assert configured.returncode == 0, configured.stderr
    calls: list[tuple[str, ...]] = []
    original_git = dual_live_windows._run_reviewed_git

    def record_git(
        git_custody: object,
        repo_root: Path,
        *arguments: str,
        **kwargs: object,
    ) -> tuple[int, bytes]:
        calls.append(arguments)
        return original_git(git_custody, repo_root, *arguments, **kwargs)

    monkeypatch.setattr(dual_live_windows, "_run_reviewed_git", record_git)
    wrapper_custody = dual_live_windows._open_executable_custody(str(wrapper))
    try:
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_source_identity_invalid",
        ):
            dual_live_windows._verify_reviewed_git_tree(
                repo,
                git_path,
                wrapper_custody,
            )
    finally:
        dual_live_windows._close_handle(wrapper_custody.handle)

    assert not any(arguments[:1] == ("diff",) for arguments in calls)


def test_runtime_ignored_source_policy_allows_only_redirected_bytecode() -> None:
    assert dual_live_windows._runtime_ignored_path_allowed(
        b"backend/app/services/__pycache__/dual_live_runtime.cpython-311.pyc"
    )
    assert dual_live_windows._runtime_ignored_path_allowed(
        b"tools/__pycache__/dual_live_run.cpython-311.pyc"
    )
    for path in (
        b"backend/app/services/dual_live_runtime.py",
        b"backend/app/services/dual_live_runtime.pyd",
        b"backend/app/services/runtime.pyc",
        b"tools/dual_live_run.pyc",
        b"tools/__pycache__/dual_live_run.pth",
    ):
        assert not dual_live_windows._runtime_ignored_path_allowed(path)


@pytest.mark.skipif(os.name != "nt", reason="Windows source custody only")
def test_reviewed_controller_requires_isolated_redirected_bytecode() -> None:
    with pytest.raises(
        DualLiveWindowsError,
        match="dual_live_source_identity_invalid",
    ):
        dual_live_windows._require_reviewed_controller_python_posture()

    script = (
        "import sys;"
        f"sys.path.insert(0, {str(BACKEND)!r});"
        "from app.services import dual_live_windows as windows;"
        "windows._require_reviewed_controller_python_posture()"
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-X",
            "pycache_prefix=NUL",
            "-c",
            script,
        ],
        cwd=ROOT,
        env=_job_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(os.name != "nt", reason="Windows source custody only")
def test_reviewed_source_custody_uses_kernel_process_image(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, wrapper = _init_source_identity_repo(tmp_path)
    actual_image = dual_live_windows._current_process_image_path()
    monkeypatch.setattr(dual_live_windows, "_reviewed_repo_root", lambda: repo)
    monkeypatch.setattr(
        dual_live_windows,
        "_require_reviewed_controller_python_posture",
        lambda: None,
    )
    monkeypatch.setattr(sys, "executable", str(tmp_path / "forged-python.exe"))

    custody = dual_live_windows._acquire_reviewed_source_custody()
    try:
        assert custody.wrapper_image_sha256 == hashlib.sha256(
            wrapper.read_bytes()
        ).hexdigest()
        assert custody.interpreter_image_sha256 == hashlib.sha256(
            actual_image.read_bytes()
        ).hexdigest()
        custody.assert_stable()
    finally:
        custody.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows source custody only")
def test_reviewed_source_custody_refuses_tracked_drift_after_acquisition(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, _wrapper = _init_source_identity_repo(tmp_path)
    monkeypatch.setattr(dual_live_windows, "_reviewed_repo_root", lambda: repo)
    monkeypatch.setattr(
        dual_live_windows,
        "_require_reviewed_controller_python_posture",
        lambda: None,
    )
    custody = dual_live_windows._acquire_reviewed_source_custody()
    try:
        (repo / "README.md").write_bytes(b"drift after acquisition\n")
        with pytest.raises(
            DualLiveWindowsError,
            match="dual_live_source_identity_invalid",
        ):
            custody.assert_stable()
    finally:
        custody.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows source custody only")
def test_owned_child_argv_uses_kernel_process_image(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    actual_image = dual_live_windows._current_process_image_path()
    monkeypatch.setattr(sys, "executable", str(tmp_path / "forged-python.exe"))

    argv = dual_live_windows._owned_child_argv("opaque-capsule")

    assert argv[0] == str(actual_image)
    assert argv[1:5] == ("-I", "-B", "-X", "pycache_prefix=NUL")
