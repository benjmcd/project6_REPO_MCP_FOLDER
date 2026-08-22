from __future__ import annotations

import contextlib
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from typing import Iterator

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.dual_live_windows_boundary import _mutex_name  # noqa: E402


pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires Win32 mutexes")

GUARD = ROOT / "scripts" / "invoke-dual-live-family-guard.ps1"
WINDOWS_POWERSHELL = Path(
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)
CAMPAIGN_ID = "sciencebase-live-v2"
ROOTS = (
    r"C:\owner-controlled\project6\sciencebase-campaign",
    r"C:\owner-controlled\project6-attempt-4\sciencebase-campaign",
    r"C:\owner-controlled\project6-attempt-5\sciencebase-campaign",
)
ERROR_FILE_NOT_FOUND = 2
SYNCHRONIZE = 0x00100000


def _ps_quote(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _ps_array(values: tuple[str, ...] | list[str]) -> str:
    return "@(" + ",".join(_ps_quote(value) for value in values) + ")"


def _guard_command(
    mode: str,
    *,
    action: str | None = None,
    current_root: str | None = None,
    py: str | Path | None = None,
    py_arguments: tuple[str, ...] = (),
) -> str:
    pieces = [f"& {_ps_quote(GUARD)}", f"-Mode {_ps_quote(mode)}"]
    if action is not None:
        pieces.append(f"-Action {{ {action} }}")
    if current_root is not None:
        pieces.append(f"-CurrentRoot {_ps_quote(current_root)}")
    if py is not None:
        pieces.append(f"-Py {_ps_quote(py)}")
    if py_arguments:
        pieces.append(f"-PyArgumentList {_ps_array(list(py_arguments))}")
    return " ".join(pieces)


def _run_powershell(
    command: str,
    *,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(WINDOWS_POWERSHELL),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _run_caught(command: str) -> subprocess.CompletedProcess[str]:
    return _run_powershell(
        "\n".join(
            (
                "try {",
                f"  {command}",
                "  [Console]::Out.Write('unexpected_success')",
                "  exit 99",
                "} catch {",
                "  [Console]::Out.Write($_.Exception.Message)",
                "  exit 17",
                "}",
            )
        )
    )


def _names() -> tuple[str, str, str]:
    return tuple(_mutex_name(root, CAMPAIGN_ID) for root in ROOTS)  # type: ignore[return-value]


@pytest.fixture
def kernel32() -> ctypes.WinDLL:
    library = ctypes.WinDLL("kernel32", use_last_error=True)
    library.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    library.CreateMutexW.restype = wintypes.HANDLE
    library.CreateEventW.argtypes = [
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    ]
    library.CreateEventW.restype = wintypes.HANDLE
    library.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    library.OpenMutexW.restype = wintypes.HANDLE
    library.CloseHandle.argtypes = [wintypes.HANDLE]
    library.CloseHandle.restype = wintypes.BOOL
    return library


def _create_mutex(kernel32: ctypes.WinDLL, name: str) -> tuple[int, int]:
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, False, name)
    return int(handle or 0), ctypes.get_last_error()


def _create_event(kernel32: ctypes.WinDLL, name: str) -> tuple[int, int]:
    ctypes.set_last_error(0)
    handle = kernel32.CreateEventW(None, False, False, name)
    return int(handle or 0), ctypes.get_last_error()


def _mutex_state(kernel32: ctypes.WinDLL, name: str) -> tuple[bool, int]:
    ctypes.set_last_error(0)
    handle = kernel32.OpenMutexW(SYNCHRONIZE, False, name)
    error = ctypes.get_last_error()
    if handle:
        assert kernel32.CloseHandle(handle)
        return True, error
    return False, error


def _assert_absent(kernel32: ctypes.WinDLL, names: tuple[str, ...]) -> None:
    for name in names:
        found, error = _mutex_state(kernel32, name)
        assert not found
        assert error == ERROR_FILE_NOT_FOUND


def _readline_with_timeout(
    process: subprocess.Popen[str],
    timeout: int = 30,
) -> str:
    assert process.stdout is not None
    result: queue.Queue[str] = queue.Queue(maxsize=1)
    reader = threading.Thread(target=lambda: result.put(process.stdout.readline()), daemon=True)
    reader.start()
    try:
        return result.get(timeout=timeout)
    except queue.Empty:
        process.kill()
        raise AssertionError("family guard did not enter its callback") from None


@contextlib.contextmanager
def _held_nonruntime(*, force_gc: bool = False) -> Iterator[subprocess.Popen[str]]:
    gc_action = (
        "[GC]::Collect(); [GC]::WaitForPendingFinalizers(); [GC]::Collect();"
        if force_gc
        else ""
    )
    action = (
        f"{gc_action} [Console]::Out.WriteLine('READY'); "
        "[Console]::Out.Flush(); [Console]::In.ReadLine() | Out-Null"
    )
    process = subprocess.Popen(
        [
            str(WINDOWS_POWERSHELL),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            _guard_command("NonRuntime", action=action),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    line = _readline_with_timeout(process)
    if line.rstrip("\r\n") != "READY":
        assert process.stderr is not None
        error = process.stderr.read()
        process.wait(timeout=10)
        raise AssertionError(f"guard failed before callback: {line!r} {error!r}")
    try:
        yield process
    finally:
        if process.poll() is None:
            assert process.stdin is not None
            process.stdin.write("\n")
            process.stdin.flush()
            process.stdin.close()
            process.wait(timeout=20)
        assert process.stderr is not None
        assert process.stderr.read() == ""
        assert process.returncode == 0


def test_guard_has_a_closed_fixed_ps51_contract() -> None:
    source = GUARD.read_text(encoding="utf-8")

    for root in ROOTS:
        assert source.count(root) == 1
    assert [source.index(root) for root in ROOTS] == sorted(
        source.index(root) for root in ROOTS
    )
    assert source.count(CAMPAIGN_ID) == 1
    for parameter in ("Mode", "Action", "CurrentRoot", "Py", "PyArgumentList"):
        assert f"${parameter}" in source
    for primitive in (
        "CreateMutexW",
        "OpenMutexW",
        "CloseHandle",
        "SetLastError(0)",
        "SetLastError = true",
        "GC]::KeepAlive",
        "TakeReverse",
        "SYNCHRONIZE",
    ):
        assert primitive in source
    assert "IntPtr.Zero, false, name" in source
    assert "PSBoundParameters" in source
    for forbidden in (
        "WaitOne",
        "ReleaseMutex",
        '"Global\\',
        "New-Item",
        "Set-Content",
        "Remove-Item",
    ):
        assert forbidden not in source


def test_guard_parses_on_windows_powershell_51() -> None:
    command = (
        "$tokens=$null;$errors=$null;"
        f"[Management.Automation.Language.Parser]::ParseFile({_ps_quote(GUARD)},"
        "[ref]$tokens,[ref]$errors)|Out-Null;"
        "if($errors.Count){$errors|ForEach-Object{$_.Message};exit 1}"
    )
    result = _run_powershell(command)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""


def test_nonruntime_holds_all_real_python_names_and_survives_forced_gc(
    kernel32: ctypes.WinDLL,
) -> None:
    names = _names()
    _assert_absent(kernel32, names)

    with _held_nonruntime(force_gc=True):
        for name in names:
            assert _mutex_state(kernel32, name)[0]

    _assert_absent(kernel32, names)


def test_nonruntime_collision_never_enters_callback_and_releases_partial_lease(
    kernel32: ctypes.WinDLL,
) -> None:
    names = _names()
    collision, error = _create_mutex(kernel32, names[1])
    assert collision and error == 0
    try:
        result = _run_caught(
            _guard_command(
                "NonRuntime",
                action="[Console]::Out.Write('callback_entered')",
            )
        )
        assert result.returncode == 17
        assert result.stdout == "sciencebase_attempt_family_active"
        assert result.stderr == ""
        assert not _mutex_state(kernel32, names[0])[0]
        assert not _mutex_state(kernel32, names[2])[0]
    finally:
        assert kernel32.CloseHandle(collision)
    _assert_absent(kernel32, names)


def test_wrong_named_object_type_is_indeterminate_and_releases_partial_lease(
    kernel32: ctypes.WinDLL,
) -> None:
    names = _names()
    event, error = _create_event(kernel32, names[1])
    assert event and error == 0
    try:
        result = _run_caught(_guard_command("NonRuntime", action="exit 91"))
        assert result.returncode == 17
        assert result.stdout == "sciencebase_attempt_family_guard_indeterminate"
        assert result.stderr == ""
        assert not _mutex_state(kernel32, names[0])[0]
        assert not _mutex_state(kernel32, names[2])[0]
    finally:
        assert kernel32.CloseHandle(event)
    _assert_absent(kernel32, names)


def test_callback_failure_survives_and_still_releases_the_complete_lease(
    kernel32: ctypes.WinDLL,
) -> None:
    names = _names()
    result = _run_caught(
        _guard_command(
            "NonRuntime",
            action="throw [InvalidOperationException]::new('callback_failed')",
        )
    )
    assert result.returncode == 17
    assert result.stdout == "callback_failed"
    assert result.stderr == ""
    _assert_absent(kernel32, names)


@pytest.mark.parametrize(
    "command",
    (
        f"& {_ps_quote(GUARD)} -Action {{ exit 91 }}",
        _guard_command(
            "NonRuntime",
            action="exit 91",
            current_root=ROOTS[1],
        ),
        _guard_command("LiveRuntime", action="exit 91", current_root=ROOTS[1]),
        _guard_command("LiveRuntime", current_root=ROOTS[0], py=sys.executable),
        _guard_command("LiveRuntime", current_root=ROOTS[1]),
    ),
)
def test_cross_mode_or_invalid_root_parameters_fail_closed(command: str) -> None:
    result = _run_caught(command)
    assert result.returncode == 17
    assert result.stdout == "sciencebase_attempt_family_guard_indeterminate"
    assert result.stderr == ""


def test_live_runtime_holds_only_other_names_while_python_creates_current(
    kernel32: ctypes.WinDLL,
) -> None:
    names = _names()
    python_body = "\n".join(
        (
            "import ctypes, sys",
            "from ctypes import wintypes",
            "k = ctypes.WinDLL('kernel32', use_last_error=True)",
            "k.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]",
            "k.CreateMutexW.restype = wintypes.HANDLE",
            "k.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]",
            "k.OpenMutexW.restype = wintypes.HANDLE",
            "k.CloseHandle.argtypes = [wintypes.HANDLE]",
            "k.CloseHandle.restype = wintypes.BOOL",
            "ctypes.set_last_error(0)",
            f"current = k.CreateMutexW(None, False, {names[1]!r})",
            "current_error = ctypes.get_last_error()",
            "others = []",
            f"others.append(k.OpenMutexW({SYNCHRONIZE}, False, {names[0]!r}))",
            f"others.append(k.OpenMutexW({SYNCHRONIZE}, False, {names[2]!r}))",
            "ok = bool(current) and current_error == 0 and all(others)",
            "[k.CloseHandle(handle) for handle in others if handle]",
            "k.CloseHandle(current) if current else None",
            "print('LIVE_OK' if ok else 'LIVE_BAD')",
            "raise SystemExit(0 if ok else 41)",
        )
    )
    result = _run_powershell(
        _guard_command(
            "LiveRuntime",
            current_root=ROOTS[1],
            py=sys.executable,
            py_arguments=("-I", "-S", "-c", python_body),
        )
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "LIVE_OK"
    assert result.stderr == ""
    _assert_absent(kernel32, names)


def test_live_runtime_preserves_python_exit_code_and_releases_other_names(
    kernel32: ctypes.WinDLL,
) -> None:
    names = _names()
    command = _guard_command(
        "LiveRuntime",
        current_root=ROOTS[2],
        py=sys.executable,
        py_arguments=("-I", "-S", "-c", "raise SystemExit(23)"),
    )
    result = _run_powershell(command + "\nexit $LASTEXITCODE")
    assert result.returncode == 23
    assert result.stdout == ""
    assert result.stderr == ""
    _assert_absent(kernel32, names)


def test_live_runtime_probe_reports_current_collision_without_running_python(
    kernel32: ctypes.WinDLL,
) -> None:
    names = _names()
    collision, error = _create_mutex(kernel32, names[1])
    assert collision and error == 0
    try:
        result = _run_caught(
            _guard_command(
                "LiveRuntime",
                current_root=ROOTS[1],
                py=sys.executable,
                py_arguments=("-c", "print('python_entered')"),
            )
        )
        assert result.returncode == 17
        assert result.stdout == "sciencebase_attempt_family_active"
        assert result.stderr == ""
        assert not _mutex_state(kernel32, names[0])[0]
        assert not _mutex_state(kernel32, names[2])[0]
    finally:
        assert kernel32.CloseHandle(collision)
    _assert_absent(kernel32, names)


def test_native_create_clears_stale_already_exists_before_new_acquisition() -> None:
    name = f"Local\\Project6DualLive-Stale-{os.getpid()}"
    command = "\n".join(
        (
            f". {_ps_quote(GUARD)} -Mode NonRuntime -Action {{ }}",
            "[Project6DualLiveFamilyGuard.FamilyGuardNative]::SetThreadLastError(183)",
            f"$result = [Project6DualLiveFamilyGuard.FamilyGuardNative]::CreateMutex({_ps_quote(name)})",
            "if($result.Handle -eq [IntPtr]::Zero -or $result.Error -ne 0){exit 41}",
            "$closed = [Project6DualLiveFamilyGuard.FamilyGuardNative]::Close($result.Handle)",
            "if(-not $closed.Success){exit 42}",
            "[Console]::Out.Write('STALE_OK')",
        )
    )
    result = _run_powershell(command)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "STALE_OK"
    assert result.stderr == ""


def test_release_failure_is_stable_and_cleanup_continues_in_reverse_order() -> None:
    first = f"Local\\Project6DualLive-Close-{os.getpid()}-A"
    second = f"Local\\Project6DualLive-Close-{os.getpid()}-B"
    command = "\n".join(
        (
            f". {_ps_quote(GUARD)} -Mode NonRuntime -Action {{ }}",
            "$lease = [Project6DualLiveFamilyGuard.FamilyGuardLease]::new()",
            f"$first = [Project6DualLiveFamilyGuard.FamilyGuardNative]::CreateMutex({_ps_quote(first)})",
            f"$second = [Project6DualLiveFamilyGuard.FamilyGuardNative]::CreateMutex({_ps_quote(second)})",
            "$lease.Add($first.Handle)",
            "$lease.Add($second.Handle)",
            "$null = [Project6DualLiveFamilyGuard.FamilyGuardNative]::Close($second.Handle)",
            "try {",
            "  Close-FamilyGuardLease -Lease $lease",
            "  exit 99",
            "} catch {",
            f"  $probe = [Project6DualLiveFamilyGuard.FamilyGuardNative]::OpenMutex({_ps_quote(first)})",
            "  if($probe.Handle -ne [IntPtr]::Zero -or $probe.Error -ne 2){exit 43}",
            "  [Console]::Out.Write($_.Exception.Message)",
            "  exit 17",
            "}",
        )
    )
    result = _run_powershell(command)
    assert result.returncode == 17
    assert result.stdout == "sciencebase_attempt_family_guard_release_failed"
    assert result.stderr == ""


def test_guard_handles_are_not_kept_alive_by_a_spawned_child(
    kernel32: ctypes.WinDLL,
) -> None:
    child_code = "import time; time.sleep(20)"
    action = (
        f"$child = Start-Process -FilePath {_ps_quote(sys.executable)} "
        f"-ArgumentList {_ps_array(['-I', '-S', '-c', child_code])} -PassThru; "
        "[Console]::Out.Write($child.Id)"
    )
    result = _run_powershell(_guard_command("NonRuntime", action=action))
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    child_pid = int(result.stdout)
    try:
        _assert_absent(kernel32, _names())
    finally:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(child_pid, 15)


def test_process_crash_releases_all_kernel_mutexes(kernel32: ctypes.WinDLL) -> None:
    names = _names()
    process: subprocess.Popen[str]
    with pytest.raises(AssertionError, match="returncode"):
        with _held_nonruntime() as process:
            for name in names:
                assert _mutex_state(kernel32, name)[0]
            process.kill()
    process.wait(timeout=20)
    _assert_absent(kernel32, names)
