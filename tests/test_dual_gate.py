from __future__ import annotations

import ast
import ctypes
import hashlib
import inspect
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.dual_live_windows import (  # noqa: E402
    DualLiveWindowsError,
    JobChild,
    ProofLocks,
    acquire_proof_locks,
    create_child_in_job,
    prove_child_quiescence,
)
from app.services import dual_live_windows  # noqa: E402
from app.services.dual_live_runtime import WINDOWS_MIB_TCP_STATES  # noqa: E402


GATE = ROOT / "tools" / "dual_live_gate.py"
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
FIRST_TRANCHE_REQUIRED_PRODUCTION_PATHS = (
    "backend/app/services/dual_live_runtime.py",
)
ALLOWED_CHANGED_PRODUCTION_PATHS = frozenset(
    (
        *ALLOWED_NEW_PRODUCTION_PATHS,
        "backend/app/services/connector_egress_authorization.py",
        "backend/app/services/connector_egress_transport.py",
        "backend/app/services/connector_egress_arming.py",
        "backend/app/services/connector_campaign_log_capture.py",
        "backend/app/services/dual_live_evaluator.py",
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


def test_proof_locks_public_constructor_is_exact_and_inert_close_is_idempotent() -> None:
    assert tuple(inspect.signature(ProofLocks).parameters) == (
        "root_identity_sha256",
        "campaign_identity_sha256",
    )
    locks = ProofLocks("a" * 64, "b" * 64)
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
            dual_live_windows.canonical_json_bytes(
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
            dual_live_windows.canonical_json_bytes(
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
            dual_live_windows.canonical_json_bytes(
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
        with pytest.raises(DualLiveWindowsError, match="dual_live_child_timeout"):
            child.wait(0.01)
        child.terminate_tree()
        assert isinstance(child.wait(5), int)
        _assert_quiescence_record(prove_child_quiescence(child))


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
    included_read = ctypes.c_void_p()
    included_write = ctypes.c_void_p()
    excluded_read = ctypes.c_void_p()
    excluded_write = ctypes.c_void_p()
    assert dual_live_windows._kernel32.CreatePipe(
        ctypes.byref(included_read),
        ctypes.byref(included_write),
        ctypes.byref(security),
        0,
    )
    assert dual_live_windows._kernel32.CreatePipe(
        ctypes.byref(excluded_read),
        ctypes.byref(excluded_write),
        ctypes.byref(security),
        0,
    )
    child_code = """
import ctypes
import sys

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
flags = ctypes.c_ulong()
included = kernel32.GetHandleInformation(ctypes.c_void_p(int(sys.argv[1])), ctypes.byref(flags))
excluded = kernel32.GetHandleInformation(ctypes.c_void_p(int(sys.argv[2])), ctypes.byref(flags))
raise SystemExit(0 if included and not excluded else 9)
"""
    handles = (
        included_read.value,
        included_write.value,
        excluded_read.value,
        excluded_write.value,
    )
    try:
        child = create_child_in_job(
            argv=(
                sys.executable,
                "-B",
                "-c",
                child_code,
                str(included_write.value),
                str(excluded_write.value),
            ),
            environment=_job_environment(),
            inherited_handles=(int(included_write.value),),
            runtime_instance_id=RUNTIME_INSTANCE_ID,
            wrapper_nonce_sha256=WRAPPER_NONCE_SHA,
        )
        with child:
            assert child.wait(5) == 0
            flags = ctypes.c_ulong()
            assert dual_live_windows._kernel32.GetHandleInformation(
                child._job_handle, ctypes.byref(flags)
            )
            assert flags.value & 1 == 0
    finally:
        for handle in handles:
            dual_live_windows._kernel32.CloseHandle(handle)


def _compact(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode()
        + os.linesep.encode()
    )


def _refusal(code: str) -> bytes:
    return _compact(
        {
            "code": code,
            "fresh_live": False,
            "schema_id": "project6.dual_live_gate_refusal.v1",
            "status": "REFUSED",
        }
    )


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
    for name in AUTHORITY_VARIABLES:
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
        [sys.executable, "-B", str(GATE), *(args if args is not None else _valid_args())],
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


def test_valid_gate_is_exact_inert_and_cwd_independent(tmp_path: Path) -> None:
    completed = _run_gate(
        tmp_path,
        env_updates={"CONNECTOR_LIVE_EGRESS_ENABLED": "OFF", "PYTHONPATH": ""},
    )

    assert completed.returncode == 2
    assert completed.stdout == _compact(EXPECTED_REPORT)
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
    assert completed.stdout == _compact(EXPECTED_REPORT)
    assert completed.stderr == b""


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
    assert absent.stdout == _compact(EXPECTED_REPORT)


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


def test_valid_main_imports_only_inert_app_surface() -> None:
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
forbidden = [
    name for name in sys.modules
    if name in ("app.core.config", "app.db.session")
    or name == "sqlalchemy"
    or name.startswith("sqlalchemy.")
    or (name.startswith("app.") and "connector" in name)
]
print(json.dumps({{"result": result, "output": output.getvalue(), "forbidden": forbidden}}))
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
    assert payload["output"] == _captured(EXPECTED_REPORT)
    assert payload["forbidden"] == []
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
    probe = f"""
import contextlib
import importlib.util
import io
import json
spec = importlib.util.spec_from_file_location("dual_live_gate_probe", {str(GATE)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module._evaluate = lambda **kwargs: {{"status": "PASS"}}
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
    assert "must-not-escape" not in payload["output"]
    assert completed.stderr == ""


def test_run_action_is_exact_refusal_without_child_or_side_effect(
    tmp_path: Path,
) -> None:
    completed = _run_powershell(
        tmp_path,
        action="run-dual-live-proof",
        env_updates={
            "DUAL_LIVE_CAMPAIGN_ID": CAMPAIGN_ID,
            "DUAL_LIVE_CAMPAIGN_FINGERPRINT": CAMPAIGN_FINGERPRINT,
        },
        empty_path=True,
    )

    assert completed.returncode == 2
    assert completed.stdout == _compact(
        {
            "action": "run-dual-live-proof",
            "code": "tracked_s3_clearance_and_privileged_runner_required",
            "fresh_live": False,
            "schema_id": "project6.dual_live_run_refusal.v1",
            "status": "REFUSED",
        }
    )
    assert completed.stderr == b""
    assert list(tmp_path.iterdir()) == []


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
    assert completed.stdout == _compact(EXPECTED_REPORT)
    assert completed.stderr == b""
    assert list(tmp_path.iterdir()) == []


def test_validate_action_contains_mandated_direct_launcher_shape() -> None:
    source = PROJECT6.read_text(encoding="utf-8")
    required = """Push-Location $RepoRoot
        try {
            & py "-$PythonVersion" -B .\\tools\\dual_live_gate.py --campaign-id $env:DUAL_LIVE_CAMPAIGN_ID --campaign-fingerprint $env:DUAL_LIVE_CAMPAIGN_FINGERPRINT
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
