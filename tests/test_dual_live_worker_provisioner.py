import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROVISIONER = ROOT / "scripts" / "provision-dual-live-worker.ps1"
WINDOWS_POWERSHELL = Path(
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)


def test_local_worker_provisioner_is_one_source_grounded_external_closure_builder() -> None:
    source = PROVISIONER.read_text(encoding="utf-8")

    assert "python-3.12.6-embed-amd64.zip" in source
    assert "a86a2e28870967745d255cc597d1e4d19ae79e65e927cdc324baa0256202231c" in source
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
    for incompatible in (
        "[IO.Path]::GetRelativePath",
        "SHA256]::HashData",
        "[Convert]::ToHexString",
        "$IsWindows",
    ):
        assert incompatible not in source


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
