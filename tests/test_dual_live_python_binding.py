import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "validate-dual-live-python-binding.ps1"
FROZEN_AMBIENT_BYTES = 104_952
FROZEN_AMBIENT_SHA256 = "4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a"
RETAINED_MEMBER_BYTES = 103_704
RETAINED_MEMBER_SHA256 = "737a7e3b71e3578f8432acc7dd88c452e593622c544bc13da4789d69c63da5ae"

pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell")


def _ps_quote(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _ambient_identity() -> tuple[Path, int, str]:
    result = subprocess.run(
        [
            "py.exe",
            "-V:PythonCore/3.12",
            "-I",
            "-S",
            "-c",
            "import sys; print(sys.executable)",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert len(result.stdout.splitlines()) == 1
    path = Path(result.stdout.strip())
    payload = path.read_bytes()
    return path, len(payload), hashlib.sha256(payload).hexdigest()


def _invoke_observation(
    archive: Path,
    ambient_bytes: int,
    ambient_sha256: str,
    *,
    archive_argument: str | None = None,
    ambient_held_probe: str = "$null",
    archive_held_probe: str = "$null",
    launcher_executable: str = "py.exe",
    launcher_tag: str = "-V:PythonCore/3.12",
) -> subprocess.CompletedProcess[str]:
    archive_payload = archive.read_bytes()
    observed_archive = archive_argument or str(archive)
    command = "\n".join(
        (
            f". {_ps_quote(GATE)} -PythonArchive {_ps_quote(archive)}",
            f"$ambientProbe = {ambient_held_probe}",
            f"$archiveProbe = {archive_held_probe}",
            "$observation = Get-PythonBindingObservation "
            f"-LauncherExecutable {_ps_quote(launcher_executable)} "
            f"-LauncherTag {_ps_quote(launcher_tag)} "
            f"-ArchivePath {_ps_quote(observed_archive)} "
            f"-ExpectedAmbientBytes {ambient_bytes} "
            f"-ExpectedAmbientSha256 '{ambient_sha256}' "
            f"-ExpectedArchiveName {_ps_quote(archive.name)} "
            f"-ExpectedArchiveBytes {len(archive_payload)} "
            f"-ExpectedArchiveSha256 '{hashlib.sha256(archive_payload).hexdigest()}' "
            "-ExpectedArchiveMember 'python.exe' "
            "-AmbientHeldProbe $ambientProbe "
            "-ArchiveHeldProbe $archiveProbe",
            "$observation | ConvertTo-Json -Compress",
        )
    )
    return _run_powershell(command)


def _invoke_failure(body: str) -> subprocess.CompletedProcess[str]:
    command = "\n".join(
        (
            "try {",
            body,
            "  exit 99",
            "} catch {",
            "  [Console]::Out.Write($_.Exception.Message)",
            "  exit 17",
            "}",
        )
    )
    return _run_powershell(command)


def _run_powershell(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell.exe",
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
    )


def _filesystem_manifest(root: Path) -> dict[str, tuple[object, ...]]:
    manifest: dict[str, tuple[object, ...]] = {}
    for path in sorted((root, *root.rglob("*")), key=lambda item: str(item).casefold()):
        relative = "." if path == root else path.relative_to(root).as_posix()
        stat_result = path.stat()
        if path.is_file():
            payload = path.read_bytes()
            manifest[relative] = (
                "file",
                len(payload),
                hashlib.sha256(payload).hexdigest(),
                stat_result.st_ctime_ns,
                stat_result.st_mtime_ns,
            )
        else:
            manifest[relative] = (
                "directory",
                stat_result.st_ctime_ns,
                stat_result.st_mtime_ns,
            )
    return manifest


def test_python_binding_gate_has_closed_validate_only_production_contract() -> None:
    source = GATE.read_text(encoding="utf-8")

    assert "[Parameter(Mandatory = $true)][string]$PythonArchive" in source
    assert "-V:PythonCore/3.12" in source
    assert "PYTHON_BINDING_OK" in source
    assert "4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a" in source
    assert "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3" in source
    assert "104952" in source
    assert "11133606" in source
    assert "System.Diagnostics.ProcessStartInfo" in source
    assert "UseShellExecute = $false" in source
    assert "RedirectStandardOutput = $true" in source
    assert "RedirectStandardError = $true" in source
    assert "System.IO.Compression.ZipArchive" in source
    assert "FileShare]::Read" in source
    parsed = _run_powershell(
        "$tokens=$null;$errors=$null;"
        f"$ast=[Management.Automation.Language.Parser]::ParseFile({_ps_quote(GATE)},"
        "[ref]$tokens,[ref]$errors);"
        "if($errors.Count -ne 0){throw 'parse_failed'};"
        "$names=@($ast.ParamBlock.Parameters | ForEach-Object "
        "{$_.Name.VariablePath.UserPath});"
        "ConvertTo-Json -Compress -InputObject $names"
    )
    assert parsed.returncode == 0, parsed.stderr
    assert json.loads(parsed.stdout) == ["PythonArchive"]
    for forbidden in (
        "Invoke-WebRequest",
        "Expand-Archive",
        "Set-Content",
        "New-Item",
        "Remove-Item",
        "Move-Item",
        "-V:PythonCore/3.12.10",
        "-V:3.12.10",
        "2>&1",
        "2>$null",
    ):
        assert forbidden not in source


def test_python_binding_gate_returns_the_exact_ordered_success_observation(
    tmp_path: Path,
) -> None:
    ambient_path, ambient_bytes, ambient_sha256 = _ambient_identity()
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        bundle.write(ambient_path, arcname="python.exe")
    before = _filesystem_manifest(tmp_path)

    result = _invoke_observation(archive, ambient_bytes, ambient_sha256)

    after = _filesystem_manifest(tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert after == before
    observation = json.loads(result.stdout)
    assert list(observation) == [
        "status",
        "launcher_tag",
        "ambient_interpreter",
        "ambient_interpreter_root",
        "ambient_bytes",
        "ambient_sha256",
        "archive_path",
        "archive_bytes",
        "archive_sha256",
        "archive_member",
        "archive_member_bytes",
        "archive_member_sha256",
        "expected_worker_sha256",
    ]
    assert observation["status"] == "PYTHON_BINDING_OK"
    assert observation["launcher_tag"] == "-V:PythonCore/3.12"
    assert Path(observation["ambient_interpreter"]) == ambient_path
    assert observation["ambient_bytes"] == ambient_bytes
    assert observation["ambient_sha256"] == ambient_sha256
    assert observation["archive_member"] == "python.exe"
    assert observation["archive_member_bytes"] == ambient_bytes
    assert observation["archive_member_sha256"] == ambient_sha256
    assert observation["expected_worker_sha256"] == ambient_sha256


def test_python_binding_gate_resolves_the_exact_frozen_ambient_identity() -> None:
    ambient_path, ambient_bytes, ambient_sha256 = _ambient_identity()

    assert ambient_path.is_absolute()
    assert ambient_path.name == "python.exe"
    assert ambient_bytes == FROZEN_AMBIENT_BYTES
    assert ambient_sha256 == FROZEN_AMBIENT_SHA256


def test_python_binding_gate_comparison_seam_rejects_retained_attempt3_identity() -> None:
    result = _invoke_failure(
        f". {_ps_quote(GATE)} -PythonArchive 'C:\\unused.zip'\n"
        "  Assert-PythonBindingMatch "
        f"-AmbientBytes {FROZEN_AMBIENT_BYTES} "
        f"-AmbientSha256 '{FROZEN_AMBIENT_SHA256}' "
        f"-MemberBytes {RETAINED_MEMBER_BYTES} "
        f"-MemberSha256 '{RETAINED_MEMBER_SHA256}'"
    )

    assert result.returncode == 17
    assert result.stdout == "python_binding_mismatch"
    assert result.stderr == ""


def test_python_binding_gate_reports_only_mismatch_for_a_valid_different_member(
    tmp_path: Path,
) -> None:
    _, ambient_bytes, ambient_sha256 = _ambient_identity()
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        bundle.writestr("python.exe", b"different-runtime-bytes")

    archive_payload = archive.read_bytes()
    result = _invoke_failure(
        f". {_ps_quote(GATE)} -PythonArchive {_ps_quote(archive)}\n"
        "  Get-PythonBindingObservation "
        "-LauncherExecutable 'py.exe' "
        "-LauncherTag '-V:PythonCore/3.12' "
        f"-ArchivePath {_ps_quote(archive)} "
        f"-ExpectedAmbientBytes {ambient_bytes} "
        f"-ExpectedAmbientSha256 '{ambient_sha256}' "
        f"-ExpectedArchiveName {_ps_quote(archive.name)} "
        f"-ExpectedArchiveBytes {len(archive_payload)} "
        f"-ExpectedArchiveSha256 '{hashlib.sha256(archive_payload).hexdigest()}' "
        "-ExpectedArchiveMember 'python.exe' | Out-Null"
    )

    assert result.returncode == 17
    assert result.stdout == "python_binding_mismatch"
    assert result.stderr == ""


def test_python_binding_gate_maps_launcher_failures_to_the_stable_code() -> None:
    result = _invoke_failure(
        f". {_ps_quote(GATE)} -PythonArchive 'C:\\unused.zip'\n"
        "  Invoke-PythonBindingLauncher "
        "-LauncherExecutable 'C:\\definitely-missing\\launcher.exe' "
        "-LauncherTag '-V:PythonCore/3.12' | Out-Null"
    )

    assert result.returncode == 17
    assert result.stdout == "python_binding_launcher_invalid"
    assert result.stderr == ""


def test_python_binding_gate_maps_one_line_relative_launcher_output_to_launcher_invalid() -> None:
    result = _invoke_failure(
        f". {_ps_quote(GATE)} -PythonArchive 'C:\\unused.zip'\n"
        "  $observed = Invoke-PythonBindingLauncher "
        "-LauncherExecutable 'cmd.exe' "
        "-LauncherTag '/d /s /c echo relative.exe'\n"
        "  throw ('unexpected_launcher_output:' + $observed)"
    )

    assert result.returncode == 17
    assert result.stdout == "python_binding_launcher_invalid"
    assert result.stderr == ""


def test_python_binding_gate_rejects_every_malformed_launcher_result() -> None:
    cases = (
        '/d /s /c "echo diagnostic 1>&2&exit /b 0"',
        '/d /s /c "exit /b 7"',
        '/d /s /c "exit /b 0"',
        '/d /s /c "echo C:\\one.exe&echo C:\\two.exe&exit /b 0"',
    )
    for launcher_tag in cases:
        result = _invoke_failure(
            f". {_ps_quote(GATE)} -PythonArchive 'C:\\unused.zip'\n"
            "  Invoke-PythonBindingLauncher "
            "-LauncherExecutable 'cmd.exe' "
            f"-LauncherTag {_ps_quote(launcher_tag)} | Out-Null"
        )

        assert result.returncode == 17
        assert result.stdout == "python_binding_launcher_invalid"
        assert result.stderr == ""


def test_python_binding_gate_distinguishes_ambient_and_archive_identity_failures(
    tmp_path: Path,
) -> None:
    ambient_path, ambient_bytes, ambient_sha256 = _ambient_identity()
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        bundle.write(ambient_path, arcname="python.exe")
    archive_payload = archive.read_bytes()
    common = (
        f". {_ps_quote(GATE)} -PythonArchive {_ps_quote(archive)}\n"
        "  Get-PythonBindingObservation "
        "-LauncherExecutable 'py.exe' "
        "-LauncherTag '-V:PythonCore/3.12' "
        f"-ArchivePath {_ps_quote(archive)} "
        f"-ExpectedAmbientSha256 '{ambient_sha256}' "
        f"-ExpectedArchiveName {_ps_quote(archive.name)} "
        f"-ExpectedArchiveSha256 '{hashlib.sha256(archive_payload).hexdigest()}' "
        "-ExpectedArchiveMember 'python.exe' "
    )

    ambient_result = _invoke_failure(
        common
        + f"-ExpectedAmbientBytes {ambient_bytes + 1} "
        + f"-ExpectedArchiveBytes {len(archive_payload)} | Out-Null"
    )
    archive_result = _invoke_failure(
        common
        + f"-ExpectedAmbientBytes {ambient_bytes} "
        + f"-ExpectedArchiveBytes {len(archive_payload) + 1} | Out-Null"
    )

    assert ambient_result.returncode == 17
    assert ambient_result.stdout == "python_binding_ambient_invalid"
    assert ambient_result.stderr == ""
    assert archive_result.returncode == 17
    assert archive_result.stdout == "python_binding_archive_invalid"
    assert archive_result.stderr == ""


def test_python_binding_gate_rejects_wrong_case_and_duplicate_member_names(
    tmp_path: Path,
) -> None:
    _, ambient_bytes, ambient_sha256 = _ambient_identity()
    for archive_name, member_names in (
        ("wrong-case.zip", ("PYTHON.EXE",)),
        ("duplicate.zip", ("python.exe", "PYTHON.EXE")),
    ):
        archive = tmp_path / archive_name
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
            for index, member_name in enumerate(member_names):
                bundle.writestr(member_name, f"payload-{index}".encode())
        archive_payload = archive.read_bytes()
        result = _invoke_failure(
            f". {_ps_quote(GATE)} -PythonArchive {_ps_quote(archive)}\n"
            "  Get-PythonBindingObservation "
            "-LauncherExecutable 'py.exe' "
            "-LauncherTag '-V:PythonCore/3.12' "
            f"-ArchivePath {_ps_quote(archive)} "
            f"-ExpectedAmbientBytes {ambient_bytes} "
            f"-ExpectedAmbientSha256 '{ambient_sha256}' "
            f"-ExpectedArchiveName {_ps_quote(archive.name)} "
            f"-ExpectedArchiveBytes {len(archive_payload)} "
            f"-ExpectedArchiveSha256 '{hashlib.sha256(archive_payload).hexdigest()}' "
            "-ExpectedArchiveMember 'python.exe' | Out-Null"
        )

        assert result.returncode == 17
        assert result.stdout == "python_binding_archive_member_invalid"
        assert result.stderr == ""


def test_python_binding_gate_maps_archive_open_failure_to_archive_invalid(
    tmp_path: Path,
) -> None:
    ambient_path, ambient_bytes, ambient_sha256 = _ambient_identity()
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        bundle.write(ambient_path, arcname="python.exe")
    archive_payload = archive.read_bytes()
    result = _invoke_failure(
        f". {_ps_quote(GATE)} -PythonArchive {_ps_quote(archive)}\n"
        f"  $held = [IO.File]::Open({_ps_quote(archive)}, "
        "[IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::None)\n"
        "  try {\n"
        "    Get-PythonBindingObservation "
        "-LauncherExecutable 'py.exe' "
        "-LauncherTag '-V:PythonCore/3.12' "
        f"-ArchivePath {_ps_quote(archive)} "
        f"-ExpectedAmbientBytes {ambient_bytes} "
        f"-ExpectedAmbientSha256 '{ambient_sha256}' "
        f"-ExpectedArchiveName {_ps_quote(archive.name)} "
        f"-ExpectedArchiveBytes {len(archive_payload)} "
        f"-ExpectedArchiveSha256 '{hashlib.sha256(archive_payload).hexdigest()}' "
        "-ExpectedArchiveMember 'python.exe' | Out-Null\n"
        "  } finally { $held.Dispose() }"
    )

    assert result.returncode == 17
    assert result.stdout == "python_binding_archive_invalid"
    assert result.stderr == ""


def test_python_binding_gate_rejects_noncanonical_and_reparse_archive_paths(
    tmp_path: Path,
) -> None:
    ambient_path, ambient_bytes, ambient_sha256 = _ambient_identity()
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    archive = real_parent / "fixture.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        bundle.write(ambient_path, arcname="python.exe")

    noncanonical = str(real_parent) + r"\.\fixture.zip"
    noncanonical_result = _invoke_observation(
        archive,
        ambient_bytes,
        ambient_sha256,
        archive_argument=noncanonical,
    )
    assert noncanonical_result.returncode != 0
    assert "python_binding_archive_invalid" in noncanonical_result.stderr

    junction = tmp_path / "junction"
    create_junction = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "New-Item -ItemType Junction "
            f"-Path {_ps_quote(junction)} -Target {_ps_quote(real_parent)} | Out-Null",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert create_junction.returncode == 0, create_junction.stderr
    reparse_result = _invoke_observation(
        archive,
        ambient_bytes,
        ambient_sha256,
        archive_argument=str(junction / archive.name),
    )
    assert reparse_result.returncode != 0
    assert "python_binding_archive_invalid" in reparse_result.stderr


def test_python_binding_gate_rejects_nonfixed_drive_from_the_internal_path_seam() -> None:
    ambient_path, _, _ = _ambient_identity()
    result = _invoke_failure(
        f". {_ps_quote(GATE)} -PythonArchive 'C:\\unused.zip'\n"
        "  Resolve-OrdinaryFixedFile "
        f"-Path {_ps_quote(ambient_path)} "
        "-Code 'python_binding_ambient_invalid' "
        "-DriveTypeResolver { param($root) [IO.DriveType]::Removable } | Out-Null"
    )

    assert result.returncode == 17
    assert result.stdout == "python_binding_ambient_invalid"
    assert result.stderr == ""


def test_python_binding_gate_holds_both_identity_files_without_write_delete_sharing(
    tmp_path: Path,
) -> None:
    installed_ambient, _, _ = _ambient_identity()
    disposable_root = tmp_path / "runtime"
    disposable_root.mkdir()
    ambient_path = disposable_root / "python.exe"
    shutil.copy2(installed_ambient, ambient_path)
    ambient_payload = ambient_path.read_bytes()
    ambient_bytes = len(ambient_payload)
    ambient_sha256 = hashlib.sha256(ambient_payload).hexdigest()
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        bundle.write(ambient_path, arcname="python.exe")
    probe = (
        "{ param($path,$stream,$extra) "
        "if(-not $stream.CanRead){throw 'held_stream_unreadable'};"
        "if($null -ne $extra){"
        "$field=$extra.GetType().GetField('_archiveStream',"
        "[Reflection.BindingFlags]'Instance,NonPublic');"
        "if($null -eq $field -or -not [object]::ReferenceEquals("
        "$field.GetValue($extra),$stream)){throw 'zip_not_backed_by_held_stream'}};"
        "$writer=$null;try{$writer=[IO.File]::Open($path,[IO.FileMode]::Open,"
        "[IO.FileAccess]::Write,[IO.FileShare]::ReadWrite)}catch{};"
        "if($null -ne $writer){$writer.Dispose();throw 'held_stream_write_allowed'};"
        "$renamed=$true;try{[IO.File]::Move($path,($path + '.moved'))}catch{$renamed=$false};"
        "if($renamed){throw 'held_stream_rename_allowed'};"
        "$deleted=$true;try{[IO.File]::Delete($path)}catch{$deleted=$false};"
        "if($deleted){throw 'held_stream_delete_allowed'} }"
    )

    result = _invoke_observation(
        archive,
        ambient_bytes,
        ambient_sha256,
        ambient_held_probe=probe,
        archive_held_probe=probe,
        launcher_executable="cmd.exe",
        launcher_tag=f'/d /s /c "echo {ambient_path}&exit /b 0"',
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert archive.is_file()
    assert ambient_path.is_file()
