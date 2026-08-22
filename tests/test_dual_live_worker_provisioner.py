import hashlib
import os
from pathlib import Path
import stat
import subprocess
import struct
import zipfile
import zlib

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROVISIONER = ROOT / "scripts" / "provision-dual-live-worker.ps1"
WINDOWS_POWERSHELL = Path(
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)


def _ps_quote(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _write_empty_name_zip(path: Path, payload: bytes) -> None:
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    local = struct.pack(
        "<I5H3I2H",
        0x04034B50,
        20,
        0,
        0,
        0,
        0,
        crc,
        len(payload),
        len(payload),
        0,
        0,
    )
    central = struct.pack(
        "<I6H3I5H2I",
        0x02014B50,
        20,
        20,
        0,
        0,
        0,
        0,
        crc,
        len(payload),
        len(payload),
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    end = struct.pack(
        "<I4H2IH",
        0x06054B50,
        0,
        0,
        1,
        1,
        len(central),
        len(local) + len(payload),
        0,
    )
    path.write_bytes(local + payload + central + end)


def _invoke_archive_expander(
    archive: Path,
    destination: Path,
    *,
    held_probe: str = "$null",
) -> subprocess.CompletedProcess[str]:
    payload = archive.read_bytes()
    command = "\n".join(
        (
            "$ErrorActionPreference='Stop'",
            "Add-Type -AssemblyName System.IO.Compression",
            "Add-Type -AssemblyName System.IO.Compression.FileSystem",
            f"$source=Get-Content -Raw -LiteralPath {_ps_quote(PROVISIONER)}",
            "$tokens=$null;$errors=$null",
            "$ast=[Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors)",
            "$names=@('Test-FullyQualifiedLocalPath','Assert-StableDirectoryAncestors','Get-Sha256Hex','Expand-ValidatedPythonArchive')",
            "$definitions=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $names -contains $node.Name},$true))",
            "if($errors.Count -or $definitions.Count -ne $names.Count){exit 91}",
            "foreach($definition in $definitions){Invoke-Expression $definition.Extent.Text}",
            "try {",
            f"  $probe={held_probe}",
            "  Expand-ValidatedPythonArchive "
            f"-ArchivePath {_ps_quote(archive)} "
            f"-DestinationPath {_ps_quote(destination)} "
            f"-ExpectedArchiveName {_ps_quote(archive.name)} "
            f"-ExpectedArchiveBytes {len(payload)} "
            f"-ExpectedArchiveSha256 '{hashlib.sha256(payload).hexdigest()}' "
            "-ArchiveHeldProbe $probe",
            "  [Console]::Out.Write('OK')",
            "} catch {",
            "  [Console]::Out.Write($_.Exception.Message)",
            "  exit 17",
            "}",
        )
    )
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
        timeout=30,
    )


def test_local_worker_provisioner_is_one_source_grounded_external_closure_builder() -> None:
    source = PROVISIONER.read_text(encoding="utf-8")

    assert "$PythonVersion = '3.12.10'" in source
    assert "$PythonArchiveName = 'python-3.12.10-embed-amd64.zip'" in source
    assert "$PythonArchiveBytes = 11133606" in source
    assert (
        "$PythonArchiveUrl = "
        "'https://www.python.org/ftp/python/3.12.10/"
        "python-3.12.10-embed-amd64.zip'"
    ) in source
    assert "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3" in source
    for relative in (
        "tools/dual_live_run.py",
        "backend/app/__init__.py",
        "backend/app/services/__init__.py",
        "backend/app/services/connector_egress_contract.py",
        "backend/app/services/dual_live_effect_guard.py",
        "backend/app/services/dual_live_sciencebase_producer.py",
        "backend/app/services/dual_live_worker_bundle.py",
        "backend/app/services/dual_live_windows_boundary.py",
    ):
        assert f"'{relative}'" in source
    for forbidden in (
        "Invoke-WebRequest",
        "Start-Process",
        "CreateAppContainerProfile",
        "net.exe user",
        "Remove-Item",
        "PRIVATE KEY",
    ):
        assert forbidden not in source

    assert "ConvertTo-Json -Compress -Depth 8" in source
    assert "sha256-$manifestDigest" in source
    assert "worker-bundle.json" in source
    assert "git rev-parse HEAD" in source
    assert "SetOwner" in source
    assert "/inheritance:r" in source
    assert "*:($" not in source
    assert "Write-CreateOnce ([IO.Path]::GetFullPath($OutputBinding))" in source
    assert "worker_output_binding_parent_invalid" in source
    assert "status --porcelain=v1 --untracked-files=all" in source
    assert "worker_source_not_clean" in source
    assert "cat-file blob" in source
    assert "worker_source_identity_drift" in source
    assert source.count("(& git -C $repo rev-parse HEAD") == 2
    assert source.count("@(& git -C $repo status --porcelain=v1 --untracked-files=all") == 2
    assert "Assert-Outside $outputParent @($repo, $campaign, $appProfile)" in source
    assert "Get-RelativeWorkerPath" in source
    assert "Get-Sha256Hex" in source
    assert "Assert-StableDirectoryAncestors $provisioningParent" in source
    assert "Assert-StableDirectoryAncestors $outputParent" in source
    assert "Add-Type -AssemblyName System.IO.Compression" in source
    assert "Add-Type -AssemblyName System.IO.Compression.FileSystem" in source
    assert "function Expand-ValidatedPythonArchive" in source
    compact_source = " ".join(source.split())
    assert "[IO.FileAccess]::Read, [IO.FileShare]::Read" in compact_source
    assert "ComputeHash($stream)" in source
    assert "[System.IO.Compression.ZipArchiveMode]::Read, $true" in source
    assert (
        "[System.IO.Compression.ZipFileExtensions]::ExtractToFile("
        "$entry, $destination, $false)"
    ) in source
    assert "Expand-Archive" not in source
    assert "ExtractToDirectory" not in source
    assert "[System.IO.Compression.ZipFile]" not in source

    expand_at = source.index("Expand-ValidatedPythonArchive")
    overlay_at = source.index("foreach ($relative in $WorkerFiles)", expand_at)
    manifest_at = source.index("$manifest = [ordered]@{", overlay_at)
    move_at = source.index("Move-Item -LiteralPath $stage", manifest_at)
    assert expand_at < overlay_at < manifest_at < move_at
    assert "New-Item -ItemType Directory -Path $provisioning" not in source
    complete_validation_at = source.index("if ($null -ne $ArchiveHeldProbe)")
    parent_create_at = source.index(
        "[void][IO.Directory]::CreateDirectory($destinationParent)",
        complete_validation_at,
    )
    stage_create_at = source.index(
        "[void][IO.Directory]::CreateDirectory($destinationRoot)",
        parent_create_at,
    )
    assert complete_validation_at < parent_create_at < stage_create_at
    for incompatible in (
        "[IO.Path]::GetRelativePath",
        "SHA256]::HashData",
        "[Convert]::ToHexString",
        "$IsWindows",
    ):
        assert incompatible not in source


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell 5.1")
def test_worker_archive_expander_holds_one_stream_through_extraction(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        bundle.writestr("python.exe", b"held-python")
        bundle.writestr("Lib/module.py", b"VALUE = 1\n")

    replacement = tmp_path / "replacement.zip"
    moved = tmp_path / "moved.zip"
    held_probe = (
        "{ param($archivePath,$stream,$zip) "
        "if(-not $stream.CanRead -or $zip.Mode -ne [IO.Compression.ZipArchiveMode]::Read){throw 'held_stream_probe_failed'};"
        "$writer=$null;try{$writer=[IO.File]::Open($archivePath,[IO.FileMode]::Open,[IO.FileAccess]::Write,[IO.FileShare]::ReadWrite)}catch{};"
        "if($null -ne $writer){$writer.Dispose();throw 'held_stream_write_allowed'};"
        f"[IO.File]::WriteAllBytes({_ps_quote(replacement)},[byte[]](1,2,3));"
        "$replaced=$true;try{[IO.File]::Replace("
        f"{_ps_quote(replacement)},$archivePath,$null)"
        "}catch{$replaced=$false};if($replaced){throw 'held_stream_replace_allowed'};"
        "$renamed=$true;try{[IO.File]::Move($archivePath,"
        f"{_ps_quote(moved)})"
        "}catch{$renamed=$false};if($renamed){throw 'held_stream_rename_allowed'};"
        "$deleted=$true;try{[IO.File]::Delete($archivePath)}catch{$deleted=$false};"
        "if($deleted){throw 'held_stream_delete_allowed'} }"
    )
    provisioning = tmp_path / "provisioning"
    destination = provisioning / "stage"

    result = _invoke_archive_expander(
        archive,
        destination,
        held_probe=held_probe,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "OK"
    assert result.stderr == ""
    assert provisioning.is_dir()
    assert (destination / "python.exe").read_bytes() == b"held-python"
    assert (destination / "Lib" / "module.py").read_bytes() == b"VALUE = 1\n"


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell 5.1")
@pytest.mark.parametrize(
    "entries",
    (
        (("", b"empty"),),
        (("/absolute.txt", b"absolute"),),
        ((r"C:\drive.txt", b"drive"),),
        (("../outside.txt", b"outside"),),
        (("pkg/./file.txt", b"dot"),),
        (("pkg/../file.txt", b"dotdot"),),
        (("pkg/File.txt", b"one"), ("PKG/file.TXT", b"two")),
        (("pkg/file.txt", b"one"), (r"PKG\FILE.TXT", b"two")),
        (("pkg", b"file"), ("pkg/child.txt", b"child")),
        (("pkg/child.txt", b"child"), ("PKG", b"file")),
    ),
)
def test_worker_archive_expander_rejects_ambiguous_entry_sets_before_writing(
    tmp_path: Path,
    entries: tuple[tuple[str, bytes], ...],
) -> None:
    archive = tmp_path / "fixture.zip"
    if entries[0][0] == "":
        _write_empty_name_zip(archive, entries[0][1])
    else:
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
            for name, payload in entries:
                bundle.writestr(name, payload)
    destination = tmp_path / "stage"

    result = _invoke_archive_expander(archive, destination)

    assert result.returncode == 17
    assert result.stdout == "worker_python_archive_entry_invalid"
    assert result.stderr == ""
    assert not destination.exists()


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell 5.1")
def test_worker_archive_expander_validates_before_creating_provisioning_parent(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        bundle.writestr("../outside.txt", b"outside")
    provisioning = tmp_path / "provisioning"
    destination = provisioning / "stage"

    result = _invoke_archive_expander(archive, destination)

    assert result.returncode == 17
    assert result.stdout == "worker_python_archive_entry_invalid"
    assert result.stderr == ""
    assert not provisioning.exists()
    assert not destination.exists()


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell 5.1")
@pytest.mark.parametrize(
    ("create_system", "external_attributes"),
    (
        (3, (stat.S_IFLNK | 0o777) << 16),
        (0, int(0x400)),
    ),
)
def test_worker_archive_expander_rejects_symlink_and_reparse_entries(
    tmp_path: Path,
    create_system: int,
    external_attributes: int,
) -> None:
    archive = tmp_path / "fixture.zip"
    entry = zipfile.ZipInfo("ambiguous-entry")
    entry.create_system = create_system
    entry.external_attr = external_attributes
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        bundle.writestr(entry, b"target")
    destination = tmp_path / "stage"

    result = _invoke_archive_expander(archive, destination)

    assert result.returncode == 17
    assert result.stdout == "worker_python_archive_entry_invalid"
    assert result.stderr == ""
    assert not destination.exists()


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell 5.1")
def test_worker_archive_expander_rejects_reparse_path_ambiguity(
    tmp_path: Path,
) -> None:
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    archive = real_parent / "fixture.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        bundle.writestr("python.exe", b"python")

    junction = tmp_path / "junction"
    create_junction = subprocess.run(
        [
            str(WINDOWS_POWERSHELL),
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
        timeout=15,
    )
    assert create_junction.returncode == 0, create_junction.stdout + create_junction.stderr

    archive_result = _invoke_archive_expander(
        junction / archive.name,
        tmp_path / "archive-stage",
    )
    stage_result = _invoke_archive_expander(
        archive,
        junction / "stage",
    )

    assert archive_result.returncode == 17
    assert archive_result.stdout == "worker_python_archive_invalid"
    assert archive_result.stderr == ""
    assert stage_result.returncode == 17
    assert stage_result.stdout == "worker_stage_invalid"
    assert stage_result.stderr == ""
    assert not (tmp_path / "archive-stage").exists()
    assert not (real_parent / "stage").exists()


def test_local_worker_provisioner_requires_external_profile_and_archive_inputs() -> None:
    source = PROVISIONER.read_text(encoding="utf-8")

    for parameter in (
        "PythonArchive",
        "ProfileBinding",
        "ProvisioningRoot",
        "OutputBinding",
        "CampaignRoot",
        "AmbientInterpreterRoot",
        "RepositoryRoot",
    ):
        assert f"${parameter}" in source
    for field in (
        "profile_moniker",
        "package_sid",
        "broker_sid",
        "appcontainer_profile_root",
        "broker_profile_root",
        "user_data_root",
    ):
        assert f".{field}" in source


def test_local_worker_provisioner_hardens_bundle_acls_before_emitting_a_binding() -> None:
    """Assert ACL *sequencing*, not just that ACL primitives are mentioned.

    The presence-only checks above were satisfied by the parent-first
    implementation that failed W6-PRE attempt 2 at ``worker_bundle_acl_failed``:
    ``SetOwner`` and ``/inheritance:r`` were both present and both in the wrong
    order.  These assertions pin the order instead.
    """

    source = PROVISIONER.read_text(encoding="utf-8")

    # The parent-first target list must never come back.
    assert "$aclTargets = @($provisioning, $bundleRoot)" not in source
    # Nor may it be "fixed" by making the ancestor grants inheritable: the bundle
    # contract requires zero inheritance flags on every explicit ACE.
    assert "(OI)(CI)" not in source

    enumerate_at = source.index("$aclDescendants = @(Get-ChildItem")
    reverse_at = source.index("[Array]::Reverse($aclDescendants)")
    targets_at = source.index(
        "$aclTargets = @($aclDescendants) + @($bundleRoot, $provisioning)"
    )
    apply_at = source.index("foreach ($target in $aclTargets) {")
    grant_at = source.index("/inheritance:r /grant:r")
    verify_at = source.index("$finalAcl = Get-Acl -LiteralPath $target")
    unverified_at = source.index("worker_bundle_acl_unverified")
    binding_at = source.index("$binding = [ordered]@{")
    emit_at = source.index("Write-CreateOnce ([IO.Path]::GetFullPath($OutputBinding))")

    # The full target list is enumerated and reversed into descendant-first
    # order before the first descriptor is touched.
    assert enumerate_at < reverse_at < targets_at < apply_at < grant_at

    # Every final descriptor is checked after the apply loop, and the worker
    # binding is only built and written once that check has passed.
    assert grant_at < verify_at < unverified_at < binding_at < emit_at


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell 5.1")
def test_local_worker_provisioner_parses_with_powershell_51_apis() -> None:
    command = (
        "$tokens=$null;$errors=$null;"
        f"[Management.Automation.Language.Parser]::ParseFile('{PROVISIONER}',"
        "[ref]$tokens,[ref]$errors)|Out-Null;"
        "if($errors.Count){$errors|ForEach-Object{$_.Message};exit 1};"
        "$root=[IO.Path]::GetPathRoot('C:\\worker');"
        "$full=[IO.Path]::GetFullPath('C:\\worker');"
        "$drive=[IO.DriveInfo]::new($root);"
        "if($root -ne 'C:\\' -or $full -ne 'C:\\worker' -or $null -eq $drive){exit 2}"
    )
    result = subprocess.run(
        [str(WINDOWS_POWERSHELL), "-NoProfile", "-NonInteractive", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
